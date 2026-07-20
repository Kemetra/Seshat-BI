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

from . import DEMO_MARKER
from ._dsn import resolve_dsn as _resolve_dsn  # shared with `demo run` (#376)

__all__ = ["run_load", "target_is_demo_scoped", "_resolve_dsn"]


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

    try:
        load_demo_scoped(dsn, schema=schema, marker=DEMO_MARKER)
    except Exception as exc:
        # The live leg's psycopg2.connect had no local handler, so an unreachable
        # DSN surfaced as a raw traceback -- and psycopg2 reformats the DSN into
        # its own error text (host/user/password), so credentials could leak
        # (#379). Route the message through _redact_dsn and exit non-zero: a load
        # the user asked for failed; do not silently hide it, and never echo the
        # DSN. `_redact_dsn` is purpose-built for the psycopg2 reformatted shape.
        import sys

        from seshat.cli import _redact_dsn

        print(f"demo load: live leg failed -- {_redact_dsn(exc, dsn)}", file=sys.stderr)
        return 1
    print(f"demo load: wrote demo-scoped sample into {schema} (idempotent)")
    return 0
