"""Tests for strict regular-series normalization."""

from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

from seshat.statistical.contracts import (
    AnalysisWithheld,
    ColumnBinding,
    MethodContext,
    MethodSpec,
)
from seshat.statistical.methods.time_index import regular_series, rolling_origins

from ._support import SpecSettings, method_context

pytestmark = pytest.mark.statistics


@dataclass(frozen=True, slots=True)
class _Options:
    """The cadence and seasonality a time-series test declares."""

    cadence: str = "daily"
    period: int = 2
    cycles: int = 0


def time_context(timestamps, values, **overrides: object) -> MethodContext:
    """Build the governed context every regular-series method test starts from."""

    options = _Options(**overrides)  # type: ignore[arg-type]
    columns = ("time", "response")
    rows = tuple(zip(timestamps, values, strict=True))
    settings = SpecSettings(
        analysis_id="time_example",
        question="Is the approved series unusual?",
        method_id="detect_anomalies",
        parameters={
            "model": "trailing_mad",
            "period": options.period,
            "threshold": "3.5",
        },
        roles={
            "time": ColumnBinding("time", "date"),
            "response": ColumnBinding("response", "number"),
        },
        minimum_data={
            "observations": 2,
            "groups": 1,
            "seasonal_cycles": options.cycles,
        },
        privacy_floor=1,
        cadence=options.cadence,
    )
    return method_context(settings, columns, rows)


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


def test_declared_partial_final_period_is_excluded_or_withheld() -> None:
    context = time_context(["2026-01-01", "2026-01-02", "2026-01-03"], [1, 2, 999])
    excluded = replace(
        context,
        spec=replace(
            context.spec,
            method=MethodSpec(
                "detect_anomalies",
                "1.0",
                {
                    **context.spec.method.parameters,
                    "final_period": "partial",
                    "partial_period_policy": "exclude",
                },
            ),
        ),
    )
    result = regular_series(excluded)
    assert result.values.tolist() == [1.0, 2.0]
    assert result.excluded_partial_period == "2026-01-03"

    failed = replace(
        excluded,
        spec=replace(
            excluded.spec,
            method=MethodSpec(
                "detect_anomalies",
                "1.0",
                {
                    **excluded.spec.method.parameters,
                    "partial_period_policy": "fail",
                },
            ),
        ),
    )
    with pytest.raises(AnalysisWithheld) as exc_info:
        regular_series(failed)
    assert exc_info.value.blockers[0].code == "STAT_PARTIAL_PERIOD"
