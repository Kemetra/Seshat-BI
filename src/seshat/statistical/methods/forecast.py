"""Governed forecasting with mandatory baselines and rolling-origin evidence."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Literal

from ..contracts import (
    AnalysisWithheld,
    Blocker,
    Diagnostic,
    Estimate,
    Interval,
    MethodContext,
    MethodResult,
)
from ..evidence import decimal_text
from .common import unit_for_role
from .time_index import regular_series


@dataclass(frozen=True, slots=True)
class ForecastCandidate:
    candidate_id: str
    trend: Literal["add", "none"]
    damped: bool
    seasonal: Literal["add", "none"]
    period: int


@dataclass(frozen=True, slots=True)
class BacktestFold:
    cutoff_index: int
    horizon: int
    actual: tuple[str, ...]
    predicted: tuple[str, ...]
    mase: str | None
    smape: str | None


@dataclass(frozen=True, slots=True)
class ForecastEvaluation:
    candidate_id: str
    folds: tuple[BacktestFold, ...]
    mean_mase: str | None
    mean_smape: str | None
    diagnostics: tuple[Diagnostic, ...]
    failure: str | None


@dataclass(frozen=True, slots=True)
class ForecastOutput:
    point: object
    low: object
    high: object
    residuals: object
    interval_method: str


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return AnalysisWithheld((Blocker(code, message, recovery),))


def naive(values, horizon: int):
    import numpy as np

    return np.repeat(float(values[-1]), horizon)


def seasonal_naive(values, period: int, horizon: int):
    import numpy as np

    if period < 1 or len(values) < period:
        raise ValueError("seasonal naive requires one complete cycle")
    cycle = np.asarray(values[-period:], dtype=float)
    return np.resize(cycle, horizon)


def mase(actual, predicted, training, period: int = 1) -> float | None:
    import numpy as np

    actual_array = np.asarray(actual, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    training_array = np.asarray(training, dtype=float)
    lag = period if period > 1 else 1
    if len(training_array) <= lag:
        return None
    denominator = float(np.mean(np.abs(training_array[lag:] - training_array[:-lag])))
    if not math.isfinite(denominator) or denominator <= np.finfo(float).eps:
        return None
    return float(np.mean(np.abs(actual_array - predicted_array)) / denominator)


def smape(actual, predicted) -> float:
    import numpy as np

    actual_array = np.asarray(actual, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    denominator = np.abs(actual_array) + np.abs(predicted_array)
    terms = np.divide(
        2.0 * np.abs(actual_array - predicted_array),
        denominator,
        out=np.zeros_like(denominator),
        where=denominator > 0,
    )
    return float(np.mean(terms) * 100.0)


def candidate_from_id(candidate_id: str, period: int) -> ForecastCandidate:
    catalog = {
        "naive": ForecastCandidate("naive", "none", False, "none", period),
        "seasonal_naive": ForecastCandidate(
            "seasonal_naive", "none", False, "add", period
        ),
        "ets_add": ForecastCandidate("ets_add", "none", False, "none", period),
        "ets_add_trend": ForecastCandidate(
            "ets_add_trend", "add", False, "none", period
        ),
        "ets_add_damped": ForecastCandidate(
            "ets_add_damped", "add", True, "none", period
        ),
        "ets_add_seasonal": ForecastCandidate(
            "ets_add_seasonal", "none", False, "add", period
        ),
    }
    try:
        return catalog[candidate_id]
    except KeyError:
        raise ValueError(
            f"unknown governed forecast candidate: {candidate_id}"
        ) from None


def _normal_interval(point, residuals, level: float):
    import numpy as np

    residual_array = np.asarray(residuals, dtype=float)
    scale = float(np.std(residual_array, ddof=1)) if len(residual_array) > 1 else 0
    if not math.isfinite(scale) or scale <= np.finfo(float).eps:
        point_array = np.asarray(point, dtype=float)
        return point_array.copy(), point_array.copy()
    critical = NormalDist().inv_cdf(0.5 + level / 2.0)
    point_array = np.asarray(point, dtype=float)
    spread = critical * scale * np.sqrt(np.arange(1, len(point_array) + 1))
    return point_array - spread, point_array + spread


def fit_candidate(
    training,
    candidate: ForecastCandidate,
    horizon: int,
    level: float = 0.95,
) -> ForecastOutput:
    """Fit one closed candidate to only the supplied training history."""

    import numpy as np

    values = np.asarray(training, dtype=float)
    if candidate.candidate_id == "naive":
        point = naive(values, horizon)
        residuals = np.diff(values)
        low, high = _normal_interval(point, residuals, level)
        return ForecastOutput(point, low, high, residuals, "normal-naive-residual")
    if candidate.candidate_id == "seasonal_naive":
        point = seasonal_naive(values, candidate.period, horizon)
        residuals = values[candidate.period :] - values[: -candidate.period]
        low, high = _normal_interval(point, residuals, level)
        return ForecastOutput(point, low, high, residuals, "normal-seasonal-residual")

    from statsmodels.tsa.statespace.exponential_smoothing import (
        ExponentialSmoothing,
    )

    seasonal = (
        candidate.period
        if candidate.seasonal == "add" and candidate.candidate_id != "seasonal_naive"
        else None
    )
    model = ExponentialSmoothing(
        values,
        trend=candidate.trend == "add",
        damped_trend=candidate.damped,
        seasonal=seasonal,
        initialization_method="estimated",
    )
    fitted = model.fit(disp=False)
    prediction = fitted.get_forecast(horizon)
    point = np.asarray(prediction.predicted_mean, dtype=float)
    confidence = np.asarray(prediction.conf_int(alpha=1.0 - level), dtype=float)
    residuals = np.asarray(fitted.resid, dtype=float)
    return ForecastOutput(
        point,
        confidence[:, 0],
        confidence[:, 1],
        residuals,
        "statsmodels-state-space",
    )


def _cutoffs(
    length: int,
    initial_window: int,
    horizon: int,
    step: int,
    max_folds: int,
) -> tuple[int, ...]:
    cutoffs = tuple(range(initial_window, length - horizon + 1, step))
    return cutoffs[-max_folds:]


def evaluate_candidate(
    values,
    candidate: ForecastCandidate,
    *,
    horizon: int,
    initial_window: int,
    step: int,
    max_folds: int,
) -> ForecastEvaluation:
    """Evaluate a candidate on deterministic prior-only rolling origins."""

    import numpy as np

    array = np.asarray(values, dtype=float)
    folds: list[BacktestFold] = []
    diagnostics: list[Diagnostic] = []
    try:
        for cutoff in _cutoffs(len(array), initial_window, horizon, step, max_folds):
            training = array[:cutoff]
            actual = array[cutoff : cutoff + horizon]
            output = fit_candidate(training, candidate, horizon)
            fold_mase = mase(actual, output.point, training, candidate.period)
            fold_smape = smape(actual, output.point)
            folds.append(
                BacktestFold(
                    cutoff,
                    horizon,
                    tuple(decimal_text(value) for value in actual),
                    tuple(decimal_text(value) for value in output.point),
                    None if fold_mase is None else decimal_text(fold_mase),
                    decimal_text(fold_smape),
                )
            )
    except (ArithmeticError, RuntimeError, ValueError) as exc:
        return ForecastEvaluation(
            candidate.candidate_id,
            tuple(folds),
            None,
            None,
            tuple(diagnostics),
            str(exc),
        )
    mase_values = [float(item.mase) for item in folds if item.mase is not None]
    smape_values = [float(item.smape) for item in folds if item.smape is not None]
    if len(mase_values) != len(folds):
        diagnostics.append(
            Diagnostic(
                "STAT_FORECAST_MASE_UNDEFINED",
                "warning",
                str(len(folds) - len(mase_values)),
                "MASE is undefined where the training scale is zero.",
            )
        )
    return ForecastEvaluation(
        candidate.candidate_id,
        tuple(folds),
        decimal_text(np.mean(mase_values)) if mase_values else None,
        decimal_text(np.mean(smape_values)) if smape_values else None,
        tuple(diagnostics),
        None,
    )


def _residual_diagnostic(residuals, period: int) -> Diagnostic:
    from statsmodels.stats.diagnostic import acorr_ljungbox

    lag = max(1, min(period, len(residuals) // 5))
    result = acorr_ljungbox(residuals, lags=[lag], return_df=False)
    if hasattr(result, "iloc"):
        p_value = float(result.iloc[0]["lb_pvalue"])
    else:
        p_value = float(result[1][0])
    return Diagnostic(
        "STAT_FORECAST_RESIDUAL_AUTOCORRELATION",
        "warning" if p_value < 0.05 else "holds",
        decimal_text(p_value),
        f"Ljung-Box residual autocorrelation p-value at lag {lag}.",
    )


def run_forecast(context: MethodContext) -> MethodResult:
    """Backtest declared candidates, select stably, then fit the full history."""

    import numpy as np

    series = regular_series(context)
    parameters = context.spec.method.parameters
    period = int(parameters["period"])
    horizon = int(parameters["horizon"])
    level = float(parameters["confidence_level"])
    metric = str(parameters["evaluation_metric"])
    initial_window = int(parameters["initial_window"])
    step = int(parameters["step"])
    max_folds = int(parameters["max_folds"])
    candidate_ids = tuple(str(item) for item in parameters["candidates"])
    baseline = "seasonal_naive" if period > 1 else "naive"
    if baseline not in candidate_ids:
        raise _withheld(
            "STAT_FORECAST_BASELINE",
            f"The declared candidates omit the mandatory {baseline} baseline.",
            "Add the governed baseline to the candidate list.",
        )
    cutoffs = _cutoffs(len(series.values), initial_window, horizon, step, max_folds)
    if len(cutoffs) < 2:
        raise _withheld(
            "STAT_FORECAST_FOLDS",
            "Fewer than two complete rolling-origin folds are available.",
            "Provide more history or revise the approved evaluation windows.",
        )
    estimated_evidence_items = (
        len(candidate_ids) * (2 + len(cutoffs) * (3 + 2 * horizon)) + horizon
    )
    if estimated_evidence_items > 9_500:
        raise _withheld(
            "STAT_FORECAST_EVIDENCE_LIMIT",
            "The declared folds, horizon, and candidates exceed the evidence ceiling.",
            "Reduce max_folds, horizon, or the candidate count.",
        )
    candidates = tuple(candidate_from_id(item, period) for item in candidate_ids)
    evaluations = tuple(
        evaluate_candidate(
            series.values,
            candidate,
            horizon=horizon,
            initial_window=initial_window,
            step=step,
            max_folds=max_folds,
        )
        for candidate in candidates
    )
    diagnostics: list[Diagnostic] = []
    estimates: list[Estimate] = []
    ranked: list[tuple[float, int, ForecastEvaluation]] = []
    for order, evaluation in enumerate(evaluations):
        diagnostics.extend(evaluation.diagnostics)
        if evaluation.failure is not None:
            diagnostics.append(
                Diagnostic(
                    "STAT_FORECAST_CANDIDATE_FAILED",
                    "warning",
                    evaluation.candidate_id,
                    evaluation.failure,
                )
            )
            continue
        value = evaluation.mean_mase if metric == "mase" else evaluation.mean_smape
        if value is not None:
            ranked.append((float(value), order, evaluation))
        if evaluation.mean_mase is not None:
            estimates.append(
                Estimate(
                    f"backtest_mean_mase:{evaluation.candidate_id}",
                    evaluation.mean_mase,
                    None,
                )
            )
        if evaluation.mean_smape is not None:
            estimates.append(
                Estimate(
                    f"backtest_mean_smape:{evaluation.candidate_id}",
                    evaluation.mean_smape,
                    None,
                )
            )
        for fold_index, fold in enumerate(evaluation.folds, start=1):
            prefix = f"{evaluation.candidate_id}:{fold_index}"
            estimates.extend(
                (
                    Estimate(
                        f"fold_cutoff:{prefix}",
                        str(fold.cutoff_index),
                        None,
                    ),
                    Estimate(f"fold_mase:{prefix}", fold.mase, None),
                    Estimate(f"fold_smape:{prefix}", fold.smape, None),
                )
            )
            for point_index, (actual, predicted) in enumerate(
                zip(fold.actual, fold.predicted, strict=True), start=1
            ):
                estimates.extend(
                    (
                        Estimate(
                            f"fold_actual:{prefix}:{point_index}",
                            actual,
                            unit_for_role(context, "response"),
                        ),
                        Estimate(
                            f"fold_predicted:{prefix}:{point_index}",
                            predicted,
                            unit_for_role(context, "response"),
                        ),
                    )
                )
    if not ranked:
        raise _withheld(
            "STAT_FORECAST_ALL_FAILED",
            "No declared candidate produced the selected backtest metric.",
            "Review candidate failures, history, and the evaluation metric.",
        )
    ranked.sort(key=lambda item: (item[0], item[1]))
    _, selected_order, selected_evaluation = ranked[0]
    baseline_evaluation = next(
        item for item in evaluations if item.candidate_id == baseline
    )
    baseline_value = (
        baseline_evaluation.mean_mase
        if metric == "mase"
        else baseline_evaluation.mean_smape
    )
    selected_value = (
        selected_evaluation.mean_mase
        if metric == "mase"
        else selected_evaluation.mean_smape
    )
    if baseline_value is None:
        raise _withheld(
            "STAT_FORECAST_BASELINE_FAILED",
            "The mandatory baseline did not produce the selected metric.",
            "Provide history with a non-degenerate baseline scale.",
        )
    if selected_evaluation.candidate_id == baseline or float(selected_value) >= float(
        baseline_value
    ):
        diagnostics.append(
            Diagnostic(
                "STAT_FORECAST_BASELINE_NOT_BEATEN",
                "warning",
                baseline,
                "No declared alternative beat the governed baseline; no model "
                "endorsement is warranted.",
            )
        )
    selected_candidate = candidates[selected_order]
    try:
        output = fit_candidate(series.values, selected_candidate, horizon, level)
    except (ArithmeticError, RuntimeError, ValueError) as exc:
        raise _withheld(
            "STAT_FORECAST_FINAL_FIT",
            "The selected candidate failed on the full permitted history.",
            "Review the candidate diagnostics and approved history.",
        ) from exc
    if np.max(np.abs(output.high - output.low)) <= np.finfo(float).eps:
        raise _withheld(
            "STAT_FORECAST_INTERVAL_DEGENERATE",
            "The selected forecast has zero residual uncertainty.",
            "Provide more variable approved history for uncertainty estimation.",
        )
    diagnostics.extend(
        (
            Diagnostic(
                "STAT_FORECAST_SELECTED",
                "holds",
                selected_candidate.candidate_id,
                f"Selected by lowest declared mean {metric} with stable tie order.",
            ),
            _residual_diagnostic(output.residuals, period),
        )
    )
    for index, (point, low, high) in enumerate(
        zip(output.point, output.low, output.high, strict=True), start=1
    ):
        estimates.append(
            Estimate(
                f"forecast:{index}",
                decimal_text(point),
                unit_for_role(context, "response"),
            )
        )
    intervals = tuple(
        Interval(
            f"forecast:{index}",
            decimal_text(low),
            decimal_text(high),
            decimal_text(level),
            output.interval_method,
        )
        for index, (low, high) in enumerate(
            zip(output.low, output.high, strict=True), start=1
        )
    )
    return MethodResult(
        estimates=tuple(estimates),
        intervals=intervals,
        diagnostics=tuple(diagnostics),
        interpretation_cautions=(
            "Forecasts are derived scenarios with uncertainty, not guarantees.",
        ),
    )
