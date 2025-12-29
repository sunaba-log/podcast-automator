import json  # noqa: D100
import logging
from dataclasses import dataclass

from google.cloud import secretmanager_v1

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SecretJson:
    """シークレット."""

    r2_access_key: str
    r2_secret_key: str
    discord_webhook_url: str


class SecretManagerClient:
    """Secret Manager クライアント."""

    def __init__(self, project_id: str, secret_name: str, version: str = "latest") -> None:
        """Secret Manager クライアントを初期化."""
        self.project_id = project_id
        self.secret_name = secret_name
        self.version = version
        self.client = secretmanager_v1.SecretManagerServiceClient()
        self.secrets = self._get_credentials()

    def _get_credentials(self) -> SecretJson:
        """Secret Manager から 認証情報を取得."""
        try:
            secret_path = self.client.secret_version_path(self.project_id, self.secret_name, self.version)
            response = self.client.access_secret_version(request={"name": secret_path})
            secret_json = json.loads(response.payload.data.decode("UTF-8"))
            return SecretJson(
                r2_access_key=secret_json.get("r2_access_key", ""),
                r2_secret_key=secret_json.get("r2_secret_key", ""),
                discord_webhook_url=secret_json.get("discord_webhook_url", ""),
            )
        except Exception as e:
            logger.exception("Failed to get credentials")
            raise

    def get_r2_credentials(self) -> tuple:
        """R2 認証情報を取得."""
        return self.secrets.r2_access_key, self.secrets.r2_secret_key

    def get_discord_webhook_url(self) -> str:
        """Discord Webhook URL を取得."""
        return self.secrets.discord_webhook_url
