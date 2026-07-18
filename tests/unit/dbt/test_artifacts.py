from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "dbt_artifacts"


def _write_mutation(tmp_path: Path, fixture: str, mutate) -> Path:
    payload = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
    mutate(payload)
    path = tmp_path / fixture
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


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
            name="fct_sales_rss",
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
            "model.seshat_bi.fct_sales_rss",
            "model.seshat_bi.stg_retail_store_sales",
            "model.seshat_bi.dim_customer_rss",
            "model.seshat_bi.dim_product_rss",
            "model.seshat_bi.dim_payment_method_rss",
            "model.seshat_bi.dim_location_rss",
            "model.seshat_bi.dim_date_rss",
            "test.seshat_bi.not_null_fact_transaction_id.abc123",
        ),
    )


def test_load_manifest_retains_only_allowlisted_fields() -> None:
    from seshat.dbt.artifacts import load_manifest

    manifest = load_manifest(FIXTURES / "manifest-v12.json")

    assert manifest.schema_uri.endswith("manifest/v12.json")
    assert manifest.dbt_version == "1.12.0"
    assert len(manifest.sha256) == 64
    node = manifest.nodes["model.seshat_bi.fact_retail_store_sales"]
    assert node.depends_on_nodes == ("model.seshat_bi.stg_retail_store_sales",)
    assert node.materialized == "table"
    assert node.database == "seshat_verify"
    assert node.alias == "fact_retail_store_sales"
    assert node.relation_name.endswith(
        '."seshat_dbt_shadow_gold"."fact_retail_store_sales"'
    )
    assert not hasattr(node, "compiled_code")


def test_manifest_semantic_hash_ignores_volatile_invocation_metadata(
    tmp_path: Path,
) -> None:
    from seshat.dbt.artifacts import load_manifest

    payload = json.loads((FIXTURES / "manifest-v12.json").read_text(encoding="utf-8"))
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    payload["metadata"].update(
        generated_at="2026-07-16T20:00:00Z",
        invocation_id="11111111-1111-1111-1111-111111111111",
    )
    first.write_text(json.dumps(payload), encoding="utf-8")
    payload["metadata"].update(
        generated_at="2026-07-16T20:01:00Z",
        invocation_id="22222222-2222-2222-2222-222222222222",
    )
    second.write_text(json.dumps(payload), encoding="utf-8")

    first_summary = load_manifest(first)
    second_summary = load_manifest(second)

    assert first_summary.sha256 != second_summary.sha256
    assert first_summary.semantic_sha256 == second_summary.semantic_sha256


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (
            lambda value: value["metadata"].update(
                dbt_schema_version="https://schemas.getdbt.com/dbt/manifest/v13.json"
            ),
            "manifest schema",
        ),
        (
            lambda value: value["metadata"].update(dbt_version="1.13.0"),
            "dbt version",
        ),
        (
            lambda value: value["nodes"][
                "model.seshat_bi.fact_retail_store_sales"
            ].update(unique_id="model.seshat_bi.wrong"),
            "dictionary key",
        ),
    ),
)
def test_load_manifest_rejects_unsupported_or_inconsistent_content(
    tmp_path: Path, mutation, message: str
) -> None:
    from seshat.dbt.artifacts import ArtifactIntegrityError, load_manifest

    path = _write_mutation(tmp_path, "manifest-v12.json", mutation)

    with pytest.raises(ArtifactIntegrityError, match=message):
        load_manifest(path)


def test_artifact_loaders_reject_malformed_json(tmp_path: Path) -> None:
    from seshat.dbt.artifacts import ArtifactIntegrityError, load_manifest

    path = tmp_path / "manifest.json"
    path.write_text('{"metadata":', encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="valid JSON"):
        load_manifest(path)


def test_load_run_results_normalizes_without_adapter_messages() -> None:
    from seshat.dbt.artifacts import load_run_results

    summary = load_run_results(FIXTURES / "run-results-v6.json")

    assert summary.which == "build"
    assert len(summary.results) == 8
    assert summary.results[0].execution_seconds.as_tuple().exponent <= 0
    assert not hasattr(summary.results[0], "message")


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (
            lambda value: value["metadata"].update(
                dbt_schema_version=(
                    "https://schemas.getdbt.com/dbt/run-results/v7.json"
                )
            ),
            "run-results schema",
        ),
        (lambda value: value["args"].update(which="run"), "args.which"),
        (
            lambda value: value["results"][0].update(status="mystery"),
            "status",
        ),
        (
            lambda value: value["results"].append(value["results"][0]),
            "duplicate",
        ),
    ),
)
def test_load_run_results_rejects_unsupported_content(
    tmp_path: Path, mutation, message: str
) -> None:
    from seshat.dbt.artifacts import ArtifactIntegrityError, load_run_results

    path = _write_mutation(tmp_path, "run-results-v6.json", mutation)

    with pytest.raises(ArtifactIntegrityError, match=message):
        load_run_results(path)


def test_run_results_reject_nodes_outside_accepted_plan(tmp_path: Path) -> None:
    from seshat.dbt.artifacts import (
        ArtifactIntegrityError,
        cross_check_execution,
        load_run_results,
    )

    path = _write_mutation(
        tmp_path,
        "run-results-v6.json",
        lambda value: value["results"].append(
            {
                "unique_id": "model.seshat_bi.outside_plan",
                "status": "success",
                "failures": None,
                "execution_time": 0.1,
            }
        ),
    )
    results = load_run_results(path)

    with pytest.raises(ArtifactIntegrityError, match="outside accepted plan"):
        cross_check_execution(_sample_plan(), results)


def test_run_results_allow_generated_test_bound_in_plan() -> None:
    from seshat.dbt.artifacts import cross_check_execution, load_run_results

    results = load_run_results(FIXTURES / "run-results-v6.json")

    cross_check_execution(_sample_plan(), results)


def test_build_requires_every_planned_node() -> None:
    from seshat.dbt.artifacts import ArtifactIntegrityError, load_run_results

    results = load_run_results(FIXTURES / "run-results-v6.json")
    shortened = replace(results, results=results.results[:-1])

    with pytest.raises(ArtifactIntegrityError, match="missing planned nodes"):
        from seshat.dbt.artifacts import cross_check_execution

        cross_check_execution(_sample_plan(), shortened)
