"""Gate-command execution: the SAME commands CI runs, as child processes.

Closed argv, no shell (Principle IX posture shared with the spec-133 runner).
Output is redacted before anyone sees or records it. This module is the
monkeypatch seam the in-process tests use to force gate exits.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from seshat.dagster_adapter.redaction import redact_and_tail

_TAIL_CHARS = 2000


def checker_argv() -> list[str]:
    """The static governance gate -- identical to CI's ``seshat check``."""
    return [sys.executable, "-m", "seshat.cli", "check"]


def semantic_argv() -> list[str]:
    """The complete contract-to-TMDL binding gate."""
    return [
        sys.executable,
        "-m",
        "seshat.cli",
        "semantic-check",
        "--repo",
        ".",
        "--metrics-dir",
        "mappings",
    ]


def validate_argv(table: str) -> list[str]:
    """The live validation gate -- identical to CI's ``seshat validate``."""
    return [
        sys.executable,
        "-m",
        "seshat.cli",
        "validate",
        "--source-map",
        f"mappings/{table}/source-map.yaml",
    ]


def run_gate_command(argv: list[str], cwd: Path) -> tuple[int, str]:
    """Run one gate command; return (exit_code, redacted output tail)."""
    proc = subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        # Force UTF-8 decoding of the child's output instead of the platform
        # default (cp1252 on Windows). Gate output echoes redacted findings that
        # can contain non-Latin-1 governed values (e.g. Arabic `billing_type`);
        # `text=True` alone decodes via locale.getpreferredencoding() and crashes
        # the reader thread with UnicodeDecodeError on Windows (#404).
        encoding="utf-8",
        errors="replace",
        timeout=1800,
    )
    combined = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, redact_and_tail(combined, _TAIL_CHARS)
