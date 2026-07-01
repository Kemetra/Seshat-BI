from __future__ import annotations

from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.readiness_status import check_readiness_status_consistency

pytestmark = pytest.mark.unit

STATUS_PATH = "mappings/demo/readiness-status.yaml"


def _status_yaml(
    *,
    current_stage: str = "publish_ready",
    publish_status: str = "pass",
    publish_blockers: str = "[]",
    approvals: str | None = None,
    top_blockers: str = "[]",
) -> str:
    if approvals is None:
        approvals = (
            "  - {stage: mapping_ready, owner: data_owner, at: '2026-01-01'}\n"
            "  - {stage: semantic_model_ready, owner: data_owner, at: '2026-01-01'}\n"
            "  - {stage: dashboard_ready, owner: data_owner, at: '2026-01-01'}\n"
            "  - {stage: publish_ready, owner: data_owner, at: '2026-01-01'}\n"
        )
    return f"""table: "bronze.demo"
source_id: "demo"
source_family: "demo"
current_stage: "{current_stage}"
stages:
  source_ready:
    status: "pass"
    evidence: ["source-profile.md"]
    blocking_reasons: []
  mapping_ready:
    status: "pass"
    evidence: ["source-map.yaml"]
    blocking_reasons: []
  silver_ready:
    status: "pass"
    evidence: ["silver.sql"]
    blocking_reasons: []
  gold_ready:
    status: "pass"
    evidence: ["validate exit 0"]
    blocking_reasons: []
  semantic_model_ready:
    status: "pass"
    evidence: ["contracts approved"]
    blocking_reasons: []
  dashboard_ready:
    status: "pass"
    evidence: ["binding map approved"]
    blocking_reasons: []
  publish_ready:
    status: "{publish_status}"
    evidence: ["handoff pack"]
    blocking_reasons: {publish_blockers}
blocking_reasons: {top_blockers}
approvals:
{approvals}next_action: "done"
last_checked_at: "2026-01-01"
checked_by: "test"
"""


def _ctx(tmp_path: Path, text: str, rel: str = STATUS_PATH) -> RuleContext:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=(rel,))


def _messages(ctx: RuleContext) -> list[str]:
    findings = list(check_readiness_status_consistency(ctx))
    assert all(f.rule_id == "RS1" for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)
    return [f.message for f in findings]


def test_valid_readiness_status_passes(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _status_yaml())
    assert list(check_readiness_status_consistency(ctx)) == []


def test_pass_stage_without_evidence_fails(tmp_path: Path) -> None:
    text = _status_yaml().replace('evidence: ["source-profile.md"]', "evidence: []")
    messages = _messages(_ctx(tmp_path, text))
    assert any("source_ready" in m and "no evidence" in m for m in messages)


def test_blocked_stage_without_blockers_fails(tmp_path: Path) -> None:
    text = _status_yaml(
        current_stage="publish_ready",
        publish_status="blocked",
        publish_blockers="[]",
        top_blockers='["publish approval missing"]',
    )
    messages = _messages(_ctx(tmp_path, text))
    assert any(
        "publish_ready" in m and "blocked" in m and "no blocking" in m for m in messages
    )


def test_non_blocked_stage_with_blockers_fails(tmp_path: Path) -> None:
    text = _status_yaml(
        publish_status="warning",
        publish_blockers='["publish re-approval pending"]',
    )
    messages = _messages(_ctx(tmp_path, text))
    assert any("publish_ready" in m and "blocking_reasons" in m for m in messages)


def test_approval_required_stage_pass_without_approval_fails(tmp_path: Path) -> None:
    approvals = (
        "  - {stage: mapping_ready, owner: data_owner, at: '2026-01-01'}\n"
        "  - {stage: semantic_model_ready, owner: data_owner, at: '2026-01-01'}\n"
        "  - {stage: dashboard_ready, owner: data_owner, at: '2026-01-01'}\n"
    )
    messages = _messages(_ctx(tmp_path, _status_yaml(approvals=approvals)))
    assert any("publish_ready" in m and "approvals" in m for m in messages)


def test_current_stage_cannot_skip_earlier_blocked_stage(tmp_path: Path) -> None:
    old = (
        "  mapping_ready:\n"
        '    status: "pass"\n'
        '    evidence: ["source-map.yaml"]\n'
        "    blocking_reasons: []"
    )
    new = (
        "  mapping_ready:\n"
        '    status: "blocked"\n'
        '    evidence: ["source-map.yaml"]\n'
        '    blocking_reasons: ["grain not approved"]'
    )
    text = _status_yaml().replace(
        old,
        new,
    )
    messages = _messages(_ctx(tmp_path, text))
    assert any("skips past earlier blocked stage" in m for m in messages)


def test_blocked_current_stage_requires_top_level_blocker_mirror(
    tmp_path: Path,
) -> None:
    text = _status_yaml(
        current_stage="publish_ready",
        publish_status="blocked",
        publish_blockers='["publish approval missing"]',
        top_blockers="[]",
    )
    messages = _messages(_ctx(tmp_path, text))
    assert any("top-level blocking_reasons" in m for m in messages)


def test_no_status_files_is_silent_pass(tmp_path: Path) -> None:
    ctx = RuleContext(
        repo_root=tmp_path,
        tracked_files=("mappings/demo/source-map.yaml",),
    )
    assert list(check_readiness_status_consistency(ctx)) == []
