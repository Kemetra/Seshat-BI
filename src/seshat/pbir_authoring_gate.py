"""Fail-closed readiness gate for bounded PBIR mutation commands."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from seshat.gitstate import committed_text


@dataclass(frozen=True)
class PbirGateResult:
    """Whether committed evidence authorizes a bounded PBIR mutation."""

    allowed: bool
    blockers: tuple[str, ...]


def _valid_table_name(table: str) -> bool:
    return bool(table) and table not in {".", ".."} and Path(table).name == table


def _complete_dashboard_approval(document: dict[object, object]) -> bool:
    approvals = document.get("approvals")
    if not isinstance(approvals, list):
        return False
    for approval in approvals:
        if not isinstance(approval, dict) or approval.get("stage") != "dashboard_ready":
            continue
        if all(
            isinstance(approval.get(field), str) and approval[field].strip()
            for field in ("owner", "at", "note")
        ):
            return True
    return False


def check_pbir_authoring_gate(repo_root: Path, table: str) -> PbirGateResult:
    """Check committed, exact-table semantic and human-approval evidence."""

    if not _valid_table_name(table):
        return PbirGateResult(
            allowed=False,
            blockers=("--table must be one exact table name without path traversal",),
        )

    relative = f"mappings/{table}/readiness-status.yaml"
    text = committed_text(Path(repo_root), relative)
    if text is None:
        return PbirGateResult(
            allowed=False,
            blockers=(
                f"{relative} must be tracked, committed and clean before "
                "PBIR authoring",
            ),
        )

    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError:
        document = None
    if not isinstance(document, dict):
        return PbirGateResult(
            allowed=False,
            blockers=(f"{relative} must contain valid YAML mapping evidence",),
        )

    blockers: list[str] = []
    stages = document.get("stages")
    semantic = stages.get("semantic_model_ready") if isinstance(stages, dict) else None
    status = semantic.get("status") if isinstance(semantic, dict) else None
    if status != "pass":
        blockers.append(
            f"{table} semantic_model_ready must be pass in committed evidence"
        )
    if not _complete_dashboard_approval(document):
        blockers.append(
            f"{table} requires a complete named-human dashboard_ready approval"
        )
    return PbirGateResult(allowed=not blockers, blockers=tuple(blockers))


def enforce_pbir_authoring_gate(args: object, command: str) -> bool:
    """Render gate blockers for a mutating CLI command and return its decision."""

    result = check_pbir_authoring_gate(Path(args.repo), args.table)
    for blocker in result.blockers:
        print(f"{command}: blocked: {blocker}", file=sys.stderr)
    return result.allowed
