"""Read-only approval inbox for readiness-status files.

The inbox surfaces approval seams that need a named human or contain invalid
approval records. It never records decisions, never edits approvals[], and never
moves a stage to pass.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from seshat.readiness_spine import (
    STAGE_AUTHORITY,
    STAGE_ORDER,
    approval_required,
    load_status_mapping,
    owner_is_valid,
    required_authority,
    stage_has_valid_approval,
)

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


def _stage_approvals(approvals: object, stage_name: str) -> list[dict[str, Any]]:
    if not isinstance(approvals, list):
        return []
    return [
        item
        for item in approvals
        if isinstance(item, dict) and item.get("stage") == stage_name
    ]


def _invalid_stage_owners(approvals: object, stage_name: str) -> list[str]:
    owners: list[str] = []
    for item in _stage_approvals(approvals, stage_name):
        owner = item.get("owner")
        if not owner_is_valid(owner):
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
        "required_authority": required_authority(stage),
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
    from seshat.rules.readiness_status import APPROVAL_SHAPE_HINT

    issue = "invalid_approval" if invalid_owners else "missing_approval"
    # Naming the shape here is the whole fix for issue #487: "no shape-valid
    # approval is recorded" told the reader a shape existed but never what it was,
    # so it had to be reverse-engineered from this module's source.
    detail = (
        f"stage {item['stage']!r} is pass but no shape-valid approval is "
        f"recorded; {APPROVAL_SHAPE_HINT}"
    )
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
    if not isinstance(status, str) or stage_name not in STAGE_AUTHORITY:
        return None

    approvals = context["approvals"]
    base = _base_item(context["table"], context["source_path"], stage_name, status)
    blockers = _as_str_list(block.get("blocking_reasons"))
    invalid_owners = _invalid_stage_owners(approvals, stage_name)

    if status == "blocked":
        return _blocked_approval_item(base, blockers, invalid_owners)
    if status != "pass" or not approval_required(stage_name, block):
        return None
    # One predicate with the gate: shape-valid AND a class eligible for the stage
    # (issue #487; audit F073 -- required_authority is now enforced, not decor).
    if stage_has_valid_approval(approvals, stage_name):
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
    for stage_name in STAGE_ORDER:
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


UNREADABLE_ISSUE = "unreadable_status"


def unreadable_status_item(table: str, source_path: str) -> dict[str, Any]:
    """An explicit item for a readiness file that cannot be parsed (audit F074).

    A corrupt file used to vanish from the inbox, so a table whose state could
    not be read looked exactly like a table with nothing awaiting approval.
    """
    return {
        "table": table,
        "source_path": source_path,
        "stage": None,
        "status": None,
        "required_authority": None,
        "issue": UNREADABLE_ISSUE,
        "detail": (
            "readiness-status.yaml is unreadable or not a mapping; its approval "
            "state cannot be established (this is NOT the same as 'nothing to "
            "approve')"
        ),
        "blocking_reasons": [],
        "invalid_approvals": [],
    }


def _items_from_status_path(root: Path, status_path: Path) -> list[dict[str, Any]]:
    source_path = status_path.relative_to(root).as_posix()
    data = load_status_mapping(status_path)
    if data is None:
        return [unreadable_status_item(status_path.parent.name, source_path)]
    return _items_for_status(data, source_path, status_path.parent.name)


def _sort_key(item: dict[str, Any]) -> tuple[str, int]:
    stage = item["stage"]
    return item["source_path"], STAGE_ORDER.index(stage) if stage else -1


def build_approval_inbox(repo_root: Path | str = ".") -> dict[str, Any]:
    """Return approval issues across committed mapping readiness statuses."""
    root = Path(repo_root)
    mappings_dir = root / "mappings"
    items: list[dict[str, Any]] = []
    if mappings_dir.is_dir():
        for status_path in sorted(mappings_dir.glob("*/readiness-status.yaml")):
            items.extend(_items_from_status_path(root, status_path))
    items.sort(key=_sort_key)
    return {"items": items, "read_only_proof": True}
