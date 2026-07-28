"""Strict numerical preparation and privacy helpers for statistical methods."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from ..contracts import AnalysisWithheld, Blocker, MethodContext


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
    return AnalysisWithheld((Blocker(code, message, recovery),))


def finite_array(values: Iterable[object], role: str):
    """Convert declared numeric observations without coercing invalid values."""

    import numpy as np

    converted: list[float] = []
    for value in values:
        if isinstance(value, bool):
            raise _withheld(
                "STAT_NON_NUMERIC_INPUT",
                f"The {role} role contains a boolean, not a numeric observation.",
                "Provide values matching the approved numeric role.",
            )
        if not isinstance(value, (Decimal, int, float, str)):
            raise _withheld(
                "STAT_NON_NUMERIC_INPUT",
                f"The {role} role contains a non-numeric observation.",
                "Provide values matching the approved numeric role.",
            )
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise _withheld(
                "STAT_NON_NUMERIC_INPUT",
                f"The {role} role contains a non-numeric observation.",
                "Provide values matching the approved numeric role.",
            ) from exc
        if not math.isfinite(number):
            raise _withheld(
                "STAT_NON_FINITE_INPUT",
                f"The {role} role contains a non-finite observation.",
                (
                    "Replace NaN or infinite values under the approved "
                    "missing-data policy."
                ),
            )
        converted.append(number)
    return np.asarray(converted, dtype=np.float64)


def _is_missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _column_index(context: MethodContext, role: str) -> int:
    binding = context.spec.roles.get(role)
    if binding is None:
        raise _withheld(
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


def numeric_role(context: MethodContext, role: str) -> NumericSample:
    """Prepare one role with explicit missingness and minimum-data behavior."""

    index = _column_index(context, role)
    retained: list[object] = []
    row_indices: list[int] = []
    missing_count = 0
    for row_index, row in enumerate(context.data.rows):
        value = row[index]
        if _is_missing(value):
            missing_count += 1
            continue
        retained.append(value)
        row_indices.append(row_index)

    if missing_count and context.spec.missing_policy == "fail":
        raise _withheld(
            "STAT_MISSING_DATA",
            f"The {role} role contains missing observations.",
            "Resolve missing values or approve a non-failing missing-data policy.",
        )

    values = finite_array(retained, role)
    minimum = context.spec.minimum_data.get("observations", 1)
    if len(values) < minimum:
        raise _withheld(
            "STAT_MINIMUM_DATA",
            (
                f"The {role} role retains {len(values)} observations; "
                f"the governed minimum is {minimum}."
            ),
            (
                "Provide more eligible observations or obtain approval "
                "for a revised floor."
            ),
        )
    reasons = list(context.data.exclusion_reasons)
    if missing_count:
        reasons.append(f"{role}:missing={missing_count}")
    return NumericSample(
        values=values,
        row_indices=tuple(row_indices),
        total_count=context.data.total_count,
        retained_count=len(values),
        excluded_count=context.data.excluded_count + missing_count,
        exclusion_reasons=tuple(reasons),
    )


def safe_groups(context: MethodContext, role: str = "group") -> SafeGroups:
    """Suppress undersized groups before any group-level method executes."""

    index = _column_index(context, role)
    grouped: dict[str, list[int]] = {}
    missing_count = 0
    for row_index, row in enumerate(context.data.rows):
        value = row[index]
        if _is_missing(value):
            missing_count += 1
            continue
        grouped.setdefault(str(value), []).append(row_index)

    floor = context.spec.pii.get("minimum_group_count", 1)
    if not isinstance(floor, int) or isinstance(floor, bool) or floor < 1:
        raise _withheld(
            "STAT_PRIVACY_FLOOR_INVALID",
            "The approved minimum group count is invalid.",
            "Set pii.minimum_group_count to a positive approved integer.",
        )
    safe: list[SafeGroup] = []
    suppressed = 0
    for label, row_indices in sorted(grouped.items()):
        if len(row_indices) < floor:
            suppressed += 1
        else:
            safe.append(SafeGroup(label, tuple(row_indices)))
    return SafeGroups(tuple(safe), suppressed, missing_count)


def unit_for_role(context: MethodContext, role: str) -> str | None:
    """Return the approved metric unit when the bound column identifies it."""

    binding = context.spec.roles.get(role)
    if binding is None:
        return None
    for contract in context.policy.contracts:
        if binding.column in contract.columns and contract.unit:
            return contract.unit
    return None
