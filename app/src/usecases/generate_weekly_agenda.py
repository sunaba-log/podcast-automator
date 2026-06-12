"""Use case for generating and notifying weekly agenda."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import logging

    from domain.interfaces import NotificationGateway


class AgendaMessageBuilder(Protocol):
    """Builds a weekly agenda notification message."""

    def __call__(self) -> str:
        """Return a message body for weekly notification."""


class GenerateWeeklyAgendaUsecase:
    """Coordinates weekly agenda message generation and notification."""

    def __init__(self, *, notifier: NotificationGateway, logger: logging.Logger) -> None:
        """Initialize use case dependencies."""
        self._notifier = notifier
        self._logger = logger

    def run(
        self,
        *,
        message_builder: AgendaMessageBuilder,
        fallback_message: str,
        username: str = "Podcast Scheduler",
    ) -> bool:
        """Build and send weekly agenda message with fallback on builder failure."""
        self._logger.info("## Weekly Agenda Job Start ##")

        message = fallback_message
        try:
            message = message_builder()
        except Exception:  # noqa: BLE001
            self._logger.exception("Transcript analysis failed. Falling back to fixed-message notification.")

        success = self._notifier.send_discord_message(message=message, username=username)
        if success:
            self._logger.info("Weekly agenda sent to Discord successfully.")
            return True

        self._logger.error("Failed to send weekly agenda to Discord.")
        return False
