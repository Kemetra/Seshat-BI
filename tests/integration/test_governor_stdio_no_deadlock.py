"""Regression guard for issue #557: the governor must answer over a real pipe.

WHY THIS TEST SPAWNS A SUBPROCESS INSTEAD OF CALLING THE SERVICE
----------------------------------------------------------------
The #557 deadlock is invisible in-process. ``GovernorService.call(
"seshat_run_static_check", ...)`` returns in ~0.2s under pytest, while the same
operation over stdio hung indefinitely (>11 minutes observed) in the shipped
v0.8.0 plugin.

The bug lives in the relationship between the parent's stdin and the child's:
``subprocess.run`` without an explicit ``stdin`` gives the child the PARENT's
stdin. For ``seshat mcp`` that handle is the live JSON-RPC pipe from the client.
``git`` inherits it and blocks on it; the parent blocks in ``communicate()``
waiting for ``git``; the pipe can only be fed by the MCP client, which is itself
waiting for the response. Deadlock.

So the oracle has to BE the pipe. A test that asserts ``stdin=DEVNULL`` was
passed would pass against a future refactor that reintroduces the hang by another
route, and a test that calls the service directly never had stdin wired to a pipe
at all. This test drives the real server the way a real client does and asserts a
response ARRIVES -- the only property that actually failed.

``seshat_run_static_check`` is the specific tool that hung, because it is the only
governor tool that shells out to git (``runner._git_ls_files``). ``seshat_get_status``
is included as the control: it never hung, so if BOTH time out the failure is the
harness, not a regression.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Generous next to the sub-second real answer, short next to the >11 min hang.
# A regression fails this in seconds rather than hanging CI until its job cap.
_RESPONSE_TIMEOUT_S = 60

pytestmark = pytest.mark.integration

mcp = pytest.importorskip("mcp", reason="governor stdio server requires the mcp extra")


def _read_line(stream: object, seconds: int) -> bytes | None:
    """Read one line, returning None on timeout instead of blocking forever.

    A plain ``readline()`` is exactly what deadlocks, so the read itself must be
    bounded: the daemon thread is abandoned on timeout and dies with the process.
    """
    box: dict[str, bytes] = {}

    def _target() -> None:
        box["line"] = stream.readline()  # type: ignore[attr-defined]

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(seconds)
    return box.get("line")


def _serve() -> subprocess.Popen:
    """Start the real stdio server in a child process, stdin wired to a pipe."""
    script = (
        "from seshat.governor.mcp_server import run_stdio\n"
        f"run_stdio({str(REPO_ROOT)!r})\n"
    )
    return subprocess.Popen(
        [sys.executable, "-c", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )


def _send(proc: subprocess.Popen, message: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write((json.dumps(message) + "\n").encode())
    proc.stdin.flush()


@pytest.mark.parametrize(
    "tool",
    [
        pytest.param("seshat_run_static_check", id="shells-out-to-git"),
        pytest.param("seshat_get_status", id="control-never-hung"),
    ],
)
def test_governor_tool_answers_over_stdio(tool: str) -> None:
    """Every governor tool must return a response over a real JSON-RPC pipe."""
    proc = _serve()
    try:
        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "regression-557", "version": "1"},
                },
            },
        )
        handshake = _read_line(proc.stdout, _RESPONSE_TIMEOUT_S)
        assert handshake, "server did not complete the MCP initialize handshake"

        _send(
            proc,
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        )
        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool,
                    "arguments": {"workspace": str(REPO_ROOT)},
                },
            },
        )

        response = _read_line(proc.stdout, _RESPONSE_TIMEOUT_S)
        assert response is not None, (
            f"{tool} produced no response within {_RESPONSE_TIMEOUT_S}s over stdio "
            "-- the issue #557 deadlock is back. A subprocess started by this tool "
            "is inheriting the server's stdin (the JSON-RPC pipe); route it through "
            "seshat.gitutil.run_subprocess, which sets stdin=DEVNULL."
        )
        payload = json.loads(response)
        assert payload.get("id") == 2, f"unexpected frame on the wire: {payload!r}"
        assert "result" in payload, f"{tool} returned an error frame: {payload!r}"
    finally:
        proc.kill()
        proc.wait(timeout=30)
