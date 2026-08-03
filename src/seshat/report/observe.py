"""Figures read from gold, compiled from the contracts that approve them.

Increment A took its numbers from a file. This module takes them from the
warehouse, and the shape it returns is byte-for-byte what :mod:`seshat.report
.bundle` already consumed -- which is why the seam was put at the bundle.

**Driver-free, like everything else that touches the DB here.** Every query runs
through the ``QueryRunner`` Protocol defined in :mod:`seshat.validate`, so this
module and its import path never import psycopg2. The static core stays
``pyyaml``-only, the real driver is built once in the CLI handler, and every rule
below is testable with an injected fake and no database present.

**It computes nothing it was not told to compute.** The SQL comes from the
contract's own ``definition`` and ``binds_to``. An aggregation outside the
recognized set, a filter op outside the recognized set, or a definition that is
neither family is REFUSED rather than approximated -- a dropped filter changes the
number without changing the citation, which is the most dangerous shape of wrong
a cited report can take.

**Every no-answer path returns ``None``**, which the bundle already renders as
``[PENDING LIVE DATA]``: no rows, a NULL scalar, an unparseable scalar, a zero
ratio denominator. A report that could not reach a number says so.

**A successful read is data, never an approval.** Nothing here writes a readiness
status or advances a stage.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from seshat.dialect import Dialect, get_dialect
from seshat.report.model import ReportError
from seshat.validate import QueryRunner

# The aggregate vocabulary, mirroring `value_proxy._AGG_SQL` so an aggregation
# name means the same thing to the live value check and to a report.
_AGG_SQL: dict[str, str] = {
    "sum": "sum({col})",
    "count": "count({col})",
    "distinct_count": "count(DISTINCT {col})",
    "average": "avg({col})",
    "count_rows": "count(*)",
}
# Aggregates that need a column; `count_rows` is the only one that does not.
_NEEDS_COLUMN = frozenset({"sum", "count", "distinct_count", "average"})

# The filter vocabulary, mirroring `metric_drift`'s recognized-op whitelist.
# Anything else refuses; there is no "unrecognized means no filter" path.
_FILTER_SQL: dict[str, str] = {
    "is_not_null": "{col} IS NOT NULL",
    "is_true": "{col} IS TRUE",
}

_RATIO_UNIT = "ratio"


@dataclass(frozen=True, slots=True)
class FigureRequest:
    """One figure a layout asked for, before its value is known."""

    visual_id: str
    contract_id: str
    unit_kind: str
    label: str | None = None


@dataclass(frozen=True, slots=True)
class CompiledQuery:
    """The SQL for one contract, and whether its row is a pair to divide."""

    sql: str
    is_ratio: bool


def compile_query(
    contract: Mapping[str, object], *, dialect: Dialect | None = None
) -> CompiledQuery:
    """Turn one approved contract into the statement that recomputes it."""
    dialect = dialect or get_dialect("postgres")
    definition = contract.get("definition")
    if not isinstance(definition, dict):
        raise ReportError(
            f"contract {_name(contract)!r} has no machine-readable definition, so "
            "there is nothing to recompute from"
        )
    table = _gold_table(contract, dialect)
    if "numerator" in definition and "denominator" in definition:
        return _ratio_query(definition, contract, table, dialect)
    if definition.get("kind") == "base":
        return _base_query(definition, contract, table, dialect)
    raise ReportError(
        f"contract {_name(contract)!r} definition is neither a base aggregate nor a "
        "ratio, so this module cannot recompute it without inventing a rule"
    )


def observe(
    runner: QueryRunner,
    requests: Sequence[FigureRequest],
    contracts: Mapping[str, Mapping[str, object]],
    *,
    dialect: Dialect | None = None,
) -> list[dict[str, object]]:
    """Resolve every requested figure against gold, in the bundle's own shape."""
    dialect = dialect or get_dialect("postgres")
    return [_observation(runner, request, contracts, dialect) for request in requests]


def _observation(
    runner: QueryRunner,
    request: FigureRequest,
    contracts: Mapping[str, Mapping[str, object]],
    dialect: Dialect,
) -> dict[str, object]:
    contract = _required_contract(request, contracts)
    _assert_groupable(request)
    query = compile_query(contract, dialect=dialect)
    _assert_unit_agrees(request, query)
    return {
        "visual_id": request.visual_id,
        "contract_id": request.contract_id,
        "metric": str(contract.get("name") or request.contract_id),
        "unit_kind": request.unit_kind,
        "label": request.label,
        "value": _value(runner, query),
    }


