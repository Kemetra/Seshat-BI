"""Spec-120 ecosystem subcommand parsers (passport / pack / benchmark / explorer).

Split out of ``parser.py`` verbatim (flag order, metavar, and help text
unchanged) because that module is a standing CodeScene
Lines-of-Code-in-a-Single-File hotspot: the four spec-120 verb groups pushed
it past the file-size threshold, and each group is self-contained. add-order
on top-level ``--help`` is still owned by ``parser._build_parser``, which
calls these helpers in its assembly sequence exactly like the in-module
``_add_*_parser`` helpers. argparse-only (stdlib), same purity contract as
``parser.py``.
"""

from __future__ import annotations

import argparse


def _add_passport_parser(sub: argparse._SubParsersAction) -> None:
    """`passport` verb group (spec 120, US4): export a portable readiness
    passport from committed state, and verify one against the current
    workspace. Both legs are projections over existing readiness authorities;
    neither grants approval nor advances a stage. Export output is contained
    under `.seshat-output/` and disclosure-gated (fail closed)."""
    passport_p = sub.add_parser(
        "passport",
        help=(
            "portable readiness passports: export a disclosure-safe evidence "
            "snapshot or verify one against the workspace (never an approval)"
        ),
    )
    passport_sub = passport_p.add_subparsers(dest="passport_command", required=True)

    export_p = passport_sub.add_parser(
        "export",
        help="assemble and write a passport for one or more tables",
    )
    export_p.add_argument("--repo", default=".", help="repo root to read from")
    export_p.add_argument(
        "--table",
        action="append",
        default=None,
        metavar="TABLE",
        help=(
            "table identity to include (repeatable); omit to include every "
            "table with a committed readiness-status.yaml"
        ),
    )
    export_p.add_argument(
        "--output",
        default=".seshat-output/passports/passport.json",
        metavar="PATH",
        help=(
            "passport output under .seshat-output/ "
            "(default: .seshat-output/passports/passport.json)"
        ),
    )
    export_p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="'text' (default) prints a summary; 'json' prints the passport.",
    )

    verify_p = passport_sub.add_parser(
        "verify",
        help="verify a passport's artifact identities against the workspace",
    )
    verify_p.add_argument("--repo", default=".", help="repo root to verify against")
    verify_p.add_argument(
        "--passport",
        required=True,
        metavar="PATH",
        help="path to the passport JSON to verify",
    )
    verify_p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="'text' (default) is human-readable; 'json' emits the result.",
    )


def _add_pack_parser(sub: argparse._SubParsersAction) -> None:
    """`pack` verb group (spec 120, US5): scaffold and validate declarative
    local extension packs. Packs are explicitly selected data + prose; they
    never execute, never reorder stages, and never carry approval authority.
    Validation reports conflicts before any pack content reaches a
    projection; there is no install/activate verb by design. The validate
    subcommand's flags live in ``_add_pack_validate_args`` (split, add-order
    preserved, to stay under the CodeScene 70-line Large-Method threshold)."""
    pack_p = sub.add_parser(
        "pack",
        help=(
            "governed local extension packs: scaffold a declarative pack "
            "skeleton or validate manifests + their selection graph"
        ),
    )
    pack_sub = pack_p.add_subparsers(dest="pack_command", required=True)

    scaffold_p = pack_sub.add_parser(
        "scaffold",
        help="write a new category-aware declarative pack skeleton",
    )
    scaffold_p.add_argument("--repo", default=".", help="repo root to write into")
    scaffold_p.add_argument(
        "--id",
        dest="pack_id",
        required=True,
        metavar="OWNER.NAME",
        help="owner-qualified lowercase pack id (e.g. acme.retail-kpis)",
    )
    scaffold_p.add_argument(
        "--category",
        required=True,
        choices=(
            "kpi",
            "source_vocabulary",
            "warehouse_compatibility",
            "regional_policy",
            "accessibility",
            "dashboard_blueprint",
        ),
        help="supported pack category",
    )
    scaffold_p.add_argument(
        "--owner",
        required=True,
        metavar="NAME",
        help="named human or team that owns this pack's content",
    )
    scaffold_p.add_argument(
        "--dir",
        default=None,
        metavar="PATH",
        help="target directory (default: packs/local/<name>); must be new",
    )
    _add_pack_validate_args(pack_sub)


