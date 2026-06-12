"""Backward-compatible Discord fetcher exports.

This module re-exports concrete implementations from infrastructure.
"""

import requests  # noqa: F401

from infrastructure.discord_fetcher import DiscordFetcher, DiscordMessage

__all__ = ["DiscordFetcher", "DiscordMessage"]
