"""Pinned dbt 1.12/Postgres 1.10 artifact compatibility proof."""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "dbt_artifacts"
TABLE_ID = "retail_store_sales"
SELECTOR = f"seshat_table_{TABLE_ID}"
EXPECTED_MODELS = (
    "audit_retail_store_sales_parity",
    "dim_customer_rss",
    "dim_date_rss",
    "dim_location_rss",
    "dim_payment_method_rss",
    "dim_product_rss",
    "fct_sales_rss",
    "stg_retail_store_sales",
)


def _fixture_execution_plan(manifest, selected: tuple[str, ...]):
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
        table_id=TABLE_ID,
        fact=FactBinding(
            name="fct_sales_rss",
            business_key=("transaction_id",),
            additive_money_measures=("total_spent",),
        ),
        mapping=MappingBinding(
            path=f"mappings/{TABLE_ID}/source-map.yaml",
            git_blob="a" * 40,
            sha256="b" * 64,
            readiness_sha256="c" * 64,
            unresolved_questions_sha256="d" * 64,
            approval_id="named-human-fixture",
        ),
        project=ProjectBinding(path="dbt", sha256="e" * 64),
        runtime=RuntimeBinding(
            dbt_core="1.12.0",
            dbt_adapter="dbt-postgres",
            dbt_adapter_version="1.10.2",
            profile="seshat_bi_warehouse",
            target="shadow",
            selector=SELECTOR,
        ),
        schemas=ShadowSchemas(
            silver="seshat_dbt_shadow_silver",
            gold="seshat_dbt_shadow_gold",
            audit="seshat_dbt_shadow_audit",
        ),
        manifest=ManifestBinding(
            schema_uri=manifest.schema_uri,
            semantic_sha256=manifest.semantic_sha256,
        ),
        selected_unique_ids=selected,
    )


def test_pinned_parse_fixture_has_complete_governed_selection() -> None:
    from seshat.dbt.artifacts import load_manifest
    from seshat.dbt.contracts import ShadowSchemas
    from seshat.dbt.planning import resolve_selected_ids

    path = FIXTURES / "manifest-pinned-v12.json"
    manifest = load_manifest(path)
    selected = resolve_selected_ids(
        (FIXTURES / "list-pinned.jsonl").read_text(encoding="utf-8"),
        manifest,
        SELECTOR,
        EXPECTED_MODELS,
        ShadowSchemas(
            silver="seshat_dbt_shadow_silver",
            gold="seshat_dbt_shadow_gold",
            audit="seshat_dbt_shadow_audit",
        ),
    )

    models = [node for node in manifest.nodes.values() if node.resource_type == "model"]
    tests = [node for node in manifest.nodes.values() if node.resource_type == "test"]
    assert manifest.schema_uri.endswith("/manifest/v12.json")
    assert manifest.dbt_version == "1.12.0"
    assert len(models) == 8
    assert len(tests) == 24
    assert len(selected) == 32
    assert {node.schema for node in models} == {
        "seshat_dbt_shadow_silver",
        "seshat_dbt_shadow_gold",
        "seshat_dbt_shadow_audit",
    }

    text = path.read_text(encoding="utf-8").lower()
    for forbidden in (
        "compiled_code",
        "compiled_sql",
        "invocation_id",
        "generated_at",
        "root_path",
        "password",
    ):
        assert forbidden not in text


def test_pinned_artifacts_round_trip_through_strict_readers() -> None:
    from seshat.dbt.artifacts import (
        cross_check_execution,
        load_manifest,
        load_run_results,
    )

    manifest = load_manifest(FIXTURES / "manifest-v12.json")
    results = load_run_results(FIXTURES / "run-results-v6.json")
    selected = tuple(sorted(result.unique_id for result in results.results))
    plan = _fixture_execution_plan(manifest, selected)

    cross_check_execution(plan, results)

    assert manifest.schema_uri.endswith("/manifest/v12.json")
    assert results.schema_uri.endswith("/run-results/v6.json")
    assert results.dbt_version == "1.12.0"
