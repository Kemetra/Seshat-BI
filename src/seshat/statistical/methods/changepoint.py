"""Governed offline change-point detection through a closed ruptures adapter."""

from __future__ import annotations

import importlib
import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from ..contracts import (
    AnalysisWithheld,
    Diagnostic,
    Estimate,
    MethodContext,
    MethodResult,
    require,
    withheld,
)
from ..evidence import decimal_text
from .time_index import RegularSeries, regular_series

_MAX_COMPLEXITY = 2_000_000


@dataclass(frozen=True, slots=True)
class _Search:
    """The declared search rule, read once from the approved parameters."""

    model: str
    min_segment: int
    algorithm: str
    jump: int
    change_count: int
    penalty: float

    @property
    def penalized(self) -> bool:
        return self.algorithm == "pelt"


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return withheld(code, message, recovery)


def _ruptures():
    return importlib.import_module("ruptures")


def _search_rule(parameters: Mapping[str, object]) -> _Search:
    return _Search(
        model=str(parameters["model"]),
        min_segment=int(parameters["min_segment"]),
        algorithm=str(parameters.get("algorithm", "pelt")),
        jump=int(parameters.get("jump", 1)),
        change_count=int(parameters.get("change_count", 1)),
        penalty=float(parameters.get("penalty", "1")),
    )


def _assert_searchable(search: _Search, count: int) -> None:
    """Hold every resource and segment-size rule before any search runs."""

    penalty_valid = math.isfinite(search.penalty) and search.penalty > 0
    require(
        not search.penalized or penalty_valid,
        "STAT_CHANGEPOINT_PENALTY",
        "The change-point penalty must be finite and positive.",
        "Use a positive governed penalty.",
    )
    require(
        count >= 2 * search.min_segment,
        "STAT_CHANGEPOINT_HISTORY",
        "The series cannot form two segments at the declared minimum size.",
        "Provide more contiguous history or revise the approved segment floor.",
    )
    complexity = count * (search.change_count + 1)
    require(
        search.algorithm != "dynamic_programming" or complexity <= _MAX_COMPLEXITY,
        "STAT_CHANGEPOINT_COMPLEXITY",
        "The fixed-count candidate search exceeds the governed resource ceiling.",
        "Reduce the series length or approved change count.",
    )
    require(
        search.change_count * search.min_segment < count,
        "STAT_CHANGEPOINT_HISTORY",
        "The requested change count cannot satisfy the minimum segment size.",
        "Reduce the approved change count or provide more history.",
    )


def _predict(ruptures, search: _Search, values):
    """Run exactly the declared algorithm; an unknown one is a KeyError."""

    if search.algorithm == "pelt":
        estimator = ruptures.Pelt(
            model=search.model, min_size=search.min_segment, jump=search.jump
        )
        return estimator.fit(values).predict(pen=search.penalty)
    if search.algorithm == "dynamic_programming":
        estimator = ruptures.Dynp(
            model=search.model, min_size=search.min_segment, jump=search.jump
        )
        return estimator.fit(values).predict(n_bkps=search.change_count)
    raise KeyError(search.algorithm)


def _breakpoints(ruptures, search: _Search, values) -> tuple[int, ...]:
    try:
        predicted = _predict(ruptures, search, values)
    except (KeyError, ValueError, RuntimeError) as exc:
        raise _withheld(
            "STAT_CHANGEPOINT_UNIDENTIFIED",
            "The declared change-point search could not identify valid segments.",
            "Review the model, penalty/count, and minimum segment decision.",
        ) from exc
    return tuple(int(index) for index in predicted if 0 < int(index) < len(values))


def _search_estimates(search: _Search, breakpoints: Sequence[int]) -> list[Estimate]:
    rule = (
        Estimate("penalty", decimal_text(search.penalty), None)
        if search.penalized
        else Estimate("change_count", str(search.change_count), None)
    )
    return [
        Estimate("breakpoint_count", str(len(breakpoints)), None),
        Estimate("minimum_segment", str(search.min_segment), None),
        Estimate("jump", str(search.jump), None),
        rule,
        *(
            Estimate(f"breakpoint_index:{sequence}", str(index), None)
            for sequence, index in enumerate(breakpoints, start=1)
        ),
    ]


def _candidate_diagnostics(
    series: RegularSeries, breakpoints: Sequence[int]
) -> list[Diagnostic]:
    if not breakpoints:
        return [
            Diagnostic(
                "STAT_NO_CHANGEPOINT",
                "holds",
                "0",
                "No candidate regime boundary met the declared search rule.",
            )
        ]
    return [
        Diagnostic(
            "STAT_CANDIDATE_REGIME_CHANGE",
            "warning",
            series.timestamps[index],
            (
                f"Candidate regime boundary {sequence} occurs before index "
                f"{index}; review is required."
            ),
        )
        for sequence, index in enumerate(breakpoints, start=1)
    ]


def run_detect_change_points(context: MethodContext) -> MethodResult:
    """Detect candidate regime boundaries without assigning an event cause."""

    series = regular_series(context)
    search = _search_rule(context.spec.method.parameters)
    _assert_searchable(search, len(series.values))
    ruptures = _ruptures()
    breakpoints = _breakpoints(ruptures, search, series.values)
    engine = Diagnostic(
        "STAT_CHANGEPOINT_ENGINE",
        "holds",
        getattr(ruptures, "__version__", "unknown"),
        f"{search.algorithm} with {search.model} cost completed.",
    )
    return MethodResult(
        estimates=tuple(_search_estimates(search, breakpoints)),
        diagnostics=(engine, *_candidate_diagnostics(series, breakpoints)),
        interpretation_cautions=(
            "Candidate regime changes require review and do not identify event cause.",
        ),
    )
