"""Distinct exit codes: 'blindness aborted' must never read as 'kit regressed'."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Exit(IntEnum):
    OK = 0
    HARNESS_ERROR = 1
    BLINDNESS_ABORT = 2
    FINDINGS = 3
    METRIC_OUT_OF_BAND = 4
    PARTIAL = 5
    FIXTURE_FAILED = 6


@dataclass(frozen=True)
class RunOutcome:
    """Everything that decides an invocation's exit code."""

    aborted_blindness: bool = False
    fixture_failed: bool = False
    harness_error: bool = False
    partial: bool = False
    confirmed_findings: int = 0
    metric_out_of_band: bool = False


def classify(outcome: RunOutcome) -> Exit:
    """Highest-precedence condition wins; a partial run is never OK."""
    ranked = (
        (outcome.fixture_failed, Exit.FIXTURE_FAILED),
        (outcome.aborted_blindness, Exit.BLINDNESS_ABORT),
        (outcome.harness_error, Exit.HARNESS_ERROR),
        (outcome.confirmed_findings > 0, Exit.FINDINGS),
        (outcome.partial, Exit.PARTIAL),
        (outcome.metric_out_of_band, Exit.METRIC_OUT_OF_BAND),
    )
    return next((code for triggered, code in ranked if triggered), Exit.OK)
