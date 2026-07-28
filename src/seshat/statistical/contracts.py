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
