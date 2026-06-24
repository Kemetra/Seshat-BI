-- 0001_create_silver_sales_c086.sql
-- Build silver.sales_c086 (typed/cleaned line-item fact) from bronze.sales_c086_raw.
--
-- Medallion: bronze = faithful TEXT landing (retained); silver = typed/cleaned flat
-- table; gold (later) = Kimball facts/dims. Power BI reads gold, not silver.
--
-- Grain: invoice LINE ITEM. PK = (invoice_no, line_no). 249,106 bronze -> 246,916 silver.
-- Idempotent: DROP+CREATE in one transaction; safe to re-run after a bronze reload.
--
-- IMPORTANT (encoding): this file contains Arabic literals. Save UTF-8 without BOM.
-- client_encoding is set to UTF8 so the billing_type CASE matches correctly.
--
-- Cleaning rules captured interactively + hardened by a 7-lens review (2026-06-24).
-- See memory: silver-cleaning-ruleset. Decisions baked in below are annotated.

SET client_encoding TO 'UTF8';

BEGIN;

CREATE SCHEMA IF NOT EXISTS silver;

DROP TABLE IF EXISTS silver.sales_c086;

CREATE TABLE silver.sales_c086 AS
WITH src AS (
  -- M1: TRIM every text column up front (kills whitespace-variant phantom distincts).
  SELECT
    trim(material)            AS material,
    trim(material_desc)       AS material_desc,
    trim(quantity)            AS quantity,
    trim(gross_sales)         AS gross_sales,
    trim(net_sales)           AS net_sales,
    trim(tax)                 AS tax,
    trim(subtotal5_discount)  AS subtotal5_discount,
    trim(reference_no)        AS reference_no,
    trim(item_no)             AS item_no,
    trim(date)                AS date,
    trim(billing_type)        AS billing_type,
    trim(billing_type_2)      AS billing_type_2,
    trim(customer)            AS customer,
    trim(customer_name)       AS customer_name,
    trim(personel_number)     AS personel_number,
    trim(person_name)         AS person_name,
    trim(position)            AS position,
    trim(buyer)               AS buyer,
    trim(division)            AS division,
    trim(category)            AS category,
    trim(subcategory)         AS subcategory,
    trim(segment)             AS segment,
    trim(brand)               AS brand,
    trim(mat_group)           AS mat_group,
    trim(item_cluster)        AS item_cluster,
    trim(ref_return)          AS ref_return,
    trim(site)                AS site,
    trim(site_name)           AS site_name
  FROM bronze.sales_c086_raw
),
filtered AS (
  SELECT * FROM src
  -- H1: division-junk filter runs BEFORE ''->NULL, so blank '' is matched here
  --     (NULLIF later would make IN() miss it). Drops AUX/ARCHIVE/EL EZABY SERVICES/blank.
  WHERE division NOT IN ('AUX', 'ARCHIVE', 'EL EZABY SERVICES', '')
  -- C2: zero-value line filter on NUMERIC cast, NOT text ('0.0' <> '0'). Drops 1,680 lines.
  AND NOT (
        NULLIF(quantity, '')::numeric = 0
    AND NULLIF(gross_sales, '')::numeric = 0
  )
)
SELECT
  -- identity
  material                                          AS product_id,        -- TEXT, leading zeros
  -- H4: mojibake cleanup via positive whitelist — keep ASCII (32-126), Arabic (1569-1791),
  --     and pharma dosing micro signs (181 µ, 924 Μ, 956 μ); strip everything else
  --     (covers all box-drawing/symbol families, not just a 3-char blacklist).
  regexp_replace(
    material_desc,
    '[^' || chr(32) || '-' || chr(126)
         || chr(181) || chr(924) || chr(956)
         || chr(1569) || '-' || chr(1791) || ']',
    '', 'g'
  )                                                 AS product_name,
  -- measures (4): gross / net / tax / discount
  NULLIF(quantity, '')::numeric(18,4)               AS quantity,          -- negatives = returns
  NULLIF(gross_sales, '')::numeric(18,2)            AS sales_amount,      -- gross
  NULLIF(net_sales, '')::numeric(18,2)              AS net_amount,
  NULLIF(tax, '')::numeric(18,2)                    AS tax_amount,
  NULLIF(subtotal5_discount, '')::numeric(18,2)     AS discount_amount,   -- negative on sales
  -- keys / dates
  NULLIF(reference_no, '')                          AS invoice_no,        -- PK part (TEXT)
  NULLIF(item_no, '')::smallint                     AS line_no,           -- M2: SMALLINT, PK part
  NULLIF(date, '')::date                            AS sale_date,
  -- billing_type -> English, ALL 10 values enumerated (H2). ELSE 'UNMAPPED' loud sentinel.
  CASE billing_type
    WHEN 'اجل'                  THEN 'Credit'
    WHEN 'فورى'                 THEN 'Cash'
    WHEN 'مرتجع اجل'            THEN 'Credit Return'
    WHEN 'مرتجع فورى'           THEN 'Cash Return'
    WHEN 'Pick-Up Order'        THEN 'Pick-Up Order'
    WHEN 'Pick-Up Order Return' THEN 'Pick-Up Order Return'
    WHEN 'توصيل'                THEN 'Delivery'
    WHEN 'مرتجع توصيل'          THEN 'Delivery Return'
    WHEN 'توصيل - اجل'          THEN 'Delivery Credit'
    WHEN 'مرتجع توصيل - اجل'    THEN 'Delivery Credit Return'
    ELSE 'UNMAPPED'
  END                                               AS billing_type,
  billing_type_2                                    AS billing_type_code, -- Z-codes
  -- H3: is_return boolean (TRUE for the 5 return billing codes). Belt-and-suspenders
  --     with the English 'Return' label; makes SUM(sales_amount) separable in DAX.
  (billing_type_2 IN ('Z4', 'Z5', 'Z6', 'Z8', 'Z10')) AS is_return,
  -- customer
  NULLIF(customer, '')                              AS customer_id,       -- TEXT, leading zeros
  customer_name,                                                          -- attribute, NOT a key
  -- staff (sentinels applied below)
  personel_number                                   AS salesperson_id,
  person_name                                       AS salesperson_name,
  position                                          AS job_title,
  buyer                                             AS procurement_buyer,
  -- product hierarchy (flat, as-is; multi-parent overlaps preserved)
  division                                          AS product_division,
  category                                          AS product_category,
  subcategory                                       AS product_subcategory,
  segment                                           AS product_segment,
  brand                                             AS product_brand,
  mat_group                                         AS product_group,
  item_cluster                                      AS product_cluster,
  -- M1: only return->originating-invoice link; NULL on non-returns (no fill)
  NULLIF(ref_return, '')                            AS original_invoice_ref,
  -- branch (single store today; kept for multi-store future)
  site                                              AS branch_code,
  site_name                                         AS branch_name,
  -- M4: business_segment derived from product_division (merchandising rollup).
  CASE division
    WHEN 'OTC'                 THEN 'PHARMA'
    WHEN 'RX'                  THEN 'PHARMA'
    WHEN 'NUTRACEUTICAL'       THEN 'PHARMA'
    WHEN 'EVERYDAY ESSENTIALS' THEN 'PHARMA'
    WHEN 'HOME HEALTH CARE'    THEN 'PHARMA'
    WHEN 'HIGH VALUE ITEMS'    THEN 'HVI'
    WHEN 'BEAUTY SKIN CARE'    THEN 'NON-PHARMA'
    WHEN 'TOTAL HAIR CARE'     THEN 'NON-PHARMA'
    WHEN 'BABY AND MOM'        THEN 'NON-PHARMA'
    WHEN 'COSMETICS'           THEN 'NON-PHARMA'
    WHEN 'PREMIUM SKIN CARE'   THEN 'NON-PHARMA'
    ELSE 'UNMAPPED'
  END                                               AS business_segment
