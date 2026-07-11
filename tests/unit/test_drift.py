"""TDD tests for the F014 source-drift comparator (src/seshat/drift.py).

Task 1 scope: classify_drift() diffs a baseline ProfileResult against an
observed ProfileResult and reports column_added / column_removed findings.
Findings must be emitted in a deterministic order (sorted by column name) so
the schema-shaped output stays diffable and snapshot-testable -- set
iteration order over string keys is not stable across process hash seeds.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.profile import ColumnProfile, PkProof, ProfileResult
from tests.unit._schema_check import assert_matches_schema

pytestmark = pytest.mark.unit

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "source-drift-findings.schema.json"
)


def _col(name, missing_pct=0.0, card=10, landed_type=None):
    return ColumnProfile(
        name=name,
        missing_count=0,
        missing_pct=missing_pct,
        distinct_cardinality=card,
        landed_type=landed_type,
    )


def _profile(cols, *, table="bronze.t", rows=100, is_unique=True):
    # null_pk stays 0 here; the grain-PK tests express "PK broke" via is_unique
    # (a non-unique observed PK is the drift the comparator keys on).
    return ProfileResult(
        table=table,
        row_count=rows,
        column_count=len(cols),
        columns=tuple(cols),
        pk=PkProof(total=rows, distinct_pk=rows, null_pk=0, is_unique=is_unique),
    )


def test_column_added_is_warning():
    from seshat.drift import classify_drift

    base = _profile([_col("a")])
    obs = _profile([_col("a"), _col("b")])
    findings = classify_drift(base, obs)
    added = [f for f in findings if f.drift_class == "column_added"]
    assert len(added) == 1
    assert added[0].column == "b"
    assert added[0].severity == "warning"
    assert added[0].principle_v is False


def test_column_removed_is_blocked():
    from seshat.drift import classify_drift

    base = _profile([_col("a"), _col("b")])
    obs = _profile([_col("a")])
    findings = classify_drift(base, obs)
    removed = [f for f in findings if f.drift_class == "column_removed"]
    assert len(removed) == 1
    assert removed[0].column == "b"
    assert removed[0].severity == "blocked"


def test_findings_are_deterministically_ordered():
    from seshat.drift import classify_drift

    base = _profile([_col("a")])
    obs = _profile([_col("a"), _col("z"), _col("m"), _col("b")])
    findings = classify_drift(base, obs)
    added = [f.column for f in findings if f.drift_class == "column_added"]
    assert added == sorted(added)


def test_missingness_shift_reports_measured_before_after():
    from seshat.drift import classify_drift

    base = _profile([_col("a", missing_pct=3.1)])
    obs = _profile([_col("a", missing_pct=11.7)])
    findings = classify_drift(base, obs)
    ms = [f for f in findings if f.drift_class == "missingness_shift"]
    assert len(ms) == 1
    assert ms[0].before == "3.10%"
    assert ms[0].after == "11.70%"
    assert ms[0].severity == "warning"


def test_cardinality_shift_reported():
    from seshat.drift import classify_drift

    base = _profile([_col("a", card=5)])
    obs = _profile([_col("a", card=42)])
    findings = classify_drift(base, obs)
    cs = [f for f in findings if f.drift_class == "cardinality_shift"]
    assert len(cs) == 1
    assert cs[0].before == "5 distinct"
    assert cs[0].after == "42 distinct"


def test_no_shift_when_equal():
    from seshat.drift import classify_drift

    base = _profile([_col("a", missing_pct=3.1, card=5)])
    obs = _profile([_col("a", missing_pct=3.1, card=5)])
    assert classify_drift(base, obs) == []


def test_no_missingness_shift_when_rounded_values_are_equal():
    from seshat.drift import classify_drift

    # Sub-cent-of-a-percent float delta must not produce a finding whose
    # rendered before/after strings are identical (e.g. "3.00%" -> "3.00%").
    base = _profile([_col("a", missing_pct=3.001, card=5)])
    obs = _profile([_col("a", missing_pct=3.004, card=5)])
    assert classify_drift(base, obs) == []


def test_shift_findings_are_deterministically_ordered_by_column():
    from seshat.drift import classify_drift

    base = _profile(
        [
            _col("z", missing_pct=1.0, card=1),
            _col("m", missing_pct=1.0, card=1),
            _col("b", missing_pct=1.0, card=1),
        ]
    )
    obs = _profile(
        [
            _col("z", missing_pct=2.0, card=2),
            _col("m", missing_pct=2.0, card=2),
            _col("b", missing_pct=2.0, card=2),
        ]
    )
    findings = classify_drift(base, obs)
    shift_columns = [
        f.column
        for f in findings
        if f.drift_class in ("missingness_shift", "cardinality_shift")
    ]
    # Both shift kinds are reported per column in sorted column order:
    # b's findings before m's before z's.
    assert shift_columns == ["b", "b", "m", "m", "z", "z"]


def test_grain_pk_drift_is_blocked_and_principle_v():
    from seshat.drift import classify_drift

    base = _profile([_col("a")], is_unique=True)
    obs = _profile([_col("a")], is_unique=False)
    findings = classify_drift(base, obs)
    g = [f for f in findings if f.drift_class == "grain_pk_drift"]
    assert len(g) == 1
    assert g[0].severity == "blocked"
    assert g[0].principle_v is True


def _validate(doc):
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert_matches_schema(doc, schema)


def test_derive_status_blocked_when_fatal_class_present():
    from seshat.drift import classify_drift, derive_status

    base = _profile([_col("a"), _col("b")])
    obs = _profile([_col("a")])  # b removed -> blocked
    assert (
        derive_status(classify_drift(base, obs), observed_available=True) == "blocked"
    )


def test_derive_status_warning_when_only_nonfatal():
    from seshat.drift import classify_drift, derive_status

    base = _profile([_col("a", missing_pct=1.0)])
    obs = _profile([_col("a", missing_pct=9.0)])  # missingness shift only
    assert (
        derive_status(classify_drift(base, obs), observed_available=True) == "warning"
    )


def test_derive_status_pass_when_no_findings():
    from seshat.drift import classify_drift, derive_status

    base = _profile([_col("a")])
    obs = _profile([_col("a")])
    assert derive_status(classify_drift(base, obs), observed_available=True) == "pass"


def test_deferred_live_is_pending_and_schema_valid():
    from seshat.drift import ReportContext, to_findings_dict

    base = _profile([_col("a")])
    doc = to_findings_dict(
        base,
        None,
        ReportContext(
            baseline_ref="mappings/t/source-profile.md@abc",
            evidence=["mappings/t/source-drift-report.md"],
        ),
    )
    assert doc["status"] == "pending_live_reprofile"
    assert doc["observed"]["available"] is False
    assert doc["findings"] == []
    _validate(doc)


def test_full_report_schema_valid_with_findings_and_handoff():
    from seshat.drift import ReportContext, to_findings_dict

    base = _profile([_col("a")], is_unique=True)
    obs = _profile([_col("a")], is_unique=False)  # grain_pk_drift -> handoff
    doc = to_findings_dict(
        base,
        obs,
        ReportContext(
            baseline_ref="mappings/t/source-profile.md@abc",
            evidence=["mappings/t/source-drift-report.md"],
        ),
    )
    assert doc["status"] == "blocked"
    assert any(h["drift_class"] == "grain_pk_drift" for h in doc["principle_v_handoff"])
    assert doc["blocking_reasons"]  # non-empty
    _validate(doc)


# --- returns_rule_drift + pii_surface_drift (Principle-V escalations) ---------
# Both are RE-CLASSIFICATIONS of an already-detected shape change, keyed on a
# semantic role that arrives via the optional DriftSemantics param. They are
# NEVER auto-resolved -- measured + raised to a named owner (returns->analyst,
# pii->governance). semantics=None => neither fires (the pre-existing behavior).


def test_no_semantics_means_no_returns_or_pii_findings():
    # Regression guard: without semantics, the two new classes never fire, so
    # every prior caller (and the 14 earlier tests) behaves exactly as before.
    from seshat.drift import classify_drift

    base = _profile([_col("is_return"), _col("email")])
    obs = _profile([_col("email")])  # is_return removed; would-be PII 'email' stays
    findings = classify_drift(base, obs)  # no semantics
    classes = {f.drift_class for f in findings}
    assert "returns_rule_drift" not in classes
    assert "pii_surface_drift" not in classes
    # the plain column_removed still fires (unchanged)
    assert any(f.drift_class == "column_removed" for f in findings)


def test_returns_column_removed_is_returns_rule_drift():
    from seshat.drift import DriftSemantics, classify_drift

    base = _profile([_col("is_return"), _col("amount")])
    obs = _profile([_col("amount")])  # the authoritative returns column disappeared
    findings = classify_drift(base, obs, DriftSemantics(returns_column="is_return"))
    rr = [f for f in findings if f.drift_class == "returns_rule_drift"]
    assert len(rr) == 1
    assert rr[0].severity == "blocked"
    assert rr[0].principle_v is True
    assert rr[0].column == "is_return"


def test_returns_column_shift_is_returns_rule_drift():
    from seshat.drift import DriftSemantics, classify_drift

    base = _profile([_col("is_return", missing_pct=1.0, card=2)])
    obs = _profile([_col("is_return", missing_pct=9.0, card=2)])  # population moved
    findings = classify_drift(base, obs, DriftSemantics(returns_column="is_return"))
    rr = [f for f in findings if f.drift_class == "returns_rule_drift"]
    assert len(rr) == 1
    assert rr[0].severity == "blocked"
    assert rr[0].principle_v is True


def test_dropped_pii_column_reappearing_is_pii_surface_drift():
    from seshat.drift import DriftSemantics, classify_drift

    base = _profile([_col("amount")])
    obs = _profile([_col("amount"), _col("ssn")])  # a dropped-PII column returns
    findings = classify_drift(
        base, obs, DriftSemantics(dropped_pii_columns=frozenset({"ssn"}))
    )
    pii = [f for f in findings if f.drift_class == "pii_surface_drift"]
    assert len(pii) == 1
    assert pii[0].severity == "blocked"
    assert pii[0].principle_v is True
    assert pii[0].column == "ssn"


def test_new_nonpii_column_is_not_pii_surface_drift():
    # Deterministic scope: only a column in the dropped-PII set escalates. A
    # brand-new column NOT in that set is a plain column_added, never PII drift
    # (no name-guessing -- publish-safety is never auto-decided).
    from seshat.drift import DriftSemantics, classify_drift

    base = _profile([_col("amount")])
    obs = _profile([_col("amount"), _col("region")])
    findings = classify_drift(
        base, obs, DriftSemantics(dropped_pii_columns=frozenset({"ssn"}))
    )
    assert not any(f.drift_class == "pii_surface_drift" for f in findings)
    added = [f for f in findings if f.drift_class == "column_added"]
    assert [f.column for f in added] == ["region"]


def test_returns_and_pii_handoffs_are_schema_valid():
    from seshat.drift import DriftSemantics, ReportContext, to_findings_dict

    base = _profile([_col("is_return"), _col("amount")])
    obs = _profile([_col("amount"), _col("ssn")])  # returns removed + PII reappears
    doc = to_findings_dict(
        base,
        obs,
        ReportContext(
            baseline_ref="mappings/t/source-profile.md@abc",
            evidence=["mappings/t/source-drift-report.md"],
        ),
        semantics=DriftSemantics(
            returns_column="is_return", dropped_pii_columns=frozenset({"ssn"})
        ),
    )
    assert doc["status"] == "blocked"
    owners = {h["drift_class"]: h["owner"] for h in doc["principle_v_handoff"]}
    assert owners.get("returns_rule_drift") == "analyst"
    assert owners.get("pii_surface_drift") == "governance"
    _validate(doc)


def test_unchanged_returns_column_is_not_returns_rule_drift():
    # Pins the no-change guard: an authoritative returns column whose stats are
    # UNCHANGED must not fire returns_rule_drift (else every run of a stable
    # table would raise a false Principle-V blocker). Deleting the
    # `before == after` guard in _returns_rule_findings must fail this.
    from seshat.drift import DriftSemantics, classify_drift

    base = _profile([_col("is_return", missing_pct=2.0, card=2)])
    obs = _profile([_col("is_return", missing_pct=2.0, card=2)])  # identical
    findings = classify_drift(base, obs, DriftSemantics(returns_column="is_return"))
    assert not any(f.drift_class == "returns_rule_drift" for f in findings)


def test_dropped_pii_column_present_in_both_is_not_pii_surface_drift():
    # Pins the "reappeared-ONLY" semantics: a dropped-PII name that is present in
    # BOTH baseline and observed has NOT reappeared (it never left the profile),
    # so it must not fire. Dropping the `- base_cols.keys()` from the set logic
    # in _pii_surface_findings must fail this.
    from seshat.drift import DriftSemantics, classify_drift

    base = _profile([_col("amount"), _col("ssn")])  # ssn already in the baseline
    obs = _profile([_col("amount"), _col("ssn")])
    findings = classify_drift(
        base, obs, DriftSemantics(dropped_pii_columns=frozenset({"ssn"}))
    )
    assert not any(f.drift_class == "pii_surface_drift" for f in findings)


# --- column_retyped (mechanical, warning; NOT Principle-V) --------------------
# The landed type of a surviving column changed. blocked-if-key/measure is a
# deferred follow-on (severity's semantic half); this ships the warning level.


def test_column_retyped_is_warning_not_principle_v():
    from seshat.drift import classify_drift

    base = _profile([_col("a", landed_type="text")])
    obs = _profile([_col("a", landed_type="numeric")])
    findings = classify_drift(base, obs)
    rt = [f for f in findings if f.drift_class == "column_retyped"]
    assert len(rt) == 1
    assert rt[0].column == "a"
    assert rt[0].before == "text"
    assert rt[0].after == "numeric"
    assert rt[0].severity == "warning"
    assert rt[0].principle_v is False


def test_case_only_type_difference_is_not_retyped(tmp_path=None):
    # THE GATING GUARD: baseline markdown records uppercase "TEXT"; a live
    # information_schema re-profile returns lowercase "text". These are the SAME
    # type -- a naive != would fire column_retyped on every bronze-all-TEXT
    # column (a false-drift storm). The compare must normalize (lowercase+strip).
    from seshat.drift import classify_drift

    base = _profile([_col("a", landed_type="TEXT")])
    obs = _profile([_col("a", landed_type="text")])
    findings = classify_drift(base, obs)
    assert not any(f.drift_class == "column_retyped" for f in findings)


def test_no_retyped_when_landed_type_unknown_on_either_side():
    # Both-known guard: if either side lacks a landed_type (None), we can't prove
    # a retype -> stay silent (honest-skip), rather than fabricate one. This is
    # also what keeps the older _col(landed_type=None) tests free of retype noise.
    from seshat.drift import classify_drift

    base = _profile([_col("a", landed_type=None)])
    obs = _profile([_col("a", landed_type="numeric")])
    assert not any(f.drift_class == "column_retyped" for f in classify_drift(base, obs))
