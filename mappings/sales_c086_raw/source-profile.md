# Source Profile -- `sales_c086_raw`

> Filled instance of `templates/source-profile.md` for the C086 pharmacy branch sales
> export, landed into the `Ex-1` DB bronze layer. Stage 1 (Source Ready) of the
> readiness spine. Mechanical numbers measured over a READ-ONLY connection via
> `seshat.profile.profile()` against `bronze.sales_c086_raw`; semantic rows below are
> PROPOSED for human confirmation, not asserted as fact.

---

## Header

| Field | Value |
|-------|-------|
| Table id | `sales_c086_raw` |
| Source kind | `db-table` |
| Source system | Pharmacy branch (site `C086`) sales export, folded from multiple periodic Excel exports (see `_source_file` lineage) |
| Landed location | `bronze.sales_c086_raw` (faithful all-TEXT landing + `_source_file`/`_loaded_at` lineage) |
| Connection | read-only; credentials from the gitignored `.env` at runtime -- no connection string committed |
| Profiled on | 2026-07-16 |
| Profiled by | agent (`seshat.profile.profile()`, read-only session over `doctl`-provisioned Postgres) |
| Source files folded in | 4 distinct values in `_source_file` (e.g. `C086_Sales_2023_H1_Jan-Jun.xlsx`) -- see Cross-file schema drift below |

---

## Shape

| Metric | Value |
|--------|-------|
| Row count (landed) | 249,106 |
| Column count (landed) | 46 source columns (+ 2 lineage: `_source_file`, `_loaded_at`) |
| Schema(s) present | `bronze` (this table); `silver`/`gold` not yet created |

---

## Per-column profile

Missingness measured as `'' OR NULL` (RC5 -- a faithful landing writes `''` for blank,
so `IS NULL` alone would report 0). All source columns landed as `TEXT`. Numbers from
`seshat.profile.profile()` against the live table.

