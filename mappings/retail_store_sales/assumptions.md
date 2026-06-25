# Assumptions -- `retail_store_sales`

> Per-table record of which ADR 0002 cleaning/modeling defaults (RC1-RC16) this table
> ADOPTED as-is vs DEVIATED from -- the engineering expression of "Defaults Then
> Deviations". Each deviation cites its triggering data fact from `source-profile.md`.

| Field | Value |
|-------|-------|
| Table id | `silver.retail_store_sales` (from `bronze.retail_store_sales`) |
| Date | 2026-06-25 |
| Author | agent (`source-mapping`) |
| Source profile | `mappings/retail_store_sales/source-profile.md` (the profiled evidence) |
| Source map | `mappings/retail_store_sales/source-map.yaml` (the keep/drop/type/grain/star decisions) |
| Per-table ADR | (none yet -- deviations recorded here pending review) |

---

## Defaults adopted as-is

| ADR id | Default summary (generic ruling) | Adopted? | Note |
|--------|----------------------------------|----------|------|
| RC1  | Model at the lowest grain the source provides; decide grain first. | `[OK]` | one row = one transaction |
| RC2  | Verify the PK on the data, and re-verify on the transformed output. | `[OK]` | transaction_id 12,575 = 12,575, 0 null on landed; re-verify in silver |
| RC3  | Drop no-signal columns. | `[OK]` | none here -- all 11 source columns carry signal |
| RC4  | Remove PII/sensitive data before the BI layer, decided early. | `[x]` | DEVIATED -- see below (customer_id kept pending governance) |
| RC5  | `''` -> NULL first; measure missingness as `'' OR NULL`. | `[OK]` | applied to all columns; discount_applied blank NOT coerced to False (Q2) |
| RC6  | NULL for unknown; sentinel only on grouping dims after a no-collision check. | `[OK]` | no sentinel proposed |
| RC7  | Money/qty -> exact NUMERIC; dates -> DATE; leading-zero IDs stay TEXT. | `[OK]` | price/quantity/total -> numeric(12,2); transaction_date -> date; TXN/CUST ids TEXT |
| RC8  | Keep returns; derive `is_return` from the authoritative type column, never the measure sign. | `[x]` | DEVIATED -- see below (no returns in this source) |
| RC9  | Keep the independent money measures; drop only true duplicates. | `[OK]` | keep quantity + total_spent; total_spent = price*qty but kept as landed measure |
| RC10 | Unify categorical encodings; keep the original code if a stable join key. | `[OK]` | category/payment/location values already clean + consistent |
| RC11 | Add business rollups only from an analyst-supplied mapping; never invent. | `[OK]` | no rollup -- category is a source attribute, not invented |
| RC12 | Model a non-tree hierarchy as flat denormalized levels, not a snowflake. | `[OK]` | item->category 1:1 (0 fan-out) -> flat dim_product |
| RC13 | Materialize silver as a TABLE via an idempotent numbered migration. | `[OK]` | for the silver build (downstream) |
| RC14 | Gold is a Kimball star: `_sk` keys, `-1` unknown member + FK COALESCE, degenerate dims. | `[OK]` | fct_sales + 4 dims + dim_date; transaction_id/discount_applied degenerate |
| RC15 | Date dimension is a contiguous generated calendar over the full span. | `[OK]` | generate_series 2022-01-01..2025-01-18 |
| RC16 | Reconcile measure totals at every layer and assert 0 orphan FKs before done. | `[OK]` | for the live validate run (downstream) |

**Integrity invariant:** every `[x]` row has a matching Deviations entry below.

---

## Deviations

**Status for this table:** 2 deviations, listed below.

### Deviation 1 -- RC8 (returns)

| Field | Value |
|-------|-------|
| ADR id | RC8 -- keep returns; derive `is_return` from the authoritative type column |
| What we did instead | No `is_return` column; returns are N/A for this source. |
| Triggering data fact | `source-profile.md`: every measure is strictly positive (total_spent 5..410, quantity 1..10, price 5..41 -- 0 negatives, 0 zeros); there is no transaction-type / return-flag column. The data owner confirmed returns exist in a SEPARATE figure/system not loaded here. |
| Recorded in | this file + `unresolved-questions.md` (Returns category, marked N/A). A future returns source would be onboarded separately. |

### Deviation 2 -- RC4 (PII)

| Field | Value |
|-------|-------|
| ADR id | RC4 -- remove PII/sensitive data before the BI layer (default: drop) |
| What we did instead | `customer_id` is KEPT as `dim_customer` (PROPOSED), pending governance sign-off -- not auto-dropped. |
| Triggering data fact | `source-profile.md`: `customer_id` is a pseudonymous surrogate (`CUST_xx`, 25 distinct), not raw PII (no name/phone/email/address). The default RC4 auto-drop would remove all per-customer analysis for a column that carries no raw identity. |
| Recorded in | this file + `unresolved-questions.md` Q1 (governance must rule before the gate clears). Status: OPEN -- if governance rules drop, the deviation reverts to the RC4 default. |

> No fabricated deviations. These two are forced by the profiled data + the data
> owner's confirmation; both are OPEN/under-review at the gate.

---

## See also

- Method: `../../docs/medallion-playbook.md`; defaults:
  `../../docs/decisions/0002-retail-cleaning-defaults.md` (RC1-RC16).
- Siblings: `source-profile.md`, `source-map.yaml`, `unresolved-questions.md`,
  `reconciliation-report.md`.
