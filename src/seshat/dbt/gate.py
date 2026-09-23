"""Fail-closed Mapping Ready entry gate for governed dbt operations."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from seshat.gitstate import is_tracked_and_clean, run_git
from seshat.unresolved_mirror import parse_mirror

from .contracts import (
    Blocker,
    GateDecision,
    GovernanceError,
    MappingApproval,
    WorkingSet,
)

_TABLE_ID = re.compile(r"^[a-z][a-z0-9_]*$")


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """One hardened, read-only git call (the shared ``gitstate`` wrapper)."""
    return run_git(repo_root, *args)


def _require_file(path: Path, code: str, label: str) -> None:
    if not path.is_file():
        raise GovernanceError(code, f"{label} is missing: {path.name}")


def _validate_table_id(table_id: str) -> None:
    if not _TABLE_ID.fullmatch(table_id):
        raise GovernanceError(
            "DBT_TABLE_ID_INVALID",
            "table ID must match ^[a-z][a-z0-9_]*$",
        )


def _mapping_paths(root: Path, table_id: str) -> tuple[Path, Path, Path, Path]:
    mapping_dir = root / "mappings" / table_id
    if not mapping_dir.is_dir():
        raise GovernanceError(
            "DBT_WORKING_SET_MISSING",
            f"mapping working set is missing for table {table_id}",
        )
    source_map = mapping_dir / "source-map.yaml"
    readiness_status = mapping_dir / "readiness-status.yaml"
    unresolved_questions = mapping_dir / "unresolved-questions.md"
    return mapping_dir, source_map, readiness_status, unresolved_questions


def _require_mapping_files(
    source_map: Path, readiness_status: Path, unresolved_questions: Path
) -> None:
    _require_file(source_map, "DBT_SOURCE_MAP_MISSING", "approved source map")
    _require_file(
        readiness_status,
        "DBT_READINESS_MISSING",
        "readiness status",
    )
    _require_file(
        unresolved_questions,
        "DBT_MAPPING_MIRROR_MISSING",
        "unresolved-question mirror",
    )


def _require_tracked_source_map(root: Path, relative_map: str) -> None:
    tracked = _git(root, "ls-files", "--error-unmatch", "--", relative_map)
    if tracked.returncode != 0:
        raise GovernanceError(
            "DBT_SOURCE_MAP_UNTRACKED",
            "approved source map must be committed before dbt planning",
        )


def _require_clean_source_map(root: Path, relative_map: str) -> None:
    clean = _git(root, "diff", "--quiet", "HEAD", "--", relative_map)
    if clean.returncode != 0:
        raise GovernanceError(
            "DBT_SOURCE_MAP_DIRTY",
            "approved source map differs from its committed approval revision",
        )


def _committed_revision(root: Path, relative_map: str) -> str:
    revision_result = _git(root, "rev-parse", f"HEAD:{relative_map}")
    revision = revision_result.stdout.strip()
    if revision_result.returncode != 0 or not re.fullmatch(
        r"[0-9a-f]{40,64}", revision
    ):
        raise GovernanceError(
            "DBT_SOURCE_MAP_REVISION_UNAVAILABLE",
            "could not resolve the approved source-map Git revision",
        )
    return revision


def _source_map_revision(root: Path, source_map: Path) -> str:
    relative_map = source_map.relative_to(root).as_posix()
    _require_tracked_source_map(root, relative_map)
    _require_clean_source_map(root, relative_map)
    return _committed_revision(root, relative_map)


def resolve_working_set(repo_root: Path, table_id: str) -> WorkingSet:
    """Resolve exactly one governed table and bind its committed source map."""

    _validate_table_id(table_id)
    root = Path(repo_root).resolve()
    paths = _mapping_paths(root, table_id)
    mapping_dir, source_map, readiness_status, unresolved_questions = paths
    _require_mapping_files(source_map, readiness_status, unresolved_questions)
    revision = _source_map_revision(root, source_map)

    return WorkingSet(
        repo_root=root,
        table_id=table_id,
        mapping_dir=mapping_dir,
        source_map=source_map,
        readiness_status=readiness_status,
        unresolved_questions=unresolved_questions,
        source_map_revision=revision,
        source_map_sha256=hashlib.sha256(source_map.read_bytes()).hexdigest(),
    )


def _approval_id(owner: str, approved_at: str, note: str) -> str:
    canonical = {
        "at": approved_at,
        "note": note,
        "owner": owner,
        "stage": "mapping_ready",
    }
    return hashlib.sha256(
        json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _valid_approval_date(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _approval_owner(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _approval_note(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _mapping_approval_row(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    if row.get("stage") != "mapping_ready":
        return None
    return row


def _approval_candidate(row: Any) -> MappingApproval | None:
    approval_row = _mapping_approval_row(row)
    if approval_row is None:
        return None
    owner = _approval_owner(approval_row.get("owner"))
    approved_at = _valid_approval_date(approval_row.get("at"))
    note = _approval_note(approval_row.get("note", ""))
    return _approval_from_fields(owner, approved_at, note)


def _approval_from_fields(
    owner: str | None, approved_at: str | None, note: str | None
) -> MappingApproval | None:
    if owner is None:
        return None
    if approved_at is None:
        return None
    if note is None:
        return None
    return MappingApproval(
        stage="mapping_ready",
        owner=owner,
        at=approved_at,
        note=note,
        approval_id=_approval_id(owner, approved_at, note),
    )


def _approval(rows: Any) -> MappingApproval | None:
    if not isinstance(rows, list):
        return None
    candidates: list[MappingApproval] = []
    for row in rows:
        candidate = _approval_candidate(row)
        if candidate is not None:
            candidates.append(candidate)
    return candidates[-1] if candidates else None


def _mirror_state(text: str) -> tuple[bool, bool]:
    state = parse_mirror(text)
    return state.gate_status == "CLEARED", state.open_rows == 0


def _relative(working_set: WorkingSet, path: Path) -> str:
    return path.relative_to(working_set.repo_root).as_posix()


def _committed_blob(working_set: WorkingSet, path: Path) -> str | None:
    """The HEAD text of a governed file, or None when it is not committed.

    The gate trusts only audited state: an untracked or dirty readiness record
    or mirror never entered history, so it can never unlock the gate. The
    content parsed is the committed blob, never the worktree bytes."""
    relative = _relative(working_set, path)
    if not is_tracked_and_clean(working_set.repo_root, relative):
        return None
    shown = _git(working_set.repo_root, "show", f"HEAD:{relative}")
    return shown.stdout if shown.returncode == 0 else None


def committed_sha256(working_set: WorkingSet, path: Path) -> str | None:
    """SHA-256 of a governed file's committed blob, or None if not committed."""
    text = _committed_blob(working_set, path)
    if text is None:
        return None
    return hashlib.sha256(text.encode("utf-8", "surrogateescape")).hexdigest()


