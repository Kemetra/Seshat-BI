"""`retail semantic-check` handler: L3 contract<->DAX drift gate.

Extracted verbatim from the former ``retail/cli.py`` (CodeScene hotspot split).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def run_semantic_check(args: argparse.Namespace) -> int:
    """Run the L3 contract<->DAX drift gate.

    Lazy imports (yaml via load_definition, plus semantic + metric_drift, plus the
    TMDL parser) live INSIDE this handler so the stdlib-only `retail check` import
    chain never pulls them. Pairs each committed measure (parsed from the model
    TMDL) with its contract definition (mappings/<dataset>/metrics/<name>.yaml) and
    reports drift (ERROR) / escalate (WARNING). Returns 1 iff any drift.

    Scans the model TMDL directly from the filesystem (not git ls-files): the
    semantic-check surface is not a registered rule, so it reads the repo tree
    directly -- which also makes it runnable in a non-git directory.
    """
    from seshat.metric_drift import load_definition
    from seshat.runner import _format
    from seshat.semantic import MeasurePair, run_semantic_pairs
    from seshat.tmdl import parse_tmdl

    repo = Path(args.repo)

    # Confine --metrics-dir to the repo tree: resolve it and reject a value that
    # traverses outside the repo root (e.g. `../../etc`) so contract discovery
    # cannot be pointed at arbitrary filesystem locations (audit 2026-06-26 #26).
    repo_resolved = repo.resolve()
    metrics_root = (repo / args.metrics_dir).resolve()
    if metrics_root != repo_resolved and not metrics_root.is_relative_to(repo_resolved):
        print(
            f"error: --metrics-dir {args.metrics_dir!r} escapes the repo root; "
            "it must resolve to a path inside --repo.",
            file=sys.stderr,
        )
        return 1

    # 1. Index contract definitions by measure name (YAML stem == measure name).
    definitions: dict[str, dict | None] = {}
    if metrics_root.is_dir():
        for contract_path in sorted(metrics_root.glob("*/metrics/*.yaml")):
            name = contract_path.stem
            try:
                definitions[name] = load_definition(str(contract_path))
            except (OSError, ValueError) as exc:
                print(
                    f"error: could not load contract {contract_path}: {exc}",
                    file=sys.stderr,
                )
                return 1

    # 2. Pair each committed measure with its contract definition (if any).
    # Scan *.SemanticModel/definition/**/*.tmdl, skipping any tests/ fixtures.
    # The recursive ``**`` glob matches zero-or-more intermediate dirs, so it
    # covers both top-level (definition/foo.tmdl) and nested (definition/tables/
    # foo.tmdl) files in one pass -- no separate top-level glob (which would
    # double-count) is needed.
    pairs: list[MeasurePair] = []
    for tmdl_path in sorted(repo.rglob("*.SemanticModel/definition/**/*.tmdl")):
        rel = tmdl_path.relative_to(repo).as_posix()
        if rel.startswith("tests/") or "/tests/" in rel:
            continue
        try:
            text = tmdl_path.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        table = parse_tmdl(text)
        if table is None:
            continue
        for measure in table.measures:
            if measure.name in definitions:
                pairs.append(
                    MeasurePair(
                        name=measure.name,
                        dax=measure.expression,
                        locator=f"{rel}:{measure.line}",
                        definition=definitions[measure.name],
                    )
                )

    # 3. Run the drift check; print findings; return the exit code.
    findings, exit_code = run_semantic_pairs(pairs)
    for finding in findings:
        print(_format(finding))
    if exit_code == 0 and not findings:
        print("retail semantic-check: no drift (0 findings).", file=sys.stderr)
    return exit_code