FROM filtered;

-- ''->NULL already handled by NULLIF on cast columns; now fill text-attribute NULLs
-- (sentinels chosen interactively; verified 0 collision with real values).
UPDATE silver.sales_c086 SET salesperson_id   = 'UNKNOWN'      WHERE salesperson_id   IS NULL OR salesperson_id   = '';
UPDATE silver.sales_c086 SET salesperson_name = 'UNKNOWN'      WHERE salesperson_name IS NULL OR salesperson_name = '';
UPDATE silver.sales_c086 SET job_title        = 'UNKNOWN'      WHERE job_title        IS NULL OR job_title        = '';
UPDATE silver.sales_c086 SET product_brand    = 'UNKNOWN'      WHERE product_brand    IS NULL OR product_brand    = '';
UPDATE silver.sales_c086 SET product_cluster  = 'UNCLASSIFIED' WHERE product_cluster  IS NULL OR product_cluster  = '';
-- NOTE: insurance_no / insurance_phone are DROPPED (C1 — patient health PII). Not in silver.

-- PK can be declared because the dry-run proved (invoice_no, line_no) is unique post-transform
-- and both columns are non-NULL.
ALTER TABLE silver.sales_c086 ADD PRIMARY KEY (invoice_no, line_no);

-- M6: supporting indexes for the common Power BI / gold slice paths.
CREATE INDEX idx_silver_c086_sale_date   ON silver.sales_c086 (sale_date);
CREATE INDEX idx_silver_c086_customer_id ON silver.sales_c086 (customer_id);
CREATE INDEX idx_silver_c086_product_id  ON silver.sales_c086 (product_id);

COMMIT;
