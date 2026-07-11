"""The live-leg DB write for ``retail demo load`` (spec 083, US2).

Isolated here so the offline path (load.py) never imports a driver, and so a test
can exercise the write logic against a fixture ``Writer`` without a real database.
The real driver is imported LAZILY inside ``load_demo_scoped`` only.

Safety: writes ONLY into demo-scoped objects (the caller has already verified the
schema/table names carry the demo marker, FR-011). Idempotent: DROP+CREATE so a
re-run converges to the same rows (FR-004).
"""

from __future__ import annotations

from typing import Protocol


class Writer(Protocol):
    """Minimal DDL/DML sink -- a fixture in tests, a psycopg2 cursor in the CLI."""

    def execute(self, sql: str) -> None: ...


def demo_scoped_ddl(schema: str) -> list[str]:
    """The idempotent DDL statements for the demo-scoped gold objects.

    Pure -- returns the SQL as a list so a test can assert on it without a DB. The
    schema name is caller-supplied and already demo-scoped (FR-011 verified upstream).
    """
    return [
        f"CREATE SCHEMA IF NOT EXISTS {schema}",
        f"DROP TABLE IF EXISTS {schema}.fct_order_line",
        (
            f"CREATE TABLE {schema}.fct_order_line ("
            "order_line_id TEXT NOT NULL, order_date DATE NOT NULL, "
            "product_key TEXT NOT NULL, quantity INTEGER NOT NULL, "
            "unit_price NUMERIC(12,2) NOT NULL, line_total NUMERIC(12,2) NOT NULL)"
        ),
    ]


def apply_ddl(writer: Writer, schema: str) -> None:
    """Apply the demo-scoped DDL via any ``Writer`` (fixture or real cursor)."""
    for stmt in demo_scoped_ddl(schema):
        writer.execute(stmt)


def load_demo_scoped(dsn: str, *, schema: str, marker: str) -> None:
    """Open a real (lazy) psycopg2 connection and apply the demo-scoped DDL.

    Only reached on the live leg after load.py verified the DSN resolved and the
    target is demo-scoped. Not exercised in CI (no live DB); the DDL itself is
    unit-tested via ``apply_ddl`` with a fixture Writer.
    """
    import psycopg2  # lazy: only on a real live run

    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            apply_ddl(cur, schema)
    finally:
        conn.close()
