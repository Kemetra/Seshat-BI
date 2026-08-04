"""Argument definitions for the first-arrival and readiness workflow commands.

This module depends only on :mod:`argparse`.  ``parser._build_parser`` retains
the top-level add order, so its ``--help`` output remains the public contract.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from functools import partial
from pathlib import Path


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


def _add_scaffold_design_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "scaffold-design",
        help=(
            "materialize the Stage-6/7 design + handoff templates (blueprint / "
            "visual-spec / report-composition / 16x9 grid / handoff pack) into "
            "the workspace so Dashboard-Ready and Publish-Ready authoring has "
            "templates to copy"
        ),
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


def _add_readiness_diff_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "readiness-diff",
        help=(
            "read-only comparison of committed readiness state between two git "
            "revisions (stage/blocker/approval changes, and whether anything "
            "REGRESSED); grants no approval and writes nothing"
        ),
    )
    p.add_argument("--repo", default=".", help="repo root to read from")
    p.add_argument(
        "range",
        nargs="?",
        default=None,
        metavar="BASE..HEAD",
        help=(
            "revision range to compare, e.g. `main..HEAD`. Equivalent to the "
            "--base/--head pair; give exactly one form, never both."
        ),
    )
    p.add_argument(
        "--base",
        default=None,
        metavar="REV",
        help="base revision (the 'before' side), e.g. `main`.",
    )
    p.add_argument(
        "--head",
        default=None,
        metavar="REV",
        help="head revision (the 'after' side), e.g. `HEAD`.",
    )
    p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help=(
            "'text' (default) is human-readable; 'json' emits the readiness-diff "
            "document -- categorical changes and a boolean has_regression, never "
            "a numeric score."
        ),
    )


def _add_xray_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "xray",
        help=(
            "read-only model-graph audit of a committed PBIP semantic model "
            "(unused fields, relationship risks, measure-graph findings); "
            "advisory only -- findings never change the exit code, and there "
            "is no numeric score"
        ),
    )
    p.add_argument("--repo", default=".", help="repo root to read from")
    p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help=(
            "'text' (default) is human-readable; 'json' emits the audit "
            "document -- findings and per-family counts, never a score."
        ),
    )


def _add_model_diff_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "model-diff",
        help=(
            "read-only semantic diff of the committed PBIP model against a "
            "base git ref, classified semantic/cosmetic/additive/removed in "
            "business terms; the base side is read with `git show` only"
        ),
    )
    p.add_argument("--repo", default=".", help="repo root to read from")
    p.add_argument(
        "--base",
        required=True,
        metavar="REV",
        help="base revision (the 'before' side), e.g. `origin/main`.",
    )
    p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help=(
            "'text' (default) is human-readable; 'json' emits the diff "
            "document -- classified changes and bucket counts."
        ),
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


def _add_reset_parser(sub: argparse._SubParsersAction) -> None:
    """`reset` (issue #433): tear ONE table back to a fresh Source stage by
    removing its complete DERIVED file-set (mappings/, exact-token silver/gold
    migrations, nested dbt models, shared dbt rows, table-scoped dagster run
    evidence) and STAGING the deletions (the #430 workaround made native).
    Preserves the bronze landing and every other table; never touches a live
    database. Prints the exact plan and asks for confirmation (`--yes` to
    skip); refuses fail-closed when stdin is non-interactive without `--yes`."""
    p = sub.add_parser(
        "reset",
        help=(
            "remove ONE table's derived file-set (mappings/, migrations, dbt "
            "models, shared-file rows, dagster run evidence) and stage the "
            "deletions, returning it to a fresh Source stage; preserves the "
            "bronze landing; never touches a live database"
        ),
    )
    p.add_argument(
        "table",
        metavar="TABLE",
        help="table id (the mappings/<table>/ directory name)",
    )
    p.add_argument("--repo", default=".", help="repo root to reset in")
    p.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="print the exact removal plan and exit 0 without removing anything",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="skip the interactive confirmation (for automation)",
    )
    p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help=(
            "'text' (default) is human-readable; 'json' emits the stable "
            "reset document -- never a numeric score."
        ),
    )


def add_report_arguments(p: argparse.ArgumentParser) -> None:
    """The `report` flags, defined ONCE.

    Both the `seshat report` subcommand and the standalone parser in
    ``commands/report.py`` call this. They were separate definitions and had already
    drifted -- the subcommand knew nothing of --from-gold, --figure-plan, --dsn or
    --audience, so documented options failed as unrecognized arguments.

    It lives here rather than in the command module so building the parser still
    imports no command code.
    """
    p.add_argument("--table", required=True, help="table id under mappings/")
    p.add_argument("--format", required=True, choices=("html", "xlsx", "pdf"))
    p.add_argument("--language", default="en")
    p.add_argument(
        "--audience",
        default="board",
        help="who the report is for; printed on the cover, not a locale",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path(".seshat-output") / "report",
        help="output directory (default .seshat-output/report)",
    )
    p.add_argument(
        "--layout",
        type=Path,
        default=None,
        help="print overlay; default mappings/<table>/design/report-layout.yaml",
    )
    p.add_argument(
        "--observations",
        type=Path,
        default=None,
        help="figures WITH values, read offline; no database is contacted",
    )
    p.add_argument(
        "--from-gold",
        action="store_true",
        help="read every figure's value from the warehouse; needs --figure-plan",
    )
    p.add_argument(
        "--figure-plan",
        type=Path,
        default=None,
        help="which figures to render and how to format them, carrying NO values",
    )
    p.add_argument(
        "--dsn",
        default=None,
        help="Postgres DSN for --from-gold; falls back to the workspace environment",
    )
    p.add_argument("--repo-root", type=Path, default=Path("."))


def _add_report_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "report",
        help=(
            "render an approved design as an HTML page, an Excel workbook or a "
            "PDF; every figure cites the approved metric contract it came from. "
            "Gated on dashboard_ready: pass. Needs the `report` extra "
            "(`report-pdf` as well for PDF)"
        ),
    )
    add_report_arguments(p)


_FAMILIES: dict[str, Callable[[argparse._SubParsersAction], None]] = {
    "first_arrival": _add_init_project_parser,
    "scaffold_source": _add_scaffold_source_parser,
    "scaffold_design": _add_scaffold_design_parser,
    "report": _add_report_parser,
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
    "readiness_diff": _add_readiness_diff_parser,
    "xray": _add_xray_parser,
    "model_diff": _add_model_diff_parser,
    "reset": _add_reset_parser,
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
