"""AgendaResult を Discord markdown メッセージに整形するフォーマッタ.

設計方針:
- Pure function: I/O 禁止、logger 禁止、datetime.now() 禁止、env access 禁止
- Discord API の知識を持たない (メッセージ長の上限値のみ定数として持つ)
- split_message() に依存しない。formatter 単体で長さ制限を管理する
- section 単位で budget 管理し、超過しそうな section を丸ごとスキップする
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.news_relevance import NewsCandidate
    from services.transcript_analyzer import (
        ActionItem,
        AgendaResult,
        DiscussionPrompt,
        MentionEvidence,
        TopicMatch,
    )

# Discord が許容する 1 メッセージの文字数上限 (実際は 2000 だが余裕を持たせる)
_MAX_MESSAGE_LENGTH: int = 1900

# action_item / discussion_prompt / news title の 1 行あたりの最大文字数
_MAX_LINE_LENGTH: int = 80


def format_agenda_message(
    result: AgendaResult,
    *,
    news_candidates: list[NewsCandidate] | None = None,
    max_themes: int = 3,
    max_items: int = 0,
    max_prompts: int = 3,
    max_news: int = 3,
) -> str:
    """AgendaResult を Discord 投稿用 markdown 文字列に整形する.

    Pure function: 引数のみを使用し、副作用を持たない。

    セクション構成:
      1. ヘッダー (常に表示)
      2. 最近よく出てきたテーマ (0 件の場合は省略)
      3. 最近の会話と繋がりそうなニュース (news_candidates が None / 空の場合は省略)
      4. アクションアイテム (max_items=0 の場合は省略 / デフォルト非表示)
      5. 気になっている問い (0 件の場合は省略)
      6. フッター (常に表示)

    長さ制御:
      ヘッダーとフッターを先に確保し、残りの budget に収まるセクションのみ
      追加する。section 単位でスキップするため、メッセージが途中で切れない。

    Args:
        result: フォーマット対象の AgendaResult。
        news_candidates: ニュース候補リスト。None または空の場合はニュースセクションを省略。
        max_themes: 表示する recurring_themes の最大件数。
        max_items: 表示する action_items の最大件数。0 の場合はセクション非表示 (デフォルト)。
        max_prompts: 表示する discussion_prompts の最大件数。
        max_news: 表示する news_candidates の最大件数。

    Returns:
        Discord markdown 形式の文字列。_MAX_MESSAGE_LENGTH 以内に収まる。
    """
    header = "🎙️ **今週の会話のタネ**"
    footer = _build_footer(result, news_candidates)

    # ヘッダー、フッター、区切り文字分を先に予算から差し引く
    base_cost = len(header) + 2 + len(footer)
    budget = _MAX_MESSAGE_LENGTH - base_cost

    candidate_sections = [
        _build_themes_section(result.recurring_themes[:max_themes]),
        _build_news_section((news_candidates or [])[:max_news]),
        _build_items_section(result.action_items[:max_items]),
        _build_prompts_section(result.discussion_prompts[:max_prompts]),
    ]

    included: list[str] = []
    for section in candidate_sections:
        if section is None:
            continue
        cost = len(section) + 2  # +2 for "\n\n" separator
        if budget >= cost:
            included.append(section)
            budget -= cost

    parts = [header, *included, footer]
    return "\n\n".join(parts)


# ── Section builders ───────────────────────────────────────────────────────────


def _build_themes_section(themes: list[TopicMatch]) -> str | None:
    """テーマセクションを構築する。0 件の場合は None を返す."""
    if not themes:
        return None
    lines = ["🧵 **最近よく出てきたテーマ**"]
    lines.extend(f"・{theme.display_name}" for theme in themes)
    return "\n".join(lines)


def _build_news_section(candidates: list[NewsCandidate]) -> str | None:
    """ニュースセクションを構築する。0 件の場合は None を返す.

    1 件あたり 2 行:
      ・{title} ({source})
        ↳ {topic}
    """
    if not candidates:
        return None
    lines = ["🗞️ **最近の会話と繋がりそうなニュース**"]
    for c in candidates:
        title = _truncate(c.news_item.title, _MAX_LINE_LENGTH)
        source = c.news_item.source
        topic = c.topic_match.display_name
        lines.append(f"・{title} ({source})")
        lines.append(f"  ↳ {topic}")
    return "\n".join(lines)


def _build_items_section(items: list[ActionItem]) -> str | None:
    """action_items セクションを構築する。0 件の場合は None を返す."""
    if not items:
        return None
    lines = ["✅ **アクションアイテム**"]
    for item in items:
        text = _truncate(item.text, _MAX_LINE_LENGTH)
        lines.append(f"・{text} [#{item.source_episode}]")
    return "\n".join(lines)


def _build_prompts_section(prompts: list[DiscussionPrompt]) -> str | None:
    """discussion_prompts セクションを構築する。0 件の場合は None を返す."""
    if not prompts:
        return None
    lines = ["💡 **気になっている問い**"]
    for prompt in prompts:
        sentence = _truncate(prompt.sentence, _MAX_LINE_LENGTH)
        lines.append(f"・{sentence} [#{prompt.source_episode}]")
    return "\n".join(lines)


def _build_footer(result: AgendaResult, news_candidates: list[NewsCandidate] | None = None) -> str:
    """分析メタデータのフッターを構築する.

    news_candidates が存在する場合はニュース接続件数を表示する。
    """
    ep_count = result.analyzed_episodes
    if news_candidates:
        return f"📊 *{ep_count} エピソード / {len(news_candidates)} ニュース接続*"
    fetched = result.metadata.fetched_message_count
    return f"📊 *分析: {ep_count} エピソード / {fetched} 件取得*"


# ── Line-level helpers ─────────────────────────────────────────────────────────


def _format_episode_refs(evidence: list[MentionEvidence]) -> str:
    """Evidence リストからエピソード参照文字列 (#N, #M, ...) を生成する.

    重複するエピソード番号は排除し、登場順を維持する。
    現在は formatter 内では未使用だが、外部からのテスト用に公開を維持する。
    """
    seen: set[int] = set()
    ep_nums: list[int] = []
    for ev in evidence:
        if ev.source_episode not in seen:
            seen.add(ev.source_episode)
            ep_nums.append(ev.source_episode)
    if not ep_nums:
        return ""
    return "(" + ", ".join(f"#{n}" for n in ep_nums) + ")"


def _truncate(text: str, max_len: int) -> str:
    """Text が max_len を超える場合は '...' を付けて切り詰める."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
