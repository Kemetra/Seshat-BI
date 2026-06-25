-- 0003_create_silver_retail_store_sales.sql
-- Build silver.retail_store_sales (typed/cleaned transaction fact) from
-- bronze.retail_store_sales (the dirty Kaggle "retail store sales" CSV, training DB).
--
-- Medallion: bronze = faithful TEXT landing (retained); silver = typed/cleaned flat
-- table; gold (0004) = Kimball star. Power BI reads gold, not silver.
--
-- Grain: one retail transaction. PK = (transaction_id). 12,575 bronze rows.
-- Idempotent: DROP+CREATE in one transaction; safe to re-run after a bronze reload.
--
-- Cleaning rules from the APPROVED mappings/retail_store_sales/ (gate CLEARED
-- 2026-06-25, Q1-Q4 answered). Decisions baked in below are annotated. No Arabic, no
-- mojibake, no junk-filter list, no business rollup, no returns (RC8 N/A -- the data
-- owner confirmed returns live in a separate figure). ASCII only; UTF-8 no BOM.

SET client_encoding TO 'UTF8';

BEGIN;

CREATE SCHEMA IF NOT EXISTS silver;

DROP TABLE IF EXISTS silver.retail_store_sales;

CREATE TABLE silver.retail_store_sales AS
WITH src AS (
  -- TRIM every text column up front (kills whitespace-variant phantom distincts).
  SELECT
    trim(transaction_id)   AS transaction_id,
    trim(customer_id)      AS customer_id,
    trim(category)         AS category,
    trim(item)             AS item,
    trim(price_per_unit)   AS price_per_unit,
    trim(quantity)         AS quantity,
    trim(total_spent)      AS total_spent,
    trim(payment_method)   AS payment_method,
    trim(location)         AS location,
    trim(transaction_date) AS transaction_date,
    trim(discount_applied) AS discount_applied
  FROM bronze.retail_store_sales
)
-- No junk-row filter and no zero-value filter: the profile found no junk rows and no
-- zero/negative measures (total_spent 5..410, quantity 1..10). Missing measures are
-- kept as NULL (not dropped) -- a transaction with a blank price/qty is still a real row.
SELECT
  -- identity / keys
  NULLIF(transaction_id, '')                  AS transaction_id,   -- PK (TEXT, TXN_ id)
  NULLIF(customer_id, '')                     AS customer_id,      -- pseudonymous (Q1: KEPT)
  -- product (item is the natural key; category is its 1:1 attribute)
  NULLIF(item, '')                            AS item,             -- 9.65% NULL -> -1 member in gold (Q4)
  NULLIF(category, '')                        AS category,
  -- measures (RC7: money/qty -> exact NUMERIC; '' -> NULL via NULLIF)
  NULLIF(price_per_unit, '')::numeric(12,2)   AS price_per_unit,
  NULLIF(quantity, '')::numeric(12,2)         AS quantity,         -- landed as float (10.0); NUMERIC
  NULLIF(total_spent, '')::numeric(12,2)      AS total_spent,      -- = price*qty on 100% of complete rows
  -- transaction attributes
  NULLIF(payment_method, '')                  AS payment_method,
  NULLIF(location, '')                        AS location,
  NULLIF(transaction_date, '')::date          AS transaction_date, -- RC7: date -> DATE
  -- discount flag: blank = UNKNOWN -> NULL (Q2: do NOT coerce blank to False).
  -- Cast the explicit True/False to boolean; blank/other stays NULL.
  CASE lower(NULLIF(discount_applied, ''))
    WHEN 'true'  THEN TRUE
    WHEN 'false' THEN FALSE
    ELSE NULL
  END                                         AS discount_applied
FROM src;

-- No sentinel UPDATEs: the missing item is handled by the gold -1 unknown member
-- (Q4), not a silver text sentinel; measure NULLs stay NULL (fact NULLs, not grouped).

-- PK can be DECLARED here but is UNVERIFIED-UNTIL-APPLIED: transaction_id was unique on
-- the LANDED data (12,575 = 12,575, 0 null); RC2 requires re-proving it on the
-- TRANSFORMED rows. The live retail-validate run (V-RC2) is the proof.
ALTER TABLE silver.retail_store_sales ADD PRIMARY KEY (transaction_id);

-- supporting indexes for the common gold slice paths
CREATE INDEX idx_silver_rss_date     ON silver.retail_store_sales (transaction_date);
CREATE INDEX idx_silver_rss_customer ON silver.retail_store_sales (customer_id);
CREATE INDEX idx_silver_rss_item     ON silver.retail_store_sales (item);

COMMIT;
