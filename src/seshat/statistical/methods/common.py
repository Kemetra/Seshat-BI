"""Strict numerical preparation and privacy helpers for statistical methods."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from ..contracts import AnalysisWithheld, MethodContext, require, withheld

_NUMERIC_TYPES = (Decimal, int, float, str)


@dataclass(frozen=True, slots=True)
class NumericSample:
    values: object
    row_indices: tuple[int, ...]
    total_count: int
    retained_count: int
    excluded_count: int
    exclusion_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SafeGroup:
    label: str
    row_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SafeGroups:
    groups: tuple[SafeGroup, ...]
    suppressed_count: int
    missing_count: int


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return withheld(code, message, recovery)


def _finite_number(value: object, role: str) -> float:
    """Convert one declared observation, refusing anything that is not numeric."""

    require(
        not isinstance(value, bool),
        "STAT_NON_NUMERIC_INPUT",
        f"The {role} role contains a boolean, not a numeric observation.",
        "Provide values matching the approved numeric role.",
    )
    require(
        isinstance(value, _NUMERIC_TYPES),
        "STAT_NON_NUMERIC_INPUT",
        f"The {role} role contains a non-numeric observation.",
        "Provide values matching the approved numeric role.",
    )
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError) as exc:
        raise _withheld(
            "STAT_NON_NUMERIC_INPUT",
            f"The {role} role contains a non-numeric observation.",
            "Provide values matching the approved numeric role.",
        ) from exc
    require(
        math.isfinite(number),
        "STAT_NON_FINITE_INPUT",
        f"The {role} role contains a non-finite observation.",
        "Replace NaN or infinite values under the approved missing-data policy.",
    )
    return number


def finite_array(values: Iterable[object], role: str):
    """Convert declared numeric observations without coercing invalid values."""

    import numpy as np

    converted = [_finite_number(value, role) for value in values]
    return np.asarray(converted, dtype=np.float64)


def _is_missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _column_index(context: MethodContext, role: str) -> int:
    binding = context.spec.roles.get(role)
    require(
        binding is not None,
        "STAT_METHOD_ROLE_MISSING",
        f"The governed {role} role is not bound.",
        "Bind every required method role in the analysis specification.",
    )
    try:
        return context.data.columns.index(binding.column)
    except ValueError as exc:
        raise _withheld(
            "STAT_PROVIDER_INVALID_DATA",
            f"The acquired data omits the governed {role} column.",
            "Repair the provider projection and rerun the analysis.",
        ) from exc


def _present_values(context: MethodContext, index: int):
    """Split one column into its present values, their rows, and a missing count."""

    present = [
        (row_index, row[index])
        for row_index, row in enumerate(context.data.rows)
        if not _is_missing(row[index])
    ]
    missing_count = len(context.data.rows) - len(present)
    return present, missing_count


def numeric_role(context: MethodContext, role: str) -> NumericSample:
    """Prepare one role with explicit missingness and minimum-data behavior."""

    index = _column_index(context, role)
    present, missing_count = _present_values(context, index)
    require(
        not missing_count or context.spec.missing_policy != "fail",
        "STAT_MISSING_DATA",
        f"The {role} role contains missing observations.",
        "Resolve missing values or approve a non-failing missing-data policy.",
    )
    values = finite_array([value for _, value in present], role)
    minimum = context.spec.minimum_data.get("observations", 1)
    require(
        len(values) >= minimum,
        "STAT_MINIMUM_DATA",
        (
            f"The {role} role retains {len(values)} observations; "
            f"the governed minimum is {minimum}."
        ),
        "Provide more eligible observations or obtain approval for a revised floor.",
    )
    reasons = list(context.data.exclusion_reasons)
    if missing_count:
        reasons.append(f"{role}:missing={missing_count}")
    return NumericSample(
        values=values,
        row_indices=tuple(row_index for row_index, _ in present),
        total_count=context.data.total_count,
        retained_count=len(values),
        excluded_count=context.data.excluded_count + missing_count,
        exclusion_reasons=tuple(reasons),
    )


def _privacy_floor(context: MethodContext) -> int:
    floor = context.spec.pii.get("minimum_group_count", 1)
    require(
        isinstance(floor, int) and not isinstance(floor, bool) and floor >= 1,
        "STAT_PRIVACY_FLOOR_INVALID",
        "The approved minimum group count is invalid.",
        "Set pii.minimum_group_count to a positive approved integer.",
    )
    return int(floor)


def safe_groups(context: MethodContext, role: str = "group") -> SafeGroups:
    """Suppress undersized groups before any group-level method executes."""

    index = _column_index(context, role)
    present, missing_count = _present_values(context, index)
    grouped: dict[str, list[int]] = {}
    for row_index, value in present:
        grouped.setdefault(str(value), []).append(row_index)

    floor = _privacy_floor(context)
    safe = tuple(
        SafeGroup(label, tuple(row_indices))
        for label, row_indices in sorted(grouped.items())
        if len(row_indices) >= floor
    )
    return SafeGroups(safe, len(grouped) - len(safe), missing_count)


def unit_for_role(context: MethodContext, role: str) -> str | None:
    """Return the approved metric unit when the bound column identifies it."""

    binding = context.spec.roles.get(role)
    if binding is None:
        return None
    units = (
        contract.unit
        for contract in context.policy.contracts
        if binding.column in contract.columns and contract.unit
    )
    return next(units, None)
