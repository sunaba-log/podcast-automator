"""Weekly agenda notification job for Discord.

このモジュールは毎週水曜日 07:00 JST に Cloud Scheduler によって起動され、
ポッドキャスト収録の週次リマインダーを Discord へ投稿します。
"""

from __future__ import annotations

import logging
import os
import sys

from services.notifier import Notifier

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)

DISCORD_WEBHOOK_AGENDA_URL = os.environ.get("DISCORD_WEBHOOK_AGENDA_URL")

AGENDA_MESSAGE = (
    "📅 **今週の収録リマインダー**\n\n"
    "今週のポッドキャスト収録の準備はできていますか?\n\n"
    "収録後は音声ファイルを GCS にアップロードしてください 🎙️"
)


def send_weekly_agenda() -> None:
    """毎週水曜日に Discord へアジェンダを投稿する."""
    logger.info("## Weekly Agenda Job Start ##")
    logger.info("DISCORD_WEBHOOK_AGENDA_URL configured: %s", bool(DISCORD_WEBHOOK_AGENDA_URL))

    notifier = Notifier(discord_webhook_url=DISCORD_WEBHOOK_AGENDA_URL)
    success = notifier.send_discord_message(
        message=AGENDA_MESSAGE,
        username="Podcast Scheduler",
    )

    if success:
        logger.info("Weekly agenda sent to Discord successfully.")
    else:
        logger.error("Failed to send weekly agenda to Discord.")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    send_weekly_agenda()


if __name__ == "__main__":
    main()
