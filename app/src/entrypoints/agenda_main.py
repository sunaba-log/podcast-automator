"""Weekly agenda notification entrypoint for Discord."""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from services.agenda_formatter import format_agenda_message
from services.discord_fetcher import DiscordFetcher
from services.news_fetcher import DEFAULT_RSS_SOURCES, NewsFetcher
from services.news_relevance import match_news_to_agenda
from services.news_researcher import AINewsResearcher
from services.notifier import Notifier
from services.transcript_analyzer import AgendaResult, TranscriptAnalyzer
from usecases import GenerateWeeklyAgendaUsecase

if TYPE_CHECKING:
    from services.news_relevance import NewsCandidate


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)

AGENDA_MESSAGE = (
    "📅 **今週の収録リマインダー**\n\n"
    "今週のポッドキャスト収録の準備はできていますか?\n\n"
    "収録後は音声ファイルを GCS にアップロードしてください 🎙️"
)


@dataclass(frozen=True)
class AgendaEnvConfig:
    """Resolved environment variables for weekly agenda job."""

    discord_webhook_agenda_url: str | None
    discord_bot_token: str | None
    discord_transcript_channel_id: str | None
    transcript_fetch_limit: int
    debug_json_path: str | None
    gcp_project_id: str | None


def _load_agenda_env() -> AgendaEnvConfig:
    """Load environment variables for weekly agenda job."""
    return AgendaEnvConfig(
        discord_webhook_agenda_url=os.environ.get("DISCORD_WEBHOOK_AGENDA_URL"),
        discord_bot_token=os.environ.get("DISCORD_BOT_TOKEN"),
        discord_transcript_channel_id=os.environ.get("DISCORD_TRANSCRIPT_CHANNEL_ID"),
        transcript_fetch_limit=int(os.environ.get("TRANSCRIPT_FETCH_LIMIT", "50")),
        debug_json_path=os.environ.get("DEBUG_JSON_PATH"),
        gcp_project_id=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    )


def _fetch_and_reconstruct(cfg: AgendaEnvConfig) -> tuple[AgendaResult | None, list[str], list[NewsCandidate]]:
    """Fetch Discord transcripts, reconstruct episodes, and match RSS news."""
    if not cfg.discord_bot_token or not cfg.discord_transcript_channel_id:
        logger.info(
            "DISCORD_BOT_TOKEN / DISCORD_TRANSCRIPT_CHANNEL_ID が未設定のため transcript 取得をスキップします。",
        )
        return None, [], []

    fetcher = DiscordFetcher(bot_token=cfg.discord_bot_token)
    messages = fetcher.fetch_messages(
        channel_id=cfg.discord_transcript_channel_id,
        limit=cfg.transcript_fetch_limit,
    )
    logger.info("Fetched %d messages from transcript channel.", len(messages))

    analyzer = TranscriptAnalyzer()
    episodes, warnings = analyzer.reconstruct_episodes(messages)
    logger.info(
        "Reconstructed %d episodes (warnings=%d).",
        len(episodes),
        len(warnings),
    )
    for warning in warnings:
        logger.warning("  [transcript] %s", warning)

    recurring_themes = analyzer.extract_recurring_themes(episodes)
    action_items = analyzer.extract_action_items(episodes)
    discussion_prompts = analyzer.extract_discussion_prompts(episodes)
    logger.info(
        "Extracted: themes=%d, action_items=%d, prompts=%d.",
        len(recurring_themes),
        len(action_items),
        len(discussion_prompts),
    )

    result = analyzer.build_agenda(
        episodes=episodes,
        recurring_themes=recurring_themes,
        action_items=action_items,
        discussion_prompts=discussion_prompts,
        generated_at=datetime.now(UTC).isoformat(),
        analysis_window_size=cfg.transcript_fetch_limit,
        fetched_message_count=len(messages),
    )

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
    """Write AgendaResult as JSON for local debugging."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Debug JSON written to %s", path)


def send_weekly_agenda() -> None:
    """毎週水曜日に Discord へアジェンダを投稿する."""
    cfg = _load_agenda_env()

    if not cfg.discord_webhook_agenda_url:
        raise RuntimeError("DISCORD_WEBHOOK_AGENDA_URL is not set.")
    logger.info("DISCORD_WEBHOOK_AGENDA_URL configured: %s", bool(cfg.discord_webhook_agenda_url))

    notifier = Notifier(discord_webhook_url=cfg.discord_webhook_agenda_url)
    usecase = GenerateWeeklyAgendaUsecase(notifier=notifier, logger=logger)

    def build_agenda_message() -> str:
        result, _warnings, news_candidates = _fetch_and_reconstruct(cfg)
        if result is None:
            return AGENDA_MESSAGE

        episode_count = len(result.metadata.source_episode_numbers)
        logger.info(
            "AgendaResult: episodes=%d, schema_version=%s",
            episode_count,
            result.schema_version,
        )
        if cfg.debug_json_path:
            _export_debug_json(result, cfg.debug_json_path)

        ai_news_section: str | None = None
        if cfg.gcp_project_id and result.recurring_themes:
            try:
                researcher = AINewsResearcher(project_id=cfg.gcp_project_id)
                ai_news_section = researcher.research(result.recurring_themes)
                logger.info("AI news research succeeded (%d chars).", len(ai_news_section))
            except Exception:  # noqa: BLE001
                logger.warning("AI news research failed. Falling back to RSS candidates.", exc_info=True)
        else:
            logger.info(
                "AI news research skipped (GCP_PROJECT_ID=%s, themes=%d).",
                bool(cfg.gcp_project_id),
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
