"""Unit tests for HR11 (summed measure inputs share a unit)."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.currency_unit import check_unit_currency_agreement

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]


def _source_map(tmp_path: Path, table: str, yaml_body: str) -> str:
    rel = f"mappings/{table}/source-map.yaml"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(yaml_body, encoding="utf-8")
    return rel


def _metric(tmp_path: Path, table: str, name: str, yaml_body: str) -> str:
    rel = f"mappings/{table}/metrics/{name}.yaml"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(yaml_body, encoding="utf-8")
    return rel


def _ctx(tmp_path: Path, *rel: str) -> RuleContext:
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(rel))


_SOURCE_MAP_BODY = """
columns:
  - source_name: "SRC_WEIGHT"
    decision: "keep"
    reason: "quantity measure"
    rename_to: "weight_kg"
    silver_type: "numeric(18,2)"
    missing_policy: "null"
    pii: false
    gold_placement: "fact_measure"
    unit: "kg"
    currency: null
  - source_name: "SRC_SECONDARY_WEIGHT"
    decision: "keep"
    reason: "quantity measure"
    rename_to: "secondary_weight_kg"
    silver_type: "numeric(18,2)"
    missing_policy: "null"
    pii: false
    gold_placement: "fact_measure"
    unit: "kg"
    currency: null
  - source_name: "SRC_UNIT_COUNT"
    decision: "keep"
    reason: "item count"
    rename_to: "unit_count"
    silver_type: "numeric(18,2)"
    missing_policy: "null"
    pii: false
    gold_placement: "fact_measure"
    unit: "each"
    currency: null
  - source_name: "SRC_REVENUE_EGP"
    decision: "keep"
    reason: "money measure"
    rename_to: "revenue_egp"
    silver_type: "numeric(18,2)"
    missing_policy: "null"
    pii: false
    gold_placement: "fact_measure"
    unit: null
    currency: "EGP"
  - source_name: "SRC_REVENUE_EGP_2"
    decision: "keep"
    reason: "money measure"
    rename_to: "revenue_egp_2"
    silver_type: "numeric(18,2)"
    missing_policy: "null"
    pii: false
    gold_placement: "fact_measure"
    unit: null
    currency: "EGP"
  - source_name: "SRC_REVENUE_USD"
    decision: "keep"
    reason: "money measure"
    rename_to: "revenue_usd"
    silver_type: "numeric(18,2)"
    missing_policy: "null"
    pii: false
    gold_placement: "fact_measure"
    unit: null
    currency: "USD"
  - source_name: "SRC_UNDECLARED"
    decision: "keep"
    reason: "quantity measure, not yet declared"
    rename_to: "undeclared_qty"
    silver_type: "numeric(18,2)"
    missing_policy: "null"
    pii: false
    gold_placement: "fact_measure"
    unit: null
    currency: null
