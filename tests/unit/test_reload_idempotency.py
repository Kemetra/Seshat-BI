"""Unit tests for HR7 (reload-strategy declaration for gold loads)."""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.reload_idempotency import check_hr7

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]


def _mig(tmp_path: Path, name: str, sql: str) -> str:
    """Write a migration under tmp_path/warehouse/migrations/; return its rel path."""
    rel = f"warehouse/migrations/{name}"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(sql, encoding="utf-8")
    return rel


def _ctx(tmp_path: Path, *rel: str) -> RuleContext:
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(rel))


# --- US1: full drop-and-rebuild passes free ---


def test_hr7_full_drop_and_rebuild_passes_with_no_finding(tmp_path: Path) -> None:
    sql = (
        "CREATE SCHEMA IF NOT EXISTS gold;\n"
        "DROP TABLE IF EXISTS gold.fct_sales;\n"
        "CREATE TABLE gold.fct_sales (id int);\n"
        "INSERT INTO gold.fct_sales SELECT * FROM silver.sales;\n"
    )
    ctx = _ctx(tmp_path, _mig(tmp_path, "0100_gold.sql", sql))
    assert list(check_hr7(ctx)) == []


def test_hr7_whole_table_truncate_then_insert_passes(tmp_path: Path) -> None:
    sql = (
        "TRUNCATE TABLE gold.fct_sales;\n"
        "INSERT INTO gold.fct_sales SELECT * FROM silver.sales;\n"
    )
    ctx = _ctx(tmp_path, _mig(tmp_path, "0101_gold.sql", sql))
    assert list(check_hr7(ctx)) == []


def test_hr7_whole_table_delete_no_where_passes(tmp_path: Path) -> None:
    sql = (
        "DELETE FROM gold.fct_sales;\n"
        "INSERT INTO gold.fct_sales SELECT * FROM silver.sales;\n"
    )
    ctx = _ctx(tmp_path, _mig(tmp_path, "0102_gold.sql", sql))
    assert list(check_hr7(ctx)) == []


def test_hr7_passes_against_real_committed_migrations() -> None:
    """SC-001: HR7 emits zero Findings on the real committed migration set."""
    mig_dir = _REPO / "warehouse" / "migrations"
    rels = [f"warehouse/migrations/{p.name}" for p in sorted(mig_dir.glob("*.sql"))]
    ctx = RuleContext(repo_root=_REPO, tracked_files=tuple(rels))
    assert list(check_hr7(ctx)) == []


# --- US2: undeclared deviation fails closed; declaration clears ---


