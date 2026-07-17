"""CLI argument-parser construction.

Extracted verbatim from the former ``retail/cli.py`` (CodeScene hotspot split).
``_build_parser`` assembles the subcommands by calling one ``_add_*_parser(sub)``
helper per subcommand (or per small related group), in the exact order they must
appear on top-level ``--help`` -- add-order and every flag's order/metavar/help
text stay byte-for-byte identical to the pre-split monolith. The helpers exist
because ``_build_parser`` itself is a standing CodeScene Large-Method hotspot
(70-line threshold): each new subcommand (spec 109's ``status`` is the latest)
gets its own ``_add_status_parser``-shaped helper instead of growing the body of
``_build_parser`` inline, which is what keeps the change-set delta from
re-degrading it. The spec-120 ecosystem verb groups (passport/pack/benchmark/
explorer) live in ``parser_ecosystem.py`` for the same reason at file scope
(the Lines-of-Code hotspot); ``_build_parser`` still owns their add-order.
argparse-only (stdlib), so importing this at ``cli/__init__.py`` module scope
stays pure.
"""

from __future__ import annotations

import argparse

from .parser_adoption import _add_adopt_pbip_parser
from .parser_dbt import _add_dbt_parser
from .parser_ecosystem import (
    _add_agent_parser,
    _add_benchmark_parser,
    _add_explorer_parser,
    _add_impact_map_parser,
    _add_pack_parser,
    _add_passport_parser,
    _add_watch_parser,
)


def _add_init_project_parser(sub: argparse._SubParsersAction) -> None:
    """`init-project` (spec 107, roadmap M3): scaffold a FRESH, empty Retail-BI
    project workspace for a new user -- distinct from `init` (which bootstraps
    `.seshat/` into an EXISTING repo). Pure stdlib filesystem; no DB/network;
    never prompts. Deliberately does NOT bootstrap `.seshat/` (see
    src/seshat/workspace_init.py for why). Extracted to keep `_build_parser`
    from growing (CodeScene large-method guard)."""
    p = sub.add_parser(
        "init-project",
        help=(
            "scaffold a fresh, empty Retail-BI project workspace for a new user "
            "(mappings/, warehouse/{bronze,silver,gold}/, powerbi/, reports/, "
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


def _add_status_parser(sub: argparse._SubParsersAction) -> None:
    """`status` (spec 109, roadmap M4, under ratified Option B): the ONE
    sanctioned CLI addition -- a thin, READ-ONLY JSON projection of committed
    ``mappings/*/readiness-status.yaml`` state. NOT a new computation; NOT a
    broad verb surface. Extracted (mirrors ``_add_init_project_parser``) to
    keep ``_build_parser`` from growing (CodeScene large-method guard)."""
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
    """`next` (spec 080 + Agent-Driven v0.1): read-only run-next readiness
    answer. With --table (text/json) it is the original per-table response;
    without --table, or with --format agent, it emits the agent-facing
    next-action document (current_stage, readiness_state, evidence,
    blocking_reasons, next_allowed_action, forbidden_scope,
    validation_commands, stop_point). It never writes, executes, approves, or
    emits a numeric readiness value."""
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


def _add_approvals_parser(sub: argparse._SubParsersAction) -> None:
    """`approvals`: read-only inbox for missing/invalid approval seams."""
    p = sub.add_parser(
        "approvals",
        help=(
            "read-only approval inbox over mappings/*/readiness-status.yaml; "
            "reports missing or invalid named-human approvals"
        ),
    )
    p.add_argument("--repo", default=".", help="repo root to read from")
    p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="'text' (default) is human-readable; 'json' emits the inbox document.",
    )


def _add_evidence_pack_parser(sub: argparse._SubParsersAction) -> None:
    """`evidence-pack`: read-only 10-section evidence pack preview."""
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


def _add_blockers_parser(sub: argparse._SubParsersAction) -> None:
    """`blockers`: read-only explanations for recorded readiness blockers."""
    p = sub.add_parser(
        "blockers",
        help=(
            "read-only blocker explainer over mappings/*/readiness-status.yaml; "
            "categorizes blockers and names the next surface"
        ),
    )
    p.add_argument("--repo", default=".", help="repo root to read from")
    p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="'text' (default) is human-readable; 'json' emits the blocker document.",
    )


