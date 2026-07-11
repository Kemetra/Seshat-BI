"""Tests for the read-only run-next readiness surface (spec 080)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.cli import main
from seshat.run_next import build_run_next_response

pytestmark = pytest.mark.unit


def _write_status(tmp_path: Path, table_dir: str, body: str) -> Path:
    path = tmp_path / "mappings" / table_dir / "readiness-status.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_missing_status_starts_at_source_ready(tmp_path: Path) -> None:
    result = build_run_next_response(tmp_path, "silver.new_table")
    assert result["table"] == "silver.new_table"
    assert result["outcome"] == "next_action"
    assert result["stage"] == "source_ready"
    assert "Source Ready" in result["action_text"]
    assert result["read_only_proof"] is True


def test_forward_action_uses_earliest_non_pass_stage(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
current_stage: "mapping_ready"
stages:
  source_ready:
    status: "pass"
    evidence: ["mappings/orders/source-profile.md"]
  mapping_ready:
    status: "not_started"
  silver_ready:
    status: "not_started"
  gold_ready:
    status: "not_started"
  semantic_model_ready:
    status: "not_started"
  dashboard_ready:
    status: "not_started"
  publish_ready:
    status: "not_started"
approvals: []
next_action: "Begin Mapping Ready (Stage 2) -- the source-mapping gate."
""",
    )

    result = build_run_next_response(tmp_path, "silver.orders")
    assert result["outcome"] == "next_action"
    assert result["stage"] == "mapping_ready"
    assert "Mapping Ready" in result["action_text"]


def test_blocked_stage_stops_with_verbatim_reasons(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
current_stage: "mapping_ready"
stages:
  source_ready:
    status: "pass"
    evidence: ["mappings/orders/source-profile.md"]
  mapping_ready:
    status: "blocked"
    blocking_reasons: ["grain not confirmed unique on data"]
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals: []
next_action: "resolve grain"
""",
    )

    result = build_run_next_response(tmp_path, "orders")
    assert result["outcome"] == "stop_blocked"
    assert result["stage"] == "mapping_ready"
    assert result["blocking_reasons"] == ["grain not confirmed unique on data"]
    assert result["action_text"] is None


def test_pass_stage_missing_shape_valid_approval_requires_human(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
current_stage: "semantic_model_ready"
stages:
  source_ready:
    status: "pass"
    evidence: ["mappings/orders/source-profile.md"]
  mapping_ready:
    status: "pass"
    evidence: ["mappings/orders/source-map.yaml"]
  silver_ready:
    status: "pass"
    evidence: ["warehouse/migrations/0001_silver.sql"]
  gold_ready:
    status: "pass"
    evidence: ["warehouse/migrations/0002_gold.sql", "retail validate exit 0"]
  semantic_model_ready:
    status: "pass"
    evidence: ["powerbi/Orders.SemanticModel"]
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals:
  - {stage: mapping_ready, owner: "Ada Lovelace (analyst)", at: "2026-07-01"}
  - {stage: semantic_model_ready, owner: "metric_owner", at: "2026-07-01"}
next_action: "done"
""",
    )

    result = build_run_next_response(tmp_path, "orders")
    assert result["outcome"] == "approval_required"
    assert result["stage"] == "semantic_model_ready"
    assert result["required_authority"] == "metric_owner"
    assert result["action_text"] is None


def test_terminal_pass_when_all_approvals_are_shape_valid(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
current_stage: "publish_ready"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "pass", evidence: ["map"]}
  silver_ready: {status: "pass", evidence: ["silver"]}
  gold_ready: {status: "pass", evidence: ["gold"]}
  semantic_model_ready: {status: "pass", evidence: ["model"]}
  dashboard_ready: {status: "pass", evidence: ["dashboard"]}
  publish_ready: {status: "pass", evidence: ["handoff"]}
approvals:
  - {stage: mapping_ready, owner: "Ada Lovelace (analyst)", at: "2026-07-01"}
  - stage: semantic_model_ready
    owner: "Grace Hopper (metric_owner)"
    at: "2026-07-01"
  - {stage: dashboard_ready, owner: "Katherine Johnson (governance)", at: "2026-07-01"}
  - {stage: publish_ready, owner: "Ahmed Shaaban (data_owner)", at: "2026-07-01"}
next_action: "done"
""",
    )

    result = build_run_next_response(tmp_path, "orders")
    assert result["outcome"] == "terminal_pass"
    assert result["stage"] is None
    assert result["action_text"] is None


def test_pass_without_evidence_is_caveated_not_silently_hidden(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
current_stage: "silver_ready"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "pass", evidence: []}
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals:
  - {stage: mapping_ready, owner: "Ada Lovelace (analyst)", at: "2026-07-01"}
next_action: "write silver"
""",
    )

    result = build_run_next_response(tmp_path, "orders")
    assert result["outcome"] == "next_action"
    assert result["stage"] == "silver_ready"
    assert any(c["kind"] == "pass_without_evidence" for c in result["caveats"])


def test_cli_next_json_is_read_only_and_score_free(tmp_path: Path, capsys) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
current_stage: "mapping_ready"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "not_started"}
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals: []
next_action: "Begin Mapping Ready (Stage 2) -- the source-mapping gate."
""",
    )
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())

    exit_code = main(
        [
            "next",
            "--repo",
            str(tmp_path),
            "--table",
            "silver.orders",
            "--format",
            "json",
        ]
    )

    assert exit_code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["outcome"] == "next_action"
    dumped = json.dumps(parsed).lower()
    for banned in ("score", "confidence", "health", "maturity"):
        assert banned not in dumped
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert before == after
