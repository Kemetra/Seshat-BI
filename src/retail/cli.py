from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import retail.rules  # noqa: F401  (import for side effects: fires every @register)

from .registry import all_rules
from .runner import build_context, run, run_json

if TYPE_CHECKING:
    # Type-only imports: kept behind TYPE_CHECKING so the driver-free / lazy-import
    # discipline of the runtime handlers is preserved (these modules are imported
    # lazily inside the handlers, never at module scope).
    from .validate import QueryRunner
    from .validate_targets import ValidationTargets


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
        choices=("text", "json"),
        default="text",
        help=(
            "findings output format. 'text' (default) is the human-readable "
            "[severity] id message (locator) lines, unchanged. 'json' emits one "
            "structured document for tooling; the exit code is identical."
        ),
    )

    # LIVE validators (feature 004). Needs a running DB + the optional `db` extra
    # (psycopg2). The driver is imported LAZILY in _run_validate, never here, so
    # `retail check` and CI (no driver installed) never import it.
    # Connection is host-agnostic: ANY Postgres (local / remote / DigitalOcean /
    # other) via a DSN -- from --dsn, or DATABASE_URL, or the ANALYTICS_DB_* parts.
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

    # L3 semantic / contract<->DAX drift gate (feature: DAX fortification Phase 1).
    # Parses metric-contract YAML (lazy yaml inside the handler) -- NOT in the
    # stdlib-only `retail check` core chain.
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

    # L4 value proxy (DAX fortification #4). Recomputes each metric contract's
    # `definition.expected_value` against the live gold table and asserts it still
    # equals the approved number, within tolerance. Lazy psycopg2 inside the handler
    # (reusing the validate path), so the stdlib-only `retail check` chain never
    # imports a driver. Live-deferred by repo YAGNI: needs a DSN + the `db` extra.
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

    # DAX generator (Task 7). Lazy imports inside _run_generate keep dax_gen/yaml
    # out of the `retail check` import chain (mirrors the validate / semantic-check
    # handlers). --out is fail-closed: refuses powerbi/ writes and overwrites.
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

    # Theme generator (Slice 1, DEFINE-only). Assembles a caller-supplied palette
    # into a gated surface-3 theme artifact set (tokens + theme JSON + spec).
    # stdlib-only; self-checks CT1 before writing; readiness = warning (no self-
    # pass). Writes NO PBIR / visual.json; no pbi-cli; adds NO new `retail check`
    # rule (the emitted files are covered by DL1/DL3/CT1).
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
    themegen.add_argument("--repo", default=".", help="repo root to write into")
    themegen.add_argument(
        "--force", action="store_true", help="overwrite existing files"
    )

    # Rule-registry snapshot manifest (feature 043). Writes the golden inventory
    # docs/rules/rules-manifest.json from the live registry. Test-only consumer
    # (the snapshot test); adds NO new `retail check` rule.
    manifest = sub.add_parser(
        "manifest",
        help="regenerate docs/rules/rules-manifest.json from the live rule registry",
    )
    manifest.add_argument(
        "--repo", default=".", help="repo root to write the manifest into"
    )

    # Severity-posture golden record (feature 044). Writes the observed severity
    # posture of every registered rule + the L3 surface to
    # docs/rules/severity-posture.json. Test-only consumer (the snapshot test);
    # adds NO new `retail check` rule and NO new EXPECTED_RULE_ID.
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

    # Scaffold-rule authoring helper + doctor (feature 062). Static, stdlib-only.
    # Author mode WRITES exactly three targets (stub module, failing test stub,
    # EXPECTED_RULE_IDS insertion) and PRINTS the golden-regen commands + a
    # suggested glossary row; doctor mode READS the five wiring places and reports
    # drift. Adds NO new `retail check` rule (it is tooling).
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

    # `init` (feature 070): SUBSTRATE-WRITING ONLY. Writes the compass projection +
    # manifests + the fenced SESHAT-KIT regions of AGENTS.md/CLAUDE.md, then PRINTS
    # the next agent step. It NEVER prompts, shows a menu, or emits a profile -- the
    # delegate/route/profile flow is the agent performing the `retail-init` skill.
    init_p = sub.add_parser(
        "init",
        help=(
            "bootstrap the Compass-Driven kit substrate (writes .seshat/ + fenced "
            "AGENTS.md/CLAUDE.md regions) and print the next agent step -- no wizard"
        ),
    )
    init_p.add_argument("--repo", default=".", help="repo root to bootstrap")

    # `kit-lint` (feature 072): standalone Maintenance-Automation step (NOT a `retail
    # check` rule -- it parses yaml). Fails loud (exit 1) when a compass PROJECTION
    # drifts from the canonical kit source. Read-only; reads no constitution.
    kit_lint_p = sub.add_parser(
        "kit-lint",
        help=(
            "fail loud if a compass projection (.seshat/compass.yaml or the fenced "
            "AGENTS.md/CLAUDE.md regions) drifts from .seshat/kit-source.yaml"
        ),
    )
    kit_lint_p.add_argument("--repo", default=".", help="repo root to lint")

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

    # `demo` verb group (spec 083): prove the readiness spine on a generic sample.
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
        "--format", choices=["text", "json"], default="text", help="output format"
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as exc:
        # argparse exits 2 on bad/missing args (e.g. no subcommand); surface it
        # as a return code rather than letting it propagate.
        return int(exc.code or 0)

    if args.command == "check":
        commit_message: str | None = None
        if args.commit_msg_file is not None:
            try:
                raw = Path(args.commit_msg_file).read_text(encoding="utf-8")
            except FileNotFoundError:
                print(
                    f"error: commit message file not found: {args.commit_msg_file}",
                    file=sys.stderr,
                )
                return 1  # main() is -> int; the __main__ guard does sys.exit(main())
            # git's COMMIT_EDITMSG ends in a trailing newline (\r\n on Windows) —
            # strip it so the message passed to rules is the bare text.
            commit_message = raw.rstrip("\r\n")

        ctx = build_context(
            Path(args.repo),
            commit_range=args.commit_range,
            commit_message=commit_message,
        )
        # Spec A drop-in fitness: in a repo the kit was merely downloaded into
        # (not bootstrapped), KIT_SELF rules SKIP (INFO) instead of ERROR-ing on
        # internal manifests that repo can't have. The kit's own repo IS
        # bootstrapped, so nothing skips there -- behavior is unchanged.
        from .kit_lint import is_bootstrapped

        bootstrapped = is_bootstrapped(Path(args.repo))
        # Default 'text' calls the unchanged run(); 'json' is the opt-in path.
        if args.output_format == "json":
            return run_json(all_rules(), ctx, bootstrapped=bootstrapped)
        return run(all_rules(), ctx, bootstrapped=bootstrapped)

    if args.command == "validate":
        return _run_validate(args)

    if args.command == "semantic-check":
        return _run_semantic_check(args)

    if args.command == "value-check":
        return _run_value_check(args)

    if args.command == "generate":
        return _run_generate(args)

    if args.command == "theme-gen":
        from .theme_gen import theme_gen_main

        return theme_gen_main(args)

    if args.command == "manifest":
        return _run_manifest(args)

    if args.command == "severity-posture":
        return _run_severity_posture(args)

    if args.command == "scaffold":
        return _run_scaffold(args)

    if args.command == "init":
        return _run_init(args)

    if args.command == "kit-lint":
        return _run_kit_lint(args)

    if args.command == "doctor":
        from .doctor import run_doctor

        return run_doctor(Path(args.repo), strict=args.strict)

    if args.command == "demo":
        from .demo import run_demo

        return run_demo(args)

    return 0


