# Source Profile -- `sales_c086`

> First artifact of the source-mapping gate (architecture Sec 5). Phase 1
> (Connect & profile) of the medallion playbook, recorded as a committed record.
> Produced by an **independent** read-only profiling pass via `retail.profile.profile`
> on 2026-06-29 -- NOT copied from the prior c086 worked example. Numbers are
> re-measured against the live `bronze.sales_c086_raw`. ASCII only.

---

## Header

| Field | Value |
|-------|-------|
| Table id | `sales_c086` (El Ezaby pharmacy branch C086 sales) |
| Source system | retail POS / ERP sales export (xlsx, faithfully landed) |
| Landed location | `bronze.sales_c086_raw` (faithful all-TEXT landing) |
| Connection | read-only; credentials from gitignored `.env` / runtime env -- no connection string inlined here |
| Profiled on | `2026-06-29` |
| Profiled by | agent (`retail.profile.profile`, read-only) |
| Source files folded in | `4` files (2023 H1, 2023 H2, 2024 full, 2025 full) -- see cross-file drift check below |

---

## Shape

| Metric | Value |
|--------|-------|
| Row count (landed) | `249,106` |
| Column count (landed) | `48` (46 business `text` + 2 lineage) |
| Schema(s) present | `bronze` |

---

## Per-column profile

Missingness measured as `trim(col) = '' OR col IS NULL` (RC5), not `IS NULL` alone.
Distinct cardinality is `COUNT(DISTINCT trim(col))`.

| Column | Type as landed | Missingness (`'' OR NULL`) | Distinct | Candidate key? | Notes |
|--------|----------------|-----------------------------|----------|----------------|-------|
| `material` | TEXT | 0 / 0.00% | 9,690 | no | product id; 1:1 with `material_desc`; leading-zero -> TEXT |
| `material_desc` | TEXT | 0 / 0.00% | 9,690 | no | product name; 1:1 with `material` |
| `quantity` | TEXT | 0 / 0.00% | 369 | no | qty measure -> NUMERIC |
| `personel_number` | TEXT | 1,748 / 0.70% | 258 | no | salesperson id; 1:1 with `person_name` |
| `person_name` | TEXT | 22,044 / 8.85% | 142 | no | PERSON NAME -> PII |
| `position` | TEXT | 22,044 / 8.85% | 32 | no | salesperson attribute |
| `category` | TEXT | 3 / 0.00% | 88 | no | product hierarchy (flat) |
| `division` | TEXT | 3 / 0.00% | 15 | no | product division; drives junk-row filter |
| `customer_name` | TEXT | 0 / 0.00% | 512 | no | customer name -> PII |
| `brand` | TEXT | 284 / 0.11% | 3,420 | no | product attribute |
| `item_cluster` | TEXT | 79,734 / 32.01% | 7 | no | product attribute; high-missing |
| `subcategory` | TEXT | 3 / 0.00% | 243 | no | product hierarchy; MULTI-PARENT (see semantics) |
| `segment` | TEXT | 3 / 0.00% | 699 | no | product hierarchy (flat) |
| `billing_type` | TEXT | 0 / 0.00% | 10 | no | Arabic billing label; 1:1 with `billing_type_2`; returns signal |
| `certification` | TEXT | 169,302 / 67.96% | 19,742 | no | high-missing; low signal |
| `assignment` | TEXT | 116,776 / 46.88% | 12,820 | no | high-missing; low signal |
| `salse_not_tax` | TEXT | 0 / 0.00% | 7,234 | no | ~= `gross_sales` on 78% rows (RC9 dup candidate) |
| `fi_document_no` | TEXT | 33,809 / 13.57% | 89,887 | no | finance doc ref; 13.6% blank -> NOT a PK |
| `insurance_tel` | TEXT | 95,018 / 38.14% | 10,108 | no | PATIENT PII (phone) -> drop |
| `insurance_no` | TEXT | 95,018 / 38.14% | 14,436 | no | PATIENT PII (claim no) -> drop |
| `dis_tax` | TEXT | 0 / 0.00% | 4,555 | no | discount measure -> NUMERIC |
| `paid` | TEXT | 0 / 0.00% | 15,891 | no | operational (cash paid); not a sales measure |
| `kzwi1` | TEXT | 0 / 0.00% | 6,504 | no | SAP condition value; ~= `salse_not_tax` |
| `crm_order` | TEXT | 247,912 / 99.52% | 579 | no | 99.5% empty; near-no-signal |
| `buyer` | TEXT | 6 / 0.00% | 17 | no | PERSON NAME -> PII |
| `item_status` | TEXT | 0 / 0.00% | 7 | no | product lifecycle attribute |
| `subtotal5_discount` | TEXT | 0 / 0.00% | 4,069 | no | ~= `dis_tax` (RC9 dup candidate) |
| `tax` | TEXT | 0 / 0.00% | 3,929 | no | tax measure -> NUMERIC |
| `add_dis` | TEXT | 0 / 0.00% | 1,344 | no | additional discount; operational |
| `customer` | TEXT | 0 / 0.00% | 638 | no | customer id; **85,911 rows = site code `C086`** (DQ defect, see issues) |
| `mat_group` | TEXT | 0 / 0.00% | 536 | no | product material group |
| `mat_group_2` | TEXT | 0 / 0.00% | 536 | no | product material group code; 1:1 with `mat_group` |
| `item_no` | TEXT | 0 / 0.00% | 44 | **part-of-composite** | line number within invoice -> PK part |
| `knumv` | TEXT | 249,106 / 100.00% | 1 | no | 100% empty -> DROP (RC3) |
| `billing_document` | TEXT | 0 / 0.00% | 102,818 | **part-of-composite** | invoice id -> PK part; leading-zero TEXT |
| `billing_type_2` | TEXT | 0 / 0.00% | 10 | no | Z-code billing type; AUTHORITATIVE returns column |
| `cosm_mg` | TEXT | 0 / 0.00% | 1 | no | single value (manager name) -> constant; PII |
| `area_mg` | TEXT | 0 / 0.00% | 1 | no | single value (manager name) -> constant; PII |
| `date` | TEXT | 0 / 0.00% | 1,094 | no | sale date -> DATE; drives date dim |
| `reference_no` | TEXT | 0 / 0.00% | 102,818 | no | per-INVOICE reference (= invoice count, not per-line) |
| `site` | TEXT | 0 / 0.00% | 1 | no | single value `C086` -> single-branch constant |
| `site_name` | TEXT | 0 / 0.00% | 1 | no | single value -> single-branch constant |
| `gross_sales` | TEXT | 0 / 0.00% | 4,939 | no | gross measure -> NUMERIC |
| `net_sales` | TEXT | 0 / 0.00% | 11,730 | no | net measure -> NUMERIC |
| `ref_return` | TEXT | 236,741 / 95.04% | 4,183 | no | original-invoice ref on returns (95% blank as expected) |
| `ref_return_date` | TEXT | 249,106 / 100.00% | 1 | no | 100% empty -> DROP (RC3) |
| `_source_file` | TEXT | 0 / 0.00% | 4 | no | lineage (loader) |
| `_loaded_at` | timestamptz | 0 / 0.00% | 4 | no | lineage (loader) |

