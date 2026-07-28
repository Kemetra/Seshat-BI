"""Argparse-only surface for the lazy ``seshat analyze`` command family."""

from __future__ import annotations

import argparse


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=".", help="repository root")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="human-readable text or one stable JSON object",
    )


def add_analysis_parser(sub: argparse._SubParsersAction) -> None:
    """Add the closed validate/run/render statistical analysis family."""

    parent = sub.add_parser(
        "analyze",
        help="validate and run governed statistical analyses",
    )
    commands = parent.add_subparsers(dest="analysis_command", required=True)

    validate = commands.add_parser(
        "validate",
        help="validate a governed analysis specification and its policy",
    )
    validate.add_argument("--spec", required=True, help="analysis specification")
    _common(validate)

    run = commands.add_parser(
        "run",
        help="run one governed analysis and write immutable evidence",
    )
    run.add_argument("--spec", required=True, help="analysis specification")
    run.add_argument(
        "--provider",
        required=True,
        choices=("local_csv", "gold"),
        help="closed governed data provider",
    )
    run.add_argument(
        "--input",
        help="repo-contained CSV input; required only for local_csv",
    )
    _common(run)

    render = commands.add_parser(
        "render",
        help="validate evidence and rewrite only its human review",
    )
    render.add_argument("--evidence", required=True, help="evidence JSON artifact")
    _common(render)
