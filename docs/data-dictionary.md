# Data Dictionary

Catalog of the analytics warehouse: medallion layers, tables, columns, and
business rules. Source system is the El Ezaby pharmacy POS/ERP (SAP-style),
store **C086** ("الترعة البولاقية"), sales 2023-01-01 → 2025-12-31.
Data is bilingual (Arabic staff/billing terms, English drug names).

Medallion flow: `bronze` (raw landing) → `silver` (typed/cleaned) → `gold`
(Kimball star; **Power BI reads gold**). Built by `warehouse/migrations/`.

| Layer | Table | Grain | Rows |
|-------|-------|-------|-----:|
| bronze | `sales_c086_raw` | invoice line item (raw) | 249,106 |
| silver | `sales_c086` | invoice line item (cleaned) | 246,916 |
| gold | `fct_sales` | invoice line item | 246,916 |
| gold | `dim_product` | product (SKU) | 9,669* |
| gold | `dim_customer` | customer | 639* |
| gold | `dim_salesperson` | salesperson | 257 |
| gold | `dim_date` | calendar day | 1,097* |
| gold | `dim_billing_type` | billing type | 11* |
| gold | `dim_branch` | store/branch | 2* |

\* includes the `-1` "Unknown" member (Kimball unknown-member pattern).

---

## bronze schema — faithful landing

`bronze.sales_c086_raw` — 48 columns, **all `TEXT`**, plus lineage. No cleaning.
Loaded from C086 sales Excel files by `pipelines/load_bronze.py`. Missing cells
land as empty string `''` (not NULL). Every value traceable via `_source_file`.

Not catalogued column-by-column here (it mirrors the source spreadsheet headers,
normalized to `snake_case`). The authoritative transform from bronze → silver is
`warehouse/migrations/0001_create_silver_sales_c086.sql`.

Key bronze facts that shaped silver:
- Grain verified: `reference_no + item_no` unique across all 249,106 rows.
- Returns identified by `billing_type` (contains `مرتجع`) — not by sign alone.
- 4,945 `material_desc` values carried mojibake from a Windows-1256 mis-decode.
- 14 `division` values incl. junk (`AUX`, `ARCHIVE`, `EL EZABY SERVICES`, blank).

---

## silver schema — typed & cleaned

`silver.sales_c086` — **30 columns**, grain = **invoice line item**,
**PK = (`invoice_no`, `line_no`)**. Built from bronze in migration `0001`.
Indexes: `sale_date`, `customer_id`, `product_id`.

| Column | Type | Description |
|--------|------|-------------|
| `product_id` | text | Product/SKU code (natural key). Leading zeros significant → TEXT. |
| `product_name` | text | Product description; mojibake stripped via charset whitelist. |
| `quantity` | numeric(18,4) | Units sold. **Negative = return.** |
| `sales_amount` | numeric(18,2) | **Gross** sales (line). Negative on returns. |
| `net_amount` | numeric(18,2) | Net revenue (gross − tax/discount). `net ≤ gross` verified on all sales. |
| `tax_amount` | numeric(18,2) | Tax. |
| `discount_amount` | numeric(18,2) | Discount (stored **negative** on sales; positive on returns). |
| `invoice_no` | text | Store invoice reference (e.g. `C0860010008384`). PK part. |
| `line_no` | smallint | Invoice line number (1–44). PK part. |
| `sale_date` | date | Transaction date (time component dropped — always 00:00:00). |
| `billing_type` | text | Payment/return type, **English** (see mapping below). |
| `billing_type_code` | text | SAP Z-code (`Z1`, `Z5`, …). Stable join key. |
| `is_return` | boolean | TRUE for the 5 return billing types. Use this to separate sales/returns. |
| `customer_id` | text | Customer code (natural key). Leading zeros significant. |
| `customer_name` | text | Customer/payer name. **Attribute only — not a key** (25 names span >1 id). |
| `salesperson_id` | text | Staff code. Missing → `'UNKNOWN'`. |
| `salesperson_name` | text | Staff name (Arabic). Missing → `'UNKNOWN'`. |
| `job_title` | text | Staff role (e.g. صيدلى = pharmacist). Missing → `'UNKNOWN'`. |
| `procurement_buyer` | text | Buyer/procurement code. |
| `product_division` | text | Hierarchy L1 (RX/OTC/NUTRACEUTICAL/…). |
| `product_category` | text | Hierarchy L2. |
| `product_subcategory` | text | Hierarchy L3. |
| `product_segment` | text | Hierarchy L4. |
| `product_brand` | text | Brand. Missing → `'UNKNOWN'`. |
| `product_group` | text | Material group label (e.g. `DRUG-LEGAL-LOCAL-…`). |
| `product_cluster` | text | A/B/C/D performance class. Missing → `'UNCLASSIFIED'`. |
| `original_invoice_ref` | text | For returns: the originating invoice. NULL on non-returns. |
| `branch_code` | text | Store code (`C086`). |
| `branch_name` | text | Store name (الترعة البولاقية). |
| `business_segment` | text | Rollup of `product_division` (see mapping below). |