---

## Semantics

Derived from the data, not field names.

- **Code <-> label pairs.** `billing_type_2` (Z-code) <-> `billing_type` (Arabic): 1:1
  on the data (10 codes <-> 10 labels). The Arabic label is human-readable; the Z-code
  is the stable join key -- keep the code, the label is a drop/attribute candidate.
- **Dimension fan-out (`id -> name` 1:1?).** All three candidate dims are 1:1 at the id
  level: `material -> material_desc` (9,690 ids -> 9,690 pairs); `customer -> customer_name`
  (638 ids -> 638 pairs, 512 distinct names -- shared names across ids, but each id has
  one name); `personel_number -> person_name` (257 ids -> 257 pairs). 0 fan-out violations.
- **Hierarchy nesting.** `category` / `subcategory`: NOT a clean tree -- **36 subcategories
  roll up to more than one category** (multi-parent). Forcing a single parent destroys real
  overlap -> model the product hierarchy as FLAT denormalized levels (RC12), not a snowflake.
- **Returns population & identification.** Identified from the AUTHORITATIVE column
  `billing_type_2`, NOT a measure sign. The five Z-codes whose Arabic label means
  return (transliterated `murtaja`) -- `Z4, Z5, Z6, Z8, Z10` -- carry negative `avg_net` (e.g. Z5 -244.30,
  Z6 -1646.92); the rest (`FP, Z1, Z9, Z3, Z7`) are positive. Return rows:
  `12,365 / 249,106` (`4.96%`) = sum of Z4(4,595)+Z5(7,283)+Z6(80)+Z8(31)+Z10(376).
- **Encoding.** Arabic display columns (`customer_name`, `billing_type`, `site_name`,
  `cosm_mg`) render correctly (UTF-8); no mojibake observed in the sampled rows.
- **Outliers.** Money columns carry legitimate negatives on return rows (by design).
  `quantity` range includes fractional units (e.g. `0.5`) -- pharmacy part-pack sales,
  not an error.
- **Cross-file schema drift.** 4 files folded into one header. Profiled per file: each
  file covers a DISJOINT date range (2023-H1, 2023-H2, 2024, 2025) with stable categorical
  cardinality (12-15 divisions, 9-10 billing codes). No column-order misalignment found
  -> **drift: no**.
