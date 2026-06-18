"""Secret Manager infrastructure client."""

import json
import logging
from dataclasses import dataclass

from google.cloud import secretmanager_v1

from domain.interfaces import SecretProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SecretJson:
    """Secret payload model."""

    r2_access_key: str | None
    r2_secret_key: str | None
    discord_webhook_url: str | None


class SecretManagerClient(SecretProvider):
    """Google Secret Manager client wrapper."""

    def __init__(self, project_id: str, secret_name: str, version: str = "latest") -> None:
        """Initialize secret client with project and secret metadata."""
        self.project_id = project_id
        self.secret_name = secret_name
        self.version = version
        self.client = secretmanager_v1.SecretManagerServiceClient()
        self.secrets = self._get_credentials()

    def _get_credentials(self) -> SecretJson:
        """Load secret JSON from Secret Manager."""
        try:
            secret_path = self.client.secret_version_path(self.project_id, self.secret_name, self.version)
            response = self.client.access_secret_version(request={"name": secret_path})
            secret_json = json.loads(response.payload.data.decode("UTF-8"))
            return SecretJson(
                r2_access_key=secret_json.get("r2_access_key"),
                r2_secret_key=secret_json.get("r2_secret_key"),
                discord_webhook_url=secret_json.get("discord_webhook_url"),
            )
        except Exception:
            logger.exception("Failed to get credentials")
            raise

    def get_r2_credentials(self) -> tuple[str | None, str | None]:
        """Get R2 credentials."""
        return self.secrets.r2_access_key, self.secrets.r2_secret_key

    def get_discord_webhook_url(self) -> str | None:
        """Get Discord webhook URL."""
        return self.secrets.discord_webhook_url
