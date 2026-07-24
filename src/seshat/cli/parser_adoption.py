"""Argument-only parser wiring for the governed existing-PBIP entry path."""

from __future__ import annotations

import argparse


def _add_adopt_pbip_parser(sub: argparse._SubParsersAction) -> None:
    """Add the explicit read-only assessment and accepted-scaffold commands."""
    adopt = sub.add_parser(
        "adopt-pbip",
        help=(
            "assess an existing PBIP project read-only, or create its one "
            "accepted adoption baseline"
        ),
    )
    commands = adopt.add_subparsers(dest="adopt_pbip_command", required=True)

    assess = commands.add_parser(
        "assess",
        help="read-only PBIP inventory, governance findings, and one next action",
    )
    assess.add_argument(
        "--project", required=True, help="PBIP project directory or PBIX boundary file"
    )
    assess.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="text is human-reviewable; json is the stable assessment contract",
    )

    scaffold = commands.add_parser(
        "scaffold",
        help="create only the accepted .seshat/adoption/pbip-adoption.yaml baseline",
    )
    scaffold.add_argument("--project", required=True, help="PBIP project directory")
    scaffold.add_argument(
        "--accept-assessment",
        required=True,
        help="exact 64-character digest from the assessment being accepted",
    )
    scaffold.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="text is human-reviewable; json is the stable scaffold-result contract",
    )

    measure_sync = commands.add_parser(
        "measure-sync",
        help=(
            "upsert APPROVED contract measures into one table of an already-"
            "adopted (scaffolded) semantic model; partition/M source stays "
            "byte-identical"
        ),
    )
    measure_sync.add_argument(
        "--repo",
        default=".",
        help="governed repository root holding mappings/<scope>/metrics",
    )
    measure_sync.add_argument(
        "--model",
        required=True,
        help="path to the adopted .SemanticModel directory",
    )
    measure_sync.add_argument(
        "--table",
        required=True,
        help="target table name as parsed from TMDL (e.g. 'gold fct_sales')",
    )
    measure_sync.add_argument(
        "--metrics-dir",
        default="mappings",
        help="metric-contract root under --repo (default: mappings)",
    )
    measure_sync.add_argument(
        "--dry-run",
        action="store_true",
        help="print the per-measure plan (insert/update/skip) and write nothing",
    )
    measure_sync.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="text is human-reviewable; json is the stable sync-result contract",
    )


__all__ = ["_add_adopt_pbip_parser"]
