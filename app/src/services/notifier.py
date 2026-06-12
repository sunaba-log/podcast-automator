"""Backward-compatible notifier exports.

This module re-exports concrete implementations from infrastructure.
"""

import requests  # noqa: F401

from infrastructure.notifier import DISCORD_MESSAGE_LIMIT, Notifier, split_message

__all__ = ["DISCORD_MESSAGE_LIMIT", "Notifier", "split_message"]