def _add_pack_validate_args(pack_sub: argparse._SubParsersAction) -> None:
    """The `pack validate` subcommand: split verbatim off ``_add_pack_parser``
    (add-order preserved) to keep that helper under the CodeScene 70-line
    Large-Method threshold; no flag/help text changes."""
    validate_p = pack_sub.add_parser(
        "validate",
        help="validate pack manifests and their cross-pack selection graph",
    )
    validate_p.add_argument("--repo", default=".", help="repo root to read from")
    validate_p.add_argument(
        "--pack",
        action="append",
        required=True,
        metavar="PATH",
        help="path to a seshat-pack.yaml manifest (repeatable)",
    )
    validate_p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="'text' (default) is human-readable; 'json' emits the findings.",
    )


def _add_benchmark_parser(sub: argparse._SubParsersAction) -> None:
    """`benchmark` verb group (spec 120, US7): run the vendor-neutral agent
    safety benchmark against the deterministic scripted reference
    participant, and render a run's categorical scenario matrix. No
    aggregate score, percentage, rank, or leaderboard is ever emitted."""
    benchmark_p = sub.add_parser(
        "benchmark",
        help=(
            "agent safety benchmark: run synthetic scenarios against the "
            "scripted reference participant or report a run (no scores)"
        ),
    )
    benchmark_sub = benchmark_p.add_subparsers(dest="benchmark_command", required=True)

    run_p = benchmark_sub.add_parser(
        "run",
        help="run scenario manifests against the reference participant",
    )
    run_p.add_argument("--repo", default=".", help="repo root to read from")
    run_p.add_argument(
        "--scenarios",
        action="append",
        required=True,
        metavar="PATH",
        help="path to a scenario manifest YAML (repeatable)",
    )
    run_p.add_argument(
        "--repetitions",
        type=int,
        default=1,
        metavar="N",
        help="repetitions per scenario (disclosed in the run document)",
    )
    run_p.add_argument(
        "--output",
        default=".seshat-output/benchmark/run.json",
        metavar="PATH",
        help=(
            "run document output under .seshat-output/ "
            "(default: .seshat-output/benchmark/run.json)"
        ),
    )

    report_p = benchmark_sub.add_parser(
        "report",
        help="render a run document as the categorical scenario matrix",
    )
    report_p.add_argument(
        "--run",
        required=True,
        metavar="PATH",
        help="path to the benchmark run JSON to render",
    )
    report_p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="'text' (default) is human-readable; 'json' emits the matrix.",
    )


def _add_explorer_parser(sub: argparse._SubParsersAction) -> None:
    """`explorer` verb group (spec 120, US8): generate the disclosure-safe
    offline readiness explorer from committed state only. Local output under
    `.seshat-output/`; a blocked disclosure result blocks generation
    (fail-closed). Publication stays an explicit human action."""
    explorer_p = sub.add_parser(
        "explorer",
        help=(
            "offline static readiness explorer over committed state "
            "(table-by-stage status, evidence, blockers, approvals, lineage)"
        ),
    )
    explorer_sub = explorer_p.add_subparsers(dest="explorer_command", required=True)

    build_p = explorer_sub.add_parser(
        "build",
        help="generate the self-contained explorer HTML under .seshat-output/",
    )
    build_p.add_argument("--repo", default=".", help="repo root to read from")
    build_p.add_argument(
        "--output",
        default=".seshat-output/explorer/index.html",
        metavar="PATH",
        help=(
            "HTML output under .seshat-output/ "
            "(default: .seshat-output/explorer/index.html)"
        ),
    )
