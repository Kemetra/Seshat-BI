"""Spec 149 / #660 -- the bounded stdio session for the vendor MCP.

Lifecycle lives HERE, framing lives in :mod:`protocol`. That split is the shipped
``studio/codex_protocol.py`` (pure) + T021 (lifecycle) pattern, and it is what
makes every sequencing rule testable without npx.

**The stdin constraint is inverted from the old runner, deliberately.** The
pre-#660 code used ``stdin=subprocess.DEVNULL`` citing #322, where an INHERITED
stdin deadlocked a child. A stdio MCP client must write to the child's stdin, so
DEVNULL is not available -- but the #322 lesson still binds: the pipe is
DEDICATED (``stdin=PIPE``), never inherited from the parent. Those are different
things, and conflating them is what made the one-shot CLI shape look safe.

**Correlation is by request id.** The server interleaves its own log frames and
notifications with replies; resolving a call with whatever arrives next would
silently cross-wire one result onto another request.

**The server identity is checked at handshake.** ``npx`` resolves a name from a
public registry; if something else answers, refuse rather than issue writes to it.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Protocol

from seshat.pbi_mcp_adapter import protocol as proto

__all__ = [
    "DEFAULT_DEADLINE_SECONDS",
    "EXPECTED_SERVER_NAME",
    "McpSession",
    "SessionError",
    "SubprocessTransport",
    "Transport",
]

#: The server must identify as this. Probed 2026-08-20.
EXPECTED_SERVER_NAME = "powerbi-modeling-mcp"

#: Sized for a model operation, not a git command (research R4).
DEFAULT_DEADLINE_SECONDS = 900


class SessionError(RuntimeError):
    """The session could not be established or a call could not be completed."""


class Transport(Protocol):
    """The byte-level seam. A fake implements this; no process is required."""

    def write(self, data: bytes) -> None: ...

    def read_line(self) -> bytes: ...

    def terminate(self) -> None: ...

    def stderr_text(self) -> str: ...


class McpSession:
    """One handshake-then-calls conversation with the vendor server."""

    def __init__(
        self,
        transport: Transport,
        *,
        deadline_seconds: int = DEFAULT_DEADLINE_SECONDS,
    ) -> None:
        self._transport = transport
        self._deadline = deadline_seconds
        self._next_id = 1
        self._ready = False

    def _send(self, frame: dict[str, Any]) -> None:
        self._transport.write(proto.encode_frame(frame))

    def _take_id(self) -> int:
        request_id = self._next_id
        self._next_id += 1
        return request_id

    def _await_id(self, request_id: int) -> dict[str, Any]:
        """Read frames until the one matching ``request_id`` arrives.

        Unparseable lines are skipped rather than raised: the vendor writes
        human-readable log lines to the same stream in some modes, and a log line
        is not a protocol violation. A CLOSED stream is fatal -- it means the
        reply we are waiting for will never come.
        """
        started = time.monotonic()
        while True:
            if time.monotonic() - started > self._deadline:
                raise SessionError(
                    f"no reply to request {request_id} within {self._deadline}s"
                )
            line = self._transport.read_line()
            if not line:
                raise SessionError(
                    f"the vendor stream closed before replying to {request_id}"
                )
            try:
                frame = proto.decode_frame(line)
            except proto.McpFrameError:
                continue
            if frame.get("id") == request_id:
                return frame

    def handshake(self) -> dict[str, Any]:
        """``initialize`` then the required ``initialized`` notification.

        Returns the server's ``serverInfo``. Raises if the peer is not the
        expected vendor server.
        """
        request_id = self._take_id()
        self._send(proto.initialize_request(request_id))
        reply = self._await_id(request_id)
        result = reply.get("result")
        if not isinstance(result, dict):
            raise SessionError("the handshake reply carried no result")
        info = result.get("serverInfo")
        if not isinstance(info, dict):
            raise SessionError("the handshake reply named no server")
        if info.get("name") != EXPECTED_SERVER_NAME:
            raise SessionError(
                f"unexpected server identity: {info.get('name')!r} "
                f"(expected {EXPECTED_SERVER_NAME!r})"
            )
        # Required by the protocol: the server may reject calls until this lands.
        self._send(proto.initialized_notification())
        self._ready = True
        return dict(info)

    def call(self, tool: str, request: dict[str, Any]) -> proto.ToolOutcome:
        """One ``tools/call``. Refuses before a completed handshake."""
        if not self._ready:
            raise SessionError("call() before a completed handshake")
        request_id = self._take_id()
        self._send(proto.tool_call_request(request_id, tool, request))
        return proto.parse_tool_result(self._await_id(request_id))

    def close(self) -> None:
        self._transport.terminate()


class SubprocessTransport:
    """The real transport: npx over dedicated pipes.

    ``stdin=PIPE`` is required (we speak to the child) and is NOT the #322
    defect, which was an INHERITED stdin. The pipe here is ours alone.
    """

    def __init__(
        self,
        argv: list[str],
        cwd: Path,
        env: dict[str, str] | None = None,
    ) -> None:
        self._proc = subprocess.Popen(  # noqa: S603 - fixed argv shape, no shell
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )

    def write(self, data: bytes) -> None:
        if self._proc.stdin is None:  # pragma: no cover - PIPE always present
            raise SessionError("the child has no stdin pipe")
        try:
            self._proc.stdin.write(data)
            self._proc.stdin.flush()
        except OSError as exc:
            raise SessionError(f"the vendor stdin closed: {exc}") from exc

    def read_line(self) -> bytes:
        if self._proc.stdout is None:  # pragma: no cover - PIPE always present
            return b""
        return self._proc.stdout.readline()

    def terminate(self) -> None:
        """Close stdin, then terminate, then kill. Never leaks the child."""
        try:
            if self._proc.stdin and not self._proc.stdin.closed:
                self._proc.stdin.close()
        except OSError:  # pragma: no cover - best-effort teardown
            pass
        try:
            self._proc.terminate()
            self._proc.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):  # pragma: no cover
            try:
                self._proc.kill()
            except OSError:
                pass

    def stderr_text(self) -> str:
        """Whatever the child has written to stderr so far, non-blocking-ish.

        Only read after termination: reading a live pipe here would block.
        """
        if self._proc.stderr is None:  # pragma: no cover - PIPE always present
            return ""
        try:
            return self._proc.stderr.read().decode("utf-8", errors="replace")
        except (OSError, ValueError):  # pragma: no cover
            return ""
