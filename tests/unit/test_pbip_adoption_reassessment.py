"""Fingerprint-baseline reassessment behavior for PBIP adoption."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from seshat.pbip_adoption import MANIFEST_PATH, assess_pbip, scaffold_pbip

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "pbip_adoption" / "supported"


def _commit(project: Path, message: str) -> None:
    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-m",
            message,
        ],
        cwd=project,
        check=True,
        capture_output=True,
    )


def _project_with_baseline(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    shutil.copytree(FIXTURE, project)
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    _commit(project, "fixture")
    assessment = assess_pbip(project)
    assert (
        scaffold_pbip(project, assessment["assessment_digest"])["outcome"] == "written"
    )
    _commit(project, "adoption baseline")
    assert (project / Path(MANIFEST_PATH)).is_file()
    return project


def test_reassessment_marks_unchanged_inputs_deterministically(tmp_path: Path) -> None:
    project = _project_with_baseline(tmp_path)
    first = assess_pbip(project)
    second = assess_pbip(project)
    assert first == second
    assert first["changes"]
    assert {change["kind"] for change in first["changes"]} == {"unchanged"}


def test_reassessment_surfaces_added_changed_and_removed_inputs(tmp_path: Path) -> None:
    project = _project_with_baseline(tmp_path)
    added = project / "Adoption.Report" / "definition" / "pages" / "new.json"
    added.write_text("{}\n", encoding="utf-8")
    change_rows = assess_pbip(project)["changes"]
    assert any(
        change["kind"] == "added" and change["artifact"].endswith("new.json")
        for change in change_rows
    )

    model = project / "Adoption.SemanticModel" / "definition" / "model.tmdl"
    model.write_text(
        model.read_text(encoding="utf-8") + "\n// changed\n", encoding="utf-8"
    )
    assert any(
        change["kind"] == "changed" and change["artifact"].endswith("model.tmdl")
        for change in assess_pbip(project)["changes"]
    )

    model.unlink()
    assert any(
        change["kind"] == "removed" and change["artifact"].endswith("model.tmdl")
        for change in assess_pbip(project)["changes"]
    )
