from __future__ import annotations

import argparse
import sys
from pathlib import Path

import retail.rules  # noqa: F401  (import for side effects: fires every @register)

from .registry import all_rules
from .runner import build_context, run


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
                sys.exit(1)
            # git's COMMIT_EDITMSG ends in a trailing newline (\r\n on Windows) —
            # strip it so the message passed to rules is the bare text.
            commit_message = raw.rstrip("\r\n")

        ctx = build_context(
            Path(args.repo),
            commit_range=args.commit_range,
            commit_message=commit_message,
        )
        return run(all_rules(), ctx)

    if args.command == "validate":
        return _run_validate(args)

    return 0


def _ensure_driver() -> bool:
    """True if the optional psycopg2 driver is importable. LAZY: the import lives
    here, never at module scope, so `retail check` / CI (no driver) never load it."""
    try:
        import psycopg2  # noqa: F401  (lazy: only when validate actually connects)
    except ImportError:
        return False
    return True


def _make_runner(dsn: str):
    """Build a real (lazy psycopg2) QueryRunner. Indirected through cli so tests
    can monkeypatch it with a fake -- no real DB is touched in the suite."""
    from .validate import make_psycopg2_runner

    return make_psycopg2_runner(dsn)


def _load_targets(source_map: str):
    """Load per-table validate targets from a source-map.yaml. Indirected (and
    lazy-importing the YAML loader) so the driver-free import path is preserved
    and tests can monkeypatch it."""
    from .validate_targets import load_targets

    return load_targets(source_map)


def _run_validate(args) -> int:
    """Run the LIVE validators against a real DB.

    The psycopg2 import is LAZY (via ``_ensure_driver`` / ``_make_runner``, never
    at module scope) so that `retail check` and CI -- which install no DB driver --
    never import it. If the driver or a usable connection is missing, exit non-zero
    with an actionable message, never a raw traceback.

    Connection is host-agnostic (any Postgres: local / remote / DigitalOcean /
    other) via a DSN resolved from --dsn or env (DATABASE_URL / ANALYTICS_DB_*).

    Two modes:
      * ``--source-map PATH`` given -> load that table's targets, connect, run the
        four live checks, print findings, return 1 iff any ERROR (the live run).
      * no ``--source-map`` -> report the deferred state (the surface is built and
        fixture-tested; a live run needs a table's targets). Returns 1.
    """
    import os

    from .core import Severity
    from .runner import _format  # reuse the [severity] id message (locator) format
    from .validate import resolve_dsn, run_live_checks

    # 1. Resolve a DSN (host-agnostic). --dsn wins; else env. No DSN -> clear error.
    env = dict(os.environ)
    if args.dsn:
        env = {**env, "DATABASE_URL": args.dsn}
    dsn = resolve_dsn(env)
    if dsn is None:
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

    safe_host = dsn.split("@")[-1] if "@" in dsn else dsn  # never echo credentials

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
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: could not load source-map: {exc}", file=sys.stderr)
        return 1

    print(f"retail validate: running live checks against {safe_host}", file=sys.stderr)
    runner = _make_runner(dsn)
    findings = run_live_checks(runner, targets)
    for finding in findings:
        print(_format(finding))
    if any(f.severity is Severity.ERROR for f in findings):
        return 1
    print("retail validate: all live checks passed (0 findings).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    # Make `python -m retail.cli ...` invoke the CLI instead of being a silent no-op.
    # The installed `retail` console script (pyproject [project.scripts]) calls main()
    # directly; without this guard `python -m retail.cli` imported the module and
    # exited 0 without running anything. Under pytest __name__ != "__main__", so this
    # never fires during tests.
    sys.exit(main())
