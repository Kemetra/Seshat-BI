"""#417: defense-in-depth guard -- a silver/gold migration must never WRITE Bronze.

The existing-bronze source ADAPTER is read-only (proven by
``test_existing_bronze_mode``: ``load_csv`` never runs). This guard extends that
guarantee to the WHOLE run: in existing-bronze mode, a to-be-applied
silver/gold migration that WRITES to Bronze (a layering violation) fails closed
before it can mutate the customer's pre-existing Bronze.

The correctness that matters lives in the pure predicate ``_targets_bronze_write``:
it must fire on a Bronze WRITE (the target of DDL/DML) and MUST NOT fire on a
legitimate Bronze READ (``FROM``/``JOIN bronze.<t>`` -- the medallion flow
itself). These unit tests pin that read-vs-write distinction exhaustively.
"""

from __future__ import annotations

import pytest
from tower_bi_orchestration.assets.bronze_guard import _targets_bronze_write

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# WRITES to bronze -> True (the layering violation the guard exists to catch)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "sql",
    [
        "CREATE TABLE bronze.orders (id int);",
        "create table if not exists bronze.orders (id int);",
        "DROP TABLE bronze.orders;",
        "DROP TABLE IF EXISTS bronze.orders;",
        "ALTER TABLE bronze.orders ADD COLUMN x int;",
        "TRUNCATE bronze.orders;",
        "TRUNCATE TABLE bronze.orders;",
        "INSERT INTO bronze.orders (id) VALUES (1);",
        "insert into bronze.orders select * from staging;",
        "UPDATE bronze.orders SET id = 2;",
        "DELETE FROM bronze.orders WHERE id = 1;",
        "CREATE SCHEMA bronze;",
        "CREATE SCHEMA IF NOT EXISTS bronze;",
        "COPY bronze.orders FROM STDIN;",
        "CREATE VIEW bronze.v AS SELECT 1;",
        'DROP TABLE "bronze"."orders";',
        # newline / extra whitespace between keywords must still trip
        "CREATE\n  TABLE\n  bronze.orders (id int);",
        # SELECT ... INTO bronze.x (target follows INTO)
        "SELECT * INTO bronze.snapshot FROM silver.orders;",
        # H1: schema-level DDL -- the schema ITSELF is the target (DROP SCHEMA
        # bronze CASCADE is the single most destructive bronze write).
        "DROP SCHEMA bronze CASCADE;",
        "DROP SCHEMA IF EXISTS bronze CASCADE;",
        "ALTER SCHEMA bronze RENAME TO bronze_old;",
        "ALTER SCHEMA bronze OWNER TO app;",
        # H3: the Postgres ONLY modifier must not defeat DML detection.
        "TRUNCATE ONLY bronze.orders;",
        "TRUNCATE TABLE ONLY bronze.orders;",
        "UPDATE ONLY bronze.orders SET id = 1;",
        "DELETE FROM ONLY bronze.orders;",
        # ALTER TABLE ONLY bronze.x (pg_dump output) -- ONLY in the DDL position too
        "ALTER TABLE ONLY bronze.orders ADD COLUMN x int;",
        "ALTER TABLE ONLY bronze.orders DROP COLUMN x;",
        # MERGE writes bronze too.
        "MERGE INTO bronze.orders USING src ON src.id = bronze.orders.id "
        "WHEN MATCHED THEN UPDATE SET id = src.id;",
        # a temp/materialized bronze relation is still a bronze write
        "CREATE MATERIALIZED VIEW bronze.mv AS SELECT 1;",
        # CREATE OR REPLACE VIEW targeting bronze (codex review P1)
        "CREATE OR REPLACE VIEW bronze.v AS SELECT 1;",
        # CREATE [UNIQUE] INDEX ... ON bronze.<rel> -- target follows ON
        "CREATE INDEX ix ON bronze.orders (id);",
        "CREATE UNIQUE INDEX ix ON bronze.orders (id);",
        "CREATE INDEX CONCURRENTLY ix ON bronze.orders (id);",
        "CREATE INDEX IF NOT EXISTS ix ON bronze.orders (id);",
        'CREATE INDEX ix ON "bronze"."orders" (id);',
    ],
)
def test_bronze_write_is_detected(sql: str) -> None:
    assert _targets_bronze_write(sql) is True