"""


def _metric_yaml(name: str, columns: list[str]) -> str:
    cols = "\n".join(f'    - "{c}"' for c in columns)
    return (
        f'name: "{name}"\n'
        f'grain: "test grain"\n'
        f'formula_intent: "test intent"\n'
        f'owner: "test_owner"\n'
        "binds_to:\n"
        '  gold_table: "gold.fct_test"\n'
        "  columns:\n"
        f"{cols}\n"
        "  pii_sensitive: false\n"
        "readiness:\n"
        '  status: "not_started"\n'
        "  evidence: []\n"
        "  blocking_reasons: []\n"
    )


# --- US1: clashing unit fails closed ---


def test_clashing_unit_fails(tmp_path: Path) -> None:
    smap = _source_map(tmp_path, "fixture_table", _SOURCE_MAP_BODY)
    metric = _metric(
        tmp_path,
        "fixture_table",
        "ClashingUnit",
        _metric_yaml("ClashingUnit", ["weight_kg", "unit_count"]),
    )
    ctx = _ctx(tmp_path, smap, metric)
    findings = list(check_unit_currency_agreement(ctx))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "HR11"
    assert f.severity is Severity.ERROR
    assert "ClashingUnit" in f.message
    assert "weight_kg" in f.message
    assert "unit_count" in f.message
    assert "kg" in f.message
    assert "each" in f.message


def test_hr11_finding_never_carries_a_conversion_hint(tmp_path: Path) -> None:
    smap = _source_map(tmp_path, "fixture_table", _SOURCE_MAP_BODY)
    metric = _metric(
        tmp_path,
        "fixture_table",
        "ClashingUnit",
        _metric_yaml("ClashingUnit", ["weight_kg", "unit_count"]),
    )
    ctx = _ctx(tmp_path, smap, metric)
    findings = list(check_unit_currency_agreement(ctx))
    assert len(findings) == 1
    msg_lower = findings[0].message.lower()
    for forbidden in ("rate", "factor", "convert"):
        assert forbidden not in msg_lower
    assert "%" not in findings[0].message


def test_unresolvable_bound_column_fails(tmp_path: Path) -> None:
    smap = _source_map(tmp_path, "fixture_table", _SOURCE_MAP_BODY)
    metric = _metric(
        tmp_path,
        "fixture_table",
        "UnresolvableColumn",
        _metric_yaml("UnresolvableColumn", ["weight_kg", "totally_unknown_col"]),
    )
    ctx = _ctx(tmp_path, smap, metric)
    findings = list(check_unit_currency_agreement(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "UnresolvableColumn" in findings[0].message
    assert "totally_unknown_col" in findings[0].message


def test_missing_source_map_fails(tmp_path: Path) -> None:
    # No sibling source-map.yaml is written at all.
    metric = _metric(
        tmp_path,
        "fixture_table_missing_map",
        "OrphanMetric",
        _metric_yaml("OrphanMetric", ["weight_kg", "unit_count"]),
    )
    ctx = _ctx(tmp_path, metric)
    findings = list(check_unit_currency_agreement(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "OrphanMetric" in findings[0].message
    assert "source-map.yaml" in findings[0].message


# --- US2: same-unit / same-currency clears; single-column never fires ---


def test_same_unit_produces_no_finding(tmp_path: Path) -> None:
    smap = _source_map(tmp_path, "fixture_table", _SOURCE_MAP_BODY)
    metric = _metric(
        tmp_path,
        "fixture_table",
        "CleanUnit",
        _metric_yaml("CleanUnit", ["weight_kg", "secondary_weight_kg"]),
    )
    ctx = _ctx(tmp_path, smap, metric)
    assert list(check_unit_currency_agreement(ctx)) == []


def test_same_currency_produces_no_finding(tmp_path: Path) -> None:
    smap = _source_map(tmp_path, "fixture_table", _SOURCE_MAP_BODY)
    metric = _metric(
        tmp_path,
        "fixture_table",
        "CleanCurrency",
        _metric_yaml("CleanCurrency", ["revenue_egp", "revenue_egp_2"]),
    )
    ctx = _ctx(tmp_path, smap, metric)
    assert list(check_unit_currency_agreement(ctx)) == []


def test_single_bound_column_never_fires(tmp_path: Path) -> None:
    smap = _source_map(tmp_path, "fixture_table", _SOURCE_MAP_BODY)
    metric = _metric(
        tmp_path,
        "fixture_table",
        "SingleColumn",
        _metric_yaml("SingleColumn", ["weight_kg"]),
    )
    ctx = _ctx(tmp_path, smap, metric)
    assert list(check_unit_currency_agreement(ctx)) == []


def test_undeclared_unit_on_one_side_is_not_a_finding(tmp_path: Path) -> None:
    """FR-014 stays OPEN: a null vs. a declared value is excluded from
    comparison, not treated as a mismatch (nor as "matches anything") --
    this module does not adopt a strict enforcement posture on its own
    authority."""
    smap = _source_map(tmp_path, "fixture_table", _SOURCE_MAP_BODY)
    metric = _metric(
        tmp_path,
        "fixture_table",
        "UndeclaredSide",
        _metric_yaml("UndeclaredSide", ["weight_kg", "undeclared_qty"]),
    )
    ctx = _ctx(tmp_path, smap, metric)
    assert list(check_unit_currency_agreement(ctx)) == []


def test_hr11_findings_never_carry_a_numeric_score(tmp_path: Path) -> None:
    smap = _source_map(tmp_path, "fixture_table", _SOURCE_MAP_BODY)
    m1 = _metric(
        tmp_path,
        "fixture_table",
        "ClashingUnit",
        _metric_yaml("ClashingUnit", ["weight_kg", "unit_count"]),
    )
    m2 = _metric(
        tmp_path,
        "fixture_table",
        "ClashingCurrency",
        _metric_yaml("ClashingCurrency", ["revenue_egp", "revenue_usd"]),
    )
    ctx = _ctx(tmp_path, smap, m1, m2)
    findings = list(check_unit_currency_agreement(ctx))
    assert len(findings) == 2
    for f in findings:
        assert "%" not in f.message
        assert not hasattr(f, "score")
        assert not hasattr(f, "confidence")


# --- US3: currency clash caught the same way; independent axes ---


def test_clashing_currency_fails(tmp_path: Path) -> None:
    smap = _source_map(tmp_path, "fixture_table", _SOURCE_MAP_BODY)
    metric = _metric(
        tmp_path,
        "fixture_table",
        "ClashingCurrency",
        _metric_yaml("ClashingCurrency", ["revenue_egp", "revenue_usd"]),
    )
    ctx = _ctx(tmp_path, smap, metric)
    findings = list(check_unit_currency_agreement(ctx))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "HR11"
    assert f.severity is Severity.ERROR
    assert "ClashingCurrency" in f.message
    assert "revenue_egp" in f.message
    assert "revenue_usd" in f.message
    assert "EGP" in f.message
    assert "USD" in f.message


def test_currency_finding_never_carries_a_conversion_hint(tmp_path: Path) -> None:
    smap = _source_map(tmp_path, "fixture_table", _SOURCE_MAP_BODY)
    metric = _metric(
        tmp_path,
        "fixture_table",
        "ClashingCurrency",
        _metric_yaml("ClashingCurrency", ["revenue_egp", "revenue_usd"]),
    )
    ctx = _ctx(tmp_path, smap, metric)
    findings = list(check_unit_currency_agreement(ctx))
    assert len(findings) == 1
    msg_lower = findings[0].message.lower()
    for forbidden in ("rate", "factor", "convert"):
        assert forbidden not in msg_lower


def test_unit_and_currency_clash_are_independent_findings(tmp_path: Path) -> None:
    """A metric whose bound columns clash on BOTH unit and currency reports
    both conditions (FR-006 is independent of FR-005), not only the first
    one found."""
    smap = _source_map(
        tmp_path,
        "fixture_table",
        _SOURCE_MAP_BODY
        + """
  - source_name: "SRC_MIXED_A"
    decision: "keep"
    reason: "mixed measure a"
    rename_to: "mixed_a"
    silver_type: "numeric(18,2)"
    missing_policy: "null"
    pii: false
    gold_placement: "fact_measure"
    unit: "kg"
    currency: "EGP"
  - source_name: "SRC_MIXED_B"
    decision: "keep"
    reason: "mixed measure b"
    rename_to: "mixed_b"
    silver_type: "numeric(18,2)"
    missing_policy: "null"
    pii: false
    gold_placement: "fact_measure"
    unit: "each"
    currency: "USD"
