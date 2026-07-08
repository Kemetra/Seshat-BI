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
