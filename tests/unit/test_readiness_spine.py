"""One readiness spine: per-stage approval authority, enforced on every surface.

Before this module existed, run_next, approval_inbox, approver_view,
blocker_explainer and evidence_pack each carried their own copy of the stage
table and their own idea of a "valid approval". Two of them checked the owner
shape only, and none checked the authority CLASS against the stage, so an analyst
approval cleared the metric_owner-gated semantic_model_ready stage. These tests
pin one predicate across all five surfaces plus RS1.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.approval_inbox import build_approval_inbox
from seshat.approver_view import build_approver_view
from seshat.blocker_explainer import build_blocker_explanations
from seshat.core import RuleContext, Severity
from seshat.evidence_pack import build_evidence_pack
from seshat.rules.readiness_status import (
    check_readiness_status_consistency,
    stage_approval_valid,
)
from seshat.run_next import build_run_next_response

pytestmark = pytest.mark.unit

_REL = "mappings/orders/readiness-status.yaml"


def _status(stages: dict[str, str], approvals: str) -> str:
    lines = ['table: "silver.orders"', "current_stage: publish_ready", "stages:"]
    for stage, status in stages.items():
        evidence = '["e"]' if status == "pass" else "[]"
        lines.append(f"  {stage}: {{status: {status}, evidence: {evidence}}}")
    lines.append("approvals:")
    lines.append(approvals or "  []")
    lines.append('last_checked_at: "2026-09-01"')
    return "\n".join(lines) + "\n"


_ALL = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)


def _through(last: str) -> dict[str, str]:
    """Every stage up to and including ``last`` passes; the rest not_started."""
    cut = _ALL.index(last)
    return {s: ("pass" if i <= cut else "not_started") for i, s in enumerate(_ALL)}


def _appr(stage: str, owner: str, key: str = "at") -> str:
    return f'  - {{stage: {stage}, owner: "{owner}", {key}: "2026-09-01"}}'


def _write(root: Path, text: str) -> None:
    path = root / _REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _rs1(root: Path) -> list[str]:
    ctx = RuleContext(repo_root=root, tracked_files=(_REL,))
    return [
        f.message
        for f in check_readiness_status_consistency(ctx)
        if f.severity is Severity.ERROR
    ]


_MAPPING_OK = _appr("mapping_ready", "Ada Lovelace (analyst)")


# --- the shared predicate ---------------------------------------------------


@pytest.mark.parametrize(
    ("stage", "owner", "expected"),
    [
        ("semantic_model_ready", "Grace Hopper (metric_owner)", True),
        ("semantic_model_ready", "Ada Lovelace (analyst)", False),
        ("semantic_model_ready", "Ada Lovelace (data_owner)", False),
        ("dashboard_ready", "Dana Report (report_owner)", True),
        ("dashboard_ready", "Ada Lovelace (analyst)", False),
        ("publish_ready", "Ada Lovelace (metric_owner)", False),
        ("mapping_ready", "Ada Lovelace (metric_owner)", False),
    ],
)
def test_stage_approval_valid_checks_class_against_stage(
    stage: str, owner: str, expected: bool
) -> None:
    entry = {"stage": stage, "owner": owner, "at": "2026-09-01"}
    assert stage_approval_valid(stage, entry) is expected


def test_stage_approval_valid_rejects_an_entry_for_another_stage() -> None:
    entry = {"stage": "mapping_ready", "owner": "Ada (analyst)", "at": "2026-09-01"}
    assert stage_approval_valid("publish_ready", entry) is False


# --- analyst on semantic_model_ready (F005 / F073 / F051) --------------------


def _analyst_semantic(root: Path) -> None:
    approvals = "\n".join(
        [_MAPPING_OK, _appr("semantic_model_ready", "Ada Lovelace (analyst)")]
    )
    _write(root, _status(_through("semantic_model_ready"), approvals))


def test_analyst_semantic_approval_does_not_advance_next(tmp_path: Path) -> None:
    _analyst_semantic(tmp_path)
    response = build_run_next_response(tmp_path, "orders")
    assert response["outcome"] == "approval_required"
    assert response["stage"] == "semantic_model_ready"
    assert response["required_authority"] == "metric_owner"


def test_analyst_semantic_approval_fails_rs1(tmp_path: Path) -> None:
    _analyst_semantic(tmp_path)
    messages = _rs1(tmp_path)
    assert any("semantic_model_ready" in m and "approvals" in m for m in messages)


def test_analyst_semantic_approval_is_an_inbox_item(tmp_path: Path) -> None:
    _analyst_semantic(tmp_path)
    items = build_approval_inbox(tmp_path)["items"]
    assert [i["stage"] for i in items] == ["semantic_model_ready"]


def test_metric_owner_semantic_approval_advances(tmp_path: Path) -> None:
    approvals = "\n".join(
        [_MAPPING_OK, _appr("semantic_model_ready", "Grace Hopper (metric_owner)")]
    )
    _write(tmp_path, _status(_through("semantic_model_ready"), approvals))
    assert build_run_next_response(tmp_path, "orders")["stage"] == "dashboard_ready"
    assert _rs1(tmp_path) == []


def test_dashboard_ready_names_report_owner(tmp_path: Path) -> None:
    approvals = "\n".join(
        [_MAPPING_OK, _appr("semantic_model_ready", "Grace Hopper (metric_owner)")]
    )
    _write(tmp_path, _status(_through("dashboard_ready"), approvals))
    response = build_run_next_response(tmp_path, "orders")
    assert response["outcome"] == "approval_required"
    assert response["required_authority"] == "report_owner"
    items = build_approval_inbox(tmp_path)["items"]
    assert items[0]["required_authority"] == "report_owner"


# --- an approval keyed `date:` is flagged by all four surfaces (F015) --------


def test_date_keyed_approval_is_flagged_everywhere(tmp_path: Path) -> None:
    _write(
        tmp_path,
        _status(
            _through("publish_ready"),
            "\n".join(
                [
                    _MAPPING_OK,
                    _appr("semantic_model_ready", "Grace Hopper (metric_owner)"),
                    _appr("dashboard_ready", "Dana Report (report_owner)"),
                    _appr("publish_ready", "Ann Lee (data_owner)", key="date"),
                ]
            ),
        ),
    )
    inbox = [i["stage"] for i in build_approval_inbox(tmp_path)["items"]]
    assert inbox == ["publish_ready"]
    view = build_approver_view(tmp_path, "orders")
    assert [i.get("stage") for i in view["refusal_case"]] == ["publish_ready"]
    assert not any(
        r["kind"] == "valid_approval" and r["detail"].startswith("publish_ready")
        for r in view["reassurance"]
    )
    explained = build_blocker_explanations(tmp_path)["items"]
    assert [i["stage"] for i in explained] == ["publish_ready"]
    pack = build_evidence_pack(tmp_path, "orders")
    assert pack["publish_ready"]["approval"] is None


def test_evidence_pack_accepts_a_yaml_date_literal(tmp_path: Path) -> None:
    """A real YAML date parses to datetime.date, not str -- it must still count."""
    approvals = "\n".join(
        [
            _MAPPING_OK,
            "  - {stage: publish_ready, owner: 'Ann Lee (data_owner)', at: 2026-09-01}",
        ]
    )
    _write(tmp_path, _status(_through("gold_ready"), approvals))
    pack = build_evidence_pack(tmp_path, "orders")
    assert pack["publish_ready"]["approval"] == {
        "owner": "Ann Lee (data_owner)",
        "at": "2026-09-01",
    }


# --- monotonic stage ordering (F051) ----------------------------------------


def test_pass_after_not_started_stage_is_rs1_error(tmp_path: Path) -> None:
    stages = _through("gold_ready")
    stages["mapping_ready"] = "not_started"
    _write(tmp_path, _status(stages, "  []"))
    messages = _rs1(tmp_path)
    assert any("silver_ready" in m and "mapping_ready" in m for m in messages)


def test_warning_predecessor_does_not_break_ordering(tmp_path: Path) -> None:
    stages = _through("gold_ready")
    stages["silver_ready"] = "warning"
    _write(tmp_path, _status(stages, _MAPPING_OK))
    assert _rs1(tmp_path) == []


# --- parity over one fixture set --------------------------------------------

_PARITY_CASES = {
    "analyst_on_semantic": _appr("semantic_model_ready", "Ada Lovelace (analyst)"),
    "metric_owner_on_semantic": _appr(
        "semantic_model_ready", "Grace Hopper (metric_owner)"
    ),
    "date_keyed": _appr("semantic_model_ready", "Grace Hopper (metric_owner)", "date"),
    "bare_role": (
        "  - {stage: semantic_model_ready, owner: metric_owner, at: 2026-09-01}"
    ),
    "at_tbd": '  - {stage: semantic_model_ready, owner: "G H (metric_owner)", at: TBD}',
}


@pytest.mark.parametrize("case", sorted(_PARITY_CASES))
def test_every_surface_agrees_on_semantic_approval(tmp_path: Path, case: str) -> None:
    approvals = "\n".join([_MAPPING_OK, _PARITY_CASES[case]])
    _write(tmp_path, _status(_through("semantic_model_ready"), approvals))
    satisfied = {
        "rs1": not any("semantic_model_ready" in m for m in _rs1(tmp_path)),
        "next": build_run_next_response(tmp_path, "orders")["outcome"]
        != "approval_required",
        "inbox": not build_approval_inbox(tmp_path)["items"],
        "approver": not build_approver_view(tmp_path, "orders")["refusal_case"],
        "explainer": not build_blocker_explanations(tmp_path)["items"],
    }
    expected = case == "metric_owner_on_semantic"
    assert set(satisfied.values()) == {expected}, satisfied


# --- table-name resolution (F232) -------------------------------------------


@pytest.mark.parametrize("name", ["..", ".", "a/..", "../orders"])
def test_status_path_candidates_reject_traversal(tmp_path: Path, name: str) -> None:
    from seshat.readiness_spine import status_path_candidates

    for candidate in status_path_candidates(tmp_path, name):
        assert candidate.parent.parent == tmp_path / "mappings"
        assert candidate.parent.name not in ("", ".", "..")


def test_run_next_and_evidence_pack_share_one_resolver() -> None:
    import seshat.evidence_pack as evidence_pack
    import seshat.run_next as run_next

    assert not hasattr(run_next, "_table_candidate_names")
    assert not hasattr(evidence_pack, "_table_candidate_names")
