from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"

from main import format_env, print_env


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
    assert "PODCAST_AUTOMATOR_TEST=ok" in result.stdout
