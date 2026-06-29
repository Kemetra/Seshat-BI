# Reconciliation Report -- `sales_c086`

> The LIVE acceptance blank. Completed only AFTER silver + gold are built. The gate
> is shut and no silver/gold exists, so live results are `PENDING`. Only the SOURCE
> (bronze) baseline is filled, measured 2026-06-29. Reflects the final chain decisions
> (Sale_SK surrogate PK; 2 measures Gross_Sales + Quantity; overlap-corrected filters).
> ASCII only.

---

## What this report is

LIVE acceptance gates (playbook Phase 5/6; ADR RC2, RC15, RC16): PK uniqueness, date
coverage, 0 orphan FKs, penny-exact reconciliation. Implemented as `retail validate`
(`src/retail/validate.py`).

> **STATUS: PENDING BUILD.** silver/gold for `sales_c086` are not built; the gate is OPEN
> (judgment-call ANSWERS recorded, map REVIEW pending). Observed columns stay `PENDING`
> until the build + a read-only `retail validate` run. The SOURCE baseline is recorded now.

---

## Run header

| Field | Value |
|-------|-------|
| Table id | `sales_c086` |
| Silver object | `silver.sales_c086` (NOT YET BUILT) |
| Gold objects | `gold.fct_sales` (PK `Sale_SK`) + `dim_product` / `dim_customer` / `dim_salesperson` / `dim_product_purchaser` / `dim_billing_type` / `dim_branch` + `dim_date` (NOT YET BUILT) |
| Run date | `<PENDING>` |
| DB cluster | `db-pgsql-fra1-29712` (fra1) |
| Database | `ezaby_demo` |
| Run by | `<PENDING>` |
| Connection | **READ-ONLY**, credentials from gitignored `.env`. No writes. |

---

## 0. SOURCE baseline (bronze, measured 2026-06-29)

Totals over all **249,106** landed bronze rows. They will NOT equal silver until the row
filters remove 2,190 rows (see below). Only the 2 KEPT measures are tracked
(`Gross_Sales`, `Quantity`); other money columns were dropped at keep/drop (Q5).

| Metric | bronze.sales_c086_raw |
|--------|------------------------|
| Row count | 249,106 |
| sum(gross_sales) | 38,834,389.31 |
| sum(quantity) | 314,608.67 |
| **Row filters (Q4):** junk-division | 513 rows |
| zero-value (qty=0 AND gross=0) | 1,680 rows |
| overlap (both) | 3 rows |
| **net dropped** | 513 + 1,680 - 3 = **2,190** |
| **Expected silver row count** | **246,916** (= 249,106 - 2,190) |

> ORDERING NOTE (D12): the junk-division filter targets blanks (`trim(division)=''`) and
> MUST run before the `Division` sentinel substitution, or the 3 blank-division rows
> (none of which are zero-value) survive and silver would be 246,919, not 246,916.

---

## 1. PK uniqueness (ADR RC2)

**Gate:** the fact PK is unique + non-null. PK is the generated `Sale_SK` (unique by
construction); the MEANINGFUL proof is that the **natural key `(Invoice_No, Line_No)`**
(retained silver-only) is still unique on the post-filter rows.

| Check | Expected | Observed |
|-------|----------|----------|
| Silver row count | 246,916 | PENDING |
| Distinct `Sale_SK` | 246,916 (= row count) | PENDING |
| Distinct natural key `(Invoice_No, Line_No)` | 246,916 (= row count) | PENDING |
| NULL `Sale_SK` / null natural key | 0 / 0 | PENDING |

**Result:** PENDING. Landed natural-key proof: 249,106 = 249,106 distinct, 0 null
(source-profile.md). Must re-prove on the post-filter silver output.

---

## 2. Date-dim coverage (ADR RC15)

**Gate:** `gold.dim_date` is a contiguous `generate_series` calendar spanning every real
`Sale_Date`, **with NO `-1`/unknown member** (so it is markable as a Power BI date table,
D10/S8). An unmatched fact date fails via `Date_SK NOT NULL`, never a sentinel.

| Check | Expected | Observed |
|-------|----------|----------|
| Calendar span | 2023-01-01 .. 2025-12-31 | PENDING |
| Calendar row count | 1,096 (contiguous; incl. 2024 leap) | PENDING |
| Unknown/sentinel member present | **0 (forbidden)** | PENDING |
| Real fact dates outside the calendar | 0 | PENDING |

**Result:** PENDING. Source fact has 1,094 distinct dates within the span.

---

## 3. Orphan FKs (ADR RC16)

**Gate:** 0 hard orphan FKs across all 6 entity dims; rows on each `-1` member counted as
a DQ signal. (dim_date has no `-1` -- an unmatched date is a hard failure, not absorbed.)

| Dimension | Hard orphan FKs (expected 0) | Rows on `-1` unknown member (DQ signal) |
|-----------|------------------------------|-----------------------------------------|
| `dim_product` | PENDING | PENDING |
| `dim_customer` | PENDING | PENDING -- walk-in rows go to the named `WALK_IN` member (Q6), NOT `-1` |
| `dim_salesperson` | PENDING | PENDING -- ~1,748 blank-id rows expected on `-1` |
| `dim_product_purchaser` | PENDING | PENDING |
| `dim_billing_type` | PENDING | PENDING |
| `dim_branch` | PENDING | PENDING -- single-member dim |

**Result:** PENDING.

---

## 4. Cross-layer measure reconciliation (ADR RC16)

**Gate:** every kept measure total matches to the penny source -> silver -> gold.
Source = bronze total; silver/gold = after the 2,190-row filter.

| Measure | Source (bronze) | Silver | Gold | BI | Match? |
|---------|-----------------|--------|------|----|--------|
| Gross_Sales | 38,834,389.31 | PENDING | PENDING | n/a | PENDING |
| Quantity | 314,608.67 | PENDING | PENDING | n/a | PENDING |
| Row count | 249,106 | PENDING (246,916 expected) | PENDING | n/a | PENDING |

**Result:** PENDING. source != silver by design (the 2,190-row filter); the delta must be
explained by the filtered rows' contribution, not rounded away.

---

## Verdict

| Category | ADR | Result |
|----------|-----|--------|
| 1. PK uniqueness | RC2 | PENDING |
| 2. Date-dim coverage | RC15 | PENDING |
| 3. Orphan FKs | RC16 | PENDING |
| 4. Cross-layer reconciliation | RC16 | PENDING |

**Overall:** **PENDING** -- no build; gate OPEN. This blank is filled by a live
`retail validate` run once the gate clears and silver/gold are built.

## See also

- `src/retail/validate.py` (`retail validate`); `docs/decisions/0002-retail-cleaning-defaults.md`.
- Sibling artifacts: `source-profile.md`, `source-map.yaml`, `assumptions.md`,
  `unresolved-questions.md` (this folder).
