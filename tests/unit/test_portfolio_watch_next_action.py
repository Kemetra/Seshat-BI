"""US1 tests: the prioritized-next-action selector (spec 131, T009).

For a scope whose top open condition is a missing approval,
``prioritized_next_action.category == "approval"`` (the highest of the
shipped ``readiness_classify`` rank) and ``action`` equals the scope's
RELAYED ``next_action`` -- the readiness projection's own computed
``next_action`` field, never a string this module assembles itself
(FR-005, SC-003). A top-category tie across scopes surfaces both scopes' own
actions, unbroken by a synthesized number.

NOTE: the readiness projection's ``next_action`` is COMPUTED from the
committed stage statuses/approvals by ``run_next``/``agent_next`` -- it is NOT
simply the free-text ``next_action:`` line in the YAML fixture. Tests below
therefore compare against ``build_readiness_projection``'s own output (the
thing Portfolio Watch must relay verbatim) rather than a hand-written string.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat import portfolio_watch as pw
from seshat.readiness_projection import build_readiness_projection
from tests.fixtures.portfolio_watch.builders import write_readiness_status

pytestmark = pytest.mark.unit


def _projection_by_scope(root: Path) -> dict[str, dict]:
    projection = build_readiness_projection(root)
    return {t["table_id"]: t for t in projection["tables"]}


def test_approval_blocker_outranks_grain_and_artifact(tmp_path: Path) -> None:
    write_readiness_status(
        tmp_path,
        "scope_alpha",
        current_stage="mapping_ready",
        stage_status={"source_ready": "pass", "mapping_ready": "blocked"},
        stage_blocking_reasons={
            "mapping_ready": [
                "mapping_ready approval is missing",
                "a required artifact is missing",
            ],
        },
        top_blocking_reasons=["mapping_ready approval is missing"],
    )

    summary = pw.build_portfolio_watch_summary(tmp_path)
    scope = summary["scopes"][0]
    expected = _projection_by_scope(tmp_path)["scope_alpha"]["next_action"]

    assert scope["prioritized_next_action"]["category"] == "approval"
    assert scope["prioritized_next_action"]["action"] == expected


def test_action_is_relayed_never_synthesized(tmp_path: Path) -> None:
    """The action string is the readiness projection's own computed
    next_action verbatim -- never assembled from the classify() explanation/
    next_surface text this module never even reads for the action."""
    write_readiness_status(
        tmp_path,
        "scope_alpha",
        current_stage="mapping_ready",
        stage_status={"source_ready": "pass", "mapping_ready": "blocked"},
        stage_blocking_reasons={"mapping_ready": ["grain needs owner approval"]},
        top_blocking_reasons=["grain needs owner approval"],
    )

    summary = pw.build_portfolio_watch_summary(tmp_path)
    scope = summary["scopes"][0]
    expected = _projection_by_scope(tmp_path)["scope_alpha"]["next_action"]

    assert scope["prioritized_next_action"]["action"] == expected
    # Never a string built from readiness_classify's explanation/next_surface.
    assert "next_surface" not in scope["prioritized_next_action"]["action"]


def test_terminal_scope_relays_its_live_validation_stop(tmp_path: Path) -> None:
    write_readiness_status(
        tmp_path,
        "scope_alpha",
        current_stage="publish_ready",
        stage_status={
            "source_ready": "pass",
            "mapping_ready": "pass",
            "silver_ready": "pass",
            "gold_ready": "pass",
            "semantic_model_ready": "pass",
            "dashboard_ready": "pass",
            "publish_ready": "pass",
        },
        approvals=[
            {"stage": "mapping_ready", "owner": "Test Owner (analyst)"},
            {"stage": "semantic_model_ready", "owner": "Test Owner (metric_owner)"},
            {"stage": "dashboard_ready", "owner": "Test Owner (governance)"},
            {"stage": "publish_ready", "owner": "Test Owner (data_owner)"},
        ],
    )

    summary = pw.build_portfolio_watch_summary(tmp_path)
    scope = summary["scopes"][0]
    expected = _projection_by_scope(tmp_path)["scope_alpha"]["next_action"]

    assert scope["prioritized_next_action"]["category"] == "readiness"
    assert scope["prioritized_next_action"]["action"] == expected
    assert expected.startswith("STOP")
    assert "retail validate" in expected


def test_two_scopes_tying_on_the_top_category_both_surface_their_own_action(
    tmp_path: Path,
) -> None:
    write_readiness_status(
        tmp_path,
        "scope_alpha",
        current_stage="mapping_ready",
        stage_status={"source_ready": "pass", "mapping_ready": "blocked"},
        stage_blocking_reasons={"mapping_ready": ["mapping_ready approval is missing"]},
        top_blocking_reasons=["mapping_ready approval is missing"],
    )
    write_readiness_status(
        tmp_path,
        "scope_beta",
        current_stage="dashboard_ready",
        stage_status={
            "source_ready": "pass",
            "mapping_ready": "pass",
            "silver_ready": "pass",
            "gold_ready": "pass",
            "semantic_model_ready": "pass",
            "dashboard_ready": "blocked",
        },
        stage_blocking_reasons={
            "dashboard_ready": ["dashboard_ready approval is missing"],
        },
        top_blocking_reasons=["dashboard_ready approval is missing"],
    )

    summary = pw.build_portfolio_watch_summary(tmp_path)
    by_scope = {s["scope_id"]: s for s in summary["scopes"]}
    expected = _projection_by_scope(tmp_path)

    assert by_scope["scope_alpha"]["prioritized_next_action"]["category"] == "approval"
    assert by_scope["scope_beta"]["prioritized_next_action"]["category"] == "approval"
    assert (
        by_scope["scope_alpha"]["prioritized_next_action"]["action"]
        == (expected["scope_alpha"]["next_action"])
    )
    assert (
        by_scope["scope_beta"]["prioritized_next_action"]["action"]
        == (expected["scope_beta"]["next_action"])
    )
    # The two scopes' actions are genuinely distinct -- neither is suppressed
    # or overwritten by the other despite tying on category.
    assert (
        by_scope["scope_alpha"]["prioritized_next_action"]["action"]
        != by_scope["scope_beta"]["prioritized_next_action"]["action"]
    )
