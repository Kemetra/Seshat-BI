"""Leak-free robust anomaly evidence for regular governed series."""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass

from ..contracts import (
    Diagnostic,
    Estimate,
    MethodContext,
    MethodResult,
    require,
)
from ..evidence import decimal_text
from .time_index import regular_series, rolling_origins

_MAD_SCALE = 1.4826

# A robust dispersion has to be judged RELATIVE to the magnitude of the values it
# was measured from. An exactly periodic series leaves residuals at float
# round-off (~1e-15 on values of order 10), which clears an absolute epsilon and
# then makes round-off itself decide every flag -- a platform-dependent coin
# toss. Anything at or below this fraction of the baseline's magnitude carries no
# usable signal, so the point is reported as degenerate instead of flagged.
_DISPERSION_RELATIVE_FLOOR = 1e-9


def _is_noise_level(dispersion: float, scale: float) -> bool:
    """Report whether a robust dispersion is indistinguishable from round-off."""

    floor = max(sys.float_info.epsilon, _DISPERSION_RELATIVE_FLOOR * scale)
    return not math.isfinite(dispersion) or dispersion <= floor


def seasonal_components(values, period: int):
    """Return the same robust STL components used by governed seasonal baselines."""

    from statsmodels.tsa.seasonal import STL

    fit = STL(values, period=period, robust=True).fit()
    return fit.trend, fit.seasonal, fit.resid


def _mad(values):
    import numpy as np

    center = float(np.median(values))
    dispersion = float(_MAD_SCALE * np.median(np.abs(values - center)))
    return center, dispersion


@dataclass(frozen=True, slots=True)
class _Baseline:
    """One prior-only baseline and the residual of the point it evaluates."""

    center: float
    dispersion: float
    residual: float
    scale: float
    observed: float


def _trailing_baseline(history, observed: float, period: int) -> _Baseline:
    import numpy as np

    baseline = history[-period:]
    center, dispersion = _mad(baseline)
    return _Baseline(
        center,
        dispersion,
        observed - center,
        float(np.max(np.abs(baseline))),
        observed,
    )


def _seasonal_baseline(history, observed: float, period: int) -> _Baseline | None:
    """Extrapolate one step from the prior-only robust STL decomposition."""

    import numpy as np

    if len(history) < period * 2:
        return None
    trend, seasonal, residuals = seasonal_components(history, period)
    center, dispersion = _mad(residuals)
    trend_step = float(trend[-1] - trend[-2])
    expected = float(trend[-1] + trend_step + seasonal[-period])
    return _Baseline(
        center,
        dispersion,
        observed - expected,
        float(np.max(np.abs(history))),
        observed,
    )


def _is_anomaly(deviation: float, limit: float, direction: str) -> bool:
    if direction == "upper":
        return deviation > limit
    if direction == "lower":
        return deviation < -limit
    return abs(deviation) > limit


def _required_history(context: MethodContext, model: str, period: int) -> int:
    """Return the index of the first point that has a full governed baseline."""

    cycles = max(
        2 if model == "seasonal_mad" else 1,
        context.spec.minimum_data.get("seasonal_cycles", 0),
    )
    return max(period * cycles, context.spec.minimum_data.get("observations", 1))


def _point_estimates(
    key: str, baseline: _Baseline, limit: float, origin
) -> tuple[Estimate, ...]:
    return (
        Estimate(f"observed:{key}", decimal_text(baseline.observed), None),
        Estimate(f"baseline_center:{key}", decimal_text(baseline.center), None),
        Estimate(f"baseline_dispersion:{key}", decimal_text(baseline.dispersion), None),
        Estimate(f"threshold:{key}", decimal_text(limit), None),
        Estimate(f"baseline_source_end:{key}", str(origin.source_end), None),
        Estimate(f"evaluated_index:{key}", str(origin.evaluate_index), None),
    )


def _degenerate(key: str) -> Diagnostic:
    return Diagnostic(
        "STAT_ANOMALY_BASELINE_DEGENERATE",
        "warning",
        key,
        "The prior-only baseline has no robust dispersion above the numerical "
        "noise of its own values.",
    )


def run_detect_anomalies(context: MethodContext) -> MethodResult:
    """Evaluate points only against strictly earlier robust baselines."""

    series = regular_series(context)
    parameters = context.spec.method.parameters
    model = str(parameters["model"])
    multiplier = float(parameters["threshold"])
    direction = str(parameters.get("direction", "two-sided"))
    require(
        math.isfinite(multiplier) and multiplier > 0,
        "STAT_THRESHOLD_INVALID",
        "The anomaly threshold must be finite and positive.",
        "Use a positive governed MAD multiplier.",
    )
    period = series.seasonal_period
    initial = _required_history(context, model, period)
    require(
        initial < len(series.values),
        "STAT_ANOMALY_HISTORY",
        "No observation remains after the required historical baseline.",
        "Provide history plus at least one later evaluation point.",
    )

    estimates: list[Estimate] = []
    diagnostics: list[Diagnostic] = []
    evaluated = 0
    for origin in rolling_origins(len(series.values), initial):
        history = series.values[: origin.evaluate_index]
        observed = float(series.values[origin.evaluate_index])
        key = series.timestamps[origin.evaluate_index]
        baseline = (
            _trailing_baseline(history, observed, period)
            if model == "trailing_mad"
            else _seasonal_baseline(history, observed, period)
        )
        if baseline is None:
            continue
        if _is_noise_level(baseline.dispersion, baseline.scale):
            diagnostics.append(_degenerate(key))
            continue
        limit = multiplier * baseline.dispersion
        flagged = _is_anomaly(baseline.residual - baseline.center, limit, direction)
        estimates.append(Estimate(f"anomaly:{key}", "1" if flagged else "0", None))
        estimates.extend(_point_estimates(key, baseline, limit, origin))
        evaluated += 1
    require(
        evaluated,
        "STAT_ANOMALY_BASELINE_DEGENERATE",
        "No prior-only baseline had robust dispersion above its own numerical noise.",
        "Provide more variable historical observations.",
    )
    diagnostics.append(
        Diagnostic(
            "STAT_ANOMALY_BASELINE",
            "holds",
            str(evaluated),
            "Every evaluated point used a baseline ending at the prior index.",
        )
    )
    return MethodResult(
        estimates=tuple(estimates),
        diagnostics=tuple(diagnostics),
        interpretation_cautions=(
            "Anomaly flags are derived signals for review, not explanations of cause.",
        ),
    )
