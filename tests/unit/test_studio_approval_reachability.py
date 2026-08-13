"""The decision reaches a provider THROUGH THE ROUTE, not through injection.

`test_studio_approval_delivery` proves `deliver_decision` writes a correct frame when
handed a sink. It cannot prove production can FIND that sink -- and for the whole life
of PR #626 it could not: `app.state.provider_sessions` was initialized and read but
never assigned, so `_frame_sink` always returned `None`, `_deliver` took its
"no provider is waiting" branch, and every decision returned 204 while Codex stayed
blocked. Twelve green tests, dead feature.

So every test here drives the REAL path -- boot the app, register a session the way a
turn does, POST to the contract's relay route -- and asserts on what landed on the
session. The falsification is explicit: `test_an_empty_registry_is_a_reported_failure`
re-creates the original defect and requires it to be LOUD.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")  # CI's unit job installs no app extras

from fastapi.testclient import TestClient  # noqa: E402

from seshat.studio.approvals import normalize_approval  # noqa: E402

API = "/api/v1"
_BROWSER_ORIGIN = {"Origin": "http://127.0.0.1:9999"}

#: A technical approval with a provider request waiting on it. `provider_request_id`
#: is what `register_approval` reads to decide whether anything must be answered.
BLOCKED_TECHNICAL = {
    "approval_id": "turn-1-approval-1",
    "required_authority": "technical",
    "action": "run_command",
    "target": "pytest -q",
    "reason": "Verify the mapping change",
    "scope": "read_only",
    "risk": "low",
    "provider_request_id": 20,
}


class _RecordingSession:
    """Stands in for a live `CodexSession`: records frames instead of writing a pipe."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    def send(self, frame: dict[str, Any]) -> None:
        self.sent.append(frame)


def _client(tmp_path: Path) -> tuple[TestClient, Any]:
    from seshat.studio.app import create_app

    (tmp_path / ".seshat").mkdir(parents=True)
    app, token = create_app(tmp_path, port=9999)
    client = TestClient(
        app, base_url="http://127.0.0.1:9999", headers=dict(_BROWSER_ORIGIN)
    )
    assert client.post(f"{API}/bootstrap", params={"token": token}).status_code == 204
    return client, app


def _thread(client: TestClient) -> str:
    created = client.post(f"{API}/agent/threads", json={"selected_table_id": None})
    assert created.status_code == 201, created.text
    return created.json()["thread_id"]


def _decide(client: TestClient, thread_id: str, approval_id: str, *, allow: bool):
    return client.post(
        f"{API}/agent/threads/{thread_id}/approvals/{approval_id}",
        json={"decision": "allow_once" if allow else "deny"},
    )


def _armed(tmp_path: Path, *, register_session: bool):
    """A booted client with one blocked approval, and optionally its live session.

    `register_session=False` reproduces the original defect exactly: the approval is
    decidable and names a waiting provider request, but nothing put a session in the
    registry for the route to find.
    """
    client, app = _client(tmp_path)
    thread_id = _thread(client)
    session = _RecordingSession()
    if register_session:
        app.state.provider_sessions[thread_id] = session
    app.state.pending_approvals.register(
        normalize_approval(
            BLOCKED_TECHNICAL,
            [],
            thread_id=thread_id,
            request_id=BLOCKED_TECHNICAL["provider_request_id"],
        )
    )
    return client, app, thread_id, session


# --------------------------------------------------------------------------- #
# The round trip, end to end through the route                                #
# --------------------------------------------------------------------------- #


def test_an_allowed_decision_reaches_the_registered_session(tmp_path: Path):
    """The assertion the injection tests structurally cannot make."""
    client, _, thread_id, session = _armed(tmp_path, register_session=True)

    response = _decide(client, thread_id, "turn-1-approval-1", allow=True)

    assert response.status_code == 204, response.text
    assert len(session.sent) == 1, "the route must write exactly one reply"
    assert session.sent[0] == {
        "jsonrpc": "2.0",
        "id": 20,
        "result": {"decision": "approved"},
    }


def test_a_denied_decision_also_reaches_the_session(tmp_path: Path):
    """A deny that never lands leaves the provider blocked exactly like an allow."""
    client, _, thread_id, session = _armed(tmp_path, register_session=True)

    assert _decide(client, thread_id, "turn-1-approval-1", allow=False).status_code == (
        204
    )
    assert session.sent[0]["result"]["decision"] == "denied"


def test_the_reply_goes_only_to_the_thread_that_raised_it(tmp_path: Path):
    """A second thread's session must not receive another thread's decision."""
    client, app, thread_id, session = _armed(tmp_path, register_session=True)
    other_thread = _thread(client)
    other_session = _RecordingSession()
    app.state.provider_sessions[other_thread] = other_session

    _decide(client, thread_id, "turn-1-approval-1", allow=True)

    assert len(session.sent) == 1
    assert other_session.sent == [], "the wrong provider was answered"


