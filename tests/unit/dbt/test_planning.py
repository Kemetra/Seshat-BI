from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _sample_plan():
    from seshat.dbt.contracts import (
        ExecutionPlan,
        FactBinding,
        ManifestBinding,
        MappingBinding,
        ProjectBinding,
        RuntimeBinding,
        ShadowSchemas,
    )

    return ExecutionPlan(
        schema_version=2,
        table_id="retail_store_sales",
        fact=FactBinding(
            name="fact_retail_store_sales",
            business_key=("transaction_id",),
            additive_money_measures=("total_spent",),
        ),
        mapping=MappingBinding(
            path="mappings/retail_store_sales/source-map.yaml",
            git_blob="b" * 40,
            sha256="c" * 64,
            readiness_sha256="d" * 64,
            unresolved_questions_sha256="e" * 64,
            approval_id="approval-1",
        ),
        project=ProjectBinding(path="dbt", sha256="f" * 64),
        runtime=RuntimeBinding(
            dbt_core="1.12.0",
            dbt_adapter="dbt-postgres",
            dbt_adapter_version="1.10.2",
            profile="seshat_bi_warehouse",
            target="shadow",
            selector="seshat_table_retail_store_sales",
        ),
        schemas=ShadowSchemas(
            silver="seshat_dbt_shadow_silver",
            gold="seshat_dbt_shadow_gold",
            audit="seshat_dbt_shadow_audit",
        ),
        manifest=ManifestBinding(
            schema_uri="https://schemas.getdbt.com/dbt/manifest/v12.json",
            semantic_sha256="a" * 64,
        ),
        selected_unique_ids=(
            "model.seshat_bi.fact_retail_store_sales",
            "model.seshat_bi.stg_retail_store_sales",
            "test.seshat_bi.not_null_fact_transaction_id.abc123",
        ),
    )


def test_plan_digest_is_deterministic() -> None:
    from seshat.dbt.planning import canonical_plan_bytes, plan_digest

    plan = _sample_plan()

    assert plan_digest(plan) == plan_digest(plan)
    assert len(plan_digest(plan)) == 64
    assert b"generated_at" not in canonical_plan_bytes(plan)
    assert b"C:\\" not in canonical_plan_bytes(plan)


def _changed_bound_fact(plan, field: str):
    changes = {
        "mapping": replace(plan, mapping=replace(plan.mapping, sha256="0" * 64)),
        "fact": replace(
            plan,
            fact=replace(plan.fact, additive_money_measures=("net_amount",)),
        ),
        "project": replace(plan, project=replace(plan.project, sha256="0" * 64)),
        "runtime": replace(
            plan,
            runtime=replace(plan.runtime, selector="seshat_table_changed"),
        ),
        "schemas": replace(
            plan,
            schemas=replace(plan.schemas, silver="changed_shadow_silver"),
        ),
        "manifest": replace(
            plan,
            manifest=replace(plan.manifest, semantic_sha256="0" * 64),
        ),
        "selected_unique_ids": replace(
            plan,
            selected_unique_ids=(
                *plan.selected_unique_ids,
                "test.seshat_bi.extra.123",
            ),
        ),
    }
    return changes[field]


@pytest.mark.parametrize(
    "field",
    (
        "mapping",
        "fact",
        "project",
        "runtime",
        "schemas",
        "manifest",
        "selected_unique_ids",
    ),
)
def test_each_bound_fact_changes_the_digest(field: str) -> None:
    from seshat.dbt.planning import plan_digest

    plan = _sample_plan()
    changed = _changed_bound_fact(plan, field)

    assert plan_digest(changed) != plan_digest(plan)


def test_require_accepted_plan_uses_exact_digest() -> None:
    from seshat.dbt.planning import PlanDrift, plan_digest, require_accepted_plan

    plan = _sample_plan()
    require_accepted_plan(plan_digest(plan), plan)

    with pytest.raises(PlanDrift, match="accepted plan"):
        require_accepted_plan("0" * 64, plan)


