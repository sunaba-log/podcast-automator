"""Discord transcript メッセージから Episode を再構築し AgendaResult を生成する.

設計方針:
- Pure logic layer: I/O 禁止、Discord API 禁止、filesystem access 禁止
- 非決定論的な値(generated_at 等)は呼び出し元が生成して注入する
- Phase 1-A: reconstruct_episodes() と build_agenda() のみ実装
- Phase 1-B: extract_recurring_themes / extract_action_items / extract_discussion_prompts を追加予定
- sentence split は rule-based で実装し、重い NLP ライブラリは導入しない
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.discord_fetcher import DiscordMessage

# ── Enums ──────────────────────────────────────────────────────────────────────


class PromptType(StrEnum):
    """Discussion prompt の分類種別."""

    question = "question"
    uncertain = "uncertain"
    design_decision = "design_decision"
    future_consideration = "future_consideration"


class SortPolicy(StrEnum):
    """AgendaResult 内の各リストに適用するソート方針."""

    continuity = "continuity"
    """episode_count desc → mention_count desc(Phase 1 デフォルト)."""

    recentness = "recentness"
    """最新エピソード番号の言及を優先する."""

    hybrid = "hybrid"
    """continuity x recentness の重み付きスコア(Phase 2 実装予定)."""


# ── SeedTopic ─────────────────────────────────────────────────────────────────


@dataclass
class SeedTopic:
    """継続的に議論している概念を表す seed topic.

    flat graph 構造: parent_topic_id による参照で将来の階層化に対応する。
    Phase 1 では parent_topic_id は常に None。
    """

    id: str
    """一意のスラッグ。例: "infra-terraform"."""

    name: str
    """表示名。例: "インフラ / Terraform"."""

    category: str
    """大分類ラベル。例: "infrastructure", "product", "technology", "engineering"."""

    keywords: list[str]
    """いずれかが含まれれば「言及あり」と判定するキーワード群。"""

    parent_topic_id: str | None = None
    """Phase 1 は None。Phase 2+ で topic graph のエッジとして使用する。"""


# ── Episode ────────────────────────────────────────────────────────────────────


@dataclass
class Episode:
    """#N Meeting Transcript: を境界として再構築した 1 エピソード."""

    number: int
    """エピソード番号(整数)。表示時のみ display_number を使う。"""

    content: str
    """全 source_message の content を結合済みの全文テキスト。"""

    timestamp: str
    """境界メッセージ(#N Meeting Transcript:)の ISO8601 タイムスタンプ。"""

    source_message_ids: list[str]
    """このエピソードを構成する Discord message id のリスト(古い順)。"""

    @property
    def display_number(self) -> str:
        """表示用フォーマット。例: "#42"."""
        return f"#{self.number}"


# ── MentionEvidence ────────────────────────────────────────────────────────────


@dataclass
class MentionEvidence:
    """TopicMatch が保持する、言及箇所の構造化エビデンス."""

    source_episode: int
    """言及があったエピソード番号。"""

    text: str
    """キーワードを含む抜粋文(最大 100 字)。"""

    sentence_index: int
    """_split_into_sentences() 後の位置インデックス。前後文脈の再取得に使用する(Phase 2)。"""


# ── TopicMatch ─────────────────────────────────────────────────────────────────


@dataclass
class TopicMatch:
    """Seed topic ごとの言及状況まとめ.

    topic_id は SeedTopic.id(rename 耐性のある安定識別子)。
    display_name は表示用で、SeedTopic.name を参照せずとも描画できる。
    """

    topic_id: str
    """SeedTopic.id。rename 後も安定する識別子。"""

    display_name: str
    """SeedTopic.name の表示用コピー。参照解決なしで描画できる。"""

    episode_count: int
    """言及があったエピソード数(主指標: 継続性の根拠)。"""

    mention_count: int
    """全エピソード通算のキーワードマッチ行数(副指標)。"""

    evidence: list[MentionEvidence]
    """言及箇所のエビデンス(最大 3 件)。"""

    score: float | None = None
    """Phase 1 は None。Phase 2+ でランキングスコアとして使用する。"""


# ── ActionItem ─────────────────────────────────────────────────────────────────


@dataclass
class ActionItem:
    """議事録から抽出されたアクションアイテム."""

    text: str
    """アクションアイテムのテキスト。"""

    source_episode: int
    """抽出元エピソード番号。"""

    assignee: str | None = None
    """Phase 1 は None。Phase 2+ で @username パターン抽出を実装予定。"""


# ── DiscussionPrompt ───────────────────────────────────────────────────────────


