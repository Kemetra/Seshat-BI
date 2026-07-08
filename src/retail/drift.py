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


def _column_set_findings(base_cols: dict, obs_cols: dict) -> list[DriftFinding]:
    """Columns added (warning) or removed (blocked). Deterministic (sorted)."""
    findings: list[DriftFinding] = []
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


def _surviving_column_findings(base_cols: dict, obs_cols: dict) -> list[DriftFinding]:
    """Missingness / cardinality shifts on columns present in BOTH. Deterministic."""
    findings: list[DriftFinding] = []
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
    return findings


def _grain_pk_broke(baseline: ProfileResult, observed: ProfileResult) -> bool:
    """The baseline PK was unique but the observed re-profile no longer proves it."""
    return baseline.pk.is_unique and (
        not observed.pk.is_unique or observed.pk.null_pk > 0
    )


def _grain_pk_findings(
    baseline: ProfileResult, observed: ProfileResult
) -> list[DriftFinding]:
    """Grain / PK drift -- a Principle-V human seam, never auto-rejudged."""
    if not _grain_pk_broke(baseline, observed):
        return []
    after = (
        f"is_unique={str(observed.pk.is_unique).lower()}, null_pk={observed.pk.null_pk}"
    )
    return [
        DriftFinding(
            drift_class="grain_pk_drift",
            column="(candidate PK)",
            before=f"is_unique=true, null_pk={baseline.pk.null_pk}",
            after=after,
            severity="blocked",
            principle_v=True,
            note="grain is never auto-rejudged; raise for the analyst",
        )
    ]


def classify_drift(
    baseline: ProfileResult, observed: ProfileResult | None
) -> list[DriftFinding]:
    """Classify the differences between baseline and observed into drift findings.

    observed=None is the deferred-live case: no comparison is possible, so NO
    findings are fabricated (the caller maps this to pending_live_reprofile).
    """
    if observed is None:
        return []
    base_cols = {c.name: c for c in baseline.columns}
    obs_cols = {c.name: c for c in observed.columns}
    return [
        *_column_set_findings(base_cols, obs_cols),
        *_surviving_column_findings(base_cols, obs_cols),
        *_grain_pk_findings(baseline, observed),
    ]


# Scoped to the drift classes classify_drift() actually emits with
# principle_v=True today (grain_pk_drift only). returns_rule_drift,
# pii_surface_drift, and semantic_pair_drift are not yet classified anywhere
# in this module (see classify_drift docstring / TODO in the taxonomy) --
# adding their entries here ahead of that work would be untested, unreachable
# dict entries. Add each class's entry in the SAME task that wires it into
# classify_drift(). Until then, a future principle_v=True finding for an
# unmapped class fails loudly with KeyError in _handoffs() rather than
# silently -- that is the intended safety net, not a bug.
_DEFAULT_OWNER = {
    "grain_pk_drift": "analyst",
}

_HANDOFF_QUESTION = {
    "grain_pk_drift": "is the new grain acceptable, or is dedup a defect?",
}


def derive_status(findings: list[DriftFinding], *, observed_available: bool) -> str:
    """Map findings to one Source-Ready spine status. Never a numeric score."""
    if not observed_available:
        return "pending_live_reprofile"
    if any(f.severity == "blocked" for f in findings):
        return "blocked"
    if findings:
        return "warning"
    return "pass"


def _handoffs(findings: list[DriftFinding]) -> list[HandoffQuestion]:
    return [
        HandoffQuestion(
            question=_HANDOFF_QUESTION[f.drift_class],
            drift_class=f.drift_class,
            measured_fact=f"{f.column}: {f.before} -> {f.after}",
            owner=_DEFAULT_OWNER[f.drift_class],
        )
        for f in findings
        if f.principle_v
    ]


@dataclass(frozen=True)
class ReportContext:
    """Provenance metadata for a drift report -- where the baseline came from,
    the evidence trail, and when/who took the observed re-profile. Bundled so
    to_findings_dict keeps a small, cohesive signature (data in, provenance in)."""

    baseline_ref: str
    evidence: list[str]
    reprofiled_at: str | None = None
    reprofiled_by: str | None = None


def to_findings_dict(
    baseline: ProfileResult,
    observed: ProfileResult | None,
    context: ReportContext,
) -> dict:
    """Serialize a drift comparison to the source-drift-findings.schema.json shape."""
    findings = classify_drift(baseline, observed)
    available = observed is not None
    status = derive_status(findings, observed_available=available)
    blocking = [
        f"{f.drift_class} on {f.column}: {f.before} -> {f.after}"
        for f in findings
        if f.severity == "blocked"
    ]
    return {
        "table": baseline.table,
        "baseline": context.baseline_ref,
        "observed": {
            "available": available,
            "reprofiled_at": context.reprofiled_at,
            "reprofiled_by": context.reprofiled_by,
        },
        "findings": [
            {
                "drift_class": f.drift_class,
                "column": f.column,
                "before": f.before,
                "after": f.after,
                "severity": f.severity,
                "principle_v": f.principle_v,
                **({"note": f.note} if f.note is not None else {}),
            }
            for f in findings
        ],
        "status": status,
        "blocking_reasons": blocking,
        "evidence": list(context.evidence),
        "principle_v_handoff": [
            {
                "question": h.question,
                "drift_class": h.drift_class,
                "measured_fact": h.measured_fact,
                "owner": h.owner,
            }
            for h in _handoffs(findings)
        ],
    }
