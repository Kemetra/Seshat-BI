"""US2: human-seam assets read committed approvals; absent -> BLOCK; and the
publish wall fails closed even when publish_ready is pass (F016 absent)."""

from __future__ import annotations

import pytest
from dagster import Failure, build_asset_context, materialize

from tower_bi_orchestration.assets import build_table_assets
from tower_bi_orchestration.evidence_writer import EvidenceWriter

from conftest import TABLE, make_fixture_repo, mappings_digest, stub_green_db


def _asset_by_name(assets: list, name: str):
    for asset in assets:
        if asset.key.path[-1] == name:
            return asset
    raise AssertionError(f"asset {name} not found")


def _setup(monkeypatch, root) -> None:
    monkeypatch.setenv("SESHAT_REPO_ROOT", str(root))
    monkeypatch.setenv("SESHAT_DAGSTER_RUN_ID", "testrun-002")


def test_open_gate_blocks_silver_and_writes_no_approval(tmp_path, monkeypatch) -> None:
    root = make_fixture_repo(tmp_path, gate_cleared=False)
    _setup(monkeypatch, root)
    stub_green_db(monkeypatch)
    before = mappings_digest(root)

    result = materialize(build_table_assets(TABLE, root), raise_on_error=False)
    assert result.success is False

    records = {row["asset"]: row for row in EvidenceWriter(root, "testrun-002").records()}
    seam = records["source_map"]
    assert seam["outcome"] == "blocked"
    assert "not CLEARED" in seam["blocking_reason"]
    assert "unresolved-questions.md" in seam["blocking_reason"]
    assert seam["owner"] == "the mapping reviewer"
    assert "silver_tables" not in records  # never ran; finalize would mark it skipped
    assert mappings_digest(root) == before  # nothing wrote CLEARED / any approval


def test_cleared_gate_permits_silver(tmp_path, monkeypatch) -> None:
    root = make_fixture_repo(tmp_path, gate_cleared=True)
    _setup(monkeypatch, root)
    stub_green_db(monkeypatch)
    result = materialize(build_table_assets(TABLE, root), raise_on_error=False)
    records = {row["asset"]: row for row in EvidenceWriter(root, "testrun-002").records()}
    assert records["source_map"]["outcome"] == "materialized"
    assert records["silver_tables"]["outcome"] == "materialized"
    assert result.success is False  # the publish wall still fails closed (below)


def test_semantic_model_blocks_without_the_committed_approval(tmp_path, monkeypatch) -> None:
    root = make_fixture_repo(tmp_path, semantic_approved=False)
    _setup(monkeypatch, root)
    stub_green_db(monkeypatch)
    asset = _asset_by_name(build_table_assets(TABLE, root), "semantic_model")
    with pytest.raises(Failure, match="approval absent"):
        asset(build_asset_context())
    records = {row["asset"]: row for row in EvidenceWriter(root, "testrun-002").records()}
    assert records["semantic_model"]["outcome"] == "blocked"
    assert records["semantic_model"]["owner"] == "the metric owner"


def test_publish_wall_blocks_when_publish_ready_not_pass(tmp_path, monkeypatch) -> None:
    root = make_fixture_repo(tmp_path, publish_status="not_started")
    _setup(monkeypatch, root)
    asset = _asset_by_name(build_table_assets(TABLE, root), "publish_execution_evidence")
    with pytest.raises(Failure, match="publish_ready not pass"):
        asset(build_asset_context())
    records = {row["asset"]: row for row in EvidenceWriter(root, "testrun-002").records()}
    row = records["publish_execution_evidence"]
    assert row["outcome"] == "blocked"
    assert row["measured"]["publish_ready_read"] == "not_started"


def test_publish_wall_fails_closed_when_f016_is_absent(tmp_path, monkeypatch) -> None:
    root = make_fixture_repo(tmp_path, publish_status="pass")
    _setup(monkeypatch, root)
    asset = _asset_by_name(build_table_assets(TABLE, root), "publish_execution_evidence")
    with pytest.raises(Failure, match="F016 publish adapter not available"):
        asset(build_asset_context())
    records = {row["asset"]: row for row in EvidenceWriter(root, "testrun-002").records()}
    row = records["publish_execution_evidence"]
    assert row["outcome"] == "blocked"
    assert row["blocking_reason"] == "F016 publish adapter not available"
    assert row["owner"] == "the F016 owner"
