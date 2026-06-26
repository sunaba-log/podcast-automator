from __future__ import annotations

# ruff: noqa: ARG002, ARG005
import logging
from dataclasses import dataclass

import pytest

from domain.models import SnsPromotionContent, SnsPromotionsResponse, Summary
from usecases.process_podcast_workflow import (
    ProcessPodcastWorkflow,
    ProcessPodcastWorkflowInput,
    _duration_to_seconds,
)


class _TranscriptProvider:
    def __init__(self, *, transcript: str = "transcript") -> None:
        self.transcript = transcript

    def generate_transcript(self, source_uri: str, model_id: str | None = None) -> str:
        return self.transcript

    def summarize_transcript(
        self,
        transcript: str,
        prompt: str | None = None,
        model_id: str | None = None,
    ) -> Summary:
        return Summary(title="Generated title", description="Generated description")

    def generate_sns_promotions(
        self,
        summary_description: str,
        num_promotions: int = 3,
        model_id: str | None = None,
    ) -> SnsPromotionsResponse:
        return SnsPromotionsResponse(
            promotions=[
                SnsPromotionContent(message=f"Promotion {index}", hashtags=[f"#Tag{index}"])
                for index in range(1, num_promotions + 1)
            ]
        )


class _ObjectStorage:
    def __init__(self) -> None:
        self.uploads: list[str] = []

    def download_file(self, remote_key: str) -> bytes:
        return b"<rss />"

    def upload_file(self, file_content: bytes, remote_key: str, content_type: str, *, public: bool = True) -> None:
        self.uploads.append(remote_key)

    def generate_public_url(self, remote_key: str, custom_domain: str | None = None) -> str:
        return f"https://{custom_domain}/{remote_key}"


class _BlobSource:
    def download_blob_as_bytes(self, bucket_name: str, blob_name: str) -> bytes:
        return b"audio"


class _Notifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send_discord_message(self, message: str) -> bool:
        self.messages.append(message)
        return True


class _RssManager:
    def __init__(self, *, rss_xml: str) -> None:
        self.episodes: list[dict[str, object]] = []

    def get_total_episodes(self) -> int:
        return 3

    def add_episode(self, new_episode_data: dict) -> None:
        self.episodes.append(new_episode_data)

    def get_rss_xml(self) -> str:
        return "<rss />"


@dataclass
class _EpisodeRepository:
    processing: tuple[int, int, str] | None = None
    completed: dict[str, object] | None = None
    failed: tuple[int, int, str] | None = None

    def mark_processing(self, *, podcast_id: int, episode_id: int, source_audio_path: str) -> None:
        self.processing = (podcast_id, episode_id, source_audio_path)

    def mark_completed(self, **values: object) -> None:
        self.completed = values

    def mark_failed(self, *, podcast_id: int, episode_id: int, error_message: str) -> None:
        self.failed = (podcast_id, episode_id, error_message)


class _FirestoreManager:
    def __init__(self) -> None:
        self.episode_content: dict[str, object] | None = None
        self.transcript: dict[str, object] | None = None
        self.promotions: list[dict[str, object]] = []

    def save_episode_content(self, **values: object) -> str:
        self.episode_content = values
        return str(values["episode_id"])

    def save_transcript_chunks(self, **values: object) -> list[str]:
        self.transcript = values
        return ["chunk_0001"]

    def create_sns_promotion(self, **values: object) -> str:
        self.promotions.append(values)
        return f"promotion-{len(self.promotions)}"


def _request(object_path: str = "podcasts/1/episodes/42/source/recording.mp3") -> ProcessPodcastWorkflowInput:
    return ProcessPodcastWorkflowInput(
        project_id="project",
        sns_schedule_offset_hours=1,
        gcs_bucket="bucket",
        gcs_trigger_object_name=object_path,
        r2_bucket="r2",
        r2_key_prefix="dev",
        ai_model_id="model",
        r2_custom_domain="podcast.example.com",
        sns_promotion_count=2,
    )


def _workflow(
    *,
    repository: _EpisodeRepository,
    firestore: _FirestoreManager,
    transcript_provider: _TranscriptProvider | None = None,
) -> ProcessPodcastWorkflow:
    return ProcessPodcastWorkflow(
        transcript_provider=transcript_provider or _TranscriptProvider(),
        object_storage=_ObjectStorage(),
        blob_source=_BlobSource(),
        notifier=_Notifier(),
        rss_manager_factory=_RssManager,
        audio_converter=lambda audio, suffix: b"mp3",
        audio_info_reader=lambda file_buffer, audio_format: [3, "01:02:03"],
        firestore_manager=firestore,
        episode_repository=repository,
        logger=logging.getLogger("test-workflow"),
    )


def test_workflow_uses_object_path_ids_for_cloud_sql_and_firestore() -> None:
    repository = _EpisodeRepository()
    firestore = _FirestoreManager()

    _workflow(repository=repository, firestore=firestore).run(_request())

    assert repository.processing == (1, 42, "podcasts/1/episodes/42/source/recording.mp3")
    assert repository.completed == {
        "podcast_id": 1,
        "episode_id": 42,
        "title": "#4 Generated title",
        "description": "Generated description",
        "audio_url": "https://podcast.example.com/dev/ep/4/audio.mp3",
        "duration_seconds": 3723,
    }
    assert repository.failed is None
    assert firestore.episode_content is not None
    assert firestore.episode_content["podcast_id"] == "1"
    assert firestore.episode_content["episode_id"] == "42"
    assert firestore.transcript is not None
    assert firestore.transcript["episode_id"] == "42"
    assert len(firestore.promotions) == 2
    assert firestore.promotions[0]["episode_id"] == "42"
    assert firestore.promotions[0]["podcast_id"] == "1"
    assert firestore.promotions[0]["message"] == "Promotion 1"
    assert firestore.promotions[1]["episode_id"] == "42"
    assert firestore.promotions[1]["message"] == "Promotion 2"


def test_workflow_marks_episode_failed_and_reraises() -> None:
    repository = _EpisodeRepository()
    firestore = _FirestoreManager()
    workflow = _workflow(
        repository=repository,
        firestore=firestore,
        transcript_provider=_TranscriptProvider(transcript=""),
    )

    with pytest.raises(ValueError, match="Failed to make transcript"):
        workflow.run(_request())

    assert repository.failed == (1, 42, "Failed to make transcript.")
    assert repository.completed is None


def test_workflow_rejects_invalid_path_before_database_update() -> None:
    repository = _EpisodeRepository()

    with pytest.raises(ValueError, match="GCS object path must match"):
        _workflow(repository=repository, firestore=_FirestoreManager()).run(_request("recording.mp3"))

    assert repository.processing is None
    assert repository.failed is None


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        ("01:02:03", 3723),
        ("00:00:00", 0),
        ("1:60:00", None),
        ("invalid", None),
    ],
)
def test_duration_to_seconds(duration: str, expected: int | None) -> None:
    assert _duration_to_seconds(duration) == expected
