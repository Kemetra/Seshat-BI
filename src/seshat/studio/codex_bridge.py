"""The live Codex app-server session and the bridge built on it (T021).

`codex_process` stops at an inspectable PLAN so handle discipline is unit-testable
without a Codex CLI. This module is where that plan is actually spawned.

**Why sync `Popen` and a reader thread.** `agent_routes` endpoints are `async def`,
but `_record_turn` drives `AgentBridge.run_turn` with a plain `for` loop and FastAPI
already offloads sync work to a threadpool. Making `run_turn` an `AsyncIterator`
would change the Protocol, `FakeAgentBridge`, `_record_turn`, and every test in the
shared suite, for no behaviour this form cannot deliver. The cost is that
thread-plus-pipe deadlock is a real risk -- which is why the tests drive an actual
child over an actual pipe rather than a mock.

**stdout is never parsed here.** Bytes go to `CodexProtocolReader`, which owns the
framing rules and the `MAX_FRAME_BYTES` bound on untrusted provider output. Parsing
inline would leave that bound existing only in the protocol module's own tests.

**stderr is drained on its own thread and redacted before retention.** It carries
credential-shaped strings; merging it into stdout would feed those to the frame
parser and into any diagnostic that kept the stream.
"""

from __future__ import annotations

import queue
import subprocess
import threading
from collections.abc import Callable, Iterator
from typing import Any

from seshat.studio.codex_process import CodexLaunchPlan, redact_provider_stderr
from seshat.studio.codex_protocol import CodexProtocolReader

__all__ = ["CodexSession"]

#: Sentinel pushed onto the frame queue when the reader thread sees EOF.
_EOF = object()

#: Upper bound `close()` gives a child to exit on its own before escalating to
#: `terminate()`. Not a sleep -- `wait(timeout=...)` returns the instant the
#: child exits, so a healthy child pays only its own runtime. It exists
#: because Windows `terminate()` is `TerminateProcess`, a hard kill: closing
#: right after `start()` would otherwise destroy a child that had not yet
#: been scheduled, losing stderr it was about to write. Measured child
#: startup-to-exit on this fixture is ~70ms worst case across 10 runs, so this
#: leaves over an order of magnitude of headroom for the fast path.
_EXIT_GRACE_SECONDS = 1.0


class CodexSession:
    """Owns one Codex app-server child process and its two reader threads."""

    def __init__(
        self, plan: CodexLaunchPlan, *, spawn: Callable[..., Any] | None = None
    ) -> None:
        self.plan = plan
        self._spawn = spawn or subprocess.Popen
        self._process: Any | None = None
        self._frames: queue.Queue[Any] = queue.Queue()
        self._stderr_parts: list[str] = []
        self._threads: list[threading.Thread] = []

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self) -> None:
        """Spawn the child with three explicit pipes and start both readers."""
        if self.plan.inherits_any_handle:
            raise ValueError(
                "refusing to spawn: the launch plan would inherit a handle (#557)"
            )
        self._process = self._spawn(
            list(self.plan.argv),
            cwd=str(self.plan.cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._start_thread(self._read_stdout)
        self._start_thread(self._read_stderr)

    def _start_thread(self, target: Callable[[], None]) -> None:
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        self._threads.append(thread)

    def _read_stdout(self) -> None:
        reader = CodexProtocolReader()
        stream = self._process.stdout if self._process else None
        if stream is None:
            self._frames.put(_EOF)
            return
        try:
            for chunk in iter(stream.readline, ""):
                for frame in reader.feed(chunk):
                    self._frames.put(frame)
        except Exception as error:  # surfaced as a frame, never swallowed
            self._frames.put(error)
        finally:
            self._frames.put(_EOF)

    def _read_stderr(self) -> None:
        stream = self._process.stderr if self._process else None
        if stream is None:
            return
        try:
            for chunk in iter(stream.readline, ""):
                self._stderr_parts.append(
                    redact_provider_stderr(chunk, workspace_root=self.plan.cwd)
                )
        except Exception as error:  # a close-during-read race must not vanish silently
            self._stderr_parts.append(
                redact_provider_stderr(
                    f"<stderr reader error: {error}>",
                    workspace_root=self.plan.cwd,
                )
            )

    def frames(self, timeout: float = 30.0) -> Iterator[dict[str, Any]]:
        """Yield parsed frames until the child closes stdout."""
        while True:
            item = self._frames.get(timeout=timeout)
            if item is _EOF:
                return
            if isinstance(item, Exception):
                raise item
            yield item

    def send(self, frame: dict[str, Any]) -> None:
        """Write one JSON-RPC frame to the child's stdin."""
        import json

        if self._process is None or self._process.stdin is None:
            raise RuntimeError("session is not started")
        self._process.stdin.write(json.dumps(frame) + "\n")
        self._process.stdin.flush()

    def stderr_text(self) -> str:
        """Everything the child wrote to stderr, already redacted."""
        return "".join(self._stderr_parts)

    def close(self, timeout: float = 5.0) -> int | None:
        """Terminate the child and join both readers. Safe to call twice.

        A caller may close() right after start() with no frames() call in
        between -- an error path or a cancellation has no reason to drain
        stdout first -- so whatever the child already wrote to stderr must
        not depend on that drain having happened.

        The grace wait below is why: on Windows, `terminate()` is
        `TerminateProcess`, a hard kill with no equivalent of a graceful
        SIGTERM. Calling it immediately after start() can kill a child before
        the OS has even scheduled it, destroying stderr it was about to write
        a moment later. `wait(timeout=_EXIT_GRACE_SECONDS)` costs nothing on a
        child that exits quickly -- it returns the instant the child exits --
        and only escalates to terminate/kill once that bound is spent, which
        is what keeps a genuinely hung child's close() bounded.

        The reader threads are joined AFTER that resolution but BEFORE the
        streams are closed, so each thread drains whatever the child flushed
        and exits via its own EOF rather than via a stream ripped out from
        under an in-flight `readline()`.
        """
        if self._process is None:
            return None
        if self._process.poll() is None:
            try:
                self._process.wait(timeout=_EXIT_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                self._process.terminate()
        for thread in self._threads:
            thread.join(timeout=timeout)
        if self._process.poll() is None:
            self._process.kill()
        try:
            self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
        for stream in (
            self._process.stdin,
            self._process.stdout,
            self._process.stderr,
        ):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass
        return self._process.returncode
