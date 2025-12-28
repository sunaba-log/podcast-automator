from __future__ import annotations

import logging
from unittest import mock

from main import send_discord_notification


def test_send_discord_notification_posts_payload() -> None:
    env = {"DISCORD_WEBHOOK_INFO_URL": "https://discord.example/webhook"}
    handler = logging.NullHandler()
    logger = logging.getLogger("test_discord")
    logger.setLevel(logging.INFO)
    logger.handlers = [handler]
    logger.propagate = False

    with mock.patch("urllib.request.urlopen") as mocked:
        mocked.return_value.__enter__.return_value.read.return_value = b""
        send_discord_notification("hello", environ=env, logger=logger)

    assert mocked.called


def test_send_discord_notification_no_webhook_is_noop() -> None:
    with mock.patch("urllib.request.urlopen") as mocked:
        send_discord_notification("hello", environ={})

    assert not mocked.called
