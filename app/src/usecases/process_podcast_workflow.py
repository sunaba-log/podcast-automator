"""Use case for end-to-end podcast processing workflow."""

from __future__ import annotations

import io
import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from domain.models import EpisodeObjectReference

if TYPE_CHECKING:
    import logging

    from domain.interfaces import BlobSource, EpisodeRepository, NotificationGateway, ObjectStorage, TranscriptProvider
    from services.firestore_manager import FirestoreManager


class PodcastFeedManager(Protocol):
    """Minimal interface required to update the podcast RSS feed."""

    def get_total_episodes(self) -> int:
        """Return current episode count from RSS feed."""

    def add_episode(self, new_episode_data: dict) -> None:  # type: ignore[type-arg]
        """Append a new episode item to RSS feed."""

    def get_rss_xml(self) -> str:
        """Return serialized RSS XML."""


class PodcastFeedManagerFactory(Protocol):
    """Factory for RSS manager creation from source XML."""

    def __call__(self, *, rss_xml: str) -> PodcastFeedManager:
        """Build an RSS manager instance from XML string."""


class AudioConverterGateway(Protocol):
    """Converts source audio bytes into MP3 bytes."""

    def __call__(self, audio_bytes: bytes, source_suffix: str) -> bytes:
        """Convert source audio bytes to MP3 bytes."""


class AudioInfoReader(Protocol):
    """Reads file size and duration information from audio bytes."""

    def __call__(self, file_buffer: io.BytesIO, audio_format: str) -> list:
        """Return [size_bytes, duration_str]."""


@dataclass(frozen=True)
class ProcessPodcastWorkflowInput:
    """Input parameters for podcast processing workflow."""

    project_id: str
    sns_schedule_offset_hours: int
    gcs_bucket: str
    gcs_trigger_object_name: str
    r2_bucket: str
    r2_key_prefix: str
    ai_model_id: str
    r2_custom_domain: str
    sns_promotion_count: int = 3