def _add_pii_notice_parser(sub: argparse._SubParsersAction) -> None:
    """`pii-notice` (spec 114): read-only per-column PII-disclosure notice from a
    table's committed source-map.yaml. Echoes each pii:true column's flag +
    recorded governance disposition verbatim (joined by the column's
    deviation_ref); GAP-marks any pii:true column with no recorded decision.
    Renders no publish-safety verdict, emits no score, adds no gate."""
    p = sub.add_parser(
        "pii-notice",
        help=(
            "read-only per-column PII-disclosure notice for one table from its "
            "source-map.yaml; echoes recorded dispositions, GAP-marks undecided"
        ),
    )
    p.add_argument("--repo", default=".", help="repo root to read from")
    p.add_argument(
        "--table",
        required=True,
        help="table identity (the mappings/<table>/ directory name)",
    )
    p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="'text' (default) is human-readable; 'json' emits the notice document.",
    )
    p.add_argument(
        "--write",
        action="store_true",
        help=(
            "write the notice to mappings/<table>/pii-touch-notice.md (the only "
            "file it writes); without it, the notice is printed"
        ),
    )


def _add_approver_view_parser(sub: argparse._SubParsersAction) -> None:
    """`approver-view` (spec 115): read-only refutation-first reading view for a
    human signer over one table's committed readiness-status.yaml +
    unresolved-questions.md. Orders the refusal case (blocked/warning stages,
    unmet approvals, open questions) by the shipped fixed category rank;
    reassurance last. Writes nothing, grants no approval, emits no score."""
    p = sub.add_parser(
        "approver-view",
        help=(
            "read-only refutation-first signer view for one table: what would "
            "make you refuse first, reassurance last; writes nothing, no score"
        ),
    )
    p.add_argument("--repo", default=".", help="repo root to read from")
    p.add_argument(
        "--table",
        required=True,
        help="table identity (the mappings/<table>/ directory name)",
    )
    p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="'text' (default) is human-readable; 'json' emits the view document.",
    )


def _add_dashboard_planner_parser(sub: argparse._SubParsersAction) -> None:
    """`dashboard-planner` (spec 116): read-only categorical new/extends/duplicate
    verdict on a PROPOSED dashboard idea, compared against the target table's
    committed ``mappings/<table>/design/`` corpus by set membership over
    ``(bound_contract, dimension)`` tuples. Prints only; writes nothing; grants no
    approval; emits no score/overlap/ranking; adds no gate (a `new` verdict is not
    clearance to build)."""
    p = sub.add_parser(
        "dashboard-planner",
        help=(
            "read-only new/extends/duplicate verdict on a proposed dashboard idea "
            "vs the table's committed design corpus; writes nothing, no score"
        ),
    )
    p.add_argument("--repo", default=".", help="repo root to read from")
    p.add_argument(
        "--table",
        required=True,
        help="table identity (the mappings/<table>/ directory name)",
    )
    p.add_argument(
        "--proposal",
        default=None,
        metavar="TEXT_OR_@FILE",
        help=(
            "the proposed dashboard idea as free text, or @path to read it from a "
            "file; '<contract> by <dimension>' clauses are read as given"
        ),
    )
    p.add_argument(
        "--tuple",
        dest="tuple",
        action="append",
        metavar="Q::CONTRACT::DIM",
        help=(
            "an explicit proposed tuple '<business_question>::<contract>::"
            "<dimension>' (repeatable); question/dimension optional"
        ),
    )
    p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="'text' (default) is human-readable; 'json' emits the verdict document.",
    )


def _add_gap_detector_parser(sub: argparse._SubParsersAction) -> None:
    """`dashboard-gaps` (spec 117): read-only pre-design gap inventory. Given a
    human-supplied page-intent (business questions + their required metrics/
    dimensions), classifies each required item against the table's committed
    metric contracts, gold_star dimensions, and open owner decisions into ONE of
    SL1's five coverage statuses plus a named blocker. Writes nothing, records no
    pass, adds no gate, emits no score."""
    p = sub.add_parser(
        "dashboard-gaps",
        help=(
            "read-only pre-design gap inventory for one table + a supplied "
            "page-intent; per-item coverage status + named blocker, no score"
        ),
    )
    p.add_argument("--repo", default=".", help="repo root to read from")
    p.add_argument(
        "--table",
        required=True,
        help="table identity (the mappings/<table>/ directory name)",
    )
    p.add_argument(
        "--page-intent",
        dest="page_intent",
        default=None,
        metavar="PATH",
        help=(
            "path to the human-supplied page-intent YAML (business questions with "
            "their required metrics/dimensions); without it, a document-level GAP "
            "is reported and nothing is classified"
        ),
    )
    p.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="'text' (default) is human-readable; 'json' emits the inventory document.",
    )


