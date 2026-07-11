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

    Returns None when no DSN is configured (the honest offline case).
    """
    explicit = getattr(args, "dsn", None)
    if explicit:
        return explicit
    try:
        from seshat.validate import resolve_dsn
    except Exception:
        return None
    try:
        return resolve_dsn()
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
    Path(getattr(args, "repo", "."))
    dsn = _resolve_dsn(args)

    if dsn is None:
        print(
            "demo load: no DSN configured -- offline mode. "
            "Nothing to load; the offline legs (Source/Mapping/Silver) still reach "
            "pass. To exercise the live leg, set a local Postgres DSN "
            "(--dsn postgresql://... or the same env vars retail validate uses)."
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
