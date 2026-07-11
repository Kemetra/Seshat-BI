"""TDD tests for the kit projection-drift linter (feature 072).

Covers:
* YAML + prose projection drift detected + clean (SC-001);
* not-bootstrapped repo → exit-0 report, no drift (SC-003);
* a broken source → a named `source_parse` failing check, NOT a traceback (FR-008);
* reads no constitution file (SC-006, FR-010);
* no numeric score on results; specific detail lines (SC-005, FR-008);
* read-only (FR-004): a lint run mutates no file;
* the dogfood: this repo's committed substrate lints clean (SC-004).

tmp_path repos only (except the dogfood, which reads the real repo, read-only).
"""

from __future__ import annotations

import inspect
import shutil
from dataclasses import fields
from pathlib import Path

import pytest

from seshat import kit_lint

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_REL = ".seshat/kit-source.yaml"


def _bootstrap(tmp_path: Path) -> Path:
    """Copy the real source + minimal governed files, then project via retail init."""
    from seshat import kit_init

    (tmp_path / ".seshat").mkdir()
    shutil.copyfile(REPO_ROOT / SOURCE_REL, tmp_path / SOURCE_REL)
    (tmp_path / "AGENTS.md").write_text("# AGENTS\n\n- rule\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("# CLAUDE\n\nlaw\n", encoding="utf-8")
    kit_init.bootstrap(tmp_path)  # writes compass.yaml + fences
    return tmp_path


def test_clean_bootstrapped_repo_lints_ok(tmp_path) -> None:
    repo = _bootstrap(tmp_path)
    report = kit_lint.lint(repo)
    assert report.ok
    assert report.bootstrapped
    assert all(r.ok for r in report.results)


def test_yaml_projection_drift_detected(tmp_path) -> None:
    repo = _bootstrap(tmp_path)
    compass = repo / ".seshat/compass.yaml"
    compass.write_text(
        compass.read_text(encoding="utf-8") + "\n# tamper\n", encoding="utf-8"
    )
    report = kit_lint.lint(repo)
    assert not report.ok
    yaml_check = next(r for r in report.results if r.name == "yaml_projection")
    assert not yaml_check.ok
    assert yaml_check.details  # names the drift


def test_prose_projection_drift_detected(tmp_path) -> None:
    repo = _bootstrap(tmp_path)
    agents = repo / "AGENTS.md"
    text = agents.read_text(encoding="utf-8").replace(
        "<!-- SESHAT-KIT END -->", "TAMPER\n<!-- SESHAT-KIT END -->"
    )
    agents.write_text(text, encoding="utf-8")
    report = kit_lint.lint(repo)
    assert not report.ok
    prose_check = next(r for r in report.results if r.name == "prose_projection")
    assert not prose_check.ok
    assert any("AGENTS.md" in d for d in prose_check.details)


def test_not_bootstrapped_is_ok_exit_0(tmp_path) -> None:
    # no .seshat/ at all
    report = kit_lint.lint(tmp_path)
    assert report.ok
    assert report.bootstrapped is False


def test_broken_source_is_named_check_not_traceback(tmp_path) -> None:
    repo = _bootstrap(tmp_path)
    (repo / SOURCE_REL).write_text("this: is: not: valid: yaml: [", encoding="utf-8")
    # must not raise -- lint catches and reports
    report = kit_lint.lint(repo)
    assert not report.ok
    assert any(r.name == "source_parse" and not r.ok for r in report.results)


def test_reads_no_constitution_file(tmp_path) -> None:
    # SC-006 / FR-010: a bootstrapped repo with NO constitution still lints clean.
    repo = _bootstrap(tmp_path)
    assert not (repo / ".specify/memory/constitution.md").exists()
    report = kit_lint.lint(repo)
    assert report.ok  # constitution is irrelevant to kit-lint


def test_module_reads_no_constitution_and_no_net() -> None:
    src = inspect.getsource(kit_lint)
    # The docstring may DESCRIBE the cut source-vs-constitution check; what matters is
    # that the module never READS a constitution file (no path reference to it).
    assert "constitution.md" not in src
    assert ".specify/memory" not in src
    for net in ("import socket", "import urllib", "import http", "import requests"):
        assert net not in src


def test_results_carry_no_numeric_score(tmp_path) -> None:
    repo = _bootstrap(tmp_path)
    report = kit_lint.lint(repo)
    for r in report.results:
        names = {f.name for f in fields(r)}
        assert "score" not in names and "confidence" not in names


def test_lint_is_read_only(tmp_path) -> None:
    repo = _bootstrap(tmp_path)
    before = {p: p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    kit_lint.lint(repo)
    after = {p: p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    assert before == after  # no file created, deleted, or modified


def test_dogfood_this_repo_substrate_lints_clean() -> None:
    # SC-004: the committed .seshat/ + fenced regions on this branch are consistent.
    report = kit_lint.lint(REPO_ROOT)
    assert report.ok, [d for r in report.results for d in r.details]
