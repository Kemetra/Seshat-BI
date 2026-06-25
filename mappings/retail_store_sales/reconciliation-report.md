# Reconciliation Report -- `retail_store_sales`

> The blank a later LIVE acceptance run fills (RC16), after silver + gold are built.
> NOT filled yet -- silver/gold do not exist. The `training` DB is reachable, so this
> runs via `retail validate --source-map mappings/retail_store_sales/source-map.yaml`
> once the warehouse build exists. Fill from a read-only live run; never fabricate or
> round figures to reach a verdict. ASCII only.

---

## Run header

| Field | Value |
|-------|-------|
| Table id | `retail_store_sales` |
| Silver object | `silver.retail_store_sales` (12,575 rows) |
| Gold objects | `gold.fct_sales_rss` + `dim_customer_rss` / `dim_product_rss` / `dim_payment_method_rss` / `dim_location_rss` / `dim_date_rss` |
| Run date | 2026-06-25 |
| DB cluster / database | `db-pgsql-fra1-29712` / `training` |
| Run by | agent (`retail validate`, read-only, console-script CLI) |
| Connection | READ-ONLY; credentials from the gitignored `.env`; no writes |

## 1. PK uniqueness (RC2) -- on the TRANSFORMED silver rows

| Check | Expected | Observed |
|-------|----------|----------|
| `COUNT(*) = COUNT(DISTINCT transaction_id)` on `silver.retail_store_sales` | equal | 12,575 = 12,575 -- PASS |
| `0` NULL `transaction_id` | 0 | 0 -- PASS |

## 2. Date-dim coverage (RC15)

| Check | Expected | Observed |
|-------|----------|----------|
| `dim_date_rss` spans every fact `transaction_date` (2022-01-01 .. 2025-01-18), contiguous | full coverage, no gaps | full coverage (contiguous calendar; NO `-1` member -- it is a marked date table, rule S8) -- PASS |

## 3. Orphan FKs (RC16)

| Fact FK | Dimension | Expected orphans | Observed |
|---------|-----------|------------------|----------|
| `customer_sk` | `dim_customer_rss` | 0 | 0 -- PASS |
| `product_sk` | `dim_product_rss` | 0 (the 9.65% missing item -> -1 member, per Q4) | 0 -- PASS (1,213 rows correctly on the `-1` unknown member) |
| `payment_method_sk` | `dim_payment_method_rss` | 0 | 0 -- PASS |
| `location_sk` | `dim_location_rss` | 0 | 0 -- PASS |
| `date_sk` | `dim_date_rss` | 0 | 0 -- PASS |

## 4. Cross-layer measure reconciliation (RC16)

| Measure | Silver | Gold | BI | Match? |
|---------|--------|------|----|--------|
| `quantity` (sum) | 66,276.00 | 66,276.00 | n/a | PASS (penny-exact) |
| `total_spent` (sum) | 1,552,071.00 | 1,552,071.00 | n/a | PASS (penny-exact) |
| row count | 12,575 | 12,575 | n/a | PASS |

> Note: blanks in price/quantity/total in bronze (~4.8% each) mean the silver
> transform's handling of NULL measures (sum-ignoring-NULL vs row-drop) must be stated
> and reconciled -- a build decision recorded when silver is authored.

## Verdict

**PASS** -- `retail validate --source-map mappings/retail_store_sales/source-map.yaml`
returned exit 0 WITH the "running live checks" banner and "all live checks passed
(0 findings)". PK unique on transformed silver, date coverage complete, 0 orphan FKs
across all 5 dims, penny-exact reconciliation on both measures. Gold Ready satisfied.
(Run via the `retail` console script; `python -m retail.cli` is a no-op -- it has no
`__main__` guard, so it exits 0 without running. See global-lessons.md.)

## See also

- The check: `../../src/retail/validate.py` (RC16); the live verb: the `retail-validate`
  skill. The durable history: `../../templates/reconciliation-ledger-entry.md` (F015).
- Siblings: `source-profile.md`, `source-map.yaml`, `assumptions.md`,
  `unresolved-questions.md`; the readiness state: `readiness-status.yaml`.
