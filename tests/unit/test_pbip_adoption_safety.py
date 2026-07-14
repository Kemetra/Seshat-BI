"""Failure-closed safety boundaries for PBIP adoption."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from seshat.pbip_adoption import PbipAdoptionError, assess_pbip, render_assessment_text

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
