"""``seshat.reset.execute_reset`` -- removals, surgical edits, git staging (#433).

Executor contract: the whole plan is validated BEFORE anything is removed;
the derived paths are gone afterwards AND staged as deletions (the #430
workaround made native); the bronze landing survives; shared dbt files retain
other tables' rows byte-for-byte; a mid-removal OS error reports exactly which
paths were already removed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import seshat.reset as reset_mod
from seshat.reset import (
    ResetError,
    ResetExecutionError,
    execute_reset,
    plan_reset,
    verify_reset,
)
from tests.unit._gitfix import commit_all, make_git_repo
from tests.unit._reset_fixtures import (
    add_dagster_run,
    build_workspace,
    selectors_text,
)

pytestmark = pytest.mark.unit


def _onboarded_repo(tmp_path: Path, tables: tuple[str, ...]) -> Path:
    repo = make_git_repo(tmp_path)
    build_workspace(repo, tables)
    add_dagster_run(repo, "20260101T000000Z-aaaaaaaa", (tables[0],))
    commit_all(repo, "feat: onboard fixture tables")
    return repo


def _porcelain(repo: Path) -> list[str]:
    out = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def test_execute_removes_derived_set_and_stages_deletions(
    tmp_path: Path,
) -> None:
    repo = _onboarded_repo(tmp_path, ("orders", "orders_archive"))
    plan = plan_reset(repo, "orders")
    report = execute_reset(repo, plan)

    # Derived paths are gone.
    assert not (repo / "mappings" / "orders").exists()
    assert not (repo / "dbt" / "models" / "staging" / "orders").exists()
    assert not (repo / "dbt" / "models" / "marts" / "orders").exists()
    assert not (repo / "dbt" / "models" / "audit" / "orders").exists()
    assert not (
        repo / "warehouse" / "migrations" / "0003_create_silver_orders.sql"
    ).exists()
    assert not (
        repo / ".seshat" / "dagster" / "runs" / "20260101T000000Z-aaaaaaaa"
    ).exists()

    # Bronze landing survives; the other table is untouched.
    assert (repo / "data" / "raw" / "orders.csv").is_file()
    assert (repo / "mappings" / "orders_archive").is_dir()
    assert (
        repo / "warehouse" / "migrations" / "0005_create_silver_orders_archive.sql"
    ).is_file()

    # Shared dbt files retain the other table's rows byte-for-byte.
    selectors = (repo / "dbt" / "selectors.yml").read_text(encoding="utf-8")
    assert selectors == selectors_text("orders_archive")
    sources = (repo / "dbt" / "models" / "sources" / "_sources.yml").read_text(
        encoding="utf-8"
    )
    assert "- name: fct_orders_archive" in sources
    assert "- name: fct_orders\n" not in sources

    # Everything removed is STAGED as a deletion; nothing is left unstaged.
    status = _porcelain(repo)
    staged_deletes = {line[3:] for line in status if line.startswith("D ")}
    assert "mappings/orders/source-map.yaml" in staged_deletes
    assert "dbt/models/marts/orders/fct_orders.sql" in staged_deletes
    assert not [line for line in status if line.startswith(" D")], status
    assert report.removed
    assert report.staging_note is None

    # The executor's own verification finds no residual state.
    assert verify_reset(repo, "orders", plan) == ()


def test_dry_state_before_execute_is_untouched_by_planning(
    tmp_path: Path,
) -> None:
    repo = _onboarded_repo(tmp_path, ("orders",))
    plan_reset(repo, "orders")
    assert _porcelain(repo) == []
    assert (repo / "mappings" / "orders").is_dir()


def test_plan_is_validated_before_any_removal(tmp_path: Path) -> None:
    repo = _onboarded_repo(tmp_path, ("orders",))
    plan = plan_reset(repo, "orders")
    # Invalidate the plan AFTER planning: a planned path vanished.
    (repo / "warehouse" / "migrations" / "0003_create_silver_orders.sql").unlink()
    with pytest.raises(ResetError) as excinfo:
        execute_reset(repo, plan)
    assert excinfo.value.reason == "plan_stale"
    # Fail-closed means NOTHING was removed.
    assert (repo / "mappings" / "orders").is_dir()
    assert (repo / "dbt" / "models" / "marts" / "orders").is_dir()


def test_shared_file_changed_since_planning_is_refused(tmp_path: Path) -> None:
    repo = _onboarded_repo(tmp_path, ("orders",))
    plan = plan_reset(repo, "orders")
    (repo / "dbt" / "selectors.yml").write_text(
        selectors_text("orders", "late_arrival"), encoding="utf-8"
    )
    with pytest.raises(ResetError) as excinfo:
        execute_reset(repo, plan)
    assert excinfo.value.reason == "shared_file_changed"
    assert (repo / "mappings" / "orders").is_dir()


def test_mid_removal_error_reports_already_removed_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _onboarded_repo(tmp_path, ("orders",))
    plan = plan_reset(repo, "orders")

    real_rmtree = reset_mod.shutil.rmtree
    calls: list[str] = []

    def failing_rmtree(path, *args: object, **kwargs: object) -> None:
        calls.append(str(path))
        if len(calls) == 2:
            raise OSError("simulated removal failure")
        real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(reset_mod.shutil, "rmtree", failing_rmtree)
    with pytest.raises(ResetExecutionError) as excinfo:
        execute_reset(repo, plan)
    assert len(excinfo.value.removed) == 1
    assert "simulated removal failure" in str(excinfo.value)


def test_non_git_workspace_removes_but_notes_no_staging(tmp_path: Path) -> None:
    root = tmp_path / "plain"
    root.mkdir()
    build_workspace(root, ("orders",))
    plan = plan_reset(root, "orders")
    report = execute_reset(root, plan)
    assert not (root / "mappings" / "orders").exists()
    assert report.staging_note is not None
    assert "not a git repository" in report.staging_note


def test_verify_reports_residual_state(tmp_path: Path) -> None:
    repo = _onboarded_repo(tmp_path, ("orders",))
    plan = plan_reset(repo, "orders")
    execute_reset(repo, plan)
    # Plant residue back: a leftover exact-token migration.
    (repo / "warehouse" / "migrations" / "0009_create_silver_orders.sql").write_text(
        "SELECT 1;\n", encoding="utf-8"
    )
    findings = verify_reset(repo, "orders", plan)
    assert findings
    assert any("0009_create_silver_orders.sql" in f for f in findings)
