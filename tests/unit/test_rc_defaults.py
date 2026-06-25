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
    s8_date_dim_no_unknown_member,
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


def test_s5_clean_on_ordinal_line_no_to_smallint(tmp_path: Path) -> None:
    # RC7 SANCTIONS "ordinal line numbers with no leading zeros -> small integer".
    # So line_no::smallint is correct, not a violation -- S5 must NOT flag it.
    # (Regression: S5 originally fired on C086's line_no::smallint in 0002_*.sql.)
    rel = _write(
        tmp_path,
        "warehouse/migrations/0001_silver.sql",
        "SELECT line_no::smallint, seq_no::int2 FROM bronze.b;",
    )
    findings = list(s5_type_discipline(_ctx(tmp_path, rel)))
    assert findings == [], (
        "ordinal _no columns cast to smallint/int2 are RC7-sanctioned; "
        f"S5 must not flag them, got: {findings}"
    )


def test_s5_still_flags_id_cast_to_wide_int(tmp_path: Path) -> None:
    # The data-loss case (leading zeros): a cast to int/integer/bigint -- still flagged.
    rel = _write(
        tmp_path,
        "warehouse/migrations/0001_silver.sql",
        "SELECT customer_id::int, product_id::bigint FROM bronze.b;",
    )
    findings = list(s5_type_discipline(_ctx(tmp_path, rel)))
    assert len(findings) == 2, f"id cast to int/bigint must still flag, got: {findings}"
    assert all(f.rule_id == "S5" and "RC7" in f.message for f in findings)


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


def test_s6_exempts_dim_date_from_minus_one_requirement(tmp_path: Path) -> None:
    """A gold.dim_date* must NOT be required to carry a -1 unknown member (S6).

    Reconciliation with S8 (2026-06-25 Codex review): every OTHER gold dim gets a
    `-1 'UNKNOWN'` member (RC14/S6), but the DATE dim is the documented exception --
    it is destined to be a marked date table (dataCategory: Time), which Power BI
    validates as unique/contiguous/NO-nulls. So S6 must not flag a date dim that has
    no -1 member, and S8 (below) flags a date dim that DOES. The two are inverse and
    complementary, never contradictory.
    """
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "CREATE TABLE gold.dim_date (date_sk int, full_date date);\n"
        "INSERT INTO gold.dim_date\n"
        "SELECT (to_char(g.d,'YYYYMMDD'))::int, g.d::date\n"
        "FROM generate_series(DATE '2023-01-01', DATE '2025-12-31',"
        " INTERVAL '1 day') AS g(d);\n",  # NO -1 member -- correct for a date dim
    )
    findings = list(s6_gold_unknown_member(_ctx(tmp_path, rel)))
    assert findings == [], (
        "S6 must EXEMPT a date dim from the -1-member requirement (it becomes a "
        f"marked date table that rejects nulls), got: {findings}"
    )


# ===========================================================================
# S8 -- a marked date dim must carry NO -1/NULL unknown member (inverse of S6)
# ===========================================================================


def test_s8_flags_date_dim_with_minus_one_member(tmp_path: Path) -> None:
    """S8 ERRORs on a `gold.dim_date*` that inserts a -1/NULL unknown member.

    Codex PR review #1 (2026-06-25): a -1,NULL member in a date table that is marked
    dataCategory: Time makes Power BI date-table validation fail (or breaks
    time-intelligence) even though the SQL migration succeeds. The SQL must not
    create such a member; ERROR (a hard correctness gate, unlike S6/S7 warnings).
    """
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "CREATE TABLE gold.dim_date (date_sk int, full_date date);\n"
        "INSERT INTO gold.dim_date VALUES (-1, NULL);\n",
    )
    findings = list(s8_date_dim_no_unknown_member(_ctx(tmp_path, rel)))
    assert findings, "expected S8 to flag a date dim with a -1/NULL member"
    f = findings[0]
    assert f.rule_id == "S8"
    assert f.severity == Severity.ERROR
    assert "dim_date" in f.message


def test_s8_clean_when_date_dim_has_no_unknown_member(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "CREATE TABLE gold.dim_date (date_sk int, full_date date);\n"
        "INSERT INTO gold.dim_date\n"
        "SELECT (to_char(g.d,'YYYYMMDD'))::int, g.d::date\n"
        "FROM generate_series(DATE '2023-01-01', DATE '2025-12-31',"
        " INTERVAL '1 day') AS g(d);\n",
    )
    findings = list(s8_date_dim_no_unknown_member(_ctx(tmp_path, rel)))
    assert findings == [], (
        f"a date dim with no -1 member must be clean, got: {findings}"
    )