def test_save_plan_writes_atomic_envelope_to_fixed_local_path(tmp_path: Path) -> None:
    from seshat.dbt.planning import plan_digest, save_plan

    plan = _sample_plan()
    path = save_plan(tmp_path, plan)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path == (
        tmp_path / ".seshat" / "dbt" / "plans" / "retail_store_sales-shadow.json"
    )
    assert payload["digest"] == plan_digest(plan)
    assert payload["plan"]["table_id"] == "retail_store_sales"
    assert not list(path.parent.glob("*.tmp"))


@pytest.mark.parametrize(
    ("business_key", "money", "message"),
    (
        (("Bad-Name",), ("total_spent",), "business_key"),
        ((), ("total_spent",), "business_key"),
        (("invoice_no", "invoice_no"), ("total_spent",), "business_key"),
        (
            ("transaction_id",),
            ("total_spent", "net_amount"),
            "additive_money_measures",
        ),
        (
            ("transaction_id",),
            ("total_spent", "total_spent"),
            "additive_money_measures",
        ),
        (("total_spent",), ("total_spent",), "business_key"),
        # Malformed-but-valid-JSON element types must yield the handled
        # PlanDrift, never an uncaught TypeError from sorting/set-building.
        (("transaction_id",), (1, "amount"), "additive_money_measures"),
        (("transaction_id",), ({"col": "amount"},), "additive_money_measures"),
        ((None, "line_no"), ("total_spent",), "business_key"),
    ),
)
def test_save_plan_rejects_invalid_fact_binding(
    tmp_path: Path,
    business_key: tuple[str, ...],
    money: tuple[str, ...],
    message: str,
) -> None:
    from seshat.dbt.contracts import FactBinding
    from seshat.dbt.planning import PlanDrift, save_plan

    plan = replace(
        _sample_plan(),
        fact=FactBinding(
            name="fact_retail_store_sales",
            business_key=business_key,
            additive_money_measures=money,
        ),
    )

    with pytest.raises(PlanDrift, match=message):
        save_plan(tmp_path, plan)


def test_save_plan_accepts_a_factless_empty_money_set(tmp_path: Path) -> None:
    """A factless fact (templates/factless-fact.yaml: measures [] BY DESIGN)
    legitimately declares zero additive money measures -- the plan must accept
    the empty set."""
    from seshat.dbt.contracts import FactBinding
    from seshat.dbt.planning import save_plan

    plan = replace(
        _sample_plan(),
        fact=FactBinding(
            name="fact_retail_store_sales",
            business_key=("transaction_id",),
            additive_money_measures=(),
        ),
    )

    save_plan(tmp_path, plan)  # no raise


def test_save_plan_rejects_table_path_escape(tmp_path: Path) -> None:
    from seshat.dbt.planning import PlanDrift, save_plan

    plan = replace(_sample_plan(), table_id="../outside")

    with pytest.raises(PlanDrift, match="table_id"):
        save_plan(tmp_path, plan)

    assert not (tmp_path / "outside-shadow.json").exists()


@pytest.mark.parametrize(
    ("stdout", "message"),
    (
        ("not-json\n", "JSON"),
        (
            '{"unique_id":"model.seshat_bi.fact_retail_store_sales"}\n'
            '{"unique_id":"model.seshat_bi.fact_retail_store_sales"}\n',
            "duplicate",
        ),
        (
            '{"unique_id":"model.seshat_bi.outside"}\n',
            "manifest",
        ),
    ),
)
def test_resolve_selected_ids_rejects_invalid_list_output(
    stdout: str, message: str
) -> None:
    from seshat.dbt.artifacts import ArtifactIntegrityError, load_manifest
    from seshat.dbt.planning import resolve_selected_ids

    fixtures = Path(__file__).resolve().parents[2] / "fixtures" / "dbt_artifacts"
    manifest = load_manifest(fixtures / "manifest-v12.json")

    with pytest.raises(ArtifactIntegrityError, match=message):
        resolve_selected_ids(
            stdout,
            manifest,
            "seshat_table_retail_store_sales",
            ("fact_retail_store_sales", "stg_retail_store_sales"),
            _sample_plan().schemas,
        )


