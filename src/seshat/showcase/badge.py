"""Truthful evidence-derived badge / project card (spec 127, US2).

The badge summarizes only committed evidence already classified by the
reused Explorer/readiness projection: the highest CONTIGUOUS ``pass`` stage
and the count of passed stages. It never expresses a percentage, a grade, or
any other fabricated confidence signal (FR-012/FR-013; hard rule #9). It
renders offline as inline SVG markup -- no external image fetch (FR-014).
"""

from __future__ import annotations

import html
from typing import Any

STAGE_ORDER = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)
STAGE_LABELS = {
    "source_ready": "Source",
    "mapping_ready": "Mapping",
    "silver_ready": "Silver",
    "gold_ready": "Gold",
    "semantic_model_ready": "Semantic Model",
    "dashboard_ready": "Dashboard",
    "publish_ready": "Publish",
}
_TOTAL_STAGES = len(STAGE_ORDER)


def _table_stage_status(table: dict[str, Any], stage: str) -> str:
    """The stage's recorded status, exactly as the projection classified it.

    An input-defect entry (a malformed readiness file) has no interpretable
    stages, so every stage is treated as not passed -- never inferred pass.
    """
    if "input_defect" in table:
        return "blocked"
    block = table["stages"].get(stage)
    return block["status"] if block else "not_started"


def _contiguous_pass(status_by_stage: dict[str, str]) -> tuple[int, str | None]:
    count = 0
    highest: str | None = None
    for stage in STAGE_ORDER:
        if status_by_stage.get(stage) == "pass":
            count += 1
            highest = stage
        else:
            break
    return count, highest


def _next_blocked(
    status_by_stage: dict[str, str], passed_count: int
) -> tuple[str | None, str | None]:
    if passed_count >= _TOTAL_STAGES:
        return None, None
    stage = STAGE_ORDER[passed_count]
    return stage, status_by_stage.get(stage, "not_started")


def table_badge(table: dict[str, Any]) -> dict[str, Any]:
    """Per-table evidence-derived summary; feeds the richer project card."""
    status_by_stage = {
        stage: _table_stage_status(table, stage) for stage in STAGE_ORDER
    }
    passed_count, highest = _contiguous_pass(status_by_stage)
    next_stage, next_status = _next_blocked(status_by_stage, passed_count)
    return {
        "table_id": table.get("table_id"),
        "highest_contiguous_pass": highest,
        "passed_stage_count": passed_count,
        "total_stages": _TOTAL_STAGES,
        "next_blocked_stage": next_stage,
        "next_blocked_status": next_status,
    }


def _label(passed_count: int, next_stage: str | None, next_status: str | None) -> str:
    if passed_count == 0:
        return "Onboarding: no stage has passed yet"
    base = f"{passed_count}/{_TOTAL_STAGES} stages ready"
    if next_stage is None:
        return f"{base} -- all stages passed"
    stage_label = STAGE_LABELS[next_stage]
    status_word = (next_status or "not_started").replace("_", " ")
    return f"{base} -- {stage_label}: {status_word}"


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def render_badge_svg(label: str) -> str:
    """Offline inline SVG markup for the badge; no external image fetch."""
    safe = _escape(label)
    width = max(220, 9 * len(label) + 24)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="28" '
        f'role="img" aria-label="{safe}" class="showcase-badge-svg">'
        f'<rect width="{width}" height="28" rx="4" fill="#001e35"/>'
        f'<text x="12" y="18" fill="#f2ede1" '
        'font-family="Inter, Arial, sans-serif" font-size="13">'
        f"{safe}</text></svg>"
    )


def build_badge(tables: list[dict[str, Any]]) -> dict[str, Any]:
    """Evidence-only badge for the whole bundle (FR-012..015).

    Worst-first across tables: the portfolio badge counts a stage as passed
    only up to the least-advanced table's contiguous run, so it never claims
    an advancement a real table has not reached. When no table has passed
    any stage (including an empty workspace), it states the truthful
    onboarding status rather than an empty or celebratory claim (FR-015).

    An input-defect table (malformed readiness file) takes part in the
    minimum as zero passed stages: its state is unknown, so it must pull the
    portfolio claim down rather than be dropped from it.
    """
    if not tables:
        label = _label(0, STAGE_ORDER[0], "not_started")
        return {
            "highest_contiguous_pass": None,
            "passed_stage_count": 0,
            "total_stages": _TOTAL_STAGES,
            "next_blocked_stage": STAGE_ORDER[0],
            "label": label,
            "svg": render_badge_svg(label),
        }
    per_table = [table_badge(table) for table in tables]
    worst = min(per_table, key=lambda entry: entry["passed_stage_count"])
    label = _label(
        worst["passed_stage_count"],
        worst["next_blocked_stage"],
        worst["next_blocked_status"],
    )
    return {
        "highest_contiguous_pass": worst["highest_contiguous_pass"],
        "passed_stage_count": worst["passed_stage_count"],
        "total_stages": _TOTAL_STAGES,
        "next_blocked_stage": worst["next_blocked_stage"],
        "label": label,
        "svg": render_badge_svg(label),
    }
