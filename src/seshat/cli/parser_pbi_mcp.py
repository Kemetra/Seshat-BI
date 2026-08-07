"""Argument definitions for the read-only Power BI MCP doctor family (#450).

Same closed-vocabulary adapter-family shape as ``seshat dagster`` / ``seshat
dbt`` (the sanctioned Option-B narrow-gate precedent): one ``pbi-mcp`` group,
three read-only verbs, no raw MCP arguments accepted. Registration is
stdlib-only; importing the root CLI never imports the pbi_mcp modules.
"""

from __future__ import annotations

import argparse

# Kept in sync with seshat.pbi_mcp.recommend.INTENTS by a unit test; a literal
# copy here keeps this module import-light (no package import at parse time).
_INTENT_CHOICES: tuple[str, ...] = (
    "model-edit",
    "published-query",
    "report-authoring",
    "report-formatting",
    "desktop-verification",
    "db-connectivity",
    "ci-validation",
    "sensitive-production",
)


def _add_doctor_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "doctor",
        help=(
            "read-only: detect the local environment and map a task intent "
            "to the governed Power BI surface (issue #450 section 7)"
        ),
    )
    parser.add_argument("--repo", default=".", help="repo root to inspect")
    parser.add_argument(
        "--target",
        default=None,
        help=(
            "exact governed table whose dashboard readiness applies; required "
            "for report-authoring"
        ),
    )
    parser.add_argument(
        "--intent",
        required=True,
        choices=_INTENT_CHOICES,
        help="the governed task you want routed (closed vocabulary)",
    )
    parser.add_argument(
        "--write-advisory",
        action="store_true",
        help=(
            "also write the .seshat/powerbi-mcp-recommendation.yaml advisory "
            "record (write-once; refuses to overwrite). Never a side effect."
        ),
    )
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="machine-readable output"
    )


def _add_generate_config_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "generate-config",
        help=(
            "emit a placeholder-only, read-only .mcp.json template (or the "
            "generated setup doc) -- secret-scanned, never overwrites"
        ),
    )
    parser.add_argument(
        "--transport",
        default="local",
        choices=("local", "remote", "both"),
        help="which official server shape(s) to include (default: local)",
    )
    parser.add_argument(
        "--setup-doc",
        dest="setup_doc",
        action="store_true",
        help="emit the generated setup guidance markdown instead of the JSON",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="write to this path instead of stdout (refuses to overwrite)",
    )


def _add_preflight_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "preflight",
        help=(
            "read-only capability discovery + target-allowlist validation; "
            "refuses write-mode/--skipconfirmation configs; fails closed on "
            "a not-passed semantic_model_ready gate; graceful when the MCP "
            "runtime is absent"
        ),
    )
    parser.add_argument("--repo", default=".", help="repo root to inspect")
    parser.add_argument(
        "--target", default=None, help="declared target to validate (optional)"
    )
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        help="allowlisted target (repeatable); a declared target requires one",
    )
    parser.add_argument(
        "--require-tool",
        dest="require_tool",
        action="append",
        default=[],
        help="capability the server must offer (repeatable)",
    )
    parser.add_argument(
        "--write-artifact",
        dest="write_artifact",
        action="store_true",
        help=(
            "also write .seshat/powerbi-mcp-preflight.json (derived evidence "
            "only, no score). Never a side effect."
        ),
    )
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="machine-readable output"
    )


def add_pbi_mcp_parsers(sub: argparse._SubParsersAction) -> None:
    """Register the closed pbi-mcp command vocabulary."""
    parser = sub.add_parser(
        "pbi-mcp",
        help=(
            "read-only Power BI MCP doctor family: doctor / generate-config "
            "/ preflight (#450 slices 2-4; F016 stays parked -- no mutation "
            "path exists here)"
        ),
    )
    commands = parser.add_subparsers(dest="pbi_mcp_cmd", required=True)
    for add_parser in (
        _add_doctor_parser,
        _add_generate_config_parser,
        _add_preflight_parser,
    ):
        add_parser(commands)
