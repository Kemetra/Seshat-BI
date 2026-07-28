"""Governed offline change-point detection through a closed ruptures adapter."""

from __future__ import annotations

import importlib
import math

from ..contracts import (
    AnalysisWithheld,
    Blocker,
    Diagnostic,
    Estimate,
    MethodContext,
    MethodResult,
)
from ..evidence import decimal_text
from .time_index import regular_series

_MAX_COMPLEXITY = 2_000_000


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return AnalysisWithheld((Blocker(code, message, recovery),))


def _ruptures():
    return importlib.import_module("ruptures")


def run_detect_change_points(context: MethodContext) -> MethodResult:
    """Detect candidate regime boundaries without assigning an event cause."""

    series = regular_series(context)
    values = series.values
    parameters = context.spec.method.parameters
    model = str(parameters["model"])
    min_segment = int(parameters["min_segment"])
    algorithm = str(parameters.get("algorithm", "pelt"))
    jump = int(parameters.get("jump", 1))
    change_count = int(parameters.get("change_count", 1))
    penalty = float(parameters.get("penalty", "1"))
    if algorithm == "pelt" and (not math.isfinite(penalty) or penalty <= 0):
        raise _withheld(
            "STAT_CHANGEPOINT_PENALTY",
            "The change-point penalty must be finite and positive.",
            "Use a positive governed penalty.",
        )
    if len(values) < 2 * min_segment:
        raise _withheld(
            "STAT_CHANGEPOINT_HISTORY",
            "The series cannot form two segments at the declared minimum size.",
            "Provide more contiguous history or revise the approved segment floor.",
        )
    complexity = len(values) * (change_count + 1)
    if algorithm == "dynamic_programming" and complexity > _MAX_COMPLEXITY:
        raise _withheld(
            "STAT_CHANGEPOINT_COMPLEXITY",
            "The fixed-count candidate search exceeds the governed resource ceiling.",
            "Reduce the series length or approved change count.",
        )
    if change_count * min_segment >= len(values):
        raise _withheld(
            "STAT_CHANGEPOINT_HISTORY",
            "The requested change count cannot satisfy the minimum segment size.",
            "Reduce the approved change count or provide more history.",
        )

    ruptures = _ruptures()
    try:
        if algorithm == "pelt":
            predicted = (
                ruptures.Pelt(model=model, min_size=min_segment, jump=jump)
                .fit(values)
                .predict(pen=penalty)
            )
        elif algorithm == "dynamic_programming":
            predicted = (
                ruptures.Dynp(model=model, min_size=min_segment, jump=jump)
                .fit(values)
                .predict(n_bkps=change_count)
            )
        else:
            raise KeyError(algorithm)
    except (KeyError, ValueError, RuntimeError) as exc:
        raise _withheld(
            "STAT_CHANGEPOINT_UNIDENTIFIED",
            "The declared change-point search could not identify valid segments.",
            "Review the model, penalty/count, and minimum segment decision.",
        ) from exc

    breakpoints = tuple(
        int(index) for index in predicted if 0 < int(index) < len(values)
    )
    estimates: list[Estimate] = [
        Estimate("breakpoint_count", str(len(breakpoints)), None),
        Estimate("minimum_segment", str(min_segment), None),
        Estimate("jump", str(jump), None),
    ]
    if algorithm == "pelt":
        estimates.append(Estimate("penalty", decimal_text(penalty), None))
    else:
        estimates.append(Estimate("change_count", str(change_count), None))
    diagnostics: list[Diagnostic] = [
        Diagnostic(
            "STAT_CHANGEPOINT_ENGINE",
            "holds",
            getattr(ruptures, "__version__", "unknown"),
            f"{algorithm} with {model} cost completed.",
        )
    ]
    for sequence, index in enumerate(breakpoints, start=1):
        estimates.append(Estimate(f"breakpoint_index:{sequence}", str(index), None))
        diagnostics.append(
            Diagnostic(
                "STAT_CANDIDATE_REGIME_CHANGE",
                "warning",
                series.timestamps[index],
                (
                    f"Candidate regime boundary {sequence} occurs before index "
                    f"{index}; review is required."
                ),
            )
        )
    if not breakpoints:
        diagnostics.append(
            Diagnostic(
                "STAT_NO_CHANGEPOINT",
                "holds",
                "0",
                "No candidate regime boundary met the declared search rule.",
            )
        )
    return MethodResult(
        estimates=tuple(estimates),
        diagnostics=tuple(diagnostics),
        interpretation_cautions=(
            "Candidate regime changes require review and do not identify event cause.",
        ),
    )
