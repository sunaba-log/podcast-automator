from __future__ import annotations

import io
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from main import format_env, log_trigger_file, print_env

SRC_DIR = Path(__file__).resolve().parents[1] / "src"


def test_format_env_sorts() -> None:
    lines = format_env({"B": "2", "A": "1"})
    assert lines == ["A=1", "B=2"]


def test_print_env_writes_lines() -> None:
    buf = io.StringIO()
    print_env({"B": "2", "A": "1"}, stream=buf)
    assert buf.getvalue() == "A=1\nB=2\n"


def test_main_outputs_env() -> None:
    env = os.environ.copy()
    env["PODCAST_AUTOMATOR_TEST"] = "ok"
    result = subprocess.run(
        [sys.executable, str(SRC_DIR / "main.py")],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    payloads = [
        json.loads(line)
        for line in result.stderr.splitlines()
        if line.strip()
    ]
    assert {
        "event": "environment_variable",
        "key": "PODCAST_AUTOMATOR_TEST",
        "value": "ok",
    } in payloads


def test_log_trigger_file_emits_json_line() -> None:
    env = {"TRIGGER_FILE": "uploads/test.mp3"}
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("test_trigger_file")
    logger.setLevel(logging.INFO)
    logger.handlers = [handler]
    logger.propagate = False

    log_trigger_file(env, logger=logger)

    handler.flush()
    payload = json.loads(stream.getvalue().strip())
    assert payload["event"] == "trigger_file"
    assert payload["name"] == "uploads/test.mp3"
