"""Phase C -- the decision recording route (spec 140, US3, Tasks 3.3-3.6).

This is the security core of spec 140. The claims under test:

- the agent cannot supply, choose, or infer a named-human answer (FR-140-009);
- a stale proposal or revision fails closed BEFORE any write (FR-140-012);
- a recorded decision reports `pending commit`, never approved (FR-140-021);
- readiness does not move until a human commits (FR-140-015).

Every negative assertion is paired with the positive case that proves it is not
vacuous.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unit import _workbench_fixtures as fixtures  # noqa: E402

pytestmark = pytest.mark.unit

API = "/api/v1"
_SIGNER = "Ahmed Shaaban (owner)"


def _prepare(client) -> dict:
    """Ask the server to prepare a proposal, returning its JSON body."""
    response = client.post(
        f"{API}/proposals",
        json={
            "intent": "Report net sales net of returns",
            "target_artifact": ".seshat/semantic-decisions.yaml",
            "table_id": "ready_sales",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _decision_payload(proposal: dict, **overrides) -> dict:
    payload = {
        "signer": _SIGNER,
        "declared_authority": "owner",
        "answer": proposal["allowed_answers"][0],
        "proposal_hash": proposal["proposal_hash"],
        "workspace_revision": proposal["workspace_revision"],
    }
    payload.update(overrides)
    return payload


# --- Proposal route -------------------------------------------------------------------


def test_preparing_a_proposal_requires_a_session(tmp_path: Path):
    client = fixtures.unauthenticated_client(tmp_path)

    response = client.post(
        f"{API}/proposals", json={"intent": "x", "target_artifact": "y"}
    )

    assert response.status_code == 401, response.text


def test_a_prepared_proposal_carries_its_hash_revision_and_closed_answers(
    tmp_path: Path,
):
    client = fixtures.studio_client(tmp_path)

    proposal = _prepare(client)

    assert proposal["proposal_hash"]
    assert proposal["workspace_revision"]
    assert proposal["allowed_answers"], "a decision needs a closed answer set"
    assert proposal["question"]


def test_a_proposal_can_be_re_read_and_reports_staleness(tmp_path: Path):
    client = fixtures.studio_client(tmp_path)
    proposal = _prepare(client)

    response = client.get(f"{API}/proposals/{proposal['proposal_id']}")

    assert response.status_code == 200, response.text
    assert response.json()["stale"] is False


def test_an_unknown_proposal_is_404(tmp_path: Path):
    client = fixtures.studio_client(tmp_path)

    response = client.get(f"{API}/proposals/deadbeefcafe")

    assert response.status_code == 404, response.text


# --- Task 3.3: no server-supplied signer, authority, or answer -----------------------


@pytest.mark.parametrize("omitted", ["signer", "declared_authority", "answer"])
def test_a_missing_human_supplied_field_is_refused(tmp_path: Path, omitted: str):
    """FR-140-009: absent means refuse, never infer. No default exists for these."""
    client = fixtures.studio_client(tmp_path)
    proposal = _prepare(client)
    payload = _decision_payload(proposal)
    del payload[omitted]

    response = client.post(f"{API}/decisions/record", json=payload)

    assert response.status_code == 422, response.text
    assert omitted in response.text


def test_an_answer_outside_the_allowed_set_is_refused(tmp_path: Path):
    """The closed answer set is what stops a judgement being smuggled in by phrasing."""
    client = fixtures.studio_client(tmp_path)
    proposal = _prepare(client)

    response = client.post(
        f"{API}/decisions/record",
        json=_decision_payload(proposal, answer="whatever the agent thinks"),
    )

    assert response.status_code == 422, response.text


def test_a_malformed_signer_is_refused(tmp_path: Path):
    """`owner (owner)` fails the shipped owner_shape_ok: the name is a role token."""
    client = fixtures.studio_client(tmp_path)
    proposal = _prepare(client)

    response = client.post(
        f"{API}/decisions/record",
        json=_decision_payload(proposal, signer="owner (owner)"),
    )

    assert response.status_code == 422, response.text


def test_a_declared_authority_that_contradicts_the_signer_is_refused(tmp_path: Path):
    client = fixtures.studio_client(tmp_path)
    proposal = _prepare(client)

    response = client.post(
        f"{API}/decisions/record",
        json=_decision_payload(proposal, declared_authority="analyst"),
    )

    assert response.status_code == 422, response.text


# --- Task 3.4: the receipt cannot claim approval ------------------------------------


def test_a_successful_record_reports_pending_commit(tmp_path: Path):
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    proposal = _prepare(client)

    response = client.post(f"{API}/decisions/record", json=_decision_payload(proposal))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["state"] == "pending_commit"
    assert "approved" not in body["state"]
    assert body["gate_authority"], "the receipt must say why it is not authority"


# --- Task 3.6: stale proposal or revision fails closed before any write --------------


def test_a_stale_proposal_hash_is_refused_and_nothing_is_written(tmp_path: Path):
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    store = fixtures.store_file(tmp_path)
    proposal = _prepare(client)
    original = store.read_text(encoding="utf-8")

    response = client.post(
        f"{API}/decisions/record",
        json=_decision_payload(proposal, proposal_hash="0" * 64),
    )

    assert response.status_code == 409, response.text
    assert store.read_text(encoding="utf-8") == original


def test_a_stale_workspace_revision_is_refused(tmp_path: Path):
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    store = fixtures.store_file(tmp_path)
    proposal = _prepare(client)
    original = store.read_text(encoding="utf-8")

    response = client.post(
        f"{API}/decisions/record",
        json=_decision_payload(proposal, workspace_revision="z" * 16),
    )

    assert response.status_code == 409, response.text
    assert store.read_text(encoding="utf-8") == original


# --- Task 3.5: readiness moves only on commit ---------------------------------------


def test_an_uncommitted_decision_moves_no_readiness_stage(tmp_path: Path):
    """A working-tree write is not authority (FR-140-015)."""
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    proposal = _prepare(client)
    before = client.get(f"{API}/workspace").json()["tables"]

    recorded = client.post(f"{API}/decisions/record", json=_decision_payload(proposal))
    assert recorded.status_code == 201, recorded.text

    after = client.get(f"{API}/workspace").json()["tables"]
    assert after == before, "an uncommitted decision must move no stage"


def test_the_decision_is_written_to_the_working_tree_even_though_nothing_moved(
    tmp_path: Path,
):
    """The paired positive case for the test above.

    Without this, "nothing moved" would also pass if the write silently did nothing --
    which would make the boundary test vacuous rather than meaningful.
    """
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    store = fixtures.store_file(tmp_path)
    proposal = _prepare(client)
    before = store.read_text(encoding="utf-8")

    client.post(f"{API}/decisions/record", json=_decision_payload(proposal))

    # The file MUST have changed -- that is the half this test adds.
    assert store.read_text(encoding="utf-8") != before

    from seshat import decision_store

    loaded = decision_store.load_store_file(tmp_path, ".seshat/semantic-decisions.yaml")
    assert loaded.ok, loaded.problems
    assert len(loaded.decisions) == 1
    assert loaded.decisions[0]["approval"]["approved_by"] == _SIGNER


def test_the_recorded_decision_is_absent_from_committed_state_until_committed(
    tmp_path: Path,
):
    """The boundary, read the way the gate reads it: at HEAD."""
    from seshat import decision_write

    workspace = fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: empty store")
    proposal = _prepare(client)

    client.post(f"{API}/decisions/record", json=_decision_payload(proposal))
    uncommitted = decision_write.decisions_at_head(
        workspace, ".seshat/semantic-decisions.yaml"
    )

    workspace.commit_all("decision: net of returns")
    committed = decision_write.decisions_at_head(
        workspace, ".seshat/semantic-decisions.yaml"
    )

    assert uncommitted == [], "an uncommitted decision must not appear at HEAD"
    assert len(committed) == 1, "a committed decision must appear at HEAD"


# --- FR-140-013: technical approval and business decision stay distinct --------------


def test_the_decision_route_does_not_accept_a_technical_approval_shape(tmp_path: Path):
    """FR-140-013: distinct models. A tool-approval payload must not record a business
    decision by accident."""
    client = fixtures.studio_client(tmp_path)

    response = client.post(
        f"{API}/decisions/record",
        json={"approval_id": "a-1", "allow": True},
    )

    assert response.status_code == 422, response.text
