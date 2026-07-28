"""Leak-free robust anomaly evidence for regular governed series."""

from __future__ import annotations

import math
import sys

from ..contracts import (
    AnalysisWithheld,
    Blocker,
    Diagnostic,
    Estimate,
    MethodContext,
    MethodResult,
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


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return AnalysisWithheld((Blocker(code, message, recovery),))


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


def run_detect_anomalies(context: MethodContext) -> MethodResult:
    """Evaluate points only against strictly earlier robust baselines."""

    import numpy as np

    series = regular_series(context)
    parameters = context.spec.method.parameters
    model = str(parameters["model"])
    threshold_multiplier = float(parameters["threshold"])
    direction = str(parameters.get("direction", "two-sided"))
    if not math.isfinite(threshold_multiplier) or threshold_multiplier <= 0:
        raise _withheld(
            "STAT_THRESHOLD_INVALID",
            "The anomaly threshold must be finite and positive.",
            "Use a positive governed MAD multiplier.",
        )
    period = series.seasonal_period
    cycles = max(
        2 if model == "seasonal_mad" else 1,
        context.spec.minimum_data.get("seasonal_cycles", 0),
    )
    initial = max(period * cycles, context.spec.minimum_data.get("observations", 1))
    if initial >= len(series.values):
        raise _withheld(
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
        if model == "trailing_mad":
            baseline = history[-period:]
            center, dispersion = _mad(baseline)
            residual = observed - center
            scale = float(np.max(np.abs(baseline)))
        else:
            if len(history) < period * 2:
                continue
            trend, seasonal, residuals = seasonal_components(history, period)
            center, dispersion = _mad(residuals)
            trend_step = float(trend[-1] - trend[-2])
            expected = float(trend[-1] + trend_step + seasonal[-period])
            residual = observed - expected
            scale = float(np.max(np.abs(history)))
        if _is_noise_level(dispersion, scale):
            diagnostics.append(
                Diagnostic(
                    "STAT_ANOMALY_BASELINE_DEGENERATE",
                    "warning",
                    series.timestamps[origin.evaluate_index],
                    "The prior-only baseline has no robust dispersion above the "
                    "numerical noise of its own values.",
                )
            )
            continue
        limit = threshold_multiplier * dispersion
        deviation = residual - center
        if direction == "upper":
            is_anomaly = deviation > limit
        elif direction == "lower":
            is_anomaly = deviation < -limit
        else:
            is_anomaly = abs(deviation) > limit
        key = series.timestamps[origin.evaluate_index]
        estimates.extend(
            (
                Estimate(f"anomaly:{key}", "1" if is_anomaly else "0", None),
                Estimate(f"observed:{key}", decimal_text(observed), None),
                Estimate(f"baseline_center:{key}", decimal_text(center), None),
                Estimate(f"baseline_dispersion:{key}", decimal_text(dispersion), None),
                Estimate(f"threshold:{key}", decimal_text(limit), None),
                Estimate(f"baseline_source_end:{key}", str(origin.source_end), None),
                Estimate(f"evaluated_index:{key}", str(origin.evaluate_index), None),
            )
        )
        evaluated += 1
    if not evaluated:
        raise _withheld(
            "STAT_ANOMALY_BASELINE_DEGENERATE",
            "No prior-only baseline had robust dispersion above its own "
            "numerical noise.",
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
