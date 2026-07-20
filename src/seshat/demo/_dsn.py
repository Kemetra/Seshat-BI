"""Shared DSN resolution + reachability probe for the demo verbs (spec 083).

`demo load` and `demo run` used to resolve (or not resolve) a DSN independently,
which drifted: `load` honored the workspace `.env` while `run` read only
`args.dsn` (#376), and `run` decided "live mode" on `bool(dsn)` without ever
connecting (#375). This module is the single seam both verbs call so the two can
never disagree again.

Postgres-only, mirroring the demo live leg (`psycopg2` in `demo.live`). No new
dependency: the probe imports psycopg2 lazily and degrades to "unreachable" when
the `[db]` extra is absent -- exactly the offline posture the demo already takes.
"""

from __future__ import annotations

from pathlib import Path


def resolve_dsn(args) -> str | None:
    """Resolve a DSN via the same precedence as ``retail validate`` (reused).

    Precedence: an explicit ``--dsn`` wins; otherwise the workspace ``.env`` is
    applied over the process environment (``applied_dotenv``, #340) and
    ``resolve_dsn(env)`` builds the DSN from ``DATABASE_URL`` / ``ANALYTICS_DB_*``
    -- so a DSN documented only in the gitignored ``.env`` resolves here exactly
    as it does for ``retail validate`` (#350).

    The demo live leg is Postgres-only (``psycopg2`` in ``demo.live``), so it
    respects the repository's single engine authority: when ``.env`` selects a
    NON-Postgres ``ANALYTICS_DB_ENGINE`` (mysql/sqlserver/snowflake), the generic
    ``ANALYTICS_DB_*`` values must NOT be force-built into a bogus
    ``postgresql://...`` DSN and handed to psycopg2 (Codex P2). That case
    degrades to offline. Returns None when no DSN is configured (the honest
    offline case); a malformed ``.env`` also degrades to offline (the demo is a
    convenience path, never a hard failure).
    """
    explicit = getattr(args, "dsn", None)
    if explicit:
        return explicit
    try:
        import os

        from seshat.cli import _current_engine
        from seshat.connection_env import applied_dotenv
        from seshat.validate import resolve_dsn as resolve_dsn_from_env
    except Exception:
        return None
    try:
        with applied_dotenv(Path(getattr(args, "repo", "."))):
            # The live leg only speaks Postgres; a non-Postgres engine selection
            # is honored as "no Postgres DSN here" -> offline, never a fabricated
            # postgresql:// DSN aimed at the wrong engine.
            if _current_engine() != "postgres":
                return None
            return resolve_dsn_from_env(dict(os.environ))
    except Exception:
        return None


def probe_reachable(dsn: str) -> bool:
    """Return whether ``dsn`` names an actually-reachable Postgres.

    A truthful "live mode" claim needs EVIDENCE, not the mere presence of a DSN
    string (#375). Attempts a real, short-lived psycopg2 connection and returns
    whether it succeeded. Degrades to ``False`` when the ``[db]`` extra is absent
    or the connection fails for any reason -- the demo never turns an offline
    condition into a hard error. Never raises; never echoes the DSN.
    """
    if not dsn:
        return False
    try:
        import psycopg2
    except Exception:
        return False
    try:
        conn = psycopg2.connect(dsn, connect_timeout=3)
    except Exception:
        return False
    try:
        conn.close()
    except Exception:
        pass
    return True
