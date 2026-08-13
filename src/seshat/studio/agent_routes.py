"""Thread, turn, and SSE routes (FR-016, FR-023, FR-035).

Kept out of `app.py` so the deterministic routes stay readable, and because the
streaming concerns here are genuinely different from a JSON projection.

**Why the stream authenticates on a cookie.** `EventSource` cannot set request headers,
so the usual `Authorization` pattern is unavailable to a browser-initiated stream. The
common workaround -- a token in the query string -- writes the credential into access
logs, browser history, and any referrer. Studio's session is already an `HttpOnly`,
`SameSite=Strict` cookie, which the browser attaches to the SSE request automatically,
so this route needs no exception at all: it runs the same three enforcement steps as
every other route, and page JavaScript never touches the session value.

**Why replay refuses rather than shortens.** FR-035 forbids a database, so retention is
bounded and a resume point can genuinely expire. Serving "everything still retained" for
an evicted `Last-Event-ID` would silently skip events and leave the browser rendering a
state that never existed, so the store raises and this module turns that into the
contract's 409.

**The stream is a finite replay, deliberately.** `/events` serves what is retained and
closes; `EventSource` then reconnects on its own with `Last-Event-ID`. Reconnect is
therefore the NORMAL path rather than a failure path, so the resume logic is exercised
on every poll instead of only after an error. The trade-off is real and stated rather
than hidden: a turn's events appear on the next reconnect, so `SSE_RETRY_MILLISECONDS`
is the perceived latency. A held-open stream is the alternative and would change this
module only.
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from functools import partial
from typing import Any

import anyio
import anyio.to_thread
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from seshat.studio.approval_routes import (
    ApprovalRequest,
    decide_approval,
    register_approval,
)
from seshat.studio.bridge import validate_turn_request
from seshat.studio.events import ReplayExpired, TurnAlreadyActive

#: Contract's `AgentThreadRef.state` enum. Used to VALIDATE the state this module
#: reports, so a typo cannot ship a state no client knows how to render.
THREAD_STATES: frozenset[str] = frozenset(
    {
        "starting",
        "ready",
        "running",
        "awaiting_technical_approval",
        "completed",
        "failed",
        "interrupted",
    }
)

#: Event types that express intent to CHANGE the workspace.
#:
#: Refused outright during a `read_only` turn. This list IS the enforcement point
#: for that mode, so a new write-shaped event type in the contract belongs here too.
WRITE_INTENT_TYPES: frozenset[str] = frozenset(
    {"file_change_proposed", "approval_required"}
)


def _problem(
    status: int, title: str, detail: str, recovery_action: str
) -> JSONResponse:
    """The contract's `Problem` shape. Mirrors `app._problem` deliberately.

    Imported rather than duplicated would be cleaner, but `app` imports THIS module, so
    reaching back would be a cycle. The shape is pinned by contract tests on both sides.
    """
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "recovery_action": recovery_action,
        },
    )


def _sse_frame(event: Any) -> str:
    """One SSE frame.

    The `id:` field is what a browser echoes back as `Last-Event-ID`, so omitting it
    would silently disable replay: every reconnect would restart from zero, or refuse
    once the buffer rotated. It carries the per-thread sequence, exactly as the contract
    specifies.
    """
    payload = json.dumps(event.as_dict(), separators=(",", ":"), sort_keys=True)
    return f"id: {event.sequence}\nevent: {event.type}\ndata: {payload}\n\n"


#: What the browser is TOLD to wait before reconnecting, in milliseconds.
#:
#: This endpoint is a FINITE replay: it serves what is retained and closes. The browser
#: treats a closed connection as a dropped one and reconnects on its own, sending
#: `Last-Event-ID` -- so reconnect is this design's NORMAL path, not its failure path,
#: which is the property worth having (a resume path only exercised after a failure is a
#: resume path that is never tested).
#:
#: The cost is that a turn's events surface on the next reconnect rather than instantly,
#: so the interval IS the perceived latency. Declaring it explicitly rather than leaving
#: the browser on its ~3s default makes that a stated choice instead of an accident, and
#: keeps it tunable in one place when a held-open stream replaces this.
SSE_RETRY_MILLISECONDS = 750


def _stream_preamble() -> str:
    """The `retry:` directive, sent once before any event."""
    return f"retry: {SSE_RETRY_MILLISECONDS}\n\n"


def _parse_last_event_id(raw: str | None) -> int | None:
    """`None` if absent, a non-negative int if valid, else `ValueError`.

    Absent and zero are NOT the same thing to the store, and neither may be
    conflated with unparseable: treating garbage as 0 would replay the whole buffer
    to a client that asked to resume, duplicating everything already rendered.

    The contract declares this header `type: integer, minimum: 0`, so validation
    belongs HERE rather than in the store. An earlier revision accepted `-1` because
    `int("-1")` does not raise; the store's own `ValueError` then escaped as an
    uncaught 500 WITH a traceback -- while this route already had a 400 branch whose
    message described a case it could never reach.

    `int` alone also accepts `"+5"`, `" 3 "`, and non-ASCII digits, none of which the
    contract permits, so the accepted set is pinned to exactly the contracted one.
    """
    if raw is None or raw.strip() == "":
        return None
    candidate = raw.strip()
    if not candidate.isascii() or not candidate.isdigit():
        raise ValueError(f"Last-Event-ID must be a non-negative integer, got {raw!r}")
    return int(candidate)


def _unknown_thread() -> JSONResponse:
    """The one 404 three routes share, so its wording cannot drift between them."""
    return _problem(
        404,
        "Unknown thread",
        "No agent thread matches that identifier.",
        "Start a new conversation from the Command Room.",
    )


#: The state a freshly created thread reports, checked against the contract's enum
#: at import time. This is what `THREAD_STATES` is FOR: declaring the enum and never
#: consulting it looked like validation while validating nothing.
_NEW_THREAD_STATE = "ready"
assert _NEW_THREAD_STATE in THREAD_STATES, (
    f"{_NEW_THREAD_STATE!r} is not in the contract's AgentThreadRef.state enum"
)


def _create_thread(app: FastAPI, body: dict[str, Any] | None) -> dict[str, Any]:
    """Create a thread and record its opening event."""
    thread_id = f"thread-{uuid.uuid4().hex[:12]}"
    selected = (body or {}).get("selected_table_id")
    app.state.threads.thread(thread_id).append(
        "thread_started", {"selected_table_id": selected}
    )
    return {"thread_id": thread_id, "state": _NEW_THREAD_STATE}


async def _start_turn(app: FastAPI, thread_id: str, body: dict[str, Any]) -> Any:
    """Accept one turn and stream its result, per the contract's 202.

    The turn is ACCEPTED here and drained in the background: the endpoint is
    documented as "Turn accepted; updates stream from the events endpoint", and a
    real provider takes seconds, so draining inline held the event loop for the whole
    turn -- no SSE polling, no interrupt, until it finished. The fake bridge hid that
    by completing instantly.

    What still happens synchronously is everything the caller must learn from the
    STATUS: an unknown thread (404), a malformed request (422), and a second live
    turn (409). Each is decided by validating and recording `turn_started` before
    returning, so the conflict a browser needs to see is still in the response rather
    than only in the stream.

    Failures discovered LATER cannot be a status -- the response has already gone --
    so they arrive as a `turn_failed` event. That includes the `read_only` refusal,
    which previously returned 502: a status the contract does not list, and one that
    left `_active_turn` set because no terminal was recorded.
    """
    if not app.state.threads.has_thread(thread_id):
        return _unknown_thread()

    if getattr(app.state, "agent_turns_refused", False):
        # Codex was CONFIGURED and is unusable -- missing CLI, or a build outside the
        # tested range. The bridge contract requires an unsupported protocol to refuse
        # turns rather than be handled opportunistically, so answering with the
        # deterministic fake would hand the analyst canned text under the belief that
        # their configured agent produced it. 503 with the reason, and every
        # deterministic workspace view stays available.
        return _problem(
            503,
            "Agent unavailable",
            getattr(app.state, "agent_provider_detail", "The agent is unavailable."),
            "Install or update the Codex CLI and restart Studio; workspace views "
            "remain usable meanwhile.",
        )

    thread = app.state.threads.thread(thread_id)
    turn_id = f"turn-{uuid.uuid4().hex[:12]}"
    request = TurnRequest(
        prompt=str(body.get("prompt", "")),
        turn_id=turn_id,
        requested_mode=str(body.get("requested_mode", "")),
    )
    try:
        # Validated by the same helper the bridge uses, BEFORE anything is recorded:
        # a malformed prompt must be a 422, not a turn that opens and then fails.
        validate_turn_request(request.prompt, request.requested_mode)
        thread.append(
            "turn_started",
            {"prompt_echo": request.prompt[:200]},
            turn_id=turn_id,
        )
    except TurnAlreadyActive as conflict:
        # BEFORE the ValueError clause: TurnAlreadyActive subclasses it, so the
        # broad handler would otherwise swallow this and report a live-turn
        # conflict as the analyst's own formatting mistake.
        return _problem(
            409,
            "A turn is already running",
            str(conflict),
            "Wait for the current reply, or stop it first.",
        )
    except ValueError as invalid:
        return _problem(
            422,
            "Invalid turn request",
            str(invalid),
            "Adjust the request and try again.",
        )

    # Parked for the poll loop to advance. Not a background task: one created inside
    # a request dies with that request's event loop (verified under `TestClient`), so
    # the turn would silently stop after its first frame.
    _reap_abandoned_turns(app)
    _publish_provider_session(app, thread_id)
    app.state.pending_turns[thread_id] = _PendingTurn(
        events=app.state.bridge.run_turn(
            prompt=request.prompt,
            turn_id=request.turn_id,
            requested_mode=request.requested_mode,
        ),
        request=request,
        pumping=asyncio.Lock(),
        last_touched=time.monotonic(),
        results=queue.Queue(),
    )
    return {"turn_id": turn_id}


def _publish_provider_session(app: FastAPI, thread_id: str) -> None:
    """Let this thread's turn register its live provider session for the relay.

    The approval relay answers a blocked `requestApproval` by writing to the child
    process that raised it, so it must be able to find that child by thread. Nothing
    did this before: `app.state.provider_sessions` was initialized and read but never
    assigned, so every lookup missed and every decision returned 204 while the
    provider stayed blocked.

    Registration is a CLOSURE handed to the bridge rather than a value the bridge
    returns, for two reasons. `run_turn` never receives a `thread_id`, so the bridge
    cannot key the registry itself; and `app.state.bridge` is ONE instance shared by
    every thread, so a session stored on it would let a second thread's turn overwrite
    the first and answer the wrong provider.

    A bridge with no session to publish -- `FakeAgentBridge` -- simply has no
    `on_session` attribute, and this is a no-op for it.
    """
    if not hasattr(app.state.bridge, "on_session"):
        return

    def publish(session: Any) -> None:
        if session is None:
            app.state.provider_sessions.pop(thread_id, None)
        else:
            app.state.provider_sessions[thread_id] = session

    app.state.bridge.on_session = publish


def _interrupt_turn(app: FastAPI, thread_id: str, turn_id: str) -> Response:
    if not app.state.threads.has_thread(thread_id):
        return _unknown_thread()
    try:
        app.state.threads.thread(thread_id).interrupt(turn_id)
    except ValueError as inactive:
        return _problem(
            409,
            "No live turn to interrupt",
            str(inactive),
            "The turn has already ended; no action is needed.",
        )
    # The turn is over as far as the store is concerned; drop and close its generator
    # too, or a real provider's child process outlives the turn that spawned it.
    pending = app.state.pending_turns.get(thread_id)
    if pending is not None:
        _finish_turn(app, thread_id, pending)
    return Response(status_code=204)


async def _stream_events(app: FastAPI, thread_id: str, request: Request) -> Response:
    """Replay what is retained, then end the response.

    A finite replay rather than an open connection: the fake bridge records
    synchronously, so everything a client needs is already in the buffer when it
    connects, and `EventSource` reconnects on its own with `Last-Event-ID`. That makes
    reconnect the SAME code path as first connect -- an endpoint whose resume path is
    only exercised after a failure is an endpoint whose resume path is untested.
    """
    if not app.state.threads.has_thread(thread_id):
        return _unknown_thread()

    # Advance any live turn BEFORE replaying, so this poll serves what it just
    # produced rather than making the browser wait another interval for it.
    await _pump_turn(app, thread_id, app.state.threads.thread(thread_id))

    try:
        last_seen = _parse_last_event_id(request.headers.get("Last-Event-ID"))
    except ValueError:
        return _problem(
            400,
            "Malformed Last-Event-ID",
            "The resume point must be a non-negative integer.",
            "Reload Studio to start a fresh stream.",
        )

    try:
        # `is None` rather than `or 0`: absent and explicit-zero are distinct upstream
        # (the parser keeps them apart on purpose), and collapsing them with a falsy
        # test would erase that distinction the moment either side grows a meaning.
        resume_from = 0 if last_seen is None else last_seen
        events = app.state.threads.thread(thread_id).replay_after(resume_from)
    except ReplayExpired:
        return _problem(
            409,
            "Replay point expired",
            "Those events are no longer retained, so the stream cannot resume "
            "without a gap.",
            "Reload Studio to start a fresh stream.",
        )

    def frames() -> Iterator[str]:
        # The preamble goes out even when `events` is empty: a reconnect that finds
        # nothing new still needs the retry interval, and it is the empty responses that
        # dominate an idle thread.
        yield _stream_preamble()
        for event in events:
            yield _sse_frame(event)

    return StreamingResponse(
        frames(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


def register_agent_routes(app: FastAPI) -> None:
    """Bind the thread, turn, interrupt, and event-stream routes.

    Each handler is a thin adapter over a module-level function taking `app`. The logic
    lives outside the closure so it is readable and testable on its own -- four route
    bodies nested in one registration function made the whole thing one large method
    whose branches could only be reached through HTTP.
    """
    from seshat.studio.app import API_PREFIX

    #: thread_id -> (live generator, its TurnRequest). One in-flight turn per thread,
    #: which `TurnAlreadyActive` already guarantees.
    app.state.pending_turns = {}

    @app.post(f"{API_PREFIX}/agent/threads", status_code=201)
    async def create_thread(body: dict[str, Any] | None = None) -> Any:
        return _create_thread(app, body)

    @app.post(f"{API_PREFIX}/agent/threads/{{thread_id}}/turns", status_code=202)
    async def start_turn(thread_id: str, body: dict[str, Any]) -> Any:
        return await _start_turn(app, thread_id, body)

    @app.post(
        f"{API_PREFIX}/agent/threads/{{thread_id}}/turns/{{turn_id}}/interrupt",
        status_code=204,
    )
    async def interrupt_turn(thread_id: str, turn_id: str) -> Response:
        return _interrupt_turn(app, thread_id, turn_id)

    @app.post(
        f"{API_PREFIX}/agent/threads/{{thread_id}}/approvals/{{approval_id}}",
        status_code=204,
    )
    async def respond_to_tool_approval(
        thread_id: str, approval_id: str, body: dict[str, Any]
    ) -> Response:
        return decide_approval(
            ApprovalRequest(
                app=app,
                thread_id=thread_id,
                approval_id=approval_id,
                body=body,
                problem=_problem,
                unknown_thread=_unknown_thread,
            )
        )

    @app.get(f"{API_PREFIX}/agent/threads/{{thread_id}}/events")
    async def stream_events(thread_id: str, request: Request) -> Response:
        return await _stream_events(app, thread_id, request)


#: Returned by `next(...)` when the bridge's generator is exhausted. A sentinel
#: rather than catching StopIteration: `to_thread.run_sync` would surface that as a
#: RuntimeError from the worker, obscuring an ordinary end-of-turn.
_DRAINED = object()

#: Returned when the pump's slice expired before the provider produced anything. The
#: generator keeps running on its worker; the next poll picks it up.
_STILL_WAITING = object()

#: Event types that END a turn. Local rather than imported from `events` to keep this
#: module's pump readable; the store owns the authoritative transition.
_TERMINAL_EVENTS: frozenset[str] = frozenset({"turn_completed", "turn_failed"})

#: How long a parked turn may go unpolled before it is reaped. The pump only runs on a
#: poll, so a browser that closes mid-reply would otherwise leave its generator parked
#: forever -- holding a live `CodexSession` and its child process past the tab that
#: started it.
ABANDONED_TURN_SECONDS = 120.0


@dataclass(frozen=True, slots=True)
class TurnRequest:
    """One turn's validated-by-the-bridge inputs.

    A value object rather than three parallel keyword arguments: the trio always travels
    together, and passing them separately made every caller a five-argument call whose
    order mattered at the wrong moments.
    """

    prompt: str
    turn_id: str
    requested_mode: str


@dataclass(slots=True)
class _PendingTurn:
    """One in-flight turn: its generator, its request, and who is advancing it.

    The lock is per TURN rather than global: two threads may legitimately pump at
    once, but the same generator must never be advanced twice concurrently. Python
    raises `ValueError: generator already executing`, which the pump's own handler
    would then record as `provider_error` -- killing a healthy turn because a second
    tab happened to poll.
    """

    events: Any
    request: TurnRequest
    pumping: asyncio.Lock
    last_touched: float
    #: The thread advancing the generator right now, if any. A read the pump gave up
    #: waiting for is still running INSIDE the generator, so a second `next()` would
    #: raise "generator already executing"; the next poll waits on the same reader.
    reader: Any = None
    #: Where that reader posts its one result. A queue rather than a future because
    #: nothing tied to an event loop survives the request that created it.
    results: Any = None


#: How long one `/events` poll may spend advancing a live turn before it serves the
#: buffer. Bounded so the browser always gets a timely response: the turn continues
#: on the NEXT poll, which `SSE_RETRY_MILLISECONDS` already schedules.
TURN_PUMP_SECONDS = 0.5


async def _pump_turn(app: FastAPI, thread_id: str, thread: Any) -> None:
    """Advance a live turn by up to `TURN_PUMP_SECONDS`, then return.

    **Why the poll drives the turn rather than a background task.** The blocking work
    is a sync generator, so it must be offloaded; but every `thread.append(...)` has
    to stay on the event loop, because `ThreadEvents` is documented as deliberately
    not thread-safe and `_active_turn` is mutated inside `append`. A worker draining
    the whole turn would put a concurrent writer beside `_stream_events` and
    `_interrupt_turn` on that object.

    `asyncio.create_task` was the obvious alternative and does not survive: a task
    created inside a request is cancelled when its loop ends, which under
    `TestClient` is the end of that same request. Rather than depend on a loop
    outliving the request, the pump runs where the browser already is -- `/events` is
    a finite replay the client reconnects to on `SSE_RETRY_MILLISECONDS`, so the poll
    loop that renders the turn is also the loop that advances it.

    Errors become EVENTS, never exceptions: the 202 has already been sent, so a raise
    here would surface as a 500 on a POLL, and leave `_active_turn` set so every
    later turn on the thread is refused as already-active.
    """
    pending = app.state.pending_turns.get(thread_id)
    if pending is None:
        return
    pending.last_touched = time.monotonic()
    if pending.pumping.locked():
        # Another poll is already inside `next()` on this generator -- a second tab,
        # or a reconnect overlapping the previous poll. Advancing it concurrently
        # raises "generator already executing", which the handler below would convert
        # into `provider_error` and kill a healthy turn. This poll serves what is
        # already buffered; the other one is making progress.
        return

    request = pending.request
    async with pending.pumping:
        deadline = time.monotonic() + TURN_PUMP_SECONDS
        try:
            while time.monotonic() < deadline:
                produced = await _next_event(pending, deadline)
                if produced is _STILL_WAITING:
                    return  # provider is slow: serve the buffer, resume next poll
                if produced is _DRAINED:
                    # A stream that ends with NO terminal is a failure, not a quiet
                    # success: `turn_started` is already recorded, so returning here
                    # would leave `_active_turn` set with no generator left to advance
                    # it, refusing every later turn with 409. This is the case the
                    # synchronous route used to report as 503.
                    _fail_turn(
                        thread,
                        request.turn_id,
                        "provider_error",
                        "the provider produced no events for this turn",
                    )
                    _finish_turn(app, thread_id, pending)
                    return
                if produced.type == "turn_started":
                    # The route already opened this turn, synchronously, so the caller
                    # could be told 409 in the RESPONSE rather than only in the stream.
                    # Every bridge also yields its own opening envelope; recording it
                    # again raises `TurnAlreadyActive` against our own event.
                    continue
                if (
                    request.requested_mode == "read_only"
                    and produced.type in WRITE_INTENT_TYPES
                ):
                    # The read_only refusal, recorded rather than raised: the response
                    # has already gone, so a 502 has nowhere to land -- and ending the
                    # turn is what releases `_active_turn`.
                    _fail_turn(
                        thread,
                        request.turn_id,
                        "read_only_violation",
                        f"the bridge emitted {produced.type!r} during a read_only turn",
                    )
                    _finish_turn(app, thread_id, pending)
                    return
                if produced.type == "approval_required":
                    register_approval(app, thread_id, thread, produced)
                thread.append(produced.type, produced.payload, turn_id=produced.turn_id)
                if produced.type in _TERMINAL_EVENTS:
                    _finish_turn(app, thread_id, pending)
                    return
        except Exception as error:  # a dead turn must still END
            _fail_turn(
                thread,
                request.turn_id,
                "provider_error",
                f"the turn failed: {type(error).__name__}",
            )
            _finish_turn(app, thread_id, pending)


async def _next_event(pending: _PendingTurn, deadline: float) -> Any:
    """One generator advance, bounded by what remains of the pump's budget.

    `CodexSession.frames()` blocks for up to 30 seconds waiting on a stalled provider.
    Unbounded, the pump would hold the poll for that long -- withholding even the
    `turn_started` already sitting in the buffer, so the browser could not render the
    Stop control for the very turn the analyst wants to stop.

    `_STILL_WAITING` means "nothing yet, serve the buffer": the generator keeps
    running on its worker and the next poll collects the result. `abandon_on_cancel`
    lets this coroutine move on while that thread finishes its read, rather than
    blocking on it.
    """
    if pending.reader is None:
        # A plain daemon thread with a queue, NOT a task or future. Anything bound to
        # an event loop dies when that loop does, and under `TestClient` the loop ends
        # with each request -- the same trap that ruled out `asyncio.create_task`.
        # A thread survives across polls, so the generator is advanced exactly once
        # and never re-entered while a read is outstanding.
        pending.reader = _start_reader(pending)

    remaining = max(0.0, deadline - time.monotonic())
    try:
        produced = await anyio.to_thread.run_sync(
            partial(pending.results.get, True, remaining)
        )
    except queue.Empty:
        return _STILL_WAITING  # still reading; this same reader continues

    pending.reader = None
    if isinstance(produced, BaseException):
        raise produced
    return produced


def _start_reader(pending: _PendingTurn) -> threading.Thread:
    """Advance the generator once, on a thread, and post the result to the queue."""

    def read() -> None:
        try:
            pending.results.put(next(pending.events, _DRAINED))
        except BaseException as error:  # surfaced to the pump, never swallowed
            pending.results.put(error)

    thread = threading.Thread(target=read, daemon=True)
    thread.start()
    return thread


def _reap_abandoned_turns(app: FastAPI) -> None:
    """End turns nobody is polling any more.

    The pump only runs on a poll, so a browser that closes mid-reply leaves its
    generator parked with nothing to advance or close it -- holding a live
    `CodexSession` and its child process. Swept when a new turn is started, which is
    the only moment this dictionary can grow.

    The turn is FAILED, not merely dropped. Closing the generator alone would leave
    `_active_turn` set on a thread whose stream never reports an ending -- so that
    conversation would refuse every later turn with 409 while no generator remained
    to advance it. That is precisely the wedge this reaper exists to prevent.
    """
    cutoff = time.monotonic() - ABANDONED_TURN_SECONDS
    for thread_id, pending in list(app.state.pending_turns.items()):
        if pending.last_touched >= cutoff or pending.pumping.locked():
            continue
        # `has_thread` FIRST: `ThreadStore.thread()` is create-on-access and evicts
        # the oldest to make room, so calling it for a thread the store has already
        # evicted would resurrect a dead conversation, push out a live one, and write
        # the failure into a fresh log nobody is reading. An evicted thread needs no
        # terminal -- its event log is gone -- but its generator must still be closed.
        if app.state.threads.has_thread(thread_id):
            _fail_turn(
                app.state.threads.thread(thread_id),
                pending.request.turn_id,
                "provider_error",
                "the turn was abandoned before it finished",
            )
        _finish_turn(app, thread_id, pending)


def _finish_turn(
    app: FastAPI, thread_id: str, pending: _PendingTurn
) -> threading.Thread | None:
    """Drop the pending turn and close its generator.

    Closing runs the generator's own `finally`, which is what terminates a real
    provider's child process -- so a turn that ends any way at all, including an
    interrupt, must reach here or the process leaks.

    The slot is cleared only if it STILL HOLDS the turn being finished. An interrupt
    followed immediately by a new turn installs a replacement; a late terminal from
    the old generator would otherwise pop the new one, leaving a turn that is active
    in `ThreadEvents` but can never advance -- every later turn stuck at 409.
    """
    if app.state.pending_turns.get(thread_id) is pending:
        del app.state.pending_turns[thread_id]
        # NOT abandoning this thread's approvals here, deliberately. It looks like the
        # right place -- a finished turn cannot honour an allow -- but Phase 4 streams
        # `approval_required` as INERT ACTIVITY beside a `turn_completed` in the same
        # turn (`bridge.FakeAgentBridge.run_turn`), so "the turn ended" and "an
        # approval is still pending" legitimately coexist. Dropping them here made a
        # just-streamed approval undecidable the instant it appeared. The ledger is
        # bounded by COUNT instead; `abandon_thread` stays available for a future
        # paused-turn model, where a turn really does own its approvals.
    close = getattr(pending.events, "close", None)
    if close is None:
        return None

    reader = pending.reader

    def shut_down() -> None:
        # WAIT for any outstanding advance to finish, however long it takes. A reader
        # the pump gave up waiting for is still inside `next()`, and closing then
        # raises "generator already executing" -- swallowed below, leaving the
        # provider's child alive. Stop would appear to work while the process kept
        # running.
        #
        # Unbounded on purpose. A bounded join looks safer and is not: on timeout it
        # would fall through to a `close()` that raises, gets swallowed, and never
        # retries -- exactly the leak this guards against, now with a deadline
        # attached. The bridge protocol sets no maximum for one advance, so any bound
        # is a guess. This is a daemon thread holding one generator reference, so
        # waiting costs nothing and never delays a request or blocks shutdown.
        if reader is not None:
            reader.join()
        try:
            close()
        except Exception:  # pragma: no cover -- never mask the turn's own outcome
            pass

    # Closed on a THREAD, never inline. `close()` runs the generator's `finally`,
    # which for a real provider is `CodexSession.close(timeout=5.0)` -- terminating a
    # child and joining two reader threads. Called directly it would hold the sole
    # event loop for up to five seconds, freezing unrelated Studio requests and
    # partially reintroducing the very unresponsiveness this change removes.
    #
    # A thread rather than `to_thread.run_sync`, because this runs from both the async
    # pump and the SYNC interrupt route; the caller does not wait either way, since
    # nothing downstream depends on the child being gone.
    # RETURNED so a caller that must not outlive the cleanup -- application
    # shutdown -- can join it. Request paths deliberately do not: nothing they do
    # next depends on the child being gone, and waiting would put a process
    # teardown on the response path.
    shutdown_thread = threading.Thread(target=shut_down, daemon=True)
    shutdown_thread.start()
    return shutdown_thread


def _fail_turn(thread: Any, turn_id: str, category: str, detail: str) -> None:
    """Record one terminal failure, tolerating a thread that already ended.

    `append` refuses nothing here, but a turn that ended between the failure and this
    call would make the terminal `ignored_for_state` -- harmless, and preferable to
    letting a bookkeeping error mask the original fault.
    """
    try:
        thread.append(
            "turn_failed",
            {"category": category, "detail": detail},
            turn_id=turn_id,
        )
    except Exception:  # pragma: no cover -- never mask the original failure
        pass
