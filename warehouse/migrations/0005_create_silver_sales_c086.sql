-- 0005_create_silver_sales_c086.sql
-- Build silver.sales_c086 (typed/cleaned line-item fact) from bronze.sales_c086_raw.
--
-- SUPERSEDES 0001_create_silver_sales_c086.sql. Authoritative silver build for the
-- FINAL approved map (mappings/sales_c086/; map review + approval recorded 2026-07-02
-- in readiness-status.yaml approvals[]. NOTE: this SQL was authored 2026-06-29, AHEAD
-- of that review -- the gate-ordering violation is acknowledged + remediated there).
-- Differs from 0001 by design:
--   * 2 measures only: gross_sales + quantity (net/tax/discount dropped -- RC9 deviation).
--   * Generated surrogate PK sale_sk; natural key (invoice_no, line_no) kept SILVER-ONLY
--     for the uniqueness/dedup proof (NOT exposed to gold).
--   * buyer -> product_purchaser (its own gold dim 0006), not a folded attribute.
--   * customer 'C086' (site code) -> customer_id_clean = 'WALK_IN' (value remap).
--   * billing English label keyed on the CODE (no Arabic literals in this file).
--   * NO business_segment rollup (none analyst-supplied -- RC11).
--
-- Identifiers are snake_case unquoted (rule S1). PascalCase display names
-- (Product_ID, Gross_Sales, ...) are applied LATER in the Power BI model layer, not here.
-- Both 0005/0006 are DROP+CREATE in one txn -> safe to re-run; latest build wins.
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
    _source_file,
    _loaded_at
  FROM bronze.sales_c086_raw
),
filtered AS (
  SELECT * FROM src
  -- Step 3: junk-division filter runs BEFORE ''->NULL and BEFORE the division sentinel
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
  NULLIF(billing_document, '')               AS invoice_no,        -- TEXT, leading zeros
  NULLIF(item_no, '')::smallint              AS line_no,           -- ordinal -> SMALLINT
  -- ---- product (-> dim_product) ----
  material                                   AS product_id,        -- TEXT, leading zeros
  -- Step 2: mojibake cleanup via positive whitelist -- keep ASCII (32-126), Arabic
  --   (1569-1791), and pharma dosing micro signs (181, 924, 956); strip the rest
  --   (covers box-drawing/symbol families, e.g. the observed 'ADULT[box]').
  regexp_replace(
    material_desc,
    '[^' || chr(32) || '-' || chr(126)
         || chr(181) || chr(924) || chr(956)
         || chr(1569) || '-' || chr(1791) || ']',
    '', 'g'
  )                                          AS product_name,
  brand                                      AS brand,
  category                                   AS category,
  subcategory                                AS subcategory,
  segment                                    AS segment,
  division                                   AS division,
  item_cluster                               AS cluster,
  -- ---- customer (-> dim_customer) ----
  NULLIF(customer, '')                       AS customer_id,       -- raw landed id (TEXT)
  -- Q6 VALUE REMAP: the site code 'C086' in the customer field (85,911 rows) is a
  --   walk-in/cash marker, not a customer. Remap to 'WALK_IN' (a meaningful member,
  --   distinct from the dim -1 unknown). dim_customer (0006) is keyed on this column.
  CASE WHEN NULLIF(customer, '') = 'C086' THEN 'WALK_IN'
       ELSE NULLIF(customer, '') END         AS customer_id_clean,
  customer_name                              AS customer_name,     -- B2B company name (not PII)
  -- ---- salesperson (-> dim_salesperson) -- staff names, KPI use (not PII) ----
  -- NULLIF so a blank id becomes NULL -> excluded from the dim -> fact COALESCEs to -1
  -- (without NULLIF a '' id would form a phantom dim member and steal the -1 rows).
  NULLIF(personel_number, '')                AS salesperson_id,
  person_name                                AS salesperson_name,
  position                                   AS salesperson_position,
  -- ---- product purchaser (-> dim_product_purchaser) -- the counter agent ----
  NULLIF(buyer, '')                          AS product_purchaser, -- NULLIF: blank -> -1, not a phantom member
  -- ---- billing type (-> dim_billing_type) ----
  billing_type_2                             AS billing_type_code, -- Z-code, the join key
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
  END                                        AS billing_type_label,
  -- Step 7: is_return from the AUTHORITATIVE code (RC8), never the measure sign.
  (billing_type_2 IN ('Z4', 'Z5', 'Z6', 'Z8', 'Z10')) AS is_return,
  -- ---- branch (-> dim_branch; single store today, kept for multi-store future) ----
  site                                       AS branch_id,
  site_name                                  AS branch_name,
  -- ---- date (-> dim_date FK in gold) ----
  NULLIF(date, '')::date                     AS sale_date,
  -- ---- degenerate dim on the fact ----
  NULLIF(reference_no, '')                   AS invoice,           -- per-invoice reference
  -- ---- measures (ONLY 2 kept -- RC9 deviation) ----
  NULLIF(gross_sales, '')::numeric(18,2)     AS gross_sales,
  NULLIF(quantity, '')::numeric(18,3)        AS quantity,          -- fractional (part-packs); negatives = returns
  -- ---- lineage (silver-only) ----
  _source_file,
  _loaded_at
FROM filtered;

-- Step 8: sentinel UPDATEs for grouping-dim text NULLs (verified 0 collision with real
--   values). Facts stay NULL. salesperson_id (the key) -> NULL stays NULL so it routes
--   to the gold -1 unknown member; its NAME/role get the sentinel for clean grouping.
UPDATE silver.sales_c086 SET brand                = 'UNKNOWN'      WHERE brand                IS NULL OR brand                = '';
UPDATE silver.sales_c086 SET cluster              = 'UNKNOWN'      WHERE cluster              IS NULL OR cluster              = '';
UPDATE silver.sales_c086 SET category             = 'UNCLASSIFIED' WHERE category             IS NULL OR category             = '';
UPDATE silver.sales_c086 SET subcategory          = 'UNCLASSIFIED' WHERE subcategory          IS NULL OR subcategory          = '';
UPDATE silver.sales_c086 SET segment              = 'UNCLASSIFIED' WHERE segment              IS NULL OR segment              = '';
UPDATE silver.sales_c086 SET division             = 'UNCLASSIFIED' WHERE division             IS NULL OR division             = '';
UPDATE silver.sales_c086 SET salesperson_name     = 'UNKNOWN'      WHERE salesperson_name     IS NULL OR salesperson_name     = '';
UPDATE silver.sales_c086 SET salesperson_position = 'UNKNOWN'      WHERE salesperson_position IS NULL OR salesperson_position = '';

-- Generated surrogate PK sale_sk over the POST-FILTER rows (1..246,916). Added as an
-- IDENTITY column AFTER load so it numbers the surviving rows with no gaps.
ALTER TABLE silver.sales_c086 ADD COLUMN sale_sk bigint GENERATED BY DEFAULT AS IDENTITY;
ALTER TABLE silver.sales_c086 ADD PRIMARY KEY (sale_sk);

-- UNVERIFIED-UNTIL-APPLIED: the natural key (invoice_no, line_no) uniqueness can only be
-- PROVEN on the transformed rows by the live dry-run (the deferred DB-write seam). This
-- unique index ASSERTS it; if a double-load made it non-unique, applying this FAILS LOUD
-- (which is the desired behavior -- the surrogate PK alone could not catch that).
CREATE UNIQUE INDEX uq_silver_c086_natural_key ON silver.sales_c086 (invoice_no, line_no);

-- supporting indexes for the common gold-build / Power BI slice paths.
CREATE INDEX idx_silver_c086_sale_date ON silver.sales_c086 (sale_date);
CREATE INDEX idx_silver_c086_customer  ON silver.sales_c086 (customer_id_clean);
CREATE INDEX idx_silver_c086_product   ON silver.sales_c086 (product_id);

COMMIT;
