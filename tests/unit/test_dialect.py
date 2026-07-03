from __future__ import annotations

import pytest

from retail.dialect import get_dialect

pytestmark = pytest.mark.unit


def test_postgres_count_where_is_filter() -> None:
    pg = get_dialect("postgres")
    # Postgres KEEPS the native FILTER form (byte-identical to today's SQL).
    assert pg.count_where("x IS NULL") == "count(*) FILTER (WHERE x IS NULL)"


def test_postgres_quote_ident_double_quote() -> None:
    pg = get_dialect("postgres")
    assert pg.quote_ident("invoice_no") == '"invoice_no"'


def test_postgres_placeholder_is_percent_s() -> None:
    assert get_dialect("postgres").placeholder() == "%s"


def test_get_dialect_unknown_raises() -> None:
    with pytest.raises(ValueError):
        get_dialect("oracle")


def test_postgres_distinct_tuple_count_row_value() -> None:
    pg = get_dialect("postgres")
    assert pg.distinct_tuple_count(("invoice_no", "line_no"), "silver.t") == (
        "count(DISTINCT (invoice_no, line_no))"
    )


def test_postgres_columns_query_is_information_schema() -> None:
    pg = get_dialect("postgres")
    sql = pg.columns_query()
    assert "information_schema.columns" in sql
    assert "table_schema = %s" in sql
    assert "table_name = %s" in sql
    assert "ORDER BY ordinal_position" in sql


def test_sqlserver_count_where_is_count_case() -> None:
    d = get_dialect("sqlserver")
    # COUNT(CASE ...) — exact on empty input (returns 0, not NULL like SUM).
    assert d.count_where("x IS NULL") == "COUNT(CASE WHEN x IS NULL THEN 1 END)"


def test_sqlserver_distinct_tuple_is_derived_table() -> None:
    d = get_dialect("sqlserver")
    assert d.distinct_tuple_count(("a", "b"), "s.t") == (
        "(SELECT COUNT(*) FROM (SELECT DISTINCT a, b FROM s.t) AS sub)"
    )


def test_sqlserver_quote_ident_brackets() -> None:
    assert get_dialect("sqlserver").quote_ident("col") == "[col]"


def test_sqlserver_placeholder_is_qmark() -> None:
    assert get_dialect("sqlserver").placeholder() == "?"


def test_sqlserver_translate_params_percent_s_to_qmark() -> None:
    d = get_dialect("sqlserver")
    assert d.translate_params("WHERE a = %s AND b = %s") == "WHERE a = ? AND b = ?"


def test_sqlserver_is_text_type() -> None:
    d = get_dialect("sqlserver")
    assert d.is_text_type("varchar")
    assert d.is_text_type("NVARCHAR")
    assert not d.is_text_type("int")


def test_mysql_count_where_is_count_case() -> None:
    assert get_dialect("mysql").count_where("x IS NULL") == (
        "COUNT(CASE WHEN x IS NULL THEN 1 END)"
    )


def test_mysql_quote_ident_backtick() -> None:
    assert get_dialect("mysql").quote_ident("col") == "`col`"


def test_mysql_placeholder_is_percent_s() -> None:
    # mysql-connector paramstyle is pyformat (%s), same as psycopg2.
    assert get_dialect("mysql").placeholder() == "%s"


def test_mysql_translate_params_noop() -> None:
    d = get_dialect("mysql")
    assert d.translate_params("WHERE a = %s") == "WHERE a = %s"


def test_mysql_distinct_tuple_is_derived_table() -> None:
    assert get_dialect("mysql").distinct_tuple_count(("a", "b"), "s.t") == (
        "(SELECT COUNT(*) FROM (SELECT DISTINCT a, b FROM s.t) AS sub)"
    )
