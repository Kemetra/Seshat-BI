"""TDD tests for the layer-aware S4b rule and schema_zone helper.

Every test creates its own tmp_path fixtures — no writes into the real repo tree.
All fixtures are written inline (no external fixture files needed).

Policy table being tested:
  silver/gold  + in-txn         -> PASS (no finding)
  silver/gold  + bare no-txn    -> WARNING
  bronze       + bare DROP      -> ERROR
  bronze       + bare CREATE    -> ERROR
  bronze       + guarded        -> PASS
  unknown/unqualified + bare    -> WARNING (fail-closed)
  search_path + unqualified     -> WARNING (fail-closed)
  CREATE INDEX ON silver.x + in-txn -> PASS (zone from table, not index)
  guarded forms (any zone)      -> PASS (existing behaviour preserved)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.sql import s4b_guard_form
from seshat.sql import schema_zone, tokenize_sql

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, rel: str, content: str) -> str:
    """Write SQL content to tmp_path/rel and return the rel path."""
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return rel


def _ctx(tmp_path: Path, *rels: str) -> RuleContext:
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(rels))


# ---------------------------------------------------------------------------
# schema_zone unit tests
# ---------------------------------------------------------------------------


def test_schema_zone_silver_table() -> None:
    """CREATE TABLE silver.foo -> zone 'silver'."""
    toks = [t for t in tokenize_sql("CREATE TABLE silver.foo (id INT);") if t.text]
    assert schema_zone(toks, 0) == "silver"


def test_schema_zone_gold_table() -> None:
    """CREATE TABLE gold.bar -> zone 'gold'."""
    toks = [t for t in tokenize_sql("CREATE TABLE gold.bar (id INT);") if t.text]
    assert schema_zone(toks, 0) == "gold"


def test_schema_zone_bronze_table() -> None:
    """DROP TABLE bronze.raw_data -> zone 'bronze'."""
    toks = [t for t in tokenize_sql("DROP TABLE bronze.raw_data;") if t.text]
    assert schema_zone(toks, 0) == "bronze"


def test_schema_zone_unqualified_is_unknown() -> None:
    """Unqualified target has no schema -> 'unknown'."""
    toks = [t for t in tokenize_sql("CREATE TABLE foo (id INT);") if t.text]
    assert schema_zone(toks, 0) == "unknown"


def test_schema_zone_create_index_uses_table_schema() -> None:
    """CREATE INDEX idx ON silver.x -- zone is silver (table, not index)."""
    sql = "CREATE INDEX idx ON silver.x (col);"
    toks = [t for t in tokenize_sql(sql) if t.text]
    assert schema_zone(toks, 0) == "silver"


def test_schema_zone_search_path_followed_by_unqualified_is_unknown() -> None:
    """SET search_path=silver; DROP TABLE x; -- x is unqualified -> unknown.

    The zone scanner is bounded to the statement, so the search_path of the
    previous statement does NOT carry forward.
    """
    sql = "SET search_path=silver; DROP TABLE x;"
    toks = [t for t in tokenize_sql(sql) if t.text]
    # Find the DROP token index
    drop_idx = next(i for i, t in enumerate(toks) if t.text.upper() == "DROP")
    assert schema_zone(toks, drop_idx) == "unknown"


def test_schema_zone_unqualified_with_silver_source_is_unknown() -> None:
    """CREATE TABLE foo AS SELECT * FROM silver.bar -- target is unqualified -> unknown.

    This is the key fail-closed safety test: a silver SOURCE must not grant
    the silver zone to an unqualified TARGET.
    """
    sql = "CREATE TABLE foo AS SELECT * FROM silver.bar;"
    toks = [t for t in tokenize_sql(sql) if t.text]
    assert schema_zone(toks, 0) == "unknown"


# ---------------------------------------------------------------------------
# Policy row: silver/gold DROP+CREATE inside BEGIN/COMMIT -> PASS
# ---------------------------------------------------------------------------


def test_s4b_silver_drop_create_in_txn_no_finding(tmp_path: Path) -> None:
    """Silver DROP+CREATE inside BEGIN/COMMIT -> zero findings (the C086 case)."""
    sql = (
        "BEGIN;\n"
        "DROP TABLE IF EXISTS silver.foo;\n"
        "CREATE TABLE silver.foo AS SELECT 1 AS x;\n"
        "COMMIT;\n"
    )
    rel = _write(tmp_path, "warehouse/migrations/0099_silver.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert s4b == [], f"Expected no S4b findings, got: {s4b}"


def test_s4b_gold_drop_create_in_txn_no_finding(tmp_path: Path) -> None:
    """Gold DROP+CREATE inside BEGIN/COMMIT -> zero findings."""
    sql = (
        "BEGIN;\n"
        "DROP TABLE IF EXISTS gold.dim_x;\n"
        "CREATE TABLE gold.dim_x (id INT);\n"
        "COMMIT;\n"
    )
    rel = _write(tmp_path, "warehouse/migrations/0099_gold.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert s4b == [], f"Expected no S4b findings, got: {s4b}"


def test_s4b_silver_bare_drop_in_txn_no_finding(tmp_path: Path) -> None:
    """BARE silver DROP (no IF EXISTS) inside a txn -> no finding.

    Exercises the zone+in_txn PASS branch directly: a bare DROP is NOT caught
    by _is_guarded, so this proves the pass comes from (zone=silver AND in_txn),
    not from the guarded-form short-circuit. The existing
    test_s4b_silver_drop_create_in_txn_no_finding uses DROP TABLE IF EXISTS,
    which short-circuits via _is_guarded and would not demonstrate this path.
    """
    sql = (
        "BEGIN;\n"
        "DROP TABLE silver.foo;\n"  # BARE drop — no IF EXISTS
        "CREATE TABLE silver.foo AS SELECT 1 AS x;\n"
        "COMMIT;\n"
    )
    rel = _write(tmp_path, "warehouse/migrations/0099_silver_bare_drop.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert s4b == [], (
        f"Expected no S4b findings (bare DROP, zone=silver, in_txn), got: {s4b}"
    )


def test_s4b_gold_bare_drop_in_txn_no_finding(tmp_path: Path) -> None:
    """BARE gold DROP (no IF EXISTS) inside a txn -> no finding (zone+in_txn pass)."""
    sql = (
        "BEGIN;\n"
        "DROP TABLE gold.dim_x;\n"  # BARE drop — no IF EXISTS
        "CREATE TABLE gold.dim_x (id INT);\n"
        "COMMIT;\n"
    )
    rel = _write(tmp_path, "warehouse/migrations/0099_gold_bare_drop.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert s4b == [], (
        f"Expected no S4b findings (bare DROP, zone=gold, in_txn), got: {s4b}"
    )


def test_s4b_silver_bare_drop_not_in_txn_warns(tmp_path: Path) -> None:
    """BARE silver DROP with NO BEGIN/COMMIT -> exactly one WARNING.

    Symmetric negative of test_s4b_silver_bare_drop_in_txn_no_finding: confirms
    the transaction is precisely what flips pass<->warn for a silver bare DROP.
    """
    sql = "DROP TABLE silver.foo;\n"  # BARE drop, no transaction
    rel = _write(tmp_path, "warehouse/migrations/0099_silver_bare_drop_notxn.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert len(s4b) == 1, (
        f"Expected 1 WARNING (bare DROP, zone=silver, no txn), got: {s4b}"
    )
    assert s4b[0].severity is Severity.WARNING
    assert "silver" in s4b[0].message.lower()


def test_s4b_silver_alter_in_txn_no_finding(tmp_path: Path) -> None:
    """Silver ALTER inside BEGIN/COMMIT -> zero findings."""
    sql = "BEGIN;\nALTER TABLE silver.foo ADD PRIMARY KEY (id);\nCOMMIT;\n"
    rel = _write(tmp_path, "warehouse/migrations/0099_alter.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert s4b == [], f"Expected no S4b findings, got: {s4b}"


def test_s4b_create_index_on_silver_in_txn_no_finding(tmp_path: Path) -> None:
    """CREATE INDEX ON silver.x in txn -> no finding (zone=silver via table)."""
    sql = "BEGIN;\nCREATE INDEX idx_x ON silver.sales (sale_date);\nCOMMIT;\n"
    rel = _write(tmp_path, "warehouse/migrations/0099_idx.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert s4b == [], f"Expected no S4b findings, got: {s4b}"


# ---------------------------------------------------------------------------
# Policy row: silver/gold bare NOT in transaction -> WARNING
# ---------------------------------------------------------------------------


def test_s4b_silver_bare_create_no_txn_warning(tmp_path: Path) -> None:
    """Silver bare CREATE not in a transaction -> WARNING."""
    sql = "CREATE TABLE silver.foo AS SELECT 1;\n"
    rel = _write(tmp_path, "warehouse/migrations/0099_bare_silver.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert len(s4b) == 1
    assert s4b[0].severity is Severity.WARNING
    assert "silver" in s4b[0].message.lower()


def test_s4b_gold_bare_create_no_txn_warning(tmp_path: Path) -> None:
    """Gold bare CREATE not in a transaction -> WARNING."""
    sql = "CREATE TABLE gold.dim_x (id INT);\n"
    rel = _write(tmp_path, "warehouse/migrations/0099_bare_gold.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert len(s4b) == 1
    assert s4b[0].severity is Severity.WARNING


# ---------------------------------------------------------------------------
# Policy row: bronze bare DROP/CREATE -> ERROR
# ---------------------------------------------------------------------------


def test_s4b_bronze_bare_drop_error(tmp_path: Path) -> None:
    """Bronze bare DROP -> ERROR (blocks build)."""
    sql = "DROP TABLE bronze.raw_data;\n"
    rel = _write(tmp_path, "warehouse/migrations/0099_bronze_drop.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert len(s4b) == 1
    assert s4b[0].severity is Severity.ERROR
    assert "bronze" in s4b[0].message.lower()


def test_s4b_bronze_bare_create_error(tmp_path: Path) -> None:
    """Bronze bare CREATE -> ERROR (blocks build)."""
    sql = "CREATE TABLE bronze.raw_data (col TEXT);\n"
    rel = _write(tmp_path, "warehouse/migrations/0099_bronze_create.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert len(s4b) == 1
    assert s4b[0].severity is Severity.ERROR
    assert "bronze" in s4b[0].message.lower()


def test_s4b_bronze_in_txn_still_error(tmp_path: Path) -> None:
    """Bronze bare DROP inside a transaction -> ERROR (in-txn does NOT rescue bronze).

    This pins the safety-critical invariant: bronze is strict regardless of
    transaction. A false-pass here would be the worst outcome (destroys
    source-of-truth without any guard).
    """
    sql = "BEGIN;\nDROP TABLE bronze.raw_data;\nCOMMIT;\n"
    rel = _write(tmp_path, "warehouse/migrations/0099_bronze_in_txn.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert len(s4b) == 1, (
        f"Expected 1 ERROR (bronze in-txn must not earn the pass), got: {s4b}"
    )
    assert s4b[0].severity is Severity.ERROR


# ---------------------------------------------------------------------------
# Policy row: bronze guarded -> PASS
# ---------------------------------------------------------------------------


def test_s4b_bronze_guarded_no_finding(tmp_path: Path) -> None:
    """Bronze CREATE TABLE IF NOT EXISTS -> no finding."""
    sql = "CREATE TABLE IF NOT EXISTS bronze.raw_data (col TEXT);\n"
    rel = _write(tmp_path, "warehouse/migrations/0099_bronze_guarded.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert s4b == [], f"Expected no S4b findings, got: {s4b}"


# ---------------------------------------------------------------------------
# Policy row: unqualified bare DROP/CREATE -> WARNING (fail-closed)
# ---------------------------------------------------------------------------


def test_s4b_unqualified_bare_drop_warning(tmp_path: Path) -> None:
    """Unqualified bare DROP -> WARNING (fail-closed, not pass)."""
    sql = "DROP TABLE foo;\n"
    rel = _write(tmp_path, "warehouse/migrations/0099_unqualified_drop.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert len(s4b) == 1
    assert s4b[0].severity is Severity.WARNING


def test_s4b_search_path_unqualified_warning(tmp_path: Path) -> None:
    """SET search_path=silver; DROP TABLE x; -> WARNING (fail-closed, zone unknown)."""
    sql = "SET search_path=silver;\nDROP TABLE x;\n"
    rel = _write(tmp_path, "warehouse/migrations/0099_search_path.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert len(s4b) == 1
    assert s4b[0].severity is Severity.WARNING


# ---------------------------------------------------------------------------
# Fail-closed safety: unqualified target + silver source -> WARNING, not PASS
# ---------------------------------------------------------------------------


def test_s4b_unqualified_target_silver_source_warning(tmp_path: Path) -> None:
    """CREATE TABLE foo AS SELECT * FROM silver.bar; -> WARNING (not a pass).

    This is the key fail-closed safety test. The silver is in the SELECT source,
    not the target. schema_zone must return unknown for target 'foo'.
    """
    sql = "BEGIN;\nCREATE TABLE foo AS SELECT * FROM silver.bar;\nCOMMIT;\n"
    rel = _write(tmp_path, "warehouse/migrations/0099_failclosed.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert len(s4b) == 1, (
        f"Expected 1 WARNING (fail-closed: target is unqualified), got: {s4b}"
    )
    assert s4b[0].severity is Severity.WARNING


# ---------------------------------------------------------------------------
# Regression: existing guarded-form cases still pass
# ---------------------------------------------------------------------------


def test_s4b_existing_guarded_forms_still_pass(tmp_path: Path) -> None:
    """Existing guarded forms pass regardless of zone (regression check)."""
    sql = (
        "CREATE TABLE IF NOT EXISTS gold.fct_sales (sale_id BIGINT);\n"
        "CREATE OR REPLACE VIEW gold.vw_returns AS SELECT 1;\n"
        "ALTER TABLE IF EXISTS gold.fct_sales ADD COLUMN qty INT;\n"
        "DROP TABLE IF EXISTS gold.tmp_load;\n"
    )
    rel = _write(tmp_path, "warehouse/pass_s4b_guarded.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert s4b == [], f"Expected no S4b findings for guarded forms, got: {s4b}"


def test_s4b_regression_gold_bare_outside_txn_warns(tmp_path: Path) -> None:
    """Existing test_s4b_warns_on_bare_create_and_alter regression.

    Gold bare CREATE + ALTER with no BEGIN/COMMIT -> 2 WARNINGs (gold bare no-txn).
    Both remain WARNING (not ERROR, not suppressed).
    """
    sql = (
        "CREATE TABLE gold.fct_sales (sale_id BIGINT);\n"
        "ALTER TABLE gold.fct_sales ADD COLUMN qty INT;\n"
    )
    rel = _write(tmp_path, "warehouse/fail_s4b_bare.sql", sql)
    findings = list(s4b_guard_form(_ctx(tmp_path, rel)))
    s4b = [f for f in findings if f.rule_id == "S4b"]
    assert len(s4b) == 2
    assert all(f.severity is Severity.WARNING for f in s4b)
    assert {f.locator for f in s4b} == {
        "warehouse/fail_s4b_bare.sql:1",
        "warehouse/fail_s4b_bare.sql:2",
    }
