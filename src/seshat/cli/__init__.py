"""retail CLI entry point.

CodeScene hotspot split (score 4.83, #1 churn-weighted hotspot): the former
~1009-line ``retail/cli.py`` module is now a package. ``main`` stays the
installed entry point (pyproject ``retail = "seshat.cli:main"``); every
subcommand's argparse surface, exit codes, and stdout/stderr output are
UNCHANGED byte-for-byte.

Structure:
  - ``parser.py``: ``_build_parser`` (kept whole -- top-level --help lists
    subcommands in add-order and every flag's metavar/help must stay
    byte-identical; centralizing assembly is lower-risk than scattering
    ordered ``add_*_parser`` calls across many modules).
  - ``commands/*.py``: one handler per subcommand. ``main`` dispatches through
    ``_DISPATCH``, a ``{command_name: handler}`` table, instead of an
    if/elif chain, so a new subcommand adds one table row and does NOT grow
    ``main``'s cyclomatic complexity. Each non-uniform handler is imported
    LAZILY -- via ``_lazy(module_path, func_name)``, which defers the import
    to call time -- mirroring the pre-split lazy-import discipline (e.g.
    ``from .theme_gen import theme_gen_main``): ``retail check`` / CI never
    loads driver-touching or PBIR/demo modules it doesn't need.
  - The seams below (``_ensure_driver``, ``_make_runner``, ``_load_targets``,
    ``_current_engine``, ``_safe_target_label``, ``_redact_dsn``) stay defined
    HERE (not relocated into a handler module) because the test suite patches
    them as ``seshat.cli.<name>`` and handler modules read them back via
    ``from seshat import cli; cli.<name>(...)`` -- module-attribute lookup at
    call time, so a monkeypatch on this module is always visible to callers.
  - ``_run_check`` and ``_run_doctor`` are the two non-uniform dispatch
    entries, kept as small wrapper functions in THIS module (not lazy
    factories) because they are not a plain ``handler(args)`` call:
      - ``_run_check`` is tightly coupled to ``build_context`` / ``run`` /
        ``run_json`` / ``all_rules``, which the test suite patches directly
        as ``seshat.cli.build_context`` / ``seshat.cli.run``; it carries none
        of the CC/LOC hotspot weight the other handlers do.
      - ``_run_doctor`` adapts the table's uniform ``handler(args)`` shape to
        ``run_doctor``'s actual signature, ``run_doctor(repo_root, strict=)``.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import seshat.rules  # noqa: F401  (import for side effects: fires every @register)

from ..registry import all_rules
from ..runner import build_context, run, run_json, run_review, run_sarif
from .parser import _build_parser

if TYPE_CHECKING:
    # Type-only imports: kept behind TYPE_CHECKING so the driver-free / lazy-import
    # discipline of the runtime handlers is preserved (these modules are imported
    # lazily inside the handlers, never at module scope).
    from ..validate import QueryRunner
    from ..validate_targets import ValidationTargets


def _run_check(args: object) -> int:
    """Handler for ``check``. Kept as a wrapper (not a lazy-imported handler)
    -- see the module docstring for why: it reads ``build_context`` / ``run``
    / ``run_json`` / ``all_rules`` as bare module globals so test-suite
    monkeypatches on ``seshat.cli.*`` stay visible."""
    commit_message: str | None = None
    if args.commit_msg_file is not None:  # type: ignore[attr-defined]
        try:
            raw = Path(args.commit_msg_file).read_text(encoding="utf-8")  # type: ignore[attr-defined]
        except FileNotFoundError:
            print(
                f"error: commit message file not found: {args.commit_msg_file}",  # type: ignore[attr-defined]
                file=sys.stderr,
            )
            return 1  # main() is -> int; the __main__ guard does sys.exit(main())
        # git's COMMIT_EDITMSG ends in a trailing newline (\r\n on Windows) —
        # strip it so the message passed to rules is the bare text.
        commit_message = raw.rstrip("\r\n")

    try:
        ctx = build_context(
            Path(args.repo),  # type: ignore[attr-defined]
            commit_range=args.commit_range,  # type: ignore[attr-defined]
            commit_message=commit_message,
        )
    except (OSError, RuntimeError) as exc:
        # build_context -> _git_ls_files exercises git BEFORE any rule runs. A git
        # that cannot launch (OSError: missing binary) or fails non-zero/non-128
        # (RuntimeError: e.g. a corrupt repo) must surface as a clean error, not a
        # raw traceback (the #371 crash class). A non-git workspace is NOT this
        # case -- git exit-128 is tolerated inside _git_ls_files (returns ()), so
        # `check` still runs there (#384). (#394, reframed.)
        print(
            f"error: git is required to run 'check' but failed: {exc}", file=sys.stderr
        )
        return 1
    # Spec A drop-in fitness: in a repo the kit was merely downloaded into
    # (not bootstrapped), KIT_SELF rules SKIP (INFO) instead of ERROR-ing on
    # internal manifests that repo can't have. The kit's own repo IS
    # bootstrapped, so nothing skips there -- behavior is unchanged.
    from ..kit_lint import is_bootstrapped

    bootstrapped = is_bootstrapped(Path(args.repo))  # type: ignore[attr-defined]
    # Default 'text' calls the unchanged run(); 'json' is the opt-in path.
    if args.output_format == "json":  # type: ignore[attr-defined]
        return run_json(all_rules(), ctx, bootstrapped=bootstrapped)
    if args.output_format == "review":  # type: ignore[attr-defined]
        return run_review(all_rules(), ctx, bootstrapped=bootstrapped)
    if args.output_format == "sarif":  # type: ignore[attr-defined]
        return run_sarif(all_rules(), ctx, bootstrapped=bootstrapped)
    return run(all_rules(), ctx, bootstrapped=bootstrapped)


def _run_doctor(args: object) -> int:
    """Handler for ``doctor``. Kept as a wrapper because ``run_doctor``'s
    signature (``repo_root, strict=``) isn't the table's uniform
    ``handler(args)`` shape."""
    from ..doctor import run_doctor

    return run_doctor(
        Path(args.repo),  # type: ignore[attr-defined]
        strict=args.strict,  # type: ignore[attr-defined]
        prog=getattr(args, "prog", "seshat"),
    )


def _run_mcp(args: object) -> int:
    try:
        from ..governor.mcp_server import run_stdio
    except ImportError:
        print(
            "error: MCP support is optional; install with "
            "`pip install 'seshat-bi[mcp]'`.",
            file=sys.stderr,
        )
        return 2
    run_stdio(Path(args.repo))  # type: ignore[attr-defined]
    return 0


def _lazy(module_path: str, func_name: str):
    """Build a dispatch-table handler that imports ``func_name`` from
    ``module_path`` at CALL time, not at table-construction time. This is
    what keeps the lazy-import discipline intact: building ``_DISPATCH`` as a
    module-level dict must NOT force-import every command module (drivers,
    PBIR, demo, ...) just because ``seshat.cli`` was imported.
    """

    def handler(args: object) -> int:
        import importlib

        module = importlib.import_module(module_path, package=__name__)
        func = getattr(module, func_name)
        return func(args)

    return handler


_DISPATCH: dict[str, Callable[[object], int]] = {
    "check": _run_check,
    "validate": _lazy(".commands.validate", "run_validate"),
    "profile": _lazy(".commands.profile", "run_profile"),
    "drift": _lazy(".commands.drift", "run_drift"),
    "semantic-check": _lazy(".commands.semantic", "run_semantic_check"),
    "value-check": _lazy(".commands.value_check", "run_value_check"),
    "generate": _lazy(".commands.generate", "run_generate"),
    "theme-gen": _lazy("..theme_gen", "theme_gen_main"),
    "theme-compile": _lazy("..theme_compile", "theme_compile_main"),
    "pbir-apply-theme": _lazy("..pbir_theme_apply", "pbir_apply_main"),
    "pbir-format-visual": _lazy("..pbir_visual_format", "pbir_format_main"),
    "pbir-set-page-background": _lazy("..pbir_page_background", "pbir_page_bg_main"),
    "pbir-set-geometry": _lazy("..pbir_geometry", "pbir_geometry_main"),
    "pbir-validate-blueprint": _lazy(
        "..pbir_validate_blueprint", "pbir_validate_blueprint_main"
    ),
    "manifest": _lazy(".commands.manifest", "run_manifest"),
    "severity-posture": _lazy(".commands.severity_posture", "run_severity_posture"),
    "scaffold": _lazy(".commands.scaffold", "run_scaffold"),
    "init": _lazy(".commands.init", "run_init"),
    "init-project": _lazy(".commands.init_project", "init_project_main"),
    "scaffold-source": _lazy(".commands.scaffold_source", "scaffold_source_main"),
    "adopt-pbip": _lazy(".commands.adopt_pbip", "adopt_pbip_main"),
    "dbt": _lazy(".commands.dbt", "dbt_main"),
    "kit-lint": _lazy(".commands.kit_lint", "run_kit_lint"),
    "status": _lazy(".commands.status", "status_main"),
    "dashboard": _lazy(".commands.dashboard", "dashboard_main"),
    "next": _lazy(".commands.next", "next_main"),
    "approvals": _lazy(".commands.approvals", "approvals_main"),
    "evidence-pack": _lazy(".commands.evidence_pack", "evidence_pack_main"),
    "blockers": _lazy(".commands.blockers", "blockers_main"),
    "pii-notice": _lazy(".commands.pii_notice", "pii_notice_main"),
    "approver-view": _lazy(".commands.approver_view", "approver_view_main"),
    "mapping-mirror": _lazy(".commands.mapping_mirror", "mapping_mirror_main"),
    "dashboard-planner": _lazy(".commands.dashboard_planner", "dashboard_planner_main"),
    "dashboard-gaps": _lazy(".commands.gap_detector", "gap_detector_main"),
    "doctor": _run_doctor,
    "demo": _lazy("..demo", "run_demo"),
    "passport": _lazy(".commands.passport", "passport_main"),
    "pack": _lazy(".commands.pack", "pack_main"),
    "benchmark": _lazy(".commands.benchmark", "benchmark_main"),
    "explorer": _lazy(".commands.explorer", "explorer_main"),
    "impact-map": _lazy(".commands.impact_map", "impact_map_main"),
    "agent": _lazy(".commands.agent_verify", "agent_verify_main"),
    "watch": _lazy(".commands.watch", "watch_main"),
    "dagster": _lazy(".commands.dagster", "dagster_main"),
    "mcp": _run_mcp,
}


def _force_utf8_stdio() -> None:
    """Make CLI output UTF-8 on Windows so non-ASCII renders instead of crashing.

    Renderers emit Unicode (box-drawing, arrows) and governed data can contain
    non-Latin text (e.g. Arabic ``billing_type`` values). Windows consoles
    default to a legacy code page (cp1252), so the default stdout encoder raises
    ``UnicodeEncodeError`` on the most basic verbs (``status``, ``next``). This
    is the single dispatch chokepoint, so reconfiguring here fixes every
    subcommand at once.

    Scoped to win32 and gated on ``hasattr(..., "reconfigure")`` -- POSIX stdout
    is already UTF-8 (reconfiguring to the same encoding is a byte-for-byte
    no-op, so the CLI's unchanged-output contract holds there), and under pytest
    capture / some pipe redirects ``sys.stdout`` is not a ``TextIOWrapper`` and
    has no ``reconfigure``. Strict encoding (no ``errors=`` override) is
    deliberate: replacement would silently corrupt Arabic output we govern.
    """
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        if (getattr(stream, "encoding", "") or "").lower().replace("-", "") == "utf8":
            continue
        try:
            reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            # A stream that refuses reconfiguration is left as-is rather than
            # turning a rendering nicety into a hard failure.
            pass


def _invoked_prog() -> str:
    """The command name the client actually typed (``seshat`` or ``retail``).

    Derived from argv[0]'s basename so the two byte-identical console entry
    points each print their own identity in usage/error text (#378) and output
    prefixes (#402).

    Only the two real brand stems are honored; anything else -- an empty argv0
    (``python -c``), or a module run whose stem is the entry file, not the brand
    (``python -m seshat.cli`` -> ``__main__``; ``python -m retail.cli`` -> ``cli``)
    -- normalizes to ``seshat``, the primary brand, so no command ever emits a
    nonsense ``__main__ status:`` / ``cli drift:`` prefix (PR #403 review). The
    module entry points additionally pass an explicit ``prog`` to preserve the
    deprecated ``retail`` identity on ``-m retail.cli``; this is the safety net.
    """
    import os
    import sys

    raw = sys.argv[0] if sys.argv else ""
    stem = os.path.splitext(os.path.basename(raw))[0]
    return stem if stem in ("seshat", "retail") else "seshat"


def _prog(args: object) -> str:
    """The brand the client typed, for a handler's output prefix.

    ``main`` stamps ``args.prog`` with the resolved invoked name (``seshat`` or the
    deprecated ``retail`` alias). Read via ``getattr`` with a ``seshat`` default so
    a handler stays callable from a unit test that builds a bare ``Namespace``
    without ``prog`` -- and the customer-facing brand (``seshat``, the primary
    command) is the default, never the ``retail`` alias (#402).
    """
    return getattr(args, "prog", "seshat") or "seshat"


def _db_extra_hint(engine: str = "postgres") -> str:
    """Actionable, install-path-aware guidance for the optional DB driver (#399).

    Names the real distribution (``seshat-bi``, not the internal ``retail``) and
    both supported ways to add the driver: ``pipx inject`` for the documented
    external-customer ``pipx`` install (where ``pip install`` inside the isolated
    venv is the wrong mechanism), and the ``pip install`` extra for a plain venv.
    Sourced from ONE place so the brand + remedy can't drift per command.

    ``engine`` selects the right driver/extra so a non-Postgres run (SQL Server /
    MySQL / Snowflake) is told to install ITS driver, not psycopg2 (PR #409). The
    default is ``postgres`` -- unchanged output for callers that don't pass one.
    """
    driver, extra = {
        "postgres": ("psycopg2-binary", "db"),
        "sqlserver": ("pyodbc", "mssql"),
        "mysql": ("mysql-connector-python", "mysql"),
        "snowflake": ("snowflake-connector-python", "snowflake"),
    }.get(engine, ("psycopg2-binary", "db"))
    return (
        f"       pipx install:  pipx inject seshat-bi {driver}\n"
        f"       pip install:   pip install 'seshat-bi[{extra}]'"
    )


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    _force_utf8_stdio()
    resolved_prog = prog or _invoked_prog()
    try:
        args = _build_parser(resolved_prog).parse_args(argv)
    except SystemExit as exc:
        # argparse exits on bad/missing args (code 2) AND on --help / --version
        # (code 0) after printing. The established contract is to SURFACE the code
        # as a return value, not let it propagate -- so `main([...])` never raises.
        return int(exc.code or 0)

    # Stamp the invoked command name onto args so every handler can echo the brand
    # the client actually typed (`seshat` or the deprecated `retail` alias) in its
    # output prefix, instead of a hardcoded literal that drifts (#402). Threading it
    # via args keeps all handler signatures at their existing `handler(args)` shape.
    args.prog = resolved_prog

    handler = _DISPATCH.get(args.command)
    if handler is None:
        return 0
    return handler(args)


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
        return _postgres_target_label(config)
    return engine


def _postgres_target_label(config: str) -> str:
    """A credential-free label from a Postgres config string.

    Classify by OUTER syntax, never by content (#409 P1). A libpq KEYWORD
    conninfo can embed anything inside a quoted credential -- ``@``, ``host=``,
    even ``://`` (``password='abc://u:s3cret@x'``) -- so any content-based test
    (``"://" in config``, a ``host=`` regex, an ``@`` split) can be spoofed into
    surfacing the secret. A genuine Postgres URL is identified ONLY by its
    leading ``postgresql://`` / ``postgres://`` scheme, which a keyword conninfo
    (always ``keyword=value ...``) can never produce at offset 0. Anything that
    is not outwardly a URL renders NO component -- just the bare engine label.
    """
    if config.lstrip().lower().startswith(("postgresql://", "postgres://")):
        # URL form. Parse STRUCTURALLY (urlsplit) rather than string-splitting on
        # "@"/"?": a query-string credential whose value contains a raw "@"
        # defeats a split-then-strip and leaks the trailing fragment (#409 P1).
        # urlsplit.hostname excludes any userinfo and .path excludes the query,
        # so only host[:port]/dbname is surfaced.
        from urllib.parse import urlsplit

        try:
            parts = urlsplit(config.lstrip())
            host = parts.hostname
            # .port is a lazily-parsed property: it raises ValueError on a
            # non-numeric / out-of-range port (`host:notaport`). This label is
            # computed BEFORE the handler's DB-boundary try, so an unguarded
            # access would surface an uncaught traceback instead of the clean
            # config error (#409). Access it inside the guard.
            port = parts.port
        except ValueError:
            return "postgres"
        if not host:
            return "postgres"
        label = f"{host}:{port}" if port else host
        return f"{label}{parts.path}" if parts.path not in ("", "/") else label
    return "postgres"


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
    the DSN and redact each non-empty component (host, username, password, db-name,
    and the ``user@`` credentials prefix) wherever it appears (audit 2026-06-26 #7).

    The component decomposition is delegated to :mod:`seshat.redaction_core` -- the
    single hardened source of truth (#365/#366) -- so this boundary redactor also
    scrubs the DB-NAME and the percent-decoded form of every component, and can
    never drift from the shared decomposition (#385).
    """
    from ..redaction_core import replace_fragments, uri_components

    text = str(message) or message.__class__.__name__
    if not dsn:
        return text
    # Order matters: replace the verbatim DSN (and its ``user@`` prefix) BEFORE
    # decomposing, so the "<redacted DSN>" token survives for callers that assert
    # on it. uri_components sorts longest-first and tolerates a non-URI dsn (empty
    # tuple), so the reformatted-by-the-driver leak is covered without a crash.
    text = text.replace(dsn, "<redacted DSN>")
    if "@" in dsn:
        text = text.replace(dsn.split("@", 1)[0] + "@", "<credentials>@")
    # uri_components -> urlsplit can raise ValueError on a malformed DSN (e.g. a
    # bad IPv6 literal). This runs WHILE formatting a DB error, so a crash here is
    # worse than under-redaction: fall back to the literal-DSN scrub already done.
    try:
        fragments = uri_components([dsn])
    except ValueError:
        return text
    return replace_fragments(text, fragments, "<redacted>")


__all__ = [
    "main",
    "_build_parser",
    "_safe_target_label",
    "_current_engine",
    "_ensure_driver",
    "_make_runner",
    "_load_targets",
    "_redact_dsn",
    "_prog",
    "_db_extra_hint",
    "build_context",
    "run",
    "run_json",
    "run_review",
    "run_sarif",
    "all_rules",
]
