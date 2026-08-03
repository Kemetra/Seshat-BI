"""Command-line surface for the adopter-sim harness."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from scripts.adopter_sim.exitcodes import Exit

STEP_TIMEOUT_AGENT = 300
STEP_TIMEOUT_CLI = 120
INVOCATION_CEILING = 90 * 60


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adopter-sim",
        description=(
            "Run a Claude Code agent through an adopter journey in a workspace "
            "provably blind to this dev repo."
        ),
    )
    parser.add_argument("--journey", default="first-hour")
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="repeats per dataset; 1 labels every finding advisory",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["clean", "messy"],
        choices=["clean", "messy"],
    )
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument(
        "--invoked-by",
        default="",
        help="name of the human accepting a baseline update",
    )
    parser.add_argument("--agent-timeout", type=int, default=STEP_TIMEOUT_AGENT)
    parser.add_argument("--cli-timeout", type=int, default=STEP_TIMEOUT_CLI)
    parser.add_argument("--ceiling", type=int, default=INVOCATION_CEILING)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from scripts.adopter_sim.runner import run_invocation

    try:
        return int(run_invocation(args))
    except KeyboardInterrupt:
        print("[FAIL] interrupted", flush=True)
        return int(Exit.HARNESS_ERROR)
