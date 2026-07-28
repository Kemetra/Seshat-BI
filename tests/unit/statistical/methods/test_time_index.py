"""Tests for strict regular-series normalization."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from types import MappingProxyType

import pytest

from seshat.statistical.contracts import (
    AnalysisSpec,
    AnalysisWithheld,
    ColumnBinding,
    MethodContext,
    MethodSpec,
)
from seshat.statistical.methods.time_index import regular_series, rolling_origins
from seshat.statistical.policy import PolicyContext
from seshat.statistical.providers.base import ProviderProvenance, RectangularData

pytestmark = pytest.mark.statistics


def time_context(timestamps, values, *, cadence="daily", period=2, cycles=0):
    rows = tuple(zip(timestamps, values, strict=True))
    spec = AnalysisSpec(
        "1.0",
        "time_example",
        1,
        "sample",
        "Is the approved series unusual?",
        cadence,
        "Example Analyst",
        PurePosixPath("mappings/sample/readiness-status.yaml"),
        (PurePosixPath("mappings/sample/metrics/ApprovedMetric.yaml"),),
        MappingProxyType({"kind": "local_csv", "dataset_id": "sample"}),
        MappingProxyType({"grain": "one row", "inclusion": (), "exclusion": ()}),
        MappingProxyType(
            {
                "time": ColumnBinding("time", "date"),
                "response": ColumnBinding("response", "number"),
            }
        ),
        MethodSpec(
            "detect_anomalies",
            "1.0",
            MappingProxyType(
                {"model": "trailing_mad", "period": period, "threshold": "3.5"}
            ),
        ),
        "complete_case",
        MappingProxyType({"observations": 2, "groups": 1, "seasonal_cycles": cycles}),
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
        ("time", "response"),
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
        MappingProxyType({"gold.sample": frozenset({"time", "response"})}),
    )
    return MethodContext(spec, policy, data)


def test_unsorted_unique_series_is_normalized_after_validation() -> None:
    result = regular_series(
        time_context(
            ["2026-01-03", "2026-01-01", "2026-01-02"],
            [3, 1, 2],
        )
    )
    assert result.timestamps == ("2026-01-01", "2026-01-02", "2026-01-03")
    assert result.values.tolist() == [1.0, 2.0, 3.0]
    assert result.frequency == "daily"
    assert result.excluded_partial_period is None


@pytest.mark.parametrize(
    ("timestamps", "code"),
    (
        (
            ["2026-01-01", "2026-01-01", "2026-01-02"],
            "STAT_TIME_DUPLICATE",
        ),
        (["2026-01-01", "2026-01-03"], "STAT_TIME_IRREGULAR"),
        (["2026-01-01", ""], "STAT_TIME_MISSING"),
        (["2026-01-01", "not-a-date"], "STAT_TIME_UNPARSEABLE"),
        (
            ["2026-01-01T00:00:00Z", "2026-01-02T00:00:00+02:00"],
            "STAT_TIMEZONE_MIXED",
        ),
    ),
)
def test_invalid_time_indexes_are_withheld(timestamps, code) -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        regular_series(time_context(timestamps, range(len(timestamps))))
    assert exc_info.value.blockers[0].code == code


def test_monthly_contiguity_and_seasonal_cycle_floor() -> None:
    timestamps = [f"2025-{month:02d}-01" for month in range(1, 7)]
    result = regular_series(
        time_context(timestamps, range(6), cadence="monthly", period=3, cycles=2)
    )
    assert result.seasonal_period == 3

    with pytest.raises(AnalysisWithheld) as exc_info:
        regular_series(
            time_context(
                timestamps[:5], range(5), cadence="monthly", period=3, cycles=2
            )
        )
    assert exc_info.value.blockers[0].code == "STAT_SEASONAL_HISTORY"


def test_rolling_origins_never_include_the_evaluated_point() -> None:
    origins = rolling_origins(10, 4, step=2)
    assert [(item.source_end, item.evaluate_index) for item in origins] == [
        (3, 4),
        (5, 6),
        (7, 8),
    ]
    assert all(item.source_end == item.evaluate_index - 1 for item in origins)
