"""Reference-suite acceptance outcomes for existing PBIP adoption."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from seshat.cli import main
from seshat.pbip_adoption import (
    MANIFEST_PATH,
    assess_pbip,
    render_assessment_text,
    scaffold_pbip,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "pbip_adoption"


def _copy_fixture(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    shutil.copytree(FIXTURES / name, target)
    return target


def _snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def _commit_fixture(project: Path) -> None:
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


def test_sc_001_002_005_006_010_supported_assessment_is_complete_and_consistent(
    tmp_path: Path, capsys
) -> None:
    project = _copy_fixture(tmp_path, "supported")
    first = assess_pbip(project)
    second = assess_pbip(project)

    assert first == second
    assert first["next_step"]
    assert all(fact["artifact"] or fact["reason"] for fact in first["facts"])

    code = main(["adopt-pbip", "assess", "--project", str(project), "--format", "json"])
    assert code in {0, 1}
    assert json.loads(capsys.readouterr().out) == first

    text = render_assessment_text(first)
    for fact in first["facts"]:
        assert fact["subject"] in text
        if fact["artifact"]:
            assert fact["artifact"] in text
    assert first["next_step"]["action"] in text


def test_sc_003_004_and_009_boundaries_preserve_inputs_and_redact_output(
    tmp_path: Path,
) -> None:
    expected_boundaries = {
        "unsafe_literal": "blocked",
        "missing_model": "missing",
        "multi_model": "ambiguous",
        "unsupported_schema": "unsupported",
        "out_of_root": "blocked",
    }
    for name, classification in expected_boundaries.items():
        project = _copy_fixture(tmp_path, name)
        before = _snapshot(project)
        assessment = assess_pbip(project)
        assert _snapshot(project) == before
        assert assessment["next_step"]
        if classification in {"ambiguous", "unsupported"}:
            assert assessment["coverage"][classification] >= 1
        else:
            assert any(
                fact["classification"] == classification for fact in assessment["facts"]
            )

    unsafe = assess_pbip(tmp_path / "unsafe_literal")
    assert "do-not-disclose" not in json.dumps(unsafe)

    boundary = _copy_fixture(tmp_path, "pbix_boundary") / "Legacy.pbix"
    before = boundary.read_bytes()
    assessment = assess_pbip(boundary)
    assert assessment["next_step"]["kind"] == "terminal_stop"
    assert boundary.read_bytes() == before


def test_sc_007_and_sc_008_scaffold_is_exact_and_never_grants_governance(
    tmp_path: Path,
) -> None:
    project = _copy_fixture(tmp_path, "supported")
    _commit_fixture(project)
    before = _snapshot(project)
    assessment = assess_pbip(project)

    assert assessment["scaffold_plan"]["writes"] == [MANIFEST_PATH]
    assert assessment["scaffold_plan"]["approvals"] == []
    assert not (project / MANIFEST_PATH).exists()
    assert not any(fact["classification"] == "approved" for fact in assessment["facts"])
    missing_subjects = {
        fact["subject"]
        for fact in assessment["facts"]
        if fact["classification"] == "missing"
    }
    assert {"source map", "metric contract"} <= missing_subjects

    result = scaffold_pbip(project, assessment["assessment_digest"])
    assert result["outcome"] == "written"
    assert result["written"] == [MANIFEST_PATH]
    after = _snapshot(project)
    assert {path: after[path] for path in before} == before

    collision = scaffold_pbip(project, assessment["assessment_digest"])
    assert collision["outcome"] == "refused"
    assert collision["written"] == []


def _write_typical_scope_project(root: Path) -> None:
    (root / "Portfolio.pbip").write_text(
        '{"version": "1.0", "artifacts": []}\n', encoding="utf-8"
    )
    measures = "\n".join(f"\tmeasure Measure {number} = 1" for number in range(100))
    for number in range(5):
        model = root / f"Model{number}.SemanticModel" / "definition"
        model.mkdir(parents=True)
        (model / "model.tmdl").write_text(
            f"table Table{number}\n{measures}\n", encoding="utf-8"
        )

        report = root / f"Report{number}.Report"
        report.mkdir()
        (report / "definition.pbir").write_text(
            json.dumps(
                {
                    "version": "4.0",
                    "datasetReference": {
                        "byPath": {"path": f"../Model{number}.SemanticModel"}
                    },
                }
            ),
            encoding="utf-8",
        )
        for page_number in range(20):
            page = report / "definition" / "pages" / f"page-{page_number}"
            page.mkdir(parents=True)
            (page / "page.json").write_text(
                json.dumps({"name": f"Page {page_number}"}), encoding="utf-8"
            )


def test_sc_031_typical_scope_inventory_is_complete_under_five_minutes(
    tmp_path: Path,
) -> None:
    project = tmp_path / "typical-scope"
    project.mkdir()
    _write_typical_scope_project(project)

    started = time.monotonic()
    assessment = assess_pbip(project)
    elapsed = time.monotonic() - started
    kinds = [component["kind"] for component in assessment["target"]["components"]]

    assert kinds.count("semantic_model") == 5
    assert kinds.count("report") == 5
    assert kinds.count("measure") == 500
    assert kinds.count("page") == 100
    assert elapsed < 300
