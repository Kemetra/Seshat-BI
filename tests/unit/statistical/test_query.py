"""Restricted, bound, cross-dialect Gold query compilation."""

from __future__ import annotations

import pytest

from seshat.dialect import get_dialect
from seshat.statistical.providers.base import (
    Aggregate,
    DataRequest,
    Filter,
    Join,
)
from seshat.statistical.query import (
    QueryRefused,
    compile_count,
    compile_select,
)

pytestmark = pytest.mark.unit


def _request(
    *,
    table: str = "gold.fct_sales",
    filters: tuple[Filter, ...] = (),
    joins: tuple[Join, ...] = (),
) -> DataRequest:
    return DataRequest(
        table=table,
        columns=("sale_month", "net_amount", "channel"),
        logical_types=("date", "number", "category"),
        roles={"time": "sale_month", "response": "net_amount"},
        filters=filters,
        aggregates=(Aggregate("net_amount", "sum", "net_amount"),),
        group_by=("sale_month",),
        joins=joins,
        privacy_floor=5,
    )


@pytest.mark.parametrize("engine", ["postgres", "sqlserver", "mysql", "snowflake"])
def test_compiler_quotes_identifiers_and_binds_values(engine: str) -> None:
    compiled = compile_select(
        _request(filters=(Filter("channel", "eq", "Store"),)),
        get_dialect(engine),
    )

    assert "Store" not in compiled.sql
    assert compiled.params == ("Store",)
    assert compiled.sql.lstrip().upper().startswith("SELECT")
    assert compiled.output_columns == ("sale_month", "net_amount")
    assert len(compiled.digest) == 64


@pytest.mark.parametrize(
    "unsafe",
    [
        "gold.fact; DROP TABLE x",
        "gold.fact --",
        "silver.fact",
        "gold.fact.extra",
    ],
)
def test_compiler_refuses_unsafe_or_non_gold_relations(unsafe: str) -> None:
    with pytest.raises(QueryRefused):
        compile_select(_request(table=unsafe), get_dialect("postgres"))


def test_compiler_refuses_filter_column_outside_request() -> None:
    with pytest.raises(QueryRefused, match="approved columns"):
        compile_select(
            _request(filters=(Filter("private_value", "eq", "x"),)),
            get_dialect("postgres"),
        )


def test_compiler_refuses_unrestricted_operator() -> None:
    with pytest.raises(QueryRefused, match="operator"):
        compile_select(
            _request(filters=(Filter("channel", "raw_sql", "x"),)),
            get_dialect("postgres"),
        )


def test_compiler_refuses_raw_aggregate_expression() -> None:
    request = _request()
    request = DataRequest(
        table=request.table,
        columns=request.columns,
        logical_types=request.logical_types,
        roles=request.roles,
        aggregates=(Aggregate("net_amount); DROP TABLE x", "sum", "net_amount"),),
        group_by=request.group_by,
    )
    with pytest.raises(QueryRefused):
        compile_select(request, get_dialect("postgres"))


@pytest.mark.parametrize(
    ("left_column", "cardinality", "message"),
    (
        ("channel", "many_to_many", "cardinality"),
        ("channel", "one_to_many", "cardinality"),
        ("private_key", "many_to_one", "approved columns"),
    ),
)
def test_compiler_refuses_an_unapproved_join(
    left_column: str, cardinality: str, message: str
) -> None:
    join = Join(
        table="gold.dim_channel",
        left_column=left_column,
        right_column="channel",
        cardinality=cardinality,
    )
    with pytest.raises(QueryRefused, match=message):
        compile_select(_request(joins=(join,)), get_dialect("postgres"))


def test_compiler_supports_closed_filter_set_without_interpolation() -> None:
    filters = (
        Filter("channel", "in", ("Store", "Web")),
        Filter("net_amount", "gte", 0),
        Filter("channel", "is_not_null", None),
    )
    compiled = compile_select(_request(filters=filters), get_dialect("postgres"))

    assert compiled.params == ("Store", "Web", 0)
    assert all(value not in compiled.sql for value in ("Store", "Web"))
    assert " IS NOT NULL" in compiled.sql


def test_count_wraps_same_governed_select_and_parameters() -> None:
    request = _request(filters=(Filter("channel", "eq", "Store"),))
    selected = compile_select(request, get_dialect("postgres"))
    counted = compile_count(request, get_dialect("postgres"))

    assert counted.sql.startswith("SELECT COUNT(*)")
    assert selected.sql in counted.sql
    assert counted.params == selected.params
    assert counted.output_columns == ("row_count",)


def test_compiler_emits_one_select_without_comment_or_statement_tokens() -> None:
    compiled = compile_select(_request(), get_dialect("postgres"))
    assert compiled.sql.lstrip().upper().startswith("SELECT")
    assert all(token not in compiled.sql for token in (";", "--", "/*", "*/"))