def test_s8_ignores_non_date_gold_dims(tmp_path: Path) -> None:
    """S8 only checks date dims; a normal dim's -1 member (S6-required) is fine."""
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "CREATE TABLE gold.dim_product (product_sk int, name text);\n"
        "INSERT INTO gold.dim_product VALUES (-1, 'UNKNOWN');\n",
    )
    findings = list(s8_date_dim_no_unknown_member(_ctx(tmp_path, rel)))
    assert findings == [], "S8 must only inspect gold.dim_date* tables"


def test_s8_exempts_test_fixtures(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "tests/fixtures/bad.sql",
        "INSERT INTO gold.dim_date VALUES (-1, NULL);\n",
    )
    findings = list(s8_date_dim_no_unknown_member(_ctx(tmp_path, rel)))
    assert findings == [], "tests/ fixtures are exempt from the live scan"


def test_s8_ignores_minus_one_arithmetic_in_date_insert(tmp_path: Path) -> None:
    """S8 must NOT flag a valid date-dim insert that uses `- 1` ARITHMETIC.

    Regression guard (2026-06-25 Codex review): the old pattern matched `-1` ANYWHERE
    before the `;`, so a calendar deriving e.g. a zero-based month (`extract(month
    FROM d) - 1`) or a previous-day offset tripped S8 -- and since S8 is ERROR it would
    BLOCK a perfectly valid marked calendar. Only a `-1` in the VALUES/key position is
    an unknown member; arithmetic `- 1` is not.
    """
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "CREATE TABLE gold.dim_date (date_sk int, full_date date, month_idx int);\n"
        "INSERT INTO gold.dim_date\n"
        "SELECT (to_char(g.d,'YYYYMMDD'))::int, g.d::date,\n"
        # the `- 1` below is arithmetic (zero-based month), NOT an unknown member:
        "       extract(month FROM g.d)::int - 1\n"
        "FROM generate_series(DATE '2023-01-01', DATE '2025-12-31',"
        " INTERVAL '1 day') AS g(d);\n",
    )
    findings = list(s8_date_dim_no_unknown_member(_ctx(tmp_path, rel)))
    assert findings == [], (
        "S8 must not treat arithmetic `- 1` as an unknown member; "
        f"got false-positive: {findings}"
    )


def test_s8_still_flags_values_minus_one_after_narrowing(tmp_path: Path) -> None:
    """The narrowing must NOT reopen Codex #1.

    A real `VALUES (-1, ...)` date member must still raise an S8 ERROR.
    """
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "CREATE TABLE gold.dim_date (date_sk int, full_date date);\n"
        "INSERT INTO gold.dim_date VALUES (-1, NULL);\n",
    )
    findings = list(s8_date_dim_no_unknown_member(_ctx(tmp_path, rel)))
    assert findings, "S8 must STILL flag a real VALUES(-1,...) date member"
    assert findings[0].rule_id == "S8"


# ===========================================================================
# S7 -- contiguous date dim (enforces RC15)
# ===========================================================================


def test_s7_flags_select_distinct_date_dim(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "INSERT INTO gold.dim_date\nSELECT DISTINCT sale_date FROM silver.sales;\n",
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


def test_all_four_clean_on_conforming_migration(tmp_path: Path) -> None:
    # The conforming shape (post Codex-review fix): the date dim is a contiguous
    # generate_series calendar with NO -1/NULL member (so it can be a marked date
    # table); a NORMAL dim carries its -1 member (RC14/S6). All four S-rules clean.
    rel = _write(
        tmp_path,
        "warehouse/migrations/0002_gold.sql",
        "CREATE TABLE gold.dim_product (product_sk int, name text);\n"
        "INSERT INTO gold.dim_product VALUES (-1, 'UNKNOWN');\n"
        "CREATE TABLE gold.dim_date (date_sk int, full_date date);\n"
        "INSERT INTO gold.dim_date\n"
        "SELECT (to_char(g.d,'YYYYMMDD'))::int, g.d::date\n"
        "FROM generate_series(DATE '2023-01-01', DATE '2025-12-31',"
        " INTERVAL '1 day') AS g(d);\n"
        "CREATE TABLE gold.fct_sales (amt numeric(18,2));\n",
    )
    ctx = _ctx(tmp_path, rel)
    assert list(s5_type_discipline(ctx)) == []
    assert list(s6_gold_unknown_member(ctx)) == []
    assert list(s7_contiguous_date_dim(ctx)) == []
    assert list(s8_date_dim_no_unknown_member(ctx)) == []
