"""Argument definitions for the first-arrival and readiness workflow commands.

This module depends only on :mod:`argparse`.  ``parser._build_parser`` retains
the top-level add order, so its ``--help`` output remains the public contract.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from functools import partial


def _add_init_project_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "init-project",
        help=(
            "scaffold a fresh, empty Retail-BI project workspace for a new user "
            "(mappings/, warehouse/migrations/, powerbi/, reports/, "
            "evidence/, README.md, .env.example) -- no wizard"
        ),
    )
    p.add_argument(
        "name", metavar="NAME", help="workspace directory to create (under the CWD)"
    )
    p.add_argument(
        "--force",
        action="store_true",
        help=(
            "scaffold into an existing non-empty target; overwrites only the "
            "scaffold's own files (README.md, .env.example, .gitignore, "
            ".gitattributes, .gitkeep), never touches or deletes any other file"
        ),
    )


def _add_scaffold_source_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "scaffold-source",
        help=(
            "write the three Stage-1 blank templates (source-profile.md, "
            "readiness-status.yaml, source-map.yaml) into mappings/<table>/ "
            "so a fresh workspace has the Source-Ready artifacts to fill"
        ),
    )
    p.add_argument(
        "table",
        metavar="TABLE",
        help="table id / mapping folder name to scaffold under mappings/",
    )
    p.add_argument("--repo", default=".", help="repo root to scaffold into")


def _add_status_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "status",
        help=(
            "read-only projection of committed readiness state (per-table "
            "current_stage, evidence[], blocking_reasons[], next_action) -- "
            "the agent-control status surface (spec 109)"
        ),
    )
    p.add_argument("--repo", default=".", help="repo root to project status from")
    p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help=(
            "'text' (default) is human-readable and additive. 'json' emits the "
            "stable machine surface validated by "
            "schemas/agent-status.schema.json -- never a numeric score."
        ),
    )


def _add_next_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "next",
        help=(
            "read-only run-next answer: next action, blocker, approval "
            "requirement, terminal pass, or input defect; without --table (or "
            "with --format agent) emits the agent-facing next-action document"
        ),
    )
    p.add_argument("--repo", default=".", help="repo root to read from")
    p.add_argument(
        "--table",
        default=None,
        help=(
            "table identity to inspect (matches readiness-status table, source_id, "
            "or mappings/<table>/ directory); omit for the repo-level agent "
            "document focused on the most urgent table"
        ),
    )
    p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json", "agent"),
        default="text",
        help=(
            "'text' (default) is human-readable; 'json' emits the stable "
            "response; 'agent' emits the guarded agent-facing document"
        ),
    )


def _add_readiness_report_parser(
    sub: argparse._SubParsersAction,
    *,
    command: str,
    description: str,
    output_help: str,
) -> None:
    p = sub.add_parser(
        command,
        help=description,
    )
    p.add_argument("--repo", default=".", help="repo root to read from")
    p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help=output_help,
    )


def _add_evidence_pack_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "evidence-pack",
        help=(
            "read-only 10-section evidence pack preview for one table; "
            "surfaces section blockers and publish_ready state"
        ),
    )
    p.add_argument("--repo", default=".", help="repo root to read from")
    p.add_argument(
        "--table",
        required=True,
        help=(
            "table identity to inspect (matches readiness-status table, source_id, "
            "or mappings/<table>/ directory)"
        ),
    )
    p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="'text' (default) is human-readable; 'json' emits the pack document.",
    )


_FAMILIES: dict[str, Callable[[argparse._SubParsersAction], None]] = {
    "first_arrival": _add_init_project_parser,
    "scaffold_source": _add_scaffold_source_parser,
    "status": _add_status_parser,
    "next": _add_next_parser,
    "approvals": partial(
        _add_readiness_report_parser,
        command="approvals",
        description=(
            "read-only approval inbox over mappings/*/readiness-status.yaml; "
            "reports missing or invalid named-human approvals"
        ),
        output_help=(
            "'text' (default) is human-readable; 'json' emits the inbox document."
        ),
    ),
    "evidence_pack": _add_evidence_pack_parser,
    "blockers": partial(
        _add_readiness_report_parser,
        command="blockers",
        description=(
            "read-only blocker explainer over mappings/*/readiness-status.yaml; "
            "categorizes blockers and names the next surface"
        ),
        output_help=(
            "'text' (default) is human-readable; 'json' emits the blocker document."
        ),
    ),
}


def add_core_parsers(sub: argparse._SubParsersAction, *families: str) -> None:
    """Add named core parser families in the root parser's established order."""
    for family in families:
        _FAMILIES[family](sub)
