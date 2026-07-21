"""`retail validate` handler: LIVE data checks against any Postgres DB.

Extracted verbatim from the former ``retail/cli.py`` (CodeScene hotspot split).
Calls the shared seams (``_ensure_driver``, ``_make_runner``, ``_load_targets``,
``_current_engine``, ``_safe_target_label``) via ``from seshat import cli`` and
``cli.<name>(...)`` -- NOT a by-value import -- so ``monkeypatch.setattr(
"seshat.cli._make_runner", ...)`` in the test suite still lands on the exact
attribute this handler reads at call time.
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable


def _resolve_config(
    args: argparse.Namespace,
    engine: str,
    dialect: object,
    resolve_dsn: Callable[[dict[str, str]], str | None],
) -> object:
    """Resolve the engine's DB config from the (already `.env`-applied) env.

    Postgres: ``--dsn`` wins, else the env; other engines resolve from env only
    (``--dsn`` is not applicable). ``os.environ`` already carries the workspace
    ``.env`` values here because the caller runs inside ``applied_dotenv`` (#340),
    so this reads the process env directly. Extracted to keep ``run_validate``
    below the CodeScene complexity threshold and to mirror
    ``value_check._resolve_config`` / ``drift._resolve_live_config``.
    """
    import os

    if engine == "postgres":
        env = dict(os.environ)
        if args.dsn:
            env = {**env, "DATABASE_URL": args.dsn}
        return resolve_dsn(env)
    return dialect.resolve_config(dict(os.environ))  # type: ignore[attr-defined]


def run_validate(args: argparse.Namespace) -> int:
    """Run the LIVE validators against a real DB, honoring the workspace `.env`.

    Thin wrapper: apply the workspace ``.env`` (#340) for the whole body so
    engine selection, driver choice, and config resolution all see the
    documented ``ANALYTICS_DB_*`` values, then delegate. A malformed ``.env``
    fails clean (exit 1, no traceback) rather than raising at the DB boundary.
    """
    from pathlib import Path

    from seshat.connection_env import ConnectionConfigError, applied_dotenv
    from seshat.dbt.redaction import EnvironmentConfigError

    try:
        with applied_dotenv(Path.cwd()):
            return _run_validate_body(args)
    except EnvironmentConfigError as exc:
        print(f"error: could not read the workspace .env: {exc}", file=sys.stderr)
        return 1
    except ConnectionConfigError as exc:
        print(f"error: invalid database connection setting: {exc}", file=sys.stderr)
        return 1


def _run_validate_body(args: argparse.Namespace) -> int:
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
    from seshat import cli
    from seshat.connection_env import as_connection_config
    from seshat.core import Severity
    from seshat.dialect import get_dialect
    from seshat.runner import _format  # reuse the [severity] id (locator) format
    from seshat.validate import resolve_dsn, run_live_checks

    prog = cli._prog(args)  # brand the client typed (`seshat`/`retail`), #402

    # Engine + config resolution can raise ValueError on an invalid setting
    # (unknown ANALYTICS_DB_ENGINE, unparseable port); convert those to a clean
    # boundary failure. The live-check body below is deliberately OUTSIDE this
    # wrap so its own ValueErrors are never masked.
    engine = cli._current_engine()
    dialect = as_connection_config(lambda: get_dialect(engine))

    # 1. Resolve the engine's config. Postgres: --dsn wins; else env (UNCHANGED
    #    behavior). Other engines: --dsn is not applicable; resolve from env only.
    config = as_connection_config(
        lambda: _resolve_config(args, engine, dialect, resolve_dsn)
    )
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
    if not cli._ensure_driver():
        print(
            f"error: `{prog} validate` needs the optional DB driver.\n"
            f"{cli._db_extra_hint()}\n"
            f"       (the static `{prog} check` core stays dependency-free).",
            file=sys.stderr,
        )
        return 1

    safe_host = cli._safe_target_label(engine, config)

    # 3a. Deferred mode: no table targets supplied -> report, do not connect.
    if not args.source_map:
        print(
            f"{prog} validate: the live-validator surface is built and fixture-tested. "
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
        targets = cli._load_targets(args.source_map)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"error: could not load source-map: {exc}", file=sys.stderr)
        return 1

    print(f"{prog} validate: running live checks against {safe_host}", file=sys.stderr)
    try:
        runner = cli._make_runner(config)
        findings = run_live_checks(runner, targets, dialect=dialect)
    except Exception as exc:
        print(
            "error: live validation failed at the DB boundary "
            f"({exc.__class__.__name__}): {dialect.redact(exc, config)}",
            file=sys.stderr,
        )
        print(
            "       verify the DSN, network access, database objects, and the "
            "optional DB driver:\n"
            f"{cli._db_extra_hint()}",
            file=sys.stderr,
        )
        return 1

    for finding in findings:
        print(_format(finding))
    if any(f.severity is Severity.ERROR for f in findings):
        return 1
    print(f"{prog} validate: all live checks passed (0 findings).", file=sys.stderr)
    return 0
