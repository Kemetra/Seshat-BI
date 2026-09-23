"""A blocked post-Gold stage keeps its own STOP (audit finding F042).

The live-validation and contract overrides may replace a ``next_action`` or a
``terminal_pass`` answer, never a STOP. A table blocked at semantic_model_ready,
dashboard_ready or publish_ready must still point at its recorded blocker.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.agent_next import build_agent_next_document
from tests.unit._gitfix import commit_all, make_git_repo

pytestmark = pytest.mark.unit

_STAGES = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)
_APPROVERS = {
    "mapping_ready": "Ada Lovelace (analyst)",
    "semantic_model_ready": "Grace Hopper (metric_owner)",
    "dashboard_ready": "Alan Turing (governance)",
}
_REASON = "metric owner rejected net_sales definition"


def _status_yaml(blocked_stage: str) -> str:
    index = _STAGES.index(blocked_stage)
    lines = ['table: "silver.orders"', f'current_stage: "{blocked_stage}"', "stages:"]
    for position, stage in enumerate(_STAGES):
        if position < index:
            lines.append(f'  {stage}: {{status: "pass", evidence: ["{stage}"]}}')
        elif position == index:
            lines.append(
                f'  {stage}: {{status: "blocked", blocking_reasons: ["{_REASON}"]}}'
            )
        else:
            lines.append(f'  {stage}: {{status: "not_started"}}')
    lines.append("approvals:")
    for stage in _STAGES[:index]:
        if stage in _APPROVERS:
            lines.append(
                f'  - {{stage: {stage}, owner: "{_APPROVERS[stage]}", '
                'at: "2026-07-01"}'
            )
    lines.append('next_action: "resolve the blocker"')
    return "\n".join(lines) + "\n"


def _repo(tmp_path: Path, blocked_stage: str) -> Path:
    repo = make_git_repo(tmp_path)
    path = repo / "mappings" / "orders" / "readiness-status.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(_status_yaml(blocked_stage), encoding="utf-8")
    commit_all(repo, "feat: blocked readiness fixture")
    return repo


@pytest.mark.parametrize(
    "blocked_stage", ["semantic_model_ready", "dashboard_ready", "publish_ready"]
)
def test_blocked_post_gold_stage_keeps_its_own_stop(
    tmp_path: Path, blocked_stage: str
) -> None:
    document = build_agent_next_document(_repo(tmp_path, blocked_stage), "orders")

    assert document["outcome"] == "stop_blocked"
    assert document["current_stage"] == blocked_stage
    assert document["blocking_reasons"] == [_REASON]
    action = document["next_allowed_action"]
    assert action.startswith("STOP")
    assert "validate --source-map" not in action
    assert "kpi-contract-builder" not in action
    assert "gold SQL" not in document["stop_point"]


def test_blocked_post_gold_stage_still_reports_live_validation_as_caveat(
    tmp_path: Path,
) -> None:
    document = build_agent_next_document(
        _repo(tmp_path, "semantic_model_ready"), "orders"
    )

    kinds = {caveat["kind"] for caveat in document["caveats"]}
    assert "live_validation" in kinds
