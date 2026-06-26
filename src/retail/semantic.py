"""L3 semantic-check core: pair measures with contracts, map Verdicts to Findings.

Stdlib-only at IMPORT time (it does NOT import yaml -- the caller loads contract
definitions and passes them in). Like metric_drift, this module is NEVER imported by
retail.rules; it is used only by the `retail semantic-check` CLI handler.

Verdict -> severity mapping (the gating posture, ADR 0007):
  drift    -> ERROR   (fails the gate)
  escalate -> WARNING (surfaced, does NOT fail the gate -- human review)
  pass     -> None    (silent)
  skip     -> None    (silent; contract has no structured definition yet)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .core import Finding, Severity
from .metric_drift import Verdict, check_measure_drift

__all__ = ["MeasurePair", "verdict_to_finding", "run_semantic_pairs"]

# Stable tag for L3 findings (NOT a registered rule id -- see ADR 0007).
_L3_TAG = "L3"


@dataclass(frozen=True)
class MeasurePair:
    """One measure paired with its contract definition.

    name:       measure name (== contract `name` == YAML stem).
    dax:        the measure's DAX expression (from TMDL).
    locator:    repo-relative POSIX `path:line` of the measure.
    definition: the contract's `definition` block, or None (-> skip).
    """

    name: str
    dax: str
    locator: str
    definition: dict | None


def verdict_to_finding(
    measure_name: str, locator: str, verdict: Verdict
) -> Finding | None:
    """Map a Verdict to a Finding, or None for pass/skip (no finding)."""
    if verdict.status == "drift":
        severity = Severity.ERROR
    elif verdict.status == "escalate":
        severity = Severity.WARNING
    else:  # pass | skip
        return None
    return Finding(
        rule_id=_L3_TAG,
        severity=severity,
        message=f"measure '{measure_name}': {verdict.detail}",
        locator=locator,
    )


def run_semantic_pairs(pairs: Iterable[MeasurePair]) -> tuple[list[Finding], int]:
    """Run the drift check over every pair; return (findings, exit_code).

    exit_code is 1 iff any ERROR finding (a drift), else 0. escalate/WARNING never
    fails the gate.
    """
    findings: list[Finding] = []
    for pair in pairs:
        verdict = check_measure_drift(pair.dax, pair.definition)
        finding = verdict_to_finding(pair.name, pair.locator, verdict)
        if finding is not None:
            findings.append(finding)
    exit_code = 1 if any(f.severity is Severity.ERROR for f in findings) else 0
    return findings, exit_code
