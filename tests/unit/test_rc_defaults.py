"""TDD tests for S5/S6/S7 -- the SQL-family rules that enforce ADR cleaning
defaults RC7 (type discipline), RC14 (gold -1 unknown member), RC15 (contiguous
date dim). Feature 003.

Every test builds its own tmp_path fixtures (the M3 lesson -- never write into the
real repo tree). Rules scan tracked warehouse/**/*.sql via iter_sql_files and use
the tokenize_sql lexer (so comments/string literals must NOT trigger findings).

Naming contract: the rule IDS stay in the checker S-family (S5/S6/S7); each rule
CITES the RC default it enforces in its message -- it never adopts the RC id.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.sql import (
    s5_type_discipline,
    s6_gold_unknown_member,
    s7_contiguous_date_dim,
)

pytestmark = pytest.mark.unit


def _write(tmp_path: Path, rel: str, content: str) -> str:
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return rel


def _ctx(tmp_path: Path, *rels: str) -> RuleContext:
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(rels))


# ===========================================================================
# S5 -- type discipline (enforces RC7)
# ===========================================================================


def test_s5_flags_money_cast_to_float(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0001_silver.sql",
        "CREATE TABLE silver.s AS SELECT amount::float8 AS amt FROM bronze.b;",
    )
    findings = list(s5_type_discipline(_ctx(tmp_path, rel)))
    assert findings, "expected an S5 finding for ::float8 on a money-ish column"
    f = findings[0]
    assert f.rule_id == "S5"
    assert f.severity in (Severity.WARNING, Severity.ERROR)
    assert "RC7" in f.message


def test_s5_flags_double_precision_and_real(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0001_silver.sql",
        "SELECT price::double precision, qty::real FROM bronze.b;",
    )
    findings = list(s5_type_discipline(_ctx(tmp_path, rel)))
    assert len(findings) >= 1
    assert all(f.rule_id == "S5" for f in findings)


def test_s5_clean_on_numeric_casts(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0001_silver.sql",
        "SELECT amount::numeric(18,2), qty::numeric(18,4), sale_date::date "
        "FROM bronze.b;",
    )
    findings = list(s5_type_discipline(_ctx(tmp_path, rel)))
    assert findings == [], f"exact-numeric casts must be clean, got: {findings}"


def test_s5_ignores_float_in_comment(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0001_silver.sql",
        "-- never cast amount to float here\n"
        "SELECT amount::numeric(18,2) FROM bronze.b;",
    )
    findings = list(s5_type_discipline(_ctx(tmp_path, rel)))
    assert findings == [], "a 'float' word inside a comment must not trigger S5"


def test_s5_exempts_test_fixtures(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "tests/fixtures/bad.sql",
        "SELECT amount::float FROM bronze.b;",
    )
    findings = list(s5_type_discipline(_ctx(tmp_path, rel)))
    assert findings == [], "tests/ fixtures are exempt from the live scan"


# ===========================================================================
# S6 -- gold dim unknown member (enforces RC14)
# ===========================================================================


def test_s6_flags_dim_without_minus_one_member(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "CREATE TABLE gold.dim_product (product_sk int, name text);\n"
        "-- no -1 unknown member inserted\n",
    )
    findings = list(s6_gold_unknown_member(_ctx(tmp_path, rel)))
    assert findings, "expected S6 to flag a gold dim with no -1 member"
    f = findings[0]
    assert f.rule_id == "S6"
    assert f.severity == Severity.WARNING
    assert "RC14" in f.message
    assert "dim_product" in f.message


def test_s6_clean_when_minus_one_member_present(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "CREATE TABLE gold.dim_product (product_sk int, name text);\n"
        "INSERT INTO gold.dim_product OVERRIDING SYSTEM VALUE "
        "VALUES (-1, 'UNKNOWN');\n",
    )
    findings = list(s6_gold_unknown_member(_ctx(tmp_path, rel)))
    assert findings == [], f"dim with a -1 member must be clean, got: {findings}"


def test_s6_only_inspects_gold_dims(tmp_path: Path) -> None:
    # A silver table, or a gold FACT, is not a gold dim_* -> S6 ignores it.
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "CREATE TABLE silver.sales (id int);\n"
        "CREATE TABLE gold.fct_sales (sale_sk int);\n",
    )
    findings = list(s6_gold_unknown_member(_ctx(tmp_path, rel)))
    assert findings == [], "S6 only checks gold.dim_* tables"


def test_s6_clean_multiple_dims_all_with_members(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "CREATE TABLE gold.dim_a (a_sk int);\n"
        "INSERT INTO gold.dim_a VALUES (-1, 'x');\n"
        "CREATE TABLE gold.dim_b (b_sk int);\n"
        "INSERT INTO gold.dim_b OVERRIDING SYSTEM VALUE VALUES (-1, 'y');\n",
    )
    findings = list(s6_gold_unknown_member(_ctx(tmp_path, rel)))
    assert findings == [], f"all dims have -1 members; expected clean, got: {findings}"


# ===========================================================================
# S7 -- contiguous date dim (enforces RC15)
# ===========================================================================


def test_s7_flags_select_distinct_date_dim(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "INSERT INTO gold.dim_date\n" "SELECT DISTINCT sale_date FROM silver.sales;\n",
    )
    findings = list(s7_contiguous_date_dim(_ctx(tmp_path, rel)))
    assert findings, "expected S7 to flag a SELECT DISTINCT date dim"
    f = findings[0]
    assert f.rule_id == "S7"
    assert f.severity == Severity.WARNING
    assert "RC15" in f.message


def test_s7_clean_on_generate_series(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "INSERT INTO gold.dim_date\n"
        "SELECT g.d FROM generate_series("
        "DATE '2023-01-01', DATE '2025-12-31', INTERVAL '1 day') AS g(d);\n",
    )
    findings = list(s7_contiguous_date_dim(_ctx(tmp_path, rel)))
    assert findings == [], f"generate_series calendar must be clean, got: {findings}"


def test_s7_ignores_select_distinct_on_non_date_dim(tmp_path: Path) -> None:
    # SELECT DISTINCT elsewhere (not populating dim_date) is not S7's concern.
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "INSERT INTO gold.dim_product\n"
        "SELECT DISTINCT product_id, name FROM silver.sales;\n",
    )
    findings = list(s7_contiguous_date_dim(_ctx(tmp_path, rel)))
    assert findings == [], "S7 only flags SELECT DISTINCT that populates dim_date"


# ===========================================================================
# Cross-rule: all three clean on a generate_series + -1-member + numeric file
# (the shape C086's committed migrations have -> retail check stays green)
# ===========================================================================


def test_all_three_clean_on_conforming_migration(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "CREATE TABLE gold.dim_date (date_sk int, full_date date);\n"
        "INSERT INTO gold.dim_date VALUES (-1, NULL);\n"
        "INSERT INTO gold.dim_date\n"
        "SELECT row_number() OVER (), g.d::date\n"
        "FROM generate_series(DATE '2023-01-01', DATE '2025-12-31',"
        " INTERVAL '1 day') AS g(d);\n"
        "CREATE TABLE gold.fct_sales (amt numeric(18,2));\n",
    )
    ctx = _ctx(tmp_path, rel)
    assert list(s5_type_discipline(ctx)) == []
    assert list(s6_gold_unknown_member(ctx)) == []
    assert list(s7_contiguous_date_dim(ctx)) == []