""",
    )
    metric = _metric(
        tmp_path,
        "fixture_table",
        "MixedClash",
        _metric_yaml("MixedClash", ["mixed_a", "mixed_b"]),
    )
    ctx = _ctx(tmp_path, smap, metric)
    findings = list(check_unit_currency_agreement(ctx))
    assert len(findings) == 2
    messages = " ".join(f.message for f in findings)
    assert "kg" in messages and "each" in messages
    assert "EGP" in messages and "USD" in messages


# --- static-only / real-tree-clean ---


def test_hr11_module_imports_no_database_driver() -> None:
    src = (_REPO / "src" / "seshat" / "rules" / "currency_unit.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("import psycopg", "import sqlalchemy", ".connect(", "DSN"):
        assert forbidden not in src


def test_hr11_passes_against_real_committed_tree() -> None:
    """SC-004: HR11 emits zero findings against the real committed tree --
    every committed metric contract with 2+ bound columns resolves cleanly
    against its table's source-map, and no unit/currency is yet declared
    anywhere (so no clash is possible), confirming FR-014's non-default
    holds in practice, not just in fixtures."""
    tracked: list[str] = []
    mappings_dir = _REPO / "mappings"
    if mappings_dir.exists():
        for p in mappings_dir.rglob("*.yaml"):
            rel = p.relative_to(_REPO).as_posix()
            tracked.append(rel)
    ctx = RuleContext(repo_root=_REPO, tracked_files=tuple(tracked))
    assert list(check_unit_currency_agreement(ctx)) == []
