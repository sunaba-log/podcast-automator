"""Podcast processor entrypoint."""

from __future__ import annotations

import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING

from infrastructure.ai_analyzer import AudioAnalyzer
from infrastructure.notifier import Notifier
from infrastructure.secret_manager import SecretManagerClient
from infrastructure.storage import GCSClient, R2Client, get_audio_info
from services.audio_converter import AudioConverter
from services.firestore_manager import FirestoreManager
from services.rss_manager import PodcastRssManager
from usecases import ProcessPodcastWorkflow, ProcessPodcastWorkflowInput

if TYPE_CHECKING:
    from collections.abc import Mapping


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)


@dataclass(frozen=True)
class PodcastEnvConfig:
    """Resolved environment variables for podcast workflow."""

    project_id: str
    podcast_id: str
    sns_schedule_offset_hours: int
    gcs_bucket: str
    gcs_trigger_object_name: str
    r2_bucket: str
    r2_key_prefix: str
    secret_name: str | None
    r2_endpoint_url: str
    r2_access_key_id: str | None
    r2_secret_access_key: str | None
    discord_webhook_info_url: str | None
    ai_model_id: str
    r2_custom_domain: str


def _required_env(environ: Mapping[str, str], key: str) -> str:
    """Return required environment value or raise ValueError."""
    value = environ.get(key)
    if value is None:
        msg = f"{key} environment variable is required."
        logger.error(msg)
        raise ValueError(msg)
    return value


def _load_podcast_env(environ: Mapping[str, str]) -> PodcastEnvConfig:
    """Load and validate environment variables for podcast workflow."""
    project_id = _required_env(environ, "PROJECT_ID")
    podcast_id = _required_env(environ, "PODCAST_ID")
    gcs_bucket = _required_env(environ, "GCS_BUCKET")
    gcs_trigger_object_name = _required_env(environ, "GCS_TRIGGER_OBJECT_NAME")
    r2_bucket = _required_env(environ, "R2_BUCKET")

    sns_schedule_offset_hours = int(environ.get("SNS_SCHEDULE_OFFSET_HOURS", "1"))
    r2_key_prefix = environ.get("R2_KEY_PREFIX", "test")
    secret_name = environ.get("SECRET_NAME")
    r2_account_id = environ.get("CLOUDFLARE_ACCOUNT_ID", "8ed20f6872cea7c9219d68bfcf5f98ae")
    r2_endpoint_url = environ.get("R2_ENDPOINT_URL", f"https://{r2_account_id}.r2.cloudflarestorage.com")
    r2_access_key_id = environ.get("CLOUDFLARE_ACCESS_KEY_ID")
    r2_secret_access_key = environ.get("CLOUDFLARE_SECRET_ACCESS_KEY")
    discord_webhook_info_url = environ.get("DISCORD_WEBHOOK_INFO_URL")
    ai_model_id = environ.get("AI_MODEL_ID", "gemini-2.5-flash")
    r2_custom_domain = environ.get("R2_CUSTOM_DOMAIN", "podcast.sunabalog.com")

    if secret_name is None and (r2_access_key_id is None or r2_secret_access_key is None):
        msg = "Either SECRET_NAME or both R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY must be provided."
        logger.error(msg)
        raise ValueError(msg)

    return PodcastEnvConfig(
        project_id=project_id,
        podcast_id=podcast_id,
        sns_schedule_offset_hours=sns_schedule_offset_hours,
        gcs_bucket=gcs_bucket,
        gcs_trigger_object_name=gcs_trigger_object_name,
        r2_bucket=r2_bucket,
        r2_key_prefix=r2_key_prefix,
        secret_name=secret_name,
        r2_endpoint_url=r2_endpoint_url,
        r2_access_key_id=r2_access_key_id,
        r2_secret_access_key=r2_secret_access_key,
        discord_webhook_info_url=discord_webhook_info_url,
        ai_model_id=ai_model_id,
        r2_custom_domain=r2_custom_domain,
    )


