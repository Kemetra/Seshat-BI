"""`retail kit-lint` handler: fail loud on compass projection drift.

Extracted verbatim from the former ``retail/cli.py`` (CodeScene hotspot split).
"""

from __future__ import annotations

import argparse


def run_kit_lint(args: argparse.Namespace) -> int:
    """Fail loud on compass projection drift (feature 072). Read-only.

    Standalone step, NOT a `retail check` rule -- imported LAZILY (it pulls in the
    pyyaml-using compass_project), mirroring `_run_semantic_check` / `_run_init` and
    keeping the check path yaml-free. Exit 0 clean (or not-bootstrapped), 1 on drift.
    """
    from seshat import kit_lint

    report = kit_lint.lint(args.repo)

    if not report.bootstrapped:
        print("kit-lint: not bootstrapped -- run `retail init` (nothing to lint).")
        return 0

    for r in report.results:
        status = "ok" if r.ok else "DRIFT"
        print(f"[{status}] {r.name}")
        for d in r.details:
            print(f"    {d}")
    if report.ok:
        print("kit-lint: no projection drift.")
    return 0 if report.ok else 1
