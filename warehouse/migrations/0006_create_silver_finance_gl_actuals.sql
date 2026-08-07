-- 0006_create_silver_finance_gl_actuals.sql
-- Build silver.finance_gl_actuals (typed/cleaned journal-line fact) from
-- bronze.finance_gl_actuals (the faithful TEXT landing of the CSV emitted by
-- tests/fixtures/finance_gl/generate.py, seed 20260730 -- spec 137).
--
-- AUTHORING ONLY. This migration is NEVER executed by this feature: no database
-- connection is opened anywhere in spec 137 (every live leg reads
-- [PENDING LIVE PROFILE]). It is authored because the mapping gate for
-- finance_gl_actuals is CLEARED (mappings/finance_gl_actuals/readiness-status.yaml
-- approvals[]; see mappings/finance_gl_actuals/approval-decision-mapping-gate.md
-- sub-decision B), which is the hard stop `no_silver_before_mapping_cleared`
-- being satisfied, not executed against.
--
-- Medallion: bronze = faithful TEXT landing; silver = typed/cleaned flat table;
-- gold (0008) = Kimball star. Power BI reads gold, not silver.
--
-- Grain: one journal line within one journal entry (mappings/finance_gl_actuals/
-- source-map.yaml meta.grain). PK = (journal_entry_id, line_id) -- verified unique
-- 5,000 = 5,000 on the landed synthetic data (source-profile.md).
-- Idempotent: DROP+CREATE in one transaction; safe to re-run after a bronze reload.
--
-- Cleaning rules from the APPROVED mappings/finance_gl_actuals/source-map.yaml
-- (gate CLEARED 2026-07-30, sub-decisions A/B/C1/C2/D). RC8 (is_return) is N/A --
-- a P&L journal extract carries no transaction-type or reversal column
-- (assumptions.md). ASCII only; UTF-8 no BOM.

SET client_encoding TO 'UTF8';

BEGIN;

CREATE SCHEMA IF NOT EXISTS silver;

DROP TABLE IF EXISTS silver.finance_gl_actuals;

CREATE TABLE silver.finance_gl_actuals AS
WITH src AS (
  -- TRIM every text column up front (RC5 baseline; the profile found 0 blanks, so
  -- nothing is coerced by NULLIF here -- trimming still guards against a future
  -- non-clean bronze reload without changing today's behaviour).
  SELECT
    trim(journal_entry_id) AS journal_entry_id,
    trim(line_id)          AS line_id,
    trim(posting_date)     AS posting_date,
    trim(account_code)     AS account_code,
    trim(department_code)  AS department_code,
    trim(cost_center_code) AS cost_center_code,
    trim(currency_code)    AS currency_code,
    trim(debit_amount)     AS debit_amount,
    trim(credit_amount)    AS credit_amount,
    trim(description)      AS description
  FROM bronze.finance_gl_actuals
)
SELECT
  -- grain / composite PK (RC1, RC2)
  NULLIF(journal_entry_id, '')               AS journal_entry_id,   -- degenerate dim
  NULLIF(line_id, '')::smallint               AS line_id,            -- RC7: ordinal -> smallint
  NULLIF(posting_date, '')::date              AS posting_date,       -- RC7: date -> DATE
  -- conformed dimension foreign keys (natural keys at this layer; surrogate keys in gold)
  NULLIF(account_code, '')                    AS account_code,
  NULLIF(department_code, '')                 AS department_code,
  NULLIF(cost_center_code, '')                AS cost_center_code,
  -- degenerate attributes
  NULLIF(currency_code, '')                   AS currency_code,
  -- measures (RC7: money -> exact NUMERIC, never float; RC9: independent landed measures,
  -- neither reconstructed from the other side of the entry)
  NULLIF(debit_amount, '')::numeric(18,2)     AS debit_amount,
  NULLIF(credit_amount, '')::numeric(18,2)    AS credit_amount,
  NULLIF(description, '')                     AS description
FROM src;

-- No sentinel UPDATEs: unknown/missing dimension members are handled by the gold -1
-- unknown member (RC14), never by a silver text sentinel; measure NULLs stay NULL.

-- PK can be DECLARED here but is UNVERIFIED-UNTIL-APPLIED: the composite key was
-- unique on the LANDED synthetic data (5,000 rows = 5,000 distinct journal_entry_id +
-- line_id pairs; source-profile.md). RC2 requires re-proving it on the TRANSFORMED
-- rows -- the live retail-validate-equivalent run is the proof, and it is
-- [PENDING LIVE PROFILE] because no database was opened for this feature.
ALTER TABLE silver.finance_gl_actuals ADD PRIMARY KEY (journal_entry_id, line_id);

-- supporting indexes for the common gold slice paths
CREATE INDEX idx_silver_fgla_posting_date    ON silver.finance_gl_actuals (posting_date);
CREATE INDEX idx_silver_fgla_account_code    ON silver.finance_gl_actuals (account_code);
CREATE INDEX idx_silver_fgla_department_code ON silver.finance_gl_actuals (department_code);

COMMIT;