@dataclass
class DiscussionPrompt:
    """未解決の論点として分類された 1 文."""

    sentence: str
    """分類対象の 1 文(sentence 単位で抽出)。"""

    prompt_type: PromptType
    """分類種別。StrEnum のため JSON は文字列として出力される。"""

    source_episode: int
    """抽出元エピソード番号。"""

    confidence: float | None = None
    """Phase 1(ルールベース)は None。Phase 4(LLM)で 0.0-1.0 の値が入る。"""


# ── AgendaMetadata ─────────────────────────────────────────────────────────────


@dataclass
class AgendaMetadata:
    """AgendaResult のスナップショット・再現性用メタデータ."""

    generated_at: str
    """ISO8601 UTC。呼び出し元(agenda_main.py)が生成して渡す。"""

    source_episode_numbers: list[int]
    """分析対象エピソード番号のリスト(降順)。build_agenda() が自動導出する。"""

    sort_policy: str
    """使用した SortPolicy の値(差分比較・再現用)。"""

    analysis_window_size: int
    """fetch_messages() の limit 値(要求した取得件数)。"""

    fetched_message_count: int
    """Discord API が実際に返したメッセージ数。limit と一致しないことがある。"""


# ── AgendaResult ───────────────────────────────────────────────────────────────


@dataclass
class AgendaResult:
    """週次アジェンダの生成結果。JSON-serializable かつ snapshot 保存対応."""

    metadata: AgendaMetadata
    analyzed_episodes: int
    recurring_themes: list[TopicMatch]
    action_items: list[ActionItem]
    discussion_prompts: list[DiscussionPrompt]
    schema_version: str = "1.0"
    """スキーマバージョン。将来の移行検知に使用する。default 値のため末尾に配置。"""

    def to_dict(self) -> dict:  # type: ignore[type-arg]
        """dataclasses.asdict() 経由で完全 JSON-serializable な dict を返す.

        StrEnum は str のサブクラスのため追加エンコーダ不要。
        ``json.dumps(result.to_dict(), ensure_ascii=False, indent=2)`` で可読出力。
        """
        return dataclasses.asdict(self)


# ── Exception ──────────────────────────────────────────────────────────────────


class TranscriptBoundaryError(Exception):
    """strict=True 時に境界不整合を検知した場合に raise する."""

    def __init__(self, message: str, offending_message_id: str) -> None:
        """例外を初期化する.

        Args:
            message: エラーの詳細。
            offending_message_id: 問題が検知された Discord message id。
        """
        super().__init__(message)
        self.offending_message_id = offending_message_id


# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_SEED_TOPICS: list[SeedTopic] = [
    SeedTopic(
        id="infra-terraform",
        name="インフラ / Terraform",
        category="infrastructure",
        keywords=["Terraform", "terraform", "GCP", "Cloud Run", "インフラ", "デプロイ"],
    ),
    SeedTopic(
        id="product-podcast",
        name="ポッドキャスト収録フロー",
        category="product",
        keywords=["収録", "音声", "エピソード", "RSS", "アップロード"],
    ),
    SeedTopic(
        id="tech-ai-llm",
        name="AI / LLM 活用",
        category="technology",
        keywords=["AI", "LLM", "Gemini", "Claude", "モデル", "プロンプト"],
    ),
    SeedTopic(
        id="eng-architecture",
        name="アーキテクチャ設計",
        category="engineering",
        keywords=["アーキテクチャ", "設計", "構成", "モジュール", "責務"],
    ),
    SeedTopic(
        id="infra-discord",
        name="Discord 連携",
        category="infrastructure",
        keywords=["Discord", "Webhook", "Bot", "チャンネル", "通知"],
    ),
    SeedTopic(
        id="infra-scheduler",
        name="自動化 / スケジューラ",
        category="infrastructure",
        keywords=["自動", "Scheduler", "定期", "cron", "トリガー"],
    ),
]

ACTION_KEYWORDS: list[str] = [
    # English explicit markers (case-sensitive)
    "TODO",
    "TODO:",
    "fix",
    "investigate",
    # Japanese explicit markers
    "やること",
    "対応する",
    "対応します",
    "確認する",
    "確認します",
    "確認が必要",
    "検討する",
    "検討が必要",
    "実装する",
    "修正する",
    "しておく",
    "しなければ",
    "必要がある",
]

