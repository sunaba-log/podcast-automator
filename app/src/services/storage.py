"""Backward-compatible storage exports.

This module re-exports concrete implementations from infrastructure.
"""

from infrastructure.storage import GCSClient, R2Client, get_audio_info

__all__ = ["GCSClient", "R2Client", "get_audio_info"]
