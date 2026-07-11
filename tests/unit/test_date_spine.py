"""Unit tests for HR8 (gold date dim is contiguous/gap-free)."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.date_spine import check_hr8

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


def _dim_date_sql(start: str, end: str, step: str) -> str:
    return (
        "CREATE SCHEMA IF NOT EXISTS gold;\n"
        "CREATE TABLE gold.dim_date (date_sk INT, full_date DATE);\n"
        "INSERT INTO gold.dim_date\n"
        "SELECT (to_char(d,'YYYYMMDD'))::int, d::date\n"
        f"FROM generate_series({start}, {end}, {step}) AS g(d);\n"
    )


# --- US1: non-daily / unclassifiable step fails closed; daily step passes ---


def test_hr8_non_daily_literal_step_fails_closed(tmp_path: Path) -> None:
    sql = _dim_date_sql("DATE '2022-01-01'", "DATE '2025-01-18'", "INTERVAL '1 month'")
    ctx = _ctx(tmp_path, _mig(tmp_path, "0200_gold.sql", sql))
    findings = list(check_hr8(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert findings[0].rule_id == "HR8"
    assert "1 month" in findings[0].message


def test_hr8_daily_step_typed_interval_passes(tmp_path: Path) -> None:
    sql = _dim_date_sql("DATE '2022-01-01'", "DATE '2025-01-18'", "INTERVAL '1 day'")
    ctx = _ctx(tmp_path, _mig(tmp_path, "0201_gold.sql", sql))
    assert list(check_hr8(ctx)) == []


def test_hr8_daily_step_cast_interval_passes(tmp_path: Path) -> None:
    """The Opus-review fix: '1 day'::interval must also pass (cast idiom)."""
    sql = _dim_date_sql("DATE '2022-01-01'", "DATE '2025-01-18'", "'1 day'::interval")
    ctx = _ctx(tmp_path, _mig(tmp_path, "0202_gold.sql", sql))
    assert list(check_hr8(ctx)) == []


def test_hr8_non_daily_cast_interval_fails_closed(tmp_path: Path) -> None:
    """The other half of the Opus fix: a non-daily cast interval must still ERROR."""
    sql = _dim_date_sql("DATE '2022-01-01'", "DATE '2025-01-18'", "'1 month'::interval")
    ctx = _ctx(tmp_path, _mig(tmp_path, "0203_gold.sql", sql))
    findings = list(check_hr8(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "1 month" in findings[0].message


def test_hr8_unclassifiable_step_fails_closed_with_distinct_message(
    tmp_path: Path,
) -> None:
    sql = _dim_date_sql("DATE '2022-01-01'", "DATE '2025-01-18'", "some_step_variable")
    ctx = _ctx(tmp_path, _mig(tmp_path, "0204_gold.sql", sql))
    findings = list(check_hr8(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    non_daily_sql = _dim_date_sql(
        "DATE '2022-01-01'", "DATE '2025-01-18'", "INTERVAL '1 month'"
    )
    non_daily_ctx = _ctx(tmp_path, _mig(tmp_path, "0205_gold.sql", non_daily_sql))
    non_daily_findings = list(check_hr8(non_daily_ctx))
    assert findings[0].message != non_daily_findings[0].message


# --- US2: reversed literal bounds fail closed; non-literal bound skips ---


def test_hr8_reversed_literal_bounds_fails_closed(tmp_path: Path) -> None:
    sql = _dim_date_sql("DATE '2025-01-18'", "DATE '2022-01-01'", "INTERVAL '1 day'")
    ctx = _ctx(tmp_path, _mig(tmp_path, "0206_gold.sql", sql))
    findings = list(check_hr8(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "2025-01-18" in findings[0].message
    assert "2022-01-01" in findings[0].message


def test_hr8_chronological_bounds_pass(tmp_path: Path) -> None:
    """Mutation-reverse of the previous test: swap back to chronological order."""
    sql = _dim_date_sql("DATE '2022-01-01'", "DATE '2025-01-18'", "INTERVAL '1 day'")
    ctx = _ctx(tmp_path, _mig(tmp_path, "0207_gold.sql", sql))
    assert list(check_hr8(ctx)) == []


def test_hr8_reversed_cast_literal_bounds_fails_closed(tmp_path: Path) -> None:
    sql = _dim_date_sql("'2025-01-18'::date", "'2022-01-01'::date", "INTERVAL '1 day'")
    ctx = _ctx(tmp_path, _mig(tmp_path, "0208_gold.sql", sql))
    findings = list(check_hr8(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR


def test_hr8_non_padded_valid_range_not_flagged(tmp_path: Path) -> None:
    """Regression (review Important): a valid range in non-zero-padded PG literals
    (2022-1-9 -> 2022-01-10) must NOT be flagged reversed. Lexically '2022-1-9' >
    '2022-01-10', so a string compare would falsely fire; chronologically it is
    Jan 9 -> Jan 10, a valid forward range."""
    sql = _dim_date_sql("DATE '2022-1-9'", "DATE '2022-01-10'", "INTERVAL '1 day'")
    ctx = _ctx(tmp_path, _mig(tmp_path, "0210_gold.sql", sql))
    assert list(check_hr8(ctx)) == []


def test_hr8_non_padded_reversed_range_is_flagged(tmp_path: Path) -> None:
    """Regression (review Important): a genuinely reversed non-padded range
    (2022-01-10 -> 2022-1-9) MUST be flagged -- lexically start < end (false
    negative under a string compare), chronologically Jan 10 -> Jan 9 is reversed."""
    sql = _dim_date_sql("DATE '2022-01-10'", "DATE '2022-1-9'", "INTERVAL '1 day'")
    ctx = _ctx(tmp_path, _mig(tmp_path, "0211_gold.sql", sql))
    findings = list(check_hr8(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR


def test_hr8_non_literal_bound_skips_bounds_check(tmp_path: Path) -> None:
    sql = _dim_date_sql(
        "(SELECT min(transaction_date) FROM silver.orders)",
        "DATE '2022-01-01'",
        "INTERVAL '1 day'",
    )
    ctx = _ctx(tmp_path, _mig(tmp_path, "0209_gold.sql", sql))
    # No ERROR from the bounds-order check (one side is not statically
    # comparable); the daily step is fine, so no findings at all.
    assert list(check_hr8(ctx)) == []


# --- edge cases ---


def test_hr8_no_dim_date_insert_is_a_noop(tmp_path: Path) -> None:
    sql = "INSERT INTO gold.dim_store SELECT * FROM silver.store;\n"
    ctx = _ctx(tmp_path, _mig(tmp_path, "0210_gold.sql", sql))
    assert list(check_hr8(ctx)) == []


def test_hr8_generate_series_in_comment_is_ignored(tmp_path: Path) -> None:
    sql = (
        "-- generate_series(DATE '2025-01-18', DATE '2022-01-01', INTERVAL '1 month')\n"
        "INSERT INTO gold.dim_store SELECT * FROM silver.store;\n"
    )
    ctx = _ctx(tmp_path, _mig(tmp_path, "0211_gold.sql", sql))
    assert list(check_hr8(ctx)) == []


def test_hr8_multiple_builds_in_one_file_each_flagged_independently(
    tmp_path: Path,
) -> None:
    sql = (
        "CREATE SCHEMA IF NOT EXISTS gold;\n"
        "INSERT INTO gold.dim_date_a\n"
        "SELECT d FROM generate_series(DATE '2022-01-01', DATE '2025-01-18', "
        "INTERVAL '1 month') AS g(d);\n"
        "INSERT INTO gold.dim_date_b\n"
        "SELECT d FROM generate_series(DATE '2022-01-01', DATE '2025-01-18', "
        "INTERVAL '1 day') AS g(d);\n"
    )
    ctx = _ctx(tmp_path, _mig(tmp_path, "0212_gold.sql", sql))
    findings = list(check_hr8(ctx))
    assert len(findings) == 1
    assert "1 month" in findings[0].message


def test_hr8_ignores_non_migrations_path(tmp_path: Path) -> None:
    sql = _dim_date_sql("DATE '2025-01-18'", "DATE '2022-01-01'", "INTERVAL '1 month'")
    rel = "warehouse/seeds/0001_seed.sql"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(sql, encoding="utf-8")
    ctx = _ctx(tmp_path, rel)
    assert list(check_hr8(ctx)) == []


def test_hr8_fires_order_blind_to_readiness_stage(tmp_path: Path) -> None:
    """A minimal RuleContext with no readiness-status fixture still evaluates."""
    sql = _dim_date_sql("DATE '2022-01-01'", "DATE '2025-01-18'", "INTERVAL '1 month'")
    ctx = _ctx(tmp_path, _mig(tmp_path, "0213_gold.sql", sql))
    assert list(check_hr8(ctx)) != []


# --- real committed tree stays clean (SC-001) ---


def test_hr8_passes_against_real_committed_migrations() -> None:
    """SC-001: HR8 emits zero Findings on the real committed migration set,
    including the shipped worked-example
    ``0004_create_gold_retail_store_sales_star.sql`` (daily step, chronological
    literal bounds)."""
    mig_dir = _REPO / "warehouse" / "migrations"
    rels = [f"warehouse/migrations/{p.name}" for p in sorted(mig_dir.glob("*.sql"))]
    ctx = RuleContext(repo_root=_REPO, tracked_files=tuple(rels))
    assert list(check_hr8(ctx)) == []


# --- static-only, no DB, no live coverage claim, no numeric score, no S7 edit ---


def test_hr8_module_imports_no_database_driver_or_validate() -> None:
    src = (_REPO / "src" / "seshat" / "rules" / "date_spine.py").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "import psycopg",
        "import sqlalchemy",
        ".connect(",
        "DSN",
        "from ..validate",
        "from seshat.validate",
        "import validate",
    ):
        assert forbidden not in src


def test_hr8_never_claims_coverage_is_proven(tmp_path: Path) -> None:
    """No HR8 message anywhere may claim the calendar 'covers' or is
    'complete'/'gap-free' against the fact's real span (hard rule #9)."""
    sql = _dim_date_sql("DATE '2022-01-01'", "DATE '2025-01-18'", "INTERVAL '1 month'")
    ctx = _ctx(tmp_path, _mig(tmp_path, "0214_gold.sql", sql))
    for f in check_hr8(ctx):
        low = f.message.lower()
        assert "covers" not in low
        assert "gap-free" not in low
        assert low.count("complete") == 0


def test_hr8_message_has_no_numeric_score(tmp_path: Path) -> None:
    sql = _dim_date_sql("DATE '2022-01-01'", "DATE '2025-01-18'", "INTERVAL '1 month'")
    ctx = _ctx(tmp_path, _mig(tmp_path, "0215_gold.sql", sql))
    for f in check_hr8(ctx):
        assert "%" not in f.message


def test_hr8_does_not_import_or_call_s7() -> None:
    src = (_REPO / "src" / "seshat" / "rules" / "date_spine.py").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "from .sql import",
        "from ..rules.sql import",
        "s7_contiguous_date_dim(",
    ):
        assert forbidden not in src
