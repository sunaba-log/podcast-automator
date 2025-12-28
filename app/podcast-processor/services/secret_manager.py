import json
import logging

from google.cloud import secretmanager_v1

logger = logging.getLogger(__name__)


class SecretManagerClient:
    def __init__(self, project_id: str, secret_name: str, version: str = "latest"):
        self.project_id = project_id
        self.secret_name = secret_name
        self.version = version
        self.client = secretmanager_v1.SecretManagerServiceClient()
        self.secrets = self._get_credentials()

    def _get_credentials(self) -> tuple:
        """Secret Manager から 認証情報を取得."""
        try:
            secret_path = self.client.secret_version_path(
                self.project_id, self.secret_name, self.version
            )
            response = self.client.access_secret_version(request={"name": secret_path})
            secret_data = json.loads(response.payload.data.decode("UTF-8"))
            return secret_data
        except Exception as e:
            logger.error(f"Failed to get credentials: {e}")
            raise

    def get_r2_credentials(self) -> tuple:
        """R2 認証情報を取得."""
        return self.secrets.get("r2_access_key"), self.secrets.get("r2_secret_key")

    def get_discord_webhook_url(self) -> str:
        """Discord Webhook URL を取得."""
        return self.secrets.get("discord_webhook_url", "")
