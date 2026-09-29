"""Metric-contract binding state for one governed scope (Portfolio Watch).

Extracted from ``portfolio_watch`` so the capability ``agent_next`` consumes
lives in its own module; ``portfolio_watch`` re-exports it unchanged. It
reads COMMITTED semantic inputs only (``seshat.semantic_inputs``) and never
grants an approval: ``verified`` means approved contracts bind the committed
model measures exactly, and a supplied semantic finding is clean and current.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

CONTRACT_BINDING_STATES = frozenset({"missing", "blocked", "verified"})
_STATE_COVERED = "covered"  # portfolio_watch.STATE_COVERED (no circular import)


def _semantic_inputs(root: Path, scope_dir: str) -> tuple[Path, ...] | None:
    """Committed semantic paths, or None when committed state is unknowable.

    None (-> ``blocked``) covers a git failure, a dirty or untracked input, and
    a workspace with no git at all: none of them is committed truth, and a git
    error is never read as a clean worktree.
    """
    from .semantic_inputs import (
        MODE_GIT,
        SemanticInputsUnavailable,
        discover_semantic_inputs,
        git_worktree_dirty,
    )

    try:
        inputs, mode = discover_semantic_inputs(root, include_untracked=False)
        if mode != MODE_GIT or git_worktree_dirty(
            root,
            f"mappings/{scope_dir}/metrics",
            f"mappings/{scope_dir}/readiness-status.yaml",
            "powerbi",
        ):
            return None
    except SemanticInputsUnavailable:
        return None
    return inputs


def _tmdl_measure_bindings(paths: tuple[Path, ...]) -> set[tuple[str, str]]:
    """Table-scoped model measures, using the semantic-check identity."""
    from .metric_contract_inventory import normalize_table_binding
    from .tmdl import parse_tmdl

    bindings: set[tuple[str, str]] = set()
    for path in paths:
        if path.suffix != ".tmdl":
            continue
        try:
            table = parse_tmdl(path.read_text(encoding="utf-8-sig"))
        except OSError:
            continue
        if table is not None:
            table_name = normalize_table_binding(table.name)
            bindings.update((table_name, measure.name) for measure in table.measures)
    return bindings


def _scope_bindings_match(contracts: dict, inputs: tuple[Path, ...]) -> bool:
    contract_bindings = {contract.binding for contract in contracts.values()}
    if not contract_bindings:
        return False
    bound_tables = {table for table, _measure in contract_bindings}
    scoped_model_bindings = {
        binding
        for binding in _tmdl_measure_bindings(inputs)
        if binding[0] in bound_tables
    }
    return contract_bindings == scoped_model_bindings


def _semantic_finding_clean(semantic_finding: Any) -> bool:
    if semantic_finding is None:
        return True
    if semantic_finding.state != _STATE_COVERED:
        return False
    if semantic_finding.class_ not in {"pass", "no_drift"}:
        return False
    return not semantic_finding.items


def _approved_bindings_match(
    contract_paths: tuple[Path, ...],
    root: Path,
    scope_dir: str,
    inputs: tuple[Path, ...],
) -> bool:
    from .metric_contract_inventory import load_contract_inventory

    inventory = load_contract_inventory(contract_paths, root)
    if inventory.errors or not inventory.approved:
        return False
    return _scope_bindings_match(inventory.for_scope(scope_dir), inputs)


def contract_binding_state(
    repo_root: Path | str,
    scope_dir: str,
    semantic_finding: Any = None,
) -> str:
    """Categorize one scope's metric contracts without granting an approval.

    The inventory is the shared Task-5 reader; this merely checks whether its
    approved names bind the model measures.  A supplied semantic finding must
    be a clean, current covered record before the portfolio calls it verified.
    """
    root = Path(repo_root).resolve()
    metrics_dir = root / "mappings" / scope_dir / "metrics"
    if not metrics_dir.is_dir():
        return "missing"
    inputs = _semantic_inputs(root, scope_dir)
    if inputs is None:
        return "blocked"
    contract_paths = tuple(
        path
        for path in inputs
        if path.suffix == ".yaml" and path.is_relative_to(metrics_dir)
    )
    if not contract_paths:
        return "missing"
    if not _approved_bindings_match(contract_paths, root, scope_dir, inputs):
        return "blocked"
    if not _semantic_finding_clean(semantic_finding):
        return "blocked"
    return "verified"
