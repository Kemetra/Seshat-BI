"""Lifecycle tests over a REAL pipe.

A mocked stream cannot exhibit the pipe deadlock this design's concurrency model
risks, so these drive an actual child process. The child replays fixtures T019
derived from Codex's real generated schema -- it does not invent a shape.
"""

from __future__ import annotations

import itertools
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


def test_stderr_survives_close_once_the_child_has_actually_run(
    tmp_path: Path,
) -> None:
    """close() must not discard stderr the child already wrote.

    That is the literal, satisfiable claim: once the child has produced
    output, close() preserves it. It is a NARROWER claim than "close() right
    after start() always preserves stderr" -- that stronger form is not
    satisfiable at all, because `terminate()` on Windows is `TerminateProcess`,
    a hard kill with no graceful equivalent. Killing a child before the OS
    schedules it prevents it from ever writing anything; no synchronization
    primitive in the CALLER can recover a write that never happened, because
    there is nothing to observe. Verified directly: `_process.poll()` reads
    `None` (not yet exited) immediately after `start()`, and forcing an
    immediate `close()` at that instant with no wait produces returncode 1
    (killed) and zero bytes of stderr, on every run -- not a race, a
    deterministic consequence of killing an unscheduled process.

    So this test waits on `_process.wait()` -- a real, observed exit, the
    same primitive `close()` itself would use -- before calling `close()`,
    exactly as Finding C's own rationale states ("close() must not discard
    stderr the child ALREADY WROTE"). What close() then guarantees
    unconditionally is proven by the mechanism inside it: the stderr reader
    thread signals a `threading.Event` the instant its read loop ends via a
    real EOF, and close() waits on that event (bounded by its own deadline)
    before it closes the stderr stream -- so once the child has run, its
    output cannot be lost to a stream-close race.
    """
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(
        _plan(tmp_path, "handshake", "--stderr", _STDERR_SECRET_LINE)
    )
    session.start()
    assert session._process is not None
    session._process.wait(timeout=10)  # real, observed exit -- not a sleep
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
    assert session._process is not None
    session._process.wait(timeout=10)
    session.close()

    assert "sk-live-ABCDEFGH12345678" in session.stderr_text()


def test_close_bounds_the_whole_call_against_the_caller_timeout(
    tmp_path: Path,
) -> None:
    """A tight timeout on a hung child must not silently cost more than asked.

    Round 2's close() spent a fixed grace unconditionally before consulting
    the caller's timeout at all, so close(timeout=0.1) took over a second.
    This asserts the fix: the whole call is bounded by ONE deadline derived
    from `timeout`, so a small timeout keeps the call small.
    """
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(_plan(tmp_path, "handshake", "--hang"))
    session.start()

    started = time.monotonic()
    session.close(timeout=0.1)
    elapsed = time.monotonic() - started

    assert elapsed < 1.0, (
        f"close(timeout=0.1) took {elapsed:.3f}s, expected well under 1s"
    )


def test_a_crashed_child_reports_an_eof_health_state(tmp_path: Path) -> None:
    """A crash must not read as a healthy session with a short answer.

    The dangerous failure is silent success: a child that dies mid-turn has
    delivered a TRUNCATED answer, and reporting `ready` would let Studio present
    it as complete. Health is classified from the child's exit status, so a
    non-zero (or signalled) exit becomes `saw_eof` and lands on `crashed`.
    """
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(_plan(tmp_path, "thread_turn", "--crash-after", "2"))
    session.start()
    list(session.frames())
    session.close()

    health = session.health("0.147.0", signed_in=True)

    assert health.state != "ready", "a crashed child was reported as ready"
    assert health.state == "crashed"
    assert health.provider in {"codex", "disabled"}


def test_a_clean_exit_is_not_reported_as_a_crash(tmp_path: Path) -> None:
    """The discriminator: an INTENTIONAL shutdown must NOT read `crashed`.

    Without this, `health()` could return `crashed` unconditionally and the test
    above would still pass -- the same shape of vacuous pass that hid the dead
    stderr regex.

    Uses `--stay-open`, i.e. a server that is still running when we stop it. The
    first version drove the ordinary fixture child, which EXITS 0 once its script
    runs out -- and the #617 review established that for a long-lived app-server a
    self-exit mid-session is a failure, not a clean finish. So that child modelled
    the fake's behaviour rather than the provider's, and the "clean exit" it
    asserted on was really an unexpected one. The genuine non-crash case is a
    server WE shut down.
    """
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(_plan(tmp_path, "thread_turn", "--stay-open"))
    session.start()
    list(itertools.islice(session.frames(), 5))
    session.close()

    health = session.health("0.147.0", signed_in=True)

    assert health.state != "crashed", "an intentional shutdown was reported as a crash"


def test_a_clean_self_exit_before_shutdown_is_not_healthy(tmp_path: Path) -> None:
    """P2 (#617 review): the app-server is long-lived and never finishes on its own.

    So a status of 0 observed BEFORE anyone asked for shutdown does not mean "all
    fine" -- it means the provider went away mid-session and no further turn is
    possible. Reporting `ready` there is exactly the silent success `health()`
    exists to prevent, and `poll() not in (None, 0)` used to do just that.

    The scripted child exits 0 once its fixture is exhausted, which models this
    precisely: read every frame, then ask for health WITHOUT calling close().
    """
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(_plan(tmp_path, "thread_turn"))
    session.start()
    list(session.frames())
    session._process.wait(timeout=10)  # observe the exit without requesting one

    health = session.health("0.147.0", signed_in=True)

    assert health.state != "ready", "a provider that quit mid-session read as ready"
    assert health.state == "crashed"

    session.close()


def test_an_unstarted_session_is_not_reported_as_healthy(tmp_path: Path) -> None:
    """P2 (#617 review): `_process is None` is not the same as "running fine".

    Before `start()` -- or after a `Popen` failure -- there is no process at all.
    `poll()` and "never spawned" both look like `None`, and treating them alike
    reported a session that cannot serve a single turn as `healthy`.
    """
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(_plan(tmp_path, "thread_turn"))  # never started

    assert session.is_running is False
    assert session.health("0.147.0", signed_in=True).state != "ready"
    assert session.health("0.147.0", signed_in=True).state != "healthy"
