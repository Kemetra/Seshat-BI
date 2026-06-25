# Source Profile -- `retail_store_sales`

> Filled instance of `templates/source-profile.md` for the Kaggle "retail store sales
> (dirty)" dataset, landed into the `training` DB bronze layer. Stage 1 (Source Ready)
> of the readiness spine. Mechanical numbers measured over a READ-ONLY connection via
> `retail.profile` against `bronze.retail_store_sales`; semantic rows are PROPOSED for
> human confirmation, not asserted as fact.

---

## Header

| Field | Value |
|-------|-------|
| Table id | `retail_store_sales` |
| Source system | Kaggle "retail store sales (dirty)" -- single CSV export (POS-style transactions) |
| Landed location | `bronze.retail_store_sales` (faithful all-TEXT landing + `_source_file`/`_loaded_at` lineage) |
| Connection | read-only; credentials from the gitignored `.env` at runtime -- no connection string committed |
| Profiled on | 2026-06-25 |
| Profiled by | agent (`retail.profile`, read-only session) |
| Source files folded in | single export (`retail_store_sales.csv`, 12,575 data rows) |

---

## Shape

| Metric | Value |
|--------|-------|
| Row count (landed) | 12,575 |
| Column count (landed) | 11 source columns (+ 2 lineage: `_source_file`, `_loaded_at`) |
| Schema(s) present | `bronze` (this table); `silver`/`gold` created empty |

---

## Per-column profile

Missingness measured as `'' OR NULL` (RC5 -- a faithful landing writes `''` for blank,
so `IS NULL` alone would report 0). All source columns landed as `TEXT`.

| Column | Type as landed | Missingness (`'' OR NULL`, count / %) | Distinct cardinality | Candidate key? | Notes |
|--------|----------------|----------------------------------------|----------------------|----------------|-------|
| `transaction_id` | TEXT | 0 / 0.00% | 12,575 | **yes (PK)** | `TXN_xxxxxxx`; unique on the data -- the grain key |
| `customer_id` | TEXT | 0 / 0.00% | 25 | no | `CUST_xx`; pseudonymous customer surrogate -> dim candidate. PII question (see unresolved-questions) |
| `category` | TEXT | 0 / 0.00% | 8 | no | clean product category -> dim attribute / rollup |
| `item` | TEXT | 1,213 / 9.65% | 201 | no | `Item_N_<CAT>` product key; 1:1 with category (0 fan-out); encodes the category suffix |
| `price_per_unit` | TEXT | 609 / 4.84% | 26 | no | money; float-as-text (`18.5`); silver casts to numeric (RC7) |
| `quantity` | TEXT | 604 / 4.80% | 11 | no | float-as-text (`10.0`); range 1..10; silver casts to numeric/int |
| `total_spent` | TEXT | 604 / 4.80% | 228 | no | money; **derivable**: `= price_per_unit * quantity` on 100% of complete rows |
| `payment_method` | TEXT | 0 / 0.00% | 3 | no | Cash / Credit Card / Digital Wallet -> degenerate dim or dim |
| `location` | TEXT | 0 / 0.00% | 2 | no | In-store / Online -> dim attribute |
| `transaction_date` | TEXT | 0 / 0.00% | 1,114 | no | `YYYY-MM-DD`; spans 2022-01-01 .. 2025-01-18 -> dim_date FK |
| `discount_applied` | TEXT | 4,199 / 33.39% | 3 | no | `True`/`False`/`''`; a discount FLAG (not a return). Blank semantics OPEN (see unresolved) |

Lineage columns `_source_file` (TEXT) and `_loaded_at` (TIMESTAMPTZ) are infrastructure,
not part of the mapped grain -- excluded from the per-column missingness scan. (NOTE: the
`retail.profile` helper auto-trims every discovered column and errors on the TIMESTAMPTZ
lineage column -- a tool defect logged for a later profile/checker fix; the source columns
were profiled directly with the same `'' OR NULL` measure.)

---

## Semantics

Derived FROM THE DATA, not field names (rates measured, not assumed):

- **`item` <-> `category` (1:1?).** Clean: **0** items map to more than one category
  (every item belongs to exactly one category). `item` also encodes the category as a
  suffix (`Item_10_BEV`). -> a flat denormalized product dimension; category is an
  attribute of item, no fan-out.
