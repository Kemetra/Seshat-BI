# Source Profile -- `C086`

> **SUPERSEDED (2026-07-02).** Historical artifact of the FIRST build (0001/0002);
> it profiles only the columns that build considered. The full live profile of the
> same bronze table (48 landed columns) is
> [`../sales_c086/source-profile.md`](../sales_c086/source-profile.md).
> See [`./README.md`](./README.md).

> **Filled instance** (back-authored from the committed, live-validated warehouse:
> `warehouse/migrations/0001_create_silver_sales_c086.sql`,
> `0002_create_gold_star.sql`, and `docs/c086-adr0002-compliance.md`). This is the
> first artifact of the source-mapping gate (see
> `../../docs/architecture/tower-bi-agent-kit.md` Sec 5). It formalizes Phase 1
> (Connect & profile) of `../../docs/medallion-playbook.md`.
>
> **ASCII only.** Arrows are `->`, pairs `<->`, status `[OK]`/`[x]`.
>
> **Cite numbers, not adjectives.** Counts are sourced from the committed migration
> SQL and the read-only live run of 2026-06-24 (vs the analytics DB; name from `.env`).

---

## Header

| Field | Value |
|-------|-------|
| Table id | `C086` |
| Source system | El Ezaby pharmacy POS / ERP sales export |
| Landed location | `bronze.sales_c086_raw` (faithful all-TEXT landing) |
| Connection | read-only; credentials from the gitignored `.env` at runtime -- no connection string or secret is inlined here |
| Profiled on | `2026-06-24` |
| Profiled by | back-authored from committed 0001/0002 (live-validated) |
| Source files folded in | single export (one landed header; no cross-file fold) |

---

## Shape

| Metric | Value |
|--------|-------|
| Row count (landed) | `249,106` |
| Column count (landed) | `30` (28 mapped + 2 PII dropped) |
| Schema(s) present | `bronze` (landing); downstream `silver`, `gold` |

> Landed bronze row count is `249,106`. The post-clean silver count (`246,916`) is
> recorded in `reconciliation-report.md`, not here. The `2,190`-row reduction is two
> explicit filters (division-junk + zero-value lines), detailed in Top data-quality
> issues below.

---

## Per-column profile

One row per landed column. Missingness is the `'' OR NULL` measure (RC5; a faithful
all-TEXT landing writes `''`, so `IS NULL` alone would falsely report `0`). The
counts below are the structural / decision-bearing facts carried into `source-map.yaml`;
exact per-column missingness percentages were taken in the profiling pass that the
silver build (`0001`) encodes (NULLIF on every cast; sentinel UPDATEs on grouping dims).

