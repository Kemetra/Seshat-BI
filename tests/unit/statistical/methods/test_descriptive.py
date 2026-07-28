"""Oracle, edge-case, privacy, and property tests for descriptive statistics."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

# The numerical stack is an optional extra; collection-skip without it so the
# base `.[dev]` suite never fails on an import it is not meant to satisfy.
pytest.importorskip("numpy")
pytest.importorskip("scipy")

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from seshat.statistical.contracts import (  # noqa: E402
    AnalysisWithheld,
    ColumnBinding,
    MethodContext,
)
from seshat.statistical.methods.descriptive import run_describe  # noqa: E402

from ._support import SpecSettings, method_context  # noqa: E402

pytestmark = pytest.mark.statistics


@dataclass(frozen=True, slots=True)
class _Options:
    """The knobs a descriptive test varies on the governed specification."""

    groups: list[object] | None = None
    missing_policy: str = "complete_case"
    minimum: int = 1
    privacy_floor: int = 2
    outlier_rule: str = "mad"
    quantiles: tuple[str, ...] = ("0.25", "0.5", "0.75")


def _context(values: list[object], **overrides: object) -> MethodContext:
    options = _Options(**overrides)  # type: ignore[arg-type]
    groups = options.groups
    columns = ("value", "group") if groups is not None else ("value",)
    rows = (
        tuple(zip(values, groups, strict=True))
        if groups is not None
        else tuple((value,) for value in values)
    )
    roles = {"response": ColumnBinding("value", "number")}
    if groups is not None:
        roles["group"] = ColumnBinding("group", "category")
    settings = SpecSettings(
        analysis_id="describe_example",
        question="What is the governed distribution?",
        method_id="describe",
        parameters={
            "quantiles": options.quantiles,
            "outlier_rule": options.outlier_rule,
        },
        roles=roles,
        missing_policy=options.missing_policy,
        minimum_data={
            "observations": options.minimum,
            "groups": 1,
            "seasonal_cycles": 0,
        },
        privacy_floor=options.privacy_floor,
    )
    return method_context(settings, columns, rows)


def _estimate(result, name: str) -> float | None:
    value = next(item.value for item in result.estimates if item.name == name)
    return None if value is None else float(value)


def _diagnostic(result, code: str):
    return next(item for item in result.diagnostics if item.code == code)


def test_describe_matches_numpy_and_scipy_oracles() -> None:
    values = np.array([1.0, 2.0, 3.0, 4.0, 100.0])
    result = run_describe(_context(values.tolist()))

    assert _estimate(result, "mean") == pytest.approx(np.mean(values))
    assert _estimate(result, "median") == pytest.approx(np.median(values))
    assert _estimate(result, "variance_sample") == pytest.approx(np.var(values, ddof=1))
    assert _estimate(result, "variance_population") == pytest.approx(
        np.var(values, ddof=0)
    )
    assert _estimate(result, "std_sample") == pytest.approx(np.std(values, ddof=1))
    assert _estimate(result, "std_population") == pytest.approx(np.std(values, ddof=0))
    assert _estimate(result, "skewness") == pytest.approx(
        stats.skew(values, bias=False)
    )
    assert _estimate(result, "kurtosis") == pytest.approx(
        stats.kurtosis(values, bias=False)
    )
    assert _estimate(result, "minimum") == 1
    assert _estimate(result, "maximum") == 100
    assert _estimate(result, "quantile_0.25") == 2
    assert _estimate(result, "quantile_0.5") == 3
    assert _estimate(result, "quantile_0.75") == 4
    assert _estimate(result, "iqr") == 2
    assert _estimate(result, "mad") == 1
    assert _estimate(result, "count_observed") == 5
    assert _estimate(result, "count_missing") == 0
    assert _estimate(result, "count_distinct") == 5
    assert _estimate(result, "outlier_count") == 1


def test_complete_case_records_missing_and_excluded_counts() -> None:
    result = run_describe(_context([1, None, "", "  ", 2]))
    assert _estimate(result, "count_observed") == 2
    assert _estimate(result, "count_missing") == 3
    assert _estimate(result, "count_excluded") == 3


def test_fail_missing_policy_withholds() -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_describe(_context([1, None, 2], missing_policy="fail"))
    assert exc_info.value.blockers[0].code == "STAT_MISSING_DATA"


@pytest.mark.parametrize("values", ([], [None, ""], [1]))
def test_insufficient_observations_withhold(values: list[object]) -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_describe(_context(values, minimum=2))
    assert exc_info.value.blockers[0].code == "STAT_MINIMUM_DATA"


def test_singleton_and_constant_samples_never_emit_non_finite_results() -> None:
    singleton = run_describe(_context([5]))
    assert _estimate(singleton, "variance_sample") is None
    assert _estimate(singleton, "std_sample") is None
    assert (
        _diagnostic(singleton, "STAT_SAMPLE_DISPERSION_UNDEFINED").status == "warning"
    )

    constant = run_describe(_context([5, 5, 5, 5]))
    assert _estimate(constant, "skewness") is None
    assert _estimate(constant, "kurtosis") is None
    assert _estimate(constant, "outlier_count") is None
    assert _diagnostic(constant, "STAT_MAD_ZERO").status == "warning"


def test_groups_below_privacy_floor_are_suppressed_without_label_leakage() -> None:
    result = run_describe(
        _context(
            [1, 2, 3, 100],
            groups=["public", "public", "public", "secret-person"],
            privacy_floor=2,
        )
    )
    rendered = repr(result)
    assert "group[public].mean" in rendered
    assert "secret-person" not in rendered
    diagnostic = _diagnostic(result, "STAT_GROUPS_SUPPRESSED")
    assert diagnostic.observed == "1"


@pytest.mark.parametrize("outlier_rule", ("iqr", "mad"))
def test_translation_and_positive_scale_preserve_descriptive_properties(
    outlier_rule: str,
) -> None:
    values = np.array([1.0, 2.0, 3.0, 4.0, 100.0])
    transformed = 7.0 * values - 13.0
    original = run_describe(_context(values.tolist(), outlier_rule=outlier_rule))
    changed = run_describe(_context(transformed.tolist(), outlier_rule=outlier_rule))

    assert _estimate(changed, "mean") == pytest.approx(
        7 * _estimate(original, "mean") - 13
    )
    assert _estimate(changed, "median") == pytest.approx(
        7 * _estimate(original, "median") - 13
    )
    assert _estimate(changed, "std_sample") == pytest.approx(
        7 * _estimate(original, "std_sample")
    )
    assert _estimate(changed, "iqr") == pytest.approx(7 * _estimate(original, "iqr"))
    assert _estimate(changed, "mad") == pytest.approx(7 * _estimate(original, "mad"))
    assert _estimate(changed, "outlier_count") == _estimate(original, "outlier_count")
