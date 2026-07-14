"""Failure-closed safety boundaries for PBIP adoption."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from seshat.pbip_adoption import (
    MANIFEST_PATH,
    PbipAdoptionError,
    assess_pbip,
    assessment_exit_code,
    render_assessment_text,
)
from seshat.pbip_adoption._safety import _safe_detail

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "pbip_adoption"


def _copy(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    shutil.copytree(FIXTURES / name, target)
    return target


def test_unsupported_pbip_schema_is_visible_without_traceback(tmp_path: Path) -> None:
    result = assess_pbip(_copy(tmp_path, "unsupported_schema"))
    assert result["coverage"]["unsupported"] >= 1
    assert any(
        fact["classification"] == "unavailable_with_reason" for fact in result["facts"]
    )


def test_assessment_never_discloses_absolute_root_or_fixture_literal(
    tmp_path: Path,
) -> None:
    project = _copy(tmp_path, "unsafe_literal")
    assessment = assess_pbip(project)
    json_output = json.dumps(assessment)
    text_output = render_assessment_text(assessment)
    for output in (json_output, text_output):
        assert str(project) not in output
        assert "do-not-disclose" not in output
        assert "Traceback" not in output
    assert assessment["disclosure"] == {"status": "pass", "findings": []}


def test_missing_path_is_a_concise_input_defect() -> None:
    with pytest.raises(PbipAdoptionError, match="does not exist"):
        assess_pbip(Path("does-not-exist"))


def test_safe_detail_redacts_the_credential_value_not_only_its_key() -> None:
    # Redaction must remove the assigned secret itself, not just the key and
    # delimiter (which would leave the value in the emitted prose).
    for secret in (
        "Password='super-secret-value'",
        'server="db.internal.example"',
        "token= bare-secret-token",
        "Data Source=host.internal;Password=hunter2",
    ):
        redacted = _safe_detail(secret, fallback="none")
        assert "secret" not in redacted or "<redacted" in redacted
        assert "super-secret-value" not in redacted
        assert "db.internal.example" not in redacted
        assert "bare-secret-token" not in redacted
        assert "hunter2" not in redacted


def test_malformed_adoption_manifest_fails_closed_with_a_blocker(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "Adoption.pbip").write_text(
        '{"version": "1.0", "artifacts": []}\n', encoding="utf-8"
    )
    manifest = project / Path(MANIFEST_PATH)
    manifest.parent.mkdir(parents=True)
    # Present but not a usable fingerprint baseline (no authoritative_inputs).
    manifest.write_text("this: is not a baseline\n", encoding="utf-8")

    assessment = assess_pbip(project)

    baseline_blockers = [
        fact
        for fact in assessment["facts"]
        if fact["id"] == "blocked:adoption-baseline-unusable"
    ]
    assert baseline_blockers, "an unusable manifest must be surfaced, not ignored"
    assert baseline_blockers[0]["classification"] == "blocked"
    # Fail closed: the run does not silently continue with empty changes.
    assert assessment["next_step"]["blocking_reasons"]
    assert assessment_exit_code(assessment) == 1
