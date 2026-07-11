from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.readiness_projection import build_readiness_projection

pytestmark = pytest.mark.unit


def _write_status(
    root: Path,
    *,
    mapping_status: str = "blocked",
    mapping_evidence: str = "[]",
    mapping_blockers: str = '["grain needs owner approval"]',
) -> None:
    path = root / "mappings" / "orders" / "readiness-status.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"""\
table: orders
current_stage: mapping_ready
stages:
  source_ready:
    status: pass
    evidence: [mappings/orders/source-profile.md]
    blocking_reasons: []
  mapping_ready:
    status: {mapping_status}
    evidence: {mapping_evidence}
    blocking_reasons: {mapping_blockers}
  silver_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
  gold_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
  semantic_model_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
  dashboard_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
  publish_ready: {{status: not_started, evidence: [], blocking_reasons: []}}
blocking_reasons: [grain needs owner approval]
approvals: []
next_action: Resolve grain with the data owner.
""",
        encoding="utf-8",
    )


def test_empty_workspace_has_truthful_source_ready_action(tmp_path: Path) -> None:
    result = build_readiness_projection(tmp_path)
    assert result["schema_version"] == "1.0"
    assert result["tables"] == []
    assert result["portfolio_next"]["current_stage"] == "source_ready"
    assert result["portfolio_next"]["readiness_state"] == "not_started"
    assert result["disclosure"]["status"] == "pass"


def test_projection_preserves_stage_order_evidence_blockers_and_stop(
    tmp_path: Path,
) -> None:
    _write_status(tmp_path)
    result = build_readiness_projection(tmp_path)
    table = result["tables"][0]

    assert list(table["stages"]) == [
        "source_ready",
        "mapping_ready",
        "silver_ready",
        "gold_ready",
        "semantic_model_ready",
        "dashboard_ready",
        "publish_ready",
    ]
    assert table["stages"]["source_ready"]["evidence"]
    assert table["stages"]["mapping_ready"]["blocking_reasons"]
    assert "No silver work" in " ".join(table["forbidden_scope"])
    assert table["stop_point"]
    assert table["read_only_proof"] is True


def test_projection_never_emits_score_or_confidence(tmp_path: Path) -> None:
    _write_status(tmp_path)
    payload = json.dumps(build_readiness_projection(tmp_path)).lower()
    assert '"score"' not in payload
    assert '"confidence"' not in payload


def test_pass_without_evidence_blocks_public_disclosure(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        mapping_status="pass",
        mapping_evidence="[]",
        mapping_blockers="[]",
    )
    result = build_readiness_projection(tmp_path)
    assert result["disclosure"]["status"] == "blocked"
    assert any(
        finding["rule"] == "projection_pass_without_evidence"
        for finding in result["disclosure"]["findings"]
    )


def test_blocked_without_reason_blocks_public_disclosure(tmp_path: Path) -> None:
    _write_status(tmp_path, mapping_blockers="[]")
    result = build_readiness_projection(tmp_path)
    assert result["disclosure"]["status"] == "blocked"
    assert any(
        finding["rule"] == "projection_blocked_without_reason"
        for finding in result["disclosure"]["findings"]
    )
