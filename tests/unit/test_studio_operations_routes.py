"""Phase B/C/D -- the Operations and Client Review routes (spec 141).

Claims under test:

- a recovery action cannot execute without technical approval (FR-141-005/018);
- the payload is redacted and carries no aggregate (FR-141-002/008);
- ephemeral history dies on restart, durable history survives (FR-141-009/010);
- only committed approved evidence enters the client view (FR-141-021);
- an acknowledgement writes no decision (FR-141-011).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")  # CI's unit job installs no app extras

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unit import _workbench_fixtures as fixtures  # noqa: E402

pytestmark = pytest.mark.unit

API = "/api/v1"
_STORE_REL = ".seshat/semantic-decisions.yaml"
_SIGNER = "Ahmed Shaaban (owner)"


def _record_decision(client, *, commit_with=None):
    """Prepare a proposal and record a decision; optionally commit it."""
    proposal = client.post(
        f"{API}/proposals",
        json={"intent": "net of returns", "target_artifact": _STORE_REL},
    ).json()
    recorded = client.post(
        f"{API}/decisions/record",
        json={
            "signer": _SIGNER,
            "declared_authority": "owner",
            "answer": proposal["allowed_answers"][0],
            "proposal_hash": proposal["proposal_hash"],
            "workspace_revision": proposal["workspace_revision"],
        },
    )
    assert recorded.status_code == 201, recorded.text
    if commit_with is not None:
        commit_with.commit_all("decision: recorded")
    return proposal


# --- Task B2: recovery is refused without approval -----------------------------------


def test_the_operations_route_requires_a_session(tmp_path: Path):
    client = fixtures.unauthenticated_client(tmp_path)

    assert client.get(f"{API}/operations").status_code == 401


def test_a_recovery_action_is_refused_without_technical_approval(tmp_path: Path):
    """FR-141-005: a support surface that can fix things is a mutation surface."""
    client = fixtures.studio_client(tmp_path)

    response = client.post(
        f"{API}/operations/recover", json={"component": "static_gate"}
    )

    assert response.status_code == 422, response.text
    assert "approval" in response.text.lower()


def test_recovery_is_refused_even_for_an_unknown_component(tmp_path: Path):
    """The refusal is not a lookup failure dressed as a policy decision."""
    client = fixtures.studio_client(tmp_path)

    response = client.post(
        f"{API}/operations/recover", json={"component": "no_such_component"}
    )

    assert response.status_code == 422, response.text


# --- Task B3: redacted, score-free payload -------------------------------------------


def test_the_operations_payload_lists_every_component(tmp_path: Path):
    client = fixtures.studio_client(tmp_path)

    response = client.get(f"{API}/operations")
    body = response.json()

    assert response.status_code == 200, response.text
    assert len(body["components"]) == 7, "a positive assertion: empty cannot pass"


def test_the_operations_payload_is_redacted(tmp_path: Path):
    client = fixtures.studio_client(tmp_path)

    response = client.get(f"{API}/operations")

    assert "postgres" + "ql://" not in response.text
    assert str(tmp_path) not in response.text


def test_the_operations_payload_carries_no_aggregate(tmp_path: Path):
    """Searches for a numeric roll-up at the top level, not a field name."""
    client = fixtures.studio_client(tmp_path)

    body = client.get(f"{API}/operations").json()

    numeric = {k: v for k, v in body.items() if isinstance(v, (int, float))}
    assert numeric == {}, f"unexpected aggregate in operations payload: {numeric}"


# --- Task C3: ephemeral history dies on restart --------------------------------------


def test_ephemeral_history_is_gone_after_a_restart(tmp_path: Path):
    workspace = fixtures.git_workspace(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    first = fixtures.studio_client(tmp_path)
    _record_decision(first)
    before = first.get(f"{API}/operations/history").json()["runs"]
    assert before, "the fixture must produce at least one ephemeral run"

    second = fixtures.studio_client(tmp_path)  # a fresh app is a restart

    after = second.get(f"{API}/operations/history").json()["runs"]
    assert [r for r in after if r["durability"] == "ephemeral"] == []


def test_a_committed_decision_appears_as_durable_history(tmp_path: Path):
    """The paired positive case: without it, an always-empty history would pass."""
    workspace = fixtures.git_workspace(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    client = fixtures.studio_client(tmp_path)
    _record_decision(client, commit_with=workspace)

    fresh = fixtures.studio_client(tmp_path)
    runs = fresh.get(f"{API}/operations/history").json()["runs"]

    durable = [r for r in runs if r["durability"] == "durable"]
    assert durable, "a committed decision must survive as durable history"
    assert all(r["committed_source"] for r in durable)


# --- Task D1: only committed approved evidence in the client view --------------------


def test_the_client_review_route_requires_an_explicit_scope(tmp_path: Path):
    client = fixtures.studio_client(tmp_path)

    assert client.get(f"{API}/client-review").status_code == 422


def test_an_uncommitted_decision_does_not_enter_the_client_view(tmp_path: Path):
    workspace = fixtures.git_workspace(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    client = fixtures.studio_client(tmp_path)
    _record_decision(client)

    draft = client.get(f"{API}/client-review?scope={_STORE_REL}").json()

    assert draft["decisions"] == [], "uncommitted is not approved evidence"
    assert draft["pending_items"], "it must appear as PENDING, not vanish"


def test_a_committed_decision_does_enter_the_client_view(tmp_path: Path):
    """The paired positive case."""
    workspace = fixtures.git_workspace(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    client = fixtures.studio_client(tmp_path)
    _record_decision(client, commit_with=workspace)

    draft = client.get(f"{API}/client-review?scope={_STORE_REL}").json()

    assert len(draft["decisions"]) == 1


def test_the_client_view_hides_technical_controls(tmp_path: Path):
    workspace = fixtures.git_workspace(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    client = fixtures.studio_client(tmp_path)

    response = client.get(f"{API}/client-review?scope={_STORE_REL}")

    assert "allow_permitted" not in response.text
    assert "tool_approval" not in response.text


# --- Task D3: acknowledgement writes no decision -------------------------------------


def test_posting_an_acknowledgement_writes_no_decision(tmp_path: Path):
    workspace = fixtures.git_workspace(tmp_path)
    store = fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    client = fixtures.studio_client(tmp_path)
    before = store.read_text(encoding="utf-8")

    response = client.post(
        f"{API}/client-review/acknowledge",
        json={"scope": _STORE_REL, "acknowledged_by": "Client"},
    )

    assert response.status_code == 201, response.text
    assert store.read_text(encoding="utf-8") == before


def test_an_acknowledgement_without_a_named_person_is_refused(tmp_path: Path):
    client = fixtures.studio_client(tmp_path)

    response = client.post(
        f"{API}/client-review/acknowledge", json={"scope": _STORE_REL}
    )

    assert response.status_code == 422, response.text


# --- the extracted predicates, tested directly ---------------------------------------
#
# A route-level test cannot distinguish "correctly excluded" from "never reached": I
# disabled the committed-ids check and all 14 route tests still passed. These cover the
# predicates themselves.


def test_an_already_committed_entry_is_not_also_pending():
    """The guard the route tests could not see. Without it, a committed decision would
    appear BOTH as a decision and as a pending item."""
    from seshat.studio import operations_routes

    entry = {
        "id": "studio-0001",
        "answer": "approve",
        "approval": {"reviewed_scope": _STORE_REL},
    }

    assert not operations_routes.is_pending_for_scope(
        entry, _STORE_REL, {"studio-0001"}
    )


def test_an_uncommitted_entry_in_scope_is_pending():
    """The paired positive case: without it, the predicate could reject everything."""
    from seshat.studio import operations_routes

    entry = {
        "id": "studio-0002",
        "answer": "approve",
        "approval": {"reviewed_scope": _STORE_REL},
    }

    assert operations_routes.is_pending_for_scope(entry, _STORE_REL, set())


def test_an_entry_from_another_scope_is_not_pending_here():
    from seshat.studio import operations_routes

    entry = {
        "id": "studio-0003",
        "answer": "approve",
        "approval": {"reviewed_scope": ".seshat/kpi-contracts.yaml"},
    }

    assert not operations_routes.is_pending_for_scope(entry, _STORE_REL, set())


def test_a_non_mapping_entry_is_not_pending():
    """Malformed store content must not crash the review surface."""
    from seshat.studio import operations_routes

    assert not operations_routes.is_pending_for_scope("not a dict", _STORE_REL, set())


@pytest.mark.parametrize(
    "scope,who",
    [
        (None, "Client"),
        (_STORE_REL, None),
        ("", "Client"),
        (_STORE_REL, "   "),
        (_STORE_REL, ""),
    ],
)
def test_an_acknowledgement_missing_either_half_is_refused(scope, who):
    from seshat.studio import operations_routes

    assert not operations_routes.names_a_person_and_scope(scope, who)


def test_an_acknowledgement_with_both_halves_is_accepted():
    """The paired positive case, so the predicate is not simply always False."""
    from seshat.studio import operations_routes

    assert operations_routes.names_a_person_and_scope(_STORE_REL, "Client")
