"""Argument definitions for validation and semantic governance commands.

These builders are argparse-only: optional database and YAML dependencies stay
behind their command handlers.
"""

from __future__ import annotations

import argparse


def add_validation_parsers(sub: argparse._SubParsersAction) -> None:
    """Register the validation command family in its existing public order."""
    _add_check_parser(sub)
    _add_validate_parser(sub)
    _add_profile_parser(sub)
    _add_drift_parser(sub)
    _add_semantic_and_value_check_parsers(sub)


def _add_check_parser(sub: argparse._SubParsersAction) -> None:
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
    check.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json", "review", "sarif"),
        default="text",
        help=(
            "findings output format. 'text' (default) is the human-readable "
            "[severity] id message (locator) lines, unchanged. 'json' emits one "
            "structured document for tooling; 'review' adds changed-state and a "
            "stable digest; 'sarif' emits SARIF 2.1.0. Exit policy is identical."
        ),
    )


def _add_validate_parser(sub: argparse._SubParsersAction) -> None:
    validate = sub.add_parser(
        "validate",
        help="run LIVE data checks against any Postgres DB (needs the 'db' extra)",
    )
    validate.add_argument(
        "--dsn",
        default=None,
        metavar="postgresql://...",
        help=(
            "Postgres connection string. Overrides env. If omitted, DATABASE_URL "
            "or the ANALYTICS_DB_* env vars are used. NEVER commit a real DSN."
        ),
    )
    validate.add_argument(
        "--source-map",
        dest="source_map",
        default=None,
        metavar="PATH",
        help=(
            "Path to a filled source-map.yaml. When given (with a DSN + the 'db' "
            "extra), the four live checks run against that table's targets. "
            "Without it, validate reports the deferred state."
        ),
    )


def _add_profile_parser(sub: argparse._SubParsersAction) -> None:
    profile = sub.add_parser(
        "profile",
        help="profile a landed (bronze) table for the Source Ready source-profile.md "
        "(needs a DSN + the 'db' extra)",
    )
    profile.add_argument(
        "--table",
        required=True,
        metavar="schema.table",
        help="the landed table to profile, schema-qualified, e.g. "
        "`bronze.sales_c086_raw`. An unqualified name is rejected: column "
        "discovery and the row/PK queries would resolve to different schemas "
        "on non-Postgres engines.",
    )
    profile.add_argument(
        "--pk",
        required=True,
        metavar="col[,col...]",
        help="the candidate grain key to prove unique on the landed data; "
        "comma-separate a composite, e.g. `invoice_id,line_no`.",
    )
    profile.add_argument(
        "--dsn",
        default=None,
        metavar="postgresql://...",
        help=(
            "Postgres connection string. Overrides env. If omitted, DATABASE_URL "
            "or the ANALYTICS_DB_* env vars are used. NEVER commit a real DSN."
        ),
    )
    profile.add_argument(
        "--format",
        dest="output_format",
        choices=("md", "json"),
        default="md",
        help="'md' (default) emits the source-profile.md blocks to paste, with "
        "a progress banner on stderr; 'json' emits the machine-readable "
        "ProfileResult and stays silent on stderr on success, so "
        "`--format json 2>&1 | jq` is safe (#436).",
    )


def _add_drift_parser(sub: argparse._SubParsersAction) -> None:
    drift = sub.add_parser(
        "drift",
        help="compare a baseline source-profile.md vs a live re-profile (F014); "
        "needs --dsn + the 'db' extra for the live leg",
    )
    drift.add_argument(
        "--baseline",
        required=True,
        metavar="PATH",
        help="path to the committed source-profile.md that earned Source Ready pass",
    )
    drift.add_argument(
        "--dsn",
        default=None,
        metavar="postgresql://...",
        help="Postgres DSN for the live re-profile. Without it, drift reports the "
        "deferred [PENDING LIVE RE-PROFILE] state. NEVER commit a real DSN.",
    )
    drift.add_argument(
        "--source-map",
        dest="source_map",
        default=None,
        metavar="PATH",
        help="path to the table's source-map.yaml (returns/PII rulings for the "
        "live leg). Default: the source-map.yaml sibling of --baseline. Absent "
        "=> the returns/PII drift classes stay silent.",
    )
    drift.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="'text' (default) human summary; 'json' emits the "
        "source-drift-findings.schema.json document.",
    )


def _add_semantic_and_value_check_parsers(sub: argparse._SubParsersAction) -> None:
    semantic = sub.add_parser(
        "semantic-check",
        help="L3 contract<->DAX denominator drift on committed metric contracts",
    )
    semantic.add_argument("--repo", default=".", help="repo root to check")
    semantic.add_argument(
        "--metrics-dir",
        dest="metrics_dir",
        default="mappings",
        metavar="DIR",
        help="root dir holding <dataset>/metrics/<Measure>.yaml contracts",
    )
    semantic.add_argument(
        "--include-untracked",
        action="store_true",
        help="also inspect untracked semantic inputs (default: tracked files only)",
    )

    value_check = sub.add_parser(
        "value-check",
        help="L4: recompute metric values live and compare to the approved value",
    )
    value_check.add_argument(
        "--repo", default=".", help="repo root to scan for contracts"
    )
    value_check.add_argument(
        "--metrics-dir",
        dest="metrics_dir",
        default="mappings",
        metavar="DIR",
        help="root dir holding <dataset>/metrics/<Measure>.yaml contracts",
    )
    value_check.add_argument(
        "--dsn",
        default=None,
        metavar="postgresql://...",
        help=(
            "Postgres connection string. Overrides env. If omitted, DATABASE_URL "
            "or the ANALYTICS_DB_* env vars are used. NEVER commit a real DSN."
        ),
    )
