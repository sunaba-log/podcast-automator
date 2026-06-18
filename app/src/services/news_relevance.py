"""ニュースアイテムとアジェンダトピックの関連度を計算するモジュール.

設計方針:
- Pure logic layer: I/O 禁止、外部 API 禁止、env access 禁止
- NewsScoringStrategy Protocol 経由でスコアリング実装を差し替え可能にする
- Phase 3-B: KeywordScoringStrategy のみ実装。LLM / embedding は Phase 3-D 以降
- match_news_to_agenda() が安定 API。dedup / sort / filter は固定ロジック
- 同一 URL が複数トピックにマッチした場合は最高スコアの候補のみを残す
- score は normalized float 0.0-1.0。TopicMatch.score (transcript mention count) は使用しない
- match_reason はまだ実装しない (Phase 3-D で LLM が文章生成できるようになってから)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlparse

if TYPE_CHECKING:
    from services.news_fetcher import NewsItem
    from services.transcript_analyzer import AgendaResult, TopicMatch

logger = logging.getLogger(__name__)

DEFAULT_SCORE_THRESHOLD: float = 0.05
"""スコアの下限値。この値未満の候補はフィルタされる。"""

DEFAULT_MAX_CANDIDATES: int = 10
"""返す候補の最大件数 (relevance concern)。表示件数は formatter 側で制御する。"""


# ── Data classes ───────────────────────────────────────────────────────────────


@dataclass
class NewsCandidate:
    """ニュースアイテムとアジェンダトピックのマッチング結果.

    Attributes:
        news_item: マッチしたニュースアイテム。
        topic_match: マッチしたアジェンダトピック (最高スコアのトピック)。
        score: 関連度スコア (0.0-1.0 normalized)。
        matched_keywords: マッチしたキーワードのリスト (observability 用、topic_match.keywords 定義順)。
    """

    news_item: NewsItem
    topic_match: TopicMatch
    score: float
    matched_keywords: list[str] = field(default_factory=list)


# ── Scoring Protocol ───────────────────────────────────────────────────────────


class NewsScoringStrategy(Protocol):
    """ニュースアイテムとトピックの関連度スコアリングのインターフェース.

    Phase 3-B: KeywordScoringStrategy のみ実装。
    Phase 3-D: LLM ベースのスコアリングに差し替え可能。
    Phase 3-E: embedding ベースのスコアリングに差し替え可能。
    """

    def score(
        self,
        news_item: NewsItem,
        topic_match: TopicMatch,
    ) -> tuple[float, list[str]]:
        """ニュースアイテムとトピックの関連度スコアを計算する.

        Args:
            news_item: スコアリング対象のニュースアイテム。
            topic_match: 比較対象のトピックマッチ (keywords を使用する)。

        Returns:
            (score, matched_keywords) のタプル。
            score: 0.0-1.0 の normalized スコア。
            matched_keywords: マッチしたキーワードのリスト (topic_match.keywords 定義順)。
        """
        ...  # pragma: no cover


class KeywordScoringStrategy:
    """キーワード包含チェックによるスコアリング実装.

    topic_match.keywords が news_item の title / summary に含まれるかを
    case-insensitive で検索する。

    score 計算式:
        score = (title_hit_count * 2 + summary_only_count) / (total_kw_count * 2)

    title ヒットは summary ヒットの 2 倍の重みを持つ。
    同一キーワードが title と summary の両方に出現した場合は title ヒットとして扱う。
    score は 0.0-1.0 に bounded: 全キーワードが title にマッチした場合のみ 1.0。
    """

    def score(
        self,
        news_item: NewsItem,
        topic_match: TopicMatch,
    ) -> tuple[float, list[str]]:
        """ニュースアイテムとトピックのキーワードマッチスコアを計算する.

        Args:
            news_item: スコアリング対象のニュースアイテム。
            topic_match: 比較対象のトピックマッチ (keywords を使用する)。

        Returns:
            (score, matched_keywords) のタプル。
            score: 0.0-1.0 の normalized スコア。keywords が空の場合は 0.0。
            matched_keywords: マッチしたキーワードのリスト (topic_match.keywords 定義順)。
        """
        if not topic_match.keywords:
            return (0.0, [])

        total = len(topic_match.keywords)
        title_lower = news_item.title.lower()
        summary_lower = (news_item.summary or "").lower()

        # topic_match.keywords の定義順にイテレーションして deterministic に収集する
        # set を経由しない: Python set のイテレーション順は非決定的
        matched: list[str] = []
        title_hit_count = 0

        for kw in topic_match.keywords:
            kw_lower = kw.lower()
            in_title = _kw_in_text(kw_lower, title_lower)
            in_summary = _kw_in_text(kw_lower, summary_lower)
            if in_title or in_summary:
                matched.append(kw)
                if in_title:
                    title_hit_count += 1

        summary_only_count = len(matched) - title_hit_count
        weighted_score = (title_hit_count * 2 + summary_only_count) / (total * 2)

        return (weighted_score, matched)


# ── Private helpers ────────────────────────────────────────────────────────────


def _kw_in_text(kw_lower: str, text_lower: str) -> bool:
    r"""キーワードがテキストに含まれるか判定する.

    マッチ戦略はキーワードの種類によって分岐する:

        * **ASCII single-word** (スペースなし・全 ASCII): word-boundary マッチ。
      ``re.search(r'\\bkw\\b', text)`` を使用し、"ai" が "airport" や "trail" の
      部分文字列としてマッチすることを防ぐ。
    * **フレーズ** (スペースを含む): 従来の substring マッチ。
      "cloud run" は順序付き連続マッチが必要なため substring が適切。
    * **非 ASCII** (日本語等): 従来の substring マッチ。
      日本語には単語境界 (``\\b``) が適用されないため。

    Args:
        kw_lower: 小文字化済みのキーワード文字列。
        text_lower: 小文字化済みの検索対象テキスト文字列。

    Returns:
        キーワードがテキストに含まれる場合 True、含まれない場合 False。
    """
    # フレーズ (スペースを含む) → substring マッチ
    if " " in kw_lower:
        return kw_lower in text_lower
    # 純粋な ASCII 単語 → word-boundary マッチ
    if kw_lower.isascii():
        return bool(re.search(r"\b" + re.escape(kw_lower) + r"\b", text_lower))
    # 日本語など非 ASCII → substring マッチ
    return kw_lower in text_lower


def _normalize_url(url: str) -> str:
    """URL を正規化する (dedup キーとして使用).

    クエリパラメータとフラグメントを除去し、trailing slash を正規化する。
    scheme + netloc + path のみを使用する。

    Args:
        url: 正規化対象の URL。

    Returns:
        scheme://netloc/path 形式の正規化済み URL。
        url が空文字列の場合は空文字列を返す。
    """
    if not url:
        return ""
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}{p.path}".rstrip("/")


def _dedup_by_url(candidates: list[NewsCandidate]) -> list[NewsCandidate]:
    """同一 URL の候補が複数トピックにマッチした場合、最高スコアのものだけを残す.

    同スコアの場合は candidates リストの先頭側を優先する (処理順に依存)。
    URL は _normalize_url() で正規化してから比較する。

    Args:
        candidates: 全トピック x 全ニュースのスコアリング結果。

    Returns:
        URL ごとに最高スコアの候補のみを含むリスト。元の candidates の順序は保持しない。
    """
    best_by_url: dict[str, NewsCandidate] = {}
    for candidate in candidates:
        norm_url = _normalize_url(candidate.news_item.url)
        existing = best_by_url.get(norm_url)
        if existing is None or candidate.score > existing.score:
            best_by_url[norm_url] = candidate
    return list(best_by_url.values())


def _sort_candidates(candidates: list[NewsCandidate]) -> list[NewsCandidate]:
    """候補を deterministic な順序でソートする.

    ソートキー (優先順):
    1. score 降順 (関連度が高い方が上)
    2. published_at 降順 (新しい方が上)
    3. url 昇順 (tiebreaker: 完全 deterministic を保証)

    Args:
        candidates: ソート対象の候補リスト。

    Returns:
        ソート済みの候補リスト (新しいリストを返す、元のリストは変更しない)。
    """
    return sorted(
        candidates,
        key=lambda c: (-c.score, -c.news_item.published_at.timestamp(), c.news_item.url),
    )


def _filter_candidates(
    candidates: list[NewsCandidate],
    threshold: float,
) -> list[NewsCandidate]:
    """スコアが threshold 未満の候補を除去する.

    threshold と等しいスコアは保持する (>= の包含的比較)。

    Args:
        candidates: フィルタ対象の候補リスト。
        threshold: スコアの下限値。この値以上の候補のみを残す。

    Returns:
        threshold 以上のスコアを持つ候補のリスト。
    """
    return [c for c in candidates if c.score >= threshold]


# ── Public API ─────────────────────────────────────────────────────────────────


def match_news_to_agenda(
    news_items: list[NewsItem],
    agenda_result: AgendaResult,
    *,
    strategy: NewsScoringStrategy | None = None,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> list[NewsCandidate]:
    """ニュースアイテムとアジェンダトピックを関連度でマッチングする.

    pipeline (固定ロジック):
        1. 全トピック x 全ニュースをスコアリング (strategy に委譲)
        2. 同一 URL の重複を除去 (最高スコアのトピックのみ残す)
        3. score_threshold 未満を除去
        4. score desc → published_at desc → url asc でソート
        5. max_candidates 件に切り詰め

    差し替え可能な部分:
        - strategy: NewsScoringStrategy を実装したオブジェクトを渡すことで
          LLM / embedding ベースのスコアリングに差し替えられる

    Args:
        news_items: スコアリング対象のニュースアイテムリスト。
        agenda_result: アジェンダ分析結果 (recurring_themes を使用する)。
        strategy: スコアリング戦略。None の場合は KeywordScoringStrategy を使用する。
        max_candidates: 返す候補の最大件数 (relevance concern、表示件数は formatter 側)。
        score_threshold: スコアの下限値。この値未満の候補はフィルタされる。

    Returns:
        score desc → published_at desc → url asc でソートされた NewsCandidate リスト。
        max_candidates 件に切り詰められる。
        ニュースがない / トピックがない場合は空リストを返す。
    """
    _strategy: NewsScoringStrategy = strategy if strategy is not None else KeywordScoringStrategy()
    topics = agenda_result.recurring_themes or []

    if not news_items or not topics:
        logger.info(
            "news_matching: skipped (total_news=%d, topics=%d)",
            len(news_items),
            len(topics),
        )
        return []

    # Step 1: 全トピック x 全ニュースをスコアリング
    all_candidates: list[NewsCandidate] = []
    for topic_match in topics:
        if not topic_match.keywords:
            logger.debug("Skipping topic with no keywords: topic_id=%s", topic_match.topic_id)
            continue
        for news_item in news_items:
            score, matched_keywords = _strategy.score(news_item, topic_match)
            logger.debug(
                "scored: title='%s' topic='%s' score=%.3f matched=%s",
                news_item.title[:50],
                topic_match.topic_id,
                score,
                matched_keywords,
            )
            all_candidates.append(
                NewsCandidate(
                    news_item=news_item,
                    topic_match=topic_match,
                    score=score,
                    matched_keywords=matched_keywords,
                )
            )

    # Step 2: 同一 URL の重複を除去 (最高スコアのトピックのみ残す)
    deduped = _dedup_by_url(all_candidates)

    # Step 3: threshold 未満を除去
    filtered = _filter_candidates(deduped, score_threshold)
    filtered_count = len(deduped) - len(filtered)

    # Step 4: deterministic ソート
    sorted_candidates = _sort_candidates(filtered)

    # Step 5: max_candidates 件に切り詰め
    final = sorted_candidates[:max_candidates]

    logger.info(
        "news_matching: total_news=%d, topics=%d, candidates=%d, filtered=%d, threshold=%.3f, returned=%d",
        len(news_items),
        len(topics),
        len(deduped),
        filtered_count,
        score_threshold,
        len(final),
    )

    # observability: フィルタで落ちた候補のうち最高スコアをデバッグログに出す
    if filtered_count > 0:
        below_threshold = [c for c in deduped if c.score < score_threshold]
        if below_threshold:
            top_filtered = max(below_threshold, key=lambda c: c.score)
            logger.debug(
                "Top filtered candidate: score=%.3f title='%s'",
                top_filtered.score,
                top_filtered.news_item.title[:50],
            )

    return final
