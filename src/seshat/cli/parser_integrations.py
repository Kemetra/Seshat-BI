"""Argument definitions for optional Fabric/Power BI integrations."""

import argparse


def add_integrations_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "integrations",
        help="plan, install, and validate optional Fabric/Power BI skills and MCPs",
    )
    commands = parser.add_subparsers(dest="integrations_command", required=True)
    setup = commands.add_parser(
        "setup",
        help="install supported skills/MCP configuration when --apply is explicit",
    )
    setup.add_argument(
        "--repo", default=".", help="workspace root (default: current directory)"
    )
    setup.add_argument(
        "--apply", action="store_true", help="perform network/filesystem installation"
    )
    setup.add_argument(
        "--yes",
        action="store_true",
        help="approve installation without an interactive prompt",
    )
    setup.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="emit machine-readable results",
    )
