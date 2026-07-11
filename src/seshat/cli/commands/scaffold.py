"""`retail scaffold` handler: rule-authoring boilerplate + --doctor drift check.

Extracted verbatim from the former ``retail/cli.py`` (CodeScene hotspot split).
"""

from __future__ import annotations

import argparse
import sys


def run_scaffold(args: argparse.Namespace) -> int:
    """Author a new rule's boilerplate, or --doctor the five wiring places.

    Author mode (default when --id + --title are given): writes exactly three
    targets and prints the golden-regen commands + a suggested glossary row +
    the import/__all__ edit. Exit 0 on write, non-zero on refusal.

    Doctor mode (--doctor): read-only; reports per-id per-place presence and
    exits non-zero on any drift (FR-014). An unknown --id is reported, not a
    crash-exit.

    The scaffold module is imported LAZILY here (stdlib-only, but kept off the
    module-scope import chain to mirror the other subcommand handlers).
    """
    from seshat import scaffold as scaffold_mod

    repo = args.repo

    if args.doctor:
        report = scaffold_mod.doctor(repo, args.rule_id)
        for entry in report.entries:
            states = ", ".join(
                f"{p.key}={entry.places[p.key]}" for p in scaffold_mod.FIVE_PLACES
            )
            drift = "DRIFT" if entry.has_drift else "ok"
            print(f"[{drift}] {entry.id}: {states}")
        if not report.entries:
            print(
                "scaffold --doctor: no registered rule ids to verify", file=sys.stderr
            )
        return 1 if report.has_drift else 0

    # Author mode: id + title are required.
    if not args.rule_id or not args.title:
        print(
            "error: author mode needs --id and --title (or pass --doctor to verify).",
            file=sys.stderr,
        )
        return 2
    result = scaffold_mod.scaffold(repo, args.rule_id, args.title)
    if not result.ok:
        print(f"[refused] {result.refused}", file=sys.stderr)
        return 1
    for w in result.written:
        print(f"wrote {w}")
    print("\nnext steps (run/apply by hand -- not written by scaffold):")
    for line in result.printed:
        print(f"  {line}")
    return 0
