"""Use case for automatically posting SNS promotion posts to X."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from domain.models.sns_post import SnsPost

if TYPE_CHECKING:
    from infrastructure.x_api import XClient
    from services.firestore_manager import FirestoreManager

logger = logging.getLogger(__name__)


class AutoPostSnsUsecase:
    """Retrieves due SNS promotions from Firestore and posts the oldest one to X."""

    def __init__(
        self,
        *,
        firestore_manager: FirestoreManager,
        x_client: XClient,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize use case."""
        self._firestore_manager = firestore_manager
        self._x_client = x_client
        self._logger = logger or logging.getLogger(__name__)

    def run(self) -> None:
        """Execute the auto-posting process."""
        self._logger.info("Auto-posting process started.")

        try:
            pending_promotions = self._firestore_manager.get_pending_sns_promotions()
        except Exception:
            self._logger.exception("Failed to fetch pending SNS promotions from Firestore.")
            raise

        if not pending_promotions:
            self._logger.info("No pending SNS promotions found.")
            return

        now = datetime.now(UTC)
        due_promotions = []
        for promo in pending_promotions:
            sched_time_str = promo.get("scheduled_time")
            if not sched_time_str:
                continue
            try:
                # Parse scheduled time in ISO 8601 format
                sched_time = datetime.fromisoformat(sched_time_str)
            except ValueError:
                self._logger.warning("Invalid scheduled_time format: %s", sched_time_str)
                continue

            if sched_time <= now:
                due_promotions.append((sched_time, promo))

        if not due_promotions:
            self._logger.info("No SNS promotions are due for posting.")
            return

        # Sort by scheduled time, and pick the oldest one.
        due_promotions.sort(key=lambda item: item[0])
        _, oldest_promo = due_promotions[0]

        reference_path = oldest_promo["reference_path"]
        doc_id = oldest_promo["doc_id"]
        self._logger.info("Selected promotion to post. doc_id: %s, path: %s", doc_id, reference_path)

        message = oldest_promo.get("message", "").strip()
        if not message:
            self._logger.warning("Empty message, skipping. doc_id: %s", doc_id)
            return

        # Resolve episode number from the nested 'episode' structure
        episode_number = oldest_promo.get("episode", {}).get("number")

        post = SnsPost(
            message=message,
            platform_urls=oldest_promo.get("platform_urls"),
            episode_number=episode_number,
            hashtags=oldest_promo.get("hashtags"),
        )
        post_text = post.generate_text()

        self._logger.info("Attempting to post thread. doc_id: %s, text_length: %s", doc_id, len(post_text))
        try:
            success = self._x_client.post_thread(post_text)
            if success:
                self._firestore_manager.update_sns_promotion_status(reference_path, "posted")
                self._logger.info("SNS promotion posted successfully. doc_id: %s", doc_id)
            else:
                self._firestore_manager.update_sns_promotion_status(reference_path, "failed")
                self._logger.error("SNS promotion posting failed. doc_id: %s", doc_id)
        except Exception:
            self._logger.exception("Unexpected error while posting SNS promotion. doc_id: %s", doc_id)
            try:
                self._firestore_manager.update_sns_promotion_status(reference_path, "failed")
            except Exception:
                self._logger.exception("Failed to update status to failed in Firestore. doc_id: %s", doc_id)
            raise
