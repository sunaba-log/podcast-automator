"""Tests for AutoPostSnsUsecase usecase."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from usecases.auto_post_sns import AutoPostSnsUsecase


class DummyFirestoreManager:
    def __init__(self, promotions: list[dict[str, Any]]) -> None:
        self.promotions = promotions
        self.updates: list[tuple[str, str]] = []

    def get_pending_sns_promotions(self) -> list[dict[str, Any]]:
        return self.promotions

    def update_sns_promotion_status(self, reference_path: str, status: str) -> None:
        self.updates.append((reference_path, status))


class DummyXClient:
    def __init__(self, *, post_success: bool = True, raise_error: bool = False) -> None:
        self.post_success = post_success
        self.raise_error = raise_error
        self.posted_texts: list[str] = []

    def post_thread(self, text: str) -> bool:
        if self.raise_error:
            raise RuntimeError("X API failure")
        self.posted_texts.append(text)
        return self.post_success


def test_auto_post_no_pending_promotions() -> None:
    """Test no actions when there are no pending promotions."""
    firestore = DummyFirestoreManager([])
    x_client = DummyXClient()
    usecase = AutoPostSnsUsecase(firestore_manager=firestore, x_client=x_client)  # type: ignore[arg-type]
    usecase.run()

    assert not x_client.posted_texts
    assert not firestore.updates


def test_auto_post_promotions_not_due_yet() -> None:
    """Test no actions when scheduled time is in the future."""
    future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    promo = {
        "doc_id": "doc1",
        "reference_path": "podcasts/1/episodes_contents/1/sns_promotions/doc1",
        "status": "pending",
        "scheduled_time": future_time,
        "message": "Future message",
    }
    firestore = DummyFirestoreManager([promo])
    x_client = DummyXClient()
    usecase = AutoPostSnsUsecase(firestore_manager=firestore, x_client=x_client)  # type: ignore[arg-type]
    usecase.run()

    assert not x_client.posted_texts
    assert not firestore.updates


def test_auto_post_multiple_due_posts_oldest_selected() -> None:
    """Test oldest due promotion is posted and status updated to posted."""
    now = datetime.now(UTC)
    time_oldest = (now - timedelta(hours=2)).isoformat()
    time_newer = (now - timedelta(hours=1)).isoformat()

    promo_oldest = {
        "doc_id": "doc_oldest",
        "reference_path": "podcasts/1/episodes_contents/1/sns_promotions/doc_oldest",
        "status": "pending",
        "scheduled_time": time_oldest,
        "message": "Oldest message",
        "episode": {"number": 10},
        "platform_urls": {"apple": "https://apple.com"},
        "hashtags": ["#oldest"],
    }
    promo_newer = {
        "doc_id": "doc_newer",
        "reference_path": "podcasts/1/episodes_contents/1/sns_promotions/doc_newer",
        "status": "pending",
        "scheduled_time": time_newer,
        "message": "Newer message",
        "episode": {"number": 11},
    }

    # Pass list in reversed order to ensure sorting works.
    firestore = DummyFirestoreManager([promo_newer, promo_oldest])
    x_client = DummyXClient(post_success=True)
    usecase = AutoPostSnsUsecase(firestore_manager=firestore, x_client=x_client)  # type: ignore[arg-type]
    usecase.run()

    assert len(x_client.posted_texts) == 1
    # Verify the oldest message with correct formatting is posted
    assert "第10回\nOldest message" in x_client.posted_texts[0]
    assert "▼Apple\nhttps://apple.com" in x_client.posted_texts[0]

    assert len(firestore.updates) == 1
    assert firestore.updates[0] == ("podcasts/1/episodes_contents/1/sns_promotions/doc_oldest", "posted")


def test_auto_post_posting_fails_updates_status_to_failed() -> None:
    """Test Firestore status is updated to failed when X post fails."""
    past_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    promo = {
        "doc_id": "doc_fail",
        "reference_path": "podcasts/1/episodes_contents/1/sns_promotions/doc_fail",
        "status": "pending",
        "scheduled_time": past_time,
        "message": "Failing message",
    }
    firestore = DummyFirestoreManager([promo])
    x_client = DummyXClient(post_success=False)
    usecase = AutoPostSnsUsecase(firestore_manager=firestore, x_client=x_client)  # type: ignore[arg-type]
    usecase.run()

    assert len(x_client.posted_texts) == 1
    assert len(firestore.updates) == 1
    assert firestore.updates[0] == ("podcasts/1/episodes_contents/1/sns_promotions/doc_fail", "failed")


def test_auto_post_exception_during_post_updates_status_and_raises() -> None:
    """Test exceptions from XClient are caught, status updated to failed, and raised."""
    past_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    promo = {
        "doc_id": "doc_error",
        "reference_path": "podcasts/1/episodes_contents/1/sns_promotions/doc_error",
        "status": "pending",
        "scheduled_time": past_time,
        "message": "Error message",
    }
    firestore = DummyFirestoreManager([promo])
    x_client = DummyXClient(raise_error=True)
    usecase = AutoPostSnsUsecase(firestore_manager=firestore, x_client=x_client)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="X API failure"):
        usecase.run()

    assert len(firestore.updates) == 1
    assert firestore.updates[0] == ("podcasts/1/episodes_contents/1/sns_promotions/doc_error", "failed")
