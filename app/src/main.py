"""Emit environment variables as simple log lines."""

from __future__ import annotations

from collections.abc import Mapping
import os
import sys
from typing import TextIO


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


def main() -> None:
    print_env()


if __name__ == "__main__":
    main()
