"""`retail manifest` handler: regenerate the rule-registry snapshot manifest.

Extracted verbatim from the former ``retail/cli.py`` (CodeScene hotspot split).
"""

from __future__ import annotations

import argparse


def run_manifest(args: argparse.Namespace) -> int:
    """Regenerate the rule-registry snapshot manifest from the live registry."""
    from seshat.manifest import MANIFEST_REL_PATH, write_manifest

    write_manifest(args.repo)
    print(f"wrote {MANIFEST_REL_PATH} from the live rule registry")
    return 0
