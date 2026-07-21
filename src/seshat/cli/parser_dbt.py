"""Argparse-only surface for the lazy, governed ``seshat dbt`` family."""

from __future__ import annotations

import argparse
import re

_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _accepted_digest(value: str) -> str:
    if not _DIGEST.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "accepted plan must be exactly 64 lowercase hexadecimal characters"
        )
    return value


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=".", help="repository root")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="human-readable text or one stable JSON object",
    )


def _table(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--table",
        required=True,
        help="exact governed mappings/<table> identifier",
    )


def _add_dbt_parser(sub: argparse._SubParsersAction) -> None:
    """Add the closed six-command dbt helper family."""

    parent = sub.add_parser(
        "dbt",
        help="governed shadow dbt planning, execution, and evidence helpers",
    )
    commands = parent.add_subparsers(dest="dbt_command", required=True)

    doctor = commands.add_parser("doctor", help="check local dbt prerequisites")
    _common(doctor)

    validate = commands.add_parser(
        "validate", help="validate Mapping Ready and model citations"
    )
    _table(validate)
    _common(validate)

    scaffold = commands.add_parser(
        "scaffold",
        help=(
            "materialize the governed dbt model set (staging + gold star + parity "
            "audit + contracts + selector) from an approved source map (issue #406)"
        ),
    )
    _table(scaffold)
    _common(scaffold)

    plan = commands.add_parser("plan", help="create an immutable execution plan")
    _table(plan)
    _common(plan)

    for name in ("build", "test"):
        command = commands.add_parser(
            name, help=f"run the fixed governed dbt {name} workflow"
        )
        _table(command)
        command.add_argument(
            "--accept-plan",
            required=True,
            type=_accepted_digest,
            help="exact SHA-256 printed by `seshat dbt plan`",
        )
        _common(command)

    inspect = commands.add_parser(
        "inspect-run", help="validate an ignored local dbt artifact run"
    )
    _table(inspect)
    inspect.add_argument(
        "--artifacts",
        required=True,
        help="run directory contained under .seshat/dbt/runs/",
    )
    _common(inspect)

    init = commands.add_parser(
        "init",
        help=(
            "materialize the generic governed dbt working set into this "
            "workspace from bundled templates (never overwrites; issue #325)"
        ),
    )
    _common(init)
