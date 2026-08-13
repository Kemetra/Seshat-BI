"""Route-level tests for the approval relay (T026, T027).

The OpenAPI assertion here is the structural one: FR-022 says Studio must not
record a named-human business decision, and the cheapest way to prove that is to
show the schema exposes no endpoint that could. It is stated in the positive form
too -- the ONE approval route that exists is the technical relay -- so deleting
the relay entirely cannot make this file pass.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")  # CI's unit job installs no app extras

from fastapi.testclient import TestClient  # noqa: E402

from seshat.studio.approvals import normalize_approval  # noqa: E402

API = "/api/v1"

#: See test_studio_agent_endpoints: enforcement step 2 refuses a POST with no Origin,
#: which is deliberate CSRF protection. The header belongs in the client.
_BROWSER_ORIGIN = {"Origin": "http://127.0.0.1:9999"}

TECHNICAL_EVENT = {
    "approval_id": "turn-1-approval-1",
    "required_authority": "technical",
    "action": "run_command",
    "target": "pytest -q",
    "reason": "Verify the mapping change",
    "scope": "read_only",
    "risk": "low",
}

BUSINESS_EVENT = {
    "approval_id": "turn-1-approval-2",
    "required_authority": "named_human",
    "action": "apply_change",
    "target": "mappings/example/source-map.yaml",
    "reason": "Add the missing grain declaration",
    "scope": "propose_changes",
    "risk": "high",
}

#: The path the CONTRACT specifies (`studio-api.yaml`, `respondToToolApproval`) --
#: thread-scoped, with no turn segment. An earlier draft of this suite invented a
#: `/turns/{turn_id}/` level; the contract is the authority, so the route follows it.
APPROVAL_PATH = f"{API}/agent/threads/{{thread_id}}/approvals/{{approval_id}}"


def _client(tmp_path: Path) -> tuple[TestClient, Any]:
    """A booted app plus an authenticated client, exactly as a browser gets one."""
    from seshat.studio.app import create_app

    (tmp_path / ".seshat").mkdir(parents=True)
    app, token = create_app(tmp_path, port=9999)
    client = TestClient(
        app, base_url="http://127.0.0.1:9999", headers=dict(_BROWSER_ORIGIN)
    )
    exchange = client.post(f"{API}/bootstrap", params={"token": token})
    assert exchange.status_code == 204, exchange.text
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


def _armed(tmp_path: Path, event: dict[str, Any], forbidden: list[str] | None = None):
    """A booted client with one approval already registered on a real thread.

    Every relay test needs the same three steps -- boot, open a thread, register an
    envelope -- and repeating them inline made the assertion the least visible line in
    each test. Returns the client and the thread the approval belongs to.
    """
    client, app = _client(tmp_path)
    thread_id = _thread(client)
    app.state.pending_approvals.register(
        normalize_approval(event, forbidden or [], thread_id=thread_id)
    )
    return client, app, thread_id


# --------------------------------------------------------------------------- #
# The structural boundary (T027)                                              #
# --------------------------------------------------------------------------- #


def test_no_business_decision_route_can_mutate(tmp_path: Path):
    """FR-022: Studio may PREPARE business-decision summaries, never RECORD them.

    The assertion is about METHODS, not path names. `/decisions` legitimately exists
    as a contract-specified GET (`listDecisionSummaries`) -- read-only prepared
    summaries are the half FR-022 allows. What must not exist is a mutating verb on
    any decision path, because that is the half it forbids.
    """
    _, app = _client(tmp_path)
    paths = app.openapi()["paths"]
    mutating = {"post", "put", "patch", "delete"}
    offenders = {
        f"{method.upper()} {path}"
        for path, operations in paths.items()
        if "decision" in path.lower() or "business" in path.lower()
        for method in operations
        if method.lower() in mutating
    }
    assert offenders == set()
    # Positive form: the read-only summary route IS present, and IS a GET only.
    assert set(paths[f"{API}/decisions"]) == {"get"}


def test_the_only_approval_route_is_the_technical_relay(tmp_path: Path):
    _, app = _client(tmp_path)
    paths = app.openapi()["paths"]
    assert [p for p in paths if "approval" in p.lower()] == [APPROVAL_PATH]


def test_no_capability_is_advertised_that_this_build_cannot_deliver():
    """`technical_approvals` is True only while a delivery seam actually exists.

    Now tied to the CAPABILITY rather than to a date or a phase number: the flag and
    the seam are asserted together, so a refactor that removes delivery must fail here
    instead of leaving the browser told it can carry an approval to completion.

    `business_decision_recording` stays const False -- FR-022 places that outside
    Studio permanently, and no seam will ever flip it.
    """
    from seshat.studio.app import _bootstrap_capabilities

    capabilities = _bootstrap_capabilities()
    assert capabilities["technical_approvals"] is True
    assert capabilities["business_decision_recording"] is False


def test_the_advertised_capability_is_backed_by_a_reachable_delivery_seam():
    """Pins the capability to a seam that is CALLED, not merely importable.

    The predecessor of this test asserted `not hasattr(AgentBridge,
    "respond_to_approval")` -- an implementation SHAPE. Delivery landed as a free
    function over a `FrameSink` instead of a Protocol method, so that assertion stayed
    green while the capability it guarded shipped: the guard read as reassurance while
    guarding nothing.

    This version asserts what actually matters -- that the relay module reaches the
    delivery function -- so any refactor that strands delivery breaks the flag's test
    rather than passing silently. Shipped-but-uncalled code is a defect this repo has
    seen before (#618).
    """
    import inspect

    from seshat.studio import approval_routes

    source = inspect.getsource(approval_routes)
    assert "deliver_decision" in source, (
        "the relay must reach the delivery seam; a capability advertised without a "
        "caller is the fail-open this test exists to prevent"
    )


# --------------------------------------------------------------------------- #
# The relay (T026)                                                            #
# --------------------------------------------------------------------------- #


def test_an_unknown_approval_id_is_refused_with_a_problem(tmp_path: Path):
    client, _, thread_id = _armed(tmp_path, TECHNICAL_EVENT)
    response = _decide(client, thread_id, "never-registered", allow=True)
    assert response.status_code == 409, response.text
    assert "recovery_action" in response.json()


def test_a_named_human_approval_is_refused_through_the_route(tmp_path: Path):
    client, _, thread_id = _armed(tmp_path, BUSINESS_EVENT)
    response = _decide(client, thread_id, "turn-1-approval-2", allow=True)
    # 204 here would mean Studio granted a governance ruling. 403 is the contract's
    # code for "the allow itself was impermissible", distinct from 409's "not
    # awaiting a decision".
    assert response.status_code == 403, response.text
    assert "named_human" in response.text


def test_a_readiness_blocked_allow_is_refused_with_the_reason(tmp_path: Path):
    client, _, thread_id = _armed(
        tmp_path, TECHNICAL_EVENT, ["no silver before mapping is cleared"]
    )
    response = _decide(client, thread_id, "turn-1-approval-1", allow=True)
    assert response.status_code == 403, response.text
    assert "no silver before mapping is cleared" in response.text


def test_an_unrecognized_decision_is_refused_rather_than_coerced(tmp_path: Path):
    client, _, thread_id = _armed(tmp_path, TECHNICAL_EVENT)
    for body in ({}, {"decision": "yes"}, {"allow": True}):
        response = client.post(
            f"{API}/agent/threads/{thread_id}/approvals/turn-1-approval-1", json=body
        )
        assert response.status_code == 422, f"{body} -> {response.text}"
    # The approval is still live: a malformed request must not consume it.
    assert (
        _decide(client, thread_id, "turn-1-approval-1", allow=False).status_code == 204
    )


def test_a_technical_allow_succeeds_once_then_is_refused(tmp_path: Path):
    client, _, thread_id = _armed(tmp_path, TECHNICAL_EVENT)
    first = _decide(client, thread_id, "turn-1-approval-1", allow=True)
    assert first.status_code == 204, first.text
    assert (
        _decide(client, thread_id, "turn-1-approval-1", allow=True).status_code == 409
    )


def test_a_deny_is_accepted_and_also_burns_the_id(tmp_path: Path):
    client, _, thread_id = _armed(tmp_path, TECHNICAL_EVENT)
    assert (
        _decide(client, thread_id, "turn-1-approval-1", allow=False).status_code == 204
    )
    assert (
        _decide(client, thread_id, "turn-1-approval-1", allow=False).status_code == 409
    )


def test_a_real_readiness_gate_blocks_an_allow_end_to_end(tmp_path: Path):
    """The REAL chain, no monkeypatch: agent_next -> forbidden_reasons -> 403.

    Every other route test opens its thread with `selected_table_id: None`, which hits
    `forbidden_scope_for`'s no-table refusal -- a different branch. This one names a
    table so `build_table_next_document` actually runs, and asserts the sentence the
    readiness gate itself produced reaches the analyst.
    """
    client, app = _client(tmp_path)
    created = client.post(
        f"{API}/agent/threads", json={"selected_table_id": "retail_store_sales"}
    )
    assert created.status_code == 201, created.text
    thread_id = created.json()["thread_id"]

    from seshat.studio.approval_routes import register_approval, selected_table

    thread = app.state.threads.thread(thread_id)
    assert selected_table(thread) == "retail_store_sales"

    class _Produced:
        payload = {**TECHNICAL_EVENT}

    register_approval(app, thread_id, thread, _Produced())
    envelope = app.state.pending_approvals.envelope("turn-1-approval-1")
    assert envelope is not None
    # A fresh workspace has every gate closed, so the real document forbids plenty.
    assert envelope.forbidden_reasons, "the real readiness gate forbade nothing"
    assert envelope.allow_permitted is False

    refused = _decide(client, thread_id, "turn-1-approval-1", allow=True)
    assert refused.status_code == 403, refused.text
    assert "Mapping Ready" in refused.text or "silver" in refused.text.lower()


def test_an_approval_is_not_decidable_through_another_threads_url(tmp_path: Path):
    """The id is the capability, so it must not be usable from any thread that asks."""
    client, app = _client(tmp_path)
    owner = _thread(client)
    intruder = _thread(client)
    app.state.pending_approvals.register(
        normalize_approval(TECHNICAL_EVENT, [], thread_id=owner)
    )
    assert _decide(client, intruder, "turn-1-approval-1", allow=True).status_code == 409
    # Still live for its own thread: the refusal must not have consumed it.
    assert _decide(client, owner, "turn-1-approval-1", allow=True).status_code == 204


def test_an_unknown_thread_is_refused(tmp_path: Path):
    client, _, _ = _armed(tmp_path, TECHNICAL_EVENT)
    response = _decide(client, "no-such-thread", "turn-1-approval-1", allow=True)
    assert response.status_code == 404, response.text


# --------------------------------------------------------------------------- #
# The pause (T024)                                                            #
# --------------------------------------------------------------------------- #


def test_the_pause_state_is_the_one_the_contract_already_names():
    """Not a new string: the contract's enum already carries this state."""
    from seshat.studio.agent_routes import THREAD_STATES

    assert "awaiting_technical_approval" in THREAD_STATES


def test_an_emitted_approval_is_registered_so_the_relay_can_find_it(tmp_path: Path):
    """The pump must REGISTER an approval it streams, or the relay 409s on every
    decision -- the approval would render in the browser and be undecidable."""
    client, app = _client(tmp_path)
    thread_id = _thread(client)
    started = client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "Please change the mapping",
            "requested_mode": "propose_changes",
        },
    )
    assert started.status_code == 202, started.text

    # Drain the turn the way the browser does: poll the finite replay.
    approval_ids: list[str] = []
    for _ in range(12):
        body = client.get(f"{API}/agent/threads/{thread_id}/events").text
        approval_ids += [
            json.loads(line[len("data:") :])["payload"]["approval_id"]
            for line in body.splitlines()
            if line.startswith("data:")
            and json.loads(line[len("data:") :])["type"] == "approval_required"
        ]
        if approval_ids:
            break
    # An ASSERTION, not a skip: FakeAgentBridge is deterministic, so "no approval was
    # emitted" is a real failure. A skip here would stop enforcing while still looking
    # green -- the same trap that hid T023's uncertified state.
    assert approval_ids, (
        "the fake bridge emitted no approval_required for a change prompt"
    )

    # The positive form: the id the browser saw is the id the ledger knows.
    assert app.state.pending_approvals.envelope(approval_ids[0]) is not None