def test_resolve_selected_ids_allows_bound_models_and_generated_tests() -> None:
    from seshat.dbt.artifacts import load_manifest
    from seshat.dbt.planning import SelectionContext, resolve_selected_ids

    fixtures = Path(__file__).resolve().parents[2] / "fixtures" / "dbt_artifacts"
    manifest = load_manifest(fixtures / "manifest-v12.json")
    stdout = "\n".join(
        json.dumps({"unique_id": unique_id})
        for unique_id in reversed(tuple(manifest.nodes))
    )

    selected = resolve_selected_ids(
        stdout,
        manifest,
        SelectionContext(
            selector="seshat_table_retail_store_sales",
            contract_model_names=(
                "fact_retail_store_sales",
                "stg_retail_store_sales",
            ),
            schemas=_sample_plan().schemas,
        ),
    )

    assert selected == tuple(sorted(manifest.nodes))


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (
            lambda node: node.update(schema="public"),
            "protected schema",
        ),
        (
            lambda node: node.update(schema="seshat_dbt_shadow_silver"),
            "governed gold schema",
        ),
        (
            lambda node: node["config"].update(materialized="incremental"),
            "materialization",
        ),
        (
            lambda node: node.update(relation_name='"wrong"."relation"'),
            "relation_name",
        ),
    ),
)
def test_resolve_selected_ids_rejects_unsafe_model_execution_binding(
    tmp_path: Path, mutation, message: str
) -> None:
    from seshat.dbt.artifacts import (
        ArtifactIntegrityError,
        load_manifest,
    )
    from seshat.dbt.planning import resolve_selected_ids

    fixtures = Path(__file__).resolve().parents[2] / "fixtures" / "dbt_artifacts"
    payload = json.loads((fixtures / "manifest-v12.json").read_text(encoding="utf-8"))
    mutation(payload["nodes"]["model.seshat_bi.fact_retail_store_sales"])
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    manifest = load_manifest(path)
    stdout = "\n".join(
        json.dumps({"unique_id": unique_id}) for unique_id in manifest.nodes
    )

    with pytest.raises(ArtifactIntegrityError, match=message):
        resolve_selected_ids(
            stdout,
            manifest,
            "seshat_table_retail_store_sales",
            ("fact_retail_store_sales", "stg_retail_store_sales"),
            _sample_plan().schemas,
        )


def _planning_working_set(tmp_path: Path):
    from seshat.dbt.contracts import WorkingSet

    mapping_dir = tmp_path / "mappings" / "retail_store_sales"
    mapping_dir.mkdir(parents=True)
    source_map = mapping_dir / "source-map.yaml"
    readiness = mapping_dir / "readiness-status.yaml"
    questions = mapping_dir / "unresolved-questions.md"
    source_map.write_text(
        "table_id: retail_store_sales\n"
        "gold_star:\n"
        "  fact:\n"
        '    name: "gold.fact_retail_store_sales"\n'
        '    business_key: "transaction_id"\n'
        "    measures:\n"
        '      - "total_spent"\n'
        "    additive_money_measures:\n"
        '      - "total_spent"\n',
        encoding="utf-8",
    )
    readiness.write_text("stages: {}\n", encoding="utf-8")
    questions.write_text("Gate status: CLEARED\n", encoding="utf-8")
    (tmp_path / "dbt").mkdir()
    return WorkingSet(
        repo_root=tmp_path,
        table_id="retail_store_sales",
        mapping_dir=mapping_dir,
        source_map=source_map,
        readiness_status=readiness,
        unresolved_questions=questions,
        source_map_revision="b" * 40,
        source_map_sha256="c" * 64,
    )


