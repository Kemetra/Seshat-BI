"""What a route hands a bridge's `run_turn`, beyond the prompt itself.

Split from `agent_routes` so the per-turn wiring is reviewable on its own and carries
no FastAPI import. Two seams live here:

- **the session publisher** -- a per-turn closure that registers the turn's live
  provider session so the approval relay can answer the child blocked on it;
- **the turn context** -- the governance reminder, requested mode and readiness facts
  the provider must see before the analyst's prompt (`turn_context.py`).

Each is passed only to a bridge whose `run_turn` declares the parameter: keyed on the
capability, not on the bridge's class, so `FakeAgentBridge` is unaffected.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from seshat.studio import projection
from seshat.studio.turn_context import (
    RedactionScope,
    build_turn_context,
    render_turn_context,
)


def known_table_ids(app: Any) -> frozenset[str]:
    """The table ids the current workspace snapshot actually contains."""
    snapshot = projection.build_workspace_snapshot(
        app.state.launch.workspace_root, agent_health=app.state.agent_health
    )
    return frozenset(table.table_id for table in snapshot.tables)


def turn_kwargs(
    app: Any, thread_id: str, *, table_id: str | None, requested_mode: str
) -> dict[str, Any]:
    """The optional `run_turn` arguments this bridge accepts, and nothing else."""
    accepted = inspect.signature(app.state.bridge.run_turn).parameters
    kwargs: dict[str, Any] = {}
    if "on_session" in accepted:
        kwargs["on_session"] = session_publisher(app, thread_id)
    if "turn_context" in accepted:
        kwargs["turn_context"] = rendered_context(
            app, table_id=table_id, requested_mode=requested_mode
        )
    return kwargs


def rendered_context(app: Any, *, table_id: str | None, requested_mode: str) -> str:
    """The Turn Context for this workspace, redacted as it is built.

    A table that vanished since the thread was bound is dropped rather than raised:
    the business-approval reminder must still reach the provider, and a turn that
    failed to start over missing context would hide the reminder entirely.
    """
    snapshot = projection.build_workspace_snapshot(
        app.state.launch.workspace_root, agent_health=app.state.agent_health
    )
    scope = RedactionScope(workspace_root=app.state.launch.workspace_root)
    try:
        context = build_turn_context(
            snapshot, table_id=table_id, requested_mode=requested_mode, redaction=scope
        )
    except KeyError:
        context = build_turn_context(
            snapshot, table_id=None, requested_mode=requested_mode, redaction=scope
        )
    return render_turn_context(context)


def session_publisher(app: Any, thread_id: str) -> Callable[[Any], None]:
    """A per-turn closure that registers, then retracts, ITS OWN session only.

    Passed INTO this turn's `run_turn`, never stored on the bridge: `app.state.bridge`
    is ONE instance shared by every thread and `run_turn` is lazy, so a callback
    installed on it was read by whichever turn advanced next -- one thread's session
    registered under another thread's key.

    Keyed by thread: the per-thread active-turn guard allows one live turn per thread,
    and an approval envelope names its thread, not its turn. The identity check on
    retract is what makes that key safe -- a turn that ends late (reaped after its
    successor started) must not pop the successor's live session.
    """
    mine: list[Any] = []

    def publish(session: Any) -> None:
        sessions = app.state.provider_sessions
        if session is not None:
            mine[:] = [session]
            sessions[thread_id] = session
            return
        if mine and sessions.get(thread_id) is mine[0]:
            sessions.pop(thread_id, None)
        mine.clear()

    return publish
