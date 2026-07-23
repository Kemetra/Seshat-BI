"""`retail semantic-check` handler: L3 contract<->DAX drift gate.

Extracted verbatim from the former ``retail/cli.py`` (CodeScene hotspot split).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _semantic_files(repo: Path, include_untracked: bool) -> tuple[Path, ...]:
    """Discover semantic inputs from Git, with a non-Git filesystem fallback."""

    def is_input(path: Path) -> bool:
        try:
            rel = path.relative_to(repo).as_posix()
        except ValueError:
            return False
        if rel.startswith("tests/") or "/tests/" in rel:
            return False
        return ("/metrics/" in f"/{rel}" and rel.endswith(".yaml")) or (
            ".SemanticModel/definition/" in rel and rel.endswith(".tmdl")
        )

    if not include_untracked:
        from seshat.gitutil import git_output

        try:
            git_root = Path(git_output(repo, "rev-parse", "--show-toplevel").strip())
            if git_root.resolve() != repo:
                raise RuntimeError(
                    "semantic repository is a subdirectory of another Git root"
                )
            raw = git_output(repo, "ls-files", "-z")
        except RuntimeError:
            pass
        else:
            return tuple(
                repo / Path(rel)
                for rel in raw.split("\0")
                if rel and is_input(repo / Path(rel))
            )
    candidates = sorted(repo.rglob("*.yaml")) + sorted(repo.rglob("*.tmdl"))
    return tuple(path for path in candidates if is_input(path))


def run_semantic_check(args: argparse.Namespace) -> int:
    """Run the L3 contract<->DAX drift gate.

    Lazy YAML, semantic, and TMDL imports live inside this handler so the
    stdlib-only `retail check` import chain never pulls them. Every committed
    measure must bind to a complete owner-approved contract, every approved
    contract must bind to a measure, and their shared definitions receive the
    L3 drift check. Git workspaces inspect tracked inputs by default; non-Git
    workspaces use a filesystem fallback.
    """
    from seshat.metric_contract_inventory import (
        load_contract_inventory,
        normalize_table_binding,
    )
    from seshat.runner import _format
    from seshat.semantic import MeasurePair, binding_error, run_semantic_pairs
    from seshat.tmdl import parse_tmdl

    repo = Path(args.repo).resolve()

    # Confine --metrics-dir to the repo tree: resolve it and reject a value that
    # traverses outside the repo root (e.g. `../../etc`) so contract discovery
    # cannot be pointed at arbitrary filesystem locations (audit 2026-06-26 #26).
    metrics_root = (repo / args.metrics_dir).resolve()
    if metrics_root != repo and not metrics_root.is_relative_to(repo):
        print(
            f"error: --metrics-dir {args.metrics_dir!r} escapes the repo root; "
            "it must resolve to a path inside --repo.",
            file=sys.stderr,
        )
        return 1

    inputs = _semantic_files(repo, getattr(args, "include_untracked", False))
    contract_paths = tuple(
        path
        for path in inputs
        if path.suffix == ".yaml" and path.is_relative_to(metrics_root)
    )
    inventory = load_contract_inventory(contract_paths, repo)

    # Parse the tracked TMDL measures and pair their approved contract definitions.
    pairs: list[MeasurePair] = []
    measure_locators: dict[tuple[str, str], str] = {}
    # The validated inventory rejects duplicate semantic bindings, so this
    # insertion cannot silently shadow a contract from another mapping scope.
    contracts_by_binding = {}
    for contract in inventory.approved.values():
        contracts_by_binding[contract.binding] = contract
    for tmdl_path in inputs:
        if tmdl_path.suffix != ".tmdl":
            continue
        rel = tmdl_path.relative_to(repo).as_posix()
        try:
            text = tmdl_path.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        table = parse_tmdl(text)
        if table is None:
            continue
        for measure in table.measures:
            locator = f"{rel}:{measure.line}"
            binding = (normalize_table_binding(table.name), measure.name)
            measure_locators.setdefault(binding, locator)
            contract = contracts_by_binding.get(binding)
            if contract is not None:
                pairs.append(
                    MeasurePair(
                        name=measure.name,
                        dax=measure.expression,
                        locator=locator,
                        definition=contract.definition,
                    )
                )

    findings = [
        binding_error("metric contract", error.partition(":")[0], error)
        for error in inventory.errors
    ]
    findings.extend(
        binding_error(binding[1], locator, "no approved metric contract")
        for binding, locator in sorted(measure_locators.items())
        if binding not in contracts_by_binding
    )
    findings.extend(
        binding_error(
            contract.name,
            contract.path.relative_to(repo).as_posix(),
            "approved metric contract has no corresponding TMDL measure",
        )
        for _key, contract in sorted(inventory.approved.items())
        if contract.binding not in measure_locators
    )
    drift_findings, _ = run_semantic_pairs(pairs)
    findings.extend(drift_findings)
    exit_code = (
        1 if any(finding.severity.value == "error" for finding in findings) else 0
    )
    for finding in findings:
        print(_format(finding))
    if exit_code == 0 and not findings:
        prog = getattr(args, "prog", "seshat")
        print(f"{prog} semantic-check: no drift (0 findings).", file=sys.stderr)
    return exit_code