def _add_check_parser(sub: argparse._SubParsersAction) -> None:
    """`check`: static governance checks. Extracted from ``_build_parser`` (with
    ``validate``/``semantic-check``/``value-check``/``demo``) to shrink the
    CodeScene Large-Method hotspot without changing any flag/help text."""
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
    """`validate`: LIVE data checks (feature 004). Needs a running DB + the
    optional `db` extra (psycopg2). The driver is imported LAZILY in
    _run_validate, never here, so `retail check` and CI (no driver installed)
    never import it. Connection is host-agnostic: ANY Postgres (local / remote /
    DigitalOcean / other) via a DSN -- from --dsn, or DATABASE_URL, or the
    ANALYTICS_DB_* parts."""
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


def _add_drift_parser(sub: argparse._SubParsersAction) -> None:
    """`drift` (F014): compare a committed baseline source-profile.md against a
    live observed re-profile and emit source-drift-findings. Two-mode like
    `validate`: without --dsn (no observed re-profile) it reports the deferred
    [PENDING LIVE RE-PROFILE] state + warning, never a fabricated diff. The DB
    driver is imported LAZILY in run_drift, never here. Extracted (not inlined
    into `_build_parser`) to keep that CodeScene Large-Method hotspot from
    growing."""
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
    """`semantic-check` (L3 contract<->DAX drift, DAX fortification Phase 1) and
    `value-check` (L4 value proxy, DAX fortification #4). Both parse metric-
    contract YAML lazily inside their handlers -- NOT in the stdlib-only
    `retail check` core chain. value-check reuses the validate path's lazy
    psycopg2 import; live-deferred by repo YAGNI: needs a DSN + the `db` extra."""
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


def _add_demo_parser(sub: argparse._SubParsersAction) -> None:
    """`demo` verb group (spec 083): prove the readiness spine on a generic
    sample. Extracted (with `check`/`validate`/`semantic-check`/`value-check`)
    to shrink the CodeScene Large-Method hotspot in ``_build_parser``."""
    demo_p = sub.add_parser(
        "demo",
        help="local demo harness: prove the readiness spine on a generic sample",
    )
    demo_sub = demo_p.add_subparsers(dest="demo_command", required=True)

    demo_init = demo_sub.add_parser(
        "init", help="materialize the demo fixtures into .demo-work/ (idempotent)"
    )
    demo_init.add_argument("--repo", default=".", help="repo root")
    demo_init.add_argument(
        "--force", action="store_true", help="refresh an existing working dir"
    )

    demo_load = demo_sub.add_parser(
        "load", help="offline: skip with reason; live: write demo-scoped sample"
    )
    demo_load.add_argument("--repo", default=".", help="repo root")
    demo_load.add_argument("--dsn", default=None, help="Postgres DSN for the live leg")

    demo_run = demo_sub.add_parser(
        "run", help="recompute per-stage readiness status (no separate state engine)"
    )
    demo_run.add_argument("--repo", default=".", help="repo root")
    demo_run.add_argument("--dsn", default=None, help="Postgres DSN for the live leg")

    demo_report = demo_sub.add_parser(
        "report", help="render status + evidence + blockers (never a score/dashboard)"
    )
    demo_report.add_argument("--repo", default=".", help="repo root")
    demo_report.add_argument(
        "--format",
        choices=["text", "json", "html"],
        default="text",
        help="output format",
    )
    demo_report.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help=(
            "HTML output under .seshat-output/ "
            "(default: .seshat-output/demo/index.html)"
        ),
    )


def _add_mcp_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "mcp",
        help="run the optional read-only Seshat agent governor over local stdio",
    )
    p.add_argument(
        "--repo",
        default=".",
        help="single local repository root exposed to governor reads",
    )


