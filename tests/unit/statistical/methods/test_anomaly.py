"""Oracle and leakage tests for robust anomaly evidence."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import numpy as np
import pytest
from statsmodels.tsa.seasonal import STL
from test_time_index import time_context

from seshat.statistical.contracts import AnalysisWithheld, MethodSpec
from seshat.statistical.methods.anomaly import (
    run_detect_anomalies,
    seasonal_components,
)

pytestmark = pytest.mark.statistics


def _anomaly_context(
    values,
    *,
    model="trailing_mad",
    period=6,
    threshold="3.5",
    direction="two-sided",
):
    start = date(2026, 1, 1)
    timestamps = [
        (start + timedelta(days=index)).isoformat() for index in range(len(values))
    ]
    context = time_context(timestamps, values, period=period)
    return replace(
        context,
        spec=replace(
            context.spec,
            method=MethodSpec(
                "detect_anomalies",
                "1.0",
                {
                    "model": model,
                    "period": period,
                    "threshold": threshold,
                    "direction": direction,
                },
            ),
        ),
    )


def _value(result, name: str) -> str:
    return next(item.value for item in result.estimates if item.name == name)


def test_trailing_mad_detects_spike_without_self_baseline() -> None:
    values = [9, 11, 10, 12, 8, 10, 9, 11, 10, 50, 9, 10]
    result = run_detect_anomalies(_anomaly_context(values))
    key = "2026-01-10"
    assert _value(result, f"anomaly:{key}") == "1"
    assert _value(result, f"baseline_source_end:{key}") == "8"
    assert _value(result, f"evaluated_index:{key}") == "9"


def test_seasonal_components_match_direct_robust_stl() -> None:
    values = np.array(
        [10 + (20 if index % 12 == 11 else 0) + index * 0.1 for index in range(36)]
    )
    expected = STL(values, period=12, robust=True).fit()
    trend, seasonal, residual = seasonal_components(values, 12)
    assert trend == pytest.approx(expected.trend)
    assert seasonal == pytest.approx(expected.seasonal)
    assert residual == pytest.approx(expected.resid)


def test_recurring_seasonal_peak_is_not_anomalous() -> None:
    values = [
        10 + (20 if index % 12 == 11 else 0) + ((index * 7) % 3) * 0.2
        for index in range(37)
    ]
    result = run_detect_anomalies(
        _anomaly_context(values, model="seasonal_mad", period=12, threshold="4")
    )
    assert _value(result, "anomaly:2026-02-05") == "0"


def test_zero_mad_baseline_is_withheld() -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_detect_anomalies(_anomaly_context([10] * 10, period=4))
    assert exc_info.value.blockers[0].code == "STAT_ANOMALY_BASELINE_DEGENERATE"


def test_exact_threshold_is_not_flagged(monkeypatch) -> None:
    import seshat.statistical.methods.anomaly as anomaly

    monkeypatch.setattr(anomaly, "_mad", lambda values: (10.0, 2.0))
    result = run_detect_anomalies(
        _anomaly_context([8, 9, 10, 11, 12, 17], period=5, threshold="3.5")
    )
    assert _value(result, "anomaly:2026-01-06") == "0"


def test_one_sided_rule_only_flags_the_declared_direction() -> None:
    values = [9, 11, 10, 12, 8, 10, 9, 11, 10, -30]
    upper = run_detect_anomalies(_anomaly_context(values, direction="upper"))
    lower = run_detect_anomalies(_anomaly_context(values, direction="lower"))
    assert _value(upper, "anomaly:2026-01-10") == "0"
    assert _value(lower, "anomaly:2026-01-10") == "1"
