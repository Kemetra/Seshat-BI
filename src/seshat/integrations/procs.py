"""Subprocess running and output shaping for the integration installer."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        command, cwd=cwd, text=True, capture_output=True, check=False
    )


def _detail(result: subprocess.CompletedProcess, fallback: str) -> str:
    return (result.stderr or result.stdout or "").strip() or fallback