| Column | Type as landed | Missingness (`'' OR NULL`, count / %) | Distinct cardinality | Candidate key? | Notes |
|--------|----------------|----------------------------------------|----------------------|----------------|-------|
| `material` | TEXT | low (populated) | many | no | product natural key; leading zeros -> TEXT (RC7) |
| `material_desc` | TEXT | low | many | no | display name; mixed-encoding garbage present -> de-mojibake step |
| `quantity` | TEXT | low | numeric range | no | qty measure; negatives = returns; zero-value lines filtered |
| `gross_sales` | TEXT | low | numeric range | no | gross money; independent of net/tax/discount (RC9) |
| `net_sales` | TEXT | low | numeric range | no | net money; independent measure (RC9) |
| `tax` | TEXT | low | numeric range | no | tax money; independent measure (RC9) |
| `subtotal5_discount` | TEXT | low | numeric range | no | discount money; independent measure (RC9) |
| `reference_no` | TEXT | 0 (PK part) | high | part-of-composite | invoice id; PK part with `item_no`; leading zeros -> TEXT |
| `item_no` | TEXT | 0 (PK part) | low (line ordinals) | part-of-composite | line ordinal; PK part; ordinal -> smallint (RC7) |
| `date` | TEXT | low | ~1,094 days | no | sale date; spans 2023-01-01 .. 2025-12-31 |
| `billing_type` | TEXT | low | 10 distinct labels | no | Arabic labels; mapped Arabic -> English (RC10) |
| `billing_type_2` | TEXT | low | Z-code set | no | authoritative Z-code; is_return source (RC8); kept as join key |
| `customer` | TEXT | low | many | no | customer natural key; leading zeros -> TEXT |
| `customer_name` | TEXT | low | many | no | customer display name |
| `personel_number` | TEXT | some unattributed | many | no | salesperson key; sentinel 'UNKNOWN' (RC6) |
| `person_name` | TEXT | some | many | no | salesperson name; sentinel 'UNKNOWN' (RC6) |
| `position` | TEXT | some | low | no | job title; sentinel 'UNKNOWN' (RC6) |
| `buyer` | TEXT | some | many | no | procurement buyer; retained on silver, not a gold dim |
| `division` | TEXT | low | ~12 divisions | no | top product level; drives business_segment rollup (RC11) |
| `category` | TEXT | low | many | no | product hierarchy level (flat, RC12) |
| `subcategory` | TEXT | low | many | no | product hierarchy level (flat, RC12) |
| `segment` | TEXT | low | many | no | product hierarchy level (flat, RC12) |
| `brand` | TEXT | some | many | no | product brand; sentinel 'UNKNOWN' (RC6) |
| `mat_group` | TEXT | low | many | no | material group; product hierarchy level |
| `item_cluster` | TEXT | some | many | no | merchandising cluster; sentinel 'UNCLASSIFIED' (RC6) |
| `ref_return` | TEXT | high (NULL on non-returns) | many on returns | no | original invoice ref; a fact, left NULL (no fill) |
| `site` | TEXT | low | branch set | no | branch code; leading zeros -> TEXT |
| `site_name` | TEXT | low | branch set | no | branch display name |
| `insurance_no` | TEXT | n/a | n/a | no | patient health PII -> DROPPED early (RC4) |
| `insurance_phone` | TEXT | n/a | n/a | no | patient health PII -> DROPPED early (RC4) |

**Column-table legend**
- *Type as landed* -- all-`TEXT` (faithful bronze landing). Target types are a
  Phase 2.5 decision recorded in `source-map.yaml`, not here.
- *Missingness* -- the `'' OR NULL` measure (RC5). The silver build encodes the exact
  handling: NULLIF on cast columns, sentinel UPDATEs on the grouping dims listed above.
- *Distinct cardinality* -- `COUNT(DISTINCT trim(col))`. No 100%-empty or single-value
  drop-candidates (RC3) were found among the 28 kept columns.
- *Candidate key?* -- only `reference_no` + `item_no` form the composite PK.
- *Notes* -- the decision driver carried into `source-map.yaml`.

---

## Semantics

Derived from the data, not field names.

- **Code <-> label pairs.** `billing_type_2` (Z-code) <-> `billing_type` (Arabic label):
  the label is mapped to one English standard (RC10); the Z-code is kept separately as
  the authoritative join key and is_return source -- so the code half is NOT dropped
  (RC3 exception: it is a stable join key).
- **Dimension fan-out (`id -> name` 1:1?).** `customer` -> `customer_name`,
  `personel_number` -> `person_name`, `site` -> `site_name`, `material` ->
  `material_desc`: modeled as flat denormalized dim attributes; no fan-out forced a
  bridge. Salesperson attribution has a known gap (71 line items unattributed -> the
  `-1` member; see reconciliation report).
- **Hierarchy nesting.** Product levels (`division` / `category` / `subcategory` /
  `segment` / `brand` / `mat_group` / `item_cluster`): NOT a clean single-parent tree
  -- multi-parent overlaps exist -> kept as flat denormalized levels in one
  `dim_product` (RC12), never snowflaked.
- **Returns population & how it is identified.** Identified from the authoritative
  column `billing_type_2` (Z-codes `Z4`/`Z5`/`Z6`/`Z8`/`Z10`), NOT the sign of a
  measure. The measure sign alone misses zero-value and edge-case returns (RC8).
- **Encoding corruption.** `material_desc` carries mixed-encoding / mojibake garbage ->
  a whitelist `regexp_replace` (keep chr 32-126 + 181/924/956 + 1569-1791) cleans it to
  `product_name` before any further step (load-bearing build order, step 2).
