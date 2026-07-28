"""Shared spec, data, and policy builders for the governed method tests.

Every method test needs the same three things: an AnalysisSpec that declares the
governed decisions, a RectangularData that stands in for an acquired extract,
and a PolicyContext that says which table and columns were approved. Building
them here keeps each test module's own helper short and keeps one place to look
when a contract field changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Mapping, Sequence

from seshat.statistical.contracts import (
    AnalysisSpec,
    ColumnBinding,
    MethodContext,
    MethodSpec,
)
from seshat.statistical.policy import PolicyContext
from seshat.statistical.providers.base import ProviderProvenance, RectangularData

APPROVED_TABLE = "gold.sample"


@dataclass(frozen=True, slots=True)
class SpecSettings:
    """The governed decisions one method test wants its specification to declare."""

    analysis_id: str
    question: str
    method_id: str
    parameters: Mapping[str, object]
    roles: Mapping[str, ColumnBinding]
    missing_policy: str = "complete_case"
    minimum_data: Mapping[str, int] = field(
        default_factory=lambda: {"observations": 1, "groups": 1, "seasonal_cycles": 0}
    )
    privacy_floor: int = 2
    cadence: str = "weekly"
    grain: str = "one row"
    seed: int = 1729


def analysis_spec(settings: SpecSettings) -> AnalysisSpec:
    """Build the committed-looking specification a method test runs against."""

    return AnalysisSpec(
        schema_version="1.0",
        analysis_id=settings.analysis_id,
        revision=1,
        subject="sample",
        question=settings.question,
        cadence=settings.cadence,
        owner="Example Analyst",
        readiness_status=PurePosixPath("mappings/sample/readiness-status.yaml"),
        metric_contracts=(
            PurePosixPath("mappings/sample/metrics/ApprovedMetric.yaml"),
        ),
        provider=MappingProxyType({"kind": "local_csv", "dataset_id": "sample"}),
        population=MappingProxyType(
            {"grain": settings.grain, "inclusion": (), "exclusion": ()}
        ),
        roles=MappingProxyType(dict(settings.roles)),
        method=MethodSpec(
            settings.method_id,
            "1.0",
            MappingProxyType(dict(settings.parameters)),
        ),
        missing_policy=settings.missing_policy,
        minimum_data=MappingProxyType(dict(settings.minimum_data)),
        random_seed=settings.seed,
        pii=MappingProxyType(
            {
                "classification": "none",
                "approval_evidence": (),
                "minimum_group_count": settings.privacy_floor,
            }
        ),
        outputs=MappingProxyType({}),
    )


def rectangular(columns: Sequence[str], rows: Sequence[tuple]) -> RectangularData:
    return RectangularData(
        columns=tuple(columns),
        rows=tuple(rows),
        total_count=len(rows),
        excluded_count=0,
        exclusion_reasons=(),
        provenance=ProviderProvenance(
            "local_csv", "local_csv:test", "a" * 64, None, None
        ),
    )


def policy_context(columns: Sequence[str]) -> PolicyContext:
    return PolicyContext(
        subject="sample",
        readiness_path=Path("readiness-status.yaml"),
        readiness_revision="1",
        contracts=(),
        approved_tables=frozenset({APPROVED_TABLE}),
        approved_columns=MappingProxyType({APPROVED_TABLE: frozenset(columns)}),
    )


def method_context(
    settings: SpecSettings, columns: Sequence[str], rows: Sequence[tuple]
) -> MethodContext:
    """Assemble the spec, acquired data, and approved policy into one context."""

    return MethodContext(
        analysis_spec(settings), policy_context(columns), rectangular(columns, rows)
    )
