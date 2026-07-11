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

_STAGE_ORDER: tuple[str, ...] = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)
_APPROVAL_REQUIRED: frozenset[str] = frozenset(
    {"mapping_ready", "semantic_model_ready", "dashboard_ready", "publish_ready"}
)
_FILE_SOURCE_KINDS: frozenset[str] = frozenset({"csv", "tsv", "excel"})


def _load_yaml_mapping(path: Path) -> dict[str, Any] | None:
    import yaml

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _valid_owner(owner: object) -> bool:
    from seshat.rules.readiness_status import _owner_is_valid

    return _owner_is_valid(owner)


def _source_kind(stage_block: object) -> str | None:
    from seshat.rules.readiness_status import _source_kind

    return _source_kind(stage_block)


def _approval_required(stage: str, block: dict[str, Any]) -> bool:
    if stage in _APPROVAL_REQUIRED:
        return True
    return stage == "source_ready" and _source_kind(block) in _FILE_SOURCE_KINDS


def _has_valid_approval(data: dict[str, Any], stage: str) -> bool:
    approvals = data.get("approvals")
    if not isinstance(approvals, list):
        return False
    return any(
        isinstance(item, dict)
        and item.get("stage") == stage
        and _valid_owner(item.get("owner"))
        for item in approvals
    )


def _item(table: str, source_path: str, stage: str, reason: str) -> dict[str, str]:
    category, explanation, next_surface = _classify(reason)
    return {
        "table": table,
        "source_path": source_path,
        "stage": stage,
        "category": category,
        "reason": reason,
        "explanation": explanation,
        "next_surface": next_surface,
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
    if block.get("status") != "pass" or not _approval_required(stage, block):
        return None
    if _has_valid_approval(context["data"], stage):
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
    for stage in _STAGE_ORDER:
        block = stages.get(stage)
        if isinstance(block, dict):
            items.extend(_stage_items(table, source_path, stage, block))
        approval_item = _approval_item(context, stage, block)
        if approval_item is not None:
            items.append(approval_item)

    return [*items, *_status_level_items(context, items)]


def _items_from_status_path(root: Path, status_path: Path) -> list[dict[str, str]]:
    data = _load_yaml_mapping(status_path)
    if data is None:
        return []
    source_path = status_path.relative_to(root).as_posix()
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
