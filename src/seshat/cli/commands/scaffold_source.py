"""`seshat scaffold-source <table>` handler (issue #339): write the three
Stage-1 blank templates into ``mappings/<table>/`` so a pip-only user can
produce the first Source-Ready artifact without the development repository.

Lazy-imports ``seshat.stage1_scaffold`` (mirrors the other command handlers) to
keep the stdlib-only ``check`` core import chain unaffected (B1).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def scaffold_source_main(args: argparse.Namespace) -> int:
    """Materialize the Stage-1 blanks; per-file non-destructive.

    Returns 0 on success (including an all-kept re-run), 1 on an unsafe table
    segment (writes nothing).
    """
    from seshat.stage1_scaffold import Stage1ScaffoldError, scaffold_source

    try:
        report = scaffold_source(Path(args.repo), args.table)
    except Stage1ScaffoldError as exc:
        print(f"[refused] {exc}", file=sys.stderr)
        return 1

    for rel in report.written:
        print(f"wrote {rel}")
    for rel in report.kept:
        print(f"kept {rel} (already present; not overwritten)")
    for note in report.notes:
        print(f"\nnext: {note}")
    return 0
