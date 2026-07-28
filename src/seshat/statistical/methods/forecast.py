"""Governed forecasting with mandatory baselines and rolling-origin evidence."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Literal

from ..contracts import (
    AnalysisWithheld,
    Diagnostic,
    Estimate,
    Interval,
    MethodContext,
    MethodResult,
    require,
    withheld,
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
class BacktestWindows:
    """The declared rolling-origin evaluation geometry."""

    horizon: int
    initial_window: int
    step: int
    max_folds: int


@dataclass(frozen=True, slots=True)
class ForecastOutput:
    point: object
    low: object
    high: object
    residuals: object
    interval_method: str


_MAX_EVIDENCE_ITEMS = 9_500


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return withheld(code, message, recovery)


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


def _cutoffs(length: int, windows: BacktestWindows) -> tuple[int, ...]:
    cutoffs = tuple(
        range(windows.initial_window, length - windows.horizon + 1, windows.step)
    )
    return cutoffs[-windows.max_folds :]


def _fold(
    array, cutoff: int, candidate: ForecastCandidate, horizon: int
) -> BacktestFold:
    """Backtest one origin against strictly earlier training history."""

    training = array[:cutoff]
    actual = array[cutoff : cutoff + horizon]
    output = fit_candidate(training, candidate, horizon)
    fold_mase = mase(actual, output.point, training, candidate.period)
    return BacktestFold(
        cutoff,
        horizon,
        tuple(decimal_text(value) for value in actual),
        tuple(decimal_text(value) for value in output.point),
        None if fold_mase is None else decimal_text(fold_mase),
        decimal_text(smape(actual, output.point)),
    )


def _mean_text(values: list[float]) -> str | None:
    import numpy as np

    return decimal_text(np.mean(values)) if values else None


def evaluate_candidate(
    values, candidate: ForecastCandidate, windows: BacktestWindows
) -> ForecastEvaluation:
    """Evaluate a candidate on deterministic prior-only rolling origins."""

    import numpy as np

    array = np.asarray(values, dtype=float)
    folds: list[BacktestFold] = []
    try:
        for cutoff in _cutoffs(len(array), windows):
            folds.append(_fold(array, cutoff, candidate, windows.horizon))
    except (ArithmeticError, RuntimeError, ValueError) as exc:
        return ForecastEvaluation(
            candidate.candidate_id, tuple(folds), None, None, (), str(exc)
        )
    mase_values = [float(item.mase) for item in folds if item.mase is not None]
    smape_values = [float(item.smape) for item in folds if item.smape is not None]
    diagnostics: tuple[Diagnostic, ...] = ()
    if len(mase_values) != len(folds):
        diagnostics = (
            Diagnostic(
                "STAT_FORECAST_MASE_UNDEFINED",
                "warning",
                str(len(folds) - len(mase_values)),
                "MASE is undefined where the training scale is zero.",
            ),
        )
    return ForecastEvaluation(
        candidate.candidate_id,
        tuple(folds),
        _mean_text(mase_values),
        _mean_text(smape_values),
        diagnostics,
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


@dataclass(frozen=True, slots=True)
class _Plan:
    """Everything the declared forecast parameters fix before any fitting."""

    period: int
    level: float
    metric: str
    windows: BacktestWindows
    candidate_ids: tuple[str, ...]

    @property
    def baseline(self) -> str:
        return "seasonal_naive" if self.period > 1 else "naive"


def _plan(context: MethodContext) -> _Plan:
    parameters = context.spec.method.parameters
    return _Plan(
        period=int(parameters["period"]),
        level=float(parameters["confidence_level"]),
        metric=str(parameters["evaluation_metric"]),
        windows=BacktestWindows(
            horizon=int(parameters["horizon"]),
            initial_window=int(parameters["initial_window"]),
            step=int(parameters["step"]),
            max_folds=int(parameters["max_folds"]),
        ),
        candidate_ids=tuple(str(item) for item in parameters["candidates"]),
    )


def _assert_evaluable(plan: _Plan, cutoffs: tuple[int, ...]) -> None:
    """Hold the baseline, fold-count, and evidence-size rules before fitting."""

    require(
        plan.baseline in plan.candidate_ids,
        "STAT_FORECAST_BASELINE",
        f"The declared candidates omit the mandatory {plan.baseline} baseline.",
        "Add the governed baseline to the candidate list.",
    )
    require(
        len(cutoffs) >= 2,
        "STAT_FORECAST_FOLDS",
        "Fewer than two complete rolling-origin folds are available.",
        "Provide more history or revise the approved evaluation windows.",
    )
    horizon = plan.windows.horizon
    estimated_items = (
        len(plan.candidate_ids) * (2 + len(cutoffs) * (3 + 2 * horizon)) + horizon
    )
    require(
        estimated_items <= _MAX_EVIDENCE_ITEMS,
        "STAT_FORECAST_EVIDENCE_LIMIT",
        "The declared folds, horizon, and candidates exceed the evidence ceiling.",
        "Reduce max_folds, horizon, or the candidate count.",
    )


def _metric_value(evaluation: ForecastEvaluation, metric: str) -> str | None:
    return evaluation.mean_mase if metric == "mase" else evaluation.mean_smape


def _fold_estimates(
    candidate_id: str, folds: tuple[BacktestFold, ...], unit: str | None
) -> list[Estimate]:
    estimates: list[Estimate] = []
    for fold_index, fold in enumerate(folds, start=1):
        prefix = f"{candidate_id}:{fold_index}"
        estimates.extend(
            (
                Estimate(f"fold_cutoff:{prefix}", str(fold.cutoff_index), None),
                Estimate(f"fold_mase:{prefix}", fold.mase, None),
                Estimate(f"fold_smape:{prefix}", fold.smape, None),
            )
        )
        pairs = zip(fold.actual, fold.predicted, strict=True)
        for point_index, (actual, predicted) in enumerate(pairs, start=1):
            estimates.extend(
                (
                    Estimate(f"fold_actual:{prefix}:{point_index}", actual, unit),
                    Estimate(f"fold_predicted:{prefix}:{point_index}", predicted, unit),
                )
            )
    return estimates


def _backtest_estimates(evaluation: ForecastEvaluation, unit: str | None):
    """Report one candidate's mean metrics and every fold it completed."""

    estimates: list[Estimate] = []
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
    estimates.extend(_fold_estimates(evaluation.candidate_id, evaluation.folds, unit))
    return estimates


