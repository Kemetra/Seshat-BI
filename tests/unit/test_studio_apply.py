"""Phase D -- apply and client review (spec 140, US4/US5, Tasks 4.1-4.4).

The claims under test:

- an apply is refused while its decision is only `pending commit` (US4 acceptance 5);
- an apply cannot exceed the reviewed proposal scope (FR-140-014);
- static success is never presented as live correctness (FR-140-016/017);
- client review exposes only its selected scope (FR-140-018).
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
_STORE_REL = ".seshat/semantic-decisions.yaml"


def _prepare(client) -> dict:
    response = client.post(
        f"{API}/proposals",
        json={
            "intent": "Report net sales net of returns",
            "target_artifact": _STORE_REL,
            "table_id": "ready_sales",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _record(client, proposal: dict, **overrides):
    payload = {
        "signer": _SIGNER,
        "declared_authority": "owner",
        "answer": proposal["allowed_answers"][0],
        "proposal_hash": proposal["proposal_hash"],
        "workspace_revision": proposal["workspace_revision"],
    }
    payload.update(overrides)
    return client.post(f"{API}/decisions/record", json=payload)


# --- Task 4.1: apply refuses an uncommitted decision --------------------------------


def test_apply_refuses_when_the_decision_is_only_pending_commit(tmp_path: Path):
    """A working-tree decision is not authority, so it cannot authorize an apply."""
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    proposal = _prepare(client)
    assert _record(client, proposal).status_code == 201

    response = client.post(f"{API}/proposals/{proposal['proposal_id']}/apply")

    assert response.status_code == 422, response.text
    assert "commit" in response.text.lower()


def test_apply_proceeds_once_the_decision_is_committed(tmp_path: Path):
    """The paired positive case.

    Without it, "apply refuses" would also pass if apply refused unconditionally --
    which would make the refusal test prove nothing about the commit boundary.
    """
    workspace = fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    proposal = _prepare(client)
    assert _record(client, proposal).status_code == 201
    workspace.commit_all("decision: recorded")

    response = client.post(f"{API}/proposals/{proposal['proposal_id']}/apply")

    assert response.status_code == 200, response.text
    assert response.json()["proposal_hash"] == proposal["proposal_hash"]


def test_apply_refuses_when_no_decision_exists_at_all(tmp_path: Path):
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    proposal = _prepare(client)

    response = client.post(f"{API}/proposals/{proposal['proposal_id']}/apply")

    assert response.status_code == 422, response.text


def test_apply_reports_an_unknown_proposal_as_404(tmp_path: Path):
    client = fixtures.studio_client(tmp_path)

    response = client.post(f"{API}/proposals/deadbeefcafe/apply")

    assert response.status_code == 404, response.text


# --- Task 4.2: apply is bound to the reviewed scope ---------------------------------


def test_apply_refuses_a_path_outside_the_reviewed_scope(tmp_path: Path):
    """FR-140-014: the caller must not be able to widen what gets touched."""
    workspace = fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    proposal = _prepare(client)
    _record(client, proposal)
    workspace.commit_all("decision: recorded")

    response = client.post(
        f"{API}/proposals/{proposal['proposal_id']}/apply",
        json={"extra_paths": ["src/seshat/cli.py"]},
    )

    assert response.status_code == 422, response.text
    assert "scope" in response.text.lower()


def test_the_applied_paths_are_exactly_the_reviewed_target(tmp_path: Path):
    workspace = fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    proposal = _prepare(client)
    _record(client, proposal)
    workspace.commit_all("decision: recorded")

    receipt = client.post(f"{API}/proposals/{proposal['proposal_id']}/apply").json()

    assert receipt["applied_paths"] == [proposal["target_artifact"]]


# --- Task 4.3: static success is not live correctness -------------------------------


def test_a_missing_dsn_yields_pending_live_rather_than_a_pass(tmp_path: Path):
    workspace = fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    proposal = _prepare(client)
    _record(client, proposal)
    workspace.commit_all("decision: recorded")

    verification = client.post(
        f"{API}/proposals/{proposal['proposal_id']}/apply"
    ).json()["verification"]

    assert "PENDING LIVE PROFILE" in verification["live"]
    assert "pass" not in verification["live"].lower()


def test_static_verification_is_labelled_necessary_not_sufficient(tmp_path: Path):
    """FR-140-016: a static pass must not read as semantic or live correctness."""
    workspace = fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    proposal = _prepare(client)
    _record(client, proposal)
    workspace.commit_all("decision: recorded")

    verification = client.post(
        f"{API}/proposals/{proposal['proposal_id']}/apply"
    ).json()["verification"]

    assert "necessary" in verification["static"].lower()


def test_the_receipt_is_not_a_readiness_claim(tmp_path: Path):
    """An ApplyReceipt is evidence, never authority on its own."""
    workspace = fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    proposal = _prepare(client)
    _record(client, proposal)
    workspace.commit_all("decision: recorded")

    receipt = client.post(f"{API}/proposals/{proposal['proposal_id']}/apply").json()

    assert "readiness" not in receipt
    assert "stage_advanced" not in receipt


# --- Task 4.4: client review scope ---------------------------------------------------


def test_review_requires_a_session(tmp_path: Path):
    client = fixtures.unauthenticated_client(tmp_path)

    response = client.get(f"{API}/review?scope={_STORE_REL}")

    assert response.status_code == 401, response.text


def test_review_exposes_only_the_selected_scope(tmp_path: Path):
    """FR-140-018: least privilege, filtered server-side."""
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)

    first = _prepare(client)
    _record(client, first)
    other = client.post(
        f"{API}/proposals",
        json={
            "intent": "Something else",
            "target_artifact": ".seshat/kpi-contracts.yaml",
        },
    ).json()
    _record(client, other)

    body = client.get(f"{API}/review?scope={_STORE_REL}").json()

    scopes = {item["scope"] for item in body["decisions"]}
    assert scopes == {_STORE_REL}


def test_review_hides_technical_tool_approval_controls(tmp_path: Path):
    """FR-140-018: a client-review context must not expose tool approval."""
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)

    response = client.get(f"{API}/review?scope={_STORE_REL}")

    assert response.status_code == 200, response.text
    assert "tool_approval" not in response.text
    assert "allow_permitted" not in response.text


def test_review_always_offers_decline_and_clarification(tmp_path: Path):
    """US5 acceptance 3: those two options are never absent."""
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)

    body = client.get(f"{API}/review?scope={_STORE_REL}").json()

    assert "decline" in body["available_responses"]
    assert "request_clarification" in body["available_responses"]


def test_review_requires_an_explicit_scope(tmp_path: Path):
    """No scope means no least-privilege boundary, so it is refused rather than
    defaulted to everything."""
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)

    response = client.get(f"{API}/review")

    assert response.status_code == 422, response.text
