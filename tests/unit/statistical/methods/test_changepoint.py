"""Oracle and boundary tests for governed offline change-point evidence."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, replace
from datetime import date, timedelta

import pytest

# The numerical stack is an optional extra; collection-skip without it so the
# base `.[dev]` suite never fails on an import it is not meant to satisfy.
pytest.importorskip("numpy")
pytest.importorskip("ruptures")

import numpy as np  # noqa: E402
import ruptures as rpt  # noqa: E402

from seshat.statistical.contracts import AnalysisWithheld, MethodSpec  # noqa: E402
from seshat.statistical.methods.changepoint import (  # noqa: E402
    run_detect_change_points,
)

from .test_time_index import time_context  # noqa: E402

pytestmark = pytest.mark.statistics


@dataclass(frozen=True, slots=True)
class _Search:
    """The declared change-point search rule one test varies."""

    model: str = "l2"
    penalty: str | None = "10"
    min_segment: int = 6
    algorithm: str = "pelt"
    change_count: int = 2
    jump: int = 1


def _context(values, **overrides: object):
    search = _Search(**overrides)  # type: ignore[arg-type]
    start = date(2026, 1, 1)
    timestamps = [
        (start + timedelta(days=index)).isoformat() for index in range(len(values))
    ]
    context = time_context(timestamps, values, period=1)
    parameters: dict[str, object] = {
        "model": search.model,
        "min_segment": search.min_segment,
        "algorithm": search.algorithm,
        "change_count": search.change_count,
        "jump": search.jump,
    }
    if search.penalty is not None:
        parameters["penalty"] = search.penalty
    return replace(
        context,
        spec=replace(
            context.spec,
            minimum_data={"observations": 2, "groups": 1, "seasonal_cycles": 0},
            method=MethodSpec("detect_change_points", "1.0", parameters),
        ),
    )


def _indexes(result) -> tuple[int, ...]:
    return tuple(
        int(item.value)
        for item in result.estimates
        if item.name.startswith("breakpoint_index:")
    )


def test_pelt_matches_direct_ruptures_and_removes_terminal_sentinel() -> None:
    values = np.r_[np.zeros(20), np.ones(20) * 8, np.ones(20) * -3]
    expected = rpt.Pelt(model="l2", min_size=6, jump=1).fit(values).predict(pen=10)
    result = run_detect_change_points(_context(values))
    assert _indexes(result) == tuple(expected[:-1])
    assert len(values) not in _indexes(result)
    assert "event cause" in result.interpretation_cautions[0]


def test_dynamic_programming_matches_direct_ruptures() -> None:
    values = np.r_[np.zeros(18), np.ones(18) * 5, np.ones(18) * -2]
    expected = rpt.Dynp(model="l2", min_size=6, jump=1).fit(values).predict(n_bkps=2)
    result = run_detect_change_points(
        _context(
            values,
            algorithm="dynamic_programming",
            change_count=2,
            penalty=None,
        )
    )
    assert _indexes(result) == tuple(expected[:-1])


def test_no_detected_change_is_explicit() -> None:
    values = np.linspace(0, 0.01, 30)
    result = run_detect_change_points(_context(values, penalty="1000"))
    assert _indexes(result) == ()
    assert result.estimates[0].value == "0"
    assert result.diagnostics[-1].code == "STAT_NO_CHANGEPOINT"


def test_absent_optional_dependency_propagates_as_unavailable(monkeypatch) -> None:
    original = importlib.import_module

    def missing(name):
        if name == "ruptures":
            raise ImportError(name)
        return original(name)

    monkeypatch.setattr(importlib, "import_module", missing)
    with pytest.raises(ImportError, match="ruptures"):
        run_detect_change_points(_context(np.arange(20.0)))


@pytest.mark.parametrize(
    ("kwargs", "size", "code"),
    (
        ({"min_segment": 6}, 10, "STAT_CHANGEPOINT_HISTORY"),
        (
            {"algorithm": "dynamic_programming", "change_count": 100},
            101,
            "STAT_CHANGEPOINT_HISTORY",
        ),
        ({"penalty": "0"}, 20, "STAT_CHANGEPOINT_PENALTY"),
    ),
)
def test_invalid_search_boundaries_are_withheld(kwargs, size, code) -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_detect_change_points(_context(np.arange(float(size)), **kwargs))
    assert exc_info.value.blockers[0].code == code


def test_irregular_time_and_nonfinite_values_are_withheld() -> None:
    context = _context(np.arange(20.0))
    rows = list(context.data.rows)
    rows[4] = ("2026-02-01", rows[4][1])
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_detect_change_points(
            replace(context, data=replace(context.data, rows=tuple(rows)))
        )
    assert exc_info.value.blockers[0].code == "STAT_TIME_IRREGULAR"

    values = np.arange(20.0)
    values[5] = np.inf
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_detect_change_points(_context(values))
    assert exc_info.value.blockers[0].code == "STAT_NON_FINITE_INPUT"
