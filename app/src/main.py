"""Emit environment variables as structured log lines."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING

import boto3
from google.cloud import storage

if TYPE_CHECKING:
    from collections.abc import Mapping

    from botocore.client import BaseClient


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


@dataclass(frozen=True)
class TransferConfig:
    """Configuration for transferring objects from GCS to R2."""

    gcs_bucket: str
    trigger_file: str
    r2_bucket: str
    cloudflare_account_id: str
    cloudflare_access_key_id: str
    cloudflare_secret_access_key: str


def require_env(environ: Mapping[str, str], name: str) -> str:
    """Fetch a required environment variable or raise an error."""
    value = environ.get(name)
    if not value:
        message = f"Missing required environment variable: {name}"
        raise ValueError(message)
    return value


def load_transfer_config(environ: Mapping[str, str]) -> TransferConfig:
    """Load configuration for the GCS -> R2 transfer."""
    return TransferConfig(
        gcs_bucket=require_env(environ, "GCS_BUCKET"),
        trigger_file=require_env(environ, "GCS_TRIGGER_OBJECT_NAME"),
        r2_bucket=require_env(environ, "R2_BUCKET"),
        cloudflare_account_id=require_env(environ, "CLOUDFLARE_ACCOUNT_ID"),
        cloudflare_access_key_id=require_env(environ, "CLOUDFLARE_ACCESS_KEY_ID"),
        cloudflare_secret_access_key=require_env(environ, "CLOUDFLARE_SECRET_ACCESS_KEY"),
    )


def build_r2_endpoint(account_id: str) -> str:
    """Build the R2 endpoint URL from the account ID."""
    return f"https://{account_id}.r2.cloudflarestorage.com"


def create_r2_client(config: TransferConfig) -> BaseClient:
    """Create a boto3 client configured for Cloudflare R2."""
    return boto3.client(
        "s3",
        endpoint_url=build_r2_endpoint(config.cloudflare_account_id),
        aws_access_key_id=config.cloudflare_access_key_id,
        aws_secret_access_key=config.cloudflare_secret_access_key,
        region_name="auto",
    )


def transfer_gcs_to_r2(config: TransferConfig, logger: logging.Logger) -> str:
    """Stream a GCS object into the Cloudflare R2 bucket."""
    gcs_client = storage.Client()
    r2_client = create_r2_client(config)

    bucket = gcs_client.bucket(config.gcs_bucket)
    blob = bucket.blob(config.trigger_file)
    if not blob.exists():
        message = f"GCS object not found: gs://{config.gcs_bucket}/{config.trigger_file}"
        raise FileNotFoundError(message)

    blob.reload()
    content_type = blob.content_type

    r2_key = config.trigger_file
    extra_args = {"ContentType": content_type} if content_type else None

    with blob.open("rb") as gcs_stream:
        r2_client.upload_fileobj(gcs_stream, config.r2_bucket, r2_key, ExtraArgs=extra_args)

    return r2_key


def main() -> None:
    """Log the current environment to stdout."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)
    logger = logging.getLogger(__name__)
    send_discord_notification("podcast-automator: execution started")

    try:
        config = load_transfer_config(os.environ)
        transfer_gcs_to_r2(config, logger)
    except Exception as exc:
        logger.exception("GCS to R2 transfer failed")
        error_webhook = os.environ.get("DISCORD_WEBHOOK_ERROR_URL")
        send_discord_notification(f"podcast-automator: execution failed: {exc}", webhook_url=error_webhook)
        raise SystemExit(1) from exc

    send_discord_notification("podcast-automator: execution completed")


if __name__ == "__main__":
    main()
