"""Oracle and safeguard tests for governed proportion evidence."""

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
from seshat.statistical.methods.proportions import run_proportion  # noqa: E402

from ._support import SpecSettings, method_context  # noqa: E402

pytestmark = pytest.mark.statistics


@dataclass(frozen=True, slots=True)
class _Options:
    """The knobs a proportion test varies on the governed specification."""

    grouped: bool = False
    interval: str = "wilson"
    comparison: str = "none"
    correction: str = "none"
    minimum_denominator: int = 1
    missing_policy: str = "complete_case"
    privacy_floor: int = 1


def _context(rows: list[tuple], **overrides: object) -> MethodContext:
    options = _Options(**overrides)  # type: ignore[arg-type]
    columns = (
        ("successes", "trials", "group") if options.grouped else ("successes", "trials")
    )
    roles = {
        "numerator": ColumnBinding("successes", "integer"),
        "denominator": ColumnBinding("trials", "integer"),
    }
    if options.grouped:
        roles["group"] = ColumnBinding("group", "category")
    parameters: dict[str, object] = {
        "interval": options.interval,
        "alternative": "two-sided",
        "confidence_level": "0.95",
        "comparison": options.comparison,
        "zero_cell_correction": options.correction,
        "minimum_denominator": options.minimum_denominator,
    }
    settings = SpecSettings(
        analysis_id="proportion_example",
        question="What is the governed rate?",
        method_id="proportion",
        parameters=parameters,
        roles=roles,
        missing_policy=options.missing_policy,
        privacy_floor=options.privacy_floor,
        grain="aggregated counts",
    )
    return method_context(settings, columns, rows)


def _interval(result, name: str):
    return next(item for item in result.intervals if item.name == name)


def _effect(result, name: str) -> float:
    return float(next(item.value for item in result.effect_sizes if item.name == name))


@pytest.mark.parametrize(
    ("method", "scipy_method"),
    (("wilson", "wilson"), ("exact_binomial", "exact")),
)
def test_single_proportion_interval_matches_scipy(
    method: str, scipy_method: str
) -> None:
    result = run_proportion(_context([(42, 100)], interval=method))
    expected = stats.binomtest(42, 100).proportion_ci(method=scipy_method)
    observed = _interval(result, "proportion")
    assert float(observed.low) == pytest.approx(expected.low)
    assert float(observed.high) == pytest.approx(expected.high)


def test_chi_square_comparison_and_effects_match_direct_formulas() -> None:
    result = run_proportion(
        _context(
            [(42, 100, "A"), (30, 100, "B")],
            grouped=True,
            comparison="chi_square",
        )
    )
    table = np.array([[42, 58], [30, 70]])
    expected = stats.chi2_contingency(table, correction=False)
    assert float(result.tests[0].statistic) == pytest.approx(expected.statistic)
    assert float(result.tests[0].p_value) == pytest.approx(expected.pvalue)
    assert _effect(result, "risk_difference") == pytest.approx(0.12)
    assert _effect(result, "risk_ratio") == pytest.approx(0.42 / 0.30)
    assert _effect(result, "odds_ratio") == pytest.approx((42 * 70) / (58 * 30))
    assert {item.name for item in result.intervals} == {
        "risk_difference",
        "risk_ratio",
        "odds_ratio",
    }


def test_fisher_exact_matches_scipy() -> None:
    result = run_proportion(
        _context(
            [(1, 10, "A"), (8, 10, "B")],
            grouped=True,
            comparison="fisher_exact",
        )
    )
    expected = stats.fisher_exact([[1, 9], [8, 2]])
    assert float(result.tests[0].statistic) == pytest.approx(expected.statistic)
    assert float(result.tests[0].p_value) == pytest.approx(expected.pvalue)


@pytest.mark.parametrize(
    ("rows", "kwargs", "code"),
    (
        ([(0, 0)], {}, "STAT_ZERO_DENOMINATOR"),
        ([(11, 10)], {}, "STAT_INVALID_PROPORTION"),
        ([(1, 10)], {"minimum_denominator": 20}, "STAT_MINIMUM_DENOMINATOR"),
        (
            [(1, 10, "A"), (2, 10, "B")],
            {"grouped": True, "comparison": "chi_square"},
            "STAT_EXPECTED_CELL_COUNT",
        ),
        (
            [(0, 10, "A"), (5, 10, "B")],
            {"grouped": True, "comparison": "fisher_exact"},
            "STAT_ZERO_CELL",
        ),
    ),
)
def test_invalid_or_sparse_inputs_are_withheld(rows, kwargs, code: str) -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_proportion(_context(rows, **kwargs))
    assert exc_info.value.blockers[0].code == code


def test_haldane_anscombe_is_used_only_when_explicit() -> None:
    result = run_proportion(
        _context(
            [(0, 10, "A"), (5, 10, "B")],
            grouped=True,
            comparison="fisher_exact",
            correction="haldane-anscombe",
        )
    )
    assert result.tests
    assert all(
        item.low is not None and item.high is not None for item in result.intervals
    )


def test_missing_status_policy_is_explicit() -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_proportion(_context([(1, 2), (None, 3)], missing_policy="fail"))
    assert exc_info.value.blockers[0].code == "STAT_MISSING_DATA"

    result = run_proportion(_context([(1, 2), (None, 3)]))
    assert result.diagnostics[0].observed == "1"
