# Fresh Source Analysis — `bronze.sales_c086_raw`

> **EXPLORATORY DOC — partially SUPERSEDED.** This was the first-pass analysis. The
> AUTHORITATIVE, final decisions now live in the four gate artifacts in this folder
> (`source-map.yaml`, `source-profile.md`, `assumptions.md`, `unresolved-questions.md`),
> produced by walking the hybrid cleaning chain with the data-owner. Where this doc and
> those artifacts differ, **the artifacts win.** Key changes since this was written:
> - **PK** is now a generated surrogate `Sale_SK` (natural key kept silver-only), NOT the
>   natural composite shown in §1 below.
> - **Measures** are now ONLY `Gross_Sales` + `Quantity` (the §5 multi-measure set was
>   reduced by the data-owner; RC9 deviation).
> - **Filters** have a **3-row overlap**: `513 + 1,680 - 3 = 2,190` (§6 said "no overlap"
>   -- that was WRONG).
> - **PII**: staff names (`person_name`,`buyer`) + company names (`customer_name`) are
>   KEPT (not PII); only `insurance_tel`/`cosm_mg`/`area_mg` dropped as sensitive.
> - **buyer** = product purchaser (counter agent) -> its own `dim_product_purchaser`.
> - **Star** = 6 entity dims + date (added `dim_branch`, `dim_product_purchaser`).
>
> The measured PROFILE numbers below remain valid; the DECISIONS are superseded as noted.
>
> Source: `ezaby_demo` @ cluster `db-pgsql-fra1-29712` (fra1). Read-only; no DSN committed.

## 1. Shape & grain (mechanical, via `profile.py`)

- **Rows:** 249,106  |  **Columns:** 48 (46 business `text` + 2 lineage)
- **All business columns landed as `text`** — faithful bronze landing; missingness
  measured as `'' OR NULL` (RC5), never `IS NULL` alone.
- **Grain — invoice line item.** Candidate keys tested on the live data:

  | Candidate | distinct | null/blank | unique |
  |---|---:|---:|:--:|
  | `reference_no` | 102,818 | 0 | ✗ (per-invoice, not per-line) |
  | `billing_document` | 102,818 | 0 | ✗ (invoice header) |
  | `fi_document_no` | 89,887 | 33,809 | ✗ (13.6% blank) |
  | **`billing_document` + `item_no`** | **249,106** | **0** | **✓** |
  | `billing_document`+`item_no`+`material` | 249,106 | 0 | ✓ (redundant 3rd col) |

  → **PK = (`billing_document`, `item_no`)** — minimal, unique, non-null on all
  249,106 rows. ~2.4 lines per invoice (102,818 invoices).

## 2. Column classification (from measured missingness + cardinality)

**Constant / zero-signal — DROP candidates (verified single-valued):**
| Column | Finding |
|---|---|
| `knumv` | 100% empty |
| `ref_return_date` | 100% empty |
| `cosm_mg` | 1 value (`وائل حامد`) — single manager constant |
| `area_mg` | 1 value (`Ahmed Hashem`) — single manager constant |
| `site` | 1 value (`C086`) — single store |
| `site_name` | 1 value (`الترعة البولاقية`) — single store |

`site`/`site_name` are a **single-branch constant** for this extract — they pin the
branch rather than vary, so a `dim_branch` here has exactly one member (decide:
drop-to-constant vs. keep a 1-row dim for conformance with multi-store future loads
— **judgment call**, see §5).

**High-missing attributes (keep but flag):** `certification` 67.96%,
`assignment` 46.88%, `insurance_tel`/`insurance_no` 38.14%, `item_cluster` 32.01%,
`fi_document_no` 13.57%, `person_name`/`position` 8.85%. `crm_order` 99.52% and
`ref_return` 95.04% are near-empty but **not** zero-signal (see returns, §4).

**PII present — default DROP unless governance signs off (§5):**
`person_name`, `buyer`, `customer_name`, `cosm_mg`, `area_mg` (person names),
`insurance_tel`, `insurance_no` (patient-health-adjacent identifiers).

**DATA-QUALITY DEFECT — `customer` field contaminated with the site code:**
**85,911 rows (34.5%)** carry `customer = 'C086'` — the *site* code, not a customer
id. Of 638 distinct customer codes, 637 are real numeric ids; the 638th (`C086`)
is the store itself and appears on a third of all rows. This is almost certainly
**walk-in / cash retail sales** booked against the branch rather than a named
account. It does NOT affect the PK (still unique), but a naive `dim_customer`
would gain an 85,911-row "customer" that is really *no customer*. Must be modeled
as an explicit member (e.g. "Walk-in / Cash"), never silently mapped as a customer
named `C086`. → judgment call §7.6.

## 3. Candidate dimensions (fan-out tested 1:1 on live data)

