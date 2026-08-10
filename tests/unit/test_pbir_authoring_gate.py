"""Committed-evidence gate for bounded PBIR mutation commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.pbir_authoring_gate import check_pbir_authoring_gate
from tests.unit._gitfix import commit_all, make_git_repo

pytestmark = pytest.mark.unit


def _readiness_text(*, semantic: str, approval: bool) -> str:
    approvals = (
        'approvals:\n  - stage: "dashboard_ready"\n'
        '    owner: "A Person (owner)"\n'
        '    at: "2026-08-10"\n'
        '    note: "Approved report design"\n'
        if approval
        else "approvals: []\n"
    )
    return (
        "stages:\n"
        "  semantic_model_ready:\n"
        f'    status: "{semantic}"\n'
        "  dashboard_ready:\n"
        '    status: "not_started"\n'
        f"{approvals}"
    )


def _write_readiness(
    repo: Path,
    table: str,
    *,
    semantic: str = "pass",
    approval: bool = True,
) -> Path:
    path = repo / "mappings" / table / "readiness-status.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _readiness_text(semantic=semantic, approval=approval), encoding="utf-8"
    )
    return path


def test_gate_requires_committed_semantic_pass_and_dashboard_approval(
    tmp_path: Path,
) -> None:
    repo = make_git_repo(tmp_path)
    _write_readiness(repo, "orders", approval=False)
    commit_all(repo, "record semantic readiness")

    result = check_pbir_authoring_gate(repo, "orders")

    assert result.allowed is False
    assert any("dashboard_ready approval" in item for item in result.blockers)


def test_dirty_approval_record_is_not_authority(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    path = _write_readiness(repo, "orders", approval=False)
    commit_all(repo, "record semantic readiness")
    path.write_text(_readiness_text(semantic="pass", approval=True), encoding="utf-8")

    result = check_pbir_authoring_gate(repo, "orders")

    assert result.allowed is False
    assert any("committed and clean" in item for item in result.blockers)


def test_gate_allows_complete_committed_exact_table_record(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    _write_readiness(repo, "orders")
    commit_all(repo, "approve report design")

    result = check_pbir_authoring_gate(repo, "orders")

    assert result.allowed is True
    assert result.blockers == ()


def test_other_table_cannot_supply_gate_evidence(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    _write_readiness(repo, "orders")
    _write_readiness(repo, "returns", semantic="not_started", approval=False)
    commit_all(repo, "record table readiness")

    result = check_pbir_authoring_gate(repo, "returns")

    assert result.allowed is False
    assert any("semantic_model_ready" in item for item in result.blockers)
    assert any("dashboard_ready approval" in item for item in result.blockers)


def test_invalid_table_path_is_refused(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)

    result = check_pbir_authoring_gate(repo, "../orders")

    assert result.allowed is False
    assert any("exact table name" in item for item in result.blockers)


def test_malformed_committed_yaml_is_refused(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    path = repo / "mappings" / "orders" / "readiness-status.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("stages: [broken", encoding="utf-8")
    commit_all(repo, "record malformed readiness")

    result = check_pbir_authoring_gate(repo, "orders")

    assert result.allowed is False
    assert any("valid YAML" in item for item in result.blockers)
