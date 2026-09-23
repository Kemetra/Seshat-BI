"""Truthful badge/card unit coverage (spec 127, US2). No fabricated score."""

from __future__ import annotations

import re

import pytest

from seshat.showcase.badge import STAGE_ORDER, build_badge

pytestmark = pytest.mark.unit

_GRADE_RE = re.compile(r"\b[A-F][+-]?\b")
_CONFIDENCE_RE = re.compile(r"\b0?\.\d+\s*(confidence|conf)\b", re.IGNORECASE)


def _stage_block(status: str) -> dict:
    return {"status": status, "evidence": [], "blocking_reasons": []}


def _table(table_id: str, passed_through: int) -> dict:
    """A table whose first ``passed_through`` stages (in spine order) pass and
    whose next stage is blocked; the rest are not_started."""
    stages = {}
    for index, stage in enumerate(STAGE_ORDER):
        if index < passed_through:
            stages[stage] = _stage_block("pass")
        elif index == passed_through:
            stages[stage] = _stage_block("blocked")
        else:
            stages[stage] = _stage_block("not_started")
    return {
        "table_id": table_id,
        "source_path": f"mappings/{table_id}/x",
        "stages": stages,
    }


def test_badge_names_highest_contiguous_stage_and_passed_count() -> None:
    badge = build_badge([_table("orders", 3)])
    assert badge["highest_contiguous_pass"] == "silver_ready"
    assert badge["passed_stage_count"] == 3
    assert badge["total_stages"] == 7
    assert badge["next_blocked_stage"] == "gold_ready"
    assert "3/7" in badge["label"]
    assert "Gold" in badge["label"]


def test_badge_label_never_fabricates_a_score() -> None:
    badge = build_badge([_table("orders", 3)])
    label = badge["label"]
    assert "%" not in label
    assert not _GRADE_RE.search(label)
    assert not _CONFIDENCE_RE.search(label)


def test_badge_no_stage_passed_states_truthful_onboarding_status() -> None:
    badge = build_badge([_table("orders", 0)])
    assert badge["passed_stage_count"] == 0
    assert badge["highest_contiguous_pass"] is None
    assert "onboarding" in badge["label"].lower()
    assert badge["label"].strip() != ""
    assert "%" not in badge["label"]


def test_badge_empty_workspace_states_truthful_onboarding_status() -> None:
    badge = build_badge([])
    assert badge["passed_stage_count"] == 0
    assert "onboarding" in badge["label"].lower()


def test_badge_ignores_input_defect_entries_as_real_tables() -> None:
    defect = {"table_id": "broken", "source_path": "x", "input_defect": "unreadable"}
    badge = build_badge([defect])
    assert badge["passed_stage_count"] == 0
    assert "onboarding" in badge["label"].lower()


def test_badge_input_defect_pulls_the_portfolio_down() -> None:
    """A malformed readiness file is unknown state -- never celebratory (F144)."""
    defect = {"table_id": "bad", "source_path": "x", "input_defect": "unreadable"}
    badge = build_badge([_table("good", 7), defect])
    assert badge["passed_stage_count"] == 0
    assert "all stages passed" not in badge["label"]


def test_badge_is_worst_first_across_tables() -> None:
    badge = build_badge([_table("ahead", 5), _table("behind", 1)])
    assert badge["passed_stage_count"] == 1
    assert badge["highest_contiguous_pass"] == "source_ready"


def test_badge_renders_offline_inline_svg_with_no_external_fetch() -> None:
    badge = build_badge([_table("orders", 3)])
    svg = badge["svg"]
    assert svg.startswith("<svg")
    # The xmlns attribute is a namespace URI, not a fetched resource; there
    # must be no image/script/stylesheet reference that triggers a request.
    assert "<img" not in svg
    assert "src=" not in svg
    assert "href=" not in svg
