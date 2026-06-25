from __future__ import annotations

import logging
from unittest import mock

from domain.interfaces import NotificationGateway
from services.firestore_manager import FirestoreManager
from usecases.generate_weekly_agenda import GenerateWeeklyAgendaUsecase


# Simple mock structures for test inputs
class FakeAgendaMetadata:
    def __init__(self, generated_at: str) -> None:
        self.generated_at = generated_at


class FakeEvidence:
    def __init__(self, source_episode: int, text: str) -> None:
        self.source_episode = source_episode
        self.text = text


class FakeTopicMatch:
    def __init__(self, topic_id: str, display_name: str, mention_count: int, evidence: list[FakeEvidence]) -> None:
        self.topic_id = topic_id
        self.display_name = display_name
        self.mention_count = mention_count
        self.evidence = evidence
        self.score = float(mention_count)


class FakeAgendaResult:
    def __init__(self, generated_at: str, recurring_themes: list[FakeTopicMatch]) -> None:
        self.metadata = FakeAgendaMetadata(generated_at)
        self.recurring_themes = recurring_themes
        self.schema_version = "1.0"


class FakeNewsItem:
    def __init__(self, title: str, url: str, summary: str | None) -> None:
        self.title = title
        self.url = url
        self.summary = summary


class FakeNewsCandidate:
    def __init__(self, news_item: FakeNewsItem, topic_match: FakeTopicMatch, score: float) -> None:
        self.news_item = news_item
        self.topic_match = topic_match
        self.score = score


def test_generate_weekly_agenda_no_firestore() -> None:
    # Arrange
    notifier = mock.Mock(spec=NotificationGateway)
    notifier.send_discord_message.return_value = True
    logger = logging.getLogger("test_agenda")

    usecase = GenerateWeeklyAgendaUsecase(
        notifier=notifier,
        firestore_manager=None,
        logger=logger,
    )

    # Act
    success = usecase.run(
        message_builder=lambda: ("Hello World", None, []),
        fallback_message="Fallback",
        podcast_id=None,
    )

    # Assert
    assert success is True
    notifier.send_discord_message.assert_called_once_with(message="Hello World", username="Podcast Scheduler")


def test_generate_weekly_agenda_saves_to_firestore() -> None:
    # Arrange
    notifier = mock.Mock(spec=NotificationGateway)
    notifier.send_discord_message.return_value = True
    firestore_manager = mock.Mock(spec=FirestoreManager)
    firestore_manager.create_topic_proposal.return_value = "proposal-123"
    logger = logging.getLogger("test_agenda")

    usecase = GenerateWeeklyAgendaUsecase(
        notifier=notifier,
        firestore_manager=firestore_manager,
        logger=logger,
    )

    theme1 = FakeTopicMatch(
        topic_id="tech-ai",
        display_name="AI Theme",
        mention_count=2,
        evidence=[FakeEvidence(source_episode=1, text="AI is great")],
    )
    result = FakeAgendaResult(
        generated_at="2026-06-25T00:00:00Z",
        recurring_themes=[theme1],
    )
    news_item = FakeNewsItem(title="News Title", url="https://example.com/news", summary="Summary text")
    news_candidate = FakeNewsCandidate(news_item=news_item, topic_match=theme1, score=0.9)

    # Act
    success = usecase.run(
        message_builder=lambda: ("Agenda Message", result, [news_candidate]),
        fallback_message="Fallback",
        podcast_id="podcast-456",
    )

    # Assert
    assert success is True
    notifier.send_discord_message.assert_called_once_with(message="Agenda Message", username="Podcast Scheduler")
    firestore_manager.create_topic_proposal.assert_called_once()

    # Verify the arguments passed to create_topic_proposal
    _, kwargs = firestore_manager.create_topic_proposal.call_args
    assert kwargs["podcast_id"] == "podcast-456"
    assert kwargs["proposal_id"] is None
    assert "2026年 第26週" in kwargs["target_period_string"]
    assert kwargs["generated_at"] == "2026-06-25T00:00:00Z"

    assert len(kwargs["related_news"]) == 1
    assert kwargs["related_news"][0]["title"] == "News Title"
    assert kwargs["related_news"][0]["url"] == "https://example.com/news"

    assert len(kwargs["suggested_topics"]) == 1
    assert kwargs["suggested_topics"][0]["title"] == "AI Theme"
    assert kwargs["suggested_topics"][0]["suggested_points"] == ["AI is great"]
    assert kwargs["suggested_topics"][0]["related_past_episodes"] == [1]


def test_generate_weekly_agenda_builder_failure_falls_back() -> None:
    # Arrange
    notifier = mock.Mock(spec=NotificationGateway)
    notifier.send_discord_message.return_value = True
    logger = logging.getLogger("test_agenda")

    usecase = GenerateWeeklyAgendaUsecase(
        notifier=notifier,
        firestore_manager=None,
        logger=logger,
    )

    def failing_builder():
        raise RuntimeError("Something failed")

    # Act
    success = usecase.run(
        message_builder=failing_builder,
        fallback_message="Fallback Message",
        podcast_id=None,
    )

    # Assert
    assert success is True
    notifier.send_discord_message.assert_called_once_with(message="Fallback Message", username="Podcast Scheduler")
