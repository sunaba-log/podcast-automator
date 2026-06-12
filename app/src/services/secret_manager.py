"""Backward-compatible secret manager exports.

This module re-exports concrete implementations from infrastructure.
"""

from infrastructure.secret_manager import SecretJson, SecretManagerClient

__all__ = ["SecretJson", "SecretManagerClient"]