def _run_manifest(args: argparse.Namespace) -> int:
    """Regenerate the rule-registry snapshot manifest from the live registry."""
    from .manifest import MANIFEST_REL_PATH, write_manifest

    write_manifest(args.repo)
    print(f"wrote {MANIFEST_REL_PATH} from the live rule registry")
    return 0


def _run_severity_posture(args: argparse.Namespace) -> int:
    """Regenerate the severity-posture golden record from live observation."""
    from .severity_posture import RECORD_REL_PATH, write

    write(args.repo)
    print(f"wrote {RECORD_REL_PATH} from the live rule registry + L3 surface")
    return 0


def _run_scaffold(args: argparse.Namespace) -> int:
    """Author a new rule's boilerplate, or --doctor the five wiring places.

    Author mode (default when --id + --title are given): writes exactly three
    targets and prints the golden-regen commands + a suggested glossary row +
    the import/__all__ edit. Exit 0 on write, non-zero on refusal.

    Doctor mode (--doctor): read-only; reports per-id per-place presence and
    exits non-zero on any drift (FR-014). An unknown --id is reported, not a
    crash-exit.

    The scaffold module is imported LAZILY here (stdlib-only, but kept off the
    module-scope import chain to mirror the other subcommand handlers).
    """
    from . import scaffold as scaffold_mod

    repo = args.repo

    if args.doctor:
        report = scaffold_mod.doctor(repo, args.rule_id)
        for entry in report.entries:
            states = ", ".join(
                f"{p.key}={entry.places[p.key]}" for p in scaffold_mod.FIVE_PLACES
            )
            drift = "DRIFT" if entry.has_drift else "ok"
            print(f"[{drift}] {entry.id}: {states}")
        if not report.entries:
            print(
                "scaffold --doctor: no registered rule ids to verify", file=sys.stderr
            )
        return 1 if report.has_drift else 0

    # Author mode: id + title are required.
    if not args.rule_id or not args.title:
        print(
            "error: author mode needs --id and --title (or pass --doctor to verify).",
            file=sys.stderr,
        )
        return 2
    result = scaffold_mod.scaffold(repo, args.rule_id, args.title)
    if not result.ok:
        print(f"[refused] {result.refused}", file=sys.stderr)
        return 1
    for w in result.written:
        print(f"wrote {w}")
    print("\nnext steps (run/apply by hand -- not written by scaffold):")
    for line in result.printed:
        print(f"  {line}")
    return 0


