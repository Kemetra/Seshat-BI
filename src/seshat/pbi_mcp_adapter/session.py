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

import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Protocol

from seshat.pbi_mcp_adapter import protocol as proto

__all__ = [
    "DEFAULT_DEADLINE_SECONDS",
    "EXPECTED_SERVER_NAME",
    "McpSession",
    "SessionError",
    "SessionStalled",
    "SubprocessTransport",
    "Transport",
    "resolve_launcher",
]

#: The server must identify as this. Probed 2026-08-20.
EXPECTED_SERVER_NAME = "powerbi-modeling-mcp"

#: Sized for a model operation, not a git command (research R4).
DEFAULT_DEADLINE_SECONDS = 900

#: Ceiling on undrained stdout lines. Bounds memory against a chatty server
#: without truncating anything: a full queue back-pressures the reader.
MAX_QUEUED_LINES = 4096

#: Ceiling on ``tools/list`` pages. The vendor exposes 21 tools on one page.
MAX_TOOL_PAGES = 20


class SessionError(RuntimeError):
    """The session could not be established or a call could not be completed."""


class SessionStalled(SessionError):
    """The vendor produced no reply within the deadline.

    A DISTINCT type rather than a message the caller string-matches: a stall is
    indeterminate (the artifact may be half-written, exit 124), while a closed
    stream or a refused handshake is a different cause that must not be reported
    as "did not finish within 900s and was killed" (review M2). Classifying on
    substrings would let a reworded message silently change governance behaviour.
    """


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
            # `>=`, not `>`: a deadline of 0 means "do not wait", so ZERO elapsed
            # is already spent. With `>` the first iteration fell through to a
            # read, and a caller asking not to wait got an unbounded one. That
            # also made the covering test a race on clock granularity -- on
            # Windows two consecutive `monotonic()` reads return the same value
            # about 44% of the time, so it failed in CI and passed on Linux
            # (#698).
            if time.monotonic() - started >= self._deadline:
                # SessionStalled, not a bare SessionError: this IS a timeout, and
                # the caller distinguishes the two by TYPE. Raising the base class
                # here reported a stall as "failed without naming a cause"
                # (re-review M2, the half that remained open).
                raise SessionStalled(
                    f"no reply to request {request_id} within {self._deadline}s"
                )
            line = self._transport.read_line()
            if not line:
                raise SessionError(
                    f"the vendor stream closed before replying to {request_id}"
                )
            try:
                frame = proto.decode_frame(line)
            except proto.McpFrameTooLarge as exc:
                # Fail FAST. This may be the reply we are waiting for; skipping
                # it would wait out the deadline and report a stall for a call
                # that completed.
                raise SessionError(
                    f"a vendor frame exceeded the limit while awaiting "
                    f"{request_id}: {exc}"
                ) from exc
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

    def list_tools(self) -> tuple[str, ...]:
        """Every tool the server EXPOSES, sorted, across all listing pages.

        The handshake's ``serverInfo.name`` is a string the peer asserts about
        itself; this is what it actually offers, which the runner compares with
        the characterized set before binding anything. Bounded to
        :data:`MAX_TOOL_PAGES` so a cursor that never ends cannot loop forever.
        """
        if not self._ready:
            raise SessionError("list_tools() before a completed handshake")
        names: list[str] = []
        cursor: str | None = None
        for _page in range(MAX_TOOL_PAGES):
            request_id = self._take_id()
            self._send(proto.tools_list_request(request_id, cursor))
            try:
                page, cursor = proto.parse_tool_names(self._await_id(request_id))
            except proto.McpFrameError as exc:
                raise SessionError(f"unreadable tools/list reply: {exc}") from exc
            names.extend(page)
            if cursor is None:
                return tuple(sorted(names))
        raise SessionError(f"tools/list did not end within {MAX_TOOL_PAGES} pages")

    def close(self) -> None:
        self._transport.terminate()


def resolve_launcher(argv: list[str]) -> list[str]:
    """Resolve argv[0] to an absolute executable, or leave it for Popen to fail on.

    ``npx`` on Windows is ``npx.cmd``, and ``Popen`` with ``shell=False`` does NOT
    apply PATHEXT -- so a hardcoded ``"npx"`` raises FileNotFoundError and every
    real run reported "the vendor runtime could not be launched". Hardcoding
    ``npx.cmd`` would then break POSIX, so resolution is delegated to
    :func:`shutil.which`, the pattern already used in ``integrations/installer``.

    Found by running the SHIPPED runner against the real vendor: all 444 unit
    tests inject a session factory, so none of them ever executes this argv.

    An unresolvable name is returned UNCHANGED rather than raising here, so the
    failure surfaces as the runner's typed ``BLOCKER_RUNTIME_MISSING`` result
    instead of an exception from a constructor.
    """
    if not argv:  # pragma: no cover - build_argv never returns empty
        return argv
    resolved = shutil.which(argv[0])
    return [resolved, *argv[1:]] if resolved else argv


