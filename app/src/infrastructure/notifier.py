"""Discord notification infrastructure."""

import logging

import requests

from domain.interfaces import NotificationGateway

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)

DISCORD_MESSAGE_LIMIT = 2000


def split_message(message: str, max_length: int = DISCORD_MESSAGE_LIMIT) -> list[str]:
    """Split a message by max Discord length."""
    if len(message) <= max_length:
        return [message]

    messages = []
    current_message = ""

    for line in message.split("\n"):
        if len(line) > max_length:
            if current_message:
                messages.append(current_message)
                current_message = ""

            for i in range(0, len(line), max_length):
                messages.extend([line[i : i + max_length]])
        else:
            test_message = current_message + ("\n" if current_message else "") + line

            if len(test_message) <= max_length:
                current_message = test_message
            else:
                if current_message:
                    messages.append(current_message)
                current_message = line

    if current_message:
        messages.append(current_message)

    return messages


class Notifier(NotificationGateway):
    """Notification service client."""

    def __init__(self, discord_webhook_url: str | None = None) -> None:
        """Initialize notifier with an optional Discord webhook URL."""
        self.discord_webhook_url = discord_webhook_url

        if self.discord_webhook_url is None:
            logger.warning("Discord Webhook URLが設定されていません。通知機能はスキップされます。")

    def send_discord_message(self, message: str, username: str = "Podcast Automator") -> bool:
        """Send Discord message, splitting to fit length limits."""
        if self.discord_webhook_url is None:
            logger.warning("Discord Webhook URL未設定のため、メッセージ送信をスキップしました: %s...", message[:20])
            return False

        try:
            messages = split_message(message)
            for msg in messages:
                payload = {"username": username, "content": msg}
                response = requests.post(self.discord_webhook_url, json=payload, timeout=10)

                if response.status_code not in (200, 204):
                    logger.error("Discord送信失敗: ステータス %d", response.status_code)
                    return False
            return True

        except Exception:
            logger.exception("Discordメッセージ送信エラー:")
            return False
