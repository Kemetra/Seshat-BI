"""Argument definitions for the curated analytics-stack integrations."""

import argparse

from seshat.integrations.catalog import (
    DEFAULT_PROFILE,
    PROFILE_NAMES,
    SUPPORTED_HARNESSES,
)


def add_integrations_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "integrations",
        help="plan, install, and validate the curated analytics integrations",
    )
    commands = parser.add_subparsers(dest="integrations_command", required=True)
    setup = commands.add_parser(
        "setup",
        help=(
            "install curated analytics profiles when --refresh and --apply are explicit"
        ),
    )
    setup.add_argument(
        "--repo", default=".", help="workspace root (default: current directory)"
    )
    setup.add_argument(
        "--profile",
        # DERIVED from the catalog, never re-typed: a profile added to the
        # catalog is reachable here with no second edit.
        choices=PROFILE_NAMES,
        default=DEFAULT_PROFILE,
        help=(
            f"curated analytics profile to plan or install (default: {DEFAULT_PROFILE})"
        ),
    )
    setup.add_argument(
        "--refresh",
        action="store_true",
        help=(
            "contact the official PyPI/GitHub/npm indexes to resolve the latest "
            "compatible versions; the default run is network-free"
        ),
    )
    setup.add_argument(
        "--apply", action="store_true", help="perform network/filesystem installation"
    )
    setup.add_argument(
        "--yes",
        action="store_true",
        help=(
            "confirm an already-requested --apply without an interactive prompt; "
            "it does not by itself enable --refresh or --apply"
        ),
    )
    setup.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="emit machine-readable results only",
    )
    setup.add_argument(
        "--harness",
        action="append",
        choices=SUPPORTED_HARNESSES,
        default=[],
        help=(
            "read-only discovery check for a supported agent harness; repeat to "
            "check more than one (installation is never inferred as discovery)"
        ),
    )
