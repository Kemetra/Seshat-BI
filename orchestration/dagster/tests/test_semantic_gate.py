"""Fail-closed contract and semantic STOP-edge tests."""

from __future__ import annotations

import pytest
from conftest import TABLE, make_fixture_repo, stub_green_db
from dagster import Failure, build_asset_context
from tower_bi_orchestration import commands
from tower_bi_orchestration.assets import build_table_assets
from tower_bi_orchestration.evidence_writer import EvidenceWriter


def _asset_by_name(assets: list, name: str):
    for asset in assets:
        if asset.key.path[-1] == name:
            return asset
    raise AssertionError(f"asset {name} not found")


def _setup(monkeypatch, root) -> None:
    monkeypatch.setenv("SESHAT_REPO_ROOT", str(root))
    monkeypatch.setenv("SESHAT_DAGSTER_RUN_ID", "semantic-gate-001")


def _record(root, asset: str) -> dict:
    return next(
        row
        for row in EvidenceWriter(root, "semantic-gate-001").records()
        if row["asset"] == asset
    )


def test_metric_contracts_blocks_when_no_contracts_exist(tmp_path, monkeypatch) -> None:
    root = make_fixture_repo(tmp_path)
    _setup(monkeypatch, root)
    metrics = root / "mappings" / TABLE / "metrics"
    for path in metrics.iterdir():
        path.unlink()
    asset = _asset_by_name(build_table_assets(TABLE, root), "metric_contracts")

    with pytest.raises(Failure, match="no approved metric contracts"):
        asset(build_asset_context())

    row = _record(root, "metric_contracts")
    assert row["outcome"] == "blocked"
    assert row["measured"] == {"contracts_found": 0, "approved_contracts": 0}
    assert row["owner"] == "the metric owner"


def test_metric_contracts_blocks_unapproved_contracts(tmp_path, monkeypatch) -> None:
    root = make_fixture_repo(tmp_path)
    _setup(monkeypatch, root)
    contract = root / "mappings" / TABLE / "metrics" / "AMetric.yaml"
    contract.write_text(
        contract.read_text(encoding="utf-8").replace(
            'status: "pass"', "status: blocked"
        ),
        encoding="utf-8",
    )
    asset = _asset_by_name(build_table_assets(TABLE, root), "metric_contracts")

    with pytest.raises(Failure, match="not owner-approved pass"):
        asset(build_asset_context())

    assert _record(root, "metric_contracts")["outcome"] == "blocked"


def test_semantic_failure_stops_before_approval_materializes(
    tmp_path, monkeypatch
) -> None:
    root = make_fixture_repo(tmp_path)
    _setup(monkeypatch, root)
    stub_green_db(monkeypatch)

    def gate(argv, cwd):
        if argv == commands.semantic_argv():
            return 1, "semantic bindings failed"
        return 0, ""

    monkeypatch.setattr(commands, "run_gate_command", gate)
    asset = _asset_by_name(build_table_assets(TABLE, root), "semantic_model")

    with pytest.raises(Failure, match="semantic gate failed"):
        asset(build_asset_context())

    row = _record(root, "semantic_model")
    assert row["outcome"] == "failed"
    assert row["measured"]["output_tail"] == "semantic bindings failed"


def test_static_check_failure_does_not_run_semantic_gate(tmp_path, monkeypatch) -> None:
    root = make_fixture_repo(tmp_path)
    _setup(monkeypatch, root)
    calls: list[list[str]] = []

    def gate(argv, cwd):
        calls.append(argv)
        return 1, "static failed"

    monkeypatch.setattr(commands, "run_gate_command", gate)
    asset = _asset_by_name(build_table_assets(TABLE, root), "semantic_model")

    with pytest.raises(Failure, match="static governance gate failed"):
        asset(build_asset_context())

    assert calls == [commands.checker_argv()]


def test_green_machine_gates_and_approval_materialize_semantic_model(
    tmp_path, monkeypatch
) -> None:
    root = make_fixture_repo(tmp_path)
    _setup(monkeypatch, root)
    stub_green_db(monkeypatch)
    asset = _asset_by_name(build_table_assets(TABLE, root), "semantic_model")

    asset(build_asset_context())

    row = _record(root, "semantic_model")
    assert row["outcome"] == "materialized"
    assert row["measured"]["approved_by"] == "Named Human (metric_owner)"
