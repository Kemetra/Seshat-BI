"""Argument definitions for the Dagster orchestration adapter family.

Registration is deliberately stdlib-only. Importing the root CLI therefore
does not import Dagster or the adapter runtime.
"""

from __future__ import annotations

import argparse


def _add_doctor_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "doctor", help="read-only preflight: environment, pinned dagster, gate state"
    )
    parser.add_argument("--repo", default=".", help="repo root to inspect")
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="machine-readable findings"
    )
    parser.add_argument(
        "--live-readiness",
        action="store_true",
        help=(
            "inspect configured engine, driver metadata, and credential presence "
            "without connecting or querying"
        ),
    )


def _add_run_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "run", help="execute one orchestration job behind the gates (fail-closed)"
    )
    parser.add_argument("--repo", default=".", help="repo root to run against")
    parser.add_argument(
        "--job",
        required=True,
        choices=("full_sequence_job", "through_gold_job"),
        help="the closed job vocabulary (no raw dagster arguments are accepted)",
    )
    parser.add_argument(
        "--table",
        default=None,
        help="scope the run to one mapped table (via the discovery seam, never argv)",
    )
    parser.add_argument(
        "--source-mode",
        dest="source_mode",
        default="csv",
        choices=("csv", "existing-bronze"),
        help=(
            "Bronze source: 'csv' (default; a landing file OWNS/reloads bronze) "
            "or 'existing-bronze' (non-destructive DB-first: verify a pre-loaded "
            "bronze.<table> read-only, zero writes). #404/#405"
        ),
    )
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="machine-readable result"
    )


def _add_evidence_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "evidence", help="list runs or render a run's committed evidence markdown"
    )
    parser.add_argument("--repo", default=".", help="repo root to read")
    parser.add_argument(
        "--run-id", dest="run_id", default=None, help="render this run's evidence"
    )
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="machine-readable output"
    )


def _add_init_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "init",
        help=(
            "materialize the governed Dagster orchestration project into this "
            "workspace from bundled templates (never overwrites; issue #325)"
        ),
    )
    parser.add_argument("--repo", default=".", help="repo root to materialize into")
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="machine-readable result"
    )


def add_dagster_parsers(sub: argparse._SubParsersAction) -> None:
    """Register the closed Dagster command vocabulary."""
    parser = sub.add_parser(
        "dagster",
        help="Dagster orchestration adapter: doctor / run / evidence (spec 134)",
    )
    commands = parser.add_subparsers(dest="dagster_cmd", required=True)
    for add_parser in (
        _add_doctor_parser,
        _add_run_parser,
        _add_evidence_parser,
        _add_init_parser,
    ):
        add_parser(commands)
