"""Use case for generating and notifying weekly agenda."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import logging

    from domain.interfaces import NotificationGateway
    from services.firestore_manager import FirestoreManager
    from services.news_relevance import NewsCandidate
    from services.transcript_analyzer import AgendaResult


class AgendaMessageBuilder(Protocol):
    """Builds a weekly agenda notification message."""

    def __call__(self) -> tuple[str, AgendaResult | None, list[NewsCandidate]]:
        """Return a message body and components for weekly notification."""


class GenerateWeeklyAgendaUsecase:
    """Coordinates weekly agenda message generation and notification."""

    def __init__(
        self,
        *,
        notifier: NotificationGateway,
        firestore_manager: FirestoreManager | None = None,
        logger: logging.Logger,
    ) -> None:
        """Initialize use case dependencies."""
        self._notifier = notifier
        self._firestore_manager = firestore_manager
        self._logger = logger

    def run(
        self,
        *,
        message_builder: AgendaMessageBuilder,
        fallback_message: str,
        podcast_id: str | None = None,
        username: str = "Podcast Scheduler",
    ) -> bool:
        """Build and send weekly agenda message with fallback on builder failure."""
        self._logger.info("## Weekly Agenda Job Start ##")

        message = fallback_message
        try:
            message, result, news_candidates = message_builder()

            # Save generated topic proposal to Firestore if available
            if self._firestore_manager is not None and podcast_id is not None and result is not None:
                proposal_id = self._save_topic_proposal(
                    podcast_id=podcast_id,
                    result=result,
                    news_candidates=news_candidates,
                )
                self._logger.info("Saved topic proposal to Firestore: %s", proposal_id)
        except Exception:  # noqa: BLE001
            self._logger.exception("Transcript analysis failed. Falling back to fixed-message notification.")

        success = self._notifier.send_discord_message(message=message, username=username)
        if success:
            self._logger.info("Weekly agenda sent to Discord successfully.")
            return True

        self._logger.error("Failed to send weekly agenda to Discord.")
        return False

    def _build_target_period_string(self, generated_at: str) -> str:
        """Build a readable ISO-week period string."""
        normalized = generated_at.removesuffix("Z") + ("+00:00" if generated_at.endswith("Z") else "")
        generated_dt = datetime.fromisoformat(normalized)
        iso_year, iso_week, _ = generated_dt.isocalendar()
        monday = generated_dt.date() - timedelta(days=generated_dt.weekday())
        sunday = monday + timedelta(days=6)
        return f"{iso_year}年 第{iso_week}週 ({monday:%m/%d} - {sunday:%m/%d})"

    def _build_related_news_payload(self, news_candidates: list[NewsCandidate]) -> list[dict[str, object]]:
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

    def _build_suggested_topics_payload(self, result: AgendaResult) -> list[dict[str, object]]:
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
        self,
        *,
        podcast_id: str,
        result: AgendaResult,
        news_candidates: list[NewsCandidate],
    ) -> str:
        """Persist a topic proposal derived from agenda analysis."""
        if self._firestore_manager is None:
            raise RuntimeError("FirestoreManager is not initialized.")
        return self._firestore_manager.create_topic_proposal(
            podcast_id=podcast_id,
            proposal_id=None,
            target_period_string=self._build_target_period_string(result.metadata.generated_at),
            generated_at=result.metadata.generated_at,
            related_news=self._build_related_news_payload(news_candidates),
            suggested_topics=self._build_suggested_topics_payload(result),
        )
