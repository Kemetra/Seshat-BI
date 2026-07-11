"""`retail approver-view` handler for the read-only Approver Decision Surface.

Composes a refutation-first reading view for one table (read-only). Always exits
0 -- it is not a gate (FR-007). No --write in the MVP: the default is a pure read.
"""

from __future__ import annotations

import argparse
import json


def approver_view_main(args: argparse.Namespace) -> int:
    from seshat.approver_view import build_approver_view, render_view

    view = build_approver_view(args.repo, args.table)
    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(view, indent=2))
    else:
        print(render_view(view), end="")
    return 0