### Row filters applied (bronze → silver: 249,106 → 246,916)
- Drop `division ∈ {AUX, ARCHIVE, EL EZABY SERVICES, ''}` — 513 junk rows.
- Drop zero-value lines (`quantity = 0 AND sales_amount = 0`) — 1,680 rows
  (all zero-value return adjustment lines; overlap with above = 3).

### Dropped columns (not carried to silver)
`kzwi1`, `dis_tax`, `add_dis`, `salse_not_tax` (redundant/duplicate money);
`paid` (does not reconcile); `knumv`, `ref_return_date` (100% empty);
`crm_order`, `certification`, `assignment` (mostly empty); `cosm_mg`, `area_mg`
(single-value); `mat_group_2` (1:1 code of `product_group`); `billing_document`,
`fi_document_no` (SAP refs, out of scope); `item_status` (status col dropped);
**`insurance_no`, `insurance_tel` (patient health PII — intentionally dropped)**;
`_source_file`, `_loaded_at` (lineage). Recoverable from bronze if needed.

---

## gold schema — Kimball star (Power BI reads here)

Built from silver in migration `0002`. Surrogate `_sk` INT keys; natural keys
retained; every dimension has an **Unknown member at `_sk = -1`**; fact FKs
COALESCE missing lookups to `-1`. Measures reconcile to the penny vs silver.

### `gold.fct_sales` — line-item fact (246,916 rows)
PK `fct_sales_sk`. `invoice_no` + `line_no` are **degenerate dimensions** (carried
on the fact, no `dim_invoice`). 6 FK constraints (all enforced, 0 orphans).

| Column | Type | Description |
|--------|------|-------------|
| `fct_sales_sk` | integer | Surrogate PK. |
| `invoice_no` | text | Degenerate dim — store invoice ref. |
| `line_no` | smallint | Degenerate dim — line number. |
| `original_invoice_ref` | text | Originating invoice for returns (nullable). |
| `product_sk` | integer | FK → `dim_product`. |
| `customer_sk` | integer | FK → `dim_customer`. |
| `salesperson_sk` | integer | FK → `dim_salesperson` (−1 on 71 UNKNOWN rows). |
| `date_sk` | integer | FK → `dim_date` (`YYYYMMDD`). |
| `billing_type_sk` | integer | FK → `dim_billing_type`. |
| `branch_sk` | integer | FK → `dim_branch`. |
| `quantity` | numeric(18,4) | Units (negative = return). Additive. |
| `sales_amount` | numeric(18,2) | Gross. Additive. **Mixes returns (negative) — filter `NOT is_return` for gross-only.** |
| `net_amount` | numeric(18,2) | Net revenue. Additive. |
| `tax_amount` | numeric(18,2) | Tax. Additive. |
| `discount_amount` | numeric(18,2) | Discount (signed). Additive. |
| `is_return` | boolean | Return flag (mirrors `dim_billing_type.is_return`). |

### `gold.dim_product` (9,669 incl. −1)
`product_sk` (PK), `product_id` (NK), `product_name`, `product_brand`,
`product_group`, `product_cluster`, `product_division`, `product_category`,
`product_subcategory`, `product_segment`, `business_segment`.
Hierarchy is **flat** (denormalized) — not snowflaked, because the same child can
appear under >1 parent (legitimate commercial overlap). Build a drill hierarchy in
Power BI from the flat columns; each SKU has a single path so totals don't double-count.

