"""`/decisions` lists the business decisions a NAMED HUMAN still owes (T027, FR-022).

The endpoint has existed since Phase 3 as `return {"items": []}` -- a hardcoded empty
list with no producer anywhere in `src/`, while `studio-api.yaml` defines a required
`items` array of `PreparedDecisionSummary`. The contract promised a shape the code never
built, and the only test asserted the path exposes `get` and nothing else: a claim about
the HTTP METHOD, never about content. An adversarial review refuted T027 on exactly that
basis, and this file is the answer.

**The data already existed.** `register_approval` deliberately registers `named_human`
items so they are "visible as a prepared summary" -- then the boundary discarded them.
Nothing new is computed here; a projection was missing.

**What this is NOT.** FR-022 places the business ruling itself outside Studio
permanently. Listing a prepared summary is not recording a decision, and
`business_decision_recording` stays const `False`. The tests below assert both halves:
the summaries appear, and no route can mutate them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")  # CI's unit job installs no app extras

from fastapi.testclient import TestClient  # noqa: E402

API = "/api/v1"
_BROWSER_ORIGIN = {"Origin": "http://127.0.0.1:9999"}

#: A governance ruling: a file change is ALWAYS `named_human` (FR-021).
NAMED_HUMAN_APPROVAL: dict[str, Any] = {
    "approval_id": "turn-1-approval-1",
    "required_authority": "named_human",
    "action": "apply_change",
    "target": "mappings/store_sales/source-map.yaml",
    "reason": "Add the missing grain declaration",
    "scope": "propose_changes",
    "risk": "low",
}

#: Studio's own to decide, and therefore NOT a business decision.
TECHNICAL_APPROVAL: dict[str, Any] = {
    **NAMED_HUMAN_APPROVAL,
    "approval_id": "turn-1-approval-2",
    "required_authority": "technical",
    "action": "run_command",
    "target": "pytest -q",
    "scope": "read_only",
}


def _client(tmp_path: Path) -> tuple[TestClient, Any]:
    from seshat.studio.app import create_app

    (tmp_path / ".seshat").mkdir(parents=True)
    app, token = create_app(tmp_path, port=9999)
    client = TestClient(
        app, base_url="http://127.0.0.1:9999", headers=dict(_BROWSER_ORIGIN)
    )
    assert client.post(f"{API}/bootstrap", params={"token": token}).status_code == 204
    return client, app


def _register(app: Any, payload: dict[str, Any], thread_id: str = "t1") -> None:
    """Register one approval the way a turn does, without driving a whole turn."""
    from seshat.studio.approvals import normalize_approval

    app.state.pending_approvals.register(
        normalize_approval(payload, [], thread_id=thread_id)
    )


def _summaries(client: TestClient) -> list[dict[str, Any]]:
    response = client.get(f"{API}/decisions")
    assert response.status_code == 200, response.text
    return response.json()["items"]


# --------------------------------------------------------------------------- #
# The summaries exist                                                         #
# --------------------------------------------------------------------------- #


def test_a_named_human_approval_appears_as_a_prepared_summary(tmp_path: Path):
    """The positive form. Before this, the endpoint returned [] no matter what."""
    client, app = _client(tmp_path)
    _register(app, NAMED_HUMAN_APPROVAL)

    items = _summaries(client)

    assert len(items) == 1
    assert items[0]["decision_id"] == "turn-1-approval-1"


def test_a_technical_approval_is_not_a_business_decision(tmp_path: Path):
    """`/decisions` lists what a NAMED HUMAN owes, not what Studio may decide itself.

    Listing a technical approval here would misreport Studio's own authority as a
    pending human obligation -- the inverse of FR-022's boundary.
    """
    client, app = _client(tmp_path)
    _register(app, TECHNICAL_APPROVAL)

    assert _summaries(client) == []


def test_each_summary_carries_every_contracted_field(tmp_path: Path):
    """`additionalProperties: false` with 5 required fields -- so exactly those five."""
    client, app = _client(tmp_path)
    _register(app, NAMED_HUMAN_APPROVAL)

    summary = _summaries(client)[0]

    assert set(summary) == {
        "decision_id",
        "question",
        "required_authority",
        "affected_scope",
        "status",
    }
    assert summary["required_authority"] == "named_human"
    assert summary["status"] == "prepared"
    assert isinstance(summary["affected_scope"], list)


def test_the_question_names_the_action_and_its_target(tmp_path: Path):
    """A summary that cannot say WHAT is being asked is not a summary.

    The provider sends no `question` on the real path -- only the fake bridge does -- so
    the sentence is built from `action` and `target`, which real Codex always sends.
    """
    client, app = _client(tmp_path)
    _register(app, NAMED_HUMAN_APPROVAL)

    question = _summaries(client)[0]["question"]

    assert "mappings/store_sales/source-map.yaml" in question


def test_a_decided_approval_leaves_the_prepared_list(tmp_path: Path):
    """`status` is const `prepared`, so a decided item cannot honestly appear here."""
    client, app = _client(tmp_path)
    _register(app, NAMED_HUMAN_APPROVAL)
    assert len(_summaries(client)) == 1

    app.state.pending_approvals.decide("turn-1-approval-1", allow=False, thread_id="t1")

    assert _summaries(client) == []


# --------------------------------------------------------------------------- #
# FR-022 -- read-only, permanently                                            #
# --------------------------------------------------------------------------- #


def test_no_route_can_mutate_a_decision_summary(tmp_path: Path):
    """Asserted by HTTP METHOD rather than by path name.

    `/decisions` legitimately exists as a contract-specified GET; what must not exist is
    any verb that WRITES one. Checking the path name would pass a `POST /decisions` that
    happened to be spelled differently.
    """
    client, _ = _client(tmp_path)

    for method in ("post", "put", "patch", "delete"):
        # `request` rather than the per-verb helpers: `TestClient.delete` takes no
        # `json`, and a body is irrelevant to whether the verb ROUTES at all.
        response = client.request(method.upper(), f"{API}/decisions")
        assert response.status_code == 405, (
            f"{method.upper()} {API}/decisions must not be routable: FR-022 places the "
            "business ruling outside Studio permanently"
        )


def test_listing_a_prepared_summary_is_not_the_same_as_recording(tmp_path: Path):
    """The distinction this test defends survives spec 140; only the flag moved.

    Recording became available with spec 140 (FR-022 named it as the successor), so the
    flag is now True. What must stay true is that the read-only summary route does NOT
    record anything: listing what a human owes is not their ruling.
    """
    client, _ = _client(tmp_path)

    capabilities = client.get(f"{API}/bootstrap/state").json()["capabilities"]
    listed = client.get(f"{API}/decisions")

    assert capabilities["business_decision_recording"] is True
    assert listed.status_code == 200
    # The GET is still read-only: nothing it returns is a recorded ruling.
    assert all(
        item.get("state") != "pending_commit" for item in listed.json().get("items", [])
    )
