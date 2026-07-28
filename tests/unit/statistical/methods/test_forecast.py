"""Metric, oracle, leakage, and governance tests for forecasting."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import numpy as np
import pytest

from seshat.statistical.contracts import AnalysisWithheld, MethodSpec
from seshat.statistical.methods.forecast import (
    candidate_from_id,
    evaluate_candidate,
    fit_candidate,
    mase,
    naive,
    run_forecast,
    seasonal_naive,
    smape,
)

from .test_time_index import time_context

pytestmark = pytest.mark.statistics


def _context(
    values,
    *,
    candidates=("seasonal_naive", "ets_add_seasonal"),
    period=4,
    horizon=2,
    initial_window=12,
    step=2,
    max_folds=4,
    metric="mase",
):
    start = date(2024, 1, 1)
    timestamps = [
        (start + timedelta(days=index)).isoformat() for index in range(len(values))
    ]
    context = time_context(timestamps, values, period=period, cycles=2)
    return replace(
        context,
        spec=replace(
            context.spec,
            minimum_data={"observations": 8, "groups": 1, "seasonal_cycles": 2},
            method=MethodSpec(
                "forecast",
                "1.0",
                {
                    "candidates": candidates,
                    "period": period,
                    "horizon": horizon,
                    "confidence_level": "0.95",
                    "evaluation_metric": metric,
                    "initial_window": initial_window,
                    "step": step,
                    "max_folds": max_folds,
                    "final_period": "complete",
                    "partial_period_policy": "fail",
                },
            ),
        ),
    )


def test_metrics_and_baselines_match_hand_calculation() -> None:
    actual = np.array([2.0, 4.0])
    predicted = np.array([1.0, 5.0])
    training = np.array([1.0, 2.0, 4.0])
    assert mase(actual, predicted, training) == pytest.approx(2 / 3)
    expected_smape = ((2 / 3) + (2 / 9)) / 2 * 100
    assert smape(actual, predicted) == pytest.approx(expected_smape)
    assert smape([0, 0], [0, 0]) == 0
    assert naive(np.arange(1.0, 5.0), 3).tolist() == [4.0, 4.0, 4.0]
    assert seasonal_naive(np.arange(1.0, 25.0), 12, 3).tolist() == [
        13.0,
        14.0,
        15.0,
    ]


def test_evaluation_never_passes_future_values_to_fit(monkeypatch) -> None:
    import seshat.statistical.methods.forecast as forecast

    seen = []
    original = forecast.fit_candidate

    def recording(training, candidate, horizon, level=0.95):
        seen.append(tuple(training))
        return original(training, candidate, horizon, level)

    monkeypatch.setattr(forecast, "fit_candidate", recording)
    values = np.arange(1.0, 21.0)
    result = evaluate_candidate(
        values,
        candidate_from_id("seasonal_naive", 4),
        horizon=2,
        initial_window=10,
        step=3,
        max_folds=3,
    )
    assert [len(item) for item in seen] == [fold.cutoff_index for fold in result.folds]
    assert all(item == tuple(values[: len(item)]) for item in seen)


@pytest.mark.parametrize(
    "candidate_id",
    ("ets_add", "ets_add_trend", "ets_add_damped", "ets_add_seasonal"),
)
def test_state_space_candidate_matches_direct_statsmodels(candidate_id) -> None:
    from statsmodels.tsa.statespace.exponential_smoothing import (
        ExponentialSmoothing,
    )

    values = np.array(
        [10 + index * 0.3 + (index % 4) * 2 for index in range(28)],
        dtype=float,
    )
    candidate = candidate_from_id(candidate_id, 4)
    expected = ExponentialSmoothing(
        values,
        trend=candidate.trend == "add",
        damped_trend=candidate.damped,
        seasonal=4 if candidate.seasonal == "add" else None,
        initialization_method="estimated",
    ).fit(disp=False)
    expected_prediction = expected.get_forecast(3)
    actual = fit_candidate(values, candidate, 3, 0.95)
    assert actual.point == pytest.approx(expected_prediction.predicted_mean)
    assert np.c_[actual.low, actual.high] == pytest.approx(
        expected_prediction.conf_int(alpha=0.05)
    )


def test_run_forecast_records_candidates_folds_intervals_and_selection() -> None:
    values = np.array(
        [10 + (index % 4) * 3 + index * 0.2 for index in range(28)],
        dtype=float,
    )
    result = run_forecast(_context(values))
    assert (
        len([item for item in result.estimates if item.name.startswith("forecast:")])
        == 2
    )
    assert len(result.intervals) == 2
    assert any(item.code == "STAT_FORECAST_SELECTED" for item in result.diagnostics)
    assert any(item.name.startswith("fold_cutoff:") for item in result.estimates)
    assert any(item.name.startswith("fold_actual:") for item in result.estimates)
    assert any(item.name.startswith("fold_predicted:") for item in result.estimates)


def test_mandatory_baseline_and_two_fold_floor_are_enforced() -> None:
    values = np.arange(1.0, 25.0)
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_forecast(_context(values, candidates=("ets_add",)))
    assert exc_info.value.blockers[0].code == "STAT_FORECAST_BASELINE"

    with pytest.raises(AnalysisWithheld) as exc_info:
        run_forecast(_context(values[:14], initial_window=12, horizon=2))
    assert exc_info.value.blockers[0].code == "STAT_FORECAST_FOLDS"


def test_zero_mase_scale_withholds_when_selected_metric_is_mase() -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_forecast(
            _context(
                np.ones(20),
                candidates=("seasonal_naive",),
                initial_window=10,
            )
        )
    assert exc_info.value.blockers[0].code == "STAT_FORECAST_ALL_FAILED"


def test_candidate_failure_remains_visible(monkeypatch) -> None:
    import seshat.statistical.methods.forecast as forecast

    original = forecast.fit_candidate

    def selective(training, candidate, horizon, level=0.95):
        if candidate.candidate_id == "ets_add_seasonal":
            raise ValueError("synthetic candidate failure")
        return original(training, candidate, horizon, level)

    monkeypatch.setattr(forecast, "fit_candidate", selective)
    values = np.array([10 + (index % 4) * 2 + index * 0.1 for index in range(24)])
    result = run_forecast(_context(values))
    failure = next(
        item
        for item in result.diagnostics
        if item.code == "STAT_FORECAST_CANDIDATE_FAILED"
    )
    assert failure.observed == "ets_add_seasonal"
    assert any(
        item.code == "STAT_FORECAST_BASELINE_NOT_BEATEN" for item in result.diagnostics
    )
