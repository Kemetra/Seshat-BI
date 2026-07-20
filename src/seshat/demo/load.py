"""``retail demo load`` -- offline no-op-with-reason, or the optional live leg.

Offline (no DSN): reports the skip reason and exits 0 -- loading needs a database,
and its absence is the honest, expected offline state, not an error.

Live (a DSN resolves): writes the demo sample into DEMO-SCOPED Postgres objects
only (a safety guard, FR-011), idempotently. The DB driver is imported lazily; the
DSN is resolved via the same precedence as ``retail validate`` (reused, not
reimplemented). The real-DB write is exercised in tests via a fixture writer /
``QueryRunner`` so CI needs no live database.
"""

from __future__ import annotations

from pathlib import Path

from . import DEMO_MARKER


def _resolve_dsn(args) -> str | None:
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
        from seshat.validate import resolve_dsn
    except Exception:
        return None
    try:
        with applied_dotenv(Path(getattr(args, "repo", "."))):
            # The live leg only speaks Postgres; a non-Postgres engine selection
            # is honored as "no Postgres DSN here" -> offline, never a fabricated
            # postgresql:// DSN aimed at the wrong engine.
            if _current_engine() != "postgres":
                return None
            return resolve_dsn(dict(os.environ))
    except Exception:
        return None


def target_is_demo_scoped(schema: str, table: str) -> bool:
    """FR-011 safety guard: a live write is allowed ONLY into demo-scoped objects.

    True iff both the schema and table carry the demo marker (prefix or suffix), so
    a stray ``demo load`` can never write into a real ``silver``/``gold`` table.
    """

    def _scoped(name: str) -> bool:
        return name.startswith("demo_") or DEMO_MARKER in name

    return _scoped(schema) and _scoped(table)


def run_load(args) -> int:
    """Offline: report the skip reason (exit 0). Live: write demo-scoped tables."""
    dsn = _resolve_dsn(args)

    if dsn is None:
        print(
            "demo load: no DSN configured -- offline mode. "
            "Nothing to load; the offline legs (Source/Mapping/Silver) still reach "
            "pass. To exercise the live leg, set a local Postgres DSN "
            "(--dsn postgresql://... or the same env vars retail validate uses)."
        )
        return 0

    # A DSN now resolves (post-#350 the workspace `.env` reaches here), but the
    # live leg needs psycopg2. Without `seshat-bi[db]`, `load_demo_scoped` ->
    # psycopg2 would raise; the portable operating contract requires an
    # enable-step message, never a traceback. ATTEMPT THE ACTUAL IMPORT (not just
    # find_spec): a package that is discoverable but unimportable -- e.g. its
    # native libpq is missing -- must also degrade here, exactly as the real
    # import in demo.live would fail. Check psycopg2 SPECIFICALLY (not the
    # ANALYTICS_DB_ENGINE-selected driver): this leg is Postgres-only, and an
    # explicit --dsn resolves before the engine gate, so a non-Postgres engine
    # export must not misdirect the check.
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        print(
            "demo load: a DSN is configured but psycopg2 is not available "
            "-- offline mode. Install it with:  pip install 'seshat-bi[db]'  "
            "then re-run to exercise the live leg."
        )
        return 0

    # Live leg: refuse to write into non-demo-scoped objects (FR-011).
    schema = f"gold{DEMO_MARKER}"
    fact_table = f"fct_order_line{DEMO_MARKER}"
    if not target_is_demo_scoped(schema, fact_table):  # pragma: no cover - guard
        print("error: refusing to load into non-demo-scoped objects (FR-011)")
        return 1

    # The actual idempotent write happens against a lazily-imported driver; kept
    # thin here and covered by a fixture-writer test (no real DB required in CI).
    from .live import load_demo_scoped

    load_demo_scoped(dsn, schema=schema, marker=DEMO_MARKER)
    print(f"demo load: wrote demo-scoped sample into {schema} (idempotent)")
    return 0