### `gold.dim_customer` (639 incl. −1)
`customer_sk` (PK), `customer_id` (NK), `customer_name`. **Key on `customer_id`** —
`customer_name` collapses walk-in/masked names across multiple ids.

### `gold.dim_salesperson` (257)
`salesperson_sk` (PK), `salesperson_id` (NK), `salesperson_name`, `job_title`.
Silver `'UNKNOWN'` rows fold into the `-1` member (71 fact rows).

### `gold.dim_date` (1,097 incl. −1) — **contiguous calendar**
`date_sk` (`YYYYMMDD` smart key, PK), `full_date`, `year`, `quarter`, `month`,
`month_name`, `day`, `day_name`, `iso_week`, `is_weekend`. Generated for the full
2023-01-01 → 2025-12-31 span (1,096 days) so time-intelligence is correct even on
the 2 zero-sales days. **Mark as the date table in Power BI.**

### `gold.dim_billing_type` (11 incl. −1)
`billing_type_sk` (PK), `billing_type_code` (NK, SAP Z-code), `billing_type`
(English label), `is_return`.

### `gold.dim_branch` (2 incl. −1)
`branch_sk` (PK), `branch_code` (NK), `branch_name`. One real store today;
modeled as a dim to future-proof multi-store.

---

## Reference mappings

### `billing_type` (Arabic → English) and `is_return`
| Code | Arabic (source) | English (silver/gold) | is_return |
|------|-----------------|-----------------------|:---------:|
| FP  | اجل | Credit | |
| Z1  | فورى | Cash | |
| Z5  | مرتجع اجل | Credit Return | ✓ |
| Z4  | مرتجع فورى | Cash Return | ✓ |
| Z9  | Pick-Up Order | Pick-Up Order | |
| Z10 | Pick-Up Order Return | Pick-Up Order Return | ✓ |
| Z3  | توصيل | Delivery | |
| Z6  | مرتجع توصيل | Delivery Return | ✓ |
| Z7  | توصيل - اجل | Delivery Credit | |
| Z8  | مرتجع توصيل - اجل | Delivery Credit Return | ✓ |

### `business_segment` (rollup of `product_division`)
| business_segment | source divisions |
|------------------|------------------|
| PHARMA | OTC, RX, NUTRACEUTICAL, EVERYDAY ESSENTIALS, HOME HEALTH CARE |
| HVI | HIGH VALUE ITEMS |
| NON-PHARMA | BEAUTY SKIN CARE, TOTAL HAIR CARE, BABY AND MOM, COSMETICS, PREMIUM SKIN CARE |

> `business_segment` is a **merchandising** axis, not clinical. `HIGH VALUE ITEMS`
> holds clinically-RX products (oncology, etc.), so a clinical "pharma" total must
> use `product_division`/`product_category`, not `business_segment = 'PHARMA'`.

---

## Caveats & known limitations

- **Returns mix into `sales_amount`** (they are negative). For gross sales, filter
  `is_return = FALSE`; for net-of-returns, sum across all rows. Always use
  `is_return` (or `billing_type` containing "Return") — never the quantity sign alone.
- **Patient PII (`insurance_no`, `insurance_phone`) is intentionally excluded** from
  silver/gold. Do not re-introduce into any Power BI dataset without a governance review.
- **Return events slightly undercounted**: 1,680 zero-value return lines were dropped,
  so return-line counts under-report; return *value* is unaffected.
- **`original_invoice_ref`** ties a return to its originating invoice but the original
  sale *date* is not available (source field was 100% empty).
- **Out of scope for v1** (rebuildable from bronze): per-line SAP/finance reconciliation
  (`billing_document`), product lifecycle status (`item_status`), cash-collected (`paid`).
- **`product_cluster`** (A/B/C/D) is a source-provided class and 32% blank
  (`'UNCLASSIFIED'`); compute ABC from actual revenue in analysis rather than relying on it.

---

## marts (legacy 2-layer naming)

_No `marts` schema — the deployed DB uses the 3-layer medallion above
(`bronze`/`silver`/`gold`); `gold` is the reporting layer Power BI reads._