def _run_init(args: argparse.Namespace) -> int:
    """Bootstrap the kit substrate (feature 070). SUBSTRATE-WRITING ONLY.

    Writes the compass projection + manifests + the fenced SESHAT-KIT regions, then
    PRINTS the next agent step. Never prompts, never shows a menu, never profiles --
    the delegate/route/profile flow is the agent performing the `retail-init` skill.
    The module is imported LAZILY (it pulls in the pyyaml-using compass_project),
    mirroring the other subcommand handlers and keeping the check path yaml-free.
    """
    from . import kit_init

    try:
        result = kit_init.bootstrap(args.repo)
    except RuntimeError as exc:
        # A malformed fence is a hard stop -- report, do not force a rewrite.
        print(f"[stopped] {exc}", file=sys.stderr)
        return 1

    if result.already_bootstrapped:
        print("already bootstrapped -- re-projected the SESHAT-KIT regions.")
        # Fold (074): on a re-run, show WHAT the re-projection moved (e.g. after a
        # package upgrade), not just "already bootstrapped".
        if result.changed_targets:
            print("changed targets:")
            for t in result.changed_targets:
                print(f"    {t}")
        else:
            print("no targets changed (already in sync).")
    for w in result.written:
        print(f"wrote {w}")
    for name in result.fenced:
        print(f"projected SESHAT-KIT fence in {name}")
    print(f"\n{result.next_step}")
    return 0


def _run_kit_lint(args: argparse.Namespace) -> int:
    """Fail loud on compass projection drift (feature 072). Read-only.

    Standalone step, NOT a `retail check` rule -- imported LAZILY (it pulls in the
    pyyaml-using compass_project), mirroring `_run_semantic_check` / `_run_init` and
    keeping the check path yaml-free. Exit 0 clean (or not-bootstrapped), 1 on drift.
    """
    from . import kit_lint

    report = kit_lint.lint(args.repo)

    if not report.bootstrapped:
        print("kit-lint: not bootstrapped -- run `retail init` (nothing to lint).")
        return 0

    for r in report.results:
        status = "ok" if r.ok else "DRIFT"
        print(f"[{status}] {r.name}")
        for d in r.details:
            print(f"    {d}")
    if report.ok:
        print("kit-lint: no projection drift.")
    return 0 if report.ok else 1


