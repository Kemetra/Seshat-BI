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
    from .metric_contract_inventory import load_contract_inventory

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
    inventory = load_contract_inventory(contract_paths, root)
    if inventory.errors or not inventory.approved:
        return "blocked"
    contracts = inventory.for_scope(scope_dir)
    contract_bindings = {contract.binding for contract in contracts.values()}
    model_bindings = _tmdl_measure_bindings(inputs)
    bound_tables = {table for table, _measure in contract_bindings}
    scoped_model_bindings = {
        binding for binding in model_bindings if binding[0] in bound_tables
    }
    if not contract_bindings or contract_bindings != scoped_model_bindings:
        return "blocked"
    if semantic_finding is not None and (
        semantic_finding.state != _STATE_COVERED
        or semantic_finding.class_ not in {"pass", "no_drift"}
        or semantic_finding.items
    ):
        return "blocked"
    return "verified"
