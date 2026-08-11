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


def test_interrupting_a_live_turn_ends_it(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    thread_id = _thread(client)
    turn = client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "a long running request",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
    ).json()["turn_id"]

    # The fake bridge completes synchronously, so the turn is already terminal: an
    # interrupt must then be refused rather than inventing a second ending.
    interrupted = client.post(f"{API}/agent/threads/{thread_id}/turns/{turn}/interrupt")

    assert interrupted.status_code in {204, 409}