def _safe_target_label(engine: str, config: object) -> str:
    """A credential-free label for the "running against ..." status line.

    A Postgres DSN string keeps only the host segment (matches the
    pre-existing behavior, unchanged). Every OTHER string-shaped config --
    today that's only the SQL-Server ODBC keyword string, which embeds
    PWD=/UID= directly with no "@" delimiter to split on -- is NOT safe to
    echo even partially, so it falls through to the engine-only label (same
    posture as the kwargs-dict engines, MySQL/Snowflake): no field of a
    non-Postgres config is guaranteed secret-free enough to print.
    """
    if engine == "postgres" and isinstance(config, str):
        return config.split("@")[-1] if "@" in config else config
    return engine


def _current_engine() -> str:
    """Read ANALYTICS_DB_ENGINE from the environment (default: postgres).

    Indirected (not inlined at call sites) so tests can monkeypatch a single
    seam. Reading the env HERE (not at call sites) keeps _ensure_driver() and
    _make_runner(dsn) at their existing zero-/one-arg signatures, which the
    test suite already monkeypatches directly (test_cli_context.py).
    """
    import os

    return os.environ.get("ANALYTICS_DB_ENGINE") or "postgres"


def _ensure_driver() -> bool:
    """True if the current engine's optional DB driver is importable. LAZY: the
    import lives here, never at module scope, so `retail check` / CI (no driver)
    never load it. Postgres path is UNCHANGED (identical import + behavior)."""
    engine = _current_engine()
    try:
        if engine == "postgres":
            import psycopg2  # noqa: F401  (lazy: only when validate actually connects)
        elif engine == "sqlserver":
            import pyodbc  # noqa: F401
        elif engine == "mysql":
            import mysql.connector  # noqa: F401
        elif engine == "snowflake":
            import snowflake.connector  # noqa: F401
        else:
            return False
    except ImportError:
        return False
    return True


def _make_runner(dsn: str) -> QueryRunner:
    """Build a real (lazy driver) QueryRunner for the current engine.

    Indirected through cli so tests can monkeypatch it with a fake -- no real
    DB is touched in the suite. The ``dsn`` parameter carries whatever
    ``resolve_config`` produced for the active engine (a DSN string for
    Postgres/SQL-Server's ODBC string, a kwargs dict for MySQL/Snowflake); the
    name is kept for Postgres call-site/monkeypatch compatibility.
    """
    from .dialect import get_dialect

    return get_dialect(_current_engine()).connect(dsn)


def _load_targets(source_map: str) -> ValidationTargets:
    """Load per-table validate targets from a source-map.yaml. Indirected (and
    lazy-importing the YAML loader) so the driver-free import path is preserved
    and tests can monkeypatch it."""
    from .validate_targets import load_targets

    return load_targets(source_map)


def _redact_dsn(message: object, dsn: str) -> str:
    """Scrub a DSN and its sensitive COMPONENTS out of an error message.

    A literal replace is not enough: psycopg2 reformats the DSN into its own text
    (e.g. ``connection to server at "host" (1.2.3.4), port 5432 failed: FATAL:
    password authentication failed for user "admin"``) where the literal DSN never
    appears yet host/user/password leak. So, in addition to the literal DSN, parse
    the DSN and redact each non-empty component (host, username, password, and the
    ``user@`` credentials prefix) wherever it appears (audit 2026-06-26 #7).
    """
    from urllib.parse import urlsplit

    text = str(message) or message.__class__.__name__
    if not dsn:
        return text
    text = text.replace(dsn, "<redacted DSN>")
    if "@" in dsn:
        text = text.replace(dsn.split("@", 1)[0] + "@", "<credentials>@")
    # Component-level scrub for the reformatted-by-the-driver case.
    try:
        parts = urlsplit(dsn)
    except ValueError:
        return text
    # Longest first so a host containing the username substring is fully covered.
    for secret in sorted(
        {parts.password, parts.username, parts.hostname},
        key=lambda s: len(s or ""),
        reverse=True,
    ):
        if secret:
            text = text.replace(secret, "<redacted>")
    return text


