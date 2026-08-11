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

from seshat.studio.codex_process import CodexLaunchPlan

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


def _plan(tmp_path: Path, fixture: str, *extra: str) -> CodexLaunchPlan:
    return CodexLaunchPlan(
        argv=(sys.executable, str(_SCRIPT), fixture, *extra), cwd=tmp_path
    )


def test_a_session_reads_every_frame_then_sees_eof(tmp_path: Path) -> None:
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(_plan(tmp_path, "thread_turn"))
    session.start()
    try:
        frames = list(session.frames())
    finally:
        session.close()

    assert frames, "no frames were read from the child"
    assert all(frame.get("jsonrpc") == "2.0" for frame in frames)


def test_a_session_never_inherits_a_handle(tmp_path: Path) -> None:
    """Issue #557: an inherited stdin under `seshat mcp` is the client's live pipe."""
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(_plan(tmp_path, "handshake"))
    assert session.plan.inherits_any_handle is False


def test_closing_a_hung_child_does_not_block_forever(tmp_path: Path) -> None:
    """The deadlock shape: a child that never writes must not wedge shutdown."""
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(_plan(tmp_path, "handshake", "--hang"))
    session.start()
    returncode = session.close(timeout=5.0)

    assert session.is_running is False
    assert returncode is not None


#: A credential-shaped string the child writes verbatim to stderr, so the test
#: drives the actual risk instead of asserting an absence that would pass even
#: if nothing arrived at all.
_STDERR_SECRET_LINE = "Incorrect API key provided: sk-live-ABCDEFGH12345678"


def test_stderr_is_redacted_before_retention(tmp_path: Path) -> None:
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(
        _plan(tmp_path, "handshake", "--stderr", _STDERR_SECRET_LINE)
    )
    session.start()
    try:
        # Draining to stdout EOF is the synchronization point: it guarantees the
        # child has run to completion (and therefore flushed its one stderr line)
        # before close() tears the pipes down. Without this, close() can race the
        # child's own scheduling and observe no stderr at all -- a different
        # vacuous-pass shape than finding A, not a property of the guard.
        list(session.frames())
    finally:
        session.close()

    stderr_text = session.stderr_text()
    assert "sk-live-ABCDEFGH12345678" not in stderr_text
    assert "<redacted>" in stderr_text
    assert "Incorrect API key provided" in stderr_text


def test_disabling_the_redaction_guard_lets_the_raw_secret_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proves the guard -- not luck -- is what redacts stderr.

    If this test did not observe the raw secret with the guard disabled, the
    positive test above would be passing for the wrong reason.
    """
    import seshat.studio.codex_bridge as codex_bridge

    monkeypatch.setattr(codex_bridge, "redact_provider_stderr", lambda raw, **kw: raw)

    session = codex_bridge.CodexSession(
        _plan(tmp_path, "handshake", "--stderr", _STDERR_SECRET_LINE)
    )
    session.start()
    try:
        list(session.frames())
    finally:
        session.close()

    assert "sk-live-ABCDEFGH12345678" in session.stderr_text()
