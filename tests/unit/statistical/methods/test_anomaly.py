"""Oracle and leakage tests for robust anomaly evidence."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import date, timedelta

import pytest

# The numerical stack is an optional extra; collection-skip without it so the
# base `.[dev]` suite never fails on an import it is not meant to satisfy.
pytest.importorskip("numpy")
pytest.importorskip("statsmodels")

import numpy as np  # noqa: E402
from statsmodels.tsa.seasonal import STL  # noqa: E402

from seshat.statistical.contracts import AnalysisWithheld, MethodSpec  # noqa: E402
from seshat.statistical.methods.anomaly import (  # noqa: E402
    run_detect_anomalies,
    seasonal_components,
)

from .test_time_index import time_context  # noqa: E402

pytestmark = pytest.mark.statistics


@dataclass(frozen=True, slots=True)
class _AnomalyOptions:
    """The declared anomaly rule one test varies."""

    model: str = "trailing_mad"
    period: int = 6
    threshold: str = "3.5"
    direction: str = "two-sided"


def _anomaly_context(values, **overrides: object):
    options = _AnomalyOptions(**overrides)  # type: ignore[arg-type]
    start = date(2026, 1, 1)
    timestamps = [
        (start + timedelta(days=index)).isoformat() for index in range(len(values))
    ]
    context = time_context(timestamps, values, period=options.period)
    return replace(
        context,
        spec=replace(
            context.spec,
            method=MethodSpec(
                "detect_anomalies",
                "1.0",
                {
                    "model": options.model,
                    "period": options.period,
                    "threshold": options.threshold,
                    "direction": options.direction,
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


def _seasonal_values(count: int, *, jitter: float) -> list[float]:
    """Yearly-style peaks plus jitter whose own period never divides the season.

    ``sin(index * 1.7)`` is deterministic but aperiodic against a 12-point
    season, so robust STL cannot absorb it into the seasonal component. That
    keeps the residual dispersion a real quantity instead of float round-off.
    """

    return [
        10 + (20 if index % 12 == 11 else 0) + jitter * math.sin(index * 1.7)
        for index in range(count)
    ]


def test_recurring_seasonal_peak_is_not_anomalous() -> None:
    # Five whole cycles ending on a peak: index 59 == 2026-03-01.
    values = _seasonal_values(60, jitter=0.4)
    result = run_detect_anomalies(
        _anomaly_context(values, model="seasonal_mad", period=12, threshold="4")
    )
    assert _value(result, "anomaly:2026-03-01") == "0"


def test_numerically_exact_history_is_withheld_not_flagged() -> None:
    # An exactly reproducible series leaves residuals at float round-off. Judging
    # that against an absolute epsilon would let round-off decide each flag, so
    # every baseline must be reported as degenerate instead.
    values = _seasonal_values(60, jitter=0.0)
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_detect_anomalies(
            _anomaly_context(values, model="seasonal_mad", period=12, threshold="4")
        )
    assert exc_info.value.blockers[0].code == "STAT_ANOMALY_BASELINE_DEGENERATE"


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


def test_trailing_baseline_does_not_flag_a_point_at_its_own_center() -> None:
    """A value sitting on its own baseline center is never an anomaly.

    The trailing baseline centers on the RAW values, so its center carries the
    series magnitude. Comparing anything other than `observed - center` against
    the threshold makes the flag depend on how large the values happen to be,
    and a level-100 series then reports every evaluated week as anomalous.
    """

    # Nine quiet weeks around 112, then a tenth point exactly at the center of
    # its own trailing window. Deviation is 0; the threshold is far above it.
    values = [110, 112, 111, 113, 112, 111, 113, 112, 111, 112]
    result = run_detect_anomalies(_anomaly_context(values, period=6))

    assert _value(result, "anomaly:2026-01-10") == "0"


def test_trailing_flags_survive_a_shift_in_series_magnitude() -> None:
    """The same shape flags the same way at level 10 and at level 1000.

    An anomaly rule is scale-relative by construction: it compares a deviation
    against a multiple of the baseline's own robust dispersion. Adding a
    constant to every observation must therefore change nothing.
    """

    shape = [10, 12, 11, 13, 12, 11, 13, 12, 11, 40]
    low = run_detect_anomalies(_anomaly_context(list(shape), period=6))
    high = run_detect_anomalies(
        _anomaly_context([value + 990 for value in shape], period=6)
    )

    key = "anomaly:2026-01-10"
    assert _value(low, key) == "1", "the spike must flag at level 10"
    assert _value(high, key) == _value(low, key), (
        "shifting every value by a constant must not change the verdict"
    )


def test_seasonal_deviation_stays_relative_to_the_residual_center() -> None:
    """The seasonal rule thresholds its residual RELATIVE to the residual center.

    `_seasonal_baseline` centers on the STL residuals, not on the raw values,
    so `observed - expected` is not yet the deviation. When contamination drags
    the residual median off zero, comparing the raw residual shifts both
    two-sided and directional thresholds and flips verdicts near the limit.
    """

    import numpy as np

    from seshat.statistical.methods.anomaly import _is_anomaly, _seasonal_baseline

    # Seed 43 lands the point just outside its centered threshold and just
    # inside the uncentered one, so the two comparisons disagree.
    rng = np.random.default_rng(43)
    values = np.array(
        [
            40
            + 8 * math.sin(2 * math.pi * index / 12)
            + rng.normal(0, 0.8)
            + (rng.uniform(2, 6) if rng.random() < 0.6 else 0.0)
            for index in range(60)
        ]
    )

    baseline = _seasonal_baseline(values[:-1], float(values[-1]), 12)
    assert baseline is not None
    assert baseline.center != 0.0, "this fixture must displace the residual median"

    limit = 3.5 * baseline.dispersion
    assert baseline.deviation == pytest.approx(baseline.residual - baseline.center)
    assert _is_anomaly(baseline.deviation, limit, "two-sided"), (
        "the centered comparison must flag this point"
    )
    assert not _is_anomaly(baseline.residual, limit, "two-sided"), (
        "the uncentered comparison is what this test exists to rule out; if it "
        "stops disagreeing, the fixture no longer exercises the risk"
    )
