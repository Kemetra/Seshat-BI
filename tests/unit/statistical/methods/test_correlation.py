"""Oracle and guardrail tests for governed correlation evidence."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from types import MappingProxyType

import pytest

# The numerical stack is an optional extra; collection-skip without it so the
# base `.[dev]` suite never fails on an import it is not meant to satisfy.
pytest.importorskip("numpy")
pytest.importorskip("scipy")

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from seshat.statistical.contracts import (  # noqa: E402
    AnalysisSpec,
    AnalysisWithheld,
    ColumnBinding,
    MethodContext,
    MethodSpec,
)
from seshat.statistical.methods.correlation import run_correlate  # noqa: E402
from seshat.statistical.policy import PolicyContext  # noqa: E402
from seshat.statistical.providers.base import (  # noqa: E402
    ProviderProvenance,
    RectangularData,
)

pytestmark = pytest.mark.statistics


def _context(
    first,
    second,
    coefficient="pearson",
    missing_policy="pairwise",
    minimum=3,
) -> MethodContext:
    rows = tuple(zip(first, second, strict=True))
    spec = AnalysisSpec(
        "1.0",
        "correlation_example",
        1,
        "sample",
        "Are approved metrics associated?",
        "weekly",
        "Example Analyst",
        PurePosixPath("mappings/sample/readiness-status.yaml"),
        (PurePosixPath("mappings/sample/metrics/ApprovedMetric.yaml"),),
        MappingProxyType({"kind": "local_csv", "dataset_id": "sample"}),
        MappingProxyType({"grain": "one row", "inclusion": (), "exclusion": ()}),
        MappingProxyType(
            {
                "response": ColumnBinding("response", "number"),
                "predictor": ColumnBinding("predictor", "number"),
            }
        ),
        MethodSpec(
            "correlate",
            "1.0",
            MappingProxyType(
                {
                    "coefficient": coefficient,
                    "confidence_level": "0.95",
                    "correction": "holm",
                }
            ),
        ),
        missing_policy,
        MappingProxyType({"observations": minimum, "groups": 1, "seasonal_cycles": 0}),
        1729,
        MappingProxyType(
            {
                "classification": "none",
                "approval_evidence": (),
                "minimum_group_count": 1,
            }
        ),
        MappingProxyType({}),
    )
    data = RectangularData(
        ("response", "predictor"),
        rows,
        len(rows),
        0,
        (),
        ProviderProvenance("local_csv", "local_csv:test", "a" * 64, None, None),
    )
    policy = PolicyContext(
        "sample",
        Path("readiness-status.yaml"),
        "1",
        (),
        frozenset({"gold.sample"}),
        MappingProxyType({"gold.sample": frozenset({"response", "predictor"})}),
    )
    return MethodContext(spec, policy, data)


@pytest.mark.parametrize("coefficient", ("pearson", "spearman"))
def test_correlation_matches_scipy_and_has_seeded_interval(coefficient: str) -> None:
    first = np.array([1.0, 2.0, 4.0, 5.0, 7.0, 10.0])
    second = np.array([2.0, 1.0, 5.0, 4.0, 8.0, 9.0])
    result = run_correlate(_context(first, second, coefficient))
    expected = (
        stats.pearsonr(first, second)
        if coefficient == "pearson"
        else stats.spearmanr(first, second)
    )
    assert float(result.estimates[0].value) == pytest.approx(expected.statistic)
    assert float(result.tests[0].p_value) == pytest.approx(expected.pvalue)
    assert result.tests[0].adjusted_p_value == result.tests[0].p_value
    assert float(result.intervals[0].low) <= expected.statistic
    assert float(result.intervals[0].high) >= expected.statistic
    caution = result.interpretation_cautions[0].lower()
    assert "association" in caution and "caus" in caution


def test_pairwise_missingness_records_exclusions() -> None:
    result = run_correlate(_context([1, 2, None, 4, 5, 6], [2, None, 3, 5, 7, 8]))
    assert result.estimates[1].value == "4"
    assert result.estimates[2].value == "2"
    assert result.intervals == ()
    assert [item.code for item in result.diagnostics] == [
        "STAT_INTERVAL_WITHHELD",
        "STAT_MISSING_PAIRS_EXCLUDED",
    ]
    assert result.diagnostics[1].observed == "2"


def test_fail_missing_policy_withholds() -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_correlate(_context([1, None, 3], [1, 2, 4], missing_policy="fail"))
    assert exc_info.value.blockers[0].code == "STAT_MISSING_DATA"


@pytest.mark.parametrize(
    ("first", "second", "code"),
    (
        ([1, 1, 1, 1], [1, 2, 3, 4], "STAT_CONSTANT_INPUT"),
        ([1, 2], [2, 3], "STAT_MINIMUM_DATA"),
    ),
)
def test_undefined_association_is_withheld(first, second, code: str) -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_correlate(_context(first, second))
    assert exc_info.value.blockers[0].code == code