class SubprocessTransport:
    """The real transport: npx over dedicated pipes, with a REAL read deadline.

    ``stdin=PIPE`` is required (we speak to the child) and is NOT the #322
    defect, which was an INHERITED stdin. The pipe here is ours alone.

    Three properties this class exists to guarantee, each a review finding
    (issue #660 review, H2/H3/H5):

    **The deadline binds even when the server says nothing.** A naive
    ``readline()`` under a "check the clock, then block" loop bounds a *chatty*
    server and not a *silent* one -- the case that actually matters. Reads
    therefore happen on a daemon thread feeding a queue, and ``read_line`` waits
    on the QUEUE with a timeout. A hung vendor now raises instead of hanging the
    process, which is what makes ``runner``'s "a run with no bound can hang
    forever" docstring true rather than aspirational.

    **Stderr is drained continuously.** The vendor is chatty there (auth mode,
    ``ConnectionName=``, ``IsWrite=``). With ``stderr=PIPE`` and no reader, the
    child blocks writing once the ~64KB buffer fills, while we block reading
    stdout -- a deadlock with no timeout to break it. A second daemon thread
    drains it into a bounded buffer.

    **Every OS-level failure becomes a SessionError.** A raw ``OSError`` escaping
    a read reached ``invoke``'s caller as a traceback, so no ``RunResult`` was
    built and orchestrate wrote NO evidence record -- violating FR-015 on the one
    path where a record matters most.
    """

    #: Cap on retained stderr. Bounded because vendor output is untrusted.
    STDERR_LIMIT = 64_000

    def __init__(
        self,
        argv: list[str],
        cwd: Path,
        env: dict[str, str],
        *,
        read_timeout: float = DEFAULT_DEADLINE_SECONDS,
    ) -> None:
        """Spawn the child with an EXPLICIT environment.

        ``env`` is REQUIRED, deliberately. It defaulted to ``None``, which
        ``Popen`` reads as "inherit the whole parent environment" -- so a caller
        that simply forgot the argument handed the external vendor preview every
        variable in the parent, credentials included, and #658's allowlist was
        bypassed in silence. A required parameter turns that omission into a
        TypeError at the call site instead of a leak at runtime.

        A caller that genuinely wants the ambient environment passes
        ``dict(os.environ)`` and says so.
        """
        self._read_timeout = read_timeout
        self._closed = False
        # BOUNDED: vendor output is untrusted, and an unbounded queue fed faster
        # than we drain is a memory-exhaustion path. A full queue back-pressures
        # the pump thread, which back-pressures the child's stdout pipe -- the
        # same flow control a plain blocking read would have had.
        self._stdout_q: queue.Queue[bytes | None] = queue.Queue(
            maxsize=MAX_QUEUED_LINES
        )
        self._stderr_parts: list[bytes] = []
        self._proc = subprocess.Popen(  # noqa: S603 - fixed argv shape, no shell
            resolve_launcher(argv),
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            **_tree_spawn_options(),
        )
        self._readers = [
            threading.Thread(target=self._pump_stdout, daemon=True),
            threading.Thread(target=self._pump_stderr, daemon=True),
        ]
        for reader in self._readers:
            reader.start()

    def _pump_stdout(self) -> None:
        """Feed complete lines into the queue; ``None`` marks end of stream."""
        stream = self._proc.stdout
        try:
            if stream is not None:
                while raw := _bounded_line(stream):
                    self._stdout_q.put(raw)
        except (OSError, ValueError):  # pragma: no cover - stream torn down
            pass
        finally:
            # Never block on a full queue here: the sentinel must always land, or
            # a reader waiting for EOF would wait forever.
            try:
                self._stdout_q.put_nowait(None)
            except queue.Full:  # pragma: no cover - only when 4096 lines pending
                pass

    def _pump_stderr(self) -> None:
        """Drain stderr so a full pipe buffer can never block the child."""
        stream = self._proc.stderr
        try:
            if stream is not None:
                while chunk := stream.read(4096):
                    if sum(map(len, self._stderr_parts)) < self.STDERR_LIMIT:
                        self._stderr_parts.append(chunk)
        except (OSError, ValueError):  # pragma: no cover - stream torn down
            pass

    def write(self, data: bytes) -> None:
        if self._proc.stdin is None:  # pragma: no cover - PIPE always present
            raise SessionError("the child has no stdin pipe")
        try:
            self._proc.stdin.write(data)
            self._proc.stdin.flush()
        except (OSError, ValueError) as exc:
            raise SessionError(f"the vendor stdin closed: {exc}") from exc

    def read_line(self) -> bytes:
        """One line, or ``b""`` at end of stream. Raises past the deadline.

        Waits on the QUEUE rather than the pipe, so the timeout is enforced
        against a server that never writes anything at all.
        """
        try:
            item = self._stdout_q.get(timeout=self._read_timeout)
        except queue.Empty:
            # The TIMEOUT type, so the runner reports a stall as a stall (M2).
            raise SessionStalled(
                f"the vendor sent nothing for {self._read_timeout}s"
            ) from None
        if item is None:
            # End of stream. Re-post so later reads agree rather than blocking.
            self._stdout_q.put(None)
            return b""
        return item

    def terminate(self) -> None:
        """Close stdin, then terminate, then kill. Never leaks the child."""
        if self._closed:
            return
        self._closed = True
        try:
            if self._proc.stdin and not self._proc.stdin.closed:
                self._proc.stdin.close()
        except (OSError, ValueError):  # pragma: no cover - best-effort teardown
            pass
        # The TREE first, while the direct child still exists: `npx` is a
        # shim (`npx.cmd` -> cmd.exe on win32), so the vendor is a grandchild,
        # and once the direct child is gone there is nothing left to walk.
        _kill_tree(self._proc.pid)
        try:
            self._proc.terminate()
            self._proc.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):  # pragma: no cover
            try:
                self._proc.kill()
                self._proc.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                pass
        # POSIX: anything in the group that ignored SIGTERM is killed now.
        _kill_tree(self._proc.pid, final=True)

    def stderr_text(self) -> str:
        """The drained stderr so far. Safe to call while the child is live."""
        return b"".join(self._stderr_parts).decode("utf-8", errors="replace")


