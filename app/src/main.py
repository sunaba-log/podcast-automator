"""Emit environment variables as structured log lines."""

from __future__ import annotations

import json
import logging
import os
import sys
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
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    log_env()
    log_trigger_file()


if __name__ == "__main__":
    main()
