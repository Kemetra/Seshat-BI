"""Distinct exit codes: 'blindness aborted' must never read as 'kit regressed'."""

from __future__ import annotations

from enum import IntEnum


class Exit(IntEnum):
    OK = 0
    HARNESS_ERROR = 1
    BLINDNESS_ABORT = 2
    FINDINGS = 3
    METRIC_OUT_OF_BAND = 4
    PARTIAL = 5
    FIXTURE_FAILED = 6


def classify(
    *,
    aborted_blindness: bool,
    fixture_failed: bool,
    harness_error: bool,
    partial: bool,
    confirmed_findings: int,
    metric_out_of_band: bool,
) -> Exit:
    """Highest-precedence condition wins; a partial run is never OK."""
    if fixture_failed:
        return Exit.FIXTURE_FAILED
    if aborted_blindness:
        return Exit.BLINDNESS_ABORT
    if harness_error:
        return Exit.HARNESS_ERROR
    if confirmed_findings > 0:
        return Exit.FINDINGS
    if partial:
        return Exit.PARTIAL
    if metric_out_of_band:
        return Exit.METRIC_OUT_OF_BAND
    return Exit.OK