# --------------------------------------------------------------------------- #
# READS of bronze -> False (the normal medallion flow -- must NOT trip)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "sql",
    [
        # a silver migration reading FROM bronze -- the load-bearing negative
        "CREATE TABLE silver.orders AS SELECT * FROM bronze.orders;",
        "create table silver.orders as select id from bronze.orders where id > 0;",
        "INSERT INTO silver.orders SELECT * FROM bronze.orders;",
        "SELECT * FROM bronze.orders;",
        "SELECT s.id FROM silver.orders s JOIN bronze.orders b ON s.id = b.id;",
        "WITH src AS (SELECT * FROM bronze.orders) SELECT * FROM src;",
        "CREATE VIEW gold.v AS SELECT * FROM bronze.orders;",
        # bronze only in a comment must NOT trip
        "-- reads FROM bronze.orders\nCREATE TABLE silver.orders (id int);",
        "/* stages bronze.orders */ CREATE TABLE silver.orders (id int);",
        "-- DELETE FROM bronze.orders (documented, not executed)\nSELECT 1;",
        # writes that target silver/gold, not bronze
        "CREATE TABLE silver.orders (id int);",
        "TRUNCATE gold.fct_sales;",
        "CREATE SCHEMA silver;",
        # a table whose NAME merely contains 'bronze' as a substring is not the
        # bronze schema (word boundary): silver.bronze_snapshot is a silver write
        "CREATE TABLE silver.bronze_snapshot (id int);",
        # H2: an UNQUALIFIED CREATE ... AS SELECT reading bronze -- staging via a
        # temp table is the normal medallion flow and must NOT be flagged. The
        # object-modifier run must not crawl through the SELECT body into
        # `FROM bronze.x`.
        "CREATE TEMP TABLE tmp AS SELECT id FROM bronze.orders;",
        "CREATE TEMP TABLE tmp_ids AS SELECT DISTINCT customer_id FROM bronze.orders;",
        "CREATE VIEW v AS SELECT id FROM bronze.orders;",
        "CREATE MATERIALIZED VIEW mv AS SELECT id FROM bronze.orders;",
        # writes that target silver/gold while READING bronze (the medallion flow)
        "DELETE FROM silver.x USING bronze.y WHERE silver.x.id = bronze.y.id;",
        "UPDATE silver.x SET n = b.n FROM bronze.y b WHERE silver.x.id = b.id;",
        "MERGE INTO silver.x USING bronze.y ON silver.x.id = bronze.y.id "
        "WHEN MATCHED THEN UPDATE SET n = bronze.y.n;",
        # CREATE OR REPLACE VIEW that READS bronze (target is unqualified `v`)
        "CREATE OR REPLACE VIEW v AS SELECT id FROM bronze.orders;",
        # CREATE INDEX on a SILVER table -- ON silver.x, bronze only read in a
        # partial-index predicate must not trip (bronze not the index target)
        "CREATE INDEX ix ON silver.orders (id);",
        # a JOIN's `ON bronze.c...` in a plain SELECT is a read, never a CREATE INDEX
        "SELECT * FROM silver.a JOIN bronze.b ON bronze.b.id = silver.a.id;",
        # adding ONLY to the DDL modifier run must NOT false-positive a
        # `SELECT ... FROM ONLY bronze.x` read (ONLY is legal after FROM too)
        "SELECT * FROM ONLY bronze.orders;",
        "SELECT id FROM ONLY bronze.orders WHERE id > 0;",
    ],
)
def test_bronze_read_is_not_flagged(sql: str) -> None:
    assert _targets_bronze_write(sql) is False


def test_empty_and_trivial_sql_is_not_flagged() -> None:
    assert _targets_bronze_write("") is False
    assert _targets_bronze_write("SELECT 1;") is False
