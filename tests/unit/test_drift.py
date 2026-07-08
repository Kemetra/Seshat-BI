"""TDD tests for the F014 source-drift comparator (src/retail/drift.py).

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

from retail.profile import ColumnProfile, PkProof, ProfileResult
from tests.unit._schema_check import assert_matches_schema

pytestmark = pytest.mark.unit

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "source-drift-findings.schema.json"
)


def _col(name, missing_pct=0.0, card=10):
    return ColumnProfile(
        name=name, missing_count=0, missing_pct=missing_pct, distinct_cardinality=card
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
    from retail.drift import classify_drift, derive_status

    base = _profile([_col("a"), _col("b")])
    obs = _profile([_col("a")])  # b removed -> blocked
    assert (
        derive_status(classify_drift(base, obs), observed_available=True) == "blocked"
    )


def test_derive_status_warning_when_only_nonfatal():
    from retail.drift import classify_drift, derive_status

    base = _profile([_col("a", missing_pct=1.0)])
    obs = _profile([_col("a", missing_pct=9.0)])  # missingness shift only
    assert (
        derive_status(classify_drift(base, obs), observed_available=True) == "warning"
    )


def test_derive_status_pass_when_no_findings():
    from retail.drift import classify_drift, derive_status

    base = _profile([_col("a")])
    obs = _profile([_col("a")])
    assert derive_status(classify_drift(base, obs), observed_available=True) == "pass"


def test_deferred_live_is_pending_and_schema_valid():
    from retail.drift import ReportContext, to_findings_dict

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
    from retail.drift import ReportContext, to_findings_dict

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
