"""Argument definitions for the Dagster orchestration adapter family.

Registration is deliberately stdlib-only.  Importing the root CLI therefore
does not import Dagster or the adapter runtime.
"""

from __future__ import annotations

import argparse


def add_dagster_parsers(sub: argparse._SubParsersAction) -> None:
    """Register the closed Dagster command vocabulary."""
    dagster_p = sub.add_parser(
        "dagster",
        help="Dagster orchestration adapter: doctor / run / evidence (spec 134)",
    )
    dagster_sub = dagster_p.add_subparsers(dest="dagster_cmd", required=True)

    doctor_p = dagster_sub.add_parser(
        "doctor", help="read-only preflight: environment, pinned dagster, gate state"
    )
    doctor_p.add_argument("--repo", default=".", help="repo root to inspect")
    doctor_p.add_argument(
        "--json", dest="as_json", action="store_true", help="machine-readable findings"
    )
    doctor_p.add_argument(
        "--live-readiness",
        action="store_true",
        help=(
            "inspect configured engine, driver metadata, and credential presence "
            "without connecting or querying"
        ),
    )

    run_p = dagster_sub.add_parser(
        "run", help="execute one orchestration job behind the gates (fail-closed)"
    )
    run_p.add_argument("--repo", default=".", help="repo root to run against")
    run_p.add_argument(
        "--job",
        required=True,
        choices=("full_sequence_job", "through_gold_job"),
        help="the closed job vocabulary (no raw dagster arguments are accepted)",
    )
    run_p.add_argument(
        "--table",
        default=None,
        help="scope the run to one mapped table (via the discovery seam, never argv)",
    )
    run_p.add_argument(
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
    run_p.add_argument(
        "--json", dest="as_json", action="store_true", help="machine-readable result"
    )

    evidence_p = dagster_sub.add_parser(
        "evidence", help="list runs or render a run's committed evidence markdown"
    )
    evidence_p.add_argument("--repo", default=".", help="repo root to read")
    evidence_p.add_argument(
        "--run-id", dest="run_id", default=None, help="render this run's evidence"
    )
    evidence_p.add_argument(
        "--json", dest="as_json", action="store_true", help="machine-readable output"
    )

    init_p = dagster_sub.add_parser(
        "init",
        help=(
            "materialize the governed Dagster orchestration project into this "
            "workspace from bundled templates (never overwrites; issue #325)"
        ),
    )
    init_p.add_argument("--repo", default=".", help="repo root to materialize into")
    init_p.add_argument(
        "--json", dest="as_json", action="store_true", help="machine-readable result"
    )
