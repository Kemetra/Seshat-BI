"""The ONE readiness spine shared by every read-only readiness surface.

``seshat next`` (run_next), ``seshat approvals`` (approval_inbox), the approver
view, the blocker explainer, the evidence pack and the governor used to carry
their own copies of the stage order, the approval-required set, the file-source
kinds, the stage->authority map and the "is this approval valid?" helper. The
copies drifted: two surfaces checked the owner shape only (a ``date:``-keyed or
``at: TBD`` approval passed), and none compared the owner's authority CLASS to
the stage. This module re-exports the single definitions from the RS1 rule
(``seshat.rules.readiness_status``) so a surface cannot disagree with the gate.

Read-only helpers: nothing here writes, grants an approval or moves a stage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from seshat.rules.readiness_status import (
    APPROVAL_REQUIRED,
    FILE_SOURCE_KINDS,
    STAGE_AUTHORITY,
    STAGE_ORDER,
    required_authority,
    stage_approval_valid,
)
from seshat.rules.readiness_status import _owner_is_valid as owner_is_valid
from seshat.rules.readiness_status import _source_kind as source_kind

__all__ = [
    "APPROVAL_REQUIRED",
    "FILE_SOURCE_KINDS",
    "STAGE_AUTHORITY",
    "STAGE_ORDER",
    "approval_required",
    "load_status_mapping",
    "owner_is_valid",
    "required_authority",
    "source_kind",
    "stage_approval_valid",
    "stage_has_valid_approval",
    "stage_valid_approval",
    "status_path_candidates",
    "table_candidate_names",
]

_UNSAFE_NAMES = frozenset({"", ".", ".."})


def load_status_mapping(path: Path) -> dict[str, Any] | None:
    """Parse one readiness-status file; None on any read/parse/shape failure."""
    import yaml

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def approval_required(stage: str, block: dict[str, Any]) -> bool:
    """Whether ``stage`` needs a named-human approval to pass (file sources too)."""
    if stage in APPROVAL_REQUIRED:
        return True
    return stage == "source_ready" and source_kind(block) in FILE_SOURCE_KINDS


def stage_valid_approval(approvals: object, stage: str) -> dict[str, Any] | None:
    """The first approvals[] entry that satisfies ``stage``, else None."""
    if not isinstance(approvals, list):
        return None
    return next(
        (item for item in approvals if stage_approval_valid(stage, item)),
        None,
    )


def stage_has_valid_approval(approvals: object, stage: str) -> bool:
    """Whether ``approvals`` holds an eligible, shape-valid approval of ``stage``."""
    return stage_valid_approval(approvals, stage) is not None


def table_candidate_names(table: str) -> list[str]:
    """Directory names a ``--table`` argument may resolve to under ``mappings/``.

    The name as given plus its unqualified (post-``.``) form. A name holding a
    path separator, or equal to ``.``/``..``, is refused so a table argument can
    never resolve outside ``mappings/<name>/`` (audit F232).
    """
    normalized = table.strip().replace("\\", "/").strip("/")
    names: list[str] = []
    for name in (normalized, normalized.rsplit(".", 1)[-1]):
        if name in _UNSAFE_NAMES or "/" in name or name in names:
            continue
        names.append(name)
    return names


def status_path_candidates(root: Path, table: str) -> list[Path]:
    """Candidate ``mappings/<name>/readiness-status.yaml`` paths for ``table``."""
    return [
        root / "mappings" / name / "readiness-status.yaml"
        for name in table_candidate_names(table)
    ]
