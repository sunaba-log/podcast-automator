"""Weekly agenda notification job for Discord.

このモジュールは毎週水曜日 07:00 JST に Cloud Scheduler によって起動され、
ポッドキャスト収録の週次リマインダーを Discord へ投稿します。

Phase 1-A: Discord transcript チャンネルから過去議事録を取得し、
           Episode に再構築して AgendaResult を JSON として出力する検証フェーズ。
Phase 3-C: RSS ニュースを取得し、アジェンダトピックとの関連度でマッチングして通知する。
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from services.agenda_formatter import format_agenda_message
from services.discord_fetcher import DiscordFetcher
from services.news_fetcher import DEFAULT_RSS_SOURCES, NewsFetcher
from services.news_relevance import NewsCandidate, match_news_to_agenda
from services.news_researcher import AINewsResearcher
from services.notifier import Notifier
from services.transcript_analyzer import AgendaResult, TranscriptAnalyzer
from usecases import GenerateWeeklyAgendaUsecase

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)

DISCORD_WEBHOOK_AGENDA_URL = os.environ.get("DISCORD_WEBHOOK_AGENDA_URL")

# Phase 1-A: Discord transcript channel 設定
_DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
_DISCORD_TRANSCRIPT_CHANNEL_ID = os.environ.get("DISCORD_TRANSCRIPT_CHANNEL_ID")
_TRANSCRIPT_FETCH_LIMIT: int = int(os.environ.get("TRANSCRIPT_FETCH_LIMIT", "50"))
# Cloud Run 上は ephemeral filesystem のため、設定しても次回起動時には消える。
# ローカルデバッグ用途のみを想定しており、本番では基本的に未設定とすること。
_DEBUG_JSON_PATH = os.environ.get("DEBUG_JSON_PATH")

# AI ニュース調査: GCP プロジェクト ID (Vertex AI 使用)
# Cloud Run 環境では GOOGLE_CLOUD_PROJECT が自動設定される場合があるが、
# 明示的に設定することを推奨する。
_GCP_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")

AGENDA_MESSAGE = (
    "📅 **今週の収録リマインダー**\n\n"
    "今週のポッドキャスト収録の準備はできていますか?\n\n"
    "収録後は音声ファイルを GCS にアップロードしてください 🎙️"
)


def _fetch_and_reconstruct() -> tuple[AgendaResult | None, list[str], list[NewsCandidate]]:
    """Discord transcript チャンネルからメッセージを取得して Episode を再構築し、ニュースをマッチングする.

    DISCORD_BOT_TOKEN / DISCORD_TRANSCRIPT_CHANNEL_ID が未設定の場合は (None, [], []) を返す。
    news fetch / match が失敗した場合は空リストで継続する (non-fatal)。

    Returns:
        (result, warnings, news_candidates) のタプル。
        result: AgendaResult。Bot Token / Channel ID 未設定時は None。
        warnings: reconstruct_episodes() が収集した警告メッセージ。
        news_candidates: ニュースマッチング結果。取得失敗時は空リスト。
    """
    if not _DISCORD_BOT_TOKEN or not _DISCORD_TRANSCRIPT_CHANNEL_ID:
        logger.info(
            "DISCORD_BOT_TOKEN / DISCORD_TRANSCRIPT_CHANNEL_ID が未設定のため transcript 取得をスキップします。",
        )
        return None, [], []

    fetcher = DiscordFetcher(bot_token=_DISCORD_BOT_TOKEN)
    messages = fetcher.fetch_messages(
        channel_id=_DISCORD_TRANSCRIPT_CHANNEL_ID,
        limit=_TRANSCRIPT_FETCH_LIMIT,
    )
    logger.info("Fetched %d messages from transcript channel.", len(messages))

    analyzer = TranscriptAnalyzer()
    episodes, warnings = analyzer.reconstruct_episodes(messages)
    logger.info(
        "Reconstructed %d episodes (warnings=%d).",
        len(episodes),
        len(warnings),
    )
    for w in warnings:
        logger.warning("  [transcript] %s", w)

    # Phase 1-B: rule-based extraction (no LLM, no external API)
    recurring_themes = analyzer.extract_recurring_themes(episodes)
    action_items = analyzer.extract_action_items(episodes)
    discussion_prompts = analyzer.extract_discussion_prompts(episodes)
    logger.info(
        "Extracted: themes=%d, action_items=%d, prompts=%d.",
        len(recurring_themes),
        len(action_items),
        len(discussion_prompts),
    )

    generated_at = datetime.now(UTC).isoformat()
    result = analyzer.build_agenda(
        episodes=episodes,
        recurring_themes=recurring_themes,
        action_items=action_items,
        discussion_prompts=discussion_prompts,
        generated_at=generated_at,
        analysis_window_size=_TRANSCRIPT_FETCH_LIMIT,
        fetched_message_count=len(messages),
    )

    # Phase 3-C: RSS ニュース取得 → アジェンダトピックとのマッチング
    # fetch / match の失敗は non-fatal: 空リストで継続し Discord 投稿はそのまま行う。
    news_candidates: list[NewsCandidate] = []
    try:
        news_items = NewsFetcher().fetch_all(DEFAULT_RSS_SOURCES)
        logger.info("Fetched %d news items from RSS.", len(news_items))
        news_candidates = match_news_to_agenda(news_items, result)
        logger.info("Matched %d news candidates.", len(news_candidates))
    except Exception:  # noqa: BLE001
        logger.warning("News fetch/match failed. Continuing without news.", exc_info=True)

    return result, warnings, news_candidates


def _export_debug_json(result: AgendaResult, path: str) -> None:
    """AgendaResult を JSON ファイルとして書き出す.

    Args:
        result: 書き出す AgendaResult。
        path: 出力先ファイルパス。親ディレクトリが存在しない場合は自動作成する。
    """
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Debug JSON written to %s", path)


def send_weekly_agenda() -> None:
    """毎週水曜日に Discord へアジェンダを投稿する."""
    # webhook URL は mandatory。未設定は設定ミスとして即 fail させる。
    if not DISCORD_WEBHOOK_AGENDA_URL:
        msg = "DISCORD_WEBHOOK_AGENDA_URL is not set."
        raise RuntimeError(msg)

    logger.info("DISCORD_WEBHOOK_AGENDA_URL configured: %s", bool(DISCORD_WEBHOOK_AGENDA_URL))

    notifier = Notifier(discord_webhook_url=DISCORD_WEBHOOK_AGENDA_URL)
    usecase = GenerateWeeklyAgendaUsecase(notifier=notifier, logger=logger)

    def build_agenda_message() -> str:
        """Build agenda message from transcript/news analysis when available."""
        result, _warnings, news_candidates = _fetch_and_reconstruct()
        if result is None:
            return AGENDA_MESSAGE

        episode_count = len(result.metadata.source_episode_numbers)
        logger.info(
            "AgendaResult: episodes=%d, schema_version=%s",
            episode_count,
            result.schema_version,
        )
        if _DEBUG_JSON_PATH:
            _export_debug_json(result, _DEBUG_JSON_PATH)

        ai_news_section: str | None = None
        if _GCP_PROJECT_ID and result.recurring_themes:
            try:
                researcher = AINewsResearcher(project_id=_GCP_PROJECT_ID)
                ai_news_section = researcher.research(result.recurring_themes)
                logger.info("AI news research succeeded (%d chars).", len(ai_news_section))
            except Exception:  # noqa: BLE001
                logger.warning("AI news research failed. Falling back to RSS candidates.", exc_info=True)
        else:
            logger.info(
                "AI news research skipped (GCP_PROJECT_ID=%s, themes=%d).",
                bool(_GCP_PROJECT_ID),
                len(result.recurring_themes),
            )

        return format_agenda_message(
            result,
            ai_news_section=ai_news_section,
            news_candidates=news_candidates if not ai_news_section else None,
        )

    success = usecase.run(
        message_builder=build_agenda_message,
        fallback_message=AGENDA_MESSAGE,
        username="Podcast Scheduler",
    )
    if not success:
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    send_weekly_agenda()


if __name__ == "__main__":
    main()