# --------------------------------------------------------------------------- #
# The defect this file exists to make impossible to ship again                #
# --------------------------------------------------------------------------- #


def test_an_empty_registry_is_a_reported_failure_not_a_204(tmp_path: Path):
    """Reproduces PR #626's defect and requires it to be LOUD.

    An approval that names `provider_request_id` has a provider BLOCKED on it. If no
    session resolves, the round trip did not close, and 204 would tell the analyst it
    did. That silent 204 is precisely how the dead seam shipped green.

    502 rather than 500: the failure is upstream of a well-formed request.
    """
    client, _, thread_id, _ = _armed(tmp_path, register_session=False)

    response = _decide(client, thread_id, "turn-1-approval-1", allow=True)

    assert response.status_code == 502, (
        "an unanswerable blocked approval must report failure, not 204 -- "
        f"got {response.status_code}"
    )
    assert "recovery_action" in response.json()


def test_a_real_turn_registers_its_provider_session(tmp_path: Path):
    """The production WRITER, not an injected one -- the half that was missing.

    Every other test here puts a session into the registry itself, which is precisely
    how the dead seam looked healthy: the lookup was fine, nothing populated it. This
    drives a real `CodexBridge` turn against a scripted child and asserts the registry
    is populated by the turn, then emptied when it ends.
    """
    import sys

    from seshat.studio.codex_bridge import CodexBridge
    from seshat.studio.codex_process import CodexLaunchPlan

    client, app = _client(tmp_path)
    script = Path(__file__).parent / "_codex_child_script.py"
    fixture_root = Path(__file__).resolve().parents[1] / "fixtures" / "codex_app_server"
    if not (script.exists() and fixture_root.exists()):
        pytest.skip("the scripted Codex child or its fixtures are unavailable")

    app.state.bridge = CodexBridge(
        CodexLaunchPlan(argv=(sys.executable, str(script), "thread_turn"), cwd=tmp_path)
    )
    thread_id = _thread(client)

    started = client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={"prompt": "what is the grain?", "requested_mode": "read_only"},
    )
    assert started.status_code == 202, started.text

    # Observe the TRANSITIONS, not the state. The scripted child runs a whole turn
    # inside a single poll, so sampling `provider_sessions` between polls can miss
    # both edges and report a working seam as broken. Wrapping the closure the route
    # installed records each edge while still exercising the real one underneath.
    # Records what the REGISTRY held at each edge, not merely that a callback fired.
    # An earlier draft asserted on the callback alone and passed with the route's
    # wiring deleted, because `CodexBridge.__init__` installs a no-op default -- the
    # spy dutifully recorded edges into nothing. What must be proven is that the
    # session became findable by `_frame_sink`, which means the dict.
    installed = app.state.bridge.on_session
    registry_at_edge: list[Any] = []

    def spy(session: Any) -> None:
        installed(session)
        registry_at_edge.append(app.state.provider_sessions.get(thread_id))

    app.state.bridge.on_session = spy

    # The generator is lazy: nothing runs until a poll advances it. Draining the event
    # stream is what a browser does, and what opens the session.
    for _ in range(40):
        client.get(f"{API}/agent/threads/{thread_id}/events")
        if app.state.pending_turns.get(thread_id) is None:
            break

    assert registry_at_edge, "the bridge never signalled a session at all"
    assert registry_at_edge[0] is not None, (
        "a live Codex turn opened a session but nothing put it in "
        "`provider_sessions`, so `_frame_sink` would miss and a decided approval "
        "would never reach the blocked provider -- the PR #626 defect"
    )
    assert registry_at_edge[-1] is None, (
        "the session outlived its turn; a closed child left in the registry accepts "
        "a decision and drops it"
    )
    assert thread_id not in app.state.provider_sessions


def test_an_approval_with_no_waiting_provider_still_answers_204(tmp_path: Path):
    """The fake bridge's normal case must NOT become an error.

    `FakeAgentBridge` streams `approval_required` as inert activity with no server
    request beneath it. There is genuinely nothing to answer, so the decision stands
    recorded and the route succeeds. Discriminating on `request_id` is what keeps this
    apart from the defect above -- without it, either the fake breaks or the defect
    stays silent.
    """
    client, app = _client(tmp_path)
    thread_id = _thread(client)
    app.state.pending_approvals.register(
        normalize_approval(
            {"approval_id": "a1", "required_authority": "technical"},
            [],
            thread_id=thread_id,
        )
    )

    assert _decide(client, thread_id, "a1", allow=True).status_code == 204
