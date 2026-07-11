"""`retail pii-notice` handler for the read-only Personal-Data-Touch Notice.

Composes the notice for one table (read-only). ``--write`` persists it to
``mappings/<table>/pii-touch-notice.md`` (the ONLY file it writes); without it,
the notice is printed. Always exits 0 -- it is not a gate (FR-007).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def pii_notice_main(args: argparse.Namespace) -> int:
    from seshat.pii_notice import build_pii_notice, render_markdown

    notice = build_pii_notice(args.repo, args.table)

    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(notice, indent=2))
        return 0

    body = render_markdown(notice)
    if getattr(args, "write", False):
        out = Path(args.repo) / "mappings" / args.table / "pii-touch-notice.md"
        out.write_text(body, encoding="utf-8")
        print(f"wrote {out.as_posix()}")
    else:
        print(body, end="")
    return 0
