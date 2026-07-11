"""Tests for the read-only evidence pack preview surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.cli import main
from seshat.evidence_pack import build_evidence_pack

pytestmark = pytest.mark.unit


def _write(path: Path, text: str = "filled evidence\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_status(
    tmp_path: Path, table_dir: str, *, publish_status: str = "pass"
) -> None:
    _write(
        tmp_path / "mappings" / table_dir / "readiness-status.yaml",
        f"""\
table: "silver.{table_dir}"
source_id: "{table_dir}"
source_family: "example"
current_stage: "publish_ready"
stages:
  source_ready: {{status: "pass", evidence: ["profile"]}}
  mapping_ready: {{status: "pass", evidence: ["map"]}}
  silver_ready: {{status: "pass", evidence: ["retail check exit 0"]}}
  gold_ready: {{status: "pass", evidence: ["retail validate exit 0"]}}
  semantic_model_ready: {{status: "pass", evidence: ["semantic check pass"]}}
  dashboard_ready: {{status: "pass", evidence: ["dashboard design approved"]}}
  publish_ready:
    status: "{publish_status}"
    evidence: ["handoff pack reviewed"]
    blocking_reasons: []
approvals:
  - {{stage: mapping_ready, owner: "Ada Lovelace (analyst)", at: "2026-07-01"}}
  - stage: semantic_model_ready
    owner: "Grace Hopper (metric_owner)"
    at: "2026-07-01"
  - stage: dashboard_ready
    owner: "Katherine Johnson (governance)"
    at: "2026-07-01"
  - {{stage: publish_ready, owner: "Ahmed Shaaban (data_owner)", at: "2026-07-01"}}
""",
    )


def _write_complete_pack_sources(tmp_path: Path, table_dir: str) -> None:
    base = tmp_path / "mappings" / table_dir
    _write(base / "source-profile.md")
    _write(base / "source-map.yaml")
    _write(base / "assumptions.md")
    _write(base / "unresolved-questions.md")
    _write(base / "metrics" / "TotalSales.yaml")
    _write(base / "reconciliation-report.md")
    _write(base / "design" / "dashboard-layout.md")
    _write(base / "handoff" / "bi-handoff-pack.md")
    _write(base / "data-issues.md")
    _write(base / "release-notes.md")


def test_evidence_pack_has_ten_ordered_sections(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders")
    _write_complete_pack_sources(tmp_path, "orders")

    result = build_evidence_pack(tmp_path, "orders")

    assert result["table"] == "silver.orders"
    assert result["current_stage"] == "publish_ready"
    assert [section["id"] for section in result["sections"]] == [
        "01",
        "02",
        "03",
        "04",
        "05",
        "06",
        "07",
        "08",
        "09",
        "10",
    ]
    assert all(section["status"] == "pass" for section in result["sections"])
    assert result["blockers"] == []
    assert result["read_only_proof"] is True


def test_missing_section_sources_become_blockers(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders")
    _write(tmp_path / "mappings" / "orders" / "source-profile.md")

    result = build_evidence_pack(tmp_path, "orders")

    source_profile = result["sections"][0]
    source_map = result["sections"][1]
    assert source_profile["status"] == "pass"
    assert source_map["status"] == "blocked"
    assert source_map["blocking_reasons"] == [
        "missing or unfilled source: mappings/orders/source-map.yaml"
    ]
    assert any(blocker["section"] == "02" for blocker in result["blockers"])


def test_publish_ready_approval_is_surfaced_not_granted(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders")
    _write_complete_pack_sources(tmp_path, "orders")

    result = build_evidence_pack(tmp_path, "orders")

    assert result["publish_ready"]["status"] == "pass"
    assert result["publish_ready"]["approval"] == {
        "owner": "Ahmed Shaaban (data_owner)",
        "at": "2026-07-01",
    }


def test_publish_ready_bare_role_approval_is_not_surfaced(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders")
    status = tmp_path / "mappings" / "orders" / "readiness-status.yaml"
    status.write_text(
        status.read_text(encoding="utf-8").replace(
            "Ahmed Shaaban (data_owner)", "data_owner"
        ),
        encoding="utf-8",
    )
    _write_complete_pack_sources(tmp_path, "orders")

    result = build_evidence_pack(tmp_path, "orders")

    assert result["publish_ready"]["status"] == "pass"
    assert result["publish_ready"]["approval"] is None


def test_missing_status_is_input_defect(tmp_path: Path) -> None:
    result = build_evidence_pack(tmp_path, "orders")
    assert result["outcome"] == "input_defect"
    assert result["sections"] == []
    assert result["blockers"]


def test_cli_evidence_pack_json_is_read_only_and_score_free(
    tmp_path: Path, capsys
) -> None:
    _write_status(tmp_path, "orders")
    _write_complete_pack_sources(tmp_path, "orders")
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())

    exit_code = main(
        [
            "evidence-pack",
            "--repo",
            str(tmp_path),
            "--table",
            "orders",
            "--format",
            "json",
        ]
    )

    assert exit_code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["table"] == "silver.orders"
    dumped = json.dumps(parsed).lower()
    for banned in ("score", "confidence", "health", "maturity"):
        assert banned not in dumped
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert before == after
