"""Agenda-related domain models."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import StrEnum


class PromptType(StrEnum):
    """Discussion prompt category."""

    question = "question"
    uncertain = "uncertain"
    design_decision = "design_decision"
    future_consideration = "future_consideration"


class SortPolicy(StrEnum):
    """Sort policy for agenda artifacts."""

    continuity = "continuity"
    recentness = "recentness"
    hybrid = "hybrid"


@dataclass
class SeedTopic:
    """A recurring topic seed."""

    id: str
    name: str
    category: str
    keywords: list[str]
    parent_topic_id: str | None = None


@dataclass
class Episode:
    """Single reconstructed episode."""

    number: int
    content: str
    timestamp: str
    source_message_ids: list[str]

    @property
    def display_number(self) -> str:
        """Display-friendly episode number."""
        return f"#{self.number}"


@dataclass
class MentionEvidence:
    """Evidence item for a matched topic mention."""

    source_episode: int
    text: str
    sentence_index: int


@dataclass
class TopicMatch:
    """Aggregated mention result for a topic."""

    topic_id: str
    display_name: str
    episode_count: int
    mention_count: int
    evidence: list[MentionEvidence]
    score: float | None = None
    keywords: list[str] = field(default_factory=list)


@dataclass
class ActionItem:
    """Action extracted from transcripts."""

    text: str
    source_episode: int
    assignee: str | None = None


@dataclass
class DiscussionPrompt:
    """Unresolved prompt extracted from transcripts."""

    sentence: str
    prompt_type: PromptType
    source_episode: int
    confidence: float | None = None


@dataclass
class AgendaMetadata:
    """Metadata for reproducible agenda generation."""

    generated_at: str
    source_episode_numbers: list[int]
    sort_policy: str
    analysis_window_size: int
    fetched_message_count: int


@dataclass
class AgendaResult:
    """Aggregate output for agenda generation."""

    metadata: AgendaMetadata
    analyzed_episodes: int
    recurring_themes: list[TopicMatch]
    action_items: list[ActionItem]
    discussion_prompts: list[DiscussionPrompt]
    schema_version: str = "1.0"

    def to_dict(self) -> dict:  # type: ignore[type-arg]
        """Return a JSON-serializable structure."""
        return dataclasses.asdict(self)
