"""Static contract for the follow-up warehouse migrations (0009-0011).

0004, 0005, 0006 and 0008 are already applied, so their defects are fixed by
NEW numbered migrations rather than in-place edits. This module pins what each
follow-up must do, as committed SQL text; the live behaviour (a fanned-out
dimension failing the load, unpadded labels, iso_year, a blank-side amount) is
proven against a real Postgres outside CI, since this suite opens no database.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]
_MIGRATIONS = _ROOT / "warehouse" / "migrations"
_FINANCE = _MIGRATIONS / "0009_harden_gold_finance_gl_star.sql"
_RETAIL = _MIGRATIONS / "0010_fix_gold_retail_store_sales_date_labels.sql"
_DEMO = _MIGRATIONS / "0011_enforce_silver_demo_sample_orders_pk.sql"
_DBT_DATE = _ROOT / "dbt/models/marts/retail_store_sales/dim_date_rss.sql"
_TMDL_DATE = (
    _ROOT
    / "powerbi/RetailStoreSales.SemanticModel/definition/tables/gold dim_date_rss.tmdl"
)
_LIVE_CONFTEST = _ROOT / "tests/live_db/conftest.py"

# to_char with an unpadded month/day pattern ('Month', 'Day'), i.e. WITHOUT the FM
# modifier that strips PostgreSQL's nine-character blank padding.
_PADDED_LABEL = re.compile(r"to_char\([^)]*'(?:Month|Day)'\)", re.IGNORECASE)
_DATE_DIM_INSERT = re.compile(r"INSERT\s+INTO\s+gold\.(dim_date_\w+)", re.IGNORECASE)


def _sql(path: Path) -> str:
    """Committed SQL with ``--`` comments removed and whitespace collapsed."""
    text = path.read_text(encoding="utf-8")
    code = "\n".join(line.split("--", 1)[0] for line in text.splitlines())
    return re.sub(r"\s+", " ", code)


def test_finance_dims_are_unique_on_their_natural_key() -> None:
    sql = _sql(_FINANCE)
    for table, key in (
        ("dim_account_fgl", "account_code"),
        ("dim_department_fgl", "department_code"),
        ("dim_cost_center_fgl", "cost_center_code, department_code"),
    ):
        pattern = rf"ALTER TABLE gold\.{table} ADD CONSTRAINT \w+ UNIQUE \({key}\)"
        assert re.search(pattern, sql), f"{table} is not UNIQUE on ({key})"


def test_finance_date_dim_has_unpadded_labels_and_iso_year() -> None:
    sql = _sql(_FINANCE)
    assert "DROP TABLE IF EXISTS gold.dim_date_fgl" in sql
    assert "iso_year SMALLINT" in sql
    assert "extract(isoyear FROM d)" in sql
    assert "to_char(d,'FMMonth')" in sql
    assert "to_char(d,'FMDay')" in sql
    assert not _PADDED_LABEL.search(sql)
    # the fact FK dropped for the rebuild is re-added
    assert "ADD CONSTRAINT fk_fct_gl_actuals_date FOREIGN KEY (date_sk)" in sql


@pytest.mark.parametrize(
    "table", ["silver.finance_gl_actuals", "gold.fct_gl_actuals_fgl"]
)
def test_amount_survives_a_blank_zero_side_but_stays_null_when_both_blank(
    table: str,
) -> None:
    sql = _sql(_FINANCE)
    expected = (
        f"UPDATE {table} SET amount = COALESCE(debit_amount, 0) + "
        "COALESCE(credit_amount, 0) WHERE amount IS NULL AND "
        "(debit_amount IS NOT NULL OR credit_amount IS NOT NULL);"
    )
    assert expected in sql


def test_retail_date_labels_are_unpadded_on_both_build_paths() -> None:
    sql = _sql(_RETAIL)
    assert "UPDATE gold.dim_date_rss" in sql
    assert "to_char(full_date, 'FMMonth')" in sql
    assert "to_char(full_date, 'FMDay')" in sql

    dbt_sql = _DBT_DATE.read_text(encoding="utf-8")
    assert "'FMMonth'" in dbt_sql and "'FMDay'" in dbt_sql
    assert not _PADDED_LABEL.search(dbt_sql)

    # The live dbt parity oracle rebuilds gold from migrations; it must include
    # 0010 after 0004 or it would compare padded labels to the FM shadow model.
    conftest = _LIVE_CONFTEST.read_text(encoding="utf-8")
    assert conftest.index("0004_create_gold_retail_store_sales_star.sql") < (
        conftest.index(_RETAIL.name)
    )


def test_month_name_sorts_by_month_number_in_the_semantic_model() -> None:
    tmdl = _TMDL_DATE.read_text(encoding="utf-8")
    block = tmdl.split("column month_name", 1)[1].split("\tcolumn ", 1)[0]
    assert "sortByColumn: month" in block


def test_every_padded_date_dim_is_relabelled_by_a_later_migration() -> None:
    """A gold date dimension built with blank-padded labels must be re-derived with
    the FM modifier by a LATER migration -- otherwise Power BI ships 'May      '."""
    files = sorted(_MIGRATIONS.glob("*.sql"))
    for index, path in enumerate(files):
        sql = _sql(path)
        for statement in sql.split(";"):
            match = _DATE_DIM_INSERT.search(statement)
            if not match or not _PADDED_LABEL.search(statement):
                continue
            table = match.group(1)
            fixed_later = any(
                f"gold.{table}" in _sql(later) and "FMMonth" in _sql(later)
                for later in files[index + 1 :]
            )
            assert fixed_later, f"{path.name}: gold.{table} labels stay blank-padded"


def test_demo_silver_primary_key_is_enforced() -> None:
    sql = _sql(_DEMO)
    assert re.search(
        r"ALTER TABLE silver\.demo_sample_orders ADD CONSTRAINT \w+ "
        r"PRIMARY KEY \(order_id\)",
        sql,
    )
