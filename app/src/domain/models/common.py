"""Shared domain models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from datetime import datetime


class Summary(BaseModel):
    """Structured summary for transcript output."""

    title: str = Field(..., description="Episode title")
    description: str = Field(..., description="Episode description")


@dataclass
class NewsItem:
    """News item fetched from feeds."""

    title: str
    url: str
    source: str
    published_at: datetime
    summary: str | None = None


@dataclass
class DiscordMessage:
    """Discord channel message."""

    id: str
    content: str
    timestamp: str
    author_name: str
