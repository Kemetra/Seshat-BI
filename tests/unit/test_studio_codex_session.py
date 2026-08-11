"""Lifecycle tests over a REAL pipe.

A mocked stream cannot exhibit the pipe deadlock this design's concurrency model
risks, so these drive an actual child process. The child replays fixtures T019
derived from Codex's real generated schema -- it does not invent a shape.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SCRIPT = Path(__file__).parent / "_codex_child_script.py"


def test_the_scripted_child_emits_fixture_lines_over_a_real_pipe() -> None:
    proc = subprocess.Popen(
        [sys.executable, str(_SCRIPT), "thread_turn"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, _ = proc.communicate(timeout=30)
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) >= 5, f"expected the fixture replayed, got {len(lines)} lines"
    assert '"jsonrpc"' in lines[0]
    assert proc.returncode == 0