def _add_generate_parser(sub: argparse._SubParsersAction) -> None:
    """DAX generator (Task 7). Lazy imports inside _run_generate keep dax_gen/yaml
    out of the `retail check` import chain (mirrors the validate / semantic-check
    handlers). --out is fail-closed: refuses powerbi/ writes and overwrites."""
    gen = sub.add_parser(
        "generate",
        help="generate a verified best-practice DAX measure from a metric contract",
    )
    gen.add_argument(
        "--contract",
        required=True,
        metavar="PATH",
        help="metric contract YAML (reads its `definition` block)",
    )
    gen.add_argument(
        "--out",
        default=None,
        metavar="PATH",
        help=(
            "write the verified TMDL block to a NEW standalone file "
            "(never under powerbi/; refuses to overwrite)"
        ),
    )
    gen.add_argument(
        "--format",
        dest="fmt",
        choices=("tmdl", "json"),
        default="tmdl",
        help="output format on success (tmdl or json)",
    )


def _add_theme_gen_parser(sub: argparse._SubParsersAction) -> None:
    """Theme generator (Slice 1, DEFINE-only). Assembles a caller-supplied palette
    into a gated surface-3 theme artifact set (tokens + theme JSON + spec).
    stdlib-only; self-checks CT1 before writing; readiness = warning (no self-
    pass). Writes NO PBIR / visual.json; no pbi-cli; adds NO new `retail check`
    rule (the emitted files are covered by DL1/DL3/CT1)."""
    themegen = sub.add_parser(
        "theme-gen",
        help="generate a gated Power BI theme (tokens + theme JSON + spec)",
    )
    themegen.add_argument("--name", required=True, help="theme/file basename slug")
    themegen.add_argument(
        "--mode", choices=("light", "dark"), required=True, help="light or dark"
    )
    themegen.add_argument("--accent", required=True, metavar="#RRGGBB")
    themegen.add_argument("--background", required=True, metavar="#RRGGBB")
    themegen.add_argument(
        "--text-primary", dest="text_primary", required=True, metavar="#RRGGBB"
    )
    themegen.add_argument(
        "--text-secondary", dest="text_secondary", default=None, metavar="#RRGGBB"
    )
    themegen.add_argument(
        "--text-muted", dest="text_muted", default=None, metavar="#RRGGBB"
    )
    themegen.add_argument(
        "--data-colors",
        dest="data_colors",
        default=None,
        metavar="#a,#b,...",
        help="comma-separated ramp; derived from accent if omitted",
    )
    themegen.add_argument("--good", default=None, metavar="#RRGGBB")
    themegen.add_argument("--neutral", default=None, metavar="#RRGGBB")
    themegen.add_argument("--bad", default=None, metavar="#RRGGBB")
    _add_theme_gen_output_args(themegen)


def _add_theme_gen_output_args(themegen: argparse.ArgumentParser) -> None:
    """The `theme-gen` tail: font-size floors, write target (--repo/--force),
    dark-mode pairing, and the opt-in overlay role. Split verbatim off
    ``_add_theme_gen_parser`` (add-order preserved) to keep that helper under the
    CodeScene 70-line Large-Method threshold; no flag/help text changes."""
    themegen.add_argument(
        "--title-font-pt",
        dest="title_font_pt",
        type=float,
        default=None,
        metavar="PT",
        help="title font size in points (default 12.0; floor enforced, not settable)",
    )
    themegen.add_argument(
        "--label-font-pt",
        dest="label_font_pt",
        type=float,
        default=None,
        metavar="PT",
        help="label font size in points (default 9.0; floor enforced, not settable)",
    )
    themegen.add_argument("--repo", default=".", help="repo root to write into")
    themegen.add_argument(
        "--force", action="store_true", help="overwrite existing files"
    )
    themegen.add_argument(
        "--pair",
        action="store_true",
        help="also derive and write a dark-mode pair from a light --mode seed",
    )
    themegen.add_argument(
        "--overlay-fg",
        dest="overlay_fg",
        default=None,
        metavar="#RRGGBB",
        help="opt-in overlay-role foreground; composited over background and "
        "AA-gated (needs --overlay-transparency-pct)",
    )
    themegen.add_argument(
        "--overlay-transparency-pct",
        dest="overlay_transparency_pct",
        type=float,
        default=None,
        metavar="PCT",
        help="overlay opacity in [0,100]; 0 = opaque (needs --overlay-fg)",
    )


