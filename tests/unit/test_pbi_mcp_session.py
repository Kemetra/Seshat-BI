"""Spec 149 / #660 -- session lifecycle against a FAKE transport.

No npx, no tenant, no network. The fake replays frames captured from the real
server so the sequencing rules are pinned without a live run.
"""

from __future__ import annotations

import json

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


def test_a_deadline_of_zero_raises_instead_of_looping_forever():
    """The bound is real: a server that never replies must not hang the run."""
    transport = FakeTransport([_init_reply()])
    sess = session.McpSession(transport, deadline_seconds=0)
    with pytest.raises(session.SessionError):
        sess.handshake()
