"""Immutable contracts shared by the governed dbt adapter modules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class Blocker:
    """One concrete, stable reason that prevents a governed operation."""

    code: str
    message: str
    assertion_id: str | None = None


class GovernanceError(ValueError):
    """A handled fail-closed working-set or governance error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class MappingApproval:
    """Canonical named-human approval read from readiness status."""

    stage: str
    owner: str
    at: str
    note: str
    approval_id: str


@dataclass(frozen=True, slots=True)
class WorkingSet:
    """Exact governed files for one table plus its committed map identity."""

    repo_root: Path
    table_id: str
    mapping_dir: Path
    source_map: Path
    readiness_status: Path
    unresolved_questions: Path
    source_map_revision: str
    source_map_sha256: str


@dataclass(frozen=True, slots=True)
class GateDecision:
    """Pure Mapping Ready decision; never changes readiness state."""

    allowed: bool
    table_id: str
    mapping_status: str
    approval: MappingApproval | None
    mirror_cleared: bool
    blocking_reasons: tuple[Blocker, ...]


@dataclass(frozen=True, slots=True)
class ShadowSchemas:
    """Validated target-prefixed schemas for dbt-owned shadow relations."""

    silver: str
    gold: str
    audit: str


@dataclass(frozen=True, slots=True)
class ColumnCitation:
    """Approved source or physical derivation for one model output column."""

    name: str
    source_columns: tuple[str, ...]
    derivation: str | None


@dataclass(frozen=True, slots=True)
class ModelContract:
    """Machine-readable, per-model authority and lineage contract."""

    name: str
    table_id: str
    source_map: str
    source_map_revision: str
    grain: str
    business_key: tuple[str, ...]
    authority: str
    columns: tuple[ColumnCitation, ...]


@dataclass(frozen=True, slots=True)
class ProjectValidation:
    """Static dbt project validation result."""

    valid: bool
    project_fingerprint: str
    selector_name: str
    profile_name: str
    target_name: str
    schemas: ShadowSchemas
    model_contracts: tuple[ModelContract, ...]
    blocking_reasons: tuple[Blocker, ...]


class Operation(str, Enum):
    """Closed set of dbt operations owned by the Seshat adapter."""

    PARSE = "parse"
    LIST = "list"
    BUILD = "build"
    TEST = "test"
    SHOW = "show"


@dataclass(frozen=True, slots=True)
class RunContext:
    """In-memory instruction for one isolated dbt child process."""

    repo_root: Path
    project_dir: Path
    profiles_dir: Path
    operation: Operation
    table_id: str
    selector: str
    target: str
    run_dir: Path
    environment: Mapping[str, str]
    timeout_s: float = 1800.0


@dataclass(frozen=True, slots=True)
class InvocationResult:
    """Sanitized result from one controlled dbt child process."""

    invocation_id: str
    operation: Operation
    argv_summary: tuple[str, ...]
    return_code: int
    started_at: str
    completed_at: str
    stdout: str
    stderr: str
    target_dir: Path
    log_dir: Path


@dataclass(frozen=True, slots=True)
class ManifestNode:
    """Allowlisted manifest fields for one dbt model or test node."""

    unique_id: str
    resource_type: str
    name: str
    package_name: str
    original_file_path: str
    depends_on_nodes: tuple[str, ...]
    tags: tuple[str, ...]
    schema: str
    database: str | None
    alias: str | None
    relation_name: str | None
    materialized: str | None
    meta: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ManifestSummary:
    """Strict manifest v12 summary without compiled code or absolute paths."""

    schema_uri: str
    dbt_version: str
    sha256: str
    semantic_sha256: str
    nodes: Mapping[str, ManifestNode]
    selected_unique_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NodeResult:
    """Normalized result fields for one executed dbt node."""

    unique_id: str
    status: str
    failures: int | None
    execution_seconds: Decimal


@dataclass(frozen=True, slots=True)
class RunResultsSummary:
    """Strict run-results v6 summary without raw adapter messages."""

    schema_uri: str
    dbt_version: str
    which: str
    sha256: str
    results: tuple[NodeResult, ...]


@dataclass(frozen=True, slots=True)
class ArtifactSet:
    """Verified manifest plus the normalized results for a governed run."""

    manifest: ManifestSummary
    run_results: tuple[RunResultsSummary, ...]


@dataclass(frozen=True, slots=True)
class MappingBinding:
    """Exact approved mapping inputs bound into an execution plan."""

    path: str
    git_blob: str
    sha256: str
    readiness_sha256: str
    unresolved_questions_sha256: str
    approval_id: str


@dataclass(frozen=True, slots=True)
class FactBinding:
    """Owner-declared fact column semantics bound into an execution plan.

    Read from the approved source map's ``gold_star.fact`` section: which
    ordered column(s) form the grain/business key parity counts distinct
    (one column normally; several for a composite grain), and which columns
    are the additive money measures parity reconciles by sum (possibly none
    -- a factless fact declares an explicit empty set). These make the
    expected fact-subject set derivable EXACTLY (issue #331) -- fact
    measures/keys are columns, not model nodes, so unlike dimensions the
    built graph alone cannot enumerate them. ``name`` is the approved fact
    relation's normalized MODEL name (schema qualifier stripped): evidence
    requires the single built fact model to BE this relation, so an audit
    against a different fact can never satisfy the subject checks.
    """

    name: str
    business_key: tuple[str, ...]
    additive_money_measures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProjectBinding:
    """Exact dbt project identity bound into an execution plan."""

    path: str
    sha256: str


@dataclass(frozen=True, slots=True)
class RuntimeBinding:
    """Pinned dbt runtime and fixed selection target."""

    dbt_core: str
    dbt_adapter: str
    dbt_adapter_version: str
    profile: str
    target: str
    selector: str


@dataclass(frozen=True, slots=True)
class ManifestBinding:
    """Verified manifest schema and deterministic governed-graph identity."""

    schema_uri: str
    semantic_sha256: str


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Timestamp-free, immutable governed facts accepted before execution."""

    schema_version: int
    table_id: str
    mapping: MappingBinding
    fact: FactBinding
    project: ProjectBinding
    runtime: RuntimeBinding
    schemas: ShadowSchemas
    manifest: ManifestBinding
    selected_unique_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlanEnvelope:
    """Stored execution plan plus its canonical SHA-256 acceptance digest."""

    digest: str
    plan: ExecutionPlan


@dataclass(frozen=True, slots=True)
class ParityAssertion:
    """One normalized migration-versus-dbt parity assertion."""

    assertion_id: str
    assertion_class: str
    subject: str
    expected: str
    actual: str
    delta: str
    tolerance: str
    passed: bool


@dataclass(frozen=True, slots=True)
class TestSummary:
    """Normalized counts for executed dbt data tests."""

    passed: int
    failed: int
    errored: int
    skipped: int


@dataclass(frozen=True, slots=True)
class RunEvidence:
    """Sanitized derived evidence; never a readiness or migration approval."""

    schema_version: int
    authority: str
    invocation_id: str
    table_id: str
    command: str
    outcome: str
    seshat_exit_code: int
    started_at: str
    completed_at: str
    elapsed_seconds: float
    plan_digest: str
    project_fingerprint: str
    mapping_path: str
    mapping_revision: str
    runtime: Mapping[str, str]
    target: Mapping[str, object]
    selected_unique_ids: tuple[str, ...]
    executed_unique_ids: tuple[str, ...]
    tests: TestSummary
    parity: tuple[ParityAssertion, ...]
    artifacts: Mapping[str, str]
    blocking_reasons: tuple[Blocker, ...]
    readiness_effect: str