def _run_validate(args: argparse.Namespace) -> int:
    """Run the LIVE validators against a real DB.

    The DB driver import is LAZY (via ``_ensure_driver`` / ``_make_runner``,
    never at module scope) so that `retail check` and CI -- which install no
    DB driver -- never import it. If the driver or a usable connection is
    missing, exit non-zero with an actionable message, never a raw traceback.

    Engine selection: ``ANALYTICS_DB_ENGINE`` (default ``postgres``) picks the
    Dialect. The POSTGRES PATH IS UNCHANGED -- it keeps using --dsn/DATABASE_URL/
    resolve_dsn verbatim, so engine unset (or "postgres") behaves identically to
    before this feature. Other engines resolve their config from the
    Dialect.resolve_config(env) seam (an ODBC string for SQL Server, a kwargs
    dict for MySQL/Snowflake) and do not support --dsn (a Postgres-only flag).

    Two modes:
      * ``--source-map PATH`` given -> load that table's targets, connect, run the
        four live checks, print findings, return 1 iff any ERROR (the live run).
      * no ``--source-map`` -> report the deferred state (the surface is built and
        fixture-tested; a live run needs a table's targets). Returns 1.
    """
    import os

    from .core import Severity
    from .dialect import get_dialect
    from .runner import _format  # reuse the [severity] id message (locator) format
    from .validate import resolve_dsn, run_live_checks

    engine = _current_engine()
    dialect = get_dialect(engine)

    # 1. Resolve the engine's config. Postgres: --dsn wins; else env (UNCHANGED
    #    behavior). Other engines: --dsn is not applicable; resolve from env only.
    if engine == "postgres":
        env = dict(os.environ)
        if args.dsn:
            env = {**env, "DATABASE_URL": args.dsn}
        config = resolve_dsn(env)
    else:
        config = dialect.resolve_config(dict(os.environ))
    if config is None:
        print(
            "error: no database connection configured.\n"
            "       pass --dsn (a postgresql:// connection string), or set\n"
            "       DATABASE_URL, or the ANALYTICS_DB_* vars (in your gitignored\n"
            "       .env). Never commit a real DSN.",
            file=sys.stderr,
        )
        return 1

    # 2. The DB driver is optional + lazy: only needed for a real run.
    if not _ensure_driver():
        print(
            "error: `retail validate` needs the optional DB driver.\n"
            "       install it with:  pip install 'retail[db]'\n"
            "       (the static `retail check` core stays dependency-free).",
            file=sys.stderr,
        )
        return 1

    safe_host = _safe_target_label(engine, config)

    # 3a. Deferred mode: no table targets supplied -> report, do not connect.
    if not args.source_map:
        print(
            "retail validate: the live-validator surface is built and fixture-tested. "
            "Pass --source-map <mappings/<table>/source-map.yaml> to run the four live "
            "checks against that table; the standalone live run is otherwise the "
            "deferred follow-up.\n"
            f"resolved target (credentials hidden): {safe_host}\n"
            "See specs/004-retail-validate/spec.md (FR-009).",
            file=sys.stderr,
        )
        return 1

    # 3b. Live mode: load targets, connect, run the four checks, print findings.
    try:
        targets = _load_targets(args.source_map)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"error: could not load source-map: {exc}", file=sys.stderr)
        return 1

    print(f"retail validate: running live checks against {safe_host}", file=sys.stderr)
    try:
        runner = _make_runner(config)
        findings = run_live_checks(runner, targets, dialect=dialect)
    except Exception as exc:
        print(
            "error: live validation failed at the DB boundary "
            f"({exc.__class__.__name__}): {dialect.redact(exc, config)}",
            file=sys.stderr,
        )
        print(
            "       verify the DSN, network access, database objects, and the "
            "optional DB driver: pip install 'retail[db]'",
            file=sys.stderr,
        )
        return 1

    for finding in findings:
        print(_format(finding))
    if any(f.severity is Severity.ERROR for f in findings):
        return 1
    print("retail validate: all live checks passed (0 findings).", file=sys.stderr)
    return 0


