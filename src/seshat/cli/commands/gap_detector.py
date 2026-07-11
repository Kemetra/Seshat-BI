"""`retail dashboard-gaps` handler for the read-only Dashboard Gap Detector.

Classifies a human-supplied page-intent for one table against its committed
evidence into a pre-design gap inventory (SL1's five statuses + named blockers).
Read-only: PRINTS only, contains no file-write path, always exits 0 -- it is not
a gate (FR-008/FR-010).
"""

from __future__ import annotations

import argparse
import json


def gap_detector_main(args: argparse.Namespace) -> int:
    from seshat.gap_detector import build_gap_inventory, render_view

    view = build_gap_inventory(
        args.repo, args.table, getattr(args, "page_intent", None)
    )
    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(view, indent=2))
    else:
        print(render_view(view), end="")
    return 0
