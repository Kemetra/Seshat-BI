"""`seshat scaffold-design` handler (issues #440, #441): write the six
Stage-6/7 design + handoff blank templates into the workspace so a pip-only
user can produce Dashboard-Ready / Publish-Ready artifacts without the
development repository.

Lazy-imports ``seshat.design_scaffold`` (mirrors the other command handlers)
to keep the stdlib-only ``check`` core import chain unaffected (B1).
"""

from __future__ import annotations

import argparse
import sys


def scaffold_design_main(args: argparse.Namespace) -> int:
    """Materialize the Stage-6/7 design blanks; per-file non-destructive.

    Returns 0 on success (including an all-kept re-run), 1 if the bundled
    template data is missing or the destination is unsafe to write into.
    """
    from pathlib import Path

    from seshat import cli
    from seshat.design_scaffold import scaffold_design
    from seshat.safe_write import SafeWriteError

    prog = cli._prog(args)  # brand the client typed (`seshat`/`retail`), #402
    try:
        report = scaffold_design(Path(args.repo))
    except (OSError, SafeWriteError) as exc:
        # OSError (incl. NotADirectoryError/PermissionError/FileNotFoundError from
        # an unwritable/misnamed --repo) and SafeWriteError both surface as the
        # documented [refused] line + exit 1, never a raw traceback (Codex #451).
        print(f"{prog} scaffold-design: [refused] {exc}", file=sys.stderr)
        return 1

    for rel in report.written:
        print(f"wrote {rel}")
    for rel in report.kept:
        print(f"kept {rel} (already present; not overwritten)")
    # These are BLANK templates -- having them on disk grants nothing and advances
    # no stage. Do NOT tell the agent to fill Dashboard/Publish artifacts here: that
    # could start dashboard design before metric contracts, or Stage 7 before Stage
    # 6 passes (constitution hard-stops). Route the next step through the governed
    # `next`, which reports the table's actual stage and the allowed next action.
    # Carry --repo into the follow-up so `next` inspects THIS workspace, not the
    # caller's cwd (the next parser defaults --repo to '.'), mirroring
    # scaffold-source (Codex #451).
    repo_arg = f" --repo {args.repo}" if args.repo not in (".", "") else ""
    print(
        f"\nnext: the blank templates are ready to copy. Run "
        f"`{prog} next{repo_arg} --table <table>` for the governed next action -- "
        f"fill a design/handoff template only when your table has reached that "
        f"stage (dashboard authoring needs metric contracts; the publish pack "
        f"needs Dashboard Ready). scaffold-design writes blanks only; it grants "
        f"nothing."
    )
    return 0