class ProcessPodcastWorkflow:
    """Coordinates podcast processing from transcript generation to RSS update."""

    def __init__(
        self,
        *,
        transcript_provider: TranscriptProvider,
        object_storage: ObjectStorage,
        blob_source: BlobSource,
        notifier: NotificationGateway,
        rss_manager_factory: PodcastFeedManagerFactory,
        audio_converter: AudioConverterGateway,
        audio_info_reader: AudioInfoReader,
        firestore_manager: FirestoreManager | None,
        episode_repository: EpisodeRepository,
        logger: logging.Logger,
    ) -> None:
        """Initialize use case dependencies."""
        self._transcript_provider = transcript_provider
        self._object_storage = object_storage
        self._blob_source = blob_source
        self._notifier = notifier
        self._rss_manager_factory = rss_manager_factory
        self._audio_converter = audio_converter
        self._audio_info_reader = audio_info_reader
        self._firestore_manager = firestore_manager
        self._episode_repository = episode_repository
        self._logger = logger

    def run(self, request: ProcessPodcastWorkflowInput) -> None:
        """Execute podcast workflow and emit notifications for success/failure."""
        self._logger.info("GCS Bucket: %s, File: %s", request.gcs_bucket, request.gcs_trigger_object_name)
        self._logger.info("DEBUG: Processing GCS Object Path: %s", request.gcs_trigger_object_name)
        episode_ref = EpisodeObjectReference.parse(request.gcs_trigger_object_name)
        gcs_path = Path(request.gcs_trigger_object_name)
        audio_source_mime_type = mimetypes.guess_type(request.gcs_trigger_object_name)[0] or "audio/x-m4a"
        self._logger.info("Detected mime type: %s", audio_source_mime_type)

        try:
            self._episode_repository.mark_processing(
                podcast_id=episode_ref.podcast_id,
                episode_id=episode_ref.episode_id,
                source_audio_path=episode_ref.object_path,
            )
            rss_feed_bytes = self._object_storage.download_file(f"{request.r2_key_prefix}/feed.xml")
            rss_manager = self._rss_manager_factory(rss_xml=rss_feed_bytes.decode("utf-8"))
            latest_episode_number = rss_manager.get_total_episodes() + 1
            self._logger.info("Latest Episode Number: %s", latest_episode_number)

            self._logger.info("\n## Step1: Running AI Analysis... ##")
            transcript = self._transcript_provider.generate_transcript(
                f"gs://{request.gcs_bucket}/{request.gcs_trigger_object_name}", model_id=request.ai_model_id
            )
            self._notifier.send_discord_message(message=f"#{latest_episode_number} Meeting Transcript:\n\n{transcript}")
            if not transcript:
                raise ValueError("Failed to make transcript.")

            summary = self._transcript_provider.summarize_transcript(transcript, model_id=request.ai_model_id)
            self._logger.info("Generated Summary: %s", summary)
            summary.title = f"#{latest_episode_number} {summary.title}"

            self._notifier.send_discord_message(
                message=f"New Podcast Processed:\nTitle: {summary.title}\nDescription: {summary.description}"
            )

            self._logger.info("\n## Step2: Converting to MP3 and Uploading to Cloudflare R2... ##")
            audio_upload_mime_type = "audio/mpeg"
            original_audio_bytes = self._blob_source.download_blob_as_bytes(
                request.gcs_bucket, request.gcs_trigger_object_name
            )
            mp3_bytes = self._audio_converter(original_audio_bytes, gcs_path.suffix)

            try:
                file_size_bytes, duration_str = self._audio_info_reader(
                    file_buffer=io.BytesIO(mp3_bytes),
                    audio_format="mp3",
                )
            except Exception:  # noqa: BLE001
                self._logger.warning("Failed to get audio info")
                file_size_bytes, duration_str = len(mp3_bytes), "00:00:00"

            r2_remote_key = f"{request.r2_key_prefix}/ep/{latest_episode_number}/audio.mp3"
            self._object_storage.upload_file(
                file_content=mp3_bytes,
                remote_key=r2_remote_key,
                content_type=audio_upload_mime_type,
                public=True,
            )
            public_url = self._object_storage.generate_public_url(
                remote_key=r2_remote_key,
                custom_domain=request.r2_custom_domain,
            )
            self._logger.info(
                "Uploaded audio to R2: %s, Size: %s bytes, Duration: %s",
                public_url,
                file_size_bytes,
                duration_str,
            )

            self._logger.info("\n## Updating RSS Feed... ##")
            new_episode_data = {
                "title": summary.title,
                "description": summary.description,
                "audio_url": public_url,
                "file_size": file_size_bytes,
                "itunes_duration": duration_str,
                "creator": "sunabalog",
                "mime_type": audio_upload_mime_type,
                "itunes_summary": summary.description,
                "itunes_explicit": "no",
                "itunes_season": 1,
                "itunes_episode_number": latest_episode_number,
                "itunes_episode_type": "full",
            }
            rss_manager.add_episode(new_episode_data)
            self._object_storage.upload_file(
                file_content=rss_manager.get_rss_xml().encode("utf-8"),
                remote_key=f"{request.r2_key_prefix}/feed.xml",
                content_type="application/rss+xml; charset=utf-8",
                public=True,
            )

            if self._firestore_manager is not None:
                generated_at = datetime.now(UTC).isoformat()
                transcript_summary = summary.description
                ai_generated_meta = {
                    "title": summary.title,
                    "description": summary.description,
                    "prompt_version": "v1",
                    "generated_at": generated_at,
                }
                show_notes_summary = {
                    "overview": summary.description,
                    "topics": [
                        {
                            "time": "00:00",
                            "title": summary.title,
                        },
                    ],
                }
                audio_metadata = {
                    "file_size_bytes": file_size_bytes,
                    "duration_str": duration_str,
                    "audio_url": public_url,
                    "mime_type": audio_upload_mime_type,
                }
                self._firestore_manager.save_episode_content(
                    podcast_id=episode_ref.podcast_id,
                    episode_id=episode_ref.episode_id,
                    episode_number=latest_episode_number,
                    updated_at=generated_at,
                    transcript_summary=transcript_summary,
                    ai_generated_meta=ai_generated_meta,
                    show_notes_summary=show_notes_summary,
                    audio_metadata=audio_metadata,
                )
                self._firestore_manager.save_transcript_chunks(
                    podcast_id=episode_ref.podcast_id,
                    episode_id=episode_ref.episode_id,
                    transcript=transcript,
                )
                sns_promotions = self._transcript_provider.generate_sns_promotions(
                    summary_description=summary.description,
                    num_promotions=request.sns_promotion_count,
                    model_id=request.ai_model_id,
                )
                for i, promo in enumerate(sns_promotions.promotions):
                    promo_scheduled_time = (
                        datetime.now(UTC) + timedelta(hours=request.sns_schedule_offset_hours) + timedelta(days=i)
                    ).isoformat()
                    self._firestore_manager.create_sns_promotion(
                        podcast_id=episode_ref.podcast_id,
                        episode_id=episode_ref.episode_id,
                        promotion_id=None,
                        generated_at=generated_at,
                        scheduled_time=promo_scheduled_time,
                        episode_number=latest_episode_number,
                        message=promo.message,
                        platform_urls={"apple": "", "spotify": "", "amazon": ""},
                        hashtags=promo.hashtags,
                    )

            self._episode_repository.mark_completed(
                podcast_id=episode_ref.podcast_id,
                episode_id=episode_ref.episode_id,
                title=summary.title,
                description=summary.description,
                audio_url=public_url,
                duration_seconds=_duration_to_seconds(duration_str),
            )
            self._logger.info("\n## Notifying Discord (Success)... ##")
            self._notifier.send_discord_message(
                message=f"Podcast Episode Published Successfully:\nTitle: {summary.title}\nURL: {public_url}"
            )
        except Exception as err:
            self._logger.exception("Error occurred during podcast processing:")
            try:
                self._episode_repository.mark_failed(
                    podcast_id=episode_ref.podcast_id,
                    episode_id=episode_ref.episode_id,
                    error_message=str(err),
                )
            except Exception:  # noqa: BLE001
                self._logger.exception("Failed to persist episode failure state")
            self._notifier.send_discord_message(message=f"Podcast Processing Failed:\nError: {err}")
            raise


def _duration_to_seconds(duration: str) -> int | None:
    """Convert HH:MM:SS duration text to seconds."""
    duration_part_count = 3
    parts = duration.split(":")
    if len(parts) != duration_part_count:
        return None
    try:
        hours, minutes, seconds = (int(part) for part in parts)
    except ValueError:
        return None
    if hours < 0 or minutes not in range(60) or seconds not in range(60):
        return None
    return hours * 3600 + minutes * 60 + seconds
