"""Lifecycle tests over a REAL pipe.

A mocked stream cannot exhibit the pipe deadlock this design's concurrency model
risks, so these drive an actual child process. The child replays fixtures T019
derived from Codex's real generated schema -- it does not invent a shape.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SCRIPT = Path(__file__).parent / "_codex_child_script.py"
_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "codex_app_server"


def _non_blank_line_count(fixture: str) -> int:
    path = _FIXTURES / f"{fixture}.jsonl"
    return sum(
        1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


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
    expected = _non_blank_line_count("thread_turn")
    assert len(lines) == expected, (
        f"expected {expected} lines replayed, got {len(lines)}"
    )
    assert '"jsonrpc"' in lines[0]
    assert proc.returncode == 0


def test_crash_after_writes_exactly_n_lines_in_full_then_exits_1() -> None:
    proc = subprocess.Popen(
        [sys.executable, str(_SCRIPT), "thread_turn", "--crash-after", "2"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, _ = proc.communicate(timeout=30)
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) == 2, (
        f"expected exactly 2 lines to arrive, got {len(lines)} lines"
    )
    assert proc.returncode == 1


def test_hang_produces_no_output_and_keeps_running_until_terminated() -> None:
    proc = subprocess.Popen(
        [sys.executable, str(_SCRIPT), "thread_turn", "--hang"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(0.5)
        assert proc.poll() is None, "expected the hung child to still be running"
    finally:
        proc.terminate()
        out, _ = proc.communicate(timeout=10)
    assert out == "", f"expected no output before termination, got {out!r}"
    assert proc.returncode is not None
    assert proc.returncode != 0
