"""Operational semantic/live/run state composed into Portfolio Watch."""

from __future__ import annotations

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
        "name: TotalSales\ndefinition: {}\nreadiness:\n"
        "  status: pass\n  evidence: [metric-owner-approved]\n",
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
        "table 'sales'\n\tmeasure TotalSales = SUM(Sales[amount])\n", encoding="utf-8"
    )


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
        tmp_path, "scope_alpha", current_stage="semantic_model_ready"
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
