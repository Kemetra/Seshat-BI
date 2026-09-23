"""`retail pii-notice` handler for the read-only Personal-Data-Touch Notice.

Composes the notice for one table (read-only). ``--write`` persists it to
``mappings/<table>/pii-touch-notice.md`` (the ONLY file it writes); without it,
the notice is printed. Always exits 0 -- it is not a gate (FR-007).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def pii_notice_main(args: argparse.Namespace) -> int:
    from seshat.pii_notice import build_pii_notice, render_markdown

    notice = build_pii_notice(args.repo, args.table)

    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(notice, indent=2))
        return 0

    body = render_markdown(notice)
    if getattr(args, "write", False):
        from seshat.pii_notice import _table_mapping_dir

        table_dir = _table_mapping_dir(Path(args.repo), args.table)
        if table_dir is None:
            # An invalid argument, not a gate verdict: nothing is written
            # outside mappings/<table>/.
            print(
                "error: --table must name one directory under mappings/; "
                "nothing written",
                file=sys.stderr,
            )
            return 1
        (table_dir / "pii-touch-notice.md").write_text(body, encoding="utf-8")
        shown = Path(args.repo) / "mappings" / args.table / "pii-touch-notice.md"
        print(f"wrote {shown.as_posix()}")
    else:
        print(body, end="")
    return 0
