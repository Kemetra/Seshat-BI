"""Operational semantic/live/run state composed into Portfolio Watch."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat import portfolio_watch as pw
from seshat.dagster_adapter import evidence
from tests.fixtures.portfolio_watch.builders import (
    commit_all,
    generic_artifact,
    init_git_repo,
    write_json_artifact,
    write_readiness_status,
)

pytestmark = pytest.mark.unit


def _write_bound_contract(root: Path, scope: str = "scope_alpha") -> None:
    contract = root / "mappings" / scope / "metrics" / "TotalSales.yaml"
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text(
        "name: TotalSales\nowner: metric_owner\n"
        "binds_to: {gold_table: gold.sales}\n"
        "definition: {kind: base, aggregation: sum, filter: []}\nreadiness:\n"
        "  status: pass\n  evidence: [metric-owner-approved]\n"
        "  blocking_reasons: []\n",
        encoding="utf-8",
    )
    tmdl = (
        root
        / "powerbi"
        / "Model.SemanticModel"
        / "definition"
        / "tables"
        / "sales.tmdl"
    )
    tmdl.parent.mkdir(parents=True, exist_ok=True)
    tmdl.write_text(
        "table 'gold sales'\n\tmeasure TotalSales = SUM(Sales[amount])\n",
        encoding="utf-8",
    )


def _semantic_approval() -> list[dict[str, str]]:
    return [
        {
            "stage": "semantic_model_ready",
            "owner": "Ada Lovelace (metric_owner)",
            "at": "2026-07-22",
            "note": "approved metric contract TotalSales",
        }
    ]


def _finalize_live_run(root: Path, scope: str = "scope_alpha") -> None:
    writer = evidence.EvidenceWriter(root, "run-live-001")
    writer.record(
        evidence.AssetOutcome(
            asset="live_validate",
            table=scope,
            gate_command="seshat validate",
            exit_code=0,
            measured={},
            outcome="materialized",
        )
    )
    evidence.finalize_run(
        root,
        "run-live-001",
        [scope],
        evidence.RunMeta(started="2026-07-22T00:00:00Z"),
    )


def _scope(summary: dict) -> dict:
    return summary["scopes"][0]


def _replace_run_records(root: Path, records: list[object]) -> None:
    run_dir = root / ".seshat" / "dagster" / "runs" / "run-live-001"
    records_path = run_dir / "records.jsonl"
    records_path.write_text(
        "".join(f"{json.dumps(record)}{chr(10)}" for record in records),
        encoding="utf-8",
    )
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["records_sha256"] = evidence.records_sha256(records_path)
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + chr(10), encoding="utf-8"
    )


def test_missing_metrics_and_live_evidence_degrade_to_categorical_states(
    tmp_path: Path,
) -> None:
    write_readiness_status(tmp_path, "scope_alpha", current_stage="gold_ready")

    scope = _scope(pw.build_portfolio_watch_summary(tmp_path))

    assert scope["contract_binding_state"] == "missing"
    assert scope["live_validation_state"] == "pending_live"
    assert scope["last_dagster_run"] == "unavailable"


def test_approved_bound_contract_and_current_live_run_are_verified(
    tmp_path: Path,
) -> None:
    write_readiness_status(
        tmp_path,
        "scope_alpha",
        current_stage="semantic_model_ready",
        approvals=_semantic_approval(),
    )
    _write_bound_contract(tmp_path)
    write_json_artifact(
        tmp_path,
        "scope_alpha",
        "metric-drift-findings.json",
        generic_artifact(class_="pass"),
    )
    init_git_repo(tmp_path)
    _finalize_live_run(tmp_path)

    scope = _scope(pw.build_portfolio_watch_summary(tmp_path))

    assert scope["contract_binding_state"] == "verified"
    assert scope["live_validation_state"] == "verified"
    assert scope["last_dagster_run"] == "verified"


def test_live_run_matches_mapping_directory_when_display_table_differs(
    tmp_path: Path,
) -> None:
    write_readiness_status(
        tmp_path,
        "retail_store_sales",
        table="bronze.retail_store_sales",
        current_stage="gold_ready",
    )
    init_git_repo(tmp_path)
    _finalize_live_run(tmp_path, "retail_store_sales")

    scope = _scope(pw.build_portfolio_watch_summary(tmp_path))

    assert scope["scope_id"] == "bronze.retail_store_sales"
    assert scope["live_validation_state"] == "verified"
    assert scope["last_dagster_run"] == "verified"


def _add_untracked_contract(root: Path) -> None:
    extra = root / "mappings" / "scope_alpha" / "metrics" / "Untracked.yaml"
    extra.write_text("name: Untracked\n", encoding="utf-8")


def _dirty_model(root: Path) -> None:
    tmdl = next((root / "powerbi").rglob("sales.tmdl"))
    tmdl.write_text(
        tmdl.read_text(encoding="utf-8") + "// uncommitted edit\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "mutate",
    (_add_untracked_contract, _dirty_model),
    ids=("untracked-contract", "dirty-model"),
)
def test_uncommitted_semantic_inputs_block_verified_contract_state(
    tmp_path: Path, mutate
) -> None:
    write_readiness_status(
        tmp_path,
        "scope_alpha",
        current_stage="semantic_model_ready",
        approvals=_semantic_approval(),
    )
    _write_bound_contract(tmp_path)
    init_git_repo(tmp_path)
    mutate(tmp_path)

    assert pw.contract_binding_state(tmp_path, "scope_alpha") == "blocked"


def test_uncontracted_measure_on_bound_table_blocks_contract_state(
    tmp_path: Path,
) -> None:
    write_readiness_status(
        tmp_path,
        "scope_alpha",
        current_stage="semantic_model_ready",
        approvals=_semantic_approval(),
    )
    _write_bound_contract(tmp_path)
    tmdl = next((tmp_path / "powerbi").rglob("sales.tmdl"))
    tmdl.write_text(
        tmdl.read_text(encoding="utf-8")
        + "\tmeasure UncontractedMargin = SUM(Sales[margin])\n",
        encoding="utf-8",
    )

    scope = _scope(pw.build_portfolio_watch_summary(tmp_path))

    assert scope["contract_binding_state"] == "blocked"
    assert scope["contract_binding_owner"] == "metric owner"


def test_unbound_contract_is_blocked_with_metric_owner_handoff(tmp_path: Path) -> None:
    write_readiness_status(
        tmp_path, "scope_alpha", current_stage="semantic_model_ready"
    )
    contract = tmp_path / "mappings" / "scope_alpha" / "metrics" / "TotalSales.yaml"
    contract.parent.mkdir(parents=True)
    contract.write_text("name: TotalSales\n", encoding="utf-8")

    scope = _scope(pw.build_portfolio_watch_summary(tmp_path))

    assert scope["contract_binding_state"] == "blocked"
    assert scope["contract_binding_owner"] == "metric owner"


def test_run_from_an_older_source_revision_is_stale(tmp_path: Path) -> None:
    write_readiness_status(tmp_path, "scope_alpha", current_stage="gold_ready")
    init_git_repo(tmp_path)
    _finalize_live_run(tmp_path)
    (tmp_path / "later.txt").write_text("advance\n", encoding="utf-8")
    commit_all(tmp_path, "advance")

    scope = _scope(pw.build_portfolio_watch_summary(tmp_path))

    assert scope["last_dagster_run"] == "stale"
    assert scope["live_validation_state"] == "stale"


def test_run_from_dirty_workspace_is_stale(tmp_path: Path) -> None:
    status = write_readiness_status(tmp_path, "scope_alpha", current_stage="gold_ready")
    init_git_repo(tmp_path)
    status.write_text(
        status.read_text(encoding="utf-8") + "# uncommitted governed edit\n",
        encoding="utf-8",
    )
    _finalize_live_run(tmp_path)

    scope = _scope(pw.build_portfolio_watch_summary(tmp_path))

    assert scope["last_dagster_run"] == "stale"
    assert scope["live_validation_state"] == "stale"


@pytest.mark.parametrize(
    "invalid_records",
    (
        [{"asset": "live_validate", "table": "scope_alpha", "outcome": "materialized"}],
        ["not-an-object"],
    ),
)
def test_invalid_run_schema_never_becomes_live_proof(
    tmp_path: Path, invalid_records: list[object]
) -> None:
    write_readiness_status(tmp_path, "scope_alpha", current_stage="gold_ready")
    init_git_repo(tmp_path)
    _finalize_live_run(tmp_path)
    _replace_run_records(tmp_path, invalid_records)

    scope = _scope(pw.build_portfolio_watch_summary(tmp_path))

    assert scope["last_dagster_run"] == "invalid"
    assert scope["live_validation_state"] == "pending_live"


@pytest.mark.parametrize(
    ("field", "value"),
    (("gate_command", ""), ("measured", []), ("ts", 7)),
)
def test_schema_invalid_live_record_values_never_become_proof(
    tmp_path: Path, field: str, value: object
) -> None:
    write_readiness_status(tmp_path, "scope_alpha", current_stage="gold_ready")
    init_git_repo(tmp_path)
    _finalize_live_run(tmp_path)
    _summary, records = evidence.load_run(tmp_path, "run-live-001")
    records[-1][field] = value
    _replace_run_records(tmp_path, records)

    scope = _scope(pw.build_portfolio_watch_summary(tmp_path))

    assert scope["last_dagster_run"] == "invalid"
    assert scope["live_validation_state"] == "pending_live"
