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

    # The values published in docs/worked-examples/statistical-forecast.md.
    # Asserting the names alone would let a numerical change rewrite every
    # documented number while this test still passed.
    documented_mase = {
        "naive": 0.851,
        "seasonal_naive": 0.970,
        "ets_add": 0.833,
        "ets_add_trend": 0.221,
    }
    for candidate, published in documented_mase.items():
        actual = float(estimates[f"backtest_mean_mase:{candidate}"])
        assert actual == pytest.approx(published, abs=0.001), (
            f"{candidate} scored {actual:.4f}; the worked example publishes {published}"
        )
    assert min(documented_mase, key=documented_mase.get) == "ets_add_trend", (
        "the example states ets_add_trend wins selection"
    )

    horizon = [name for name in estimates if name.startswith("forecast:")]
    assert len(horizon) == 4, "declared horizon of 4 must yield 4 forecast points"
    documented_points = [138.367, 139.396, 140.425, 141.453]
    for step, published in enumerate(documented_points, start=1):
        actual = float(estimates[f"forecast:{step}"])
        assert actual == pytest.approx(published, abs=0.001), (
            f"forecast:{step} is {actual:.3f}; the worked example publishes {published}"
        )

    intervals = {item["name"] for item in evidence["intervals"]}
    assert set(horizon) <= intervals, "every forecast point needs a declared interval"
    documented_bounds = {
        "forecast:1": (136.255, 140.479),
        "forecast:2": (137.284, 141.508),
        "forecast:3": (138.313, 142.537),
        "forecast:4": (139.341, 143.566),
    }
    for interval in evidence["intervals"]:
        assert interval["level"] == "0.95"
        assert float(interval["low"]) < float(interval["high"])
        low, high = documented_bounds[interval["name"]]
        assert float(interval["low"]) == pytest.approx(low, abs=0.001)
        assert float(interval["high"]) == pytest.approx(high, abs=0.001)

    assert any("not guarantees" in caution for caution in evidence["cautions"]), (
        "forecast evidence must retain its scenario-not-guarantee caution"
    )
    assert readiness_path.read_bytes() == readiness_before


# Each case carries the estimates docs/worked-examples/statistical-catalog.md
# publishes, so a numerical change fails here instead of staling the page.
_CATALOG_CASES = (
    (
        "regional_comparison",
        "regional_weeks.csv",
        "compare_groups",
        {"group[north].count": 48.0, "group[south].count": 48.0},
    ),
    (
        "conversion_rate",
        "regional_weeks.csv",
        "proportion",
        {"successes": 4697.0, "trials": 45192.0, "proportion": 0.10393},
    ),
    (
        "visits_correlation",
        "weekly_series.csv",
        "correlate",
        {"correlation": 0.880, "paired_count": 48.0, "excluded_pair_count": 0.0},
    ),
    (
        "visits_regression",
        "weekly_series.csv",
        "regress",
        {"coefficient:predictor": 0.19290, "standard_error:predictor": 0.03105},
    ),
    (
        "weekly_anomalies",
        "weekly_series.csv",
        "detect_anomalies",
        {"observed:2025-09-01": 146.0, "baseline_center:2025-09-01": 112.0},
    ),
    (
        "weekly_change_points",
        "weekly_series.csv",
        "detect_change_points",
        {
            "breakpoint_index:1": 12.0,
            "breakpoint_index:2": 19.0,
            "breakpoint_index:3": 29.0,
            "breakpoint_index:4": 35.0,
            "breakpoint_index:5": 41.0,
        },
    ),
)


