"""Immutable dbt preflight plans bound to approved governance inputs."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from secrets import token_hex
from typing import cast

from seshat.dbt import (
    DBT_CORE_VERSION,
    DBT_POSTGRES_VERSION,
    PROFILE_NAME,
    TARGET_NAME,
)
from seshat.dbt.artifacts import (
    MANIFEST_V12,
    ArtifactIntegrityError,
    load_manifest,
)
from seshat.dbt.contracts import (
    ExecutionPlan,
    FactBinding,
    GateDecision,
    InvocationResult,
    ManifestBinding,
    ManifestNode,
    ManifestSummary,
    MappingApproval,
    MappingBinding,
    Operation,
    PlanEnvelope,
    ProjectBinding,
    ProjectValidation,
    RunContext,
    RuntimeBinding,
    ShadowSchemas,
    WorkingSet,
)
from seshat.dbt.fact_semantics import load_fact_semantics
from seshat.dbt.gate import evaluate_mapping_gate, resolve_working_set
from seshat.dbt.project import validate_project
from seshat.dbt.redaction import load_child_environment
from seshat.dbt.runner import build_dbt_argv, target_lock

_TABLE_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_COLUMN_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_UNIQUE_ID = re.compile(r"^(model|test)\.seshat_bi\.[A-Za-z0-9_.-]+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_BLOB = re.compile(r"^[0-9a-f]{40,64}$")
_PROTECTED_SCHEMAS = frozenset({"bronze", "silver", "gold", "public"})
_MODEL_PATH_LAYERS = {
    "staging": "silver",
    "gold": "gold",
    "marts": "gold",
    "audit": "audit",
}
_MODEL_MATERIALIZATIONS = frozenset({"table", "view"})

DbtRunner = Callable[[RunContext, tuple[str, ...]], InvocationResult]


@dataclass(frozen=True)
class SelectionContext:
    """Governed expectations used to validate an exact dbt node selection."""

    selector: str
    contract_model_names: tuple[str, ...]
    schemas: ShadowSchemas


@dataclass(frozen=True)
class _NodeSelectionContext:
    selector: str
    selected_model_ids: frozenset[str]
    schemas: ShadowSchemas


@dataclass(frozen=True)
class _PlanBuildContext:
    root: Path
    table_id: str
    working_set: WorkingSet
    approval: MappingApproval
    fact: FactBinding
    project: ProjectValidation
    manifest: ManifestSummary
    selected: tuple[str, ...]


class PlanDrift(ValueError):
    """The accepted plan digest or a plan storage invariant has drifted."""


def canonical_plan_bytes(plan: ExecutionPlan) -> bytes:
    """Return timestamp-free canonical JSON bytes for the plan only."""

    return json.dumps(
        asdict(plan), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def plan_digest(plan: ExecutionPlan) -> str:
    """Return the canonical SHA-256 acceptance digest for a plan."""

    return hashlib.sha256(canonical_plan_bytes(plan)).hexdigest()


def _validate_plan_identity(plan: ExecutionPlan) -> None:
    # v2 added the required fact binding (issue #331); a v1 plan predates it
    # and must be re-planned, never silently reinterpreted.
    if plan.schema_version != 2:
        raise PlanDrift("plan schema_version must be 2")
    if not _TABLE_ID.fullmatch(plan.table_id):
        raise PlanDrift("plan table_id is unsafe")


def _validate_mapping_binding(plan: ExecutionPlan) -> None:
    expected_map = f"mappings/{plan.table_id}/source-map.yaml"
    if plan.mapping.path != expected_map:
        raise PlanDrift("plan mapping path does not match table_id")


def _validate_plan_hashes(plan: ExecutionPlan) -> None:
    hashes = (
        plan.mapping.sha256,
        plan.mapping.readiness_sha256,
        plan.mapping.unresolved_questions_sha256,
        plan.project.sha256,
        plan.manifest.semantic_sha256,
    )
    if not all(_SHA256.fullmatch(value) for value in hashes):
        raise PlanDrift("plan contains an invalid SHA-256")
    if not _GIT_BLOB.fullmatch(plan.mapping.git_blob):
        raise PlanDrift("plan contains an invalid mapping Git blob")
    if not plan.mapping.approval_id:
        raise PlanDrift("plan has no named-human approval identity")


def _canonical_money(money: tuple[str, ...]) -> bool:
    # Identifier-check FIRST: a malformed stored plan may carry non-string
    # (even unhashable) elements, and sorting/set-building those must yield a
    # handled PlanDrift, never an uncaught TypeError.
    if not all(
        isinstance(measure, str) and _COLUMN_ID.fullmatch(measure) for measure in money
    ):
        return False
    # Empty is canonical: a factless fact declares zero money measures.
    return money == tuple(sorted(set(money)))


def _require_canonical_money(money: tuple[str, ...]) -> None:
    if not _canonical_money(money):
        raise PlanDrift(
            "plan fact additive_money_measures must be sorted, unique identifiers"
        )


def _canonical_business_key(key: tuple[str, ...]) -> bool:
    # Identifier-check FIRST (see _canonical_money). Ordered and non-empty;
    # order is the grain declaration, so uniqueness is required but sorting
    # is NOT.
    if not all(
        isinstance(column, str) and _COLUMN_ID.fullmatch(column) for column in key
    ):
        return False
    return bool(key) and len(key) == len(set(key))


def _validate_fact_binding(plan: ExecutionPlan) -> None:
    name = plan.fact.name
    if not (isinstance(name, str) and _COLUMN_ID.fullmatch(name)):
        raise PlanDrift("plan fact name is unsafe")
    if not _canonical_business_key(plan.fact.business_key):
        raise PlanDrift("plan fact business_key is unsafe")
    _require_canonical_money(plan.fact.additive_money_measures)
    if set(plan.fact.business_key) & set(plan.fact.additive_money_measures):
        raise PlanDrift("plan fact business_key cannot be an additive money measure")


def _validate_runtime_binding(plan: ExecutionPlan) -> None:
    expected = RuntimeBinding(
        dbt_core=DBT_CORE_VERSION,
        dbt_adapter="dbt-postgres",
        dbt_adapter_version=DBT_POSTGRES_VERSION,
        profile=PROFILE_NAME,
        target=TARGET_NAME,
        selector=f"seshat_table_{plan.table_id}",
    )
    if plan.project.path != "dbt":
        raise PlanDrift("plan runtime binding is not the fixed governed runtime")
    if plan.runtime != expected:
        raise PlanDrift("plan runtime binding is not the fixed governed runtime")


def _validate_manifest_binding(plan: ExecutionPlan) -> None:
    if plan.manifest.schema_uri != MANIFEST_V12:
        raise PlanDrift("plan manifest schema is unsupported")


def _require_non_empty_selection(ids: tuple[str, ...]) -> None:
    if not ids:
        raise PlanDrift(
            "plan selected_unique_ids must be non-empty, sorted, and unique"
        )


def _require_sorted_selection(ids: tuple[str, ...]) -> None:
    if ids != tuple(sorted(ids)):
        raise PlanDrift(
            "plan selected_unique_ids must be non-empty, sorted, and unique"
        )


def _require_unique_selection(ids: tuple[str, ...]) -> None:
    if len(ids) != len(set(ids)):
        raise PlanDrift(
            "plan selected_unique_ids must be non-empty, sorted, and unique"
        )


def _validate_selected_ids(plan: ExecutionPlan) -> None:
    ids = plan.selected_unique_ids
    _require_non_empty_selection(ids)
    _require_sorted_selection(ids)
    _require_unique_selection(ids)
    if not all(_UNIQUE_ID.fullmatch(unique_id) for unique_id in ids):
        raise PlanDrift("plan selected_unique_ids contains an unsupported node")


def _validate_schema(layer: str, schema: str) -> None:
    if not re.fullmatch(rf"^[a-z_][a-z0-9_]*_{layer}$", schema):
        raise PlanDrift(f"plan {layer} schema is unsafe")


def _validate_schemas(plan: ExecutionPlan) -> None:
    schemas = asdict(plan.schemas)
    for layer, schema in schemas.items():
        _validate_schema(layer, schema)


def _valid_plan(plan: ExecutionPlan) -> None:
    _validate_plan_identity(plan)
    _validate_mapping_binding(plan)
    _validate_plan_hashes(plan)
    _validate_fact_binding(plan)
    _validate_runtime_binding(plan)
    _validate_manifest_binding(plan)
    _validate_selected_ids(plan)
    _validate_schemas(plan)


def save_plan(repo_root: Path, plan: ExecutionPlan) -> Path:
    """Atomically save a validated envelope at the fixed ignored local path."""

    _valid_plan(plan)
    root = Path(repo_root).resolve()
    parent = root / ".seshat" / "dbt" / "plans"
    parent.mkdir(parents=True, exist_ok=True)
    try:
        parent.resolve().relative_to(root)
    except ValueError as exc:
        raise PlanDrift("local plan path escapes the repository") from exc
    path = parent / f"{plan.table_id}-{plan.runtime.target}.json"
    envelope = PlanEnvelope(digest=plan_digest(plan), plan=plan)
    payload = json.dumps(
        asdict(envelope), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    temporary = path.with_name(f".{path.name}.{token_hex(8)}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.write("\n")
            stream.flush()
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return path


def load_plan(repo_root: Path, table_id: str) -> PlanEnvelope:
    """Load and verify the fixed local accepted-plan envelope for one table."""

    if not _TABLE_ID.fullmatch(table_id):
        raise PlanDrift("plan table_id is unsafe")
    root = Path(repo_root).resolve()
    path = root / ".seshat" / "dbt" / "plans" / f"{table_id}-shadow.json"
    payload = _load_plan_payload(path)
    envelope = _plan_envelope(payload)
    _valid_plan(envelope.plan)
    require_accepted_plan(envelope.digest, envelope.plan)
    return envelope


def _stored_columns(value: object) -> tuple[object, ...]:
    """Normalize a stored plan's column list without char-splitting a string.

    JSON stores the columns as a list; a hand-edited scalar must become a
    1-tuple (not iterated character-by-character) so _valid_plan judges the
    actual value and returns a handled PlanDrift."""
    return tuple(value) if isinstance(value, list) else (value,)


def _load_plan_payload(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PlanDrift("accepted local plan is missing or invalid") from exc


def _plan_envelope(payload: object) -> PlanEnvelope:
    try:
        raw = payload["plan"]
        plan = ExecutionPlan(
            schema_version=raw["schema_version"],
            table_id=raw["table_id"],
            mapping=MappingBinding(**raw["mapping"]),
            fact=FactBinding(
                name=raw["fact"]["name"],
                business_key=_stored_columns(raw["fact"]["business_key"]),
                additive_money_measures=_stored_columns(
                    raw["fact"]["additive_money_measures"]
                ),
            ),
            project=ProjectBinding(**raw["project"]),
            runtime=RuntimeBinding(**raw["runtime"]),
            schemas=ShadowSchemas(**raw["schemas"]),
            manifest=ManifestBinding(**raw["manifest"]),
            selected_unique_ids=tuple(raw["selected_unique_ids"]),
        )
        envelope = PlanEnvelope(digest=payload["digest"], plan=plan)
    except (KeyError, TypeError) as exc:
        raise PlanDrift("accepted local plan has an invalid shape") from exc
    if set(payload) != {"digest", "plan"}:
        raise PlanDrift("accepted local plan has unexpected fields")
    return envelope


def require_accepted_plan(expected_digest: str, actual: ExecutionPlan) -> None:
    """Refuse unless the supplied digest exactly accepts the recomputed plan."""

    actual_digest = plan_digest(actual)
    if not hmac.compare_digest(expected_digest, actual_digest):
        raise PlanDrift(
            "accepted plan has drifted; run `seshat dbt plan` and review again"
        )


def _nonblank_lines(stdout: str):
    for number, line in enumerate(stdout.splitlines(), start=1):
        if line.strip():
            yield number, line


def _unsupported_list_id(number: int) -> ArtifactIntegrityError:
    return ArtifactIntegrityError(
        f"dbt list line {number} has an unsupported unique_id"
    )


def _list_unique_id(row: object, number: int) -> str:
    if not isinstance(row, dict):
        raise _unsupported_list_id(number)
    unique_id = row.get("unique_id")
    if not isinstance(unique_id, str):
        raise _unsupported_list_id(number)
    if not _UNIQUE_ID.fullmatch(unique_id):
        raise _unsupported_list_id(number)
    return unique_id


def _parse_list_line(line: str, number: int) -> str:
    try:
        row = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ArtifactIntegrityError(
            f"dbt list line {number} is not valid JSON"
        ) from exc
    return _list_unique_id(row, number)


def _parse_list_output(stdout: str) -> tuple[str, ...]:
    return tuple(
        _parse_list_line(line, number) for number, line in _nonblank_lines(stdout)
    )


def _require_list_selection(ids: tuple[str, ...]) -> None:
    if not ids:
        raise ArtifactIntegrityError("dbt list returned no governed nodes")


def _require_distinct_list_ids(ids: tuple[str, ...]) -> None:
    if len(ids) != len(set(ids)):
        raise ArtifactIntegrityError("dbt list returned duplicate unique IDs")


def _require_manifest_nodes(ids: tuple[str, ...], manifest: ManifestSummary) -> None:
    missing_manifest = set(ids) - set(manifest.nodes)
    if missing_manifest:
        raise ArtifactIntegrityError(
            "dbt list selected nodes absent from manifest: "
            + ", ".join(sorted(missing_manifest))
        )


def _selected_model_ids(ids: tuple[str, ...]) -> frozenset[str]:
    return frozenset(unique_id for unique_id in ids if unique_id.startswith("model."))


def _validate_selected_model(
    unique_id: str,
    node: ManifestNode,
    context: _NodeSelectionContext,
) -> tuple[str, ...]:
    if context.selector not in node.tags:
        raise ArtifactIntegrityError(
            f"selected model {unique_id} lacks governed selector tag"
        )
    _validate_model_execution_binding(unique_id, node, context.schemas)
    return (node.name,)


def _model_layer(unique_id: str, node: ManifestNode) -> str:
    parts = PurePosixPath(node.original_file_path).parts
    layer_directory = parts[1] if len(parts) > 1 and parts[0] == "models" else None
    layer = _MODEL_PATH_LAYERS.get(layer_directory)
    if layer is None:
        raise ArtifactIntegrityError(
            f"selected model {unique_id} path has no governed schema layer"
        )
    return layer


def _validate_model_schema(
    unique_id: str, node: ManifestNode, schemas: ShadowSchemas
) -> None:
    if node.schema in _PROTECTED_SCHEMAS:
        raise ArtifactIntegrityError(
            f"selected model {unique_id} uses protected schema {node.schema}"
        )
    layer = _model_layer(unique_id, node)
    expected = getattr(schemas, layer)
    if node.schema != expected:
        raise ArtifactIntegrityError(
            f"selected model {unique_id} schema does not match governed {layer} schema"
        )


def _validate_model_materialization(unique_id: str, node: ManifestNode) -> None:
    if node.materialized not in _MODEL_MATERIALIZATIONS:
        raise ArtifactIntegrityError(
            f"selected model {unique_id} materialization must be table or view"
        )


def _required_relation_field(unique_id: str, label: str, value: str | None) -> str:
    if value is None:
        raise ArtifactIntegrityError(
            f"selected model {unique_id} relation {label} is missing"
        )
    return value


def _validate_model_relation(unique_id: str, node: ManifestNode) -> None:
    database = _required_relation_field(unique_id, "database", node.database)
    alias = _required_relation_field(unique_id, "alias", node.alias)
    relation_name = _required_relation_field(
        unique_id, "relation_name", node.relation_name
    )
    expected = f'"{database}"."{node.schema}"."{alias}"'
    if relation_name != expected:
        raise ArtifactIntegrityError(
            f"selected model {unique_id} relation_name is inconsistent"
        )


def _validate_model_execution_binding(
    unique_id: str, node: ManifestNode, schemas: ShadowSchemas
) -> None:
    _validate_model_schema(unique_id, node, schemas)
    _validate_model_materialization(unique_id, node)
    _validate_model_relation(unique_id, node)


def _test_model_dependencies(node: ManifestNode) -> set[str]:
    return {
        dependency
        for dependency in node.depends_on_nodes
        if dependency.startswith("model.")
    }


def _raise_unbound_test(unique_id: str) -> None:
    raise ArtifactIntegrityError(
        f"selected test {unique_id} is not bound to selected models"
    )


def _require_test_dependencies(unique_id: str, dependencies: set[str]) -> None:
    if not dependencies:
        _raise_unbound_test(unique_id)


def _require_selected_dependencies(
    unique_id: str,
    dependencies: set[str],
    selected_model_ids: frozenset[str],
) -> None:
    if not dependencies <= selected_model_ids:
        _raise_unbound_test(unique_id)


def _validate_selected_test(
    unique_id: str,
    node: ManifestNode,
    context: _NodeSelectionContext,
) -> tuple[str, ...]:
    dependencies = _test_model_dependencies(node)
    _require_test_dependencies(unique_id, dependencies)
    _require_selected_dependencies(unique_id, dependencies, context.selected_model_ids)
    return ()


def _validate_selected_node(
    unique_id: str,
    node: ManifestNode,
    context: _NodeSelectionContext,
) -> tuple[str, ...]:
    if node.package_name != "seshat_bi":
        raise ArtifactIntegrityError("dbt list selected a foreign package node")
    validators = {
        "model": _validate_selected_model,
        "test": _validate_selected_test,
    }
    validator = validators.get(node.resource_type)
    if validator is None:
        raise ArtifactIntegrityError(
            f"dbt list selected unsupported resource {node.resource_type}"
        )
    return validator(unique_id, node, context)


def _selected_contract_models(
    ids: tuple[str, ...],
    manifest: ManifestSummary,
    selection: SelectionContext,
) -> set[str]:
    selected_models: set[str] = set()
    context = _NodeSelectionContext(
        selector=selection.selector,
        selected_model_ids=_selected_model_ids(ids),
        schemas=selection.schemas,
    )
    for unique_id in ids:
        node = manifest.nodes[unique_id]
        selected_models.update(_validate_selected_node(unique_id, node, context))
    return selected_models


def _require_contract_models(
    selected_models: set[str], contract_model_names: tuple[str, ...]
) -> None:
    expected_models = set(contract_model_names)
    if selected_models == expected_models:
        return
    extras = selected_models - expected_models
    missing = expected_models - selected_models
    detail = sorted(extras or missing)
    raise ArtifactIntegrityError(
        "dbt list model selection does not match contracts: " + ", ".join(detail)
    )


def _legacy_selection_context(
    selector: str, values: tuple[object, ...]
) -> SelectionContext:
    if len(values) != 2:
        raise TypeError(
            "legacy selection validation requires contract names and schemas"
        )
    contract_model_names, schemas = values
    if not isinstance(contract_model_names, tuple):
        raise TypeError("contract model names must be a tuple")
    if not isinstance(schemas, ShadowSchemas):
        raise TypeError("schemas must be ShadowSchemas")
    return SelectionContext(
        selector=selector,
        contract_model_names=cast(tuple[str, ...], contract_model_names),
        schemas=schemas,
    )


def _selection_context(
    context_or_selector: SelectionContext | str,
    legacy_values: tuple[object, ...],
) -> SelectionContext:
    if isinstance(context_or_selector, SelectionContext):
        if legacy_values:
            raise TypeError("SelectionContext cannot be combined with legacy values")
        return context_or_selector
    return _legacy_selection_context(context_or_selector, legacy_values)


def resolve_selected_ids(
    stdout: str,
    manifest: ManifestSummary,
    context_or_selector: SelectionContext | str,
    *legacy_values: object,
) -> tuple[str, ...]:
    """Validate newline-delimited `dbt ls --output json` node identities."""

    selection = _selection_context(context_or_selector, legacy_values)
    ids = _parse_list_output(stdout)
    _require_list_selection(ids)
    _require_distinct_list_ids(ids)
    _require_manifest_nodes(ids, manifest)
    selected_models = _selected_contract_models(ids, manifest, selection)
    _require_contract_models(selected_models, selection.contract_model_names)
    return tuple(sorted(ids))


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ArtifactIntegrityError(
            f"governance input is unavailable: {path.name}"
        ) from exc


def _run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{token_hex(4)}"


def _successful(result: InvocationResult, label: str) -> None:
    if result.return_code != 0:
        raise ArtifactIntegrityError(
            f"dbt {label} failed during non-database planning: {result.stderr}"
        )


def _require_gate_allowed(gate: GateDecision) -> None:
    if not gate.allowed:
        codes = ", ".join(blocker.code for blocker in gate.blocking_reasons)
        raise PlanDrift(f"Mapping Ready gate blocks dbt planning: {codes}")


def _require_gate_approval(gate: GateDecision) -> MappingApproval:
    if gate.approval is None:
        codes = ", ".join(blocker.code for blocker in gate.blocking_reasons)
        raise PlanDrift(f"Mapping Ready gate blocks dbt planning: {codes}")
    return gate.approval


def _approved_mapping(root: Path, table_id: str) -> tuple[WorkingSet, MappingApproval]:
    working_set = resolve_working_set(root, table_id)
    gate = evaluate_mapping_gate(working_set)
    _require_gate_allowed(gate)
    return working_set, _require_gate_approval(gate)


def _validated_project(
    root: Path, working_set: WorkingSet, target_schema: str | None
) -> ProjectValidation:
    project = validate_project(root, working_set, target_schema=target_schema)
    if not project.valid:
        codes = ", ".join(blocker.code for blocker in project.blocking_reasons)
        raise PlanDrift(f"dbt project validation blocks planning: {codes}")
    return project


def _planning_context(
    root: Path,
    table_id: str,
    project: ProjectValidation,
    environment: dict[str, str],
) -> RunContext:
    run_dir = root / ".seshat" / "dbt" / "runs" / _run_id()
    return RunContext(
        repo_root=root,
        project_dir=root / "dbt",
        profiles_dir=root,
        operation=Operation.PARSE,
        table_id=table_id,
        selector=project.selector_name,
        target=project.target_name,
        run_dir=run_dir,
        environment=environment,
    )


def _run_preflight(base: RunContext, runner: DbtRunner) -> InvocationResult:
    with target_lock(base.repo_root, base.table_id, base.target):
        parse_result = runner(base, build_dbt_argv(Operation.PARSE, base))
        _successful(parse_result, "parse")
        list_context = replace(base, operation=Operation.LIST)
        list_result = runner(list_context, build_dbt_argv(Operation.LIST, list_context))
        _successful(list_result, "list")
    return list_result


def _build_plan(context: _PlanBuildContext) -> ExecutionPlan:
    working_set = context.working_set
    project = context.project
    manifest = context.manifest
    mapping_path = working_set.source_map.relative_to(context.root).as_posix()
    return ExecutionPlan(
        schema_version=2,
        table_id=context.table_id,
        mapping=MappingBinding(
            path=mapping_path,
            git_blob=working_set.source_map_revision,
            sha256=working_set.source_map_sha256,
            readiness_sha256=_sha256(working_set.readiness_status),
            unresolved_questions_sha256=_sha256(working_set.unresolved_questions),
            approval_id=context.approval.approval_id,
        ),
        fact=context.fact,
        project=ProjectBinding(path="dbt", sha256=project.project_fingerprint),
        runtime=RuntimeBinding(
            dbt_core=DBT_CORE_VERSION,
            dbt_adapter="dbt-postgres",
            dbt_adapter_version=DBT_POSTGRES_VERSION,
            profile=project.profile_name,
            target=project.target_name,
            selector=project.selector_name,
        ),
        schemas=project.schemas,
        manifest=ManifestBinding(
            schema_uri=manifest.schema_uri,
            semantic_sha256=manifest.semantic_sha256,
        ),
        selected_unique_ids=context.selected,
    )


def create_plan(repo_root: Path, table_id: str, runner: DbtRunner) -> ExecutionPlan:
    """Run governed parse/list preflight and bind every accepted plan fact."""

    root = Path(repo_root).resolve()
    working_set, approval = _approved_mapping(root, table_id)
    fact = load_fact_semantics(working_set.source_map)
    environment = load_child_environment(root)
    target_schema = environment.get("SESHAT_DBT_SCHEMA") or None
    project = _validated_project(root, working_set, target_schema)
    base = _planning_context(root, table_id, project, environment)
    list_result = _run_preflight(base, runner)
    manifest = load_manifest(list_result.target_dir / "manifest.json")
    selected = resolve_selected_ids(
        list_result.stdout,
        manifest,
        SelectionContext(
            selector=project.selector_name,
            contract_model_names=tuple(
                contract.name for contract in project.model_contracts
            ),
            schemas=project.schemas,
        ),
    )
    return _build_plan(
        _PlanBuildContext(
            root=root,
            table_id=table_id,
            working_set=working_set,
            approval=approval,
            fact=fact,
            project=project,
            manifest=manifest,
            selected=selected,
        )
    )
