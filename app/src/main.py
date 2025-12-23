"""Emit environment variables as structured log lines."""

from __future__ import annotations

import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from collections.abc import Mapping


def format_env(environ: Mapping[str, str]) -> list[str]:
    """Return sorted KEY=VALUE lines for the given environment mapping."""
    return [f"{key}={value}" for key, value in sorted(environ.items())]


def print_env(
    environ: Mapping[str, str] | None = None,
    stream: TextIO | None = None,
) -> None:
    """Print the environment to the given stream (defaults to stdout)."""
    if environ is None:
        environ = os.environ
    if stream is None:
        stream = sys.stdout

    for line in format_env(environ):
        print(line, file=stream)


def log_env(
    environ: Mapping[str, str] | None = None,
    logger: logging.Logger | None = None,
) -> None:
    """Log the environment with structured JSON lines."""
    if environ is None:
        environ = os.environ
    if logger is None:
        logger = logging.getLogger(__name__)

    for key, value in sorted(environ.items()):
        payload = {
            "event": "environment_variable",
            "key": key,
            "value": value,
        }
        logger.info("%s", json.dumps(payload, ensure_ascii=True))


def send_discord_notification(
    message: str,
    environ: Mapping[str, str] | None = None,
    logger: logging.Logger | None = None,
) -> None:
    """Send a message to Discord via webhook if configured."""
    if environ is None:
        environ = os.environ
    if logger is None:
        logger = logging.getLogger(__name__)

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
        except Exception:
            body = ""
        detail = body.strip() or str(exc.reason)
        logger.error("Discord webhook returned HTTP %s: %s", exc.code, detail)
    except Exception:
        logger.exception("Failed to send Discord notification")


def log_trigger_file(
    environ: Mapping[str, str] | None = None,
    logger: logging.Logger | None = None,
) -> None:
    """Log the trigger file name if present in the environment."""
    if environ is None:
        environ = os.environ
    if logger is None:
        logger = logging.getLogger(__name__)

    trigger_file = environ.get("TRIGGER_FILE")
    if not trigger_file:
        return

    payload = {
        "event": "trigger_file",
        "name": trigger_file,
    }
    logger.info("%s", json.dumps(payload, ensure_ascii=True))


def main() -> None:
    """Log the current environment to stdout."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)
    send_discord_notification("podcast-automator: execution started")
    log_env()
    log_trigger_file()
    send_discord_notification("podcast-automator: execution completed")


if __name__ == "__main__":
    main()