- **Outliers.** `quantity` ranges into negatives (returns); zero-value lines (quantity
  AND gross_sales both `0`) are junk and filtered: `1,680` lines dropped (zero-value
  filter on CAST, build step 4).
- **Cross-file schema drift.** Single export folded into one header -> no cross-file
  column-order drift to check (`no`).
- **Money-relationship checks (derive, never assume).** Four money columns
  (`gross_sales` / `net_sales` / `tax` / `subtotal5_discount`) are kept as INDEPENDENT
  measures (RC9); they are not collapsed on a name-based identity assumption. Live
  silver<->gold totals (penny-exact; exact figures masked 2026-07-02, held outside
  git): sales_amount `[masked]`; net_amount `[masked]`; tax_amount `[masked]`;
  discount_amount `[masked]`; quantity `[masked]`.

---

## Candidate grain & candidate PK

Grain stated first (RC1: lowest grain the source provides), PK verified unique on the
data and re-verified on the transformed output (RC2).

- **Candidate grain:** one row = `one invoice line item`.
- **Grain ratio:** `246,916` silver line rows across the invoice population = multiple
  lines per invoice (one row per line item, not per invoice).
- **Candidate PK:** `( invoice_no, line_no )` (from source `reference_no` + `item_no`).
- **Uniqueness proof (on the transformed silver data, live 2026-06-24):**
  - `COUNT(*)            = 246,916`
  - `COUNT(DISTINCT pk)  = 246,916`   *(equals `COUNT(*)` -> PK holds)*
  - `NULLs in PK columns = 0`

> Forward seam (RC2). The PK is verified on the TRANSFORMED silver output -- TRIM/cast
> did not collapse or null any key. The silver migration's `ADD PRIMARY KEY` enforces
> this at run time; the live run confirms it.

---

## Top data-quality issues

1. `material_desc` mojibake / mixed-encoding garbage -> de-mojibake whitelist step
   (build step 2) before `product_name` is usable.
2. Division junk rows (`division IN ('AUX','ARCHIVE','EL EZABY SERVICES','')`) ->
   filtered before `''`->NULL (build step 3); part of the `2,190`-row reduction.
3. Zero-value lines (quantity AND gross_sales both `0`) -> `1,680` lines dropped
   (build step 4).
4. Salesperson attribution gap -> `71` line items lack a salesperson; absorbed by the
   `dim_salesperson` `-1` unknown member (a DQ signal, not a defect; see reconciliation).
5. Patient-health PII (`insurance_no`, `insurance_phone`) present in the landing ->
   dropped early (RC4), before the BI layer.

---

## Exit gate

- [x] Grain stated, with the row-vs-entity ratio (one row = one invoice line item).
- [x] Candidate PK stated and proven unique on the data (`246,916` = `246,916`, `0`
      NULL PK) and re-verified on the transformed silver output.
- [x] Returns rule stated, from the authoritative column `billing_type_2`
      (`Z4/Z5/Z6/Z8/Z10`), not a measure sign.
- [x] Top data-quality issues listed, each with a measured count.
- [x] Missingness measured as `'' OR NULL` for every column (not `IS NULL` alone).

---

## Next artifact

Proceed to `source-map.yaml` -- the machine-readable spine (keep/drop/rename/type per
column, grain + PK first, gold star placement). This profile is its evidence base.

## See also

- **Method:** `../../docs/medallion-playbook.md` -- Phase 1 + Appendix A trap checklist.
- **Defaults:** `../../docs/decisions/0002-retail-cleaning-defaults.md` -- RC1, RC2, RC5.
  *(ADR cleaning defaults `RC*`; distinct from the checker's `D1-D8`. No collision.)*
- **Architecture:** `../../docs/architecture/tower-bi-agent-kit.md` Sec 5.
- **Worked example (narrated):** `../../docs/worked-examples/c086-pharmacy.md`.
- **Compliance matrix + live run:** `../../docs/c086-adr0002-compliance.md`.
