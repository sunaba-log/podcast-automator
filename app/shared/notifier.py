"""Discord通知ライブラリ."""

import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DiscordNotifier:
    def __init__(self, webhook_url: Optional[str] = None):
        if not webhook_url:
            from google.cloud import secretmanager

            webhook_url = self._get_webhook_url()

        self.webhook_url = webhook_url

    def _get_webhook_url(self) -> str:
        """Secret Manager から Discord Webhook URL を取得."""
        try:
            from google.cloud import secretmanager
            from config import Config

            client = secretmanager.SecretManagerServiceClient()
            secret_path = client.secret_version_path(
                Config.PROJECT_ID, Config.DISCORD_WEBHOOK_SECRET_NAME, "latest"
            )
            response = client.access_secret_version(request={"name": secret_path})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Failed to get Discord webhook URL: {e}")
            raise

    def send_message(self, message: str, embed: Optional[dict] = None) -> None:
        """Discord にメッセージを送信."""
        try:
            payload = {"content": message}
            if embed:
                payload["embeds"] = [embed]

            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            logger.info(f"Discord notification sent: {message}")
        except requests.RequestException as e:
            logger.error(f"Failed to send Discord notification: {e}")
            raise

    def send_status_update(
        self,
        job_id: str,
        status: str,
        message: str,
        error: Optional[str] = None,
        output_url: Optional[str] = None,
    ) -> None:
        """ジョブ状態の更新を通知."""

        color = {"completed": 3066993, "failed": 15158332, "in_progress": 3447003}.get(
            status, 0
        )

        embed = {
            "title": f"Podcast Processing: {status.upper()}",
            "description": message,
            "color": color,
            "fields": [
                {"name": "Job ID", "value": job_id, "inline": True},
                {"name": "Status", "value": status, "inline": True},
            ],
        }

        if error:
            embed["fields"].append({"name": "Error", "value": error, "inline": False})

        if output_url:
            embed["fields"].append(
                {"name": "Output URL", "value": output_url, "inline": False}
            )

        self.send_message("", embed=embed)