def _run_semantic_check(args: argparse.Namespace) -> int:
    """Run the L3 contract<->DAX drift gate.

    Lazy imports (yaml via load_definition, plus semantic + metric_drift, plus the
    TMDL parser) live INSIDE this handler so the stdlib-only `retail check` import
    chain never pulls them. Pairs each committed measure (parsed from the model
    TMDL) with its contract definition (mappings/<dataset>/metrics/<name>.yaml) and
    reports drift (ERROR) / escalate (WARNING). Returns 1 iff any drift.

    Scans the model TMDL directly from the filesystem (not git ls-files): the
    semantic-check surface is not a registered rule, so it reads the repo tree
    directly -- which also makes it runnable in a non-git directory.
    """
    from .metric_drift import load_definition
    from .runner import _format
    from .semantic import MeasurePair, run_semantic_pairs
    from .tmdl import parse_tmdl

    repo = Path(args.repo)

    # Confine --metrics-dir to the repo tree: resolve it and reject a value that
    # traverses outside the repo root (e.g. `../../etc`) so contract discovery
    # cannot be pointed at arbitrary filesystem locations (audit 2026-06-26 #26).
    repo_resolved = repo.resolve()
    metrics_root = (repo / args.metrics_dir).resolve()
    if metrics_root != repo_resolved and not metrics_root.is_relative_to(repo_resolved):
        print(
            f"error: --metrics-dir {args.metrics_dir!r} escapes the repo root; "
            "it must resolve to a path inside --repo.",
            file=sys.stderr,
        )
        return 1

    # 1. Index contract definitions by measure name (YAML stem == measure name).
    definitions: dict[str, dict | None] = {}
    if metrics_root.is_dir():
        for contract_path in sorted(metrics_root.glob("*/metrics/*.yaml")):
            name = contract_path.stem
            try:
                definitions[name] = load_definition(str(contract_path))
            except (OSError, ValueError) as exc:
                print(
                    f"error: could not load contract {contract_path}: {exc}",
                    file=sys.stderr,
                )
                return 1

    # 2. Pair each committed measure with its contract definition (if any).
    # Scan *.SemanticModel/definition/**/*.tmdl, skipping any tests/ fixtures.
    # The recursive ``**`` glob matches zero-or-more intermediate dirs, so it
    # covers both top-level (definition/foo.tmdl) and nested (definition/tables/
    # foo.tmdl) files in one pass -- no separate top-level glob (which would
    # double-count) is needed.
    pairs: list[MeasurePair] = []
    for tmdl_path in sorted(repo.rglob("*.SemanticModel/definition/**/*.tmdl")):
        rel = tmdl_path.relative_to(repo).as_posix()
        if rel.startswith("tests/") or "/tests/" in rel:
            continue
        try:
            text = tmdl_path.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        table = parse_tmdl(text)
        if table is None:
            continue
        for measure in table.measures:
            if measure.name in definitions:
                pairs.append(
                    MeasurePair(
                        name=measure.name,
                        dax=measure.expression,
                        locator=f"{rel}:{measure.line}",
                        definition=definitions[measure.name],
                    )
                )

    # 3. Run the drift check; print findings; return the exit code.
    findings, exit_code = run_semantic_pairs(pairs)
    for finding in findings:
        print(_format(finding))
    if exit_code == 0 and not findings:
        print("retail semantic-check: no drift (0 findings).", file=sys.stderr)
    return exit_code


def _filter_to_sql(filters: object, quote: Callable[..., str]) -> str | None:
    """Translate an L3 ``filter`` list into a SQL WHERE predicate (AND-joined).

    Reuses the L3 recognized-op vocabulary (``is_not_null`` / ``is_true``); each
    column is quoted via the hardened identifier helper. Returns None for an
    unrecognized op or a malformed entry (the caller fails the check closed).
    Empty/None filter list => "TRUE" (count all rows).
    """
    if not filters:
        return "TRUE"
    if not isinstance(filters, list):
        return None
    parts: list[str] = []
    for f in filters:
        if not isinstance(f, dict):
            return None
        col, op = f.get("column"), f.get("op")
        if not col:
            return None
        qcol = quote(col, context="L4 ratio filter column")
        if op == "is_not_null":
            parts.append(f"{qcol} IS NOT NULL")
        elif op == "is_true":
            parts.append(f"{qcol} = TRUE")
        else:
            return None
    return " AND ".join(parts)


