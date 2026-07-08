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

    # Per-surviving-column shifts (columns present in BOTH).
    for name in sorted(base_cols.keys() & obs_cols.keys()):
        b = base_cols[name]
        o = obs_cols[name]
        before_missing = f"{b.missing_pct:.2f}%"
        after_missing = f"{o.missing_pct:.2f}%"
        if before_missing != after_missing:
            findings.append(
                DriftFinding(
                    drift_class="missingness_shift",
                    column=name,
                    before=before_missing,
                    after=after_missing,
                    severity="warning",
                    principle_v=False,
                )
            )
        if b.distinct_cardinality != o.distinct_cardinality:
            findings.append(
                DriftFinding(
                    drift_class="cardinality_shift",
                    column=name,
                    before=f"{b.distinct_cardinality} distinct",
                    after=f"{o.distinct_cardinality} distinct",
                    severity="warning",
                    principle_v=False,
                )
            )

    # Grain / PK drift -- a Principle-V human seam. The candidate PK that was
    # unique on the baseline is no longer unique, or NULLs appeared in the PK.
    if baseline.pk.is_unique and (not observed.pk.is_unique or observed.pk.null_pk > 0):
        before = f"is_unique=true, null_pk={baseline.pk.null_pk}"
        after = (
            f"is_unique={str(observed.pk.is_unique).lower()}, "
            f"null_pk={observed.pk.null_pk}"
        )
        findings.append(
            DriftFinding(
                drift_class="grain_pk_drift",
                column="(candidate PK)",
                before=before,
                after=after,
                severity="blocked",
                principle_v=True,
                note="grain is never auto-rejudged; raise for the analyst",
            )
        )
    return findings
