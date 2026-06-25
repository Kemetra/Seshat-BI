"""Load a CSV source into the bronze layer (raw text + lineage).

CSV sibling of `load_bronze.py` (which loads C086 Excel). Same medallion contract:
bronze = faithful landing -- every source column as TEXT, plus lineage columns
`_source_file` and `_loaded_at`. No cleaning or typing here; that is the silver
layer's job. Empty source fields land as empty strings `''` (not NULL): the row
buffer is written with csv.QUOTE_ALL so every field, including blanks, is quoted,
and COPY lands a quoted-empty as a zero-length string -- preserving the dirtiness
(an unquoted empty would become NULL under COPY's default null string).

Idempotent: the table is rebuilt (DROP+CREATE) and the file's prior rows are
cleared before load, so a re-run replaces rather than duplicates. Loads via
PostgreSQL COPY through psycopg2 (the `db` extra), fast over TLS.

Secrets are never hardcoded. The DB connection (host/port/user/password) is read
from `doctl` at runtime; pass the cluster id and target database via flags or env.

Usage:
    python load_bronze_csv.py --cluster-id <id> --database training \\
        --csv data/raw/kaggle-retail-dirty/retail_store_sales.csv \\
        --table bronze.retail_store_sales
"""

from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import os
import re
import subprocess
import sys


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


