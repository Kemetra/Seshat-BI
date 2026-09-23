"""Studio-written decisions must pass the gate that reads them.

Claims under test (audit batch 9):

- a decision recorded through Studio passes DS1-DS5, so committing it as instructed
  does not turn `seshat check` red;
- ids are derived from the store, not a per-process counter, so a restart cannot
  reuse one -- and a reused id cannot hide a new pending item as "already committed";
- a decline is recorded as `rejected`, and apply refuses it;
- apply returns no fabricated `applied_paths` or static pass;
- a fresh workspace with no store file never produces a 500.

Every rule is run through the SHIPPED rule functions over a real git workspace,
never a hand-written expectation of what they accept.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")  # CI's unit job installs no app extras

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unit import _workbench_fixtures as fixtures  # noqa: E402

from seshat.core import RuleContext, Severity  # noqa: E402
from seshat.rules import decision_store as ds_rules  # noqa: E402

pytestmark = pytest.mark.unit

API = "/api/v1"
_SIGNER = "Ahmed Shaaban (owner)"
_STORE_REL = fixtures.SEMANTIC_DECISIONS
_TARGET = "mappings/Ready_Sales/source-map.yaml"


def _prepare(client, *, target: str = _TARGET, intent: str = "net of returns"):
    response = client.post(
        f"{API}/proposals", json={"intent": intent, "target_artifact": target}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _record(client, proposal: dict, *, answer: str = "approve"):
    return client.post(
        f"{API}/decisions/record",
        json={
            "signer": _SIGNER,
            "declared_authority": "owner",
            "answer": answer,
            "proposal_hash": proposal["proposal_hash"],
            "workspace_revision": proposal["workspace_revision"],
        },
    )


def _ds_errors(root: Path) -> list[str]:
    ctx = RuleContext(repo_root=root, tracked_files=(_STORE_REL,))
    checks = (
        ds_rules.check_ds1,
        ds_rules.check_ds2,
        ds_rules.check_ds3,
        ds_rules.check_ds4,
        ds_rules.check_ds5,
    )
    return [
        f"{finding.rule_id}: {finding.message}"
        for check in checks
        for finding in check(ctx)
        if finding.severity is Severity.ERROR
    ]


def test_a_recorded_decision_passes_every_decision_store_rule(tmp_path: Path):
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)

    recorded = _record(client, _prepare(client))

    assert recorded.status_code == 201, recorded.text
    assert _ds_errors(tmp_path) == []


def test_two_decisions_on_one_artifact_do_not_conflict(tmp_path: Path):
    """Distinct proposals on the same artifact are distinct rulings, not a DS4 clash."""
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)

    assert _record(client, _prepare(client, intent="a")).status_code == 201
    assert _record(client, _prepare(client, intent="b")).status_code == 201
    assert _record(client, _prepare(client, intent="c"), answer="decline").status_code
    assert _ds_errors(tmp_path) == []


def test_a_second_active_ruling_on_one_proposal_is_refused(tmp_path: Path):
    """Two active approvals of ONE proposal would be a DS4 conflict: refuse it."""
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    store = fixtures.store_file(tmp_path)
    proposal = _prepare(client)
    assert _record(client, proposal).status_code == 201
    before = store.read_text(encoding="utf-8")

    again = _record(client, proposal)

    assert again.status_code == 422, again.text
    assert store.read_text(encoding="utf-8") == before
    assert _ds_errors(tmp_path) == []


def test_a_restart_neither_reuses_an_id_nor_hides_the_new_pending_item(
    tmp_path: Path,
):
    workspace = fixtures.git_workspace(tmp_path)
    first = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    one = _record(first, _prepare(first, intent="first"))
    assert one.status_code == 201, one.text
    workspace.commit_all("decision: first")

    second = fixtures.studio_client(tmp_path)  # a fresh create_app: a restart
    two = _record(second, _prepare(second, intent="second"))

    assert two.status_code == 201, two.text
    assert one.json()["decision_id"] != two.json()["decision_id"]
    assert _ds_errors(tmp_path) == []
    review = second.get(f"{API}/client-review", params={"scope": _TARGET}).json()
    assert len(review["pending_items"]) == 1, review


def test_a_decline_is_recorded_as_rejected(tmp_path: Path):
    import yaml

    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    store = fixtures.store_file(tmp_path)

    assert _record(client, _prepare(client), answer="decline").status_code == 201

    entry = yaml.safe_load(store.read_text(encoding="utf-8"))["decisions"][-1]
    assert (entry["answer"], entry["status"]) == ("decline", "rejected")


def test_a_committed_decline_never_authorizes_apply(tmp_path: Path):
    workspace = fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    proposal = _prepare(client)
    assert _record(client, proposal, answer="decline").status_code == 201
    workspace.commit_all("decision: declined")

    response = client.post(f"{API}/proposals/{proposal['proposal_id']}/apply")

    assert response.status_code == 422, response.text


def test_a_hand_written_evidence_stub_never_authorizes_apply(tmp_path: Path):
    """Matching the evidence string alone is not a valid approval."""
    workspace = fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    store = fixtures.store_file(tmp_path)
    proposal = _prepare(client)
    store.write_text(
        "decisions:\n"
        "  - id: assumption_note.stub.1\n"
        "    answer: approve\n"
        "    status: approved\n"
        "    approval:\n"
        f"      evidence: proposal:{proposal['proposal_hash']}\n",
        encoding="utf-8",
    )
    workspace.commit_all("test: stub")

    response = client.post(f"{API}/proposals/{proposal['proposal_id']}/apply")

    assert response.status_code == 422, response.text


def test_the_apply_receipt_claims_no_write_and_no_static_pass(tmp_path: Path):
    workspace = fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    proposal = _prepare(client)
    assert _record(client, proposal).status_code == 201
    workspace.commit_all("decision: approved")

    receipt = client.post(f"{API}/proposals/{proposal['proposal_id']}/apply").json()

    assert receipt["applied_paths"] == []
    assert "not run" in receipt["verification"]["static"]
    assert "passed" not in receipt["verification"]["static"]


def test_history_does_not_label_a_committed_decline_authoritative(tmp_path: Path):
    workspace = fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: baseline")
    assert _record(client, _prepare(client), answer="decline").status_code == 201
    workspace.commit_all("decision: declined")

    runs = client.get(f"{API}/operations/history").json()["runs"]

    durable = [run for run in runs if run["durability"] == "durable"]
    assert [run["decision_state"] for run in durable] == ["rejected"]


def test_recording_into_a_workspace_without_a_store_never_500s(tmp_path: Path):
    fixtures.git_workspace(tmp_path)
    client = fixtures.studio_client(tmp_path)
    store = tmp_path.joinpath(*_STORE_REL.split("/"))
    if store.exists():
        store.unlink()

    recorded = _record(client, _prepare(client))

    assert recorded.status_code in (201, 422), recorded.text
    if recorded.status_code == 201:
        assert _ds_errors(tmp_path) == []
