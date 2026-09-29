"""The live-leg DB write for ``retail demo load`` (spec 083, US2).

Isolated here so the offline path (load.py) never imports a driver, and so a test
can exercise the write logic against a fixture ``Writer`` without a real database.
The real driver is imported LAZILY inside ``load_demo_scoped`` only.

Safety: writes ONLY into demo-scoped objects -- the DDL is built from the SAME
schema/table names the caller verified carry the demo marker (FR-011), so the
guard keys on the identity written. Idempotent: DROP+CREATE so a re-run
converges (FR-004). The leg creates the table shape only; it inserts no rows.
"""

from __future__ import annotations

from typing import Protocol


class Writer(Protocol):
    """Minimal DDL/DML sink -- a fixture in tests, a psycopg2 cursor in the CLI."""

    def execute(self, sql: str) -> None: ...


_DEFAULT_TABLE = "fct_order_line_seshat_demo"


def demo_scoped_ddl(schema: str, table: str = _DEFAULT_TABLE) -> list[str]:
    """The idempotent DDL statements for the demo-scoped gold objects.

    Pure -- returns the SQL as a list so a test can assert on it without a DB. The
    schema and table names are caller-supplied and already demo-scoped (FR-011
    verified upstream on exactly these names).
    """
    return [
        f"CREATE SCHEMA IF NOT EXISTS {schema}",
        f"DROP TABLE IF EXISTS {schema}.{table}",
        (
            f"CREATE TABLE {schema}.{table} ("
            "order_line_id TEXT NOT NULL, order_date DATE NOT NULL, "
            "product_key TEXT NOT NULL, quantity INTEGER NOT NULL, "
            "unit_price NUMERIC(12,2) NOT NULL, line_total NUMERIC(12,2) NOT NULL)"
        ),
    ]


def apply_ddl(writer: Writer, schema: str, table: str = _DEFAULT_TABLE) -> None:
    """Apply the demo-scoped DDL via any ``Writer`` (fixture or real cursor)."""
    for stmt in demo_scoped_ddl(schema, table):
        writer.execute(stmt)


def load_demo_scoped(dsn: str, *, schema: str, table: str = _DEFAULT_TABLE) -> None:
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
            apply_ddl(cur, schema, table)
    finally:
        conn.close()
