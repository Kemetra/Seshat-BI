"""Coherence checks between metric definitions and governed table bindings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

__all__ = ["definition_binding_errors"]


def _source_table(side: Mapping[str, object]) -> str | None:
    source = side.get("source")
    if not isinstance(source, Mapping):
        return None
    table = source.get("table")
    if not isinstance(table, str) or not table.strip():
        return None
    return table.strip()


def _binding_error(name: str, value: object) -> str | None:
    if not isinstance(value, Mapping):
        return f"two-table ratio requires {name}"
    table = value.get("gold_table")
    if not isinstance(table, str) or not table.strip().startswith("gold."):
        return f"{name}.gold_table must be a non-empty gold.* string"
    columns = value.get("columns")
    if (
        not isinstance(columns, list)
        or not columns
        or not all(isinstance(item, str) and item.strip() for item in columns)
    ):
        return f"{name}.columns must be a non-empty list of strings"
    pii_sensitive = value.get("pii_sensitive")
    if pii_sensitive is not None and not isinstance(pii_sensitive, bool):
        return f"{name}.pii_sensitive must be boolean"
    return None


def _side_columns(
    label: str, side: Mapping[str, object]
) -> tuple[tuple[str, ...] | None, str | None]:
    columns: list[str] = []
    source = side.get("source")
    if not isinstance(source, Mapping):
        return None, f"{label}.source must be a mapping"
    source_column = source.get("column")
    if source_column is not None:
        if not isinstance(source_column, str) or not source_column.strip():
            return None, f"{label} source.column must be a non-empty string"
        columns.append(source_column.strip())

    filters = side.get("filter")
    if filters is None:
        return tuple(columns), None
    if not isinstance(filters, list):
        return None, f"{label}.filter must be a list"
    for entry in filters:
        if not isinstance(entry, Mapping):
            return None, f"{label} filter entries must be mappings"
        column = entry.get("column")
        if not isinstance(column, str) or not column.strip():
            return None, f"{label} filter columns must be non-empty strings"
        columns.append(column.strip())
    return tuple(columns), None


def _comparison_bindings(
    contract: Mapping[str, object],
) -> tuple[tuple[Mapping[str, object], Mapping[str, object]] | None, str | None]:
    binds_to = contract.get("binds_to")
    compares_to = contract.get("compares_to")
    for name, binding in (("binds_to", binds_to), ("compares_to", compares_to)):
        error = _binding_error(name, binding)
        if error is not None:
            return None, error
    return (
        cast(Mapping[str, object], binds_to),
        cast(Mapping[str, object], compares_to),
    ), None


def _ratio_source_tables(
    numerator: Mapping[str, object], denominator: Mapping[str, object]
) -> tuple[tuple[str, str] | None, str | None]:
    numerator_table = _source_table(numerator)
    if numerator_table is None or not numerator_table.startswith("gold."):
        return None, "numerator source.table must be a non-empty gold.* string"
    denominator_table = _source_table(denominator)
    if denominator_table is None or not denominator_table.startswith("gold."):
        return None, "denominator source.table must be a non-empty gold.* string"
    return (numerator_table, denominator_table), None


def _table_alignment_errors(
    numerator_table: str,
    denominator_table: str,
    binds_to: Mapping[str, object],
    compares_to: Mapping[str, object],
) -> tuple[str, ...]:
    errors: list[str] = []
    if numerator_table != str(binds_to["gold_table"]).strip():
        errors.append("numerator source table must equal binds_to.gold_table")
    if denominator_table != str(compares_to["gold_table"]).strip():
        errors.append("denominator source table must equal compares_to.gold_table")
    return tuple(errors)


def _side_binding_errors(
    label: str,
    side: Mapping[str, object],
    binding_name: str,
    binding: Mapping[str, object],
) -> tuple[tuple[str, ...], str | None]:
    used_columns, error = _side_columns(label, side)
    if error is not None:
        return (), error
    assert used_columns is not None
    bound_columns = {str(item).strip() for item in binding["columns"]}
    return (
        tuple(
            f"{label} column {column!r} is absent from {binding_name}.columns"
            for column in used_columns
            if column not in bound_columns
        ),
        None,
    )


def _column_binding_errors(
    numerator: Mapping[str, object],
    denominator: Mapping[str, object],
    binds_to: Mapping[str, object],
    compares_to: Mapping[str, object],
) -> tuple[tuple[str, ...], str | None]:
    numerator_errors, error = _side_binding_errors(
        "numerator", numerator, "binds_to", binds_to
    )
    if error is not None:
        return (), error
    denominator_errors, error = _side_binding_errors(
        "denominator", denominator, "compares_to", compares_to
    )
    if error is not None:
        return (), error
    return numerator_errors + denominator_errors, None


def _validate_two_table_ratio(
    contract: Mapping[str, object],
    numerator: Mapping[str, object],
    denominator: Mapping[str, object],
) -> tuple[str, ...]:
    bindings, error = _comparison_bindings(contract)
    if error is not None:
        return (error,)
    assert bindings is not None
    binds_to, compares_to = bindings

    source_tables, error = _ratio_source_tables(numerator, denominator)
    if error is not None:
        return (error,)
    assert source_tables is not None
    numerator_table, denominator_table = source_tables

    errors = _table_alignment_errors(
        numerator_table, denominator_table, binds_to, compares_to
    )
    column_errors, error = _column_binding_errors(
        numerator, denominator, binds_to, compares_to
    )
    if error is not None:
        return (error,)
    return errors + column_errors


def definition_binding_errors(
    contract: Mapping[str, object],
) -> tuple[str, ...]:
    """Return deterministic two-table definition/binding coherence errors.

    Legacy one-table contracts are intentionally outside this validator's scope;
    their existing definition validation and generated output remain unchanged.
    """
    definition = contract.get("definition")
    if not isinstance(definition, Mapping):
        return ()
    numerator = definition.get("numerator")
    denominator = definition.get("denominator")
    compares_to = contract.get("compares_to")
    if not isinstance(numerator, Mapping) or not isinstance(denominator, Mapping):
        return (
            ("compares_to requires a ratio numerator and denominator",)
            if compares_to is not None
            else ()
        )
    numerator_table = _source_table(numerator)
    denominator_table = _source_table(denominator)
    is_two_table = compares_to is not None or (
        numerator_table is not None
        and denominator_table is not None
        and numerator_table != denominator_table
    )
    if not is_two_table:
        return ()
    if definition.get("kind") != "ratio":
        return ("two-table comparison definition.kind must be ratio",)
    return _validate_two_table_ratio(contract, numerator, denominator)
