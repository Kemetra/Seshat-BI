"""Spec 149 / #660 -- session lifecycle against a FAKE transport.

No npx, no tenant, no network. The fake replays frames captured from the real
server so the sequencing rules are pinned without a live run.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import protocol, session

pytestmark = pytest.mark.unit


class FakeTransport:
    """Records what we wrote; replays scripted replies."""

    def __init__(self, replies: list[dict] | None = None, *, noise: bool = False):
        self.written: list[dict] = []
        self.terminated = False
        frames: list[bytes] = []
        for reply in replies or []:
            if noise:
                # The real server interleaves human-readable log lines.
                frames.append(b"info: PowerBIModelingMCP starting up\n")
            frames.append(protocol.encode_frame(reply))
        self._frames = frames

    def write(self, data: bytes) -> None:
        self.written.append(json.loads(data.decode("utf-8")))

    def read_line(self) -> bytes:
        if not self._frames:
            return b""
        return self._frames.pop(0)

    def terminate(self) -> None:
        self.terminated = True

    def stderr_text(self) -> str:
        return "[INFO] Authentication mode: InteractiveBrowser"


def _init_reply(request_id: int = 1, name: str = "powerbi-modeling-mcp") -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {"listChanged": True}},
            "serverInfo": {"name": name, "version": "0.5.0.0"},
        },
    }


def _ok_reply(request_id: int, message: str, read_only: bool = True) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [{"type": "text", "text": json.dumps({"message": message})}],
            "isError": False,
            "_meta": {"annotations": {"readOnlyHint": read_only}},
        },
    }


def _child_env() -> dict[str, str]:
    """The ambient environment, explicitly.

    These children are `sys.executable` running a local script -- not the vendor
    -- so they need a working Python environment rather than the vendor
    allowlist. `SubprocessTransport` requires `env` precisely so that choice is
    stated at the call site instead of defaulting to an inherit (#658).
    """
    return dict(os.environ)


def test_handshake_sends_initialize_then_the_initialized_notification():
    transport = FakeTransport([_init_reply()])
    sess = session.McpSession(transport)
    info = sess.handshake()
    assert info["name"] == "powerbi-modeling-mcp"
    assert info["version"] == "0.5.0.0"
    methods = [frame.get("method") for frame in transport.written]
    assert methods == ["initialize", "notifications/initialized"]


def test_call_before_handshake_is_refused():
    sess = session.McpSession(FakeTransport())
    with pytest.raises(session.SessionError):
        sess.call("measure_operations", {"operation": "List"})


def test_call_correlates_on_request_id_not_arrival_order():
    """An out-of-order reply must not resolve the wrong call."""
    transport = FakeTransport(
        [_init_reply(), _ok_reply(99, "stale"), _ok_reply(2, "the real one")]
    )
    sess = session.McpSession(transport)
    sess.handshake()
    outcome = sess.call("measure_operations", {"operation": "List"})
    assert outcome.payload is not None
    assert outcome.payload["message"] == "the real one"


def test_non_protocol_log_lines_are_skipped_not_fatal():
    transport = FakeTransport([_init_reply(), _ok_reply(2, "fine")], noise=True)
    sess = session.McpSession(transport)
    sess.handshake()
    outcome = sess.call("measure_operations", {"operation": "List"})
    assert outcome.ok is True


def test_a_closed_stream_before_a_reply_raises_rather_than_hanging():
    transport = FakeTransport([_init_reply()])
    sess = session.McpSession(transport)
    sess.handshake()
    with pytest.raises(session.SessionError):
        sess.call("measure_operations", {"operation": "List"})


def test_handshake_rejects_a_server_that_names_itself_differently():
    transport = FakeTransport([_init_reply(name="not-the-vendor")])
    sess = session.McpSession(transport)
    with pytest.raises(session.SessionError):
        sess.handshake()


def test_handshake_rejects_a_reply_with_no_server_info():
    bad = _init_reply()
    del bad["result"]["serverInfo"]
    sess = session.McpSession(FakeTransport([bad]))
    with pytest.raises(session.SessionError):
        sess.handshake()


def test_request_ids_are_unique_across_calls():
    transport = FakeTransport([_init_reply(), _ok_reply(2, "a"), _ok_reply(3, "b")])
    sess = session.McpSession(transport)
    sess.handshake()
    sess.call("measure_operations", {"operation": "List"})
    sess.call("table_operations", {"operation": "List"})
    ids = [f["id"] for f in transport.written if "id" in f]
    assert ids == sorted(set(ids))


def test_close_terminates_the_transport():
    transport = FakeTransport([_init_reply()])
    sess = session.McpSession(transport)
    sess.handshake()
    sess.close()
    assert transport.terminated is True


def test_a_deadline_of_zero_raises_the_STALLED_type_not_the_base():
    """The bound is real -- AND its type carries the cause (review M2).

    Asserting `SessionError` here could not distinguish a stall from a crash, so
    reverting both timeout sites to the base class left every test green while the
    runner reported a timeout as "failed without naming a cause".
    """
    transport = FakeTransport([_init_reply()])
    sess = session.McpSession(transport, deadline_seconds=0)
    with pytest.raises(session.SessionStalled):
        sess.handshake()


def test_a_closed_stream_raises_the_BASE_type_not_stalled():
    """The other side of M2: a crash must NOT be reported as a timeout."""
    transport = FakeTransport([_init_reply()])
    sess = session.McpSession(transport)
    sess.handshake()
    with pytest.raises(session.SessionError) as caught:
        sess.call("measure_operations", {"operation": "List"})
    assert not isinstance(caught.value, session.SessionStalled)


def test_an_impostor_server_raises_the_BASE_type_not_stalled():
    transport = FakeTransport([_init_reply(name="evil-impostor")])
    sess = session.McpSession(transport)
    with pytest.raises(session.SessionError) as caught:
        sess.handshake()
    assert not isinstance(caught.value, session.SessionStalled)


def test_the_transport_read_timeout_also_raises_STALLED(tmp_path: Path) -> None:
    """Both timeout sites, not just the session one (review M2)."""
    child = tmp_path / "silent.py"
    child.write_text(chr(10).join(["import time", "time.sleep(60)"]), encoding="utf-8")
    transport = session.SubprocessTransport(
        [sys.executable, "-u", str(child)], tmp_path, _child_env(), read_timeout=2
    )
    try:
        with pytest.raises(session.SessionStalled):
            transport.read_line()
    finally:
        transport.terminate()


# --------------------------------------------------------------------------
# Launcher resolution -- found by running the SHIPPED runner for real
# --------------------------------------------------------------------------


def test_the_launcher_is_resolved_to_an_absolute_path():
    """`npx` on Windows is `npx.cmd`, and Popen(shell=False) ignores PATHEXT.

    Every real run failed with BLOCKER_RUNTIME_MISSING while 444 unit tests
    passed, because they all inject a session factory and never execute the argv.
    """
    import shutil

    resolved = session.resolve_launcher(["git", "--version"])
    assert resolved[0] == shutil.which("git")
    assert resolved[0] != "git", "argv[0] was not resolved"
    assert resolved[1:] == ["--version"], "the arguments must be preserved"


def test_an_unresolvable_launcher_passes_through_unchanged():
    """So the failure surfaces as a typed RunResult, not a constructor raise."""
    argv = ["definitely-not-a-real-binary-xyz", "--flag"]
    assert session.resolve_launcher(argv) == argv


def test_resolve_launcher_tolerates_an_empty_argv():
    assert session.resolve_launcher([]) == []


def test_the_stdout_queue_is_bounded():
    """An unbounded queue fed by a chatty server is a memory-exhaustion path."""
    assert isinstance(session.MAX_QUEUED_LINES, int)
    assert 0 < session.MAX_QUEUED_LINES <= 100_000


def test_a_full_queue_cannot_deadlock_teardown(tmp_path: Path) -> None:
    """The bound must not trade a memory risk for a hang.

    The pump thread blocks on ``put()`` once the queue is full. Teardown must
    still complete, or a server that outruns the reader hangs the process for
    ever. Driven with a REAL subprocess that emits far more lines than the bound,
    of which we read only a handful -- so the queue is genuinely full and the pump
    is genuinely blocked when ``terminate()`` is called.
    """
    child = tmp_path / "flood.py"
    lines = [
        "import json",
        "import sys",
        "import time",
        f"for i in range({session.MAX_QUEUED_LINES * 3}):",
        '    sys.stdout.write(json.dumps({"id": i}) + "\\n")',
        "sys.stdout.flush()",
        "time.sleep(30)",
    ]
    child.write_text("\n".join(lines) + "\n", encoding="utf-8")
    transport = session.SubprocessTransport(
        [sys.executable, "-u", str(child)], tmp_path, _child_env(), read_timeout=10
    )
    try:
        for _ in range(5):
            transport.read_line()
        time.sleep(2)  # let the pump fill the queue and block on put()

        started = time.monotonic()
        transport.terminate()
        assert time.monotonic() - started < 20, "terminate() blocked on a full queue"

        # A read after teardown must not hang either.
        started = time.monotonic()
        try:
            transport.read_line()
        except session.SessionStalled:
            pass
        assert time.monotonic() - started < 15, "read_line() hung after terminate()"
    finally:
        transport.terminate()


def test_the_pump_threads_are_daemons(tmp_path: Path) -> None:
    """A non-daemon pump blocked on a full queue would prevent interpreter exit."""
    child = tmp_path / "quiet.py"
    child.write_text(
        "\n".join(["import time", "time.sleep(5)"]) + "\n", encoding="utf-8"
    )
    transport = session.SubprocessTransport(
        [sys.executable, "-u", str(child)], tmp_path, _child_env(), read_timeout=1
    )
    try:
        assert transport._readers, "no pump threads were started"
        for reader in transport._readers:
            assert reader.daemon is True
    finally:
        transport.terminate()
