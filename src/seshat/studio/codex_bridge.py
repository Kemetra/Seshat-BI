"""The live Codex app-server session and the bridge built on it (T021).

`codex_process` stops at an inspectable PLAN so handle discipline is unit-testable
without a Codex CLI. This module is where that plan is actually spawned.

**Why sync `Popen` and a reader thread.** `agent_routes` endpoints are `async def`,
but `_pump_turn` advances `AgentBridge.run_turn` one event at a time, offloading only
the blocking `next()` so the event loop stays free. Making `run_turn` an `AsyncIterator`
would change the Protocol, `FakeAgentBridge`, `_pump_turn`, and every test in the
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
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from seshat.studio.bridge import _event, validate_turn_request
from seshat.studio.codex_process import (
    CodexLaunchPlan,
    ProbeObservations,
    classify_health,
    redact_provider_stderr,
)
from seshat.studio.codex_protocol import (
    CodexFrameError,
    CodexProtocolReader,
    NormalizationContext,
    normalize_approval_request,
    normalize_notification,
)
from seshat.studio.events import StudioEvent
from seshat.studio.projection import AgentHealth

__all__ = ["CodexBridge", "CodexSession"]

#: Sentinel pushed onto the frame queue when the reader thread sees EOF.
_EOF = object()

#: Request ids for the three calls one turn makes. Fixed rather than generated: a
#: session drives exactly one turn, so a counter would add state without removing a
#: collision, and a constant makes the reply that carries the thread id greppable.
_INITIALIZE_ID = 1
_THREAD_START_ID = 2
_TURN_START_ID = 3


def _thread_id_from(frame: dict[str, Any]) -> str | None:
    """The thread id from the `thread/start` REPLY, or None for any other frame.

    Keyed on our own request id rather than on "any frame carrying a threadId":
    notifications carry one too, and reacting to the first of those would send
    `turn/start` on a thread the provider had not finished opening.
    """
    if frame.get("id") != _THREAD_START_ID:
        return None
    result = frame.get("result")
    if not isinstance(result, dict):
        return None
    thread = result.get("thread")
    if not isinstance(thread, dict):
        return None
    thread_id = thread.get("id")
    return thread_id if isinstance(thread_id, str) else None


def _executable_exists(plan: CodexLaunchPlan) -> bool:
    """Whether this plan's executable could actually be launched.

    Resolved the way `Popen` resolves it, not by a bare `Path.exists()`: a plan may
    name the CLI by BARE NAME (`"codex"`, found on PATH) or relative to the child's
    `cwd`, and checking only the parent process's current directory reported a
    perfectly usable CLI as `missing` -- sending the user to install something they
    already have (#617 review).
    """
    name = plan.argv[0]
    if shutil.which(name) is not None:
        return True
    candidate = Path(name)
    if candidate.is_absolute():
        return candidate.exists()
    return (Path(plan.cwd) / candidate).exists()


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
        #: True once `close()` has been called.
        self._shutdown_requested = False

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
        self._shutdown_requested = True
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

    def health(self, version: str | None, *, signed_in: bool) -> AgentHealth:
        """Classify this session, reporting a dead child as EOF.

        Delegates to `classify_health` rather than inventing a second vocabulary:
        that function owns the seven contract states and the FR-013 rule that no
        health condition may switch Studio to a billed path.

        The dangerous reading is silent success -- a child that died mid-turn has
        delivered a TRUNCATED answer, and `ready` would let Studio present it as
        complete. `poll()` is the evidence: `None` means still running and `0` a
        clean exit, so only a non-zero or signalled status becomes `saw_eof`.
        (On POSIX a signalled child reports a NEGATIVE returncode, which this
        comparison catches for the same reason.)
        """
        # Any exit BEFORE we asked for one is unexpected, whatever its status. The
        # app-server is long-lived: it does not finish on its own, so `poll() == 0`
        # without a `close()` means it went away mid-session and no further turn is
        # possible -- reporting that as `ready` is the silent success this method
        # exists to prevent. After `close()` an exit is exactly what we requested.
        if self._process is None:
            # Never started, or `Popen` failed. `is_running` is already False and no
            # turn can be served, so reporting `healthy` here would be the same
            # silent success this method exists to prevent -- and `None` status must
            # NOT be read as "running fine" (#617 review).
            # `executable_found` is ASKED, not assumed: the usual reason `_process`
            # is None after a start attempt is that the binary is missing, and
            # hardcoding True routed the user to schema-compatibility or restart
            # advice instead of "install the CLI" (#617 review).
            return classify_health(
                ProbeObservations(
                    executable_found=_executable_exists(self.plan),
                    version=version,
                    signed_in=signed_in,
                    saw_eof=True,
                )
            )
        # Any exit ends the session, whatever its status and whoever caused it.
        # A long-lived app-server does not finish on its own, so a self-exit is a
        # failure; and after `close()` the session is over regardless, so reporting
        # `healthy` would advertise a dead adapter as responding (#617 review). Both
        # roads lead here, which is why no flag distinguishes them.
        died = self._process.poll() is not None
        return classify_health(
            ProbeObservations(
                executable_found=True,
                version=version,
                signed_in=signed_in,
                saw_eof=died,
            )
        )

    def _join_threads(self, deadline: float) -> None:
        """Join every reader thread, each bounded by what remains of `deadline`."""
        for thread in self._threads:
            thread.join(timeout=_remaining(deadline))


class CodexBridge:
    """`AgentBridge` over a live Codex app-server.

    A sync generator on purpose -- see the module docstring. Frames are normalized by
    `codex_protocol`, never mapped here: one normalization authority is what keeps the
    allowlist (and its refusal to pass through reasoning) in a single place.
    """

    def __init__(
        self, plan: CodexLaunchPlan, *, propose_plan: CodexLaunchPlan | None = None
    ) -> None:
        self._plan = plan
        #: Optional second plan used only for `propose_changes`. A real Codex child
        #: decides for itself whether a turn touches files, so production passes one
        #: plan and leaves this None; the scripted child replays a FIXED script, so a
        #: test that must see a proposal has to launch the fixture that contains one.
        #: Selecting a script is NOT the mode boundary: per `bridge`'s docstring the
        #: BINDING refusal is `agent_routes._pump_turn`, which every bridge's output
        #: passes through. This is the same cooperation `FakeAgentBridge` offers.
        self._propose_plan = propose_plan
        #: Called with the live `CodexSession` when a turn opens one, and with `None`
        #: when that turn ends. This is how a decided approval finds the child process
        #: that is blocked on it: `run_turn` does not receive a `thread_id`, so the
        #: bridge cannot key a registry itself, and this instance is SHARED across
        #: threads -- storing the session on `self` would let one thread's turn
        #: overwrite another's and answer the wrong provider. The route supplies a
        #: closure that already knows its thread. Default is a no-op so every existing
        #: caller, and `FakeAgentBridge`, are unaffected.
        self.on_session: Callable[[Any], None] = lambda _session: None

    def describe(self) -> dict[str, Any]:
        return {"bridge": "codex", "provider": "codex", "deterministic": False}

    def _plan_for(self, requested_mode: str) -> CodexLaunchPlan:
        if requested_mode == "propose_changes" and self._propose_plan is not None:
            return self._propose_plan
        return self._plan

    def _open_thread(self, session: CodexSession) -> None:
        """Ask to initialize. Nothing else may be sent until its REPLY arrives.

        The contract and the captured probe both require
        `initialize -> response -> initialized` before any thread request. Sending
        `initialized` and `thread/start` immediately after the request raced protocol
        negotiation: against the scripted child it looked fine (it replays regardless
        of what it is asked), and only a live server can reject a thread request that
        arrives before negotiation completes.

        `_start_thread` is therefore driven by the reply, in the same pass that
        already waits for `thread/start`'s reply before sending `turn/start`.
        """
        session.send(
            {
                "jsonrpc": "2.0",
                "id": _INITIALIZE_ID,
                "method": "initialize",
                "params": {"clientInfo": {"name": "seshat-studio", "version": "1"}},
            }
        )

    def _start_thread(self, session: CodexSession) -> None:
        """Confirm negotiation, then ask for a thread."""
        session.send({"jsonrpc": "2.0", "method": "initialized"})
        session.send(
            {
                "jsonrpc": "2.0",
                "id": _THREAD_START_ID,
                "method": "thread/start",
                "params": {
                    # The SESSION's plan, not `self._plan`: `_plan_for()` may have
                    # selected the propose plan, and pinning the provider thread to a
                    # different workspace than the child runs in would let it read and
                    # propose in one tree while redaction is configured for another.
                    "cwd": str(session.plan.cwd),
                    "approvalPolicy": "on-request",
                    # Studio never authorises provider-side writes: the approval
                    # surface is T024-T027 and `_pump_turn` refuses write intent
                    # under `read_only`. A sandbox that could write would make the
                    # provider capable of edits nobody reviewed.
                    "sandbox": "read-only",
                },
            }
        )

    def _turn_events(
        self,
        session: CodexSession,
        context: NormalizationContext,
        prompt: str,
    ) -> Iterator[tuple[str, dict[str, Any]]]:
        """Drive the provider's frames to `(event_type, payload)` pairs, once.

        Split from `run_turn` so that method stays a flat drive-and-emit loop: the
        two concerns here -- requesting the turn as soon as the thread id lands, and
        ending at the first terminal -- each need their own nesting, and inlining all
        three made one deeply-nested body.

        Stops at the first terminal. A real app-server is long-lived and keeps stdout
        open after `turn/completed`, so reading on would block until `frames()` timed
        out, turning a COMPLETED turn into a stalled request (the scripted child hides
        this by reaching EOF on its own). Stopping also settles the turn: a frame
        arriving after the terminal -- the committed `thread_turn` fixture ends with
        exactly that, a trailing `error` -- can no longer produce a SECOND terminal,
        which would leave a consumer holding both a completion and a failure for one
        turn. The shared suite pins "exactly one terminal last".
        """
        for frame in self._frames_once_requested(session, prompt):
            # A `requestApproval` is a REQUEST, not a notification: it carries an `id`
            # the provider blocks on, so it is translated here rather than falling
            # through `normalize_notification`, which only ever sees fire-and-forget
            # frames. Yielding it makes the approval visible; ANSWERING it is the
            # relay's job, driven by the analyst's decision on a later HTTP request.
            approval = normalize_approval_request(frame, context=context)
            if approval is not None:
                yield approval
                continue
            for event_type, payload in normalize_notification(frame, context=context):
                if event_type == "turn_started":
                    continue  # the envelope in `run_turn` already opened the turn
                yield event_type, payload
                if event_type in {"turn_completed", "turn_failed"}:
                    return

    def _frames_once_requested(
        self, session: CodexSession, prompt: str
    ) -> Iterator[dict[str, Any]]:
        """Pass frames through, sending `turn/start` as soon as the thread id lands.

        A separate pass because it is a separate job: this one WRITES to the session
        while `_turn_events` only reads. Folding it into that loop put two unrelated
        conditionals around the translation step.

        `thread/start` returns a thread id the PROVIDER mints, and `turn/start`
        requires it -- so the turn request cannot be written up front; it waits for
        this reply. The fixture hides that: its recorded `turn/start` already carries
        `thr_fixture`, so the id appears in the stream whether or not the bridge
        learned it. Only a live server, minting its own, forces the correlation.
        """
        initialized = False
        requested = False
        for frame in session.frames():
            if not initialized:
                initialized = self._negotiated(session, frame)
            if not requested:
                requested = self._requested(session, frame, prompt)
            yield frame

    def _negotiated(self, session: CodexSession, frame: dict[str, Any]) -> bool:
        """True once `initialize` has been ANSWERED and the thread requested.

        The contract requires `initialize -> response -> initialized` before any
        thread request, so this is what releases the rest of the handshake. A frame
        that is not our reply leaves the state unchanged.
        """
        if frame.get("id") != _INITIALIZE_ID:
            return False
        if "error" in frame:
            # The provider REFUSED to negotiate. Proceeding would open a thread on a
            # session that explicitly rejected initialization, and the turn would
            # fail later with a generic error instead of the incompatibility the
            # provider actually reported.
            raise CodexFrameError(
                "the provider refused to initialize; the adapter is incompatible "
                "with this build"
            )
        self._start_thread(session)
        return True

    def _requested(
        self, session: CodexSession, frame: dict[str, Any], prompt: str
    ) -> bool:
        """True once the turn has been requested on the provider's own thread id."""
        thread_id = _thread_id_from(frame)
        if thread_id is None:
            return False
        self._start_turn(session, thread_id, prompt)
        return True

    def _start_turn(self, session: CodexSession, thread_id: str, prompt: str) -> None:
        """Ask for the turn itself, on the thread the provider just minted."""
        session.send(
            {
                "jsonrpc": "2.0",
                "id": _TURN_START_ID,
                "method": "turn/start",
                "params": {
                    "threadId": thread_id,
                    "input": [{"type": "text", "text": prompt}],
                    "sandboxPolicy": {"type": "readOnly", "networkAccess": False},
                },
            }
        )

    def run_turn(
        self, *, prompt: str, turn_id: str, requested_mode: str
    ) -> Iterator[StudioEvent]:
        cleaned = validate_turn_request(prompt, requested_mode)
        sequence = 0

        def emit(event_type: str, payload: dict[str, Any]) -> StudioEvent:
            nonlocal sequence
            sequence += 1
            return _event(event_type, payload, turn_id, sequence)

        yield emit("turn_started", {"prompt_echo": cleaned[:200]})

        plan = self._plan_for(requested_mode)
        session = CodexSession(plan)
        context = NormalizationContext(workspace_root=plan.cwd)
        # Published BEFORE `start()`: a `requestApproval` can only arrive once frames
        # are flowing, and the relay must already be able to find this session by then
        # or the analyst's decision has nowhere to go. Retracted in the `finally`
        # beside `session.close()` -- a closed child left in the registry would accept
        # a decision and drop it, which is the silent failure this seam removes.
        self.on_session(session)
        saw_terminal = False
        try:
            # `start()` is INSIDE the guard: a missing or non-executable binary makes
            # `Popen` raise, and outside it that escaped after `turn_started` had
            # already been recorded -- a 500 with no terminal, leaving the thread's
            # active turn set so every later turn is refused as already-active.
            session.start()
            self._open_thread(session)
            for event_type, payload in self._turn_events(session, context, cleaned):
                if event_type in {"turn_completed", "turn_failed"}:
                    saw_terminal = True
                yield emit(event_type, payload)
        except Exception as error:
            # A read failure must still END the turn. `frames()` raises `queue.Empty`
            # when the provider stalls and `CodexFrameError` on malformed output; if
            # either escaped, the consumer would hold a `turn_started` with no
            # terminal -- breaking the contract the shared suite pins as "exactly one
            # terminal event last". The route pump records a terminal for a
            # failed drain,
            # so the exception would surface as a 500 AND leave `_active_turn` set,
            # wedging every later turn on that thread as already-active.
            #
            # The detail is the exception TYPE, never its text: provider messages can
            # carry paths or tokens, and this payload is retained.
            saw_terminal = True
            yield emit(
                "turn_failed",
                {
                    "category": "provider_error",
                    "detail": (f"the provider session failed: {type(error).__name__}"),
                },
            )
        finally:
            self.on_session(None)
            session.close()

        if not saw_terminal:
            # EOF without a terminal frame is a failure, never a quiet success.
            yield emit(
                "turn_failed",
                {
                    "category": "provider_error",
                    "detail": (
                        "the provider ended the session without completing the turn"
                    ),
                },
            )
