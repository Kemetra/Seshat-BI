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


_SPEC = "mappings/sample_orders/analyses/weekly_signal.analysis.yaml"
_EVIDENCE = "mappings/sample_orders/analyses/weekly_signal.evidence.json"
_REVIEW = "mappings/sample_orders/analyses/weekly_signal.review.md"


def _analyze(root: Path, capsys, subcommand: str, *arguments: str) -> tuple[int, dict]:
    """Run one analyze subcommand and return its exit code with its JSON response."""

    argv = [
        "analyze",
        subcommand,
        "--repo",
        str(root),
        *arguments,
        "--format",
        "json",
    ]
    code = main(argv, prog="seshat")
    return code, json.loads(capsys.readouterr().out)


def _assert_derived_evidence(evidence: dict) -> None:
    """The written evidence is schema-valid, computed, and claims no authority."""

    assert validate_json_contract(evidence, _EVIDENCE_SCHEMA) == []
    assert evidence["outcome"] == "computed"
    assert evidence["authority"] == "derived-evidence-only"
    assert evidence["review_state"] == "pending"
    assert evidence["readiness_effect"] == "none; named-human approval required"
    assert evidence["input"]["input_count"] == 36
    assert evidence["diagnostics"][0]["code"] == "STAT_OUTLIER_RULE_NONE"
    assert "rows" not in evidence


def _assert_review_awaits_a_human(review: str) -> None:
    assert (
        "It does not recompute statistics, grant approval, or change readiness"
        in review
    )
    assert "- [ ] accepted" in review
    assert "Reviewer:" in review


def test_synthetic_full_flow_writes_valid_derived_evidence(
    tmp_path: Path, capsys
) -> None:
    root = _copy_fixture_repo(tmp_path, "full_flow")
    readiness_path = root / "mappings/sample_orders/readiness-status.yaml"
    readiness_before = readiness_path.read_bytes()
    evidence_path = root / _EVIDENCE
    review_path = root / _REVIEW

    validation_rc, validation = _analyze(root, capsys, "validate", "--spec", _SPEC)
    assert validation_rc == 0
    assert validation["outcome"] == "computed"
    assert not evidence_path.exists()
    assert not review_path.exists()

    rc, response = _analyze(
        root,
        capsys,
        "run",
        "--spec",
        _SPEC,
        "--provider",
        "local_csv",
        "--input",
        "data/weekly_metric.csv",
    )
    assert rc == 0
    assert response["evidence_path"] == _EVIDENCE
    assert response["review_path"] == _REVIEW
    _assert_derived_evidence(json.loads(evidence_path.read_text(encoding="utf-8")))
    _assert_review_awaits_a_human(review_path.read_text(encoding="utf-8"))

    evidence_before_render = evidence_path.read_bytes()
    review_path.write_text("stale local projection\n", encoding="utf-8")
    render_rc, rendered = _analyze(root, capsys, "render", "--evidence", _EVIDENCE)
    assert render_rc == 0
    assert rendered["outcome"] == "computed"
    assert evidence_path.read_bytes() == evidence_before_render
    assert review_path.read_text(encoding="utf-8").startswith(
        "# Statistical analysis review"
    )
    assert readiness_path.read_bytes() == readiness_before


_FORECAST_SPEC = "mappings/sample_orders/analyses/weekly_forecast.analysis.yaml"
_FORECAST_EVIDENCE = "mappings/sample_orders/analyses/weekly_forecast.evidence.json"


def test_forecast_flow_selects_a_backtested_candidate_without_granting_authority(
    tmp_path: Path, capsys
) -> None:
    """The documented forecast example runs and stays derived evidence.

    Guards docs/worked-examples/statistical-forecast.md: every published number
    comes from this fixture, so a drifting engine breaks the test rather than
    the documentation silently going stale.
    """

    root = _copy_fixture_repo(tmp_path, "forecast_flow")
    readiness_path = root / "mappings/sample_orders/readiness-status.yaml"
    readiness_before = readiness_path.read_bytes()

    rc, response = _analyze(
        root,
        capsys,
        "run",
        "--spec",
        _FORECAST_SPEC,
        "--provider",
        "local_csv",
        "--input",
        "data/weekly_metric.csv",
    )
    assert rc == 0
    assert response["outcome"] == "computed"

    evidence = json.loads((root / _FORECAST_EVIDENCE).read_text(encoding="utf-8"))
    assert validate_json_contract(evidence, _EVIDENCE_SCHEMA) == []
    assert evidence["authority"] == "derived-evidence-only"
    assert evidence["review_state"] == "pending"
    assert evidence["readiness_effect"] == "none; named-human approval required"
    assert "rows" not in evidence

    estimates = {item["name"]: item["value"] for item in evidence["estimates"]}
    scored = {
        name.split(":", 1)[1]
        for name in estimates
        if name.startswith("backtest_mean_mase:")
    }
    assert scored == {"naive", "seasonal_naive", "ets_add", "ets_add_trend"}, (
        "every declared candidate must be backtested, not just the winner"
    )

    codes = {item["code"] for item in evidence["diagnostics"]}
    assert "STAT_FORECAST_SELECTED" in codes, (
        "candidate selection must be recorded as evidence, never left implicit"
    )

    horizon = [name for name in estimates if name.startswith("forecast:")]
    assert len(horizon) == 4, "declared horizon of 4 must yield 4 forecast points"
    intervals = {item["name"] for item in evidence["intervals"]}
    assert set(horizon) <= intervals, "every forecast point needs a declared interval"
    for interval in evidence["intervals"]:
        assert interval["level"] == "0.95"
        assert float(interval["low"]) < float(interval["high"])

    assert any("not guarantees" in caution for caution in evidence["cautions"]), (
        "forecast evidence must retain its scenario-not-guarantee caution"
    )
    assert readiness_path.read_bytes() == readiness_before
