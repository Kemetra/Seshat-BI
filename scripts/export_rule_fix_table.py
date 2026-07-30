"""Regenerate (or verify) the retail-govern skill's rule-id fix table.

Mirrors the ``export_agent_bundles.py`` idiom this repo already runs in CI: no flags
regenerates, ``--check`` proves the committed file matches a fresh render and exits
non-zero with concrete reasons when it does not.

The table's content comes from ``docs/rules/rule-fixes.yaml``; its id set comes from
``docs/rules/rules-manifest.json``. Only the bytes between the fence markers change.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from seshat.rule_fix_table import (  # noqa: E402
    RuleFixTableError,
    check_skill,
    summary,
    write_skill,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repo root (default: .)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed table matches a fresh render; write nothing",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = Path(args.repo)

    try:
        if args.check:
            reasons = check_skill(repo_root)
            for reason in reasons:
                print(f"error: {reason}", file=sys.stderr)
            if reasons:
                return 1
            counts = summary(repo_root)
            print(f"rule fix table is current ({counts['registered']} rules)")
            return 0

        changed = write_skill(repo_root)
        counts = summary(repo_root)
        state = "regenerated" if changed else "already current"
        print(f"rule fix table {state} ({counts['registered']} rules)")
        return 0
    except RuleFixTableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
