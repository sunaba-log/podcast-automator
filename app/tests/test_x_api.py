"""Tests for X API client wrapper."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import tweepy
from requests import Response

from infrastructure.x_api import XClient


class _DummyTweepyClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create_tweet(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        next_id = str(len(self.calls))
        return SimpleNamespace(data={"id": next_id})

    def get_me(self, *, user_auth: bool = True) -> SimpleNamespace:  # noqa: ARG002
        return SimpleNamespace(data=SimpleNamespace(id="dummy-user"))


class _FailOnSecondClient(_DummyTweepyClient):
    def create_tweet(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if len(self.calls) == 2:
            return SimpleNamespace(data=None)
        next_id = str(len(self.calls))
        return SimpleNamespace(data={"id": next_id})


class _ForbiddenClient(_DummyTweepyClient):
    def create_tweet(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        response = Response()
        response.status_code = 403
        response._content = b'{"title":"Forbidden","detail":"You are not permitted to perform this action."}'
        response.encoding = "utf-8"
        raise tweepy.errors.Forbidden(response)


def _new_client(dummy_client: _DummyTweepyClient) -> XClient:
    x_client = XClient("k", "s", "t", "ts")
    x_client.client = dummy_client  # type: ignore[assignment]
    return x_client


def test_split_for_x_returns_single_chunk_when_short() -> None:
    """Test split_for_x returns single chunk for short text."""
    text = "short text"
    chunks = XClient.split_for_x(text)
    assert chunks == [text]


def test_split_for_x_splits_long_text_with_limit() -> None:
    """Test split_for_x splits long text accurately."""
    text = "a" * 700
    chunks = XClient.split_for_x(text)

    assert len(chunks) >= 3
    assert "".join(chunks) == text
    assert all(XClient.x_weighted_length(chunk) <= 280 for chunk in chunks)


def test_split_for_x_splits_full_width_text_with_limit() -> None:
    """Test split_for_x splits full width text accurately."""
    text = "あ" * 141
    chunks = XClient.split_for_x(text)

    assert len(chunks) == 2
    assert chunks[0] == "あ" * 140
    assert chunks[1] == "あ"
    assert all(XClient.x_weighted_length(chunk) <= 280 for chunk in chunks)


def test_split_for_x_keeps_full_width_140_chars_in_one_chunk() -> None:
    """Test split_for_x keeps exactly 140 full-width chars in a single chunk."""
    text = "あ" * 140
    chunks = XClient.split_for_x(text)

    assert chunks == [text]
    assert XClient.x_weighted_length(chunks[0]) == 280


def test_post_thread_posts_replies_in_sequence() -> None:
    """Test post_thread posts sequence of replies with reply ids."""
    dummy_client = _DummyTweepyClient()
    x_client = _new_client(dummy_client)

    text = "a" * 600
    success = x_client.post_thread(text)

    assert success is True
    assert len(dummy_client.calls) == 3
    assert "in_reply_to_tweet_id" not in dummy_client.calls[0]
    assert dummy_client.calls[1]["in_reply_to_tweet_id"] == "1"
    assert dummy_client.calls[2]["in_reply_to_tweet_id"] == "2"


def test_post_thread_returns_false_when_any_chunk_fails() -> None:
    """Test post_thread returns False if any posting in sequence fails."""
    dummy_client = _FailOnSecondClient()
    x_client = _new_client(dummy_client)

    text = "a" * 600
    success = x_client.post_thread(text)

    assert success is False
    assert len(dummy_client.calls) == 2


def test_post_returns_false_on_forbidden_error() -> None:
    """Test post returns False on tweepy Forbidden error."""
    dummy_client = _ForbiddenClient()
    x_client = _new_client(dummy_client)

    success = x_client.post("hello")

    assert success is False
    assert len(dummy_client.calls) == 1