def _required_contract(
    request: FigureRequest, contracts: Mapping[str, Mapping[str, object]]
) -> Mapping[str, object]:
    contract = contracts.get(request.contract_id)
    if contract is None:
        raise ReportError(
            f"visual {request.visual_id!r} cites {request.contract_id!r}, for which "
            "no approved contract was supplied; an unattributed figure refuses"
        )
    return contract


def _assert_groupable(request: FigureRequest) -> None:
    """A labelled figure is a breakdown, and no governed artifact says how to group.

    The grouping column appears only in the binding map's prose table, which is a
    review artifact. Inferring it would make this module the place a breakdown is
    decided; extending the frozen binding-map schema to carry it is an owner
    action. So it refuses and names what is missing.
    """
    if request.label is None:
        return
    raise ReportError(
        f"visual {request.visual_id!r} asks for a breakdown labelled "
        f"{request.label!r}, but no approved artifact declares the grouping column. "
        "The binding map records groupings only in its prose table, which is not "
        "machine-readable. Supply this figure via --observations, or have the "
        "grouping added to the binding map and the design re-reviewed."
    )


def _assert_unit_agrees(request: FigureRequest, query: CompiledQuery) -> None:
    """The one unit fact that is derivable, checked rather than trusted.

    Whether a base aggregate renders as currency or as a count is NOT derivable --
    it depends on the source-map's declared unit, and how to treat an undeclared
    one is spec 103 FR-014, an open owner question. So only the ratio axis is
    asserted here.
    """
    if query.is_ratio and request.unit_kind != _RATIO_UNIT:
        raise ReportError(
            f"visual {request.visual_id!r} declares unit_kind "
            f"{request.unit_kind!r}, but {request.contract_id!r} is a ratio "
            "contract; rendering a rate as a total would misstate it by orders of "
            "magnitude"
        )
    if not query.is_ratio and request.unit_kind == _RATIO_UNIT:
        raise ReportError(
            f"visual {request.visual_id!r} declares unit_kind 'ratio', but "
            f"{request.contract_id!r} is not a ratio contract; its value would be "
            "multiplied by 100 and shown as a percentage"
        )


def _name(contract: Mapping[str, object]) -> str:
    return str(contract.get("name") or "<unnamed>")


def _gold_table(contract: Mapping[str, object], dialect: Dialect) -> str:
    binds_to = contract.get("binds_to")
    gold_table = binds_to.get("gold_table") if isinstance(binds_to, dict) else None
    if not gold_table:
        raise ReportError(
            f"contract {_name(contract)!r} has no binds_to.gold_table to read from"
        )
    return dialect.quote_qualified(
        str(gold_table), context="report gold table", min_parts=1, max_parts=2
    )


def _bound_column(contract: Mapping[str, object], dialect: Dialect) -> str:
    binds_to = contract.get("binds_to")
    columns = binds_to.get("columns") if isinstance(binds_to, dict) else None
    if not isinstance(columns, list) or not columns:
        raise ReportError(
            f"contract {_name(contract)!r} needs a bound column in "
            "binds_to.columns to aggregate"
        )
    return dialect.quote_ident(str(columns[0]), context="report gold column")


def _aggregation_name(
    definition: Mapping[str, object], contract: Mapping[str, object]
) -> str:
    aggregation = definition.get("aggregation")
    if str(aggregation) not in _AGG_SQL:
        raise ReportError(
            f"contract {_name(contract)!r} aggregation {aggregation!r} is outside the "
            f"recognized set {sorted(_AGG_SQL)}"
        )
    return str(aggregation)


def _aggregate(
    definition: Mapping[str, object], contract: Mapping[str, object], dialect: Dialect
) -> str:
    aggregation = _aggregation_name(definition, contract)
    template = _AGG_SQL[aggregation]
    if aggregation not in _NEEDS_COLUMN:
        return template
    return template.format(col=_bound_column(contract, dialect))


def _predicate(
    raw: object, contract: Mapping[str, object], dialect: Dialect
) -> str | None:
    """One filter entry as a SQL predicate, or None when there is no filter list."""
    if not isinstance(raw, list) or not raw:
        return None
    predicates = [_one_predicate(entry, contract, dialect) for entry in raw]
    return " AND ".join(predicates)


