"""F014 source-drift detector runtime -- the pure comparator.

Diffs a baseline ProfileResult against an observed re-profile (or None when
the live boundary is absent), classifies each difference into the nine drift
classes of docs/readiness/source-drift.md, derives the Source-Ready status,
and emits the schemas/source-drift-findings.schema.json shape.

PURE + I/O-FREE: no DB, no filesystem, no CLI. Depends only on retail.profile's
frozen dataclasses. Never emits a numeric drift score (hard rule #9). Never
re-decides a Principle-V class (grain/PK, returns, PII, identity) -- it measures,
classifies, and raises a handoff for a named owner.
"""

from __future__ import annotations

from dataclasses import dataclass

from .profile import ProfileResult


@dataclass(frozen=True)
class DriftFinding:
    drift_class: str
    column: str
    before: str
    after: str
    severity: str  # "warning" | "blocked"
    principle_v: bool
    note: str | None = None


@dataclass(frozen=True)
class HandoffQuestion:
    question: str
    drift_class: str
    measured_fact: str
    owner: str


def classify_drift(
    baseline: ProfileResult, observed: ProfileResult | None
) -> list[DriftFinding]:
    """Classify the differences between baseline and observed into drift findings.

    observed=None is the deferred-live case: no comparison is possible, so NO
    findings are fabricated (the caller maps this to pending_live_reprofile).
    """
    if observed is None:
        return []

    findings: list[DriftFinding] = []
    base_cols = {c.name: c for c in baseline.columns}
    obs_cols = {c.name: c for c in observed.columns}

    for name in sorted(obs_cols.keys() - base_cols.keys()):
        findings.append(
            DriftFinding(
                drift_class="column_added",
                column=name,
                before="absent",
                after="present",
                severity="warning",
                principle_v=False,
                note="not yet mapped; review for adoption",
            )
        )
    for name in sorted(base_cols.keys() - obs_cols.keys()):
        findings.append(
            DriftFinding(
                drift_class="column_removed",
                column=name,
                before="present",
                after="absent",
                severity="blocked",
                principle_v=False,
                note="any mapping/silver reference is now broken",
            )
        )
    return findings
