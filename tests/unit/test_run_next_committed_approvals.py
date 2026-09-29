"""run-next honours only COMMITTED approvals (audit finding F045).

An approval is a named human's ruling, and it is only an audit record once it is
committed. ``seshat next`` must not advance a stage on an approval that exists
only in the worktree copy of ``readiness-status.yaml``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.agent_next import build_agent_next_document
from seshat.run_next import build_run_next_response
from tests.unit._gitfix import commit_all, make_git_repo

pytestmark = pytest.mark.unit

_STATUS = """\
table: "silver.orders"
current_stage: "mapping_ready"
stages:
  source_ready: {status: "pass", evidence: ["mappings/orders/source-profile.md"]}
  mapping_ready: {status: "pass", evidence: ["mappings/orders/source-map.yaml"]}
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals: []
next_action: "await the mapping approval"
"""

_APPROVAL = (
    "approvals:\n"
    '  - {stage: mapping_ready, owner: "Jane Doe (analyst)", at: "2026-09-23"}\n'
)


def _status_path(repo: Path) -> Path:
    return repo / "mappings" / "orders" / "readiness-status.yaml"


def _committed_repo(tmp_path: Path, body: str) -> Path:
    repo = make_git_repo(tmp_path)
    path = _status_path(repo)
    path.parent.mkdir(parents=True)
    path.write_text(body, encoding="utf-8")
    commit_all(repo, "feat: readiness fixture")
    return repo


def _add_worktree_approval(repo: Path) -> None:
    path = _status_path(repo)
    text = path.read_text(encoding="utf-8").replace("approvals: []\n", _APPROVAL)
    path.write_text(text, encoding="utf-8")


def test_uncommitted_approval_does_not_advance_the_stage(tmp_path: Path) -> None:
    repo = _committed_repo(tmp_path, _STATUS)
    _add_worktree_approval(repo)

    response = build_run_next_response(repo, "orders")

    assert response["outcome"] == "approval_required"
    assert response["stage"] == "mapping_ready"
    kinds = {caveat["kind"] for caveat in response["caveats"]}
    assert "uncommitted_approval" in kinds


def test_uncommitted_approval_does_not_advance_the_agent_document(
    tmp_path: Path,
) -> None:
    repo = _committed_repo(tmp_path, _STATUS)
    _add_worktree_approval(repo)

    document = build_agent_next_document(repo, "orders")

    assert document["outcome"] == "approval_required"
    assert "silver migration" not in document["next_allowed_action"].lower()


def test_committed_approval_still_advances(tmp_path: Path) -> None:
    repo = _committed_repo(tmp_path, _STATUS.replace("approvals: []\n", _APPROVAL))

    response = build_run_next_response(repo, "orders")

    assert response["outcome"] == "next_action"
    assert response["stage"] == "silver_ready"
    kinds = {caveat["kind"] for caveat in response["caveats"]}
    assert "uncommitted_approval" not in kinds


def test_committed_approval_survives_an_unrelated_worktree_edit(
    tmp_path: Path,
) -> None:
    repo = _committed_repo(tmp_path, _STATUS.replace("approvals: []\n", _APPROVAL))
    path = _status_path(repo)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "await the mapping approval", "begin silver"
        ),
        encoding="utf-8",
    )

    response = build_run_next_response(repo, "orders")

    assert response["stage"] == "silver_ready"


def test_committed_approval_counts_when_repo_is_a_subdirectory(
    tmp_path: Path,
) -> None:
    """``--repo`` below the git toplevel still resolves the HEAD copy."""
    top = make_git_repo(tmp_path)
    workspace = top / "analytics"
    path = workspace / "mappings" / "orders" / "readiness-status.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(_STATUS.replace("approvals: []\n", _APPROVAL), encoding="utf-8")
    commit_all(top, "feat: nested workspace")

    response = build_run_next_response(workspace, "orders")

    assert response["stage"] == "silver_ready"


def test_approval_outside_a_git_repository_is_not_trusted(tmp_path: Path) -> None:
    path = tmp_path / "mappings" / "orders" / "readiness-status.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(_STATUS.replace("approvals: []\n", _APPROVAL), encoding="utf-8")

    response = build_run_next_response(tmp_path, "orders")

    assert response["outcome"] == "approval_required"
    kinds = {caveat["kind"] for caveat in response["caveats"]}
    assert "uncommitted_approval" in kinds
