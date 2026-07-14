"""Read-only assessment behavior for governed existing-PBIP adoption."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from seshat.pbip_adoption import (
    PbipAdoptionError,
    assess_pbip,
    canonical_assessment_digest,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "pbip_adoption"


def _copy_fixture(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    shutil.copytree(FIXTURES / name, target)
    return target


def _hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_supported_project_is_inventory_only_deterministic_and_byte_identical(
    tmp_path: Path,
) -> None:
    project = _copy_fixture(tmp_path, "supported")
    before = _hashes(project)
    first = assess_pbip(project)
    second = assess_pbip(project)
    assert first == second
    assert before == _hashes(project)
    assert first["assessment_digest"] == canonical_assessment_digest(first)
    kinds = {component["kind"] for component in first["target"]["components"]}
    assert {
        "project",
        "semantic_model",
        "report",
        "table",
        "measure",
        "relationship",
        "parameter",
        "page",
        "visual",
    } <= kinds
    assert all(
        fact["artifact"]
        for fact in first["facts"]
        if fact["classification"] == "observed"
    )
    assert any(fact["classification"] == "proposed" for fact in first["facts"])
    assert first["next_step"]["stage"] == "source_ready"
    assert first["scaffold_plan"]["approvals"] == []


def test_missing_model_and_multi_model_remain_explicit_boundaries(
    tmp_path: Path,
) -> None:
    missing = assess_pbip(_copy_fixture(tmp_path, "missing_model"))
    assert any(
        fact["id"].startswith("missing:pbir-model-target") for fact in missing["facts"]
    )

    multi = assess_pbip(_copy_fixture(tmp_path, "multi_model"))
    assert multi["coverage"]["ambiguous"] >= 2
    assert multi["next_step"]["required_authority"] == "analyst"
    assert any(
        fact["id"] == "blocked:multiple-semantic-models" for fact in multi["facts"]
    )


def test_unsafe_literal_and_out_of_root_reference_are_redacted_and_blocked(
    tmp_path: Path,
) -> None:
    unsafe = assess_pbip(_copy_fixture(tmp_path, "unsafe_literal"))
    rendered = json.dumps(unsafe)
    assert "do-not-disclose" not in rendered
    assert {fact["rule_id"] for fact in unsafe["facts"]} & {"C1", "C2"}

    escaped = assess_pbip(_copy_fixture(tmp_path, "out_of_root"))
    assert any(
        fact["id"].startswith("blocked:pbir-reference-escape")
        for fact in escaped["facts"]
    )
    assert all(
        not Path(component["artifact"]).is_absolute()
        for component in escaped["target"]["components"]
    )


def test_pbix_is_a_terminal_conversion_boundary_without_binary_parsing(
    tmp_path: Path,
) -> None:
    boundary = _copy_fixture(tmp_path, "pbix_boundary") / "Legacy.pbix"
    before = boundary.read_bytes()
    assessment = assess_pbip(boundary)
    assert assessment["target"]["kind"] == "pbix_unsupported"
    assert assessment["next_step"]["kind"] == "terminal_stop"
    assert "PBIP" in assessment["next_step"]["action"]
    assert boundary.read_bytes() == before


def test_external_symlink_is_refused_before_inventory(tmp_path: Path) -> None:
    project = _copy_fixture(tmp_path, "supported")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = project / "linked-outside.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable in this Windows test environment")
    with pytest.raises(PbipAdoptionError, match="outside"):
        assess_pbip(project)
