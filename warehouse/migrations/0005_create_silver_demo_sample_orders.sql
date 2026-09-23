-- 0005_create_silver_demo_sample_orders.sql
-- Build silver.demo_sample_orders (typed/cleaned order-line fact) from the demo
-- sample source (spec 083 local demo harness; GENERIC invented data, not C086).
--
-- Medallion: bronze = faithful TEXT landing; silver = typed/cleaned flat table;
-- no demo gold star is committed yet (0006+ are the finance GL tables). Power BI
-- reads gold, not silver.
--
-- Grain: one order line. PK = (order_id), enforced by the follow-up migration
-- 0011_enforce_silver_demo_sample_orders_pk.sql. 24 sample rows.
-- Idempotent: DROP+CREATE in one transaction; safe to re-run.
--
-- Cleaning rules from the APPROVED mappings/demo_sample_orders/ (gate CLEARED).
-- RC7 type discipline: quantity -> INTEGER; unit_price/line_total -> exact NUMERIC
-- (money); order_id kept TEXT (alphanumeric id). ASCII only; UTF-8 no BOM.

SET client_encoding TO 'UTF8';

BEGIN;

CREATE SCHEMA IF NOT EXISTS silver;

DROP TABLE IF EXISTS silver.demo_sample_orders;

CREATE TABLE silver.demo_sample_orders AS
WITH src AS (
    SELECT
        order_id,
        order_date,
        product_name,
        product_category,
        quantity,
        unit_price,
        line_total,
        store_location,
        payment_method
    FROM bronze.demo_sample_orders
)
SELECT
    order_id::text                       AS order_id,        -- RC7: alphanumeric id kept TEXT
    order_date::date                     AS order_date,
    product_name::text                   AS product_name,
    product_category::text               AS product_category,
    quantity::integer                    AS quantity,        -- RC7: qty exact integer
    unit_price::numeric(12, 2)           AS unit_price,      -- RC7: money exact NUMERIC
    line_total::numeric(12, 2)           AS line_total,      -- RC7: money exact NUMERIC
    store_location::text                 AS store_location,
    payment_method::text                 AS payment_method
FROM src;

COMMIT;