def _planning_gate():
    from seshat.dbt.contracts import GateDecision, MappingApproval

    approval = MappingApproval(
        stage="mapping_ready",
        owner="Data Owner",
        at="2026-07-16",
        note="approved",
        approval_id="approval-1",
    )
    return GateDecision(
        allowed=True,
        table_id="retail_store_sales",
        mapping_status="pass",
        approval=approval,
        mirror_cleared=True,
        blocking_reasons=(),
    )


def _planning_contract(name: str):
    from seshat.dbt.contracts import ModelContract

    return ModelContract(
        name=name,
        table_id="retail_store_sales",
        source_map="mappings/retail_store_sales/source-map.yaml",
        source_map_revision="b" * 40,
        grain="approved grain",
        business_key=("id",),
        authority="derived",
        columns=(),
    )


def _planning_project():
    from seshat.dbt.contracts import ProjectValidation, ShadowSchemas

    return ProjectValidation(
        valid=True,
        project_fingerprint="f" * 64,
        selector_name="seshat_table_retail_store_sales",
        profile_name="seshat_bi_warehouse",
        target_name="shadow",
        schemas=ShadowSchemas(
            silver="seshat_dbt_shadow_silver",
            gold="seshat_dbt_shadow_gold",
            audit="seshat_dbt_shadow_audit",
        ),
        model_contracts=tuple(
            _planning_contract(name)
            for name in (
                "fact_retail_store_sales",
                "stg_retail_store_sales",
            )
        ),
        blocking_reasons=(),
    )


@dataclass(frozen=True)
class _PlanningStubs:
    working_set: object
    gate: object
    project: object


def _stub_planning_dependencies(
    planning, monkeypatch: pytest.MonkeyPatch, stubs: _PlanningStubs
) -> None:
    monkeypatch.setattr(
        planning, "resolve_working_set", lambda root, table: stubs.working_set
    )
    monkeypatch.setattr(planning, "evaluate_mapping_gate", lambda value: stubs.gate)
    monkeypatch.setattr(
        planning,
        "validate_project",
        lambda root, value, target_schema=None: stubs.project,
    )
    monkeypatch.setattr(planning, "load_child_environment", lambda root: {})
    monkeypatch.setattr(
        planning,
        "build_dbt_argv",
        lambda operation, context: ("dbt", operation.value),
    )


def _planning_runner(fixtures: Path, listed_ids: tuple[str, ...]):
    from seshat.dbt.contracts import InvocationResult

    def runner(context, argv):
        target_dir = context.run_dir / "target"
        log_dir = context.run_dir / "logs"
        target_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "manifest.json").write_bytes(
            (fixtures / "manifest-v12.json").read_bytes()
        )
        stdout = (
            "\n".join(json.dumps({"unique_id": item}) for item in listed_ids)
            if context.operation.value == "list"
            else ""
        )
        return InvocationResult(
            invocation_id=context.run_dir.name,
            operation=context.operation,
            argv_summary=argv[1:],
            return_code=0,
            started_at="2026-07-16T12:00:00Z",
            completed_at="2026-07-16T12:00:01Z",
            stdout=stdout,
            stderr="",
            target_dir=target_dir,
            log_dir=log_dir,
        )

    return runner


