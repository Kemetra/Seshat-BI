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
| Silver object | `silver.retail_store_sales` (NOT BUILT yet) |
| Gold objects | `gold.fct_sales` + `gold.dim_customer` / `dim_product` / `dim_payment_method` / `dim_location` / `dim_date` (NOT BUILT yet) |
| Run date | `[PENDING LIVE RUN]` |
| DB cluster / database | `db-pgsql-fra1-29712` / `training` |
| Run by | `[PENDING]` |
| Connection | READ-ONLY; credentials from the gitignored `.env`; no writes |

## 1. PK uniqueness (RC2) -- on the TRANSFORMED silver rows

| Check | Expected | Observed |
|-------|----------|----------|
| `COUNT(*) = COUNT(DISTINCT transaction_id)` on `silver.retail_store_sales` | equal | `[PENDING LIVE RUN]` |
| `0` NULL `transaction_id` | 0 | `[PENDING LIVE RUN]` |

## 2. Date-dim coverage (RC15)

| Check | Expected | Observed |
|-------|----------|----------|
| `dim_date` spans every fact `transaction_date` (2022-01-01 .. 2025-01-18), contiguous | full coverage, no gaps | `[PENDING LIVE RUN]` |

## 3. Orphan FKs (RC16)

| Fact FK | Dimension | Expected orphans | Observed |
|---------|-----------|------------------|----------|
| `customer_sk` | `dim_customer` | 0 (missing -> -1 member) | `[PENDING LIVE RUN]` |
| `product_sk` | `dim_product` | 0 (the 9.65% missing item -> -1 member, per Q4) | `[PENDING LIVE RUN]` |
| `payment_method_sk` | `dim_payment_method` | 0 | `[PENDING LIVE RUN]` |
| `location_sk` | `dim_location` | 0 | `[PENDING LIVE RUN]` |
| `date_sk` | `dim_date` | 0 | `[PENDING LIVE RUN]` |

## 4. Cross-layer measure reconciliation (RC16)

| Measure | Source (bronze) | Silver | Gold | BI | Match? |
|---------|-----------------|--------|------|----|--------|
| `quantity` (sum) | `[PENDING]` | `[PENDING]` | `[PENDING]` | n/a | `[PENDING]` |
| `total_spent` (sum) | `[PENDING]` | `[PENDING]` | `[PENDING]` | n/a | `[PENDING]` |
| row count | 12,575 (bronze) | `[PENDING]` | `[PENDING]` | n/a | `[PENDING]` |

> Note: blanks in price/quantity/total in bronze (~4.8% each) mean the silver
> transform's handling of NULL measures (sum-ignoring-NULL vs row-drop) must be stated
> and reconciled -- a build decision recorded when silver is authored.

## Verdict

`[PENDING LIVE RUN]` -- penny-exact reconciliation + 0 orphan FKs required for Gold
Ready `pass`. This blank exists; the run is downstream of the silver/gold build.

## See also

- The check: `../../src/retail/validate.py` (RC16); the live verb: the `retail-validate`
  skill. The durable history: `../../templates/reconciliation-ledger-entry.md` (F015).
- Siblings: `source-profile.md`, `source-map.yaml`, `assumptions.md`,
  `unresolved-questions.md`; the readiness state: `readiness-status.yaml`.
