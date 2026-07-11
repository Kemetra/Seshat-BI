"""Read-only approval inbox for readiness-status files.

The inbox surfaces approval seams that need a named human or contain invalid
approval records. It never records decisions, never edits approvals[], and never
moves a stage to pass.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
_AUTHORITY_BY_STAGE: dict[str, str] = {
    "source_ready": "data_owner",
    "mapping_ready": "analyst",
    "semantic_model_ready": "metric_owner",
    "dashboard_ready": "governance",
    "publish_ready": "data_owner",
}
_APPROVAL_MARKERS: tuple[str, ...] = (
    "approval",
    "approved",
    "reviewed",
    "sign-off",
    "signoff",
)


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


def _load_yaml_mapping(path: Path) -> dict[str, Any] | None:
    import yaml

    try:
        raw = path.read_text(encoding="utf-8-sig")
        data = yaml.safe_load(raw)
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _approval_required(stage_name: str, block: dict[str, Any]) -> bool:
    if stage_name in _APPROVAL_REQUIRED:
        return True
    return stage_name == "source_ready" and _source_kind(block) in _FILE_SOURCE_KINDS


def _stage_approvals(approvals: object, stage_name: str) -> list[dict[str, Any]]:
    if not isinstance(approvals, list):
        return []
    return [
        item
        for item in approvals
        if isinstance(item, dict) and item.get("stage") == stage_name
    ]


def _valid_stage_approval(approvals: object, stage_name: str) -> bool:
    return any(
        _valid_owner(item.get("owner"))
        for item in _stage_approvals(approvals, stage_name)
    )


def _invalid_stage_owners(approvals: object, stage_name: str) -> list[str]:
    owners: list[str] = []
    for item in _stage_approvals(approvals, stage_name):
        owner = item.get("owner")
        if not _valid_owner(owner):
            owners.append(str(owner))
    return owners


def _looks_like_approval_blocker(reason: str) -> bool:
    lowered = reason.lower()
    return any(marker in lowered for marker in _APPROVAL_MARKERS)


def _base_item(table: str, source_path: str, stage: str, status: str) -> dict[str, Any]:
    return {
        "table": table,
        "source_path": source_path,
        "stage": stage,
        "status": status,
        "required_authority": _AUTHORITY_BY_STAGE[stage],
    }


def _with_issue(
    item: dict[str, Any],
    issue: str,
    detail: str,
    extras: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    payload = extras or {}
    return {
        **item,
        "issue": issue,
        "detail": detail,
        "blocking_reasons": payload.get("blocking_reasons", []),
        "invalid_approvals": payload.get("invalid_approvals", []),
    }


def _blocked_approval_item(
    item: dict[str, Any], blockers: list[str], invalid_owners: list[str]
) -> dict[str, Any] | None:
    approval_blockers = [
        reason for reason in blockers if _looks_like_approval_blocker(reason)
    ]
    if not approval_blockers:
        return None
    return _with_issue(
        item,
        "blocked_for_approval",
        "stage is blocked on a recorded approval/review seam",
        {
            "blocking_reasons": approval_blockers,
            "invalid_approvals": invalid_owners,
        },
    )


def _missing_approval_item(
    item: dict[str, Any], blockers: list[str], invalid_owners: list[str]
) -> dict[str, Any]:
    issue = "invalid_approval" if invalid_owners else "missing_approval"
    detail = f"stage {item['stage']!r} is pass but no shape-valid approval is recorded"
    return _with_issue(
        item,
        issue,
        detail,
        {"blocking_reasons": blockers, "invalid_approvals": invalid_owners},
    )


def _stage_item(
    context: dict[str, Any],
    stage_name: str,
    block: dict[str, Any],
) -> dict[str, Any] | None:
    status = block.get("status")
    if not isinstance(status, str) or stage_name not in _AUTHORITY_BY_STAGE:
        return None

    approvals = context["approvals"]
    base = _base_item(context["table"], context["source_path"], stage_name, status)
    blockers = _as_str_list(block.get("blocking_reasons"))
    invalid_owners = _invalid_stage_owners(approvals, stage_name)

    if status == "blocked":
        return _blocked_approval_item(base, blockers, invalid_owners)
    if status != "pass" or not _approval_required(stage_name, block):
        return None
    if _valid_stage_approval(approvals, stage_name):
        return None
    return _missing_approval_item(base, blockers, invalid_owners)


def _table_name(data: dict[str, Any], fallback_table: str) -> str:
    table = data.get("table")
    return table if isinstance(table, str) and table else fallback_table


def _items_for_status(
    data: dict[str, Any], source_path: str, fallback_table: str
) -> list[dict[str, Any]]:
    table = _table_name(data, fallback_table)
    stages = data.get("stages")
    if not isinstance(stages, dict):
        return []

    approvals = data.get("approvals")
    context = {"table": table, "source_path": source_path, "approvals": approvals}
    items: list[dict[str, Any]] = []
    for stage_name in _STAGE_ORDER:
        block = stages.get(stage_name)
        if not isinstance(block, dict):
            continue
        item = _stage_item(
            context,
            stage_name=stage_name,
            block=block,
        )
        if item is not None:
            items.append(item)
    return items


def _items_from_status_path(root: Path, status_path: Path) -> list[dict[str, Any]]:
    data = _load_yaml_mapping(status_path)
    if data is None:
        return []
    source_path = status_path.relative_to(root).as_posix()
    return _items_for_status(data, source_path, status_path.parent.name)


def build_approval_inbox(repo_root: Path | str = ".") -> dict[str, Any]:
    """Return approval issues across committed mapping readiness statuses."""
    root = Path(repo_root)
    mappings_dir = root / "mappings"
    items: list[dict[str, Any]] = []
    if mappings_dir.is_dir():
        for status_path in sorted(mappings_dir.glob("*/readiness-status.yaml")):
            items.extend(_items_from_status_path(root, status_path))
    items.sort(
        key=lambda item: (item["source_path"], _STAGE_ORDER.index(item["stage"]))
    )
    return {"items": items, "read_only_proof": True}