@pytest.mark.parametrize(
    ("analysis", "dataset", "method", "documented"), _CATALOG_CASES
)
def test_every_catalog_method_computes_without_granting_authority(
    tmp_path: Path,
    capsys,
    analysis: str,
    dataset: str,
    method: str,
    documented: dict[str, float],
) -> None:
    """Each remaining catalog method runs end to end and stays derived evidence.

    Guards docs/worked-examples/statistical-catalog.md: the published numbers
    come from this fixture, so an engine change breaks the test rather than
    leaving the documentation quietly wrong.
    """

    root = _copy_fixture_repo(tmp_path, "catalog_flow")
    readiness_path = root / "mappings/sample_orders/readiness-status.yaml"
    readiness_before = readiness_path.read_bytes()

    rc, response = _analyze(
        root,
        capsys,
        "run",
        "--spec",
        f"mappings/sample_orders/analyses/{analysis}.analysis.yaml",
        "--provider",
        "local_csv",
        "--input",
        f"data/{dataset}",
    )
    assert rc == 0, f"{analysis} did not compute: {response}"
    assert response["outcome"] == "computed"

    evidence = json.loads(
        (root / f"mappings/sample_orders/analyses/{analysis}.evidence.json").read_text(
            encoding="utf-8"
        )
    )
    assert validate_json_contract(evidence, _EVIDENCE_SCHEMA) == []
    assert evidence["method"]["id"] == method
    assert evidence["authority"] == "derived-evidence-only"
    assert evidence["review_state"] == "pending"
    assert evidence["readiness_effect"] == "none; named-human approval required"
    assert evidence["estimates"], "a computed method must publish estimates"
    assert "rows" not in evidence, "evidence must never carry raw rows"

    estimates = {item["name"]: item["value"] for item in evidence["estimates"]}
    for name, published in documented.items():
        assert name in estimates, (
            f"{analysis} no longer emits `{name}`, which the worked example publishes"
        )
        actual = float(estimates[name])
        assert actual == pytest.approx(published, rel=1e-3, abs=1e-4), (
            f"{analysis} `{name}` is {actual}; the worked example publishes {published}"
        )

    if analysis == "regional_comparison":
        test_result = next(t for t in evidence["tests"] if t["name"] == "welch_t")
        assert float(test_result["statistic"]) == pytest.approx(9.6547, abs=0.001)
        effect = next(e for e in evidence["effect_sizes"] if e["name"] == "hedges_g")
        assert float(effect["value"]) == pytest.approx(1.9550, abs=0.001)

    if analysis == "conversion_rate":
        interval = evidence["intervals"][0]
        assert float(interval["low"]) == pytest.approx(0.101154, abs=1e-5)
        assert float(interval["high"]) == pytest.approx(0.106781, abs=1e-5)

    if analysis == "visits_regression":
        codes = {item["code"] for item in evidence["diagnostics"]}
        assert {
            "STAT_RESIDUAL_NORMALITY",
            "STAT_HETEROSKEDASTICITY",
            "STAT_INFLUENCE",
            "STAT_REGRESSION_CONDITION",
            "STAT_REGRESSION_VIF",
        } <= codes, "the worked example lists all five regression diagnostics"

    assert readiness_path.read_bytes() == readiness_before


def test_trailing_anomaly_flags_only_the_injected_excursion(
    tmp_path: Path, capsys
) -> None:
    """The documented anomaly run flags the spike, not the whole series.

    Regression guard for the double-subtracted baseline center: that defect
    flagged all 23 evaluated weeks on this fixture, which reads as a working
    detector until the flags are compared against the observations.
    """

    root = _copy_fixture_repo(tmp_path, "catalog_flow")
    rc, _ = _analyze(
        root,
        capsys,
        "run",
        "--spec",
        "mappings/sample_orders/analyses/weekly_anomalies.analysis.yaml",
        "--provider",
        "local_csv",
        "--input",
        "data/weekly_series.csv",
    )
    assert rc == 0

    evidence = json.loads(
        (
            root / "mappings/sample_orders/analyses/weekly_anomalies.evidence.json"
        ).read_text(encoding="utf-8")
    )
    estimates = {item["name"]: item["value"] for item in evidence["estimates"]}
    evaluated = [name for name in estimates if name.startswith("anomaly:")]
    flagged = [name for name in evaluated if estimates[name] == "1"]

    weeks_in_fixture = 48
    assert 0 < len(evaluated) < weeks_in_fixture, (
        "the prior-only rule must skip the early weeks that have no history, "
        "and must still judge the rest"
    )
    assert len(flagged) < len(evaluated) / 2, (
        f"{len(flagged)} of {len(evaluated)} weeks flagged; a detector that "
        f"flags most of a quiet series is measuring the series level, not a "
        f"deviation from it"
    )
    assert "anomaly:2025-09-01" in flagged, "the injected excursion must flag"

    for name in flagged:
        week = name.split(":", 1)[1]
        deviation = abs(
            float(estimates[f"observed:{week}"])
            - float(estimates[f"baseline_center:{week}"])
        )
        assert deviation > float(estimates[f"threshold:{week}"]), (
            f"{week} was flagged although it sits inside its own threshold"
        )
