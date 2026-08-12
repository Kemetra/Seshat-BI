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
import time
from collections.abc import Callable, Iterator
from typing import Any

from seshat.studio.codex_process import CodexLaunchPlan, redact_provider_stderr
from seshat.studio.codex_protocol import CodexProtocolReader

__all__ = ["CodexSession"]

#: Sentinel pushed onto the frame queue when the reader thread sees EOF.
_EOF = object()


def _remaining(deadline: float) -> float:
    """Seconds left before `deadline`, floored at 0 so a spent budget never
    turns into a negative -- and therefore unbounded -- `timeout=` argument.
    """
    return max(0.0, deadline - time.monotonic())


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
        #: Set by `_read_stderr` in a `finally`, the instant its read loop ends
        #: (child EOF, or an exception). `close()` waits on this -- an OBSERVED
        #: state transition -- rather than on elapsed wall-clock time.
        self._stderr_done = threading.Event()

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
            self._stderr_done.set()
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
        finally:
            self._stderr_done.set()

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

        Bounded against ONE monotonic deadline, computed once, so the whole
        call -- terminate, kill, both joins -- costs at most `timeout`
        wall-clock seconds regardless of how many stages it takes. There is
        no wait for the child to exit on its own: the real Codex app-server
        is long-lived and never exits by itself, so a prompt production
        shutdown requires terminating immediately, not waiting to see if it
        will.

        That has one real consequence worth naming rather than hiding: if the
        child is terminated before the OS has scheduled it at all, it never
        gets to write anything, and there is nothing for `stderr_text()` to
        report -- not because it was dropped, but because it was never
        produced. No amount of synchronization recovers a write that never
        happened; only giving the child time to run does, and time-to-run is
        exactly the wait a prompt shutdown cannot afford to make unconditional
        (see `test_stderr_survives_close_once_the_child_has_actually_run` and
        its docstring for the line this draws).

        What IS guaranteed, unconditionally: once the child has produced
        output, `close()` will not discard it. The stderr reader thread sets
        `self._stderr_done` in a `finally` the instant its read loop ends --
        an observed state transition, not elapsed time -- and this method
        waits on that event (bounded by the remaining deadline) before it
        closes the stderr stream. `terminate()`/`kill()` end the child and
        thus the thread's `readline()` loop via a real EOF; the join and the
        stream-close both happen only after that event, so no stream is ever
        closed out from under an in-flight read on either reader thread.
        """
        if self._process is None:
            return None
        deadline = time.monotonic() + timeout
        if self._process.poll() is None:
            self._process.terminate()
        self._join_threads(deadline)
        if self._process.poll() is None:
            self._process.kill()
            self._join_threads(deadline)  # re-join: kill() must not race a stream close
        try:
            self._process.wait(timeout=_remaining(deadline))
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

    def _join_threads(self, deadline: float) -> None:
        """Join every reader thread, each bounded by what remains of `deadline`."""
        for thread in self._threads:
            thread.join(timeout=_remaining(deadline))
