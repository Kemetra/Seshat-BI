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
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
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


def _parse_last_event_id(raw: str | None) -> int | None:
    """`None` for absent, an int for valid, and `ValueError` for garbage.

    Absent and zero are NOT the same thing to the store, and neither may be conflated
    with unparseable: treating garbage as 0 would replay the whole buffer to a client
    that asked to resume, duplicating everything it had already rendered.
    """
    if raw is None or raw.strip() == "":
        return None
    return int(raw.strip())  # ValueError propagates to the route


def register_agent_routes(app: FastAPI) -> None:
    """Register the thread, turn, interrupt, and event-stream routes."""
    from seshat.studio.app import API_PREFIX

    def _threads() -> Any:
        return app.state.threads

    def _bridge() -> Any:
        return app.state.bridge

    @app.post(f"{API_PREFIX}/agent/threads", status_code=201)
    async def create_thread(body: dict[str, Any] | None = None) -> Any:
        """Create a thread and record its opening event."""
        thread_id = f"thread-{uuid.uuid4().hex[:12]}"
        selected = (body or {}).get("selected_table_id")
        thread = _threads().thread(thread_id)
        thread.append("thread_started", {"selected_table_id": selected})
        return {"thread_id": thread_id, "state": "ready"}

    @app.post(f"{API_PREFIX}/agent/threads/{{thread_id}}/turns", status_code=202)
    async def start_turn(thread_id: str, body: dict[str, Any]) -> Any:
        """Run one turn through the bridge, recording every event it yields.

        The fake bridge completes synchronously, so this drains the generator before
        responding. A streaming provider will need the drain moved to a background task;
        the event store is already the handoff point for that, which is why the route
        records into it rather than returning events directly.
        """
        if not _threads().has_thread(thread_id):
            return _problem(
                404,
                "Unknown thread",
                "No agent thread matches that identifier.",
                "Start a new conversation from the Command Room.",
            )

        turn_id = f"turn-{uuid.uuid4().hex[:12]}"
        thread = _threads().thread(thread_id)
        try:
            recorded = _record_turn(
                thread,
                _bridge(),
                prompt=str(body.get("prompt", "")),
                turn_id=turn_id,
                requested_mode=str(body.get("requested_mode", "")),
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

    @app.post(
        f"{API_PREFIX}/agent/threads/{{thread_id}}/turns/{{turn_id}}/interrupt",
        status_code=204,
    )
    async def interrupt_turn(thread_id: str, turn_id: str) -> Response:
        if not _threads().has_thread(thread_id):
            return _problem(
                404,
                "Unknown thread",
                "No agent thread matches that identifier.",
                "Start a new conversation from the Command Room.",
            )
        try:
            _threads().thread(thread_id).interrupt(turn_id)
        except ValueError as inactive:
            return _problem(
                409,
                "No live turn to interrupt",
                str(inactive),
                "The turn has already ended; no action is needed.",
            )
        return Response(status_code=204)

    @app.get(f"{API_PREFIX}/agent/threads/{{thread_id}}/events")
    async def stream_events(thread_id: str, request: Request) -> Response:
        """Replay what is retained, then end the response.

        A finite replay rather than an open connection: the fake bridge records
        synchronously, so everything a client needs is already in the buffer when it
        connects, and `EventSource` reconnects on its own with `Last-Event-ID`. That
        makes reconnect the SAME code path as first connect, which is the property worth
        having -- an endpoint whose resume path is only exercised after a failure is an
        endpoint whose resume path is untested.
        """
        if not _threads().has_thread(thread_id):
            return _problem(
                404,
                "Unknown thread",
                "No agent thread matches that identifier.",
                "Start a new conversation from the Command Room.",
            )
        try:
            last_seen = _parse_last_event_id(request.headers.get("Last-Event-ID"))
        except ValueError:
            return _problem(
                400,
                "Malformed Last-Event-ID",
                "The resume point must be a non-negative integer.",
                "Reload Studio to start a fresh stream.",
            )

        thread = _threads().thread(thread_id)
        try:
            events = thread.replay_after(0 if last_seen is None else last_seen)
        except ReplayExpired:
            return _problem(
                409,
                "Replay point expired",
                "Those events are no longer retained, so the stream cannot resume "
                "without a gap.",
                "Reload Studio to start a fresh stream.",
            )

        def frames() -> Iterator[str]:
            for event in events:
                yield _sse_frame(event)

        return StreamingResponse(
            frames(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )


def _record_turn(
    thread: Any, bridge: Any, *, prompt: str, turn_id: str, requested_mode: str
) -> list[Any]:
    """Drive the bridge and record each event into the thread.

    Validation happens inside the bridge, so an invalid request raises before any event
    is recorded -- a half-recorded turn would leave the stream describing something that
    never ran.
    """
    recorded = []
    for produced in bridge.run_turn(
        prompt=prompt, turn_id=turn_id, requested_mode=requested_mode
    ):
        recorded.append(
            thread.append(produced.type, produced.payload, turn_id=produced.turn_id)
        )
    return recorded