- **Money-relationship checks (derived).** `net_sales = gross_sales + dis_tax` holds on
  `194,053 / 249,106` (`77.9%`); `gross_sales = salse_not_tax` on `194,053` (`77.9%`);
  `net_sales = salse_not_tax + tax` on only `86,100` (`34.6%`). NO identity holds
  universally. (Decision: rather than keep all independent measures, the data-owner kept
  ONLY `Gross_Sales` + `Quantity` -- an RC9 deviation, see assumptions.md / Q5.)

---

## Candidate grain & PK

- **Grain:** one row = one **invoice line item**.
- **Grain ratio:** `249,106` lines vs `102,818` invoices = **`2.42` lines/invoice**.
- **Chosen PK (decision):** a **generated surrogate `Sale_SK`** over the post-filter
  silver rows (`1..246,916`). The **natural key `(billing_document, item_no)`** is
  retained in **silver only** as the uniqueness/dedup proof and is NOT exposed to gold
  (surrogate-PK pattern). `reference_no` is kept as a degenerate (invoice-level) attribute.
- **Natural-key uniqueness proof (landed data, via `profile.py`):**
  - `COUNT(*)            = 249,106`
  - `COUNT(DISTINCT (billing_document,item_no)) = 249,106`  (= COUNT(*))
  - `NULLs in key columns = 0`  -> `is_unique = True`

Rejected as PK: `reference_no` / `billing_document` alone (102,818 distinct = invoice
grain, not line); `fi_document_no` (33,809 blank, 13.6%).

> Forward seam (RC2): the natural-key uniqueness above is on the LANDED data; the silver
> migration must RE-VERIFY it on the TRANSFORMED, post-filter output. The surrogate
> `Sale_SK` is unique by construction, so the natural key remains the meaningful proof.

---

## Top data-quality issues

1. **`customer` field contaminated with the site code** -- 85,911 rows (34.5%) have
   `customer = 'C086'` (the branch), not a customer id. Walk-in/cash sales. This is a
   VALUE REMAP, not a missing value -- handled via derived `Customer_ID_Clean`
   (`'C086' -> 'WALK_IN'`); `dim_customer` is keyed on the clean value. (Q6, ANSWERED.)
2. **2,190-row reduction bronze->silver** -- 513 junk-division rows
   (`AUX`/`ARCHIVE`/`EL EZABY SERVICES`/blank) + 1,680 zero-value rows (qty=0 AND gross=0),
   with a **3-row overlap**: `513 + 1,680 - 3 = 2,190` -> silver = 246,916. ORDERING: the
   blank-division filter must run PRE-sentinel (before `Division` gets `'UNCLASSIFIED'`),
   else the 3 blank-division rows survive. (Q4, ANSWERED.)
3. **Many money columns; only 2 measures kept** -- of `gross_sales`, `net_sales`, `tax`,
   `dis_tax`, `salse_not_tax`, `subtotal5_discount`, `kzwi1`, `add_dis`, `paid`, the
   data-owner kept ONLY `Gross_Sales` + `Quantity` as fact measures; the rest dropped.
   (Q5, ANSWERED -- an RC9 deviation, recorded in assumptions.md.)
4. **Sensitive PII vs business names** -- `insurance_tel` (patient phone), `cosm_mg`,
   `area_mg` (manager personal names) are sensitive -> DROPPED. `person_name`/`buyer`
   (STAFF names for KPIs) and `customer_name` (B2B COMPANY names) are NOT personal PII ->
   KEPT as business attributes. (Q2, ANSWERED.)
5. **2 fully-empty columns** (`knumv`, `ref_return_date`) + **single-value constants**
   (`cosm_mg`, `area_mg` -> dropped). `site`/`site_name` are single-valued but KEPT as a
   1-member `dim_branch` for multi-store conformance (Q3, ANSWERED).

---

## Exit gate

- [x] Grain stated, with row-vs-entity ratio (2.42 lines/invoice).
- [x] Candidate PK stated and proven unique on landed data (249,106 = 249,106, 0 NULL).
- [x] Returns rule stated, from the authoritative column (`billing_type_2` Z-codes).
- [x] Top data-quality issues listed, each with a measured count.
- [x] Missingness measured as `'' OR NULL` for every column.

Profile complete. Proceed to `source-map.yaml`. **Gate stays shut for silver until the
mapping is reviewed and the unresolved questions are answered.**

## See also

- Method: `docs/medallion-playbook.md` Phase 1 + Appendix A.
- Defaults: `docs/decisions/0002-retail-cleaning-defaults.md` (RC1, RC2, RC5).
- Sibling artifacts: `source-map.yaml`, `assumptions.md`, `unresolved-questions.md`,
  `reconciliation-report.md` (this folder).
- Prior worked example (reference, not reused): `docs/worked-examples/c086-pharmacy.md`.