def _one_predicate(
    entry: object, contract: Mapping[str, object], dialect: Dialect
) -> str:
    if not isinstance(entry, dict):
        raise ReportError(f"contract {_name(contract)!r} has a non-mapping filter")
    op = entry.get("op")
    template = _FILTER_SQL.get(str(op))
    if template is None:
        raise ReportError(
            f"contract {_name(contract)!r} filter op {op!r} is outside the recognized "
            f"set {sorted(_FILTER_SQL)}; refusing rather than dropping it, because a "
            "dropped filter changes the number without changing the citation"
        )
    column = entry.get("column")
    if not column:
        raise ReportError(f"contract {_name(contract)!r} filter names no column")
    quoted = dialect.quote_ident(str(column), context="report filter column")
    return template.format(col=quoted)


def _base_query(
    definition: Mapping[str, object],
    contract: Mapping[str, object],
    table: str,
    dialect: Dialect,
) -> CompiledQuery:
    aggregate = _aggregate(definition, contract, dialect)
    where = _predicate(definition.get("filter"), contract, dialect)
    clause = f" WHERE {where}" if where else ""
    return CompiledQuery(sql=f"SELECT {aggregate} FROM {table}{clause}", is_ratio=False)


def _ratio_query(
    definition: Mapping[str, object],
    contract: Mapping[str, object],
    table: str,
    dialect: Dialect,
) -> CompiledQuery:
    """Both counts in ONE statement.

    `value_proxy` runs the two sides as separate queries, which is correct for a
    tolerance check. A published figure is stricter: two statements can straddle a
    write and yield a ratio that was never true of any single state of the table.
    """
    numerator = _side(definition, "numerator", contract, dialect)
    denominator = _side(definition, "denominator", contract, dialect)
    return CompiledQuery(
        sql=f"SELECT {numerator}, {denominator} FROM {table}", is_ratio=True
    )


def _side(
    definition: Mapping[str, object],
    which: str,
    contract: Mapping[str, object],
    dialect: Dialect,
) -> str:
    """One side of a ratio as a single conditional aggregate.

    Both count-over-count rates (DiscountedTransactionRate) and
    sum-over-count averages (AvgTransactionValue) are expressed this way, so a
    ratio whose sides aggregate differently still resolves in one statement.
    """
    side = definition.get(which)
    if not isinstance(side, dict):
        raise ReportError(f"contract {_name(contract)!r} {which} is not a mapping")
    aggregation = _aggregation_name(side, contract)
    predicate = _predicate(side.get("filter"), contract, dialect)
    if aggregation == "count_rows":
        return "count(*)" if predicate is None else dialect.count_where(predicate)
    return _AGG_SQL[aggregation].format(
        col=_restricted(_bound_column(contract, dialect), predicate)
    )


def _restricted(column: str, predicate: str | None) -> str:
    """The column, or the column only for rows matching the predicate.

    A CASE expression rather than each engine's FILTER syntax, because it is
    portable across every dialect here and means the same thing: a row failing the
    predicate contributes nothing, not zero.
    """
    if predicate is None:
        return column
    return f"CASE WHEN {predicate} THEN {column} END"


def _value(runner: QueryRunner, query: CompiledQuery) -> Decimal | None:
    rows = runner.run(query.sql)
    if not rows or not rows[0]:
        return None
    if query.is_ratio:
        return _ratio_value(rows[0])
    return _decimal(rows[0][0])


def _ratio_value(row: Sequence[object]) -> Decimal | None:
    if len(row) < 2:
        return None
    numerator = _decimal(row[0])
    denominator = _decimal(row[1])
    if not _divisible(numerator, denominator):
        return None
    return numerator / denominator  # type: ignore[operator]


def _divisible(numerator: Decimal | None, denominator: Decimal | None) -> bool:
    """Both sides had to arrive, and a zero denominator is pending rather than a crash.

    A rate over no eligible rows is genuinely unknown -- not zero, which would state
    that none of them qualified.
    """
    if numerator is None or denominator is None:
        return False
    return denominator != 0


def _decimal(value: object) -> Decimal | None:
    """Exact-parse via the string form, so a driver's float never becomes a figure."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