#: Bound on the win32 tree kill. `taskkill` returns in milliseconds normally.
_TREE_KILL_TIMEOUT_SECONDS = 15


def _tree_spawn_options() -> dict[str, object]:
    """Spawn the child as the root of its own group, so its tree can be killed.

    POSIX: a new session makes the child's pid the process-group id, which
    ``os.killpg`` then reaches. win32: a new process group keeps console
    signals aimed at us from reaching the vendor, and ``taskkill /T`` walks the
    tree from the child's pid.
    """
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _kill_tree(pid: int, *, final: bool = False) -> None:
    """Kill ``pid`` AND its descendants. Best effort, never raises.

    Two passes on POSIX: SIGTERM to the group first (a graceful exit for the
    common, healthy close), then -- after the direct child has been waited on
    -- SIGKILL to whatever in the group is left. win32 has one forced pass,
    ``taskkill /T /F``, which must run while the direct child still exists;
    the ``final`` pass is a no-op there.

    ``Popen.terminate`` reaches only the direct child. On a stall that left the
    vendor grandchild running, it could still finish a flush into the model
    folder after the run was recorded as aborted and the operator had rolled
    back -- silently undoing the rollback.
    """
    try:
        if sys.platform == "win32":
            if final:
                return
            subprocess.run(  # noqa: S603, S607 - fixed argv, no shell
                ["taskkill", "/T", "/F", "/PID", str(pid)],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=_TREE_KILL_TIMEOUT_SECONDS,
                check=False,
                shell=False,
            )
        else:
            os.killpg(pid, signal.SIGKILL if final else signal.SIGTERM)
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        pass


def _bounded_line(stream: Any) -> bytes:
    """One line, capped at ``MAX_FRAME_BYTES + 1`` bytes; ``b""`` at EOF.

    ``for raw in stream`` buffered a whole line before the frame-size check
    ever ran, so the cap bounded nothing. Here an over-long line is returned
    TRUNCATED -- one byte past the cap, so :func:`protocol.decode_frame` still
    classifies it as oversized -- and the rest of that line is drained and
    discarded, so the next frame starts on a clean boundary.
    """
    limit = proto.MAX_FRAME_BYTES + 1
    line = stream.readline(limit)
    if len(line) < limit or line.endswith(b"\n"):
        return line
    while (rest := stream.readline(limit)) and not rest.endswith(b"\n"):
        pass
    return line
