"""A turn is ACCEPTED, then advanced on the poll loop (#618).

Separate from `test_studio_agent_endpoints` because it tests a different thing: not
whether a route is reachable and authenticated, but whether a turn that takes REAL
TIME leaves the rest of Studio answerable while it runs. Every test here needs a
slow bridge and a polling loop, which no other endpoint test does.

The property is asserted on the wall clock and on what the stream contains
mid-flight, never on whether a task or a pending slot exists -- "a turn is pending"
is satisfiable by an implementation that then drains it inline, which is the exact
defect these guard.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

fastapi = pytest.importorskip("fastapi")

from tests.unit.test_studio_agent_endpoints import (  # noqa: E402
    _BROWSER_ORIGIN,
    API,
    _client,
    _sse_events,
    _thread,
)

pytestmark = pytest.mark.unit


class _SlowBridge:
    """A bridge whose turn takes real wall-clock time, like a real provider.

    The fake bridge completes instantly, so an inline drain LOOKS responsive: the
    turn is over before anything else could have been served. Only a turn that
    takes measurable time can show whether the loop was free while it ran.
    """

    def __init__(self, hold: float = 1.5) -> None:
        self._hold = hold
        self.started = __import__("threading").Event()

    def describe(self) -> dict[str, Any]:
        return {"bridge": "slow", "provider": "codex", "deterministic": False}

    def run_turn(self, *, prompt: str, turn_id: str, requested_mode: str):
        from seshat.studio.bridge import _event

        yield _event("turn_started", {"prompt_echo": prompt[:200]}, turn_id, 1)
        self.started.set()
        time.sleep(self._hold)  # the provider thinking
        yield _event("agent_message", {"text": "done"}, turn_id, 2)
        yield _event("turn_completed", {"status": "completed"}, turn_id, 3)


def test_a_running_turn_does_not_block_the_request(tmp_path: Path) -> None:
    """The property: a turn is ACCEPTED, not drained, before the response.

    Asserted by wall clock against a bridge that takes real time -- not by inspecting
    whether a task or a pending slot exists. "A pending turn is recorded" is
    satisfiable by an implementation that then drains it inline, which is the exact
    defect.

    The turn then advances on the polls the browser already makes: `/events` is a
    finite replay the client reconnects to, so the loop that renders a turn is the
    loop that drives it.
    """
    client, app = _client(tmp_path)
    thread_id = _thread(client)
    app.state.bridge = _SlowBridge(hold=1.5)

    started_at = time.monotonic()
    accepted = client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "summarise the readiness spine",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
        headers=_BROWSER_ORIGIN,
    )
    accept_latency = time.monotonic() - started_at

    assert accepted.status_code == 202, accepted.text
    assert accept_latency < 1.0, (
        f"POST /turns took {accept_latency:.2f}s against a 1.5s turn; it drained the "
        "whole turn before responding instead of accepting it"
    )

    # First poll: the turn is open and NOT yet finished, so this proves the response
    # was sent mid-turn rather than after it.
    streamed = client.get(f"{API}/agent/threads/{thread_id}/events")
    assert streamed.status_code == 200, streamed.text
    mid_flight = [e["type"] for e in _sse_events(streamed.text)]
    assert "turn_started" in mid_flight, mid_flight
    assert "turn_completed" not in mid_flight, (
        f"the turn had already finished when the first poll was served: {mid_flight}"
    )

    # Further polls drive it to completion.
    types: list[str] = []
    for _ in range(40):
        body = client.get(f"{API}/agent/threads/{thread_id}/events").text
        types = [e["type"] for e in _sse_events(body)]
        if "turn_completed" in types:
            break
    else:  # pragma: no cover -- only on a genuine failure
        raise AssertionError(f"the turn never completed across 40 polls: {types}")

    assert types == [
        "thread_started",
        "turn_started",
        "agent_message",
        "turn_completed",
    ], types


def test_a_live_turn_can_still_be_interrupted(tmp_path: Path) -> None:
    """Interrupt must be answerable WHILE a turn is in flight.

    This is the endpoint an inline drain made unreachable: with the whole turn
    running inside `POST /turns`, nothing could be served until it finished -- so the
    control for stopping a long turn was precisely the one you could not use.
    """
    client, app = _client(tmp_path)
    thread_id = _thread(client)
    app.state.bridge = _SlowBridge(hold=1.5)

    accepted = client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "summarise the readiness spine",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
        headers=_BROWSER_ORIGIN,
    )
    assert accepted.status_code == 202, accepted.text
    turn_id = accepted.json()["turn_id"]

    stopped = client.post(
        f"{API}/agent/threads/{thread_id}/turns/{turn_id}/interrupt",
        headers=_BROWSER_ORIGIN,
    )
    assert stopped.status_code == 204, stopped.text

    body = client.get(f"{API}/agent/threads/{thread_id}/events").text
    reasons = [
        e["payload"].get("reason")
        for e in _sse_events(body)
        if e["type"] == "turn_failed"
    ]
    assert "interrupted_by_user" in reasons, reasons

    # And the thread is usable again: the interrupt released the active turn.
    again = client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "another",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
        headers=_BROWSER_ORIGIN,
    )
    assert again.status_code == 202, again.text
