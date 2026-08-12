"""T016 -- the agent thread, turn, and SSE routes as a BROWSER meets them.

The event-store tests are all in-process, so they pass whether or not the endpoint is
reachable. That gap has already produced two shipped-broken states in this feature (a
hardcoded port that made every request 403, and a frontend that returned 404 at `/`), so
these tests drive the real ASGI app through a real client.

The load-bearing constraint is one browsers impose and nothing in-process reveals:
**`EventSource` cannot set request headers.** No `Authorization`, no custom token
header. Studio's session is an `HttpOnly` cookie, which the browser replays on the SSE
request automatically -- so the stream authenticates the same way every other route
does, and the token never appears in a URL where logs and history would keep it.
The tests below pin that: the events route runs the full enforcement chain, and it is
reachable with nothing but the cookie.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NamedTuple

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

API = "/api/v1"


#: A real browser sends `Origin` on every mutating request, and enforcement step 2
#: refuses a POST without one -- deliberate CSRF protection. `TestClient` sends no
#: `Origin` unless told to, so omitting this header made every POST 403 and briefly
#: looked like the routes were unregistered. The header belongs in the client, not an
#: exemption in the guard.
_BROWSER_ORIGIN = {"Origin": "http://127.0.0.1:9999"}


def _client(tmp_path: Path) -> tuple[TestClient, Any]:
    """A booted app plus an authenticated client, exactly as a browser gets one."""
    from seshat.studio.app import create_app

    (tmp_path / ".seshat").mkdir(parents=True)
    app, token = create_app(tmp_path, port=9999)
    client = TestClient(
        app, base_url="http://127.0.0.1:9999", headers=dict(_BROWSER_ORIGIN)
    )

    # The one-time exchange the browser performs on landing; the cookie jar keeps the
    # session cookie from here on, which is the whole point.
    exchange = client.post(f"{API}/bootstrap", params={"token": token})
    assert exchange.status_code == 204, exchange.text
    return client, app


def _thread(client: TestClient) -> str:
    created = client.post(f"{API}/agent/threads", json={"selected_table_id": None})
    assert created.status_code == 201, created.text
    return created.json()["thread_id"]


def _sse_events(body: str) -> list[dict[str, Any]]:
    """Parse an SSE body into its `data:` payloads."""
    return [
        json.loads(line[len("data:") :].strip())
        for line in body.splitlines()
        if line.startswith("data:")
    ]


# --------------------------------------------------------------------------- #
# Authentication -- the browser reality                                       #
# --------------------------------------------------------------------------- #


def test_the_events_stream_is_refused_without_a_session(tmp_path: Path) -> None:
    """The stream must run the SAME enforcement chain as every other route.

    Adding the events path to the public set would have been the easy way to make
    `EventSource` work, and it would have exposed the whole conversation to any process
    that could reach the port.
    """
    from seshat.studio.app import create_app

    (tmp_path / ".seshat").mkdir(parents=True)
    app, _ = create_app(tmp_path, port=9999)
    anonymous = TestClient(app, base_url="http://127.0.0.1:9999")

    refused = anonymous.get(f"{API}/agent/threads/t1/events")

    assert refused.status_code == 401


def test_the_stream_is_reachable_with_only_the_session_cookie(tmp_path: Path) -> None:
    """`EventSource` can send NOTHING but cookies -- so cookies must be sufficient.

    If this route needed a header, the browser could never open the stream and the chat
    UI would be dead on arrival while every in-process test stayed green.
    """
    client, _ = _client(tmp_path)
    thread_id = _thread(client)

    assert client.cookies.get("seshat_studio_session"), "the session lives in a cookie"

    streamed = client.get(f"{API}/agent/threads/{thread_id}/events")

    assert streamed.status_code == 200
    assert streamed.headers["content-type"].startswith("text/event-stream")


# --------------------------------------------------------------------------- #
# Threads and turns                                                          #
# --------------------------------------------------------------------------- #


def test_creating_a_thread_returns_the_contract_shape(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    created = client.post(f"{API}/agent/threads", json={"selected_table_id": None})

    assert created.status_code == 201
    body = created.json()
    assert set(body) == {"thread_id", "state"}
    assert body["state"] in {
        "starting",
        "ready",
        "running",
        "awaiting_technical_approval",
        "completed",
        "failed",
        "interrupted",
    }


def test_starting_a_turn_returns_202_and_a_turn_id(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    thread_id = _thread(client)

    accepted = client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "what is blocking the gold layer?",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
    )

    assert accepted.status_code == 202, accepted.text
    assert accepted.json()["turn_id"]


class Refusal(NamedTuple):
    """One expected refusal of `POST /turns`.

    A named tuple rather than four positional parameters: the case is one concept, and
    `Refusal(known_thread=False, ...)` reads at the call site where a bare `False` in
    position one does not.
    """

    known_thread: bool
    prompt: str
    mode: str
    expected_status: int


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(Refusal(False, "hello", "read_only", 404), id="unknown_thread"),
        pytest.param(Refusal(True, "   ", "read_only", 422), id="whitespace_prompt"),
        pytest.param(Refusal(True, "", "read_only", 422), id="missing_prompt"),
        pytest.param(Refusal(True, "do the thing", "root_shell", 422), id="bad_mode"),
    ],
)
def test_a_turn_request_is_refused_with_the_contracted_status(
    tmp_path: Path, case: Refusal
) -> None:
    """Every refusal path for `POST /turns`, in one table.

    Written as a table because three of these were byte-for-byte identical apart from
    the payload and the expected code, and a fourth (absent prompt) was missing
    entirely -- the usual cost of copy-paste tests is that the gap is invisible.
    """
    client, _ = _client(tmp_path)
    thread_id = _thread(client) if case.known_thread else "nope"

    refused = client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": case.prompt,
            "snapshot_revision": "r1",
            "requested_mode": case.mode,
        },
    )

    assert refused.status_code == case.expected_status, refused.text


# --------------------------------------------------------------------------- #
# The stream itself                                                           #
# --------------------------------------------------------------------------- #


def test_the_stream_carries_the_turn_events_in_order(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    thread_id = _thread(client)
    client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "explain what is blocking the gold layer",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
    )

    body = client.get(f"{API}/agent/threads/{thread_id}/events").text
    events = _sse_events(body)

    assert events, "the recorded turn must be replayed to a connecting browser"
    sequences = [event["sequence"] for event in events]
    assert sequences == sorted(sequences)
    assert events[0]["type"] == "thread_started"
    assert any(event["type"] == "turn_started" for event in events)


def test_each_sse_frame_carries_its_sequence_as_the_event_id(tmp_path: Path) -> None:
    """`Last-Event-ID` replay only works if the browser was TOLD the ids.

    The browser echoes back the last `id:` it saw, so omitting the field would make
    every reconnect start from zero -- or refuse, once the buffer had rotated.
    """
    client, _ = _client(tmp_path)
    thread_id = _thread(client)
    client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "hello there friend",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
    )

    body = client.get(f"{API}/agent/threads/{thread_id}/events").text

    ids = [
        line[len("id:") :].strip()
        for line in body.splitlines()
        if line.startswith("id:")
    ]
    payload_sequences = [str(event["sequence"]) for event in _sse_events(body)]
    assert ids == payload_sequences, "every frame needs an id matching its sequence"


def test_last_event_id_replays_only_what_follows(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    thread_id = _thread(client)
    client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "explain the mapping gate please",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
    )

    everything = _sse_events(client.get(f"{API}/agent/threads/{thread_id}/events").text)
    resume_from = everything[1]["sequence"]

    resumed = _sse_events(
        client.get(
            f"{API}/agent/threads/{thread_id}/events",
            headers={"Last-Event-ID": str(resume_from)},
        ).text
    )

    assert [event["sequence"] for event in resumed] == [
        event["sequence"] for event in everything if event["sequence"] > resume_from
    ]


def test_an_expired_replay_is_409_not_a_short_stream(tmp_path: Path) -> None:
    """The contract's 409. A silently shortened stream would leave the browser
    rendering a state that never existed, which is worse than a refusal."""
    client, app = _client(tmp_path)
    thread_id = _thread(client)

    # Force eviction: retention is bounded, so drive past it directly on the store.
    thread = app.state.threads.thread(thread_id)
    for _ in range(thread._retention + 5):  # noqa: SLF001 - deliberate: forcing eviction
        thread.append("agent_message", {"text": "filler"})

    expired = client.get(
        f"{API}/agent/threads/{thread_id}/events", headers={"Last-Event-ID": "1"}
    )

    assert expired.status_code == 409
    assert expired.headers["content-type"].startswith("application/problem+json")


def test_the_stream_declares_its_reconnect_interval(tmp_path: Path) -> None:
    """This endpoint is a finite replay, so reconnect IS the normal path.

    `EventSource` reconnects on its own after the response closes. Without an explicit
    `retry:` the browser uses its own default (~3s), which silently becomes the
    perceived latency of every agent reply. Declaring it makes the interval a choice.
    """
    client, _ = _client(tmp_path)
    thread_id = _thread(client)

    body = client.get(f"{API}/agent/threads/{thread_id}/events").text

    assert "retry:" in body, "the stream must tell the browser its reconnect interval"


def test_an_empty_reconnect_still_declares_the_interval(tmp_path: Path) -> None:
    """The empty responses dominate an idle thread, so they need it most.

    A preamble sent only alongside events would leave a caught-up client falling back to
    the browser default for every subsequent poll.
    """
    client, _ = _client(tmp_path)
    thread_id = _thread(client)
    first = client.get(f"{API}/agent/threads/{thread_id}/events").text
    latest = [line for line in first.splitlines() if line.startswith("id:")][-1]
    last_id = latest.split(":", 1)[1].strip()

    caught_up = client.get(
        f"{API}/agent/threads/{thread_id}/events",
        headers={"Last-Event-ID": last_id},
    )

    assert _sse_events(caught_up.text) == [], "nothing new is expected here"
    assert "retry:" in caught_up.text


def test_a_stream_for_an_unknown_thread_is_404(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    missing = client.get(f"{API}/agent/threads/never-existed/events")

    assert missing.status_code == 404


def test_a_malformed_last_event_id_is_refused_not_ignored(tmp_path: Path) -> None:
    """Silently treating garbage as 0 would replay the whole buffer to a client that
    asked for a resume, duplicating everything it already rendered."""
    client, _ = _client(tmp_path)
    thread_id = _thread(client)

    bad = client.get(
        f"{API}/agent/threads/{thread_id}/events",
        headers={"Last-Event-ID": "not-a-number"},
    )

    assert bad.status_code == 400


# --------------------------------------------------------------------------- #
# FR-015 at the boundary                                                     #
# --------------------------------------------------------------------------- #


def test_hidden_reasoning_never_reaches_the_stream(tmp_path: Path) -> None:
    """Asserted on the WIRE, which is the only place that ultimately matters."""
    client, app = _client(tmp_path)
    thread_id = _thread(client)

    app.state.threads.thread(thread_id).append(
        "agent_message",
        {"text": "visible", "reasoning": "SECRETCHAIN", "raw": {"provider": "x"}},
    )

    body = client.get(f"{API}/agent/threads/{thread_id}/events").text

    assert "SECRETCHAIN" not in body
    assert "reasoning" not in body


def test_interrupting_a_live_turn_returns_204_and_ends_it(tmp_path: Path) -> None:
    """The SUCCESS path, asserted on its own.

    An earlier version of this test accepted `in {204, 409}`. Because the fake bridge
    completes synchronously, every turn is already terminal by the time a test can
    interrupt it -- so that assertion only ever saw 409 and could not fail. The 204
    branch was reachable and completely untested, which is precisely the state that puts
    a working-looking button in the UI over an unexercised route.

    Forcing a genuinely live turn is what makes the success path testable at all.
    """
    client, app = _client(tmp_path)
    thread_id = _thread(client)
    thread = app.state.threads.thread(thread_id)
    thread.append("turn_started", {}, turn_id="live-turn")
    assert thread.active_turn_id == "live-turn", "the fixture must leave a LIVE turn"

    interrupted = client.post(
        f"{API}/agent/threads/{thread_id}/turns/live-turn/interrupt"
    )

    assert interrupted.status_code == 204, interrupted.text
    assert thread.active_turn_id is None, "the interrupt must end the turn"
    assert thread.retained()[-1].type == "turn_failed", (
        "the browser learns the turn ended from the stream, so it needs an event"
    )


def test_interrupting_an_already_finished_turn_is_409(tmp_path: Path) -> None:
    """The refusal path, also asserted on its own.

    Inventing a second ending for a completed turn would make the stream describe two
    terminals for one turn.

    The turn is driven to completion by polling first. Turns are ACCEPTED rather than
    drained now (the contract's 202), so posting one no longer leaves it finished --
    this test used to pass on a premise its own wording named, "a request the fake
    completes synchronously", which is no longer how any turn behaves.
    """
    client, _ = _client(tmp_path)
    thread_id = _thread(client)
    turn = client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "a request the fake answers quickly",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
    ).json()["turn_id"]

    for _ in range(40):
        body = client.get(f"{API}/agent/threads/{thread_id}/events").text
        if any(
            e["type"] in {"turn_completed", "turn_failed"} for e in _sse_events(body)
        ):
            break
    else:  # pragma: no cover -- only on a genuine failure
        raise AssertionError("the turn never finished, so this asserts nothing")

    refused = client.post(f"{API}/agent/threads/{thread_id}/turns/{turn}/interrupt")

    assert refused.status_code == 409, refused.text


def test_interrupting_a_turn_on_an_unknown_thread_is_404(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    missing = client.post(f"{API}/agent/threads/nope/turns/whatever/interrupt")

    assert missing.status_code == 404


# --------------------------------------------------------------------------- #
# Findings from an adversarial review of the first Phase 4 pass               #
# --------------------------------------------------------------------------- #


def test_an_absolute_path_in_an_event_is_redacted_on_the_wire(tmp_path: Path) -> None:
    """FR-026 PATH redaction, which was silently disabled for every event.

    `redact_for_boundary` gates `redact_paths` on `workspace_root`, so a
    `scrub_payload` call omitting it still scrubs credentials -- everything LOOKS
    redacted -- while every filesystem path passes through verbatim. Both
    directions matter: an in-root path must become workspace-relative, and an
    out-of-root path must not reveal the operator's home directory layout.
    """
    client, app = _client(tmp_path)
    thread_id = _thread(client)
    in_root = tmp_path / "mappings" / "secret" / "source-map.yaml"

    app.state.threads.thread(thread_id).append(
        "agent_message",
        {"text": f"read {in_root} and C:/Users/Operator/private/notes.txt"},
    )

    body = client.get(f"{API}/agent/threads/{thread_id}/events").text

    assert str(tmp_path) not in body, "an absolute workspace path reached the browser"
    assert "Operator" not in body, "an out-of-root path leaked the home layout"


@pytest.mark.parametrize("bad", ["-1", "not-a-number", "+5", "1.5"])
def test_a_bad_last_event_id_is_a_400_not_a_traceback(tmp_path: Path, bad: str) -> None:
    """The contract declares this header `type: integer, minimum: 0`.

    `-1` was the interesting one: `int("-1")` does not raise, so it reached the
    store, whose own `ValueError` escaped as an uncaught 500 WITH a traceback --
    while `app.py` promises "never a traceback, never a raw path" and this route
    already had a 400 branch describing a case it could never reach.
    """
    client, _ = _client(tmp_path)
    thread_id = _thread(client)

    refused = client.get(
        f"{API}/agent/threads/{thread_id}/events", headers={"Last-Event-ID": bad}
    )

    assert refused.status_code == 400, refused.text
    assert "Traceback" not in refused.text


def test_the_last_event_id_parser_rejects_non_ascii_digits() -> None:
    """Tested at the PARSER, because HTTP cannot carry this case.

    Headers are latin-1 by spec, so a client cannot transmit an Arabic-Indic digit
    and the endpoint test above cannot reach this branch. But `str.isdigit()` is
    True for it and `int()` accepts it, so a caller arriving another way (a future
    non-HTTP transport, a direct call) would get a value the contract's
    `type: integer` does not permit.
    """
    from seshat.studio.agent_routes import _parse_last_event_id

    with pytest.raises(ValueError, match="non-negative integer"):
        _parse_last_event_id("\u0663")


def test_a_read_only_turn_refuses_write_intent_from_a_rogue_bridge(
    tmp_path: Path,
) -> None:
    """The `read_only` boundary, enforced where a bridge cannot bypass it.

    `FakeAgentBridge` declines to propose under `read_only`, but a bridge is
    third-party code by design and a `Protocol` cannot constrain what a generator
    yields. So the property must hold at the RECORDER: a provider ignoring the mode
    -- bug, quirk, or prompt injection -- must not get write intent into the buffer.

    502 rather than 422: the request was valid and the provider misbehaved.
    """
    from seshat.studio import events as events_module

    class RogueBridge:
        def describe(self) -> dict[str, object]:
            return {"bridge": "rogue"}

        def run_turn(self, *, prompt: str, turn_id: str, requested_mode: str):
            def built(kind: str) -> events_module.StudioEvent:
                return events_module.StudioEvent(
                    thread_id="",
                    sequence=1,
                    type=kind,
                    occurred_at="2026-08-11T00:00:00Z",
                    turn_id=turn_id,
                    payload={},
                    ignored_for_state=False,
                )

            yield built("turn_started")
            yield built("file_change_proposed")
            yield built("turn_completed")

    client, app = _client(tmp_path)
    thread_id = _thread(client)
    app.state.bridge = RogueBridge()

    refused = client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "just have a look around",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
    )

    # 202, not 502: the turn is accepted before the bridge misbehaves, so the refusal
    # cannot be a status. It arrives as a terminal EVENT instead -- which is also what
    # releases `_active_turn`; the old 502 left it set, wedging every later turn on
    # the thread at 409.
    assert refused.status_code == 202, refused.text

    for _ in range(40):
        body = client.get(f"{API}/agent/threads/{thread_id}/events").text
        recorded = _sse_events(body)
        if any(e["type"] == "turn_failed" for e in recorded):
            break
    else:  # pragma: no cover -- only on a genuine failure
        raise AssertionError("the read_only refusal never ended the turn")

    assert not any(e["type"] == "file_change_proposed" for e in recorded), (
        "write intent from a rogue bridge reached the buffer during a read_only turn"
    )
    categories = [
        e["payload"].get("category") for e in recorded if e["type"] == "turn_failed"
    ]
    assert "read_only_violation" in categories, categories

    # The thread is usable again -- the refusal ENDED the turn rather than wedging it.
    again = client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "another",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
    )
    assert again.status_code == 202, again.text
    # Checked on the event TYPE, not as a substring of the body: the refusal's own
    # detail names the type it refused, so a raw `not in body` reports a leak that is
    # really the guard describing itself.
    body = client.get(f"{API}/agent/threads/{thread_id}/events").text
    assert not any(e["type"] == "file_change_proposed" for e in _sse_events(body)), (
        "write intent reached the buffer"
    )


def test_a_concurrent_turn_is_409_not_422(tmp_path: Path) -> None:
    """The contract gives 409 for a conflict and 422 for a malformed request.

    Both refusals were funnelled through `ValueError`, so a live-turn conflict was
    reported to the analyst as their own formatting mistake. Unreachable with the
    synchronous fake; live the moment a streaming bridge lands.
    """
    client, app = _client(tmp_path)
    thread_id = _thread(client)
    # Force a live turn the way a streaming bridge would leave one.
    app.state.threads.thread(thread_id).append(
        "turn_started", {}, turn_id="already-running"
    )

    conflict = client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "and another thing",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
    )

    assert conflict.status_code == 409, conflict.text


def test_the_reported_thread_state_is_in_the_contract_enum(tmp_path: Path) -> None:
    """`THREAD_STATES` existed with zero callers -- an enum validating nothing."""
    from seshat.studio.agent_routes import THREAD_STATES

    client, _ = _client(tmp_path)

    created = client.post(f"{API}/agent/threads", json={}).json()

    assert created["state"] in THREAD_STATES


def test_the_thread_store_is_bounded(tmp_path: Path) -> None:
    """`ThreadEvents` bounds its events; `ThreadStore` must bound its threads.

    The asymmetry was the defect: the bounded class stated its bound while the
    unbounded one said nothing, so a reader reasonably assumed both were bounded.
    """
    from seshat.studio.events import ThreadStore

    store = ThreadStore(max_threads=3)
    for index in range(10):
        store.thread(f"thread-{index}")

    assert len(store.known_thread_ids()) == 3
    assert not store.has_thread("thread-0"), "the oldest thread must be evicted"
    assert store.has_thread("thread-9"), "the newest thread must be retained"


# --------------------------------------------------------------------------- #
# The turn drain must not own the event loop (#618)                            #
# --------------------------------------------------------------------------- #


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
        import time

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
    import time

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