| Column | Type as landed | Missingness (`'' OR NULL`, count / %) | Distinct cardinality | Candidate key? | Notes |
|--------|----------------|----------------------------------------|----------------------|----------------|-------|
| `material` | TEXT | 0 / 0.00% | 9,690 | no | product code; 1:1 with `material_desc` (0 fan-out) |
| `material_desc` | TEXT | 0 / 0.00% | 9,690 | no | product description; 1:1 with `material` |
| `quantity` | TEXT | 0 / 0.00% | 369 | no | float-as-text; sign does NOT reliably indicate a return (see Semantics) |
| `personel_number` | TEXT | 1,748 / 0.70% | 258 | no | staff id (pharmacist/seller) |
| `person_name` | TEXT | 22,044 / 8.85% | 142 | no | staff display name; Arabic text confirmed clean (no mojibake) |
| `position` | TEXT | 22,044 / 8.85% | 32 | no | staff role; missingness co-occurs exactly with `person_name` (same 22,044) |
| `category` | TEXT | 3 / 0.00% | 88 | no | product category; 1:1 with `material` (0 fan-out) |
| `division` | TEXT | 3 / 0.00% | 15 | no | e.g. `RX`, `OTC` |
| `customer_name` | TEXT | 0 / 0.00% | 512 | no | Arabic pharmacy/customer display name; 1:1 with `customer` (0 fan-out) |
| `brand` | TEXT | 284 / 0.11% | 3,420 | no | product brand |
| `item_cluster` | TEXT | 79,734 / 32.01% | 7 | no | e.g. `A`/`B`/`C`; RULED 2026-07-16 (data owner): blank = unknown/missing (measured as a stable per-material attribute -- 0/9,690 materials show mixed blank/non-blank -- but ruled unknown/missing rather than a real "no cluster" category) |
| `subcategory` | TEXT | 3 / 0.00% | 243 | no | product subcategory |
| `segment` | TEXT | 3 / 0.00% | 699 | no | therapeutic/marketing segment |
| `billing_type` | TEXT | 0 / 0.00% | 10 | no | **authoritative returns/billing-type column** (Arabic); see Semantics |
| `certification` | TEXT | 169,302 / 67.96% | 19,742 | no | **DROPPED 2026-07-16 (data owner)** -- population rate varies by division (0% Cosmetics .. ~38% RX/OTC) with no clean applicability pattern; owner chose to drop the column rather than guess its meaning |
| `assignment` | TEXT | 116,776 / 46.88% | 12,820 | no | RULED 2026-07-16 (data owner): blank = unknown/missing (measured as 85.5% populated on `billing_type = 'اجل'` credit rows vs 0% on `'فورى'` cash and most other types, consistent with a credit-account reference field -- but ruled unknown/missing rather than structural not-applicable) |
| `salse_not_tax` | TEXT | 0 / 0.00% | 7,234 | no | money-like column (sic -- source-named "salse_not_tax"); numeric-clean |
| `fi_document_no` | TEXT | 33,809 / 13.57% | 89,887 | no | FI/accounting document reference; NOT unique alone (rejected as PK, see below) |
| `insurance_tel` | TEXT | 95,018 / 38.14% | 10,108 | no | **PII** -- insurance contact phone |
| `insurance_no` | TEXT | 95,018 / 38.14% | 14,436 | no | **PII** -- insurance policy number; missingness co-occurs exactly with `insurance_tel` |
| `dis_tax` | TEXT | 0 / 0.00% | 4,555 | no | money; discount-tax component |
| `paid` | TEXT | 0 / 0.00% | 15,891 | no | money |
| `kzwi1` | TEXT | 0 / 0.00% | 6,504 | no | money-like SAP condition-value field (kzwi1 is a standard SAP pricing-procedure field name) |
| `crm_order` | TEXT | 247,912 / 99.52% | 579 | no | CRM order reference; almost entirely blank -- likely applies to a small order channel only |
| `buyer` | TEXT | 6 / 0.00% | 17 | no | buyer/purchaser code |
| `item_status` | TEXT | 0 / 0.00% | 7 | no | `ACTIVE` / `DELISTED` / `CANCELLED` / `-T` suffix variants |
| `subtotal5_discount` | TEXT | 0 / 0.00% | 4,069 | no | money |
| `tax` | TEXT | 0 / 0.00% | 3,929 | no | money |
| `add_dis` | TEXT | 0 / 0.00% | 1,344 | no | money; additional discount |
| `customer` | TEXT | 0 / 0.00% | 638 | no | customer/pharmacy code; 1:1 with `customer_name` |
| `mat_group` | TEXT | 0 / 0.00% | 536 | no | material group description (long, descriptive) |
| `mat_group_2` | TEXT | 0 / 0.00% | 536 | no | material group short code; 1:1 candidate with `mat_group` (not yet verified row-rate) |
| `item_no` | TEXT | 0 / 0.00% | 44 | **part-of-composite (PK)** | line-item sequence number within a document; combined with `billing_document` or `reference_no` gives a unique grain key |
| `knumv` | TEXT | 249,106 / 100.00% | 1 | no | **entirely blank** (100% missing, 1 distinct = the blank itself) -- drop candidate (RC3) |
| `billing_document` | TEXT | 0 / 0.00% | 102,818 | **part-of-composite (PK)** | invoice/document header id; unique combined with `item_no` |
| `billing_type_2` | TEXT | 0 / 0.00% | 10 | no | short code parallel to `billing_type` (e.g. `FP`, `Z1`..`Z10`); 1:1 candidate, not yet verified |
| `cosm_mg` | TEXT | 0 / 0.00% | 1 | no | single distinct value across all rows -- drop candidate (RC3) |
| `area_mg` | TEXT | 0 / 0.00% | 1 | no | single distinct value across all rows -- drop candidate (RC3) |
| `date` | TEXT | 0 / 0.00% | 1,094 | no | `YYYY-MM-DD[ 00:00:00]`; range 2023-01-01 .. 2025-12-31 -> dim_date FK |
| `reference_no` | TEXT | 0 / 0.00% | 102,818 | **part-of-composite (PK)** | ALSO unique combined with `item_no`; NOT row-identical to `billing_document` despite equal distinct count (0 / 249,106 rows match) -- see Semantics |
| `site` | TEXT | 0 / 0.00% | 1 | no | single distinct value (`C086`) across all rows -- this table is single-branch; a drop candidate within-table, but load-bearing if/when folded with other branches |
| `site_name` | TEXT | 0 / 0.00% | 1 | no | single distinct value (Arabic branch name) -- same as `site` |
| `gross_sales` | TEXT | 0 / 0.00% | 4,939 | no | money; numeric-clean |
| `net_sales` | TEXT | 0 / 0.00% | 11,730 | no | money; numeric-clean; identity vs gross/tax/discount holds on 90.4% of rows (see Semantics) |
| `ref_return` | TEXT | 236,741 / 95.04% | 4,183 | no | cross-reference to the ORIGINAL invoice being returned against; populated only on a subset of return rows -- NOT itself the returns flag |
| `ref_return_date` | TEXT | 249,106 / 100.00% | 1 | no | **entirely blank** (100% missing) -- drop candidate (RC3) or a field never populated by this export |