def _backtest_evidence(
    evaluations: tuple[ForecastEvaluation, ...], plan: _Plan, unit: str | None
):
    """Split the backtest into ranked candidates, estimates, and diagnostics."""

    estimates: list[Estimate] = []
    diagnostics: list[Diagnostic] = []
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
        value = _metric_value(evaluation, plan.metric)
        if value is not None:
            ranked.append((float(value), order, evaluation))
        estimates.extend(_backtest_estimates(evaluation, unit))
    require(
        ranked,
        "STAT_FORECAST_ALL_FAILED",
        "No declared candidate produced the selected backtest metric.",
        "Review candidate failures, history, and the evaluation metric.",
    )
    ranked.sort(key=lambda item: (item[0], item[1]))
    return ranked, estimates, diagnostics


def _baseline_diagnostic(
    evaluations: tuple[ForecastEvaluation, ...],
    selected: ForecastEvaluation,
    plan: _Plan,
) -> tuple[Diagnostic, ...]:
    """Warn unless a declared alternative actually beat the governed baseline."""

    baseline_evaluation = next(
        item for item in evaluations if item.candidate_id == plan.baseline
    )
    baseline_value = _metric_value(baseline_evaluation, plan.metric)
    require(
        baseline_value is not None,
        "STAT_FORECAST_BASELINE_FAILED",
        "The mandatory baseline did not produce the selected metric.",
        "Provide history with a non-degenerate baseline scale.",
    )
    selected_value = _metric_value(selected, plan.metric)
    improved = float(str(selected_value)) < float(str(baseline_value))
    if selected.candidate_id != plan.baseline and improved:
        return ()
    return (
        Diagnostic(
            "STAT_FORECAST_BASELINE_NOT_BEATEN",
            "warning",
            plan.baseline,
            "No declared alternative beat the governed baseline; no model "
            "endorsement is warranted.",
        ),
    )


def _final_output(values, candidate: ForecastCandidate, plan: _Plan) -> ForecastOutput:
    """Fit the selected candidate on the full permitted history."""

    import numpy as np

    try:
        output = fit_candidate(values, candidate, plan.windows.horizon, plan.level)
    except (ArithmeticError, RuntimeError, ValueError) as exc:
        raise _withheld(
            "STAT_FORECAST_FINAL_FIT",
            "The selected candidate failed on the full permitted history.",
            "Review the candidate diagnostics and approved history.",
        ) from exc
    require(
        np.max(np.abs(output.high - output.low)) > np.finfo(float).eps,
        "STAT_FORECAST_INTERVAL_DEGENERATE",
        "The selected forecast has zero residual uncertainty.",
        "Provide more variable approved history for uncertainty estimation.",
    )
    return output


def _forecast_evidence(output: ForecastOutput, plan: _Plan, unit: str | None):
    estimates = [
        Estimate(f"forecast:{index}", decimal_text(point), unit)
        for index, point in enumerate(output.point, start=1)
    ]
    intervals = tuple(
        Interval(
            f"forecast:{index}",
            decimal_text(low),
            decimal_text(high),
            decimal_text(plan.level),
            output.interval_method,
        )
        for index, (low, high) in enumerate(
            zip(output.low, output.high, strict=True), start=1
        )
    )
    return estimates, intervals


def run_forecast(context: MethodContext) -> MethodResult:
    """Backtest declared candidates, select stably, then fit the full history."""

    series = regular_series(context)
    plan = _plan(context)
    _assert_evaluable(plan, _cutoffs(len(series.values), plan.windows))
    unit = unit_for_role(context, "response")
    candidates = tuple(
        candidate_from_id(item, plan.period) for item in plan.candidate_ids
    )
    evaluations = tuple(
        evaluate_candidate(series.values, candidate, plan.windows)
        for candidate in candidates
    )
    ranked, estimates, diagnostics = _backtest_evidence(evaluations, plan, unit)
    _, selected_order, selected_evaluation = ranked[0]
    diagnostics.extend(_baseline_diagnostic(evaluations, selected_evaluation, plan))
    selected_candidate = candidates[selected_order]
    output = _final_output(series.values, selected_candidate, plan)
    diagnostics.extend(
        (
            Diagnostic(
                "STAT_FORECAST_SELECTED",
                "holds",
                selected_candidate.candidate_id,
                (
                    f"Selected by lowest declared mean {plan.metric} with stable "
                    "tie order."
                ),
            ),
            _residual_diagnostic(output.residuals, plan.period),
        )
    )
    forecast_estimates, intervals = _forecast_evidence(output, plan, unit)
    estimates.extend(forecast_estimates)
    return MethodResult(
        estimates=tuple(estimates),
        intervals=intervals,
        diagnostics=tuple(diagnostics),
        interpretation_cautions=(
            "Forecasts are derived scenarios with uncertainty, not guarantees.",
        ),
    )