- **`total_spent` money identity (derive, never assume).** `total_spent == price_per_unit
  * quantity` holds on **11,362 / 11,362** complete rows = **100.00%**. So `total_spent`
  is fully derivable from the unit price and quantity (RC9: keep as an independent landed
  measure, but silver MAY recompute the 604 blanks from price*qty -- an analyst decision).
- **Returns population & how identified.** **NONE in this source.** No negative or zero
  measure (total_spent 5..410, quantity 1..10, price 5..41 -- all strictly positive), and
  no transaction-type / return-flag column. Confirmed with the data owner: returns exist
  in a SEPARATE figure/system NOT loaded here. RC8 (returns from an authoritative column)
  is **N/A** for this table -- recorded as a deliberate deviation in `assumptions.md`.
- **`discount_applied`.** A discount FLAG (`True`/`False`), NOT a return marker. 33.39%
  blank -- the meaning of blank (unknown vs implicit False) is an OPEN question, not
  auto-decided.
- **Encoding corruption.** None observed in the categorical/text columns (clean ASCII
  category/payment/location values).
- **Outliers.** `total_spent` 5.0..410.0; `quantity` 1.0..10.0; `price_per_unit`
  5.0..41.0 -- no suspicious extremes; the only data-quality concern is missingness.
- **Cross-file schema drift.** N/A -- a single source file; no folded headers to misalign.

---

## Candidate grain & candidate PK

- **Candidate grain:** one row = one retail transaction (a `TXN_*` sale event).
- **Grain ratio:** 12,575 rows vs 12,575 distinct `transaction_id` = **1.00** (one row per
  transaction); vs 25 distinct `customer_id` (a customer makes many transactions).
  *(PROPOSED: whether a transaction is single-item or a basket header is a semantic
  question for the analyst -- there is one row per transaction_id either way; see
  unresolved-questions.)*
- **Candidate PK:** `( transaction_id )`.
- **Uniqueness proof (on the landed data):**
  - `COUNT(*)            = 12,575`
  - `COUNT(DISTINCT pk)  = 12,575`   *(equals `COUNT(*)` -- the PK holds)*
  - `NULLs/empty in PK   = 0`        *(0 -- clean)*

> **Forward seam (RC2).** This is the candidate PK on the LANDED data; the silver build
> must re-prove `transaction_id` unique on the TRANSFORMED output (TRIM/cast can collapse
> or null a key). Landed uniqueness is the candidate, not the final.

---

## Top data-quality issues

1. `discount_applied` 33.39% blank (4,199 / 12,575) -- blank semantics undecided (unknown
   vs False); drives every discount metric downstream.
2. `item` 9.65% missing (1,213) -- a transaction with no product key; how to handle
   (drop / `UNKNOWN` member) is a silver/gold decision.
3. Measure missingness ~4.8% each: `price_per_unit` 609, `quantity` 604, `total_spent`
   604 -- blanks in money/qty; `total_spent` blanks are recomputable (price*qty, 100%
   identity) but the price/quantity blanks are not.

---

## Exit gate

- [x] Grain stated, with the row-vs-entity ratio (1.00 row per transaction).
- [x] Candidate PK stated and proven unique on the landed data (12,575 = 12,575, 0 null).
- [x] Returns rule stated -- N/A for this source (no returns; confirmed with data owner).
- [x] Top data-quality issues listed, each with a measured count.
- [x] Missingness measured as `'' OR NULL` for every column (not `IS NULL` alone).

Source-ready status: **`warning`** -- mechanical numbers are complete, BUT the semantic
proposals (grain single-item-vs-basket, `discount_applied` blank meaning) are unconfirmed
and the `customer_id` PII question is open. Not `pass` until the analyst confirms the
semantics and governance rules on the PII column.

---

## Next artifact

`source-map.yaml` -- the machine-readable spine (per-column keep/drop/rename/type, grain
+ PK decided first, target silver column, gold star placement), authored by the
`source-mapping` skill. This profile is its evidence base.

## See also

- Method: `docs/medallion-playbook.md` Phase 1 + Appendix A; the stage:
  `docs/readiness/source-ready.md`.
- The blank this fills: `templates/source-profile.md`. The readiness state:
  `mappings/retail_store_sales/readiness-status.yaml`.
