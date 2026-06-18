from __future__ import annotations

from dataclasses import dataclass

from services.firestore_manager import FirestoreManager


@dataclass
class _FakeDocRef:
    path: str

    def __post_init__(self) -> None:
        self.set_calls: list[tuple[dict[str, object], bool]] = []
        self._collections: dict[str, _FakeCollectionRef] = {}

    @property
    def id(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    def set(self, data: dict[str, object], merge: bool = False) -> None:  # noqa: FBT001, FBT002
        self.set_calls.append((data, merge))

    def collection(self, name: str) -> _FakeCollectionRef:
        return self._collections.setdefault(name, _FakeCollectionRef(f"{self.path}/{name}"))


@dataclass
class _FakeCollectionRef:
    path: str

    def __post_init__(self) -> None:
        self.documents: dict[str, _FakeDocRef] = {}

    def document(self, doc_id: str) -> _FakeDocRef:
        return self.documents.setdefault(doc_id, _FakeDocRef(f"{self.path}/{doc_id}"))


class _FakeBatch:
    def __init__(self) -> None:
        self.operations: list[tuple[str, dict[str, object]]] = []

    def set(self, doc_ref: _FakeDocRef, data: dict[str, object]) -> None:
        self.operations.append((doc_ref.path, data))

    def commit(self) -> None:
        return None


class _FakeClient:
    def __init__(self) -> None:
        self.collections: dict[str, _FakeCollectionRef] = {}
        self.batch_instance = _FakeBatch()

    def collection(self, name: str) -> _FakeCollectionRef:
        return self.collections.setdefault(name, _FakeCollectionRef(name))

    def batch(self) -> _FakeBatch:
        return self.batch_instance


def test_save_episode_content_writes_expected_document() -> None:
    client = _FakeClient()
    manager = FirestoreManager(project_id="demo", client=client)

    manager.save_episode_content(
        podcast_id="podcast-1",
        episode_id="episode-42",
        episode_number=42,
        updated_at="2026-06-16T10:00:00Z",
        transcript_summary="summary",
        ai_generated_meta={"title": "title", "description": "description", "prompt_version": "v1"},
        show_notes_summary={"overview": "overview", "topics": []},
        audio_metadata={"file_size_bytes": 10, "duration_str": "00:01:00"},
    )

    doc_ref = client.collection("podcasts").document("podcast-1").collection("episodes_contents").document("episode-42")
    assert doc_ref.set_calls == [
        (
            {
                "episode_id": "episode-42",
                "episode_number": 42,
                "updated_at": "2026-06-16T10:00:00Z",
                "transcript_summary": "summary",
                "ai_generated_meta": {"title": "title", "description": "description", "prompt_version": "v1"},
                "show_notes_summary": {"overview": "overview", "topics": []},
                "audio_metadata": {"file_size_bytes": 10, "duration_str": "00:01:00"},
            },
            True,
        ),
    ]


def test_save_transcript_chunks_writes_batch_documents() -> None:
    client = _FakeClient()
    manager = FirestoreManager(project_id="demo", client=client)

    saved_ids = manager.save_transcript_chunks(
        podcast_id="podcast-1",
        episode_id="episode-42",
        transcript="A" * 1300,
        chunk_size=800,
    )

    assert saved_ids == ["chunk_0001", "chunk_0002"]
    assert (
        client.batch_instance.operations[0][0]
        == "podcasts/podcast-1/episodes_contents/episode-42/transcripts/chunk_0001"
    )
    assert (
        client.batch_instance.operations[1][0]
        == "podcasts/podcast-1/episodes_contents/episode-42/transcripts/chunk_0002"
    )


def test_create_sns_promotion_writes_pending_record() -> None:
    client = _FakeClient()
    manager = FirestoreManager(project_id="demo", client=client)

    promotion_id = manager.create_sns_promotion(
        podcast_id="podcast-1",
        episode_id="episode-42",
        promotion_id="promotion-1",
        generated_at="2026-06-16T10:00:00Z",
        scheduled_time="2026-06-16T11:00:00Z",
        episode_number=42,
        message="hello",
        platform_urls={"apple": "", "spotify": "", "amazon": ""},
        hashtags=["#Podcast"],
    )

    assert promotion_id == "promotion-1"
    doc_ref = (
        client.collection("podcasts")
        .document("podcast-1")
        .collection("episodes_contents")
        .document("episode-42")
        .collection("sns_promotions")
        .document("promotion-1")
    )
    assert doc_ref.set_calls[0][0]["status"] == "pending"


def test_create_topic_proposal_writes_top_level_document() -> None:
    client = _FakeClient()
    manager = FirestoreManager(project_id="demo", client=client)

    proposal_id = manager.create_topic_proposal(
        podcast_id="podcast-1",
        proposal_id="proposal-1",
        target_period_string="2026年 第23週 (06/01 - 06/07)",
        generated_at="2026-06-16T10:00:00Z",
        related_news=[{"title": "news", "url": "https://example.com", "summary": "", "source_reason": "reason"}],
        suggested_topics=[
            {"title": "topic", "description": "desc", "suggested_points": ["a"], "related_past_episodes": [1]}
        ],
    )

    assert proposal_id == "proposal-1"
    doc_ref = client.collection("podcasts").document("podcast-1").collection("topic_proposals").document("proposal-1")
    assert doc_ref.set_calls[0][0]["target_period_string"] == "2026年 第23週 (06/01 - 06/07)"