Lineage columns `_source_file` (TEXT, 4 distinct values, 0 missing) and `_loaded_at`
(TIMESTAMPTZ, 4 distinct values, 0 missing) are infrastructure, not part of the mapped
grain -- excluded from the per-column missingness scan above, per the worked-example
convention. `seshat.profile.profile()` ran cleanly against both lineage columns on this
table (no timestamptz defect encountered here).

---

## Semantics

Derived FROM THE DATA, not field names (rates measured, not assumed):

- **`material` <-> `material_desc` (1:1?).** Clean: **0** materials map to more than one
  description. -> a flat product dimension, no fan-out.
- **`material` <-> `category` (1:1?).** Clean: **0** materials map to more than one
  category.
- **`customer` <-> `customer_name` (1:1?).** Clean: **0** customer codes map to more than
  one name.
- **Returns population & how it is identified.** Identified from the **authoritative
  column** `billing_type` (Arabic text), values `مرتجع اجل` / `مرتجع فورى` / `مرتجع توصيل`
  ("return, credit / immediate / delivery") and `billing_type_2` (`Z5`, `Z4`, `Z6`).
  Returns rows: **11,989 / 249,106** (4.81%). *(RC8, confirmed by measurement, NOT by
  sign: **1,667** return rows carry a non-negative `quantity`, and **363** non-return
  rows carry a negative `quantity` -- the measure sign alone would misclassify 2,030
  rows. `ref_return` is a secondary cross-reference to the original invoice, populated
  on only a subset of return rows -- it is not itself a reliable returns flag.)*
- **Money-relationship check (derive, never assume).** `gross_sales + dis_tax + add_dis -
  tax == net_sales` (rounded to 2dp) holds on **225,191 / 249,106** rows = **90.4%**. Seven
  alternative formulas were tested (substituting/adding `subtotal5_discount`,
  `salse_not_tax`, `kzwi1`, `paid` in various combinations); none improved on 90.4%. Of the
  23,915 mismatching rows, only 4,723 (19.7%) are rounding noise (residual `<= 0.01`); the
  remaining 19,192 (80.3%) carry a material residual (avg **6.18**, range **-921.04 ..
  5225.44**) that no tested column combination explains. The mismatch rate is
  approximately uniform (~10-11%) across every `billing_type` value, ruling out a
  returns-specific or channel-specific cause.
  **RULED 2026-07-16 (data owner):** landed `net_sales` is **unreliable** and will **not**
  be reconciled against or carried forward as a trusted measure. A net-sales calculation
  will instead be authored from first principles (`gross_sales`, `tax`, discount columns)
  during `source-map.yaml` / the silver build, independent of this column.
- **Encoding corruption.** None observed: 152,900 rows carry Arabic-script text in
  `customer_name` and it decodes cleanly (no `?`/replacement-character mojibake found in
  a scripted scan).
- **Cross-file schema drift.** `_source_file` carries 4 distinct values (multiple periodic
  exports folded into one table, e.g. `C086_Sales_2023_H1_Jan-Jun.xlsx`). Per-file column
  drift was NOT yet profiled (would require grouping the categorical distributions above
  by `_source_file`) -- flagged as an open follow-up, not yet measured.
