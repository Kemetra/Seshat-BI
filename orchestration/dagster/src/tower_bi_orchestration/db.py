"""The live-database boundary (research D5).

DSN resolution reuses the main package's ``seshat.validate.resolve_dsn`` (one
resolution path: ``DATABASE_URL`` or the ``ANALYTICS_DB_*`` set from the
git-ignored ``.env``). psycopg2 is imported LAZILY inside the helpers so the
definitions-load smoke and every fixture test run without a driver.

A missing DSN is a DEFERRED BOUNDARY: callers record it as a concrete
blocking reason -- never a fabricated success (Principle VIII).
"""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

_IDENT_RE = re.compile(r"[^a-z0-9_]")

DEFERRED_BOUNDARY = "no database credentials (deferred boundary)"


def resolve_dsn() -> str | None:
    from seshat.validate import resolve_dsn as _resolve

    return _resolve(dict(os.environ))


def _connect(dsn: str):
    import psycopg2  # lazy: only a live run needs the driver

    return psycopg2.connect(dsn)


def _ident(name: str) -> str:
    cleaned = _IDENT_RE.sub("_", name.strip().lower()) or "col"
    return cleaned if not cleaned[0].isdigit() else f"c_{cleaned}"


def apply_sql_file(dsn: str, sql_path: Path) -> None:
    """Apply one committed idempotent migration file."""
    sql_text = Path(sql_path).read_text(encoding="utf-8")
    with _connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_text)


def load_csv(dsn: str, table: str, csv_path: Path) -> int:
    """Land a raw CSV into ``bronze.<table>`` (all TEXT columns; idempotent
    drop-and-reload of the raw landing). Returns rows loaded."""
    csv_path = Path(csv_path)
    with csv_path.open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    columns = ", ".join(f"{_ident(col)} TEXT" for col in header)
    target = f"bronze.{_ident(table)}"
    with _connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS bronze")
            cur.execute(f"DROP TABLE IF EXISTS {target}")
            cur.execute(f"CREATE TABLE {target} ({columns})")
            with csv_path.open(encoding="utf-8") as data:
                cur.copy_expert(
                    f"COPY {target} FROM STDIN WITH (FORMAT csv, HEADER true)", data
                )
            cur.execute(f"SELECT COUNT(*) FROM {target}")
            return int(cur.fetchone()[0])
