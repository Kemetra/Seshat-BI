"""Read-only blocker explainer for readiness-status files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

# The category rank + keyword classifier were extracted to readiness_classify.py
# (spec 115) so approver_view can share the SAME rank without co-locating. This
# module's behavior is unchanged: _classify returns the identical
# (category, explanation, next_surface); a regression-lock test asserts
# byte-identical output.
from .readiness_classify import classify as _classify
from .readiness_classify import remediation_of as _remediation_of
from .readiness_spine import (
    STAGE_ORDER,
    approval_required,
    load_status_mapping,
    stage_has_valid_approval,
)

UNREADABLE_REASON = (
    "readiness-status.yaml is unreadable or not a mapping; its blockers cannot be "
    "established (this is NOT the same as 'nothing blocking')"
)


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _item(table: str, source_path: str, stage: str, reason: str) -> dict[str, str]:
    """One blocker's explained item.

    ``remediation`` / ``doc`` / ``stop_condition`` come from the COMMITTED
    allowlist in ``readiness_classify``, keyed by the same category ``_classify``
    already returns -- never generated per blocker. Free-form remediation text is
    exactly where an agent would start inventing steps the governance model does
    not sanction. An unclassified category fails safe to ``human_only``.
    """
    category, explanation, next_surface = _classify(reason)
    remediation = _remediation_of(category)
    return {
        "table": table,
        "source_path": source_path,
        "stage": stage,
        "category": category,
        "reason": reason,
        "explanation": explanation,
        "next_surface": next_surface,
        "remediation": remediation.remediation,
        "doc": remediation.doc,
        "stop_condition": remediation.stop_condition,
    }


def _table_name(data: dict[str, Any], fallback_table: str) -> str:
    table = data.get("table")
    return table if isinstance(table, str) and table else fallback_table


def _stage_items(
    table: str, source_path: str, stage: str, block: dict[str, Any]
) -> list[dict[str, str]]:
    status = block.get("status")
    if status != "blocked":
        return []
    return [
        _item(table, source_path, stage, reason)
        for reason in _as_str_list(block.get("blocking_reasons"))
    ]


def _approval_item(
    context: dict[str, Any], stage: str, block: object
) -> dict[str, str] | None:
    if not isinstance(block, dict):
        return None
    if block.get("status") != "pass" or not approval_required(stage, block):
        return None
    if stage_has_valid_approval(context["data"].get("approvals"), stage):
        return None
    return _item(
        context["table"],
        context["source_path"],
        stage,
        "invalid or missing approval for pass stage",
    )


def _current_stage(data: dict[str, Any]) -> str:
    stage = data.get("current_stage")
    return stage if isinstance(stage, str) else "unknown"


def _has_reason(items: list[dict[str, str]], reason: str) -> bool:
    return any(item["reason"] == reason for item in items)


def _status_level_items(
    context: dict[str, Any],
    existing: list[dict[str, str]],
) -> list[dict[str, str]]:
    stage = _current_stage(context["data"])
    return [
        _item(context["table"], context["source_path"], stage, reason)
        for reason in _as_str_list(context["data"].get("blocking_reasons"))
        if not _has_reason(existing, reason)
    ]


def _items_for_status(
    data: dict[str, Any], source_path: str, fallback_table: str
) -> list[dict[str, str]]:
    table = _table_name(data, fallback_table)
    stages = data.get("stages")
    if not isinstance(stages, dict):
        return []

    context = {"data": data, "table": table, "source_path": source_path}
    items: list[dict[str, str]] = []
    for stage in STAGE_ORDER:
        block = stages.get(stage)
        if isinstance(block, dict):
            items.extend(_stage_items(table, source_path, stage, block))
        approval_item = _approval_item(context, stage, block)
        if approval_item is not None:
            items.append(approval_item)

    return [*items, *_status_level_items(context, items)]


def _items_from_status_path(root: Path, status_path: Path) -> list[dict[str, str]]:
    source_path = status_path.relative_to(root).as_posix()
    data = load_status_mapping(status_path)
    if data is None:
        # A corrupt file used to vanish, reading as a table with nothing blocking
        # (audit F074); report it as an explicit, unclassified blocker instead.
        name = status_path.parent.name
        return [_item(name, source_path, "unknown", UNREADABLE_REASON)]
    return _items_for_status(data, source_path, status_path.parent.name)


def build_blocker_explanations(repo_root: Path | str = ".") -> dict[str, Any]:
    """Explain blockers across committed readiness statuses."""
    root = Path(repo_root)
    mappings_dir = root / "mappings"
    items: list[dict[str, str]] = []
    if mappings_dir.is_dir():
        for status_path in sorted(mappings_dir.glob("*/readiness-status.yaml")):
            items.extend(_items_from_status_path(root, status_path))
    items.sort(key=lambda item: (item["source_path"], item["stage"], item["reason"]))
    return {"items": items, "read_only_proof": True}