def _uncommitted(working_set: WorkingSet) -> GateDecision:
    return GateDecision(
        allowed=False,
        table_id=working_set.table_id,
        mapping_status="uncommitted",
        approval=None,
        mirror_cleared=False,
        blocking_reasons=(
            Blocker(
                "DBT_MAPPING_UNCOMMITTED",
                "readiness status and the unresolved-question mirror must be "
                "committed and clean before dbt may trust them",
            ),
        ),
    )


def _read_readiness(text: str) -> tuple[dict[str, Any] | None, str]:
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return None, f"readiness status is not valid YAML: {exc.__class__.__name__}"
    if not isinstance(document, dict):
        return None, "readiness status must be a YAML mapping"
    return document, ""


def _invalid_readiness(working_set: WorkingSet, message: str) -> GateDecision:
    return GateDecision(
        allowed=False,
        table_id=working_set.table_id,
        mapping_status="invalid",
        approval=None,
        mirror_cleared=False,
        blocking_reasons=(Blocker("DBT_READINESS_INVALID", message),),
    )


def _mapping_status(document: dict[str, Any]) -> str:
    stages = document.get("stages")
    mapping = stages.get("mapping_ready") if isinstance(stages, dict) else None
    status = (
        mapping.get("status", "missing") if isinstance(mapping, dict) else "missing"
    )
    return status if isinstance(status, str) else "invalid"


def _gate_blockers(
    mapping_status: str,
    approval: MappingApproval | None,
    mirror_cleared: bool,
    questions_answered: bool,
) -> tuple[Blocker, ...]:
    rules = (
        (
            mapping_status != "pass",
            Blocker(
                "DBT_MAPPING_NOT_PASS",
                f"Mapping Ready is {mapping_status!r}; dbt requires 'pass'",
            ),
        ),
        (
            approval is None,
            Blocker(
                "DBT_MAPPING_APPROVAL_MISSING",
                "Mapping Ready has no matching named-human approval",
            ),
        ),
        (
            not mirror_cleared,
            Blocker(
                "DBT_MAPPING_MIRROR_BLOCKED",
                "unresolved-question mirror is not exactly CLEARED",
            ),
        ),
        (
            not questions_answered,
            Blocker(
                "DBT_MAPPING_QUESTIONS_OPEN",
                "one or more mapping questions are not answered",
            ),
        ),
    )
    return tuple(blocker for failed, blocker in rules if failed)


def evaluate_mapping_gate(working_set: WorkingSet) -> GateDecision:
    """Read the COMMITTED Mapping Ready state and mirror; change neither."""

    readiness_text = _committed_blob(working_set, working_set.readiness_status)
    mirror_text = _committed_blob(working_set, working_set.unresolved_questions)
    if readiness_text is None or mirror_text is None:
        return _uncommitted(working_set)
    document, error = _read_readiness(readiness_text)
    if document is None:
        return _invalid_readiness(working_set, error)
    mapping_status = _mapping_status(document)
    approval = _approval(document.get("approvals"))
    mirror_cleared, questions_answered = _mirror_state(mirror_text)
    blockers = _gate_blockers(
        mapping_status, approval, mirror_cleared, questions_answered
    )

    return GateDecision(
        allowed=not blockers,
        table_id=working_set.table_id,
        mapping_status=mapping_status,
        approval=approval,
        mirror_cleared=mirror_cleared,
        blocking_reasons=blockers,
    )
