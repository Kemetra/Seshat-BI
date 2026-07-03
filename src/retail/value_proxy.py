"""L4 value proxy -- does the live DB still return the contract's APPROVED value?

This is the LIVE counterpart to L3's static drift check (`metric_drift.py`). L3
proves a DIVIDE measure's denominator filter-set matches the contract (structure);
L4 re-computes the measure's aggregate against the live gold table and asserts it
still equals the contract's approved `expected_value`, within tolerance (value).

    L1 -- DAX parses (form)
    L2 -- DAX is best-practice (hygiene)        D1-D11
    L3 -- denominator filter-set matches         metric_drift.py
    L4 -- the live aggregate matches the value   THIS MODULE

L3 can pass while the data silently drifts (rows dropped, a join changed): the
filter-set is right but the number is wrong. L4 catches that.

DRIVER-FREE (mirrors validate.py): every check runs against the `QueryRunner`
Protocol, so THIS module and its import path NEVER import psycopg2. The static
core's `dependencies = []` invariant is preserved; tests inject a fake runner; the
real psycopg2 runner is built lazily in the CLI's `value-check` handler, never here.

Values are Decimal-exact: the contract carries them as quoted strings so YAML never
yields a fragile float; comparison is `Decimal(str(...))` (the same discipline
validate.py uses to reconcile to the penny).

Authority boundary: a passing L4 does NOT move a readiness stage to `pass` (a named
human does -- ADR-0008 / Principle V). A failing L4 surfaces a regression; it never
edits the model or the contract, and emits no numeric confidence score (hard rule #9).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from .core import Finding, Severity
from .dialect import Dialect, get_dialect
from .validate import QueryRunner  # the driver-free DB seam (Protocol)

__all__ = ["ExpectedValue", "parse_expected_value", "check_expected_value"]

_RULE_ID = "V-L4"

# Single aggregate name -> the SQL aggregate function. `ratio` is handled separately
# (it recomputes numerator-count / denominator-count). Mirrors the L3 vocabulary
# (metric_drift._BASE_AGG_FUNC) so agg names have one source of truth.
_AGG_SQL: dict[str, str] = {
    "sum": "sum",
    "count": "count",
    "distinct_count": "count(DISTINCT {col})",
    "average": "avg",
    "count_rows": "count(*)",
}


@dataclass(frozen=True)
class ExpectedValue:
    """The L4 check target for one measure, parsed from a contract's
    ``definition.expected_value`` block plus its ``binds_to``.

    Attributes:
        value: the approved aggregate (Decimal-exact).
        tolerance_abs: absolute tolerance (Decimal); 0 => must match to the penny.
        aggregation: how to recompute -- one of _AGG_SQL keys, or "ratio".
        column: the gold column to aggregate (None for count_rows / ratio).
        gold_table: the qualified gold table (from binds_to.gold_table).
        numerator_count_sql_filter: for aggregation=="ratio" -- the WHERE predicate
            (already SQL, identifiers quoted) counting the numerator rows.
        denominator_count_sql_filter: likewise for the denominator rows.
    """

    value: Decimal
    tolerance_abs: Decimal
    aggregation: str
    column: str | None
    gold_table: str
    numerator_count_sql_filter: str | None = None
    denominator_count_sql_filter: str | None = None


def _decimal(raw: object, *, field: str) -> Decimal:
    """Decimal-parse from the STRING form (avoids binary-float fragility). Raises
    ValueError with the field name on a non-numeric value."""
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"expected_value.{field} is not numeric: {raw!r}") from exc


def parse_expected_value(
    definition: dict[str, Any] | None, binds_to: dict[str, Any] | None
) -> ExpectedValue | None:
    """Parse a contract's ``definition.expected_value`` block into an ExpectedValue.

    Returns None when there is no block (the caller SKIPS -- nothing to check).
    Raises ValueError (fail-closed) on a malformed block: unknown aggregation,
    missing column for a column-aggregate, non-numeric value/tolerance, or a missing
    gold_table. A malformed check is a defect, never a silent skip.
    """
    if not definition:
        return None
    block = definition.get("expected_value")
    if block is None:
        return None
    if not isinstance(block, dict):
        raise ValueError("expected_value must be a mapping")

    aggregation = block.get("aggregation")
    if aggregation not in _AGG_SQL and aggregation != "ratio":
        raise ValueError(
            f"expected_value.aggregation {aggregation!r} not recognized "
            f"(one of {sorted(_AGG_SQL)} or 'ratio')"
        )

    value = _decimal(block.get("value"), field="value")
    tolerance_abs = _decimal(block.get("tolerance_abs", "0"), field="tolerance_abs")

    gold_table = (binds_to or {}).get("gold_table")
    if not gold_table:
        raise ValueError(
            "expected_value needs binds_to.gold_table to recompute against"
        )

    # A column is required for the column aggregates (sum/average/count/distinct_count)
    # but NOT for count_rows or ratio.
    column = block.get("column")
    needs_column = aggregation in ("sum", "average", "count", "distinct_count")
    if needs_column and not column:
        raise ValueError(
            f"expected_value.aggregation {aggregation!r} requires a `column`"
        )

    return ExpectedValue(
        value=value,
        tolerance_abs=tolerance_abs,
        aggregation=aggregation,
        column=str(column) if column else None,
        gold_table=str(gold_table),
    )


def _to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _aggregate_sql(expected: ExpectedValue, dialect: Dialect) -> str:
    """Build the single-aggregate SELECT for a non-ratio expected value.

    Quotes the gold table and column via the dialect's identifier helpers (raises
    ValueError on an unsafe identifier BEFORE any SQL is built; validation lives
    inside the dialect, same hardening as before).
    """
    table = dialect.quote_qualified(
        expected.gold_table, context="L4 gold table", min_parts=1, max_parts=2
    )
    template = _AGG_SQL[expected.aggregation]
    if expected.aggregation == "count_rows":
        agg = template  # count(*)
    else:
        col = dialect.quote_ident(expected.column, context="L4 column")
        agg = template.format(col=col) if "{col}" in template else f"{template}({col})"
    return f"SELECT {agg} FROM {table}"


def _error(name: str, message: str, locator: str) -> Finding:
    return Finding(
        rule_id=_RULE_ID, severity=Severity.ERROR, message=message, locator=locator
    )


def _check_single(
    runner: QueryRunner, name: str, expected: ExpectedValue, *, dialect: Dialect
) -> list[Finding]:
    sql = _aggregate_sql(expected, dialect)  # may raise ValueError (unsafe identifier)
    rows = runner.run(sql)
    if not rows or not rows[0]:
        return [_error(name, f"{name}: live aggregate returned no rows (L4)", name)]
    actual = _to_decimal(rows[0][0])
    if actual is None:
        return [
            _error(
                name,
                f"{name}: live aggregate is NULL/unparseable "
                f"({rows[0][0]!r}) -- cannot verify the approved value (L4)",
                name,
            )
        ]
    gap = abs(actual - expected.value)
    if gap > expected.tolerance_abs:
        return [
            _error(
                name,
                f"{name}: live value {actual} != approved {expected.value} "
                f"(gap {gap} > tolerance {expected.tolerance_abs}) "
                "-- value regression (L4)",
                name,
            )
        ]
    return []


def _count(
    runner: QueryRunner, table: str, where_sql: str, *, dialect: Dialect
) -> int | None:
    del dialect  # unused today: the count(*) ... WHERE ... form is engine-portable
    rows = runner.run(f"SELECT count(*) FROM {table} WHERE {where_sql}")
    if not rows or not rows[0] or rows[0][0] is None:
        return None
    try:
        return int(rows[0][0])
    except (TypeError, ValueError):
        return None


def _check_ratio(
    runner: QueryRunner, name: str, expected: ExpectedValue, *, dialect: Dialect
) -> list[Finding]:
    table = dialect.quote_qualified(
        expected.gold_table, context="L4 gold table", min_parts=1, max_parts=2
    )
    num_filter = expected.numerator_count_sql_filter
    den_filter = expected.denominator_count_sql_filter
    if not num_filter or not den_filter:
        return [
            _error(
                name,
                f"{name}: ratio expected_value needs numerator + denominator "
                "filters to recompute (L4)",
                name,
            )
        ]
    numerator = _count(runner, table, num_filter, dialect=dialect)
    denominator = _count(runner, table, den_filter, dialect=dialect)
    if numerator is None or denominator is None:
        return [
            _error(
                name,
                f"{name}: a ratio side count is NULL/unparseable "
                f"(num={numerator}, den={denominator}) (L4)",
                name,
            )
        ]
    if denominator == 0:
        return [
            _error(
                name,
                f"{name}: ratio denominator is 0 -- cannot compute the rate (L4)",
                name,
            )
        ]
    actual = Decimal(numerator) / Decimal(denominator)
    gap = abs(actual - expected.value)
    if gap > expected.tolerance_abs:
        return [
            _error(
                name,
                f"{name}: live ratio {actual} != approved {expected.value} "
                f"(gap {gap} > tolerance {expected.tolerance_abs}) "
                "-- value regression (L4)",
                name,
            )
        ]
    return []


def check_expected_value(
    runner: QueryRunner,
    name: str,
    expected: ExpectedValue,
    *,
    dialect: Dialect | None = None,
) -> Iterable[Finding]:
    """Verify one measure's live aggregate against its approved value.

    Within tolerance => no finding (pass). Outside tolerance, or no rows / NULL /
    unparseable / zero ratio denominator => one V-L4 ERROR (a proven regression).
    Raises ValueError (before any query) if the contract names an unsafe identifier.

    ``dialect`` defaults to Postgres (the only engine wired up today); passing it
    explicitly is how a future engine's value-check would opt in.
    """
    dialect = dialect or get_dialect("postgres")
    if expected.aggregation == "ratio":
        return _check_ratio(runner, name, expected, dialect=dialect)
    return _check_single(runner, name, expected, dialect=dialect)
