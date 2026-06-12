"""Emit environment variables as structured log lines."""

from __future__ import annotations

import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING

from services import (
    AudioAnalyzer,
    AudioConverter,
    GCSClient,
    Notifier,
    PodcastRssManager,
    R2Client,
    SecretManagerClient,
    get_audio_info,
)
from usecases import ProcessPodcastWorkflow, ProcessPodcastWorkflowInput

if TYPE_CHECKING:
    from collections.abc import Mapping


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)

# cloud run jobs
# https://docs.cloud.google.com/run/docs/quickstarts/jobs/build-create-python?hl=ja

# 必須環境変数
PROJECT_ID = os.environ.get("PROJECT_ID")
GCS_BUCKET = os.environ.get("GCS_BUCKET")
GCS_TRIGGER_OBJECT_NAME = os.environ.get("GCS_TRIGGER_OBJECT_NAME")
R2_BUCKET = os.environ.get("R2_BUCKET")


# 任意環境変数
R2_KEY_PREFIX = os.environ.get("R2_KEY_PREFIX", "test")  # R2内の保存先フォルダ
SECRET_NAME = os.environ.get("SECRET_NAME")
R2_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "8ed20f6872cea7c9219d68bfcf5f98ae")  # noqa: RUF003
R2_ACCESS_KEY_ID = os.environ.get("CLOUDFLARE_ACCESS_KEY_ID")  # noqa: RUF003
R2_SECRET_ACCESS_KEY = os.environ.get("CLOUDFLARE_SECRET_ACCESS_KEY")  # noqa: RUF003
DISCORD_WEBHOOK_INFO_URL = os.environ.get("DISCORD_WEBHOOK_INFO_URL")
AI_MODEL_ID = os.environ.get("AI_MODEL_ID", "gemini-2.5-flash")  # GeminiモデルID(未指定時はデフォルト)  # noqa: RUF003
R2_CUSTOM_DOMAIN = os.environ.get("R2_CUSTOM_DOMAIN", "podcast.sunabalog.com")

R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL", f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com")
if SECRET_NAME is None and (R2_ACCESS_KEY_ID is None or R2_SECRET_ACCESS_KEY is None):
    msg = "Either SECRET_NAME or both R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY must be provided."
    logger.error(msg)
    raise ValueError(msg)

# 環境変数の確認
logger.info("## Environment Variables ##")
logger.info("PROJECT_ID: %s", PROJECT_ID)
logger.info("SECRET_NAME: %s", SECRET_NAME)
logger.info("GCS_BUCKET: %s", GCS_BUCKET)
logger.info("GCS_TRIGGER_OBJECT_NAME: %s", GCS_TRIGGER_OBJECT_NAME)
logger.info("R2_ENDPOINT_URL: %s", R2_ENDPOINT_URL)
logger.info("R2_BUCKET: %s", R2_BUCKET)
logger.info("R2_KEY_PREFIX: %s", R2_KEY_PREFIX)
logger.info("AI_MODEL_ID: %s", AI_MODEL_ID)
logger.info("R2_CUSTOM_DOMAIN: %s", R2_CUSTOM_DOMAIN)
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
    if PROJECT_ID is None:
        msg = "PROJECT_ID environment variable is required."
        logger.error(msg)
        raise ValueError(msg)
    if GCS_BUCKET is None:
        msg = "GCS_BUCKET environment variable is required."
        logger.error(msg)
        raise ValueError(msg)
    if GCS_TRIGGER_OBJECT_NAME is None:
        msg = "GCS_TRIGGER_OBJECT_NAME environment variable is required."
        logger.error(msg)
        raise ValueError(msg)
    if R2_BUCKET is None:
        msg = "R2_BUCKET environment variable is required."
        logger.error(msg)
        raise ValueError(msg)
    # secret manager から R2 と Discord の認証情報を取得
    if SECRET_NAME:
        secret_manager_client = SecretManagerClient(project_id=PROJECT_ID, secret_name=SECRET_NAME)
        r2_access_key, r2_secret_key = secret_manager_client.get_r2_credentials()
        discord_webhook_url = secret_manager_client.get_discord_webhook_url()
    else:
        r2_access_key = R2_ACCESS_KEY_ID
        r2_secret_key = R2_SECRET_ACCESS_KEY
        discord_webhook_url = DISCORD_WEBHOOK_INFO_URL

    notifier_client = Notifier(discord_webhook_url=discord_webhook_url)
    audio_analyzer = AudioAnalyzer(project_id=PROJECT_ID)
    r2_client = R2Client(
        project_id=PROJECT_ID,
        endpoint_url=R2_ENDPOINT_URL,
        bucket_name=R2_BUCKET,
        access_key=r2_access_key,
        secret_key=r2_secret_key,
    )
    gcs_client = GCSClient(project_id=PROJECT_ID)

    usecase = ProcessPodcastWorkflow(
        transcript_provider=audio_analyzer,
        object_storage=r2_client,
        blob_source=gcs_client,
        notifier=notifier_client,
        rss_manager_factory=PodcastRssManager,
        audio_converter=AudioConverter.convert_to_mp3,
        audio_info_reader=get_audio_info,
        logger=logger,
    )
    usecase.run(
        ProcessPodcastWorkflowInput(
            project_id=PROJECT_ID,
            gcs_bucket=GCS_BUCKET,
            gcs_trigger_object_name=GCS_TRIGGER_OBJECT_NAME,
            r2_bucket=R2_BUCKET,
            r2_key_prefix=R2_KEY_PREFIX,
            ai_model_id=AI_MODEL_ID,
            r2_custom_domain=R2_CUSTOM_DOMAIN,
        )
    )


def main() -> None:
    """Main entry point for the podcast processor."""
    for arg in sys.argv:
        logger.info("Argument: %s", arg)
    process_podcast_workflow()


if __name__ == "__main__":
    main()
