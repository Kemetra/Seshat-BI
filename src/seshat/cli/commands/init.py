"""`retail init` handler: bootstrap the Compass-Driven kit substrate.

Extracted verbatim from the former ``retail/cli.py`` (CodeScene hotspot split).
"""

from __future__ import annotations

import argparse
import sys


def run_init(args: argparse.Namespace) -> int:
    """Bootstrap the kit substrate (feature 070). SUBSTRATE-WRITING ONLY.

    Writes the compass projection + manifests + the fenced SESHAT-KIT regions, then
    PRINTS the next agent step. Never prompts, never shows a menu, never profiles --
    the delegate/route/profile flow is the agent performing the `retail-init` skill.
    The module is imported LAZILY (it pulls in the pyyaml-using compass_project),
    mirroring the other subcommand handlers and keeping the check path yaml-free.
    """
    from seshat import kit_init

    try:
        result = kit_init.bootstrap(args.repo)
    except RuntimeError as exc:
        # A malformed fence is a hard stop -- report, do not force a rewrite.
        print(f"[stopped] {exc}", file=sys.stderr)
        return 1

    if result.already_bootstrapped:
        print("already bootstrapped -- re-projected the SESHAT-KIT regions.")
        # Fold (074): on a re-run, show WHAT the re-projection moved (e.g. after a
        # package upgrade), not just "already bootstrapped".
        if result.changed_targets:
            print("changed targets:")
            for t in result.changed_targets:
                print(f"    {t}")
        else:
            print("no targets changed (already in sync).")
    for w in result.written:
        print(f"wrote {w}")
    for name in result.fenced:
        print(f"projected SESHAT-KIT fence in {name}")
    print(f"\n{result.next_step}")
    return 0
