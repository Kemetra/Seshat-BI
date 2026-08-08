-- 0007_create_silver_finance_gl_budget.sql
-- Build silver.finance_gl_budget (typed/cleaned quarterly plan fact) from
-- bronze.finance_gl_budget (the faithful TEXT landing of the CSV emitted by
-- tests/fixtures/finance_gl/generate.py, seed 20260730 -- spec 137).
--
-- AUTHORING ONLY. Never executed by this feature -- no database connection is
-- opened anywhere in spec 137 (every live leg reads [PENDING LIVE PROFILE]).
-- Authored because the mapping gate for finance_gl_budget is CLEARED
-- (mappings/finance_gl_budget/readiness-status.yaml approvals[]; see
-- mappings/finance_gl_budget/approval-decision-mapping-gate.md sub-decision B).
--
-- Medallion: bronze = faithful TEXT landing; silver = typed/cleaned flat table;
-- gold (0008) = Kimball star. Power BI reads gold, not silver.
--
-- Grain: one budgeted amount per account per department per fiscal quarter per
-- budget version (mappings/finance_gl_budget/source-map.yaml meta.grain) --
-- DISTINCT from the actuals grain (spec SC-004: two facts, never merged).
-- PK = (fiscal_year, fiscal_quarter, account_code, department_code, budget_version) --
-- verified unique 2,688 = 2,688 on the landed synthetic data (source-profile.md).
-- Dropping budget_version collides 2:1 -- the data-side proof that version is part
-- of IDENTITY (FR-011), not an attribute.
-- Idempotent: DROP+CREATE in one transaction; safe to re-run after a bronze reload.
--
-- Cleaning rules from the APPROVED mappings/finance_gl_budget/source-map.yaml (gate
-- CLEARED 2026-07-30). RC8 (is_return) is N/A -- a plan has no transaction-type
-- column (assumptions.md). RC15 deviation: this fact does NOT reference the daily
-- calendar; its time grain is the fiscal quarter (see 0008 dim_fiscal_period_fgl).
-- ASCII only; UTF-8 no BOM.

SET client_encoding TO 'UTF8';

BEGIN;

CREATE SCHEMA IF NOT EXISTS silver;

DROP TABLE IF EXISTS silver.finance_gl_budget;

CREATE TABLE silver.finance_gl_budget AS
WITH src AS (
  -- TRIM every text column up front (RC5 baseline; the profile found 0 blanks).
  SELECT
    trim(fiscal_year)      AS fiscal_year,
    trim(fiscal_quarter)   AS fiscal_quarter,
    trim(account_code)     AS account_code,
    trim(department_code)  AS department_code,
    trim(budget_version)   AS budget_version,
    trim(currency_code)    AS currency_code,
    trim(budget_amount)    AS budget_amount
  FROM bronze.finance_gl_budget
)
SELECT
  -- grain / composite PK (RC1, RC2) -- budget_version is part of IDENTITY (FR-011)
  NULLIF(fiscal_year, '')::smallint           AS fiscal_year,        -- RC7: ordinal -> smallint
  NULLIF(fiscal_quarter, '')::smallint        AS fiscal_quarter,     -- RC7: ordinal -> smallint
  NULLIF(account_code, '')                    AS account_code,
  NULLIF(department_code, '')                 AS department_code,
  NULLIF(budget_version, '')                  AS budget_version,     -- degenerate dim; part of identity
  -- degenerate attribute
  NULLIF(currency_code, '')                   AS currency_code,
  -- measure (RC7: money -> exact NUMERIC; RC9: kept as landed).
  -- ZERO is a legitimate planned amount ("nothing was planned") and is NOT the same
  -- as an ABSENT row (FR-015) -- absence is what the Missing Budget Flag metric
  -- detects downstream; NULLIF never manufactures a NULL from a real 0.00 value.
  NULLIF(budget_amount, '')::numeric(18,2)    AS budget_amount
FROM src;

-- No allocation, spreading, or interpolation of budget_amount anywhere in this
-- migration (OD-3, ruled 2026-07-30): deriving a monthly or line-level budget would
-- invent numbers the source never had. A new budget_version is a NEW set of rows in
-- the bronze reload, never an UPDATE of a prior version's rows (FR-011) -- this
-- migration only DROP+CREATEs the whole silver table from whatever bronze holds, so
-- it never overwrites a specific prior version in place; the append-only guarantee
-- is a property of how bronze is loaded, not of this statement, and stays
-- [PENDING LIVE PROFILE] until a real load is observed.

-- PK can be DECLARED here but is UNVERIFIED-UNTIL-APPLIED: the 5-part key was unique
-- on the LANDED synthetic data (2,688 rows = 2,688 distinct; source-profile.md).
-- RC2 requires re-proving it on the TRANSFORMED rows -- [PENDING LIVE PROFILE].
ALTER TABLE silver.finance_gl_budget
  ADD PRIMARY KEY (fiscal_year, fiscal_quarter, account_code, department_code, budget_version);

-- supporting indexes for the common gold slice paths
CREATE INDEX idx_silver_fglb_account_code    ON silver.finance_gl_budget (account_code);
CREATE INDEX idx_silver_fglb_department_code ON silver.finance_gl_budget (department_code);
CREATE INDEX idx_silver_fglb_budget_version  ON silver.finance_gl_budget (budget_version);

COMMIT;
