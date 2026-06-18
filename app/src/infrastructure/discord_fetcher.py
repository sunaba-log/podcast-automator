"""Discord REST API infrastructure client."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from domain.interfaces import DiscordTranscriptSource

logger = logging.getLogger(__name__)

_DISCORD_API_BASE = "https://discord.com/api/v10"
_MAX_FETCH_LIMIT = 100


@dataclass
class DiscordMessage:
    """Single Discord channel message."""

    id: str
    content: str
    timestamp: str
    author_name: str


class DiscordFetcher(DiscordTranscriptSource):
    """Read messages from Discord Bot API."""

    def __init__(self, bot_token: str) -> None:
        """Initialize fetcher with Discord bot token."""
        self._headers = {
            "Authorization": f"Bot {bot_token.strip()}",
            "Content-Type": "application/json",
        }

    def fetch_messages(
        self,
        channel_id: str,
        limit: int = 50,
    ) -> list[DiscordMessage]:
        """Fetch newest messages up to limit."""
        clamped_limit = min(max(1, limit), _MAX_FETCH_LIMIT)
        if clamped_limit != limit:
            logger.warning(
                "fetch_messages: limit %d clamped to %d (Discord API max=%d)",
                limit,
                clamped_limit,
                _MAX_FETCH_LIMIT,
            )

        url = f"{_DISCORD_API_BASE}/channels/{channel_id}/messages"
        response = requests.get(
            url,
            headers=self._headers,
            params={"limit": clamped_limit},
            timeout=10,
        )
        response.raise_for_status()

        return [
            DiscordMessage(
                id=m["id"],
                content=m.get("content", ""),
                timestamp=m["timestamp"],
                author_name=m["author"]["username"],
            )
            for m in response.json()
        ]
