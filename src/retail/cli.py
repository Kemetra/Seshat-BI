from __future__ import annotations

import argparse
import sys
from pathlib import Path

import retail.rules  # noqa: F401  (import for side effects: fires every @register)

from .registry import all_rules
from .runner import build_context, run


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Exposed (not inlined in ``main``) so flag->field mapping is unit-testable
    without executing any rules. The two commit-aware flags live UNDER the
    ``check`` subcommand alongside ``--repo``.
    """
    parser = argparse.ArgumentParser(
        prog="retail",
        description="Static governance checks for committed Power BI artifacts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="run static governance checks")
    check.add_argument("--repo", default=".", help="repo root to check")
    check.add_argument(
        "--commit-range",
        dest="commit_range",
        default=None,
        metavar="ORIGIN..HEAD",
        help="CI mode: git commit range to scope commit-aware rules (P2).",
    )
    check.add_argument(
        "--commit-msg-file",
        dest="commit_msg_file",
        default=None,
        metavar="PATH",
        help="commit-msg-hook mode: file holding the incoming commit message (P2).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as exc:
        # argparse exits 2 on bad/missing args (e.g. no subcommand); surface it
        # as a return code rather than letting it propagate.
        return int(exc.code or 0)

    if args.command == "check":
        commit_message: str | None = None
        if args.commit_msg_file is not None:
            try:
                raw = Path(args.commit_msg_file).read_text(encoding="utf-8")
            except FileNotFoundError:
                print(
                    f"error: commit message file not found: {args.commit_msg_file}",
                    file=sys.stderr,
                )
                sys.exit(1)
            # git's COMMIT_EDITMSG ends in a trailing newline (\r\n on Windows) —
            # strip it so the message passed to rules is the bare text.
            commit_message = raw.rstrip("\r\n")

        ctx = build_context(
            Path(args.repo),
            commit_range=args.commit_range,
            commit_message=commit_message,
        )
        return run(all_rules(), ctx)

    return 0
