-- 0009_harden_gold_finance_gl_star.sql
-- Harden the finance GL gold star built by 0008 (and the silver amount it reads
-- from 0006). Follow-up migration: 0006 and 0008 are already applied, so they are
-- NOT edited in place. Apply AFTER 0008, and re-apply whenever 0006 or 0008 is
-- re-applied (both are full DROP+CREATE rebuilds that would otherwise drop what
-- this file adds).
--
-- 1. CONFORMED DIMENSIONS ARE UNIQUE ON THEIR NATURAL KEY.
--    0008 builds dim_account_fgl / dim_department_fgl / dim_cost_center_fgl with a
--    GROUP BY over every attribute column, so a natural key that arrives with two
--    different attribute values (e.g. account_code '4000' named both 'Sales' and
--    'Sales ') becomes TWO dimension rows. Every fact row for that key then joins
--    both and is inserted twice with different surrogate keys -- which the
--    budget's surrogate-key grain constraint cannot see, so SUM(budget_amount)
--    silently doubles. The UNIQUE constraints below make that fan-out FAIL LOUDLY
--    instead: the ALTER raises and the whole transaction rolls back.
--    NOTE: the -1 unknown member carries the code 'UNKNOWN'; a real source key
--    spelled 'UNKNOWN' now also fails loudly here instead of colliding silently.
--
-- 2. THE BUDGET FACT'S NATURAL GRAIN IS ENFORCED.
--    With every dimension unique on its natural key, each surrogate key maps to
--    exactly one natural key, so uq_fct_gl_budget_fgl_grain (account_sk,
--    department_sk, fiscal_period_sk, budget_version) is now exactly the natural
--    grain (account_code, department_code, fiscal_year, fiscal_quarter,
--    budget_version) that silver.finance_gl_budget's primary key declares (0007).
--    Blank natural keys all resolve to the -1 member, so two blank-keyed budget
--    lines at one period/version also fail loudly on that constraint.
--
-- 3. dim_date_fgl LABELS AND ISO YEAR.
--    to_char(d,'Month') / to_char(d,'Day') blank-pad to nine characters
--    ('May      '); the FM modifier removes the padding. iso_week follows ISO-8601
--    numbering, so it is only meaningful next to the ISO year: 2024-12-30 is
--    ISO week 1 of 2025, not week 1 of calendar year 2024. iso_year is added so a
--    "by ISO week" slice can pair the two. The dimension is rebuilt (drop the fact
--    FK, drop + recreate the table, re-add the FK) so its column list stays a
--    single CREATE TABLE -- the same span and RC15 contiguity as 0008.
--
-- 4. SILVER / GOLD amount SURVIVES A BLANK ZERO SIDE.
--    0006 computes amount = NULLIF(debit,'') + NULLIF(credit,''), so a line landed
--    as debit '1500.00', credit '' gets amount NULL and drops out of SUM(amount)
--    with no error. The cleared map's derived_columns.amount rule is "the line's
--    magnitude; exactly one side is non-zero per line, so the sum is that side":
--    a blank side is that zero side. amount stays NULL only when BOTH sides are
--    blank (no magnitude was landed at all).
--
-- Idempotent: every constraint is dropped-if-exists before it is added, the date
-- dimension is a full drop-and-rebuild, and the amount UPDATEs only touch rows
-- whose amount is still NULL while a side is present.
-- ASCII only; UTF-8 no BOM.

SET client_encoding TO 'UTF8';

BEGIN;

-- ============================================================ 1. natural-key uniqueness
ALTER TABLE gold.dim_account_fgl DROP CONSTRAINT IF EXISTS uq_dim_account_fgl_code;
ALTER TABLE gold.dim_account_fgl
  ADD CONSTRAINT uq_dim_account_fgl_code UNIQUE (account_code);

ALTER TABLE gold.dim_department_fgl DROP CONSTRAINT IF EXISTS uq_dim_department_fgl_code;
ALTER TABLE gold.dim_department_fgl
  ADD CONSTRAINT uq_dim_department_fgl_code UNIQUE (department_code);

-- The fact joins cost centres on (cost_center_code, department_code) (0008, C1),
-- so that pair is the natural key the join relies on.
ALTER TABLE gold.dim_cost_center_fgl DROP CONSTRAINT IF EXISTS uq_dim_cost_center_fgl_code;
ALTER TABLE gold.dim_cost_center_fgl
  ADD CONSTRAINT uq_dim_cost_center_fgl_code UNIQUE (cost_center_code, department_code);

-- ============================================================ 3. dim_date_fgl rebuild
ALTER TABLE gold.fct_gl_actuals_fgl DROP CONSTRAINT IF EXISTS fk_fct_gl_actuals_date;
DROP TABLE IF EXISTS gold.dim_date_fgl;

-- ACTUALS-ONLY. RC15 daily calendar; a marked date table carries NO -1 member
-- (rule S8). Span unchanged from 0008.
CREATE TABLE gold.dim_date_fgl (
  date_sk    INT PRIMARY KEY,                -- smart key YYYYMMDD
  full_date  DATE,
  year       SMALLINT,
  quarter    SMALLINT,
  month      SMALLINT,
  month_name TEXT,                           -- 'January', no padding (FM)
  day        SMALLINT,
  day_name   TEXT,                           -- 'Monday', no padding (FM)
  iso_week   SMALLINT,                       -- ISO-8601 week; pair with iso_year
  iso_year   SMALLINT,                       -- ISO-8601 week-numbering year
  is_weekend BOOLEAN
);
INSERT INTO gold.dim_date_fgl
SELECT
  (to_char(d,'YYYYMMDD'))::int       AS date_sk,
  d::date                             AS full_date,
  extract(year FROM d)::smallint,
  extract(quarter FROM d)::smallint,
  extract(month FROM d)::smallint,
  to_char(d,'FMMonth'),
  extract(day FROM d)::smallint,
  to_char(d,'FMDay'),
  extract(week FROM d)::smallint,
  extract(isoyear FROM d)::smallint,
  (extract(isodow FROM d) >= 6)       AS is_weekend
FROM generate_series(DATE '2024-01-01', DATE '2025-12-31', INTERVAL '1 day') AS g(d);

ALTER TABLE gold.fct_gl_actuals_fgl ADD CONSTRAINT fk_fct_gl_actuals_date FOREIGN KEY (date_sk) REFERENCES gold.dim_date_fgl (date_sk);

-- ============================================================ 4. amount with a blank side
UPDATE silver.finance_gl_actuals
SET amount = COALESCE(debit_amount, 0) + COALESCE(credit_amount, 0)
WHERE amount IS NULL
  AND (debit_amount IS NOT NULL OR credit_amount IS NOT NULL);

-- gold carries the same landed debit/credit columns, so it is corrected from its
-- own row (same expression as silver above) rather than by re-reading silver.
UPDATE gold.fct_gl_actuals_fgl
SET amount = COALESCE(debit_amount, 0) + COALESCE(credit_amount, 0)
WHERE amount IS NULL
  AND (debit_amount IS NOT NULL OR credit_amount IS NOT NULL);

COMMIT;
