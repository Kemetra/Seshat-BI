"""Immutable cross-component contracts for governed statistical analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal, Mapping


class Outcome(StrEnum):
    COMPUTED = "computed"
    WITHHELD = "withheld"
    REFUSED = "refused"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class Blocker:
    code: str
    message: str
    recovery: str


@dataclass(frozen=True, slots=True)
class ColumnBinding:
    column: str
    logical_type: Literal[
        "number",
        "integer",
        "boolean",
        "category",
        "date",
        "datetime",
        "identifier",
    ]


@dataclass(frozen=True, slots=True)
class MethodSpec:
    method_id: str
    version: str
    parameters: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class AnalysisSpec:
    schema_version: str
    analysis_id: str
    revision: int
    subject: str
    question: str
    cadence: str
    owner: str
    readiness_status: PurePosixPath
    metric_contracts: tuple[PurePosixPath, ...]
    provider: Mapping[str, object]
    population: Mapping[str, object]
    roles: Mapping[str, ColumnBinding]
    method: MethodSpec
    missing_policy: str
    minimum_data: Mapping[str, int]
    random_seed: int
    pii: Mapping[str, object]
    outputs: Mapping[str, PurePosixPath]


@dataclass(frozen=True, slots=True)
class Estimate:
    name: str
    value: str | None
    unit: str | None


@dataclass(frozen=True, slots=True)
class Interval:
    name: str
    low: str | None
    high: str | None
    level: str
    method: str


@dataclass(frozen=True, slots=True)
class TestStatistic:
    name: str
    statistic: str | None
    p_value: str | None
    adjusted_p_value: str | None
    alternative: str | None
    method: str


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    status: Literal["holds", "warning", "violated", "not_applicable"]
    observed: str | None
    message: str


@dataclass(frozen=True, slots=True)
class AnalysisEvidence:
    engine_version: str
    invocation_id: str
    started_at: str
    completed_at: str
    analysis: Mapping[str, object]
    governance: Mapping[str, object]
    input_provenance: Mapping[str, object]
    method: Mapping[str, object]
    outcome: Outcome
    estimates: tuple[Estimate, ...] = ()
    effect_sizes: tuple[Estimate, ...] = ()
    intervals: tuple[Interval, ...] = ()
    tests: tuple[TestStatistic, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    warnings: tuple[str, ...] = ()
    blockers: tuple[Blocker, ...] = ()
    cautions: tuple[str, ...] = ()
    schema_version: str = "1.0"
    authority: str = "derived-evidence-only"
    readiness_effect: str = "none; named-human approval required"
    review_state: str = "pending"