def _log_environment(config: PodcastEnvConfig) -> None:
    """Log resolved environment settings."""
    logger.info("## Environment Variables ##")
    logger.info("PROJECT_ID: %s", config.project_id)
    logger.info("PODCAST_ID: %s", config.podcast_id)
    logger.info("SNS_SCHEDULE_OFFSET_HOURS: %s", config.sns_schedule_offset_hours)
    logger.info("SECRET_NAME: %s", config.secret_name)
    logger.info("GCS_BUCKET: %s", config.gcs_bucket)
    logger.info("GCS_TRIGGER_OBJECT_NAME: %s", config.gcs_trigger_object_name)
    logger.info("R2_ENDPOINT_URL: %s", config.r2_endpoint_url)
    logger.info("R2_BUCKET: %s", config.r2_bucket)
    logger.info("R2_KEY_PREFIX: %s", config.r2_key_prefix)
    logger.info("AI_MODEL_ID: %s", config.ai_model_id)
    logger.info("R2_CUSTOM_DOMAIN: %s", config.r2_custom_domain)
    logger.info("###########################\n")


def send_discord_notification(
    message: str,
    webhook_url: str | None = None,
    environ: Mapping[str, str] | None = None,
    logger: logging.Logger | None = None,
) -> None:
    """Send a message to Discord via webhook if configured."""
    if environ is None:
        environ = os.environ
    if logger is None:
        logger = logging.getLogger(__name__)

    if webhook_url is None:
        webhook_url = environ.get("DISCORD_WEBHOOK_INFO_URL")
    if not webhook_url:
        return
    parsed_url = urllib.parse.urlparse(webhook_url)
    if parsed_url.scheme not in {"http", "https"}:
        logger.warning("Discord webhook has unsupported scheme: %s", parsed_url.scheme)
        return

    payload = json.dumps({"content": message}, ensure_ascii=True).encode("utf-8")
    request = urllib.request.Request(  # noqa: S310
        webhook_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "podcast-automator/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            response.read()
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read(2048).decode("utf-8", errors="replace")
        except OSError:
            body = ""
        detail = body.strip() or str(exc.reason)
        logger.exception("Discord webhook returned HTTP %s: %s", exc.code, detail)
    except Exception:
        logger.exception("Failed to send Discord notification")


def process_podcast_workflow() -> None:
    """GCSへのファイルアップロードをトリガーに実行されるメイン関数."""
    config = _load_podcast_env(os.environ)
    _log_environment(config)

    if config.secret_name:
        secret_manager_client = SecretManagerClient(project_id=config.project_id, secret_name=config.secret_name)
        r2_access_key, r2_secret_key = secret_manager_client.get_r2_credentials()
        discord_webhook_url = secret_manager_client.get_discord_webhook_url()
    else:
        r2_access_key = config.r2_access_key_id
        r2_secret_key = config.r2_secret_access_key
        discord_webhook_url = config.discord_webhook_info_url

    notifier_client = Notifier(discord_webhook_url=discord_webhook_url)
    audio_analyzer = AudioAnalyzer(project_id=config.project_id)
    firestore_manager = FirestoreManager(project_id=config.project_id)
    r2_client = R2Client(
        project_id=config.project_id,
        endpoint_url=config.r2_endpoint_url,
        bucket_name=config.r2_bucket,
        access_key=r2_access_key,
        secret_key=r2_secret_key,
    )
    gcs_client = GCSClient(project_id=config.project_id)

    usecase = ProcessPodcastWorkflow(
        transcript_provider=audio_analyzer,
        object_storage=r2_client,
        blob_source=gcs_client,
        notifier=notifier_client,
        rss_manager_factory=PodcastRssManager,
        audio_converter=AudioConverter.convert_to_mp3,
        audio_info_reader=get_audio_info,
        firestore_manager=firestore_manager,
        logger=logger,
    )
    usecase.run(
        ProcessPodcastWorkflowInput(
            project_id=config.project_id,
            podcast_id=config.podcast_id,
            sns_schedule_offset_hours=config.sns_schedule_offset_hours,
            gcs_bucket=config.gcs_bucket,
            gcs_trigger_object_name=config.gcs_trigger_object_name,
            r2_bucket=config.r2_bucket,
            r2_key_prefix=config.r2_key_prefix,
            ai_model_id=config.ai_model_id,
            r2_custom_domain=config.r2_custom_domain,
        )
    )


def main() -> None:
    """Main entry point for the podcast processor."""
    for arg in sys.argv:
        logger.info("Argument: %s", arg)
    process_podcast_workflow()


if __name__ == "__main__":
    main()
