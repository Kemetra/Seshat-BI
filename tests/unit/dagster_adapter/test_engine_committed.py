"""The build-engine flag is honoured only once it is a committed, clean change."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.dagster_adapter.engine import resolve_build_engine
from tests.unit._gitfix import commit_all, make_git_repo

pytestmark = pytest.mark.unit

TABLE = "demo_table"


def _flag(root: Path, body: str) -> Path:
    table_dir = root / "mappings" / TABLE
    table_dir.mkdir(parents=True, exist_ok=True)
    path = table_dir / "build-engine.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_committed_dbt_flag_engages_dbt(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    _flag(repo, "silver: dbt\ngold: dbt\n")
    commit_all(repo, "engine flag")
    assert resolve_build_engine(repo, TABLE, "silver") == "dbt"
    assert resolve_build_engine(repo, TABLE, "gold") == "dbt"


def test_untracked_dbt_flag_falls_back_to_migrations(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    commit_all(repo, "base")
    _flag(repo, "silver: dbt\ngold: dbt\n")
    assert resolve_build_engine(repo, TABLE, "silver") == "migrations"
    assert resolve_build_engine(repo, TABLE, "gold") == "migrations"


def test_dirty_flag_falls_back_to_migrations(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path)
    path = _flag(repo, "silver: migrations\ngold: migrations\n")
    commit_all(repo, "engine flag")
    path.write_text("silver: dbt\ngold: dbt\n", encoding="utf-8")
    assert resolve_build_engine(repo, TABLE, "silver") == "migrations"


def test_flag_outside_a_repository_falls_back_to_migrations(tmp_path: Path) -> None:
    _flag(tmp_path, "silver: dbt\ngold: dbt\n")
    assert resolve_build_engine(tmp_path, TABLE, "silver") == "migrations"


def test_doctor_names_an_uncommitted_engine_flag(tmp_path: Path) -> None:
    from seshat.dagster_adapter import doctor

    repo = make_git_repo(tmp_path)
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    commit_all(repo, "base")
    _flag(repo, "silver: dbt\ngold: dbt\n")
    findings = doctor._engine_mode_findings(repo, TABLE)
    uncommitted = [f for f in findings if f.id == "DAG-ENG-UNCOMMITTED"]
    assert uncommitted and uncommitted[0].severity == "warning"
    assert TABLE in uncommitted[0].message