def _add_theme_compile_parser(sub: argparse._SubParsersAction) -> None:
    """Tokens -> theme compile (deterministic; reuses theme-gen's renderer). Reads a
    committed design-tokens YAML and writes its matching theme.json. Repairs
    DL3-governed drift but refuses to overwrite hand-tuned DL3-deferred fields."""
    themecompile = sub.add_parser(
        "theme-compile",
        help="compile a committed design-tokens YAML into its theme.json",
    )
    themecompile.add_argument(
        "--tokens",
        required=True,
        metavar="PATH",
        help="the *-design-tokens.yaml file to compile",
    )
    themecompile.add_argument(
        "--out",
        default=None,
        metavar="PATH",
        help="theme.json output path (default: the tokens' meta.compiles_to)",
    )
    themecompile.add_argument(
        "--force", action="store_true", help="overwrite an existing theme.json"
    )


def _add_pbir_apply_theme_parser(sub: argparse._SubParsersAction) -> None:
    """PBIR theme-application (adapter increment A). Applies a theme-gen theme to a
    committed PBIR report (BaseTheme resource + report.json themeCollection).
    Companion authoring adapter (ADR 0015): writes committed PBIR, allow-list-only,
    deterministic + validated; NO pbi-cli / live Power BI / external dependency."""
    pbirtheme = sub.add_parser(
        "pbir-apply-theme",
        help="apply a generated theme to a committed PBIR report (adapter)",
    )
    pbirtheme.add_argument(
        "--theme", required=True, metavar="PATH", help="the theme JSON to apply"
    )
    pbirtheme.add_argument(
        "--report",
        required=True,
        metavar="DIR",
        help="the *.Report/ dir to apply the theme to",
    )
    pbirtheme.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing different base theme",
    )


def _add_pbir_format_visual_parser(sub: argparse._SubParsersAction) -> None:
    """PBIR per-visual formatting (adapter increment B). Sets allow-listed formatting
    (objects / visualContainerObjects) on an existing data-bound visual.json; the
    data binding (query/visualType) is preserved byte-for-byte (FR-003). Same
    adapter boundary as increment A: local files only, no external dependency."""
    pbirfmt = sub.add_parser(
        "pbir-format-visual",
        help="apply allow-listed formatting to an existing PBIR visual (adapter)",
    )
    pbirfmt.add_argument(
        "--visual", required=True, metavar="PATH", help="the visual.json to format"
    )
    pbirfmt.add_argument(
        "--formatting",
        required=True,
        metavar="JSON_OR_PATH",
        help=(
            "formatting as a JSON string or a path to a JSON file: "
            '{"visualContainerObjects": {"title": {"text": "Sales"}}}'
        ),
    )
    pbirfmt.add_argument(
        "--force",
        action="store_true",
        help="overwrite a formatting property already set to a different value",
    )


def _add_pbir_page_background_parser(sub: argparse._SubParsersAction) -> None:
    """PBIR page background (adapter increment C). Sets a page's canvas background to a
    committed surface-2 image asset: copies the asset into RegisteredResources,
    registers it in report.json, references it from page.json objects.background via
    a ResourcePackageItem. Allow-list-only (touches only objects.background + the
    RegisteredResources package); no external dependency; surface-2 purity."""
    pbirbg = sub.add_parser(
        "pbir-set-page-background",
        help="set a PBIR page's canvas background to a surface-2 image asset (adapter)",
    )
    pbirbg.add_argument(
        "--asset", required=True, metavar="PATH", help="the image asset to use"
    )
    pbirbg.add_argument(
        "--report", required=True, metavar="DIR", help="the *.Report/ dir"
    )
    pbirbg.add_argument(
        "--page", required=True, metavar="PAGE_NAME", help="the page folder name"
    )
    pbirbg.add_argument(
        "--scaling",
        choices=("Fit", "Fill", "Normal"),
        default="Fit",
        help="image scaling (default Fit)",
    )
    pbirbg.add_argument(
        "--force", action="store_true", help="replace an existing page background"
    )


