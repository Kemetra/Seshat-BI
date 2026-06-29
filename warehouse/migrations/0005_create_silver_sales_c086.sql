-- 0005_create_silver_sales_c086.sql
-- Build silver.sales_c086 (typed/cleaned line-item fact) from bronze.sales_c086_raw.
--
-- SUPERSEDES 0001_create_silver_sales_c086.sql. This is the authoritative silver
-- build for the FINAL approved map (mappings/sales_c086/, gate CLEARED via PR #86,
-- 2026-06-29). It differs from 0001 by design:
--   * 2 measures only: Gross_Sales + Quantity (net/tax/discount dropped -- RC9 deviation).
--   * Generated surrogate PK Sale_SK; natural key (Invoice_No, Line_No) kept SILVER-ONLY
--     for the uniqueness/dedup proof (NOT exposed to gold).
--   * buyer -> Product_Purchaser (its own gold dim 0006), not a folded attribute.
--   * customer 'C086' (site code) -> Customer_ID_Clean = 'WALK_IN' (value remap).
--   * billing English label keyed on the CODE (no Arabic literals in this file).
--   * NO business_segment rollup (none analyst-supplied -- RC11).
--   * PascalCase column names with '_' by logic.
-- Both 0005 and 0006 are DROP+CREATE in one txn -> safe to re-run; latest build wins.
--
-- Grain: invoice LINE ITEM. 249,106 bronze -> 246,916 silver. Save UTF-8 without BOM.

SET client_encoding TO 'UTF8';

BEGIN;

CREATE SCHEMA IF NOT EXISTS silver;

DROP TABLE IF EXISTS silver.sales_c086;

CREATE TABLE silver.sales_c086 AS
WITH src AS (
  -- Step 1: TRIM every text column up front (kills whitespace-variant phantom distincts).
  SELECT
    trim(material)         AS material,
    trim(material_desc)    AS material_desc,
    trim(quantity)         AS quantity,
    trim(gross_sales)      AS gross_sales,
    trim(reference_no)     AS reference_no,
    trim(billing_document) AS billing_document,
    trim(item_no)          AS item_no,
    trim(date)             AS date,
    trim(billing_type_2)   AS billing_type_2,
    trim(customer)         AS customer,
    trim(customer_name)    AS customer_name,
    trim(personel_number)  AS personel_number,
    trim(person_name)      AS person_name,
    trim(position)         AS position,
    trim(buyer)            AS buyer,
    trim(division)         AS division,
    trim(category)         AS category,
    trim(subcategory)      AS subcategory,
    trim(segment)          AS segment,
    trim(brand)            AS brand,
    trim(item_cluster)     AS item_cluster,
    trim(site)             AS site,
    trim(site_name)        AS site_name,
    "_source_file",
    "_loaded_at"
  FROM bronze.sales_c086_raw
),
filtered AS (
  SELECT * FROM src
  -- Step 3: junk-division filter runs BEFORE ''->NULL and BEFORE the Division sentinel
  --   (D12 -- a blank-targeting filter must evaluate on the raw blank, or trim(div)=''
  --   matches 0 rows post-substitution and the 3 blank-division rows wrongly survive).
  --   Drops AUX/ARCHIVE/EL EZABY SERVICES/blank = 513 rows.
  WHERE division NOT IN ('AUX', 'ARCHIVE', 'EL EZABY SERVICES', '')
  -- Step 6: zero-value line filter on the NUMERIC cast, not text ('0.0' <> '0').
  --   Drops 1,680 rows. (Overlap with junk filter = 3 rows; net dropped = 2,190.)
  AND NOT (
        NULLIF(quantity, '')::numeric = 0
    AND NULLIF(gross_sales, '')::numeric = 0
  )
)
SELECT
  -- ---- natural key: SILVER-ONLY (the uniqueness/dedup proof; NOT carried to gold) ----
  NULLIF(billing_document, '')               AS "Invoice_No",   -- TEXT, leading zeros
  NULLIF(item_no, '')::smallint              AS "Line_No",      -- ordinal -> SMALLINT
  -- ---- product (-> dim_product) ----
  material                                   AS "Product_ID",   -- TEXT, leading zeros
  -- Step 2: mojibake cleanup via positive whitelist -- keep ASCII (32-126), Arabic
  --   (1569-1791), and pharma dosing micro signs (181, 924, 956); strip the rest
  --   (covers box-drawing/symbol families, e.g. the observed 'ADULT[box]').
  regexp_replace(
    material_desc,
    '[^' || chr(32) || '-' || chr(126)
         || chr(181) || chr(924) || chr(956)
         || chr(1569) || '-' || chr(1791) || ']',
    '', 'g'
  )                                          AS "Product_Name",
  brand                                      AS "Brand",
  category                                   AS "Category",
  subcategory                                AS "Subcategory",
  segment                                    AS "Segment",
  division                                   AS "Division",
  item_cluster                               AS "Cluster",
  -- ---- customer (-> dim_customer) ----
  NULLIF(customer, '')                       AS "Customer_ID",  -- raw landed id (TEXT)
  -- Q6 VALUE REMAP: the site code 'C086' in the customer field (85,911 rows) is a
  --   walk-in/cash marker, not a customer. Remap to 'WALK_IN' (a meaningful member,
  --   distinct from the dim -1 unknown). dim_customer (0006) is keyed on this column.
  CASE WHEN NULLIF(customer, '') = 'C086' THEN 'WALK_IN'
       ELSE NULLIF(customer, '') END         AS "Customer_ID_Clean",
  customer_name                              AS "Customer_Name", -- B2B company name (not PII)
  -- ---- salesperson (-> dim_salesperson) -- staff names, KPI use (not PII) ----
  -- NULLIF so a blank id becomes NULL -> excluded from the dim -> fact COALESCEs to -1
  -- (without NULLIF a '' id would form a phantom dim member and steal the -1 rows).
  NULLIF(personel_number, '')                AS "Salesperson_ID",
  person_name                                AS "Salesperson_Name",
  position                                   AS "Salesperson_Position",
  -- ---- product purchaser (-> dim_product_purchaser) -- the counter agent ----
  NULLIF(buyer, '')                          AS "Product_Purchaser",  -- NULLIF: blank -> -1, not a phantom member
  -- ---- billing type (-> dim_billing_type) ----
  billing_type_2                             AS "Billing_Type_Code",  -- Z-code, the join key
  -- Q1: English label keyed on the CODE (RC10). All 10 codes enumerated; ELSE loud sentinel.
  CASE billing_type_2
    WHEN 'FP'  THEN 'Credit Sale'
    WHEN 'Z1'  THEN 'Cash Sale'
    WHEN 'Z3'  THEN 'Delivery'
    WHEN 'Z7'  THEN 'Delivery - Credit'
    WHEN 'Z9'  THEN 'Pick-Up Order'
    WHEN 'Z4'  THEN 'Cash Return'
    WHEN 'Z5'  THEN 'Credit Return'
    WHEN 'Z6'  THEN 'Delivery Return'
    WHEN 'Z8'  THEN 'Delivery - Credit Return'
    WHEN 'Z10' THEN 'Pick-Up Order Return'
    ELSE 'UNMAPPED'
  END                                        AS "Billing_Type_Label",
  -- Step 7: is_return from the AUTHORITATIVE code (RC8), never the measure sign.
  (billing_type_2 IN ('Z4', 'Z5', 'Z6', 'Z8', 'Z10')) AS "Is_Return",
  -- ---- branch (-> dim_branch; single store today, kept for multi-store future) ----
  site                                       AS "Branch_ID",
  site_name                                  AS "Branch_Name",
  -- ---- date (-> dim_date FK in gold) ----
  NULLIF(date, '')::date                     AS "Sale_Date",
  -- ---- degenerate dim on the fact ----
  NULLIF(reference_no, '')                   AS "Invoice",       -- per-invoice reference
  -- ---- measures (ONLY 2 kept -- RC9 deviation) ----
  NULLIF(gross_sales, '')::numeric(18,2)     AS "Gross_Sales",
  NULLIF(quantity, '')::numeric(18,3)        AS "Quantity",      -- fractional (part-packs); negatives = returns
  -- ---- lineage (silver-only) ----
  "_source_file",
  "_loaded_at"
