"""TDD tests for the F014 source-drift comparator (src/retail/drift.py).

Task 1 scope: classify_drift() diffs a baseline ProfileResult against an
observed ProfileResult and reports column_added / column_removed findings.
Findings must be emitted in a deterministic order (sorted by column name) so
the schema-shaped output stays diffable and snapshot-testable -- set
iteration order over string keys is not stable across process hash seeds.
"""

from __future__ import annotations

import pytest

from retail.profile import ColumnProfile, PkProof, ProfileResult

pytestmark = pytest.mark.unit


def _col(name, missing_pct=0.0, card=10):
    return ColumnProfile(
        name=name, missing_count=0, missing_pct=missing_pct, distinct_cardinality=card
    )


def _profile(cols, *, table="bronze.t", rows=100, is_unique=True, null_pk=0):
    return ProfileResult(
        table=table,
        row_count=rows,
        column_count=len(cols),
        columns=tuple(cols),
        pk=PkProof(total=rows, distinct_pk=rows, null_pk=null_pk, is_unique=is_unique),
    )


def test_column_added_is_warning():
    from retail.drift import classify_drift

    base = _profile([_col("a")])
    obs = _profile([_col("a"), _col("b")])
    findings = classify_drift(base, obs)
    added = [f for f in findings if f.drift_class == "column_added"]
    assert len(added) == 1
    assert added[0].column == "b"
    assert added[0].severity == "warning"
    assert added[0].principle_v is False


def test_column_removed_is_blocked():
    from retail.drift import classify_drift

    base = _profile([_col("a"), _col("b")])
    obs = _profile([_col("a")])
    findings = classify_drift(base, obs)
    removed = [f for f in findings if f.drift_class == "column_removed"]
    assert len(removed) == 1
    assert removed[0].column == "b"
    assert removed[0].severity == "blocked"


def test_findings_are_deterministically_ordered():
    from retail.drift import classify_drift

    base = _profile([_col("a")])
    obs = _profile([_col("a"), _col("z"), _col("m"), _col("b")])
    findings = classify_drift(base, obs)
    added = [f.column for f in findings if f.drift_class == "column_added"]
    assert added == sorted(added)


def test_missingness_shift_reports_measured_before_after():
    from retail.drift import classify_drift

    base = _profile([_col("a", missing_pct=3.1)])
    obs = _profile([_col("a", missing_pct=11.7)])
    findings = classify_drift(base, obs)
    ms = [f for f in findings if f.drift_class == "missingness_shift"]
    assert len(ms) == 1
    assert ms[0].before == "3.10%"
    assert ms[0].after == "11.70%"
    assert ms[0].severity == "warning"


def test_cardinality_shift_reported():
    from retail.drift import classify_drift

    base = _profile([_col("a", card=5)])
    obs = _profile([_col("a", card=42)])
    findings = classify_drift(base, obs)
    cs = [f for f in findings if f.drift_class == "cardinality_shift"]
    assert len(cs) == 1
    assert cs[0].before == "5 distinct"
    assert cs[0].after == "42 distinct"


def test_no_shift_when_equal():
    from retail.drift import classify_drift

    base = _profile([_col("a", missing_pct=3.1, card=5)])
    obs = _profile([_col("a", missing_pct=3.1, card=5)])
    assert classify_drift(base, obs) == []


def test_no_missingness_shift_when_rounded_values_are_equal():
    from retail.drift import classify_drift

    # Sub-cent-of-a-percent float delta must not produce a finding whose
    # rendered before/after strings are identical (e.g. "3.00%" -> "3.00%").
    base = _profile([_col("a", missing_pct=3.001, card=5)])
    obs = _profile([_col("a", missing_pct=3.004, card=5)])
    assert classify_drift(base, obs) == []


def test_shift_findings_are_deterministically_ordered_by_column():
    from retail.drift import classify_drift

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
    from retail.drift import classify_drift

    base = _profile([_col("a")], is_unique=True, null_pk=0)
    obs = _profile([_col("a")], is_unique=False, null_pk=0)
    findings = classify_drift(base, obs)
    g = [f for f in findings if f.drift_class == "grain_pk_drift"]
    assert len(g) == 1
    assert g[0].severity == "blocked"
    assert g[0].principle_v is True