def test_create_plan_binds_gate_project_manifest_and_exact_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import seshat.dbt.planning as planning

    working_set = _planning_working_set(tmp_path)
    gate = _planning_gate()
    project = _planning_project()
    _stub_planning_dependencies(
        planning,
        monkeypatch,
        _PlanningStubs(
            working_set=working_set,
            gate=gate,
            project=project,
        ),
    )
    fixtures = Path(__file__).resolve().parents[2] / "fixtures" / "dbt_artifacts"
    listed_ids = (
        "test.seshat_bi.not_null_fact_transaction_id.abc123",
        "model.seshat_bi.stg_retail_store_sales",
        "model.seshat_bi.fact_retail_store_sales",
    )

    plan = planning.create_plan(
        tmp_path,
        "retail_store_sales",
        _planning_runner(fixtures, listed_ids),
    )

    assert plan.mapping.git_blob == "b" * 40
    assert plan.mapping.approval_id == "approval-1"
    assert plan.fact.business_key == ("transaction_id",)
    assert plan.fact.additive_money_measures == ("total_spent",)
    assert plan.project.sha256 == "f" * 64
    assert plan.selected_unique_ids == tuple(sorted(listed_ids))
    assert (
        plan.manifest.semantic_sha256
        == planning.load_manifest(fixtures / "manifest-v12.json").semantic_sha256
    )
    assert b"2026-07-16" not in planning.canonical_plan_bytes(plan)


def _failed_result(stdout: str, stderr: str):
    """A non-zero-return InvocationResult, mirroring `_planning_runner`'s shape.

    dbt PARSE runs under `--log-format json`, so a Compilation Error lands as
    JSON log events on stdout while stderr is typically empty (issue #341).
    """
    from seshat.dbt.contracts import InvocationResult, Operation

    return InvocationResult(
        invocation_id="run-341",
        operation=Operation.PARSE,
        argv_summary=("parse",),
        return_code=1,
        started_at="2026-07-19T12:00:00Z",
        completed_at="2026-07-19T12:00:01Z",
        stdout=stdout,
        stderr=stderr,
        target_dir=Path("target"),
        log_dir=Path("logs"),
    )


def test_successful_surfaces_stderr_when_present() -> None:
    import seshat.dbt.planning as planning

    result = _failed_result(stdout="", stderr="boom on stderr")
    with pytest.raises(planning.ArtifactIntegrityError) as exc:
        planning._successful(result, "parse")
    assert "boom on stderr" in str(exc.value)


def test_successful_surfaces_json_log_error_from_stdout_when_stderr_empty() -> None:
    """The #341 bug: PARSE fails, stderr is empty, and the real Compilation
    Error sits in stdout as JSON log events. `_successful` must surface it, not
    emit an empty-after-colon message."""
    import seshat.dbt.planning as planning

    stdout = "\n".join(
        [
            json.dumps({"info": {"level": "info", "msg": "Running with dbt=1.12"}}),
            json.dumps(
                {
                    "info": {
                        "level": "error",
                        "msg": (
                            "Compilation Error in model stg_sales_c086_raw: depends "
                            "on a source named 'bronze.sales_c086_raw' which was not "
                            "found"
                        ),
                    }
                }
            ),
        ]
    )
    result = _failed_result(stdout=stdout, stderr="")
    with pytest.raises(planning.ArtifactIntegrityError) as exc:
        planning._successful(result, "parse")
    message = str(exc.value)
    assert "Compilation Error in model stg_sales_c086_raw" in message
    assert "which was not found" in message
    # never the empty-after-colon symptom from the issue
    assert not message.rstrip().endswith("planning:")


def test_successful_falls_back_to_raw_stdout_when_not_json() -> None:
    """If stderr is empty and stdout is not JSON log events, surface the raw
    stdout rather than an empty message."""
    import seshat.dbt.planning as planning

    result = _failed_result(stdout="plain text compilation error here", stderr="")
    with pytest.raises(planning.ArtifactIntegrityError) as exc:
        planning._successful(result, "parse")
    assert "plain text compilation error here" in str(exc.value)


def test_successful_reports_no_detail_marker_when_both_streams_empty() -> None:
    """Degenerate case: both streams empty. The message must still be
    self-explanatory (a marker), never a bare trailing colon."""
    import seshat.dbt.planning as planning

    result = _failed_result(stdout="", stderr="")
    with pytest.raises(planning.ArtifactIntegrityError) as exc:
        planning._successful(result, "parse")
    message = str(exc.value).rstrip()
    assert not message.endswith("planning:")
    assert not message.endswith(":")
