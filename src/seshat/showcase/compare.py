"""Optional before/after comparison over two Passport snapshots (US4).

Two Passport snapshots are comparable only when they share ``schema_version``
and ``scope`` and differ in ``source_revision`` (R5). When comparable, the
stage transitions and evidence verdicts are expressed in the Passport
verify vocabulary reused from ``seshat.passport``. When not comparable --
different scope, different schema, only one snapshot, or none -- the result
carries ``comparable: False`` and a truthful ``omitted_reason``; no delta is
ever fabricated (FR-020/FR-021, INV-5). Read-only: no snapshot or workspace
file is written.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..passport import verify_passport


def _empty(reason: str) -> dict[str, Any]:
    return {
        "comparable": False,
        "omitted_reason": reason,
        "before_revision": None,
        "after_revision": None,
        "stage_transitions": [],
        "evidence_verdicts": [],
    }


def _load_snapshot(path: Any) -> dict[str, Any] | None:
    try:
        text = Path(path).read_text(encoding="utf-8")
        document = json.loads(text)
    except (OSError, ValueError, TypeError):
        return None
    return document if isinstance(document, dict) else None


def _comparability_reason(before: dict[str, Any], after: dict[str, Any]) -> str | None:
    if before.get("schema_version") != after.get("schema_version"):
        return "snapshots have different schema_version"
    if before.get("scope") != after.get("scope"):
        return "snapshots have different scope"
    if before.get("source_revision") == after.get("source_revision"):
        return "snapshots record the same source_revision (nothing to compare)"
    return None


def _readiness_table_map(document: dict[str, Any]) -> dict[Any, dict[str, Any]] | None:
    """Map ``table_id -> stages`` for a snapshot's ``readiness`` list, or
    ``None`` when that member is not a well-formed list (the malformed-shape
    guard: a snapshot cannot be diffed when its own shape cannot be read)."""
    readiness = document.get("readiness") or []
    if not isinstance(readiness, list):
        return None
    stages_by_table: dict[Any, dict[str, Any]] = {}
    for entry in readiness:
        if not isinstance(entry, dict):
            continue
        stages = entry.get("stages")
        if isinstance(stages, dict):
            stages_by_table[entry.get("table_id")] = stages
    return stages_by_table


def _stage_transition(
    table_id: Any, stage: str, before_block: Any, after_block: Any
) -> dict[str, Any] | None:
    if not isinstance(before_block, dict) or not isinstance(after_block, dict):
        return None
    before_status = before_block.get("status")
    after_status = after_block.get("status")
    if before_status == after_status:
        return None
    return {
        "table_id": table_id,
        "stage": stage,
        "before_status": before_status,
        "after_status": after_status,
    }


def _stage_transitions(
    before_stages_by_table: dict[Any, dict[str, Any]],
    after_stages_by_table: dict[Any, dict[str, Any]],
) -> list[dict[str, Any]]:
    transitions: list[dict[str, Any]] = []
    for table_id, after_stages in after_stages_by_table.items():
        before_stages = before_stages_by_table.get(table_id)
        if not isinstance(before_stages, dict):
            continue
        for stage, after_block in after_stages.items():
            transition = _stage_transition(
                table_id, stage, before_stages.get(stage), after_block
            )
            if transition is not None:
                transitions.append(transition)
    return transitions


def _absence_reason(snapshots: tuple[Any, Any] | None) -> str | None:
    if not snapshots:
        return "no snapshots were supplied"
    if len(snapshots) != 2 or snapshots[0] is None or snapshots[1] is None:
        return "only one snapshot was supplied"
    return None


def _incomparable_result(
    reason: str, before: dict[str, Any], after: dict[str, Any]
) -> dict[str, Any]:
    result = _empty(reason)
    result["before_revision"] = before.get("source_revision")
    result["after_revision"] = after.get("source_revision")
    return result


def build_comparison(
    repo_root: Path | str, snapshots: tuple[Any, Any] | None
) -> dict[str, Any]:
    """Always returns a dict (never ``None``) so absent/single/non-comparable
    inputs are each a truthful, testable outcome rather than a bare omission.
    ``build_showcase_bundle`` only stores this on the bundle when snapshots
    were actually supplied (see build.py); this function's own uniform
    return shape is what T024/T025 exercise directly.
    """
    absence_reason = _absence_reason(snapshots)
    if absence_reason is not None:
        return _empty(absence_reason)

    root = Path(repo_root).resolve()
    before_path, after_path = snapshots
    before = _load_snapshot(before_path)
    after = _load_snapshot(after_path)
    if before is None or after is None:
        return _empty("one or both supplied snapshot files could not be read")

    reason = _comparability_reason(before, after)
    if reason is not None:
        return _incomparable_result(reason, before, after)

    before_stages_by_table = _readiness_table_map(before)
    after_stages_by_table = _readiness_table_map(after)
    if before_stages_by_table is None or after_stages_by_table is None:
        return _incomparable_result(
            "one or both snapshots have a malformed 'readiness' member",
            before,
            after,
        )

    verify_result = verify_passport(root, after)
    evidence_verdicts = [
        {"path": item.get("path"), "verdict": item.get("verification")}
        for item in verify_result.get("artifacts", [])
        if isinstance(item, dict)
    ]
    return {
        "comparable": True,
        "omitted_reason": None,
        "before_revision": before.get("source_revision"),
        "after_revision": after.get("source_revision"),
        "stage_transitions": _stage_transitions(
            before_stages_by_table, after_stages_by_table
        ),
        "evidence_verdicts": evidence_verdicts,
    }
