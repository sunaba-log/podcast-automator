"""Emit environment variables as structured log lines."""

from __future__ import annotations

import json
import logging
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

from services import (
    AudioAnalyzer,
    GCSClient,
    Notifier,
    PodcastRssManager,
    R2Client,
    SecretManagerClient,
    transfer_gcs_to_r2,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from botocore.client import BaseClient


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)

# cloud run jobs
# https://docs.cloud.google.com/run/docs/quickstarts/jobs/build-create-python?hl=ja

PROJECT_ID = os.environ.get("PROJECT_ID", "taka-test-481815")
SECRET_NAME = os.environ.get("SECRET_NAME", "sunabalog-r2")
GCS_BUCKET = os.environ.get("GCS_BUCKET", "sample-audio-for-sunabalog")
GCS_TRIGGER_OBJECT_NAME = os.environ.get("GCS_TRIGGER_OBJECT_NAME", "short_dialogue.m4a")
R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL", "https://8ed20f6872cea7c9219d68bfcf5f98ae.r2.cloudflarestorage.com")
R2_BUCKET = os.environ.get("R2_BUCKET", "podcast")
SUBDIRECTORY = os.environ.get("SUBDIRECTORY", "test")  # R2内の保存先フォルダ
AI_MODEL_ID = os.environ.get(
    "AI_MODEL_ID", "gemini-2.5-flash"
)  # GeminiモデルID（未指定時はデフォルト）  # noqa: RUF003
R2_CUSTOM_DOMAIN = os.environ.get(
    "R2_CUSTOM_DOMAIN", "podcast.sunabalog.com"
)  # R2のカスタムドメイン（未指定時はエンドポイントURL）  # noqa: RUF003

# 環境変数の確認
logger.info("## Environment Variables ##")
logger.info("PROJECT_ID: %s", PROJECT_ID)
logger.info("SECRET_NAME: %s", SECRET_NAME)
logger.info("GCS_BUCKET: %s", GCS_BUCKET)
logger.info("GCS_TRIGGER_OBJECT_NAME: %s", GCS_TRIGGER_OBJECT_NAME)
logger.info("R2_ENDPOINT_URL: %s", R2_ENDPOINT_URL)
logger.info("R2_BUCKET: %s", R2_BUCKET)
logger.info("SUBDIRECTORY: %s", SUBDIRECTORY)
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
    logger.info("GCS Bucket: %s, File: %s", GCS_BUCKET, GCS_TRIGGER_OBJECT_NAME)
    gcs_path = Path(GCS_TRIGGER_OBJECT_NAME)
    # Mime Type 判定（タイトル等のメタデータ取得用）  # noqa: RUF003
    mime_type = mimetypes.guess_type(GCS_TRIGGER_OBJECT_NAME)[0] or "audio/x-m4a"
    logger.info("Detected mime type: %s", mime_type)
    # secret manager から R2 と Discord の認証情報を取得
    secret_manager_client = SecretManagerClient(project_id=PROJECT_ID, secret_name=SECRET_NAME)
    r2_access_key, r2_secret_key = secret_manager_client.get_r2_credentials()
    discord_webhook_url = secret_manager_client.get_discord_webhook_url()
    notifier_client = Notifier(discord_webhook_url=discord_webhook_url)

    try:
        audio_analyzer = AudioAnalyzer(project_id=PROJECT_ID)
        r2_client = R2Client(
            project_id=PROJECT_ID,
            endpoint_url=R2_ENDPOINT_URL,
            bucket_name=R2_BUCKET,
            access_key=r2_access_key,
            secret_key=r2_secret_key,
        )
        gcs_client = GCSClient(project_id=PROJECT_ID)

        # RSS feedからエピソード情報等を取得
        rss_feed = r2_client.download_file(f"{SUBDIRECTORY}/feed.xml")
        # byte -> str
        rss_feed = rss_feed.decode("utf-8")
        rss_manager = PodcastRssManager(rss_xml=rss_feed)
        latest_episode_number = rss_manager.get_total_episodes() + 1
        logger.info("Latest Episode Number: %s", latest_episode_number)

        # --- Phase 1: Fetch & Process (AI Analysis) ---
        # Vertex AIは GCS URI を直接読めるため、ダウンロード不要で分析可能
        logger.info("\n## Step1: Running AI Analysis... ##")
        transcript = audio_analyzer.generate_transcript(
            f"gs://{GCS_BUCKET}/{GCS_TRIGGER_OBJECT_NAME}", model_id=AI_MODEL_ID
        )
        if transcript:
            summary = audio_analyzer.summarize_transcript(transcript, model_id=AI_MODEL_ID)
        else:
            msg = "Failed to make transcript."
            raise ValueError(msg)
        logger.info("Generated Summary: %s", summary)
        summary.title = f"#{latest_episode_number} {summary.title}"

        # transcript と summary を保存しておくべきか
        # 保存する場合、R2 に保存するか GCS に保存するかを検討
        # 今回は保存せずWebhookで通知のみ
        notifier_client.send_discord_message(
            message=f"New Podcast Processed:\nTitle: {summary.title}\nDescription: {summary.description}"
        )

        # --- Phase 2: Upload to R2 ---
        logger.info("\n## Step2: Uploading to Cloudflare R2... ##")
        # ストリームでGCSから取得し、R2へアップロード（ローカルディスク節約）
        public_url, file_size_bytes, duration_str = transfer_gcs_to_r2(
            gcs_client=gcs_client,
            r2_client=r2_client,
            gcs_bucket_name=GCS_BUCKET,
            gcs_object_name=GCS_TRIGGER_OBJECT_NAME,
            r2_remote_key=f"{SUBDIRECTORY}/ep/{latest_episode_number}/audio{gcs_path.suffix}",
            content_type=mime_type,
            public=True,
            custom_domain=R2_CUSTOM_DOMAIN,
        )
        logger.info("Uploaded audio to R2: %s, Size: %s bytes, Duration: %s", public_url, file_size_bytes, duration_str)

        # --- Phase 3: Update RSS ---
        logger.info("\n## Updating RSS Feed... ##")
        # rss file を R2 からダウンロードし、更新して再アップロード
        new_episode_data = {
            "title": summary.title,
            "description": summary.description,
            "audio_url": public_url,
            "duration": duration_str,
            "creator": "Sunaba Log",
            "file_size": file_size_bytes,
            "mime_type": mime_type,
            "episode_type": "full",
        }
        rss_manager.add_episode(new_episode_data)
        rss_xml = rss_manager.get_rss_xml()
        rss_xml_obj = rss_xml.encode("utf-8")
        r2_client.upload_file(
            file_content=rss_xml_obj,
            remote_key=f"{SUBDIRECTORY}/feed.xml",
            content_type="application/rss+xml; charset=utf-8",
            public=True,
        )

        # --- Phase 4: Notify Success ---
        logger.info("\n## Notifying Discord (Success)... ##")
        notifier_client.send_discord_message(
            message=f"Podcast Episode Published Successfully:\nTitle: {summary.title}\nURL: {public_url}"
        )

    except Exception as e:
        logger.exception("Error occurred during podcast processing:")
        notifier_client.send_discord_message(message=f"Podcast Processing Failed:\nError: {e}")


def main() -> None:
    """Main entry point for the podcast processor."""
    for arg in sys.argv:
        logger.info("Argument: %s", arg)
    process_podcast_workflow()


if __name__ == "__main__":
    main()