def _run_value_check(args: argparse.Namespace) -> int:
    """Run the L4 value proxy: recompute each contract's approved value live.

    Lazy psycopg2 (via ``_ensure_driver`` / ``_make_runner``, reused from the
    validate path) so the stdlib-only `retail check` chain never imports a driver.
    Discovers metric contracts under --metrics-dir (confined to the repo, like
    semantic-check), parses each ``definition.expected_value`` block, recomputes the
    aggregate/ratio against the live gold table, and reports a V-L4 ERROR for any
    value outside tolerance. A contract with no expected_value block is skipped; a
    malformed block is a fail-closed ERROR, never a silent skip.
    """
    import dataclasses
    import os

    from .core import Severity
    from .dialect import get_dialect
    from .metric_drift import load_definition
    from .runner import _format
    from .validate import resolve_dsn
    from .value_proxy import check_expected_value, parse_expected_value

    repo = Path(args.repo)
    engine = _current_engine()
    dialect = get_dialect(engine)

    # Confine --metrics-dir to the repo tree (same guard as semantic-check, #26).
    repo_resolved = repo.resolve()
    metrics_root = (repo / args.metrics_dir).resolve()
    if metrics_root != repo_resolved and not metrics_root.is_relative_to(repo_resolved):
        print(
            f"error: --metrics-dir {args.metrics_dir!r} escapes the repo root; "
            "it must resolve to a path inside --repo.",
            file=sys.stderr,
        )
        return 1

    # 1. Resolve the engine's config. Postgres: --dsn wins; else env (UNCHANGED
    #    behavior). Other engines: --dsn is not applicable; resolve from env only.
    if engine == "postgres":
        env = dict(os.environ)
        if args.dsn:
            env = {**env, "DATABASE_URL": args.dsn}
        config = resolve_dsn(env)
    else:
        config = dialect.resolve_config(dict(os.environ))
    if config is None:
        print(
            "error: no database connection configured.\n"
            "       pass --dsn (a postgresql:// connection string), or set\n"
            "       DATABASE_URL, or the ANALYTICS_DB_* vars (in your gitignored\n"
            "       .env). Never commit a real DSN.",
            file=sys.stderr,
        )
        return 1

    # 2. The DB driver is optional + lazy: only needed for a real run.
    if not _ensure_driver():
        print(
            "error: `retail value-check` needs the optional DB driver.\n"
            "       install it with:  pip install 'retail[db]'\n"
            "       (the static `retail check` core stays dependency-free).",
            file=sys.stderr,
        )
        return 1

    # 3. Discover contracts and parse each expected_value block (fail-closed).
    expectations: list[tuple[str, object]] = []  # (measure_name, ExpectedValue)
    if metrics_root.is_dir():
        for contract_path in sorted(metrics_root.glob("*/metrics/*.yaml")):
            name = contract_path.stem
            try:
                definition = load_definition(str(contract_path))
            except (OSError, ValueError) as exc:
                print(
                    f"error: could not load contract {contract_path}: {exc}",
                    file=sys.stderr,
                )
                return 1
            # binds_to lives at the contract top level, not under `definition`.
            try:
                import yaml

                doc = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
            except (OSError, ValueError) as exc:
                print(
                    f"error: could not load contract {contract_path}: {exc}",
                    file=sys.stderr,
                )
                return 1
            binds_to = doc.get("binds_to") or {}
            try:
                expected = parse_expected_value(definition, binds_to)
            except ValueError as exc:
                print(
                    f"error: contract {name}: malformed expected_value ({exc})",
                    file=sys.stderr,
                )
                return 1
            if expected is None:
                continue  # no expected_value block -> skip
            # For a ratio, translate the L3 numerator/denominator filters into SQL.
            if expected.aggregation == "ratio":
                num_sql = _filter_to_sql(
                    (definition or {}).get("numerator", {}).get("filter"),
                    dialect.quote_ident,
                )
                den_sql = _filter_to_sql(
                    (definition or {}).get("denominator", {}).get("filter"),
                    dialect.quote_ident,
                )
                if num_sql is None or den_sql is None:
                    print(
                        f"error: contract {name}: ratio numerator/denominator filter "
                        "uses an unrecognized op (L4 cannot recompute it)",
                        file=sys.stderr,
                    )
                    return 1
                expected = dataclasses.replace(
                    expected,
                    numerator_count_sql_filter=num_sql,
                    denominator_count_sql_filter=den_sql,
                )
            expectations.append((name, expected))

    if not expectations:
        print(
            "retail value-check: no contract carries a `definition.expected_value` "
            "block -- nothing to verify.",
            file=sys.stderr,
        )
        return 0

    # 4. Connect and run each check. No real DB is touched in tests (fake runner).
    safe_host = _safe_target_label(engine, config)
    print(
        f"retail value-check: running L4 value checks against {safe_host}",
        file=sys.stderr,
    )
    try:
        runner = _make_runner(config)
        findings = []
        for name, expected in expectations:
            findings.extend(
                check_expected_value(runner, name, expected, dialect=dialect)
            )
    except ValueError as exc:
        # an unsafe identifier in a contract -> clean message, no traceback
        print(
            f"error: value-check rejected an unsafe contract identifier: {exc}",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(
            "error: live value-check failed at the DB boundary "
            f"({exc.__class__.__name__}): {dialect.redact(exc, config)}",
            file=sys.stderr,
        )
        return 1

    for finding in findings:
        print(_format(finding))
    if any(f.severity is Severity.ERROR for f in findings):
        return 1
    print(
        "retail value-check: all live values match the approved contracts "
        "(0 findings).",
        file=sys.stderr,
    )
    return 0


def _run_generate(args: argparse.Namespace) -> int:
    """Generate a verified DAX measure from a metric contract YAML.

    Lazy imports (dax_gen, yaml via load_contract) live INSIDE this handler so
    the stdlib-only `retail check` import chain never pulls them. Fail-closed:
    stdout carries ONLY verified output; every refusal/error writes to stderr
    and returns 1, leaving stdout empty (safe for shell redirection).

    --out guard: resolve the path before writing; refuse if it resolves under
    the repo's powerbi/ directory (prevents model mutation), and refuse if the
    target file already exists (no silent overwrite).
    """
    import json
    from pathlib import Path

    from .dax_gen import generate_measure, load_contract

    # 1. Read and parse the contract file.
    try:
        contract = load_contract(args.contract)
    except Exception as exc:
        print(f"[error] cannot read contract: {exc}", file=sys.stderr)
        return 1

    # 2. Validate required `name` field.
    name = contract.get("name")
    if not name:
        print("[error] contract has no `name`", file=sys.stderr)
        return 1

    # 3. Generate the measure (fail-closed: refuses bad contracts).
    result = generate_measure(
        contract.get("definition") or {},
        name=name,
        doc_intent=contract.get("formula_intent"),
    )
    if not result.ok:
        print(f"[refused] {name}: {result.reason}", file=sys.stderr)
        return 1

    # 4a. --out mode: write to a file with powerbi/ and overwrite guards.
    if args.out:
        out = Path(args.out).resolve()
        # PRIMARY guard (cwd-INDEPENDENT, defense in depth): refuse if ANY path
        # component of the resolved target is `powerbi` (case-insensitive). This
        # catches absolute paths into any powerbi/ tree, `../powerbi`, and nested
        # cases regardless of the process cwd -- closing the cwd-anchored hole.
        if "powerbi" in [p.lower() for p in out.parts]:
            print(
                f"[refused] --out resolves under powerbi/: {out}",
                file=sys.stderr,
            )
            return 1
        # SECONDARY guard (cwd-relative, cheap): the live model under THIS cwd.
        powerbi = (Path.cwd() / "powerbi").resolve()
        if out == powerbi or powerbi in out.parents:
            print(
                f"[refused] --out resolves under powerbi/: {out}",
                file=sys.stderr,
            )
            return 1
        if out.exists():
            print(f"[refused] --out file already exists: {out}", file=sys.stderr)
            return 1
        # M3: do NOT silently create parent dirs -- refuse cleanly if absent.
        if not out.parent.exists():
            print(
                f"[refused] --out parent directory does not exist: {out.parent}",
                file=sys.stderr,
            )
            return 1
        out.write_text(result.tmdl_block, encoding="utf-8")
        return 0

    # 4b. Stdout mode: emit verified output only.
    if args.fmt == "json":
        print(
            json.dumps(
                {
                    "ok": True,
                    "dax": result.dax,
                    "tmdl_block": result.tmdl_block,
                    "warnings": list(result.warnings),
                }
            )
        )
    else:
        print(result.tmdl_block)
    return 0


if __name__ == "__main__":
    # Make `python -m retail.cli ...` invoke the CLI instead of being a silent no-op.
    # The installed `retail` console script (pyproject [project.scripts]) calls main()
    # directly; without this guard `python -m retail.cli` imported the module and
    # exited 0 without running anything. Under pytest __name__ != "__main__", so this
    # never fires during tests.
    sys.exit(main())
