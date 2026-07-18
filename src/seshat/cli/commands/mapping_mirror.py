"""`seshat mapping-mirror` handler: guarantee the unresolved-questions mirror.

Thin CLI seam over :func:`seshat.mapping_mirror.ensure_unresolved_questions`
(issue #326). Lazy import mirrors the other subcommand handlers, keeping the
stdlib-only `retail check` core import chain unaffected (B1). Never prompts;
never overwrites an existing ledger; exit 1 on a refused table.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def mapping_mirror_main(args: argparse.Namespace) -> int:
    """Materialize ``mappings/<table>/unresolved-questions.md`` if absent."""

    from seshat.mapping_mirror import ensure_unresolved_questions

    try:
        result = ensure_unresolved_questions(Path(args.repo), args.table)
    except ValueError as exc:
        print(f"[refused] {exc}", file=sys.stderr)
        return 1

    action = "wrote" if result.created else "kept"
    print(f"{action} {result.path.as_posix()} ({result.status})")
    if result.status == "open-stub":
        print(
            "gate starts OPEN: raise each build-blocking question as a row; "
            "only a named human flips the status to CLEARED"
        )
    if result.status == "cleared-stub":
        print(
            "commit the generated ledger before any downstream build: an "
            "uncommitted clearance is not an audit record"
        )
    return 0
