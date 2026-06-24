"""Firestore persistence manager."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from google.cloud import firestore


class FirestoreManager:
    """Persist generated podcast artifacts to Firestore."""

    def __init__(  # noqa: D107
        self, *, project_id: str, client: firestore.Client | None = None, logger: logging.Logger | None = None
    ) -> None:
        self._project_id = project_id
        self._client = client or firestore.Client(project=project_id)
        self._logger = logger or logging.getLogger(__name__)

    def save_episode_content(
        self,
        *,
        podcast_id: str,
        episode_id: str,
        episode_number: int,
        updated_at: str,
        transcript_summary: str,
        ai_generated_meta: dict[str, Any],
        show_notes_summary: dict[str, Any],
        audio_metadata: dict[str, Any],
    ) -> str:
        """Upsert episode content document."""
        doc_ref = self._episode_contents_collection(podcast_id).document(episode_id)
        doc_ref.set(
            {
                "episode_id": episode_id,
                "episode_number": episode_number,
                "updated_at": updated_at,
                "transcript_summary": transcript_summary,
                "ai_generated_meta": ai_generated_meta,
                "show_notes_summary": show_notes_summary,
                "audio_metadata": audio_metadata,
            },
            merge=True,
        )
        return doc_ref.id

    def save_transcript_chunks(
        self,
        *,
        podcast_id: str,
        episode_id: str,
        transcript: str,
        chunk_size: int = 1200,
    ) -> list[str]:
        """Store transcript chunks in a subcollection."""
        chunks = list(_chunk_text(transcript, chunk_size=chunk_size))
        batch = self._client.batch()
        saved_ids: list[str] = []

        for index, chunk_text in enumerate(chunks, start=1):
            chunk_id = f"chunk_{index:04d}"
            saved_ids.append(chunk_id)
            doc_ref = (
                self._episode_contents_collection(podcast_id)
                .document(episode_id)
                .collection("transcripts")
                .document(
                    chunk_id,
                )
            )
            batch.set(
                doc_ref,
                {
                    "chunk_id": chunk_id,
                    "start_time": 0,
                    "end_time": 0,
                    "speaker": "unknown",
                    "text": chunk_text,
                },
            )

        batch.commit()
        return saved_ids

    def create_sns_promotion(
        self,
        *,
        podcast_id: str,
        episode_id: str,
        promotion_id: str | None,
        generated_at: str,
        scheduled_time: str,
        episode_number: int,
        message: str,
        platform_urls: dict[str, str],
        hashtags: list[str],
        status: str = "pending",
    ) -> str:
        """Create or overwrite an SNS promotion record."""
        promotion_doc_id = promotion_id or uuid.uuid4().hex
        doc_ref = (
            self._episode_contents_collection(podcast_id)
            .document(episode_id)
            .collection("sns_promotions")
            .document(
                promotion_doc_id,
            )
        )
        doc_ref.set(
            {
                "status": status,
                "generated_at": generated_at,
                "scheduled_time": scheduled_time,
                "episode": {"number": episode_number},
                "message": message,
                "platform_urls": platform_urls,
                "hashtags": hashtags,
            },
            merge=True,
        )
        return doc_ref.id

    def create_topic_proposal(
        self,
        *,
        podcast_id: str,
        proposal_id: str | None,
        target_period_string: str,
        generated_at: str,
        related_news: list[dict[str, Any]],
        suggested_topics: list[dict[str, Any]],
    ) -> str:
        """Create a top-level topic proposal document."""
        saved_id = proposal_id or uuid.uuid4().hex
        doc_ref = self._podcast_collection(podcast_id).collection("topic_proposals").document(saved_id)
        doc_ref.set(
            {
                "proposal_id": saved_id,
                "target_period_string": target_period_string,
                "generated_at": generated_at,
                "related_news": related_news,
                "suggested_topics": suggested_topics,
            },
            merge=True,
        )
        return doc_ref.id

    def get_pending_sns_promotions(self) -> list[dict[str, Any]]:
        """Retrieve all pending SNS promotions across all episodes using a collection group query."""
        query = self._client.collection_group("sns_promotions").where("status", "==", "pending")
        results = []
        for doc in query.stream():
            data = doc.to_dict()
            data["doc_id"] = doc.id
            data["reference_path"] = doc.reference.path
            results.append(data)
        return results

    def update_sns_promotion_status(self, doc_path: str, status: str) -> None:
        """Update status of a specific SNS promotion document by its full reference path."""
        self._client.document(doc_path).update({"status": status})

    def _podcast_collection(self, podcast_id: str) -> firestore.DocumentReference:
        return self._client.collection("podcasts").document(str(podcast_id))

    def _episode_contents_collection(self, podcast_id: str) -> firestore.CollectionReference:
        return self._podcast_collection(podcast_id).collection("episodes_contents")


def _chunk_text(text: str, *, chunk_size: int) -> list[str]:
    """Split text into Firestore-friendly chunks."""
    normalized = text.strip()
    if not normalized:
        return [""]

    chunks: list[str] = []
    current = ""
    for raw_paragraph in normalized.split("\n\n"):
        paragraph = raw_paragraph.strip()
        if not paragraph:
            continue
        if not current:
            current = paragraph
            continue
        candidate = f"{current}\n\n{paragraph}"
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        chunks.extend(_split_by_size(current, chunk_size))
        current = paragraph

    if current:
        chunks.extend(_split_by_size(current, chunk_size))

    return chunks or [normalized]


def _split_by_size(text: str, chunk_size: int) -> list[str]:
    """Split a long string by size only."""
    if len(text) <= chunk_size:
        return [text]
    return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]