# 優先順位順に評価する(先頭の型が優先される)
PROMPT_PATTERNS: dict[PromptType, list[str]] = {
    PromptType.design_decision: [
        r"にするか",
        r"べきか",
        r"どっちが",
        r"どう設計",
        r"どう実装",
        r"方針",
        r"アーキテクチャ",
    ],
    PromptType.future_consideration: [
        r"将来",
        r"いずれ",
        r"次のフェーズ",
        r"[Pp]hase\s*[2-9]",
        r"今後",
        r"長期",
        r"ロードマップ",
    ],
    PromptType.question: [r"[??]"],
    PromptType.uncertain: [
        r"かもしれない",
        r"どうするか",
        r"未定",
        r"検討中",
        r"まだ決まって",
        r"迷って",
    ],
}

# search() + MULTILINE を使用: match() より robust。
# - 行頭(^)にパターンがあれば検出(引用符やプレフィックスへの耐性)
# - multiline なメッセージでも安全に境界検出できる
_EPISODE_BOUNDARY_RE: re.Pattern[str] = re.compile(
    r"^#(\d+)\s+Meeting Transcript:",
    re.MULTILINE,
)


# ── TranscriptAnalyzer ────────────────────────────────────────────────────────


class TranscriptAnalyzer:
    """Discord transcript メッセージを解析して AgendaResult を生成する pure logic クラス.

    禁止事項: I/O、Discord API 呼び出し、filesystem アクセス、datetime.now() 直接呼び出し。
    非決定論的な値(generated_at)は呼び出し元が生成して渡す。
    """

    def __init__(self, seed_topics: list[SeedTopic] | None = None) -> None:
        """アナライザーを初期化する.

        Args:
            seed_topics: 使用する seed topics。None の場合は DEFAULT_SEED_TOPICS を使用する。
        """
        self._seed_topics: list[SeedTopic] = seed_topics if seed_topics is not None else DEFAULT_SEED_TOPICS

    # ── 公開メソッド ───────────────────────────────────────────────────────────

    def reconstruct_episodes(
        self,
        messages: list[DiscordMessage],
        *,
        strict: bool = False,
    ) -> tuple[list[Episode], list[str]]:
        """新しい順のメッセージを Episode リスト(古い順)に再構築する.

        split_message() によって複数のメッセージに分割された transcript を
        "#N Meeting Transcript:" を境界として 1 エピソードに結合する。

        メッセージは timestamp 昇順(古い順)にソートしてから処理する。
        このため Discord API が返す順序に依存しない。

        Args:
            messages: Discord API から取得した生メッセージのリスト(順序不問)。
            strict: True の場合、境界不整合で TranscriptBoundaryError を raise する。
                    False の場合、不整合を warnings に収集して処理を継続する。

        Returns:
            (episodes, warnings) のタプル。
            episodes: 古い順にソートされた Episode リスト。
            warnings: strict=False 時に収集した警告メッセージ。strict=True 時は常に空。

        Raises:
            TranscriptBoundaryError: strict=True かつ境界不整合を検知した場合。
        """
        warnings: list[str] = []

        # timestamp 昇順ソート(ISO8601 は辞書順と時系列が一致する)
        # reversed(messages) ではなく sort することで API の返却順序に依存しない
        ordered = sorted(messages, key=lambda m: m.timestamp)

        episodes: list[Episode] = []
        current_episode: Episode | None = None
        current_episode_author: str | None = None

        for msg in ordered:
            boundary_match = _EPISODE_BOUNDARY_RE.search(msg.content)

            if boundary_match:
                episode_number = int(boundary_match.group(1))

                # エピソード番号の逆転チェック(時系列上あり得ない番号の減少)
                if current_episode is not None and episode_number <= current_episode.number:
                    warning = (
                        f"Episode number regression: got #{episode_number} "
                        f"after #{current_episode.number} at message id={msg.id}"
                    )
                    if strict:
                        raise TranscriptBoundaryError(warning, offending_message_id=msg.id)
                    warnings.append(warning)

                # 前のエピソードを確定して保存する
                if current_episode is not None:
                    episodes.append(current_episode)

                current_episode = Episode(
                    number=episode_number,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    source_message_ids=[msg.id],
                )
                current_episode_author = msg.author_name

            elif current_episode is not None:
                # 現在のエピソードの続き(split_message による分割部分)
                # author_name が境界メッセージと異なる場合は unrelated chat の可能性
                if current_episode_author is not None and msg.author_name != current_episode_author:
                    warning = (
                        f"Unexpected author in episode {current_episode.display_number}: "
                        f"expected '{current_episode_author}' but got '{msg.author_name}' "
                        f"at message id={msg.id}. Possible unrelated chat included."
                    )
                    if strict:
                        raise TranscriptBoundaryError(warning, offending_message_id=msg.id)
                    warnings.append(warning)

                current_episode.content += "\n" + msg.content
                current_episode.source_message_ids.append(msg.id)

            else:
                # エピソード境界が確立される前の孤立メッセージ
                warning = f"Skipping orphan message id={msg.id}: no episode boundary established"
                if strict:
                    raise TranscriptBoundaryError(warning, offending_message_id=msg.id)
                warnings.append(warning)

        # ループ終了後、未保存の最後のエピソードを追加する
        if current_episode is not None:
            episodes.append(current_episode)

        return episodes, warnings

    def build_agenda(
        self,
        episodes: list[Episode],
        recurring_themes: list[TopicMatch],
        action_items: list[ActionItem],
        discussion_prompts: list[DiscussionPrompt],
        *,
        sort_policy: SortPolicy = SortPolicy.continuity,
        generated_at: str,
        analysis_window_size: int,
        fetched_message_count: int,
    ) -> AgendaResult:
        """受け取った抽出結果を sort_policy でソートし AgendaResult を組み立てる.

        extract_* メソッドは呼び出さない。受け取った結果のソートと組み立てのみを行う。
        Phase 1-A では recurring_themes / action_items / discussion_prompts に空リストを渡す。

        Args:
            episodes: reconstruct_episodes() で再構築したエピソードリスト。
            recurring_themes: extract_recurring_themes() の結果(Phase 1-A は [])。
            action_items: extract_action_items() の結果(Phase 1-A は [])。
            discussion_prompts: extract_discussion_prompts() の結果(Phase 1-A は [])。
            sort_policy: ソート方針。
            generated_at: ISO8601 UTC 文字列。呼び出し元が生成して渡す。
            analysis_window_size: fetch_messages() に渡した limit 値。
            fetched_message_count: Discord API が実際に返したメッセージ数。

        Returns:
            ソート済みの AgendaResult。

        Raises:
            NotImplementedError: sort_policy=SortPolicy.hybrid の場合(Phase 2 実装予定)。
        """
        if sort_policy == SortPolicy.hybrid:
            msg = "SortPolicy.hybrid は Phase 2 で実装予定です。"
            raise NotImplementedError(msg)

        sorted_themes = self._sort_themes(recurring_themes, sort_policy)
        sorted_items = self._sort_action_items(action_items, sort_policy)
        sorted_prompts = self._sort_discussion_prompts(discussion_prompts, sort_policy)

        source_episode_numbers = sorted(
            {ep.number for ep in episodes},
            reverse=True,
        )

        metadata = AgendaMetadata(
            generated_at=generated_at,
            source_episode_numbers=source_episode_numbers,
            sort_policy=str(sort_policy),
            analysis_window_size=analysis_window_size,
            fetched_message_count=fetched_message_count,
        )

        return AgendaResult(
            metadata=metadata,
            analyzed_episodes=len(episodes),
            recurring_themes=sorted_themes,
            action_items=sorted_items,
            discussion_prompts=sorted_prompts,
        )

    # ── 公開メソッド (Phase 1-B) ─────────────────────────────────────────────

    def extract_recurring_themes(
        self,
        episodes: list[Episode],
    ) -> list[TopicMatch]:
        """エピソード群から繰り返し登場するトピックを抽出する.

        precision 優先: seed topic の keyword を line-level で包含チェックする。
        score は mention_count の単純カウント (Phase 1-B)。

        Args:
            episodes: 分析対象の Episode リスト。

        Returns:
            1 件以上マッチした TopicMatch のリスト (mention_count 降順)。
        """
        results: list[TopicMatch] = []
        for topic in self._seed_topics:
            all_evidence: list[MentionEvidence] = []
            matched_episodes: set[int] = set()

            for episode in episodes:
                evidence = self._match_topic_in_episode(episode, topic)
                if evidence:
                    matched_episodes.add(episode.number)
                    all_evidence.extend(evidence)

            if not all_evidence:
                continue

            results.append(
                TopicMatch(
                    topic_id=topic.id,
                    display_name=topic.name,
                    episode_count=len(matched_episodes),
                    mention_count=len(all_evidence),
                    evidence=all_evidence[:3],
                    score=float(len(all_evidence)),
                )
            )

        return sorted(results, key=lambda t: -t.mention_count)

    def extract_action_items(
        self,
        episodes: list[Episode],
    ) -> list[ActionItem]:
        """エピソード群から明示的なアクションアイテムを抽出する.

        precision 優先: ACTION_KEYWORDS の line-level 包含チェックのみ実施する。

        Args:
            episodes: 分析対象の Episode リスト。

        Returns:
            抽出した ActionItem のリスト (古いエピソード順)。
        """
        return [
            ActionItem(
                text=line.strip()[:200],
                source_episode=episode.number,
            )
            for episode in episodes
            for line in episode.content.splitlines()
            if self._is_action_line(line)
        ]

    def extract_discussion_prompts(
        self,
        episodes: list[Episode],
    ) -> list[DiscussionPrompt]:
        """エピソード群から未解決論点の候補となる文を抽出する.

        PROMPT_PATTERNS を定義順(優先順位順)に評価し、
        最初にマッチした PromptType を採用する。

        Args:
            episodes: 分析対象の Episode リスト。

        Returns:
            抽出した DiscussionPrompt のリスト。
        """
        prompts: list[DiscussionPrompt] = []
        for episode in episodes:
            for sentence in self._split_into_sentences(episode.content):
                prompt_type = self._classify_sentence(sentence)
                if prompt_type is not None:
                    prompts.append(
                        DiscussionPrompt(
                            sentence=sentence[:200],
                            prompt_type=prompt_type,
                            source_episode=episode.number,
                        )
                    )
        return prompts

    # ── プライベートヘルパー (Phase 1-B) ─────────────────────────────────────

    def _match_topic_in_episode(
        self,
        episode: Episode,
        topic: SeedTopic,
    ) -> list[MentionEvidence]:
        """エピソード内で seed topic のキーワードがマッチした行を MentionEvidence として返す."""
        evidence: list[MentionEvidence] = []
        for line_idx, line in enumerate(episode.content.splitlines()):
            stripped = line.strip()
            if not stripped:
                continue
            if any(kw in stripped for kw in topic.keywords):
                evidence.append(
                    MentionEvidence(
                        source_episode=episode.number,
                        text=stripped[:100],
                        sentence_index=line_idx,
                    )
                )
        return evidence

    def _split_into_sentences(self, text: str) -> list[str]:
        """テキストを行単位の sentence リストに分割する (rule-based).

        各行を 1 sentence として扱う。URL やファイル名を誤分割しないよう
        ASCII ピリオドでは分割しない。重い NLP ライブラリは使用しない。
        """
        return [line.strip() for line in text.splitlines() if line.strip()]

    def _classify_sentence(self, sentence: str) -> PromptType | None:
        """文を PROMPT_PATTERNS で分類する.

        PROMPT_PATTERNS の定義順(優先順位順)に評価し、
        最初にマッチした PromptType を返す。マッチなしは None。
        """
        for prompt_type, patterns in PROMPT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, sentence):
                    return prompt_type
        return None

    def _is_action_line(self, line: str) -> bool:
        """ACTION_KEYWORDS のいずれかを含む行かどうかを返す.

        英語キーワード (fix, investigate, TODO) は case-insensitive で比較する。
        日本語キーワードは大文字小文字の概念がないためそのまま比較する。
        """
        stripped = line.strip()
        if not stripped:
            return False
        line_lower = stripped.lower()
        return any(kw.lower() in line_lower for kw in ACTION_KEYWORDS)

    # ── プライベートヘルパー ───────────────────────────────────────────────────

    def _sort_themes(
        self,
        themes: list[TopicMatch],
        sort_policy: SortPolicy,
    ) -> list[TopicMatch]:
        """recurring_themes を sort_policy に従いソートする."""
        if sort_policy == SortPolicy.continuity:
            return sorted(themes, key=lambda t: (-t.episode_count, -t.mention_count))
        if sort_policy == SortPolicy.recentness:
            return sorted(
                themes,
                key=lambda t: max((e.source_episode for e in t.evidence), default=0),
                reverse=True,
            )
        return list(themes)

    def _sort_action_items(
        self,
        items: list[ActionItem],
        sort_policy: SortPolicy,
    ) -> list[ActionItem]:
        """action_items を sort_policy に従いソートする."""
        if sort_policy == SortPolicy.continuity:
            return sorted(items, key=lambda i: i.source_episode)
        if sort_policy == SortPolicy.recentness:
            return sorted(items, key=lambda i: i.source_episode, reverse=True)
        return list(items)

    def _sort_discussion_prompts(
        self,
        prompts: list[DiscussionPrompt],
        sort_policy: SortPolicy,
    ) -> list[DiscussionPrompt]:
        """discussion_prompts を sort_policy に従いソートする."""
        if sort_policy in (SortPolicy.continuity, SortPolicy.recentness):
            return sorted(prompts, key=lambda p: p.source_episode, reverse=True)
        return list(prompts)