def test_hr7_bare_append_no_declaration_fails_closed(tmp_path: Path) -> None:
    sql = (
        "CREATE SCHEMA IF NOT EXISTS gold;\n"
        "INSERT INTO gold.fct_sales SELECT * FROM silver.sales;\n"
    )
    ctx = _ctx(tmp_path, _mig(tmp_path, "0103_gold.sql", sql))
    findings = list(check_hr7(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert findings[0].rule_id == "HR7"
    assert "gold.fct_sales" in findings[0].message


def test_hr7_bare_append_with_header_marker_clears(tmp_path: Path) -> None:
    sql = (
        "-- reload-strategy: transaction_id\n"
        "INSERT INTO gold.fct_sales SELECT * FROM silver.sales;\n"
    )
    ctx = _ctx(tmp_path, _mig(tmp_path, "0104_gold.sql", sql))
    assert list(check_hr7(ctx)) == []


def test_hr7_on_conflict_upsert_clears_without_marker(tmp_path: Path) -> None:
    sql = (
        "INSERT INTO gold.fct_sales SELECT * FROM silver.sales\n"
        "ON CONFLICT (transaction_id) DO UPDATE SET amount = excluded.amount;\n"
    )
    ctx = _ctx(tmp_path, _mig(tmp_path, "0105_gold.sql", sql))
    assert list(check_hr7(ctx)) == []


def test_hr7_load_policy_declaration_clears(tmp_path: Path) -> None:
    mig = _mig(
        tmp_path,
        "0106_gold.sql",
        "INSERT INTO gold.fct_sales SELECT * FROM silver.sales;\n",
    )
    policy_rel = "warehouse/load-policy.md"
    (tmp_path / policy_rel).write_text(
        "| 0106_gold.sql | gold.fct_sales | reload-strategy: transaction_id |\n",
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path, mig, policy_rel)
    assert list(check_hr7(ctx)) == []


def test_hr7_load_policy_ignored_when_untracked(tmp_path: Path) -> None:
    mig = _mig(
        tmp_path,
        "0107_gold.sql",
        "INSERT INTO gold.fct_sales SELECT * FROM silver.sales;\n",
    )
    # write the policy to disk but do NOT include it in tracked_files
    (tmp_path / "warehouse" / "load-policy.md").write_text(
        "| 0107_gold.sql | gold.fct_sales | reload-strategy: transaction_id |\n",
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path, mig)  # policy not tracked
    findings = list(check_hr7(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR


def test_hr7_mixed_migration_flags_only_the_deviation(tmp_path: Path) -> None:
    sql = (
        "DROP TABLE IF EXISTS gold.dim_store;\n"
        "INSERT INTO gold.dim_store SELECT * FROM silver.store;\n"
        "INSERT INTO gold.fct_sales SELECT * FROM silver.sales;\n"  # bare append
    )
    ctx = _ctx(tmp_path, _mig(tmp_path, "0108_gold.sql", sql))
    findings = list(check_hr7(ctx))
    assert len(findings) == 1
    assert "gold.fct_sales" in findings[0].message
    assert "dim_store" not in findings[0].message


def test_hr7_partial_delete_with_where_is_a_deviation(tmp_path: Path) -> None:
    sql = (
        "DELETE FROM gold.fct_sales WHERE sale_date >= '2026-01-01';\n"
        "INSERT INTO gold.fct_sales SELECT * FROM silver.sales;\n"
    )
    ctx = _ctx(tmp_path, _mig(tmp_path, "0109_gold.sql", sql))
    findings = list(check_hr7(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR


def test_hr7_ignores_non_gold_and_silver_migrations(tmp_path: Path) -> None:
    sql = "INSERT INTO silver.sales SELECT * FROM bronze.sales;\n"
    ctx = _ctx(tmp_path, _mig(tmp_path, "0110_silver.sql", sql))
    assert list(check_hr7(ctx)) == []


# --- US3: static-only, no live-proof claim, no numeric score ---


def test_hr7_commented_drop_does_not_clear_a_real_append(tmp_path: Path) -> None:
    """Regression (review Critical): a commented-out DROP must NOT clear a real
    bare append -- else an undeclared deviation slips past this fail-closed gate."""
    sql = (
        "-- DROP TABLE IF EXISTS gold.fct_sales\n"
        "INSERT INTO gold.fct_sales SELECT * FROM silver.sales;\n"
    )
    ctx = _ctx(tmp_path, _mig(tmp_path, "0120_gold.sql", sql))
    findings = list(check_hr7(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR


def test_hr7_rollback_comment_does_not_block_valid_migration(tmp_path: Path) -> None:
    """Regression (review Critical): a rollback COMMENT mentioning a bare INSERT
    must NOT be read as live SQL and block an otherwise-valid drop-and-rebuild."""
    sql = (
        "DROP TABLE IF EXISTS gold.fct_sales;\n"
        "INSERT INTO gold.fct_sales SELECT * FROM silver.sales;\n"
        "-- Rollback: INSERT INTO gold.fct_sales_backup SELECT * FROM gold.fct_sales;\n"
    )
    ctx = _ctx(tmp_path, _mig(tmp_path, "0121_gold.sql", sql))
    assert list(check_hr7(ctx)) == []


def test_hr7_sibling_upsert_does_not_clear_a_bare_append(tmp_path: Path) -> None:
    """Regression (review Critical FR-002): a per-statement ON CONFLICT on one
    table must NOT clear an unrelated bare append on another (no file-global pass)."""
    sql = (
        "INSERT INTO gold.fct_sales SELECT * FROM silver.sales;\n"  # bare deviation
        "INSERT INTO gold.dim_x SELECT * FROM silver.x\n"
        "ON CONFLICT (id) DO NOTHING;\n"  # unrelated upsert
    )
    ctx = _ctx(tmp_path, _mig(tmp_path, "0122_gold.sql", sql))
    findings = list(check_hr7(ctx))
    assert len(findings) == 1
    assert "gold.fct_sales" in findings[0].message
    assert "dim_x" not in findings[0].message


def test_hr7_module_imports_no_database_driver() -> None:
    src = (_REPO / "src" / "retail" / "rules" / "reload_idempotency.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("import psycopg", "import sqlalchemy", ".connect(", "DSN"):
        assert forbidden not in src


def test_hr7_message_has_no_numeric_score(tmp_path: Path) -> None:
    sql = "INSERT INTO gold.fct_sales SELECT * FROM silver.sales;\n"
    ctx = _ctx(tmp_path, _mig(tmp_path, "0111_gold.sql", sql))
    for f in check_hr7(ctx):
        assert "%" not in f.message
