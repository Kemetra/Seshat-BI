"""Exact-acceptance and no-partial-write checks for the adoption baseline."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

import seshat.pbip_adoption as adoption
from seshat.pbip_adoption import MANIFEST_PATH, assess_pbip, scaffold_pbip

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "pbip_adoption" / "supported"


def _copy_clean_git_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    shutil.copytree(FIXTURE, project)
    for command in (
        ["git", "init"],
        ["git", "add", "."],
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
            "fixture",
        ],
    ):
        result = subprocess.run(command, cwd=project, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    return project


def _hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def test_assessment_alone_writes_nothing_and_exact_acceptance_writes_one_manifest(
    tmp_path: Path,
) -> None:
    project = _copy_clean_git_project(tmp_path)
    before = _hashes(project)
    assessment = assess_pbip(project)
    assert _hashes(project) == before

    result = scaffold_pbip(project, assessment["assessment_digest"])
    target = project / Path(MANIFEST_PATH)
    assert result["outcome"] == "written"
    assert result["written"] == [MANIFEST_PATH]
    assert target.is_file()
    assert result["approvals"] == []
    after = _hashes(project)
    assert {path: after[path] for path in before} == before
    assert set(after) - set(before) == {MANIFEST_PATH}


def test_no_git_stale_digest_dirty_input_and_collision_all_refuse(
    tmp_path: Path,
) -> None:
    no_git = tmp_path / "no-git"
    shutil.copytree(FIXTURE, no_git)
    no_git_assessment = assess_pbip(no_git)
    no_git_result = scaffold_pbip(no_git, no_git_assessment["assessment_digest"])
    assert no_git_result["outcome"] == "refused"
    assert no_git_result["written"] == []

    project = _copy_clean_git_project(tmp_path)
    assessment = assess_pbip(project)
    model = project / "Adoption.SemanticModel" / "definition" / "model.tmdl"
    model.write_text(
        model.read_text(encoding="utf-8") + "\n// changed\n", encoding="utf-8"
    )
    stale = scaffold_pbip(project, assessment["assessment_digest"])
    assert stale["outcome"] == "refused"
    assert "stale" in stale["blocking_reasons"][0].lower()

    dirty = assess_pbip(project)
    dirty_result = scaffold_pbip(project, dirty["assessment_digest"])
    assert dirty_result["outcome"] == "refused"
    assert dirty_result["written"] == []

    collision_root = tmp_path / "collision"
    collision_root.mkdir()
    collision = _copy_clean_git_project(collision_root)
    target = collision / Path(MANIFEST_PATH)
    target.parent.mkdir(parents=True)
    target.write_text("existing\n", encoding="utf-8")
    collided = assess_pbip(collision)
    collision_result = scaffold_pbip(collision, collided["assessment_digest"])
    assert collision_result["outcome"] == "refused"
    assert "already exists" in collision_result["blocking_reasons"][0]
    assert target.read_text(encoding="utf-8") == "existing\n"


def test_publication_failure_leaves_no_partial_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    project = _copy_clean_git_project(tmp_path)
    assessment = assess_pbip(project)

    def fail_link(*_args, **_kwargs):
        raise OSError("simulated publication interruption")

    monkeypatch.setattr(adoption.os, "link", fail_link)
    result = scaffold_pbip(project, assessment["assessment_digest"])
    assert result["outcome"] == "refused"
    assert result["written"] == []
    assert not (project / Path(MANIFEST_PATH)).exists()
