-- 0010_fix_gold_retail_store_sales_date_labels.sql
-- Remove the blank padding from gold.dim_date_rss month_name / day_name.
--
-- 0004 builds the labels with to_char(d,'Month') / to_char(d,'Day'), which
-- PostgreSQL blank-pads to nine characters ('May      ', 'Friday   '). Slicers and
-- axis labels then show trailing blanks, and an exact-text filter against a clean
-- month list matches nothing. The FM modifier removes the padding.
--
-- Follow-up migration: 0004 is already applied, so it is NOT edited in place.
-- Apply AFTER 0004, and re-apply whenever 0004 is re-applied (0004 is a full
-- DROP+CREATE rebuild). The dbt shadow model
-- (dbt/models/marts/retail_store_sales/dim_date_rss.sql) emits the same
-- FM-formatted values, so both build paths agree.
--
-- Column set unchanged: dim_date_rss stays exactly the RC15 calendar contract
-- (seshat.star_discovery.RC15_CALENDAR_COLUMNS), so no consumer shape moves.
-- Idempotent: recomputing a label from full_date is a pure function of the row.
-- ASCII only; UTF-8 no BOM.

SET client_encoding TO 'UTF8';

BEGIN;

UPDATE gold.dim_date_rss
SET month_name = to_char(full_date, 'FMMonth'),
    day_name   = to_char(full_date, 'FMDay');

COMMIT;