FROM filtered;

-- Step 8: sentinel UPDATEs for grouping-dim text NULLs (verified 0 collision with real
--   values). Facts stay NULL. Salesperson_ID (the key) -> NULL stays NULL so it routes
--   to the gold -1 unknown member; its NAME/role get the sentinel for clean grouping.
UPDATE silver.sales_c086 SET "Brand"                = 'UNKNOWN'      WHERE "Brand"                IS NULL OR "Brand"                = '';
UPDATE silver.sales_c086 SET "Cluster"              = 'UNKNOWN'      WHERE "Cluster"              IS NULL OR "Cluster"              = '';
UPDATE silver.sales_c086 SET "Category"             = 'UNCLASSIFIED' WHERE "Category"             IS NULL OR "Category"             = '';
UPDATE silver.sales_c086 SET "Subcategory"          = 'UNCLASSIFIED' WHERE "Subcategory"          IS NULL OR "Subcategory"          = '';
UPDATE silver.sales_c086 SET "Segment"              = 'UNCLASSIFIED' WHERE "Segment"              IS NULL OR "Segment"              = '';
UPDATE silver.sales_c086 SET "Division"             = 'UNCLASSIFIED' WHERE "Division"             IS NULL OR "Division"             = '';
UPDATE silver.sales_c086 SET "Salesperson_Name"     = 'UNKNOWN'      WHERE "Salesperson_Name"     IS NULL OR "Salesperson_Name"     = '';
UPDATE silver.sales_c086 SET "Salesperson_Position" = 'UNKNOWN'      WHERE "Salesperson_Position" IS NULL OR "Salesperson_Position" = '';

-- Generated surrogate PK Sale_SK over the POST-FILTER rows (1..246,916). Added as an
-- IDENTITY column AFTER load so it numbers the surviving rows with no gaps.
ALTER TABLE silver.sales_c086 ADD COLUMN "Sale_SK" bigint GENERATED BY DEFAULT AS IDENTITY;
ALTER TABLE silver.sales_c086 ADD PRIMARY KEY ("Sale_SK");

-- UNVERIFIED-UNTIL-APPLIED: the natural key (Invoice_No, Line_No) uniqueness can only be
-- PROVEN on the transformed rows by the live dry-run (the deferred DB-write seam). This
-- unique index ASSERTS it; if a double-load made it non-unique, applying this FAILS LOUD
-- (which is the desired behavior -- the surrogate PK alone could not catch that).
CREATE UNIQUE INDEX uq_silver_c086_natural_key ON silver.sales_c086 ("Invoice_No", "Line_No");

-- supporting indexes for the common gold-build / Power BI slice paths.
CREATE INDEX idx_silver_c086_sale_date   ON silver.sales_c086 ("Sale_Date");
CREATE INDEX idx_silver_c086_customer    ON silver.sales_c086 ("Customer_ID_Clean");
CREATE INDEX idx_silver_c086_product     ON silver.sales_c086 ("Product_ID");

COMMIT;