| Dimension | id column | id→name fan-out | members |
|---|---|---|---:|
| product | `material` → `material_desc` | **1:1** | 9,690 |
| customer | `customer` → `customer_name` | **1:1** (638 ids, 512 names) | 638 ⚠️ incl. 1 contaminated `C086` on 85,911 rows — see §2 |
| salesperson | `personel_number` → `person_name` | **1:1** | 257 |
| billing_type | `billing_type_2` / `billing_type` | code↔label 1:1 | 10 |
| date | derived from `date` | — | span 2023-01-01 .. 2025-12-31 |
| branch | `site` | single value | 1 |

**Product hierarchy is MULTI-PARENT — keep flat.** 36 subcategories roll up to
more than one `category`. A strict `category→subcategory` snowflake is invalid;
the hierarchy attributes (`category`, `subcategory`, `segment`, `brand`,
`mat_group`) must be kept flat on the product dim, overlaps preserved.

## 4. Returns mechanism — DERIVED from the billing code (not the money sign)

The Arabic `billing_type` and the `billing_type_2` Z-codes align exactly. Codes
containing `مرتجع` ("return") carry negative `avg_net`; the rest are positive:

| `billing_type_2` | `billing_type` (ar) | rows | avg_net | return? |
|---|---|---:|---:|:--:|
| FP | اجل (credit) | 147,479 | +186.27 | no |
| Z1 | فورى (cash) | 88,433 | +115.01 | no |
| Z5 | مرتجع اجل | 7,283 | −244.30 | **yes** |
| Z4 | مرتجع فورى | 4,595 | −171.21 | **yes** |
| Z10 | Pick-Up Return | 376 | −647.05 | **yes** |
| Z6 | مرتجع توصيل | 80 | −1646.92 | **yes** |
| Z8 | مرتجع توصيل-اجل | 31 | −124.82 | **yes** |
| Z9/Z3/Z7 | pickup/delivery (non-return) | 829 | positive | no |

→ Propose `is_return := billing_type_2 IN ('Z4','Z5','Z6','Z8','Z10')`, with an
explicit Arabic→English billing-type map and a loud `UNMAPPED` fallback. The
**authoritative returns column** is a Principle-V ruling (§5).

## 5. Money relationships — partial, do NOT invent a global identity

Identity tests across all 249,106 rows:
- `net_sales = gross_sales + dis_tax` → holds for **194,053** rows (78%)
- `gross_sales = salse_not_tax` → holds for **194,053** rows (78%)
- `net_sales = salse_not_tax + tax` → holds for only **86,100** rows (35%)

No money identity holds universally. **Ruling:** keep the source measures
(`gross_sales`, `net_sales`, `tax`, `dis_tax`/discount, `quantity`) as exact
`NUMERIC` (RC7); do **not** synthesize a derived total that is only sometimes
correct. Leading-zero ids (`material`, `customer`, `billing_document`) stay TEXT.

## 6. The 2,190-row bronze→silver reduction — explained by two filters

If silver lands at line grain after filtering, the gap decomposes **exactly**:

| Filter | rows |
|---|---:|
| junk division (`AUX`/`ARCHIVE`/`EL EZABY SERVICES`/blank) | 513 |
| zero-value line (`quantity = 0 AND gross_sales = 0`) | 1,680 |
| overlap (both conditions) | −3 |
| **union** | **2,190** |

`513 + 1,680 − 3 = 2,190`; `249,106 − 2,190 = 246,916`. (CORRECTION: an earlier draft
said "no overlap" — there is a **3-row overlap**.) These two filters together account for
the entire gap.
Whether both filters are *desired* policy is a build decision for the reviewer.

## 7. Open judgment calls (Principle V — human must answer)

1. **Returns column** — confirm `billing_type_2 ∈ {Z4,Z5,Z6,Z8,Z10}` is the
   authoritative return flag, and supply the full Arabic→English billing-type map.
2. **PII publish-safety** — sign-off (or default drop) for the 7 PII columns in §2.
3. **Single-branch handling** — drop `site`/`site_name` to a constant, or keep a
   1-member `dim_branch` for multi-store conformance.
4. **Reconciliation filters** — confirm the two §6 filters are intended silver policy.
5. **Money measures** — confirm keep-all-source-measures, no invented total (§5).
6. **Contaminated `customer` field (§2)** — confirm the 85,911 `customer='C086'`
   rows are walk-in/cash sales, and how to model them: an explicit
   "Walk-in / Cash" customer member vs. routing to the `-1` unknown member. The
   analyst must confirm the business meaning before `dim_customer` is designed.

## Gate

Per the source-mapping rule (constitution Principle IV): **no `silver.*` SQL until
this analysis is reviewed and the §7 judgment calls are answered by a named human.**
This document is the fresh analysis input to that review — it is *not* a build.
