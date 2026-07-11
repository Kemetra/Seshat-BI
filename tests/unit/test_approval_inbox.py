"""Tests for the read-only approval inbox surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.approval_inbox import build_approval_inbox
from seshat.cli import main

pytestmark = pytest.mark.unit


def _write_status(tmp_path: Path, table_dir: str, body: str) -> Path:
    path = tmp_path / "mappings" / table_dir / "readiness-status.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_empty_repo_has_empty_inbox(tmp_path: Path) -> None:
    assert build_approval_inbox(tmp_path) == {"items": [], "read_only_proof": True}


def test_pass_stage_missing_approval_is_listed(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "pass", evidence: ["map"]}
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals: []
""",
    )

    result = build_approval_inbox(tmp_path)
    assert result["items"] == [
        {
            "table": "silver.orders",
            "source_path": "mappings/orders/readiness-status.yaml",
            "stage": "mapping_ready",
            "status": "pass",
            "required_authority": "analyst",
            "issue": "missing_approval",
            "detail": (
                "stage 'mapping_ready' is pass but no shape-valid approval is recorded"
            ),
            "blocking_reasons": [],
            "invalid_approvals": [],
        }
    ]


def test_invalid_owner_is_listed_as_invalid_approval(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "pass", evidence: ["map"]}
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals:
  - {stage: mapping_ready, owner: "analyst", at: "2026-07-01"}
""",
    )

    item = build_approval_inbox(tmp_path)["items"][0]
    assert item["issue"] == "invalid_approval"
    assert item["required_authority"] == "analyst"
    assert item["invalid_approvals"] == ["analyst"]


def test_blocked_approval_reason_is_listed_verbatim(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready:
    status: "blocked"
    blocking_reasons: ["Map is filled but not yet reviewed/APPROVED"]
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals: []
""",
    )

    item = build_approval_inbox(tmp_path)["items"][0]
    assert item["issue"] == "blocked_for_approval"
    assert item["blocking_reasons"] == ["Map is filled but not yet reviewed/APPROVED"]


def test_valid_approvals_are_not_listed(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
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
""",
    )

    assert build_approval_inbox(tmp_path)["items"] == []


def test_cli_approvals_json_is_read_only_and_score_free(tmp_path: Path, capsys) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "pass", evidence: ["map"]}
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals: []
""",
    )
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())

    exit_code = main(["approvals", "--repo", str(tmp_path), "--format", "json"])

    assert exit_code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["items"][0]["stage"] == "mapping_ready"
    dumped = json.dumps(parsed).lower()
    for banned in ("score", "confidence", "health", "maturity"):
        assert banned not in dumped
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert before == after
