"""Dependency-light contracts for governed rectangular data acquisition."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal, Mapping, Protocol

from ..contracts import AnalysisSpec, Blocker, ColumnBinding

if TYPE_CHECKING:
    from ..policy import PolicyContext


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    max_rows: int = 250_000
    max_bytes: int = 128 * 1024 * 1024
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        if min(self.max_rows, self.max_bytes, self.timeout_seconds) <= 0:
            raise ValueError("provider resource limits must be positive")


@dataclass(frozen=True, slots=True)
class Filter:
    column: str
    operator: str
    value: object | tuple[object, ...] | None


@dataclass(frozen=True, slots=True)
class Aggregate:
    output_column: str
    function: str
    source_column: str | None


@dataclass(frozen=True, slots=True)
class Join:
    table: str
    left_column: str
    right_column: str
    cardinality: str


@dataclass(frozen=True, slots=True)
class ProviderProvenance:
    kind: Literal["local_csv", "gold"]
    safe_label: str
    data_digest: str
    query_digest: str | None
    snapshot_id: str | None


@dataclass(frozen=True, slots=True)
class DataRequest:
    table: str | None = None
    columns: tuple[str, ...] = ()
    logical_types: tuple[str, ...] = ()
    roles: Mapping[str, str] = MappingProxyType({})
    filters: tuple[Filter, ...] = ()
    aggregates: tuple[Aggregate, ...] = ()
    group_by: tuple[str, ...] = ()
    joins: tuple[Join, ...] = ()
    privacy_floor: int = 1

    def __post_init__(self) -> None:
        if len(self.columns) != len(self.logical_types):
            raise ValueError("columns and logical_types must have the same length")
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("requested columns must be unique")
        if self.privacy_floor <= 0:
            raise ValueError("privacy_floor must be positive")


@dataclass(frozen=True, slots=True)
class RectangularData:
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    total_count: int
    excluded_count: int
    exclusion_reasons: tuple[str, ...]
    provenance: ProviderProvenance


class DataProvider(Protocol):
    def fetch(self, request: DataRequest) -> RectangularData:
        """Acquire exactly the governed rectangular data requested."""


class ProviderUnavailable(RuntimeError):
    def __init__(self, blocker: Blocker) -> None:
        super().__init__(blocker.message)
        self.blocker = blocker


def _request_refused(message: str, recovery: str) -> ProviderUnavailable:
    return ProviderUnavailable(
        Blocker(
            code="STAT_PROVIDER_REQUEST_REFUSED",
            message=message,
            recovery=recovery,
        )
    )


def _approved_table(requested: set[str], policy_context: PolicyContext) -> str:
    """Resolve the one approved Gold relation that covers every requested column."""

    candidates = tuple(
        table
        for table, approved in policy_context.approved_columns.items()
        if requested.issubset(approved) and table in policy_context.approved_tables
    )
    if len(candidates) != 1:
        columns = ", ".join(sorted(requested)) or "(none)"
        raise _request_refused(
            f"Requested columns are not approved for statistical use: {columns}.",
            "Use roles from one approved Gold metric-contract binding.",
        )
    return candidates[0]


def _projection(role_items: tuple[tuple[str, ColumnBinding], ...]):
    """Deduplicate the role bindings into one column list with stable order."""

    columns: list[str] = []
    logical_types: list[str] = []
    roles: dict[str, str] = {}
    type_by_column: dict[str, str] = {}
    for role, binding in role_items:
        existing = type_by_column.get(binding.column)
        if existing is not None and existing != binding.logical_type:
            raise _request_refused(
                f"Column {binding.column!r} has conflicting logical types.",
                "Use one approved logical type for each requested column.",
            )
        if existing is None:
            columns.append(binding.column)
            logical_types.append(binding.logical_type)
            type_by_column[binding.column] = binding.logical_type
        roles[role] = binding.column
    return tuple(columns), tuple(logical_types), roles


def _privacy_floor(spec: AnalysisSpec) -> int:
    privacy_floor = spec.pii.get("minimum_group_count")
    if not isinstance(privacy_floor, int) or isinstance(privacy_floor, bool):
        raise _request_refused(
            "The analysis privacy floor is not a valid integer.",
            "Set pii.minimum_group_count to a positive approved integer.",
        )
    return privacy_floor


def build_data_request(
    spec: AnalysisSpec, policy_context: PolicyContext
) -> DataRequest:
    """Project an analysis spec through its already-approved policy context."""

    role_items = tuple(spec.roles.items())
    requested = {binding.column for _, binding in role_items}
    table = _approved_table(requested, policy_context)
    columns, logical_types, roles = _projection(role_items)
    return DataRequest(
        table=table,
        columns=columns,
        logical_types=logical_types,
        roles=MappingProxyType(roles),
        privacy_floor=_privacy_floor(spec),
    )
