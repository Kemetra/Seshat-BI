"""`retail init-project` handler: scaffold a fresh user workspace (spec 107).

Distinct from `retail init` (bootstraps `.seshat/` + fenced regions into an
EXISTING repo, see commands/init.py) -- `init-project <name>` creates a fresh,
empty Retail-BI project workspace for a new user (roadmap M3). Lazy import of
`seshat.workspace_init` mirrors the other subcommand handlers, keeping the
stdlib-only `retail check` core import chain unaffected (B1).
"""

from __future__ import annotations

import argparse
import sys


def init_project_main(args: argparse.Namespace) -> int:
    """Scaffold a fresh Retail-BI project workspace at ``args.name``.

    Refuses (exit 1, writes nothing) if the target directory already exists,
    is non-empty, and ``--force`` was not given. Refuses (exit 1) if the target
    resolves outside the current working directory (path-traversal guard).
    Never prompts / reads stdin -- no wizard, matching `retail init`'s posture.
    """
    from seshat.workspace_init import init_project

    try:
        written = init_project(args.name, force=args.force)
    except FileExistsError as exc:
        print(
            f"[refused] {exc} (pass --force to scaffold into it anyway)",
            file=sys.stderr,
        )
        return 1
    except ValueError as exc:
        print(f"[refused] {exc}", file=sys.stderr)
        return 1

    for path in written:
        print(f"wrote {path}")
    print(
        f"\nscaffolded workspace at {args.name}. "
        "Next: `seshat check` to verify a clean baseline."
    )
    return 0
