"""retail CLI entry point.

CodeScene hotspot split (score 4.83, #1 churn-weighted hotspot): the former
~1009-line ``retail/cli.py`` module is now a package. ``main`` stays the
installed entry point (pyproject ``retail = "retail.cli:main"``); every
subcommand's argparse surface, exit codes, and stdout/stderr output are
UNCHANGED byte-for-byte.

Structure:
  - ``parser.py``: ``_build_parser`` (kept whole -- top-level --help lists
    subcommands in add-order and every flag's metavar/help must stay
    byte-identical; centralizing assembly is lower-risk than scattering
    ordered ``add_*_parser`` calls across many modules).
  - ``commands/*.py``: one handler per subcommand, each imported LAZILY inside
    ``main``'s dispatch (mirrors the pre-split lazy-import discipline, e.g.
    ``from .theme_gen import theme_gen_main``).
  - The seams below (``_ensure_driver``, ``_make_runner``, ``_load_targets``,
    ``_current_engine``, ``_safe_target_label``, ``_redact_dsn``) stay defined
    HERE (not relocated into a handler module) because the test suite patches
    them as ``retail.cli.<name>`` and handler modules read them back via
    ``from retail import cli; cli.<name>(...)`` -- module-attribute lookup at
    call time, so a monkeypatch on this module is always visible to callers.
  - The ``check`` branch stays inline in ``main`` (unextracted): it is tightly
    coupled to ``build_context`` / ``run`` / ``run_json`` / ``all_rules``,
    which are also patched directly as ``retail.cli.build_context`` /
    ``retail.cli.run`` by the test suite, and it carries none of the CC/LOC
    hotspot weight the other handlers do.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import retail.rules  # noqa: F401  (import for side effects: fires every @register)

from ..registry import all_rules
from ..runner import build_context, run, run_json
from .parser import _build_parser

if TYPE_CHECKING:
    # Type-only imports: kept behind TYPE_CHECKING so the driver-free / lazy-import
    # discipline of the runtime handlers is preserved (these modules are imported
    # lazily inside the handlers, never at module scope).
    from ..validate import QueryRunner
    from ..validate_targets import ValidationTargets


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
        from ..kit_lint import is_bootstrapped

        bootstrapped = is_bootstrapped(Path(args.repo))
        # Default 'text' calls the unchanged run(); 'json' is the opt-in path.
        if args.output_format == "json":
            return run_json(all_rules(), ctx, bootstrapped=bootstrapped)
        return run(all_rules(), ctx, bootstrapped=bootstrapped)

    if args.command == "validate":
        from .commands.validate import run_validate

        return run_validate(args)

    if args.command == "semantic-check":
        from .commands.semantic import run_semantic_check

        return run_semantic_check(args)

    if args.command == "value-check":
        from .commands.value_check import run_value_check

        return run_value_check(args)

    if args.command == "generate":
        from .commands.generate import run_generate

        return run_generate(args)

    if args.command == "theme-gen":
        from ..theme_gen import theme_gen_main

        return theme_gen_main(args)

    if args.command == "theme-compile":
        from ..theme_compile import theme_compile_main

        return theme_compile_main(args)

    if args.command == "pbir-apply-theme":
        from ..pbir_theme_apply import pbir_apply_main

        return pbir_apply_main(args)

    if args.command == "pbir-format-visual":
        from ..pbir_visual_format import pbir_format_main

        return pbir_format_main(args)

    if args.command == "pbir-set-page-background":
        from ..pbir_page_background import pbir_page_bg_main

        return pbir_page_bg_main(args)

    if args.command == "pbir-set-geometry":
        from ..pbir_geometry import pbir_geometry_main

        return pbir_geometry_main(args)

    if args.command == "manifest":
        from .commands.manifest import run_manifest

        return run_manifest(args)

    if args.command == "severity-posture":
        from .commands.severity_posture import run_severity_posture

        return run_severity_posture(args)

    if args.command == "scaffold":
        from .commands.scaffold import run_scaffold

        return run_scaffold(args)

    if args.command == "init":
        from .commands.init import run_init

        return run_init(args)

    if args.command == "init-project":
        from .commands.init_project import init_project_main

        return init_project_main(args)

    if args.command == "kit-lint":
        from .commands.kit_lint import run_kit_lint

        return run_kit_lint(args)

    if args.command == "doctor":
        from ..doctor import run_doctor

        return run_doctor(Path(args.repo), strict=args.strict)

    if args.command == "demo":
        from ..demo import run_demo

        return run_demo(args)

    return 0


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
    from ..dialect import get_dialect

    return get_dialect(_current_engine()).connect(dsn)


def _load_targets(source_map: str) -> ValidationTargets:
    """Load per-table validate targets from a source-map.yaml. Indirected (and
    lazy-importing the YAML loader) so the driver-free import path is preserved
    and tests can monkeypatch it."""
    from ..validate_targets import load_targets

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


__all__ = [
    "main",
    "_build_parser",
    "_safe_target_label",
    "_current_engine",
    "_ensure_driver",
    "_make_runner",
    "_load_targets",
    "_redact_dsn",
    "build_context",
    "run",
    "run_json",
    "all_rules",
]