def _add_pbir_geometry_parser(sub: argparse._SubParsersAction) -> None:
    """PBIR visual geometry (adapter increment D). Sets a visual's position rectangle
    (x/y/width/height/z/tabOrder), preserving its data binding (FR-003) and refusing
    off-canvas rectangles read from the real page.json canvas. NEVER visualType /
    creation / unbound moves (ADR 0016). Allow-list-only; no external dependency."""
    pbirgeom = sub.add_parser(
        "pbir-set-geometry",
        help="set a PBIR visual's position rectangle (adapter increment D)",
    )
    pbirgeom.add_argument(
        "--visual", required=True, metavar="PATH", help="the visual.json to lay out"
    )
    pbirgeom.add_argument(
        "--position",
        required=True,
        metavar="JSON_OR_PATH",
        help=(
            "position as a JSON string or path: "
            '{"x": 100, "y": 80, "width": 400, "height": 300}'
        ),
    )


def _add_pbir_validate_blueprint_parser(sub: argparse._SubParsersAction) -> None:
    """PBIR-vs-approved-design validator (US8, spec 123). Extends the shipped
    Visual Implementation Review (FR-031) -- the ONE new read-only CLI verb this
    slice adds, justified by the same check-surface precedent as R1/R2 (rules/
    pbir.py): it POLICES what a writer (the US7 compiler OR a human Desktop
    build) already produced, distinct from an authoring skill. Opens nothing for
    write; reports expected-vs-actual and exits non-zero on any deviation,
    unapproved addition, or missing element. Grants NO approval -- never sets
    `dashboard_ready: pass` (FR-031/FR-036)."""
    pbirvalidate = sub.add_parser(
        "pbir-validate-blueprint",
        help=(
            "validate committed PBIR against the approved page blueprint + "
            "binding map (read-only; grants no approval)"
        ),
    )
    pbirvalidate.add_argument(
        "--report", required=True, metavar="DIR", help="the *.Report/ dir to validate"
    )
    pbirvalidate.add_argument(
        "--blueprint",
        required=True,
        metavar="PATH",
        help="the approved page-blueprint YAML (filled dashboard-page-blueprint.yaml)",
    )
    pbirvalidate.add_argument(
        "--binding-map",
        required=True,
        metavar="PATH",
        help="the approved visual-contract-binding-map.md",
    )


def _add_manifest_parser(sub: argparse._SubParsersAction) -> None:
    """Rule-registry snapshot manifest (feature 043). Writes the golden inventory
    docs/rules/rules-manifest.json from the live registry. Test-only consumer
    (the snapshot test); adds NO new `retail check` rule."""
    manifest = sub.add_parser(
        "manifest",
        help="regenerate docs/rules/rules-manifest.json from the live rule registry",
    )
    manifest.add_argument(
        "--repo", default=".", help="repo root to write the manifest into"
    )


def _add_severity_posture_parser(sub: argparse._SubParsersAction) -> None:
    """Severity-posture golden record (feature 044). Writes the observed severity
    posture of every registered rule + the L3 surface to
    docs/rules/severity-posture.json. Test-only consumer (the snapshot test);
    adds NO new `retail check` rule and NO new EXPECTED_RULE_ID."""
    severity_posture = sub.add_parser(
        "severity-posture",
        help=(
            "regenerate docs/rules/severity-posture.json from the live rule "
            "registry + L3 surface (observed, not read)"
        ),
    )
    severity_posture.add_argument(
        "--repo", default=".", help="repo root to write the record into"
    )


def _add_scaffold_parser(sub: argparse._SubParsersAction) -> None:
    """Scaffold-rule authoring helper + doctor (feature 062). Static, stdlib-only.
    Author mode WRITES exactly three targets (stub module, failing test stub,
    EXPECTED_RULE_IDS insertion) and PRINTS the golden-regen commands + a
    suggested glossary row; doctor mode READS the five wiring places and reports
    drift. Adds NO new `retail check` rule (it is tooling)."""
    scaffold_p = sub.add_parser(
        "scaffold",
        help=(
            "author a new rule's boilerplate (write/print split) or --doctor "
            "the five wiring places for drift"
        ),
    )
    scaffold_p.add_argument("--repo", default=".", help="repo root to author/verify")
    scaffold_p.add_argument(
        "--doctor",
        action="store_true",
        help="verify mode (read-only): report wiring drift across the five places",
    )
    scaffold_p.add_argument(
        "--id",
        dest="rule_id",
        default=None,
        metavar="RULE_ID",
        help="the rule id (author mode requires it; doctor mode: verify one id)",
    )
    scaffold_p.add_argument(
        "--title",
        default=None,
        metavar="TITLE",
        help="the one-line rule title (author mode)",
    )


