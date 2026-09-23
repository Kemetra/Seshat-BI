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


def complete_stage_approval(document: dict[object, object], stage: str) -> bool:
    """A shape-valid approval of ``stage`` by an eligible class, with a note.

    Delegates to the ONE shared predicate (named human + authority class + ISO
    date + class eligible for the stage); ``{owner: claude, at: soon}`` fails it
    (audit F023). The non-empty ``note`` stays required, as before."""
    from seshat.readiness_spine import stage_approval_valid

    approvals = document.get("approvals")
    if not isinstance(approvals, list):
        return False
    return any(
        stage_approval_valid(stage, approval)
        and isinstance(approval.get("note"), str)
        and approval["note"].strip()
        for approval in approvals
    )


def _report_dir(target: Path) -> Path | None:
    for candidate in (target, *target.parents):
        if candidate.name.endswith(".Report"):
            return candidate
    return None


def _bound_model(root: Path, report: Path) -> Path | None:
    """The .SemanticModel the report's definition.pbir points at, inside root."""
    import json

    try:
        document = json.loads((report / "definition.pbir").read_text("utf-8-sig"))
        relative = document["datasetReference"]["byPath"]["path"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if not isinstance(relative, str):
        return None
    model = (report / relative).resolve()
    inside = model.is_relative_to(root) and model.name.endswith(".SemanticModel")
    return model if inside and model.is_dir() else None


def _model_tables(model: Path) -> set[str]:
    from seshat.metric_contract_inventory import normalize_table_binding
    from seshat.tmdl import parse_tmdl

    names: set[str] = set()
    for path in sorted((model / "definition" / "tables").glob("*.tmdl")):
        try:
            parsed = parse_tmdl(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError):
            continue
        if parsed is not None:
            names.add(normalize_table_binding(parsed.name))
    return names


def _table_gold_relations(root: Path, table: str) -> set[str]:
    from seshat.metric_contract_inventory import (
        approved_contracts_for_scope,
        normalize_table_binding,
    )

    approved, _errors = approved_contracts_for_scope(root, table, committed=True)
    return {normalize_table_binding(c.gold_table) for c in approved.values()}


def _target_blockers(repo_root: Path, table: str, target: Path | None) -> list[str]:
    """--report/--visual must sit in the repo, inside a report bound to a model
    that holds this table's approved gold relation (audit F023)."""
    root = Path(repo_root).resolve()
    if target is None:
        return ["a --report or --visual target is required"]
    resolved = Path(target).resolve()
    report = _report_dir(resolved)
    if not resolved.is_relative_to(root) or report is None:
        return ["the PBIR target must be inside a .Report folder in the repository"]
    model = _bound_model(root, report)
    if model is None:
        return [
            "the report's definition.pbir must reference a .SemanticModel inside "
            "the repository"
        ]
    if not _model_tables(model) & _table_gold_relations(root, table):
        return [
            f"the report's model does not hold a gold relation of {table}'s "
            "approved metric contracts"
        ]
    return []


def check_pbir_authoring_gate(
    repo_root: Path, table: str, target: Path | None = None, *, bind: bool = False
) -> PbirGateResult:
    """Check committed, exact-table semantic and human-approval evidence.

    With ``bind=True`` (every mutating command) the mutated ``target`` must also
    belong to a report bound to this table's model inside the repository."""

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
    if not complete_stage_approval(document, "dashboard_ready"):
        blockers.append(
            f"{table} requires a complete named-human dashboard_ready approval"
        )
    if bind:
        blockers.extend(_target_blockers(Path(repo_root), table, target))
    return PbirGateResult(allowed=not blockers, blockers=tuple(blockers))


def enforce_pbir_authoring_gate(args: object, command: str) -> bool:
    """Render gate blockers for a mutating CLI command and return its decision."""

    raw = getattr(args, "report", None) or getattr(args, "visual", None)
    target = Path(raw) if raw else None
    result = check_pbir_authoring_gate(Path(args.repo), args.table, target, bind=True)
    for blocker in result.blockers:
        print(f"{command}: blocked: {blocker}", file=sys.stderr)
    return result.allowed
