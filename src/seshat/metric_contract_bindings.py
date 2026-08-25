"""Coherence checks between metric definitions and governed table bindings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

__all__ = ["definition_binding_errors"]

_FILTER_OPERATORS = frozenset({"is_not_null", "is_true"})


def _valid_identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _valid_gold_table(value: object) -> bool:
    return (
        _valid_identifier(value)
        and isinstance(value, str)
        and value.startswith("gold.")
        and len(value) > len("gold.")
    )


def _source_table(side: Mapping[str, object]) -> str | None:
    source = side.get("source")
    if not isinstance(source, Mapping):
        return None
    table = source.get("table")
    if not _valid_identifier(table):
        return None
    return cast(str, table)


def _gold_table_error(name: str, binding: Mapping[str, object]) -> str | None:
    table = binding.get("gold_table")
    if _valid_gold_table(table):
        return None
    return f"{name}.gold_table must be a non-empty gold.* string"


def _non_empty_string(value: object) -> bool:
    return _valid_identifier(value)


def _valid_columns(value: object) -> bool:
    if not isinstance(value, list):
        return False
    if not value:
        return False
    return all(map(_non_empty_string, value))


def _columns_error(name: str, binding: Mapping[str, object]) -> str | None:
    columns = binding.get("columns")
    if _valid_columns(columns):
        return None
    return f"{name}.columns must be a non-empty list of strings"


def _pii_sensitive_error(name: str, binding: Mapping[str, object]) -> str | None:
    pii_sensitive = binding.get("pii_sensitive")
    if pii_sensitive is None or isinstance(pii_sensitive, bool):
        return None
    return f"{name}.pii_sensitive must be boolean"


def _binding_error(name: str, value: object) -> str | None:
    if not isinstance(value, Mapping):
        return f"two-table ratio requires {name}"
    binding = cast(Mapping[str, object], value)
    errors = (
        _gold_table_error(name, binding),
        _columns_error(name, binding),
        _pii_sensitive_error(name, binding),
    )
    return next((error for error in errors if error is not None), None)


def _source_columns(
    label: str, side: Mapping[str, object]
) -> tuple[tuple[str, ...], str | None]:
    source = side.get("source")
    if not isinstance(source, Mapping):
        return (), f"{label}.source must be a mapping"
    source_column = source.get("column")
    if source_column is None:
        return (), None
    if not isinstance(source_column, str) or not source_column.strip():
        return (), f"{label} source.column must be a non-empty string"
    if source_column != source_column.strip():
        return (), f"{label} source.column must not contain surrounding whitespace"
    return (source_column,), None


def _filter_column(label: str, entry: object) -> tuple[str | None, str | None]:
    if not isinstance(entry, Mapping):
        return None, f"{label} filter entries must be mappings"
    column = entry.get("column")
    if not isinstance(column, str) or not column.strip():
        return None, f"{label} filter columns must be non-empty strings"
    if column != column.strip():
        return None, f"{label} filter column must not contain surrounding whitespace"
    operator = entry.get("op")
    if not isinstance(operator, str) or operator not in _FILTER_OPERATORS:
        return None, f"{label} filter op must be a supported string"
    return column, None


def _filter_columns(label: str, filters: object) -> tuple[tuple[str, ...], str | None]:
    if filters is None:
        return (), None
    if not isinstance(filters, list):
        return (), f"{label}.filter must be a list"
    columns: list[str] = []
    for entry in filters:
        column, error = _filter_column(label, entry)
        if error is not None:
            return (), error
        assert column is not None
        columns.append(column)
    return tuple(columns), None


def _side_columns(
    label: str, side: Mapping[str, object]
) -> tuple[tuple[str, ...] | None, str | None]:
    source_columns, error = _source_columns(label, side)
    if error is not None:
        return None, error
    filter_columns, error = _filter_columns(label, side.get("filter"))
    if error is not None:
        return None, error
    return source_columns + filter_columns, None


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
    if not _valid_gold_table(numerator_table):
        return None, "numerator source.table must be a non-empty gold.* string"
    denominator_table = _source_table(denominator)
    if not _valid_gold_table(denominator_table):
        return None, "denominator source.table must be a non-empty gold.* string"
    return cast(tuple[str, str], (numerator_table, denominator_table)), None


def _table_alignment_errors(
    numerator_table: str,
    denominator_table: str,
    binds_to: Mapping[str, object],
    compares_to: Mapping[str, object],
) -> tuple[str, ...]:
    errors: list[str] = []
    if numerator_table != binds_to["gold_table"]:
        errors.append("numerator source table must equal binds_to.gold_table")
    if denominator_table != compares_to["gold_table"]:
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
    bound_columns = set(cast(list[str], binding["columns"]))
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


def _definition_scope_result(
    contract: Mapping[str, object],
) -> tuple[str, ...] | None:
    return None if isinstance(contract.get("definition"), Mapping) else ()


def _ratio_sides(
    contract: Mapping[str, object],
) -> tuple[Mapping[str, object], Mapping[str, object]] | None:
    definition = cast(Mapping[str, object], contract["definition"])
    numerator = definition.get("numerator")
    denominator = definition.get("denominator")
    if isinstance(numerator, Mapping) and isinstance(denominator, Mapping):
        return (
            cast(Mapping[str, object], numerator),
            cast(Mapping[str, object], denominator),
        )
    return None


def _side_shape_result(contract: Mapping[str, object]) -> tuple[str, ...] | None:
    if _ratio_sides(contract) is not None:
        return None
    if contract.get("compares_to") is not None:
        return ("compares_to requires a ratio numerator and denominator",)
    return ()


def _is_two_table_contract(contract: Mapping[str, object]) -> bool:
    if contract.get("compares_to") is not None:
        return True
    numerator, denominator = cast(
        tuple[Mapping[str, object], Mapping[str, object]], _ratio_sides(contract)
    )
    numerator_table = _source_table(numerator)
    denominator_table = _source_table(denominator)
    return (
        numerator_table is not None
        and denominator_table is not None
        and numerator_table != denominator_table
    )


def _two_table_scope_result(
    contract: Mapping[str, object],
) -> tuple[str, ...] | None:
    return None if _is_two_table_contract(contract) else ()


def _ratio_kind_result(contract: Mapping[str, object]) -> tuple[str, ...] | None:
    definition = cast(Mapping[str, object], contract["definition"])
    if definition.get("kind") == "ratio":
        return None
    return ("two-table comparison definition.kind must be ratio",)


_PRECHECKS = (
    _definition_scope_result,
    _side_shape_result,
    _two_table_scope_result,
    _ratio_kind_result,
)


def definition_binding_errors(
    contract: Mapping[str, object],
) -> tuple[str, ...]:
    """Return deterministic two-table definition/binding coherence errors.

    Legacy one-table contracts are intentionally outside this validator's scope;
    their existing definition validation and generated output remain unchanged.
    """
    for precheck in _PRECHECKS:
        result = precheck(contract)
        if result is not None:
            return result
    numerator, denominator = cast(
        tuple[Mapping[str, object], Mapping[str, object]], _ratio_sides(contract)
    )
    return _validate_two_table_ratio(contract, numerator, denominator)