def get_conn_params(cluster_id: str, database: str) -> dict:
    """Read connection details from doctl at runtime (no secrets in source)."""
    out = subprocess.run(
        ["doctl", "databases", "connection", cluster_id, "-o", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    info = json.loads(out.stdout)
    c = info[0] if isinstance(info, list) else info
    return {
        "host": c["host"],
        "port": int(c["port"]),
        "user": c["user"],
        "password": c["password"],
        "dbname": database,
        "sslmode": "require",
    }


def connect(cluster_id: str, database: str):
    # Lazy-load the optional driver so `--help` and the pure functions (used in
    # tests / static envs without the `db` extra) do not crash at import time.
    try:
        import psycopg2
    except ImportError:
        sys.exit(
            "psycopg2 not installed (the live-DB boundary is optional). "
            "Enable it with: pip install 'retail[db]'"
        )
    conn = psycopg2.connect(**get_conn_params(cluster_id, database))
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SET client_encoding TO 'UTF8';")
    return conn


def norm_headers(headers: list[str]) -> list[str]:
    """Deterministic snake_case; collision-safe (duplicate names get _N suffix).

    A GENERATED suffix name is itself reserved (added to `seen` and `used`), so a
    later real header that matches a generated name (e.g. `["A","A","A_2"]` -> a,
    a_2(gen), a_2(real)) gets a fresh suffix instead of silently duplicating
    (2026-06-25 Codex review #5). The result is always all-unique.
    """
    counts: dict[str, int] = {}
    used: set[str] = set()
    out: list[str] = []
    for h in headers:
        s = re.sub(r"[^\w]+", "_", (h or "").strip().lower(), flags=re.UNICODE)
        s = re.sub(r"_+", "_", s).strip("_") or "col"
        candidate = s
        # bump the suffix until the candidate is genuinely unused (covers a real
        # header colliding with a previously-generated suffix name)
        while candidate in used:
            counts[s] = counts.get(s, 1) + 1
            candidate = f"{s}_{counts[s]}"
        counts.setdefault(s, 1)
        used.add(candidate)
        out.append(candidate)
    return out


def read_csv_headers(path: str) -> list[str]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        hdr = next(csv.reader(f))
    return norm_headers(hdr)


def create_objects(conn, table: str, cols: list[str]) -> None:
    schema = table.split(".", 1)[0]
    with conn.cursor() as cur:
        for sch in ("bronze", "silver", "gold"):
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {sch};")
        coldefs = ",\n  ".join(f'"{c}" TEXT' for c in cols)
        cur.execute(f"DROP TABLE IF EXISTS {table};")  # rebuildable bronze layer
        cur.execute(f"""
            CREATE TABLE {table} (
              {coldefs},
              _source_file TEXT NOT NULL,
              _loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
    log(
        f"schemas bronze/silver/gold ready; {table} = {len(cols)} cols + lineage "
        f"(schema={schema})"
    )


def csv_rows(path: str):
    """Yield each data row as faithful text (None -> '')."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        r = csv.reader(f)
        next(r)  # skip header
        for row in r:
            yield ["" if v is None else str(v) for v in row]


def count_csv_records(path: str) -> int:
    """Data records (header excluded) counted by the CSV parser, NOT physical lines.

    A quoted field with an embedded newline is ONE record across several physical
    lines; counting raw lines over-counts and produces a false reconcile FAIL
    (2026-06-25 Codex review #8). Uses the same parser COPY consumes.
    """
    with open(path, newline="", encoding="utf-8-sig") as f:
        r = csv.reader(f)
        next(r, None)  # header
        return sum(1 for _ in r)


def csv_buffer(path: str, ncols: int, source_file: str) -> tuple[io.StringIO, int]:
    buf = io.StringIO()
    # QUOTE_ALL: every field quoted, so an empty source field becomes "" and COPY
    # lands a zero-length string (not NULL) -- faithful bronze landing.
    w = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    loaded_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    n = 0
    for i, row in enumerate(csv_rows(path), start=1):
        # FAIL LOUD on a ragged row wider than the header: silently dropping the
        # extra cells would corrupt the faithful-landing contract (an unescaped
        # delimiter / extra column would shift data) (2026-06-25 Codex review #6).
        if len(row) > ncols:
            raise ValueError(
                f"{source_file}: ragged row {i} has {len(row)} fields but the "
                f"header declares {ncols} columns; refusing to truncate source "
                f"data (faithful bronze). Fix the source row or the header."
            )
        row = list(row) + [""] * (
            ncols - len(row)
        )  # short rows padded (dirty-faithful)
        w.writerow(row + [source_file, loaded_at])
        n += 1
    buf.seek(0)
    return buf, n


def load_csv(conn, table: str, cols: list[str], path: str) -> None:
    if not os.path.exists(path):
        sys.exit(f"file not found: {path}")
    fname = os.path.basename(path)
    quoted = ", ".join(f'"{c}"' for c in cols) + ', "_source_file", "_loaded_at"'
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {table} WHERE _source_file = %s;", (fname,))
        log(f"{fname}: cleared prior rows; reading + copying...")
        buf, n = csv_buffer(path, len(cols), fname)
        cur.copy_expert(
            f"COPY {table} ({quoted}) FROM STDIN "
            f"WITH (FORMAT csv, QUOTE '\"', ENCODING 'UTF8')",
            buf,
        )
        log(f"{fname}: COPY done, {n} rows sent")
    reconcile(conn, table, path, fname)


def reconcile(conn, table: str, path: str, fname: str) -> None:
    file_rows = count_csv_records(path)  # CSV records, not physical lines (#8)
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE _source_file = %s;", (fname,))
        db_rows = cur.fetchone()[0]
    ok = file_rows == db_rows
    log(
        f"RECONCILE {fname}: csv={file_rows} db={db_rows} -> {'PASS' if ok else 'FAIL'}"
    )
    if not ok:
        sys.exit(f"reconcile FAILED for {fname}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Load a CSV source into bronze (all-TEXT)."
    )
    ap.add_argument("--cluster-id", default=os.environ.get("DO_DB_CLUSTER_ID"))
    ap.add_argument("--database", default=os.environ.get("ANALYTICS_DB_NAME"))
    ap.add_argument("--csv", required=True, help="path to the source CSV")
    ap.add_argument(
        "--table", required=True, help="target table, e.g. bronze.retail_store_sales"
    )
    a = ap.parse_args()

    if not a.cluster_id:
        sys.exit("missing --cluster-id (or DO_DB_CLUSTER_ID env)")
    if not a.database:
        sys.exit("missing --database (or ANALYTICS_DB_NAME env)")

    cols = read_csv_headers(a.csv)
    conn = connect(a.cluster_id, a.database)
    log(f"connected to {a.database}; columns = {cols}")
    create_objects(conn, a.table, cols)
    load_csv(conn, a.table, cols, a.csv)
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {a.table};")
        log(f"TOTAL {a.table} rows: {cur.fetchone()[0]}")
    conn.close()
    log("done")


if __name__ == "__main__":
    main()
