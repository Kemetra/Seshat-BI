"""Closed compiler for restricted, parameter-bound Gold SELECT queries."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from seshat.dialect import Dialect

from .contracts import Blocker
from .providers.base import Aggregate, DataRequest, Filter, Join

FILTER_OPS = frozenset(
    {
        "eq",
        "ne",
        "lt",
        "lte",
        "gt",
        "gte",
        "in",
        "is_null",
        "is_not_null",
        "is_true",
        "is_false",
    }
)
AGGREGATIONS = frozenset(
    {"sum", "count", "count_rows", "distinct_count", "average", "min", "max"}
)
JOIN_CARDINALITIES = frozenset({"many_to_one", "one_to_one"})
_FORBIDDEN_SQL = (";", "--", "/*", "*/")


@dataclass(frozen=True, slots=True)
class CompiledQuery:
    sql: str
    params: tuple[object, ...]
    output_columns: tuple[str, ...]
    digest: str


class QueryRefused(ValueError):
    def __init__(self, blocker: Blocker) -> None:
        super().__init__(blocker.message)
        self.blocker = blocker


def _refuse(message: str, recovery: str) -> QueryRefused:
    return QueryRefused(
        Blocker(
            code="STAT_QUERY_REFUSED",
            message=message,
            recovery=recovery,
        )
    )


def _quoted_identifier(name: str, dialect: Dialect, context: str) -> str:
    try:
        return dialect.quote_ident(name, context=context)
    except (TypeError, ValueError) as exc:
        raise _refuse(
            f"Unsafe {context} was refused.",
            "Use a policy-approved simple SQL identifier.",
        ) from exc


def _quoted_gold_table(name: str | None, dialect: Dialect, context: str) -> str:
    if not isinstance(name, str):
        raise _refuse(
            f"{context} is missing.",
            "Bind the request to one policy-approved Gold relation.",
        )
    parts = name.split(".")
    if len(parts) != 2 or parts[0].casefold() != "gold":
        raise _refuse(
            f"{context} must be an exact gold.<relation> binding.",
            "Use a policy-approved Gold relation without expressions.",
        )
    try:
        return dialect.quote_qualified(name, context=context, min_parts=2, max_parts=2)
    except (TypeError, ValueError) as exc:
        raise _refuse(
            f"Unsafe {context} was refused.",
            "Use a policy-approved Gold relation without SQL tokens.",
        ) from exc


def _approved_identifier(
    name: str,
    approved: set[str],
    dialect: Dialect,
    context: str,
) -> str:
    if name not in approved:
        raise _refuse(
            f"{context} is outside the request's approved columns.",
            "Use only columns projected by policy preflight.",
        )
    return _quoted_identifier(name, dialect, context)


_SCALAR_OPS = {
    "eq": "=",
    "ne": "<>",
    "lt": "<",
    "lte": "<=",
    "gt": ">",
    "gte": ">=",
}

_NULL_PREDICATES = {"is_null": "IS NULL", "is_not_null": "IS NOT NULL"}

_AGGREGATE_FUNCTIONS = {
    "sum": "SUM",
    "count": "COUNT",
    "distinct_count": "COUNT",
    "average": "AVG",
    "min": "MIN",
    "max": "MAX",
}


def _assert_valueless(item: Filter, subject: str) -> None:
    if item.value is not None:
        raise _refuse(
            f"Filter operator {item.operator!r} does not accept a value.",
            f"Remove the value from the {subject} predicate.",
        )


def _compile_membership(
    item: Filter, column: str, dialect: Dialect
) -> tuple[str, tuple[object, ...]]:
    if not isinstance(item.value, tuple) or not item.value:
        raise _refuse(
            "The 'in' filter requires a non-empty tuple of bound values.",
            "Provide one or more typed values.",
        )
    placeholders = ", ".join(dialect.placeholder() for _ in item.value)
    return f"{column} IN ({placeholders})", tuple(item.value)


def _compile_scalar(
    item: Filter, column: str, dialect: Dialect
) -> tuple[str, tuple[object, ...]]:
    if item.value is None or isinstance(item.value, tuple):
        raise _refuse(
            f"Filter operator {item.operator!r} requires one bound value.",
            "Provide one scalar typed value.",
        )
    operator = _SCALAR_OPS[item.operator]
    return f"{column} {operator} {dialect.placeholder()}", (item.value,)


def _compile_filter(
    item: Filter,
    approved: set[str],
    dialect: Dialect,
) -> tuple[str, tuple[object, ...]]:
    """Compile one closed predicate with every value parameter-bound."""

    if item.operator not in FILTER_OPS:
        raise _refuse(
            f"Filter operator {item.operator!r} is not allowed.",
            "Use one of the closed statistical filter operators.",
        )
    column = _approved_identifier(item.column, approved, dialect, "filter column")
    null_suffix = _NULL_PREDICATES.get(item.operator)
    if null_suffix is not None:
        _assert_valueless(item, "null")
        return f"{column} {null_suffix}", ()
    if item.operator in {"is_true", "is_false"}:
        _assert_valueless(item, "boolean")
        return f"{column} = {dialect.placeholder()}", (item.operator == "is_true",)
    if item.operator == "in":
        return _compile_membership(item, column, dialect)
    return _compile_scalar(item, column, dialect)


def _aggregate_expression(item: Aggregate, approved: set[str], dialect: Dialect) -> str:
    """Render one closed aggregation over an approved source column."""

    if item.function == "count_rows":
        if item.source_column is not None:
            raise _refuse(
                "count_rows cannot contain a source expression.",
                "Use source_column: null for count_rows.",
            )
        return "COUNT(*)"
    if not isinstance(item.source_column, str):
        raise _refuse(
            f"Aggregation {item.function!r} requires a source column.",
            "Use one policy-approved source column.",
        )
    source = _approved_identifier(
        item.source_column, approved, dialect, "aggregate source column"
    )
    distinct = "DISTINCT " if item.function == "distinct_count" else ""
    return f"{_AGGREGATE_FUNCTIONS[item.function]}({distinct}{source})"


def _compile_aggregate(
    item: Aggregate,
    approved: set[str],
    dialect: Dialect,
) -> tuple[str, str]:
    if item.function not in AGGREGATIONS:
        raise _refuse(
            f"Aggregation {item.function!r} is not allowed.",
            "Use one of the closed statistical aggregations.",
        )
    output = _approved_identifier(
        item.output_column, approved, dialect, "aggregate output column"
    )
    expression = _aggregate_expression(item, approved, dialect)
    return f"{expression} AS {output}", item.output_column


def _compile_join(
    item: Join,
    main_table: str,
    approved: set[str],
    dialect: Dialect,
) -> str:
    if item.cardinality not in JOIN_CARDINALITIES:
        raise _refuse(
            f"Join cardinality {item.cardinality!r} is not allowed.",
            "Use an approved many_to_one or one_to_one relationship.",
        )
    table = _quoted_gold_table(item.table, dialect, "join table")
    left = _approved_identifier(item.left_column, approved, dialect, "join left column")
    right = _approved_identifier(
        item.right_column, approved, dialect, "join right column"
    )
    return f"JOIN {table} ON {main_table}.{left} = {table}.{right}"


def _digest(
    sql: str, params: tuple[object, ...], output_columns: tuple[str, ...]
) -> str:
    normalized = json.dumps(
        [sql, params, output_columns],
        default=str,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def _compiled(
    sql: str, params: tuple[object, ...], output_columns: tuple[str, ...]
) -> CompiledQuery:
    if not sql.lstrip().upper().startswith("SELECT") or any(
        token in sql for token in _FORBIDDEN_SQL
    ):
        raise _refuse(
            "The compiled query violated the single-SELECT boundary.",
            "Use only the closed query compiler.",
        )
    return CompiledQuery(
        sql=sql,
        params=params,
        output_columns=output_columns,
        digest=_digest(sql, params, output_columns),
    )


def _projection(
    request: DataRequest, table: str, approved: set[str], dialect: Dialect
) -> tuple[list[str], list[str], list[str]]:
    """Return the SELECT list, its output names, and the GROUP BY list."""

    group_sql = [
        _approved_identifier(column, approved, dialect, "group-by column")
        for column in request.group_by
    ]
    if not request.aggregates:
        selections = [
            (
                f"{table}."
                f"{_approved_identifier(column, approved, dialect, 'selected column')}"
            )
            for column in request.columns
        ]
        return selections, list(request.columns), group_sql
    selections = list(group_sql)
    output_columns = list(request.group_by)
    for aggregate in request.aggregates:
        selection, output = _compile_aggregate(aggregate, approved, dialect)
        selections.append(selection)
        output_columns.append(output)
    return selections, output_columns, group_sql


def _predicates(
    request: DataRequest, approved: set[str], dialect: Dialect
) -> tuple[list[str], list[object]]:
    predicates: list[str] = []
    params: list[object] = []
    for item in request.filters:
        predicate, values = _compile_filter(item, approved, dialect)
        predicates.append(predicate)
        params.extend(values)
    return predicates, params


def compile_select(request: DataRequest, dialect: Dialect) -> CompiledQuery:
    """Compile one restricted Gold SELECT with all values parameter-bound."""

    table = _quoted_gold_table(request.table, dialect, "statistical table")
    approved = set(request.columns)
    if not approved:
        raise _refuse(
            "The statistical request has no approved columns.",
            "Request at least one approved role column.",
        )
    selections, output_columns, group_sql = _projection(
        request, table, approved, dialect
    )
    if len(set(output_columns)) != len(output_columns):
        raise _refuse(
            "The compiled output columns are not unique.",
            "Use distinct group and aggregate output names.",
        )
    joins = [_compile_join(item, table, approved, dialect) for item in request.joins]
    predicates, params = _predicates(request, approved, dialect)
    clauses = [f"SELECT {', '.join(selections)} FROM {table}", *joins]
    if predicates:
        clauses.append("WHERE " + " AND ".join(predicates))
    if group_sql:
        clauses.append("GROUP BY " + ", ".join(group_sql))
    return _compiled(" ".join(clauses), tuple(params), tuple(output_columns))


def compile_count(request: DataRequest, dialect: Dialect) -> CompiledQuery:
    """Count the exact rows the governed select would return."""

    selected = compile_select(request, dialect)
    alias = _quoted_identifier("statistical_rows", dialect, "count alias")
    output = _quoted_identifier("row_count", dialect, "count output")
    sql = f"SELECT COUNT(*) AS {output} FROM ({selected.sql}) AS {alias}"
    return _compiled(sql, selected.params, ("row_count",))