def _add_init_parser(sub: argparse._SubParsersAction) -> None:
    """`init` (feature 070): SUBSTRATE-WRITING ONLY. Writes the compass projection +
    manifests + the fenced SESHAT-KIT regions of AGENTS.md/CLAUDE.md, then PRINTS
    the next agent step. It NEVER prompts, shows a menu, or emits a profile -- the
    delegate/route/profile flow is the agent performing the `retail-init` skill."""
    init_p = sub.add_parser(
        "init",
        help=(
            "bootstrap the Compass-Driven kit substrate (writes .seshat/ + fenced "
            "AGENTS.md/CLAUDE.md regions) and print the next agent step -- no wizard"
        ),
    )
    init_p.add_argument("--repo", default=".", help="repo root to bootstrap")


def _add_kit_lint_parser(sub: argparse._SubParsersAction) -> None:
    """`kit-lint` (feature 072): standalone Maintenance-Automation step (NOT a `retail
    check` rule -- it parses yaml). Fails loud (exit 1) when a compass PROJECTION
    drifts from the canonical kit source. Read-only; reads no constitution."""
    kit_lint_p = sub.add_parser(
        "kit-lint",
        help=(
            "fail loud if a compass projection (.seshat/compass.yaml or the fenced "
            "AGENTS.md/CLAUDE.md regions) drifts from .seshat/kit-source.yaml"
        ),
    )
    kit_lint_p.add_argument("--repo", default=".", help="repo root to lint")


def _add_doctor_parser(sub: argparse._SubParsersAction) -> None:
    """`doctor`: read-only repo-wide drift digest. Extracted (mirrors the other
    `_add_*_parser` helpers) to keep `_build_parser` from growing (CodeScene
    large-method guard)."""
    doctor_p = sub.add_parser(
        "doctor",
        help=(
            "read-only repo-wide drift digest (aggregates A1/A3/SC1 + a "
            "load-bearing-doc probe); advisory by default, --strict to fail on findings"
        ),
    )
    doctor_p.add_argument("--repo", default=".", help="repo root to diagnose")
    doctor_p.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero if any finding is present (default: advisory, exit 0)",
    )


def _add_dagster_parser(sub: argparse._SubParsersAction) -> None:
    """`dagster`: the orchestration-adapter family (spec 134). Three verbs,
    closed argument set; exit codes 0..4 per the committed CLI contract."""
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


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Exposed (not inlined in ``main``) so flag->field mapping is unit-testable
    without executing any rules. The two commit-aware flags live UNDER the
    ``check`` subcommand alongside ``--repo``.
    """
    parser = argparse.ArgumentParser(
        prog="retail",
        description="Static governance checks for committed Power BI artifacts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _add_check_parser(sub)
    _add_validate_parser(sub)
    _add_drift_parser(sub)
    _add_semantic_and_value_check_parsers(sub)
    _add_generate_parser(sub)
    _add_theme_gen_parser(sub)
    _add_theme_compile_parser(sub)
    _add_pbir_apply_theme_parser(sub)
    _add_pbir_format_visual_parser(sub)
    _add_pbir_page_background_parser(sub)
    _add_pbir_geometry_parser(sub)
    _add_pbir_validate_blueprint_parser(sub)
    _add_manifest_parser(sub)
    _add_severity_posture_parser(sub)
    _add_scaffold_parser(sub)
    _add_init_parser(sub)
    _add_init_project_parser(sub)
    _add_adopt_pbip_parser(sub)
    _add_dbt_parser(sub)
    _add_status_parser(sub)
    _add_next_parser(sub)
    _add_approvals_parser(sub)
    _add_evidence_pack_parser(sub)
    _add_blockers_parser(sub)
    _add_pii_notice_parser(sub)
    _add_approver_view_parser(sub)
    _add_dashboard_planner_parser(sub)
    _add_gap_detector_parser(sub)
    _add_kit_lint_parser(sub)
    _add_doctor_parser(sub)
    _add_demo_parser(sub)
    _add_passport_parser(sub)
    _add_pack_parser(sub)
    _add_benchmark_parser(sub)
    _add_explorer_parser(sub)
    _add_impact_map_parser(sub)
    _add_agent_parser(sub)
    _add_watch_parser(sub)
    _add_dagster_parser(sub)
    _add_mcp_parser(sub)

    return parser
