"""Weekly agenda notification entrypoint for Discord."""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from infrastructure.discord_fetcher import DiscordFetcher
from infrastructure.notifier import Notifier
from services.agenda_formatter import format_agenda_message
from services.firestore_manager import FirestoreManager
from services.news_fetcher import DEFAULT_RSS_SOURCES, NewsFetcher
from services.news_relevance import match_news_to_agenda
from services.news_researcher import AINewsResearcher
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

    project_id: str | None
    podcast_id: str | None
    discord_webhook_agenda_url: str | None
    discord_bot_token: str | None
    discord_transcript_channel_id: str | None
    transcript_fetch_limit: int
    debug_json_path: str | None
    gcp_project_id: str | None


def _load_agenda_env() -> AgendaEnvConfig:
    """Load environment variables for weekly agenda job."""
    return AgendaEnvConfig(
        project_id=os.environ.get("PROJECT_ID"),
        podcast_id=os.environ.get("PODCAST_ID"),
        discord_webhook_agenda_url=os.environ.get("DISCORD_WEBHOOK_AGENDA_URL"),
        discord_bot_token=os.environ.get("DISCORD_BOT_TOKEN"),
        discord_transcript_channel_id=os.environ.get("DISCORD_TRANSCRIPT_CHANNEL_ID"),
        transcript_fetch_limit=int(os.environ.get("TRANSCRIPT_FETCH_LIMIT", "50")),
        debug_json_path=os.environ.get("DEBUG_JSON_PATH"),
        gcp_project_id=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    )


def _build_target_period_string(generated_at: str) -> str:
    """Build a readable ISO-week period string."""
    normalized = generated_at.removesuffix("Z") + ("+00:00" if generated_at.endswith("Z") else "")
    generated_dt = datetime.fromisoformat(normalized)
    iso_year, iso_week, _ = generated_dt.isocalendar()
    monday = generated_dt.date() - timedelta(days=generated_dt.weekday())
    sunday = monday + timedelta(days=6)
    return f"{iso_year}年 第{iso_week}週 ({monday:%m/%d} - {sunday:%m/%d})"


def _build_related_news_payload(news_candidates: list[NewsCandidate]) -> list[dict[str, object]]:
    """Convert news candidates into Firestore payloads."""
    return [
        {
            "title": candidate.news_item.title,
            "url": candidate.news_item.url,
            "summary": candidate.news_item.summary or "",
            "source_reason": f"{candidate.topic_match.display_name} との関連度 {candidate.score:.2f}",
        }
        for candidate in news_candidates[:3]
    ]


def _build_suggested_topics_payload(result: AgendaResult) -> list[dict[str, object]]:
    """Convert agenda output into suggested topics."""
    suggested_topics: list[dict[str, object]] = []
    for theme in result.recurring_themes[:3]:
        related_past_episodes = sorted({evidence.source_episode for evidence in theme.evidence})
        suggested_points = [evidence.text for evidence in theme.evidence[:3]]
        if not suggested_points and related_past_episodes:
            suggested_points = [f"関連エピソード: {', '.join(map(str, related_past_episodes))}"]
        suggested_topics.append(
            {
                "title": theme.display_name,
                "description": f"{theme.display_name} について次回深掘りする。",
                "suggested_points": suggested_points,
                "related_past_episodes": related_past_episodes,
            },
        )
    return suggested_topics


def _save_topic_proposal(
    *,
    firestore_manager: FirestoreManager,
    podcast_id: str,
    result: AgendaResult,
    news_candidates: list[NewsCandidate],
) -> str:
    """Persist a topic proposal derived from agenda analysis."""
    return firestore_manager.create_topic_proposal(
        podcast_id=podcast_id,
        proposal_id=None,
        target_period_string=_build_target_period_string(result.metadata.generated_at),
        generated_at=result.metadata.generated_at,
        related_news=_build_related_news_payload(news_candidates),
        suggested_topics=_build_suggested_topics_payload(result),
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
    firestore_manager = FirestoreManager(project_id=cfg.project_id) if cfg.project_id and cfg.podcast_id else None

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

        if firestore_manager is not None and cfg.podcast_id is not None:
            proposal_id = _save_topic_proposal(
                firestore_manager=firestore_manager,
                podcast_id=cfg.podcast_id,
                result=result,
                news_candidates=news_candidates,
            )
            logger.info("Saved topic proposal to Firestore: %s", proposal_id)

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
