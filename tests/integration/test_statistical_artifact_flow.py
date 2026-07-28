"""Synthetic end-to-end proof for governed statistical evidence."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from seshat.cli import main
from seshat.ecosystem_contracts import validate_json_contract

pytestmark = pytest.mark.statistics

_ROOT = Path(__file__).parents[2]
_FIXTURES = _ROOT / "tests" / "fixtures" / "statistical"
_EVIDENCE_SCHEMA = json.loads(
    (_ROOT / "schemas" / "statistical-analysis-evidence.schema.json").read_text(
        encoding="utf-8"
    )
)


def _copy_fixture_repo(tmp_path: Path, name: str) -> Path:
    root = tmp_path / name
    shutil.copytree(_FIXTURES / name, root)
    return root


def test_synthetic_full_flow_writes_valid_derived_evidence(
    tmp_path: Path, capsys
) -> None:
    root = _copy_fixture_repo(tmp_path, "full_flow")
    readiness_path = root / "mappings/sample_orders/readiness-status.yaml"
    readiness_before = readiness_path.read_bytes()
    evidence_path = root / "mappings/sample_orders/analyses/weekly_signal.evidence.json"
    review_path = root / "mappings/sample_orders/analyses/weekly_signal.review.md"

    validation_rc = main(
        [
            "analyze",
            "validate",
            "--repo",
            str(root),
            "--spec",
            "mappings/sample_orders/analyses/weekly_signal.analysis.yaml",
            "--format",
            "json",
        ],
        prog="seshat",
    )
    validation = json.loads(capsys.readouterr().out)
    assert validation_rc == 0
    assert validation["outcome"] == "computed"
    assert not evidence_path.exists()
    assert not review_path.exists()

    rc = main(
        [
            "analyze",
            "run",
            "--repo",
            str(root),
            "--spec",
            "mappings/sample_orders/analyses/weekly_signal.analysis.yaml",
            "--provider",
            "local_csv",
            "--input",
            "data/weekly_metric.csv",
            "--format",
            "json",
        ],
        prog="seshat",
    )

    assert rc == 0
    response = json.loads(capsys.readouterr().out)
    assert response["evidence_path"] == (
        "mappings/sample_orders/analyses/weekly_signal.evidence.json"
    )
    assert response["review_path"] == (
        "mappings/sample_orders/analyses/weekly_signal.review.md"
    )

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert validate_json_contract(evidence, _EVIDENCE_SCHEMA) == []
    assert evidence["outcome"] == "computed"
    assert evidence["authority"] == "derived-evidence-only"
    assert evidence["review_state"] == "pending"
    assert evidence["readiness_effect"] == ("none; named-human approval required")
    assert evidence["input"]["input_count"] == 36
    assert evidence["diagnostics"][0]["code"] == "STAT_OUTLIER_RULE_NONE"
    assert "rows" not in evidence

    review = review_path.read_text(encoding="utf-8")
    assert (
        "It does not recompute statistics, grant approval, or change readiness"
        in review
    )
    assert "- [ ] accepted" in review
    assert "Reviewer:" in review

    evidence_before_render = evidence_path.read_bytes()
    review_path.write_text("stale local projection\n", encoding="utf-8")
    render_rc = main(
        [
            "analyze",
            "render",
            "--repo",
            str(root),
            "--evidence",
            "mappings/sample_orders/analyses/weekly_signal.evidence.json",
            "--format",
            "json",
        ],
        prog="seshat",
    )
    rendered = json.loads(capsys.readouterr().out)
    assert render_rc == 0
    assert rendered["outcome"] == "computed"
    assert evidence_path.read_bytes() == evidence_before_render
    assert review_path.read_text(encoding="utf-8").startswith(
        "# Statistical analysis review"
    )
    assert readiness_path.read_bytes() == readiness_before
