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

import json
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from seshat.studio.events import ReplayExpired

#: Contract's `AgentThreadRef.state` enum.
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
    """`None` for absent, an int for valid, and `ValueError` for garbage.

    Absent and zero are NOT the same thing to the store, and neither may be conflated
    with unparseable: treating garbage as 0 would replay the whole buffer to a client
    that asked to resume, duplicating everything it had already rendered.
    """
    if raw is None or raw.strip() == "":
        return None
    return int(raw.strip())  # ValueError propagates to the route


def _unknown_thread() -> JSONResponse:
    """The one 404 three routes share, so its wording cannot drift between them."""
    return _problem(
        404,
        "Unknown thread",
        "No agent thread matches that identifier.",
        "Start a new conversation from the Command Room.",
    )


def _create_thread(app: FastAPI, body: dict[str, Any] | None) -> dict[str, Any]:
    """Create a thread and record its opening event."""
    thread_id = f"thread-{uuid.uuid4().hex[:12]}"
    selected = (body or {}).get("selected_table_id")
    app.state.threads.thread(thread_id).append(
        "thread_started", {"selected_table_id": selected}
    )
    return {"thread_id": thread_id, "state": "ready"}


def _start_turn(app: FastAPI, thread_id: str, body: dict[str, Any]) -> Any:
    """Run one turn through the bridge, recording every event it yields.

    The fake bridge completes synchronously, so this drains the generator before
    responding. A streaming provider will need the drain moved to a background task; the
    event store is already the handoff point for that, which is why this records into it
    rather than returning events directly.
    """
    if not app.state.threads.has_thread(thread_id):
        return _unknown_thread()

    turn_id = f"turn-{uuid.uuid4().hex[:12]}"
    try:
        recorded = _record_turn(
            app.state.threads.thread(thread_id),
            app.state.bridge,
            TurnRequest(
                prompt=str(body.get("prompt", "")),
                turn_id=turn_id,
                requested_mode=str(body.get("requested_mode", "")),
            ),
        )
    except ValueError as invalid:
        return _problem(
            422,
            "Invalid turn request",
            str(invalid),
            "Adjust the request and try again.",
        )
    if not recorded:
        return _problem(
            503,
            "Agent unavailable",
            "The agent produced no events for this turn.",
            "Check the agent health panel and retry.",
        )
    return {"turn_id": turn_id}


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
    return Response(status_code=204)


def _stream_events(app: FastAPI, thread_id: str, request: Request) -> Response:
    """Replay what is retained, then end the response.

    A finite replay rather than an open connection: the fake bridge records
    synchronously, so everything a client needs is already in the buffer when it
    connects, and `EventSource` reconnects on its own with `Last-Event-ID`. That makes
    reconnect the SAME code path as first connect -- an endpoint whose resume path is
    only exercised after a failure is an endpoint whose resume path is untested.
    """
    if not app.state.threads.has_thread(thread_id):
        return _unknown_thread()
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

    @app.post(f"{API_PREFIX}/agent/threads", status_code=201)
    async def create_thread(body: dict[str, Any] | None = None) -> Any:
        return _create_thread(app, body)

    @app.post(f"{API_PREFIX}/agent/threads/{{thread_id}}/turns", status_code=202)
    async def start_turn(thread_id: str, body: dict[str, Any]) -> Any:
        return _start_turn(app, thread_id, body)

    @app.post(
        f"{API_PREFIX}/agent/threads/{{thread_id}}/turns/{{turn_id}}/interrupt",
        status_code=204,
    )
    async def interrupt_turn(thread_id: str, turn_id: str) -> Response:
        return _interrupt_turn(app, thread_id, turn_id)

    @app.get(f"{API_PREFIX}/agent/threads/{{thread_id}}/events")
    async def stream_events(thread_id: str, request: Request) -> Response:
        return _stream_events(app, thread_id, request)


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


def _record_turn(thread: Any, bridge: Any, request: TurnRequest) -> list[Any]:
    """Drive the bridge and record each event into the thread.

    Validation happens inside the bridge, so an invalid request raises before any event
    is recorded -- a half-recorded turn would leave the stream describing something that
    never ran.
    """
    return [
        thread.append(produced.type, produced.payload, turn_id=produced.turn_id)
        for produced in bridge.run_turn(
            prompt=request.prompt,
            turn_id=request.turn_id,
            requested_mode=request.requested_mode,
        )
    ]