- **`billing_document` vs `reference_no`.** Both have identical distinct-value counts
  (102,818) and both form a unique grain key when paired with `item_no`, but they are
  **NOT the same value per row**: `trim(billing_document) = trim(reference_no)` holds on
  **0 / 249,106** rows. These are two DIFFERENT document-numbering schemes over the same
  invoice population (candidate: one is-a internal billing doc #, the other an external/
  reference doc #) -- which one is the durable grain key is a data-owner decision, not
  assumed here.
- **Outliers.** Money columns (`gross_sales`, `net_sales`, `tax`, `dis_tax`, `add_dis`,
  `paid`, `subtotal5_discount`, `kzwi1`, `salse_not_tax`) are all 100% numeric-parseable
  after `trim()` (0 parse-failure rows each). On the SILVER output, `gross_sales` ranges
  `-38,180.00 .. 325,000.00`; the top values are legitimately expensive specialty drugs
  (KEYTRUDA, PRIVIGEN, BRUKINSA) at plausible per-unit prices, not data errors.
  **Investigated 2026-07-16**: a 5-invoice cluster (`reference_no` C0860000190130/
  190131/190132/190134/190136, all site C086, all date 2023-11-21, 5 different staff
  including one branch manager) each pairs one bulk `FROST 100ML SPRAY` line (295-370
  units, ~115 EGP/unit -- gross_sales up to 42,550.00) with one `OZEMPIC` pen line
  (`item_status = DELISTED`). Initial read flagged the ~44% discount rate on the FROST
  lines as anomalous; a BROADER SEARCH across the full table found the exact same
  -43.9% / -43.7% / -50.0% / -87.7% discount tiers recurring on 100+ unrelated rows
  (different products, staff, and dates spanning 2023-2025) -- this is a standard,
  system-wide discount-tier pattern, NOT unique to this cluster, and the initial
  suspicion of it was a false alarm corrected on further investigation. What remains
  genuinely unusual, and is recorded here for awareness (not escalated as a compliance
  finding, since no anomaly beyond volume was substantiated): an unusually large
  single-line quantity (295-370 units, vs a typical 1-2 units for this product)
  repeated across 5 near-identical invoices, same site, same day, paired each time with
  a delisted RX product. No row-level action taken -- kept as-is in silver, per the
  no-filtering outlier policy agreed for this table.

---

## Candidate grain & candidate PK

- **Candidate grain:** one row = one billing-document line item (one product line within
  one invoice/document).
- **Grain ratio:** 249,106 rows vs 102,818 distinct `reference_no` = **2.42** line
  items per document.
- **Candidate PK -- RULED 2026-07-16 (data owner):** `( reference_no, item_no )`.
  - **Basis for the ruling:** `billing_document` and `reference_no` both prove unique
    paired with `item_no` (see proofs below), but disagree row-for-row (0 / 249,106
    match, see Semantics). `reference_no` is uniformly formatted (`C086` + 10 digits,
    site code embedded) across all 249,106 rows. `billing_document` splits into a
    `'0'`-prefix population (215,297 rows) and a letter-`'O'`-prefix population (33,809
    rows) that exactly matches the blank-`fi_document_no` population -- indicating
    `billing_document` conflates two different document/channel types (e.g. a posted-vs-
    unposted or in-store-vs-pickup distinction) under one column. `reference_no` shows no
    such split. `billing_document` is **rejected** as the grain PK.
- **Uniqueness proof (on the landed data), `( reference_no, item_no )` -- SELECTED:**
  - `COUNT(*)            = 249,106`
  - `COUNT(DISTINCT pk)  = 249,106`   *(equals `COUNT(*)` -- the PK holds)*
  - `NULLs/empty in PK   = 0`         *(0 -- clean)*
- **Uniqueness proof (on the landed data), `( billing_document, item_no )` -- REJECTED
  despite holding:**
  - `COUNT(*)            = 249,106`
  - `COUNT(DISTINCT pk)  = 249,106`   *(equals `COUNT(*)` -- mechanically unique, but
    rejected on the format-split evidence above)*
  - `NULLs/empty in PK   = 0`
- **Rejected candidate:** `( fi_document_no, item_no )` -- `fi_document_no` is 13.57%
  blank (33,809 rows), giving `COUNT(DISTINCT pk) = 215,334` and `33,809` null-PK rows.
  Not unique; not a candidate key.

> **Forward seam to the silver build (ADR 0002 RC2).** What is recorded here is the
> candidate PK on the **landed** data. RC2 requires the PK to be **re-verified on the
> TRANSFORMED output** during the silver build (Phase 5) -- `TRIM`/cast can collapse two
> raw-distinct keys or null a key. This profile establishes two competing candidates; the
> silver migration must re-prove whichever one `source-map.yaml` selects.

---

## Top data-quality issues

1. ~~**Two competing, mutually-inconsistent PK candidates**~~ -- **RESOLVED 2026-07-16**:
   ruled `( reference_no, item_no )` (see Candidate grain & PK above). `billing_document`
   rejected -- its `'0'`/`'O'` prefix split conflates two document/channel types.
2. ~~**Money-identity mismatch on 23,915 / 249,106 rows (9.6%)**~~ -- **RESOLVED
   2026-07-16**: ruled landed `net_sales` unreliable; will not be reconciled or carried
   forward. A net-sales measure will be derived from first principles downstream instead
   (see Semantics above for the full residual analysis).
3. ~~**Heavy PII exposure**~~ -- **RESOLVED 2026-07-16**: `person_name` confirmed as
   staff/employee data (sample roles: driver/سائق, cashier/موظف كاشير, pharmacist/صيدلى,
   branch manager/مدير صيدلية) -- ruled mask/pseudonymize before downstream exposure.
   `customer_name` confirmed as predominantly B2B/institutional (insurance companies,
   pharma distributors, branch names; only 517/249,106 rows show a redacted-looking hash
   pattern) -- ruled low risk, keep as-is. `insurance_tel`/`insurance_no` (61.9% populated
   each, only ~0.1% placeholder values -- genuine third-party insurance data) -- ruled
   drop entirely, excluded from `source-map.yaml`.
4. **Four columns are 100% or near-100% degenerate**: `knumv` (100% blank), `ref_return_date`
   (100% blank), `cosm_mg` (1 distinct value), `area_mg` (1 distinct value) -- drop
   candidates per RC3, pending data-owner confirmation they carry no forward-looking
   meaning (e.g. `ref_return_date` may simply never have been populated by this export
   vintage).
5. ~~**`item_cluster` 32.01% blank -- meaning undecided**~~ -- **RESOLVED 2026-07-16**:
   ruled unknown/missing (despite measuring as a stable per-material attribute; see
   per-column table above).
6. ~~**`certification`/`assignment` blank-semantics undecided**~~ -- **RESOLVED
   2026-07-16**: `certification` dropped from the model entirely (division-based
   population pattern not clean enough to rule on); `assignment` blank ruled
   unknown/missing (despite measuring as a likely credit-account reference field, see
   per-column table above).

---

## Exit gate

- [x] Grain stated, with the row-vs-entity ratio (2.42 lines per document).
- [x] Candidate PK stated and proven unique on the landed data -- RULED
      `( reference_no, item_no )` 2026-07-16 (data owner); `billing_document` rejected.
- [x] Returns rule stated, from the authoritative column `billing_type` (not a measure
      sign) -- measured, with the sign-alone error quantified (2,030 rows would
      misclassify).
- [x] Top data-quality issues listed, each with a measured count.
- [x] Missingness measured as `'' OR NULL` for every column (not `IS NULL` alone), via
      `seshat.profile.profile()`.

Source-ready status: **`pass`** -- mechanical numbers are complete via
`seshat.profile.profile()`, and all four open items are RULED (2026-07-16, data owner,
see `readiness-status.yaml` approvals[]): (a) PK is `( reference_no, item_no )`, (b)
landed `net_sales` is rejected as unreliable -- a fresh net-sales measure will be derived
downstream, (c) `item_cluster`/`assignment` blanks are ruled unknown/missing and
`certification` is dropped from the model, and (d) PII governance is set: mask
`person_name`, keep `customer_name` as-is, drop `insurance_tel`/`insurance_no` entirely.
Source Ready gate clears; proceed to `source-map.yaml`.

---

## Next artifact

Once this exit gate's open items are resolved by the data owner, proceed to
**`source-map.yaml`** -- the machine-readable spine that records the per-column keep /
drop / rename / type decisions, the grain + PK decided first, the target silver column,
and the gold star placement. This profile is its evidence base.

## See also

- **Method:** `docs/medallion-playbook.md` -- Phase 1 (Connect & profile) and Appendix A.
- **Defaults:** `docs/decisions/0002-retail-cleaning-defaults.md` -- RC1 (lowest grain),
  RC2 (verify PK on transformed data), RC3 (drop single-value/all-blank columns), RC5
  (`'' -> NULL`; missingness as `'' OR NULL`), RC7 (leading-zero/money columns stay TEXT
  until cast), RC8 (returns from an authoritative column, not a measure sign), RC9 (keep
  independent money measures; do not collapse on a name-based assumption).
- **Worked example (a filled instance):** `mappings/retail_store_sales/source-profile.md`
  in the Seshat_BI kit repo.
