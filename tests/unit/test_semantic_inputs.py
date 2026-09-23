"""Committed semantic-input discovery fails closed (never a silent worktree walk)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat import semantic_inputs
from seshat.cli import main
from seshat.semantic_inputs import (
    MODE_FILESYSTEM,
    MODE_GIT,
    SemanticInputsUnavailable,
    discover_semantic_inputs,
)
from tests.fixtures.portfolio_watch.builders import commit_all, init_git_repo

pytestmark = pytest.mark.unit


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _refuse_git(monkeypatch) -> None:
    """Simulate git refusing the checkout (e.g. dubious ownership, exit 128)."""

    def refused(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 128, "", "fatal: dubious ownership")

    monkeypatch.setattr(semantic_inputs, "run_subprocess", refused)


def test_nested_project_lists_only_its_committed_inputs(tmp_path: Path) -> None:
    """A project nested in a larger repo is read from the index, scoped to it."""
    init_git_repo(tmp_path)
    project = tmp_path / "proj"
    _write(project / "mappings/t/metrics/tracked.yaml", "name: tracked\n")
    _write(tmp_path / "other/mappings/t/metrics/outside.yaml", "name: outside\n")
    commit_all(tmp_path)
    _write(project / "mappings/t/metrics/untracked.yaml", "name: untracked\n")

    inputs, mode = discover_semantic_inputs(project, include_untracked=False)

    assert mode == MODE_GIT
    assert [p.relative_to(project).as_posix() for p in inputs] == [
        "mappings/t/metrics/tracked.yaml"
    ]


def test_git_failure_inside_a_repository_raises(tmp_path: Path, monkeypatch) -> None:
    init_git_repo(tmp_path)
    _write(tmp_path / "mappings/t/metrics/x.yaml", "name: x\n")
    _refuse_git(monkeypatch)

    with pytest.raises(SemanticInputsUnavailable):
        discover_semantic_inputs(tmp_path, include_untracked=False)


def test_no_git_repository_is_reported_as_filesystem_mode(tmp_path: Path) -> None:
    if semantic_inputs.inside_git_repository(tmp_path):
        pytest.skip("the temp directory sits inside a git repository")
    _write(tmp_path / "mappings/t/metrics/x.yaml", "name: x\n")

    inputs, mode = discover_semantic_inputs(tmp_path, include_untracked=False)

    assert mode == MODE_FILESYSTEM
    assert len(inputs) == 1


def test_semantic_check_refuses_when_git_fails(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    init_git_repo(tmp_path)
    _write(tmp_path / "mappings/t/metrics/x.yaml", "name: x\n")
    _refuse_git(monkeypatch)

    code = main(["semantic-check", "--repo", str(tmp_path)])

    assert code == 1
    assert "[blocked]" in capsys.readouterr().err


def _verifiable_scope(root: Path) -> None:
    from tests.fixtures.portfolio_watch.builders import write_readiness_status
    from tests.unit.test_portfolio_watch_semantic_run import (
        _semantic_approval,
        _write_bound_contract,
    )

    write_readiness_status(
        root,
        "scope_alpha",
        current_stage="semantic_model_ready",
        approvals=_semantic_approval(),
    )
    _write_bound_contract(root)


def test_contract_binding_is_blocked_when_git_fails(
    tmp_path: Path, monkeypatch
) -> None:
    """A git refusal is never read as a clean worktree (it used to become
    dirty=False plus a working-tree walk, which reported `verified`)."""
    from seshat import portfolio_watch as pw

    _verifiable_scope(tmp_path)
    init_git_repo(tmp_path)
    assert pw.contract_binding_state(tmp_path, "scope_alpha") == "verified"

    _refuse_git(monkeypatch)
    assert pw.contract_binding_state(tmp_path, "scope_alpha") == "blocked"


def test_contract_binding_is_blocked_without_committed_state(tmp_path: Path) -> None:
    from seshat import portfolio_watch as pw

    if semantic_inputs.inside_git_repository(tmp_path):
        pytest.skip("the temp directory sits inside a git repository")
    _verifiable_scope(tmp_path)

    assert pw.contract_binding_state(tmp_path, "scope_alpha") == "blocked"
