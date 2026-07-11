"""`retail severity-posture` handler: regenerate the severity-posture record.

Extracted verbatim from the former ``retail/cli.py`` (CodeScene hotspot split).
"""

from __future__ import annotations

import argparse


def run_severity_posture(args: argparse.Namespace) -> int:
    """Regenerate the severity-posture golden record from live observation."""
    from seshat.severity_posture import RECORD_REL_PATH, write

    write(args.repo)
    print(f"wrote {RECORD_REL_PATH} from the live rule registry + L3 surface")
    return 0
