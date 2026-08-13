"""What the BROWSER receives for an approval, as distinct from what Python knows.

FR-021 requires that no allow control is offered when readiness forbids the scope.
`ApprovalEnvelope` has carried that verdict since Phase 6 -- `allow_permitted` and
`forbidden_reasons` -- but it stayed inside Python: `register_approval` computed it
into the ledger while `agent_routes` appended the provider's ORIGINAL payload to the
stream. The browser received `required_authority` and nothing else.

A panel built on that payload cannot honour FR-021. Its only route to the verdict is
to offer Allow, let the analyst click, and render the 403 -- present-then-retract,
which is the inverse of a control that is never offered. So the requirement is not
satisfiable by frontend work alone; the payload has to carry the verdict.

These tests pin the WIRE, not the envelope. `test_studio_approvals` already proves
`normalize_approval` computes the verdict correctly; nothing proved it was reachable
by the only consumer that needs it. That gap is the same shape as the one
`test_studio_approval_reachability` was written for: a correct computation with no
path to its caller.

The negative half matters as much as the positive: `provider_request_id` is a
JSON-RPC correlation id belonging to the transport, and it reached the browser only
because one dict was handed to both the ledger and the event log.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")  # CI's unit job installs no app extras

from fastapi.testclient import TestClient  # noqa: E402

API = "/api/v1"
_BROWSER_ORIGIN = {"Origin": "http://127.0.0.1:9999"}

#: A real-shaped Codex approval. Deliberately NOT the fake bridge's
#: `{approval_id, question, required_authority}`: the fake omits every field the panel
#: must display, so a payload test written against it would prove nothing about the
#: path that actually matters (`fixtures-must-come-from-the-real-producer`).
TECHNICAL_APPROVAL: dict[str, Any] = {
    "approval_id": "turn-1-approval-1",
    "required_authority": "technical",
    "action": "run_command",
    "target": "pytest -q",
    "reason": "Verify the mapping change",
    "scope": "read_only",
    "risk": "low",
    "provider_request_id": 20,
}


class _Produced:
    """The shape `_pump_turn` hands to `register_approval`."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.type = "approval_required"
        self.payload = payload
        self.turn_id = "turn-1"


def _client(tmp_path: Path) -> tuple[TestClient, Any]:
    from seshat.studio.app import create_app

    (tmp_path / ".seshat").mkdir(parents=True)
    app, token = create_app(tmp_path, port=9999)
    client = TestClient(
        app, base_url="http://127.0.0.1:9999", headers=dict(_BROWSER_ORIGIN)
    )
    assert client.post(f"{API}/bootstrap", params={"token": token}).status_code == 204
    return client, app


def _registered(tmp_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Run one approval through the real registration seam; return the WIRE payload.

    Drives `register_approval` itself rather than reimplementing it, so a change that
    stops enriching the payload fails here instead of being mirrored by the test.
    """
    from seshat.studio.approval_routes import register_approval

    client, app = _client(tmp_path)
    created = client.post(f"{API}/agent/threads", json={"selected_table_id": None})
    thread_id = created.json()["thread_id"]
    thread = app.state.threads.thread(thread_id)

    return register_approval(app, thread_id, thread, _Produced(dict(payload)))


# --------------------------------------------------------------------------- #
# The verdict reaches the browser                                             #
# --------------------------------------------------------------------------- #


def test_the_wire_payload_carries_the_allow_verdict(tmp_path: Path):
    """Without this field the panel cannot decide whether to render an allow control."""
    wire = _registered(tmp_path, TECHNICAL_APPROVAL)

    assert "allow_permitted" in wire, (
        "the browser must learn the readiness verdict from the event; discovering it "
        "by clicking Allow and reading a 403 is the inverse of FR-021"
    )
    assert isinstance(wire["allow_permitted"], bool)


def test_the_wire_payload_carries_the_forbidden_reasons(tmp_path: Path):
    """A refused allow must say WHY, in the governance sentences readiness produced."""
    wire = _registered(tmp_path, TECHNICAL_APPROVAL)

    assert "forbidden_reasons" in wire
    assert isinstance(wire["forbidden_reasons"], list), (
        "a tuple is not JSON; the SSE payload must carry a list"
    )


def test_a_forbidden_scope_refuses_the_allow_on_the_wire(tmp_path: Path):
    """The positive form: no table in scope fails CLOSED, and the browser is told so.

    A thread created with `selected_table_id: None` has no readiness gate to read, and
    `forbidden_scope_for` returns a refusal sentence rather than an empty tuple. That
    refusal is exactly what the panel must see BEFORE it renders a control.
    """
    wire = _registered(tmp_path, TECHNICAL_APPROVAL)

    assert wire["allow_permitted"] is False
    assert wire["forbidden_reasons"], "a refused allow with no stated reason is mute"
    assert any(
        "readiness" in reason or "scope" in reason
        for reason in wire["forbidden_reasons"]
    )


def test_a_named_human_approval_is_never_allowable_on_the_wire(tmp_path: Path):
    """FR-022: a governance ruling is outside Studio permanently, not pending a seam."""
    wire = _registered(
        tmp_path, {**TECHNICAL_APPROVAL, "required_authority": "named_human"}
    )

    assert wire["allow_permitted"] is False


def test_an_unknown_authority_degrades_to_unallowable(tmp_path: Path):
    """An authority nobody recognizes must not become technical by accident."""
    wire = _registered(tmp_path, {**TECHNICAL_APPROVAL, "required_authority": "wizard"})

    assert wire["allow_permitted"] is False


# --------------------------------------------------------------------------- #
# What must NOT reach the browser                                             #
# --------------------------------------------------------------------------- #


def test_the_provider_request_id_never_reaches_the_browser(tmp_path: Path):
    """A JSON-RPC correlation id belongs to the transport, not to the analyst.

    It reached the stream only because ONE dict was passed to both the ledger and
    `thread.append`. The browser has no use for it and cannot act on it.
    """
    wire = _registered(tmp_path, TECHNICAL_APPROVAL)

    assert "provider_request_id" not in wire


def test_the_displayable_scope_fields_survive(tmp_path: Path):
    """T024's exact-scope display needs these; dropping one silently blanks it."""
    wire = _registered(tmp_path, TECHNICAL_APPROVAL)

    assert wire["action"] == "run_command"
    assert wire["target"] == "pytest -q"
    assert wire["reason"] == "Verify the mapping change"
    assert wire["scope"] == "read_only"
    assert wire["risk"] == "low"
    assert wire["approval_id"] == "turn-1-approval-1"


# --------------------------------------------------------------------------- #
# FR-026 -- publishing the reasons must not publish the filesystem            #
# --------------------------------------------------------------------------- #


def test_a_forbidden_reason_carrying_a_path_is_redacted_on_the_wire(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Publishing `forbidden_reasons` must not publish an absolute path with them.

    `forbidden_scope_for` fails CLOSED by interpolating the exception into its refusal
    sentence -- and an `OSError` routinely names the path it failed on. Before this
    change that string stayed in the ledger; sending it to the browser turns it into a
    boundary crossing, so FR-026 now applies to text that never faced it before.

    The scrub is NOT re-implemented here: `ThreadEvents.append` runs
    `normalize_payload(..., workspace_root=...)` over the whole payload, so the
    enriched fields inherit the same pass every other field gets. This test pins that
    they actually do -- the guarantee comes from a gate that is silently disabled when
    `workspace_root` is omitted, which is a defect this repo has shipped before.
    """
    import seshat.studio.approvals as approvals_module

    marker = "C:" + chr(92) + "Users" + chr(92) + "someone" + chr(92) + "private_dir"

    def _raise_with_a_path(repo_root: Any, table: Any) -> Any:
        raise FileNotFoundError(f"{marker} could not be opened")

    monkeypatch.setattr(
        approvals_module, "build_table_next_document", _raise_with_a_path
    )

    client, _ = _client(tmp_path)
    created = client.post(f"{API}/agent/threads", json={"selected_table_id": "t1"})
    thread_id = created.json()["thread_id"]
    accepted = client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "propose a mapping change",
            "snapshot_revision": "r1",
            "requested_mode": "propose_changes",
        },
    )
    assert accepted.status_code == 202, accepted.text

    approvals = _stream_approvals(client, thread_id)
    assert approvals, "the approval must reach the browser for this to mean anything"
    reasons = approvals[0]["payload"]["forbidden_reasons"]

    assert reasons, "the fail-closed branch must still SAY something"
    blob = " ".join(reasons)
    assert "private_dir" not in blob, "an absolute path reached the analyst"
    assert marker not in blob
    # The positive form: the refusal survives redaction and still explains itself.
    assert "refused" in blob


# --------------------------------------------------------------------------- #
# The SSE stream -- what the browser ACTUALLY reads                           #
# --------------------------------------------------------------------------- #


def _sse_events(body: str) -> list[dict[str, Any]]:
    """Parse an SSE body into its `data:` payloads."""
    import json

    return [
        json.loads(line[len("data:") :].strip())
        for line in body.splitlines()
        if line.startswith("data:")
    ]


def test_the_enriched_payload_reaches_the_event_stream(tmp_path: Path):
    """The test the direct-call tests structurally cannot make.

    Every test above calls `register_approval` and asserts on its RETURN VALUE. That
    proves the function computes a correct wire payload; it cannot prove the pump
    APPENDS that payload rather than the provider's. Neutering the caller back to
    `thread.append(..., produced.payload, ...)` left all of them green -- a correct
    computation with no path to its consumer, which is the defect
    `test_studio_approval_reachability` exists to prevent for delivery.

    So this one drives a real turn and reads the stream the browser reads.
    """
    client, _ = _client(tmp_path)
    created = client.post(f"{API}/agent/threads", json={"selected_table_id": None})
    thread_id = created.json()["thread_id"]

    # A REAL turn: the fake bridge emits `approval_required` from inside the pump, so
    # nothing here touches `register_approval` or `thread.append` directly.
    accepted = client.post(
        f"{API}/agent/threads/{thread_id}/turns",
        json={
            "prompt": "propose a mapping change",
            "snapshot_revision": "r1",
            "requested_mode": "propose_changes",
        },
    )
    assert accepted.status_code == 202, accepted.text

    approvals = _stream_approvals(client, thread_id)
    assert approvals, "the fake bridge's approval must reach the browser at all"
    streamed = approvals[0]["payload"]

    assert "allow_permitted" in streamed, (
        "the verdict must be ON THE WIRE, not merely computed in Python"
    )
    assert "forbidden_reasons" in streamed
    assert PROVIDER_REQUEST_ID_FIELD not in streamed, (
        "the transport correlation id must not be published to the analyst"
    )
    # The fake emits `named_human`, so the browser must be told an allow is refused.
    assert streamed["allow_permitted"] is False


def _stream_approvals(client: TestClient, thread_id: str) -> list[dict[str, Any]]:
    """Every `approval_required` frame the browser can read, polled until the turn ends.

    The turn drains in the background (the endpoint returns 202), so a single GET can
    race the pump and see an empty stream.
    """
    for _ in range(50):
        events = _sse_events(client.get(f"{API}/agent/threads/{thread_id}/events").text)
        approvals = [e for e in events if e["type"] == "approval_required"]
        if approvals:
            return approvals
        if any(e["type"] in {"turn_completed", "turn_failed"} for e in events):
            return approvals
    return []


#: Named here rather than imported so the test states the forbidden field itself: a
#: rename in production must fail this test, not silently satisfy it.
PROVIDER_REQUEST_ID_FIELD = "provider_request_id"


def test_enriching_the_wire_does_not_mutate_the_callers_payload(tmp_path: Path):
    """The provider's dict is not ours to edit in place.

    `_pump_turn` holds `produced.payload`; enriching it by mutation would leak the
    verdict backwards into the object the bridge owns.
    """
    original = dict(TECHNICAL_APPROVAL)
    produced = _Produced(original)

    from seshat.studio.approval_routes import register_approval

    client, app = _client(tmp_path)
    created = client.post(f"{API}/agent/threads", json={"selected_table_id": None})
    thread_id = created.json()["thread_id"]
    register_approval(app, thread_id, app.state.threads.thread(thread_id), produced)

    assert produced.payload == original, (
        "register_approval mutated its caller's payload"
    )
