# Data Dictionary

Catalog of the analytics warehouse: medallion layers, tables, columns, and
business rules. This dictionary documents the kit's surviving worked example,
**`retail_store_sales`** — the Kaggle "retail store sales (dirty)" CSV (a
single POS-style transaction export), landed into the `training` Postgres
database. Data is English/ASCII throughout; the source system is a flat file,
not a live POS/ERP feed.

Medallion flow: `bronze` (raw landing) → `silver` (typed/cleaned) → `gold`
(Kimball star; **Power BI reads gold**). Built by `warehouse/migrations/`.

| Layer | Table | Grain | Rows |
|-------|-------|-------|-----:|
| bronze | `retail_store_sales` | one retail transaction (raw) | 12,575 |
| silver | `retail_store_sales` | one retail transaction (cleaned) | 12,575 |
| gold | `fct_sales_rss` | one retail transaction | 12,575 |
| gold | `dim_customer_rss` | customer | see note* |
| gold | `dim_product_rss` | product (item) | see note* |
| gold | `dim_payment_method_rss` | payment method | see note* |
| gold | `dim_location_rss` | transaction channel | see note* |
| gold | `dim_date_rss` | calendar day | see note* |

\* Dimension row counts are not asserted here because they are not attested in
the source artifacts (`source-profile.md` reports *source column* distinct
cardinalities — 25 `customer_id`, 201 `item`, 8 `category`, 3
`payment_method`, 2 `location` — not gold dimension row counts, and the
reconciliation report does not enumerate them). Each entity dimension carries
one additional `-1` UNKNOWN member (Kimball unknown-member pattern); `dim_date_rss`
does not (see below).

---

## bronze schema — faithful landing

`bronze.retail_store_sales` — 11 source columns, **all `TEXT`**, plus lineage
(`_source_file`, `_loaded_at`). No cleaning. Loaded from the single
`retail_store_sales.csv` export. Missing cells land as empty string `''`
(not NULL) — a faithful landing, so missingness must be measured as
`'' OR NULL`, never `IS NULL` alone.

Not catalogued column-by-column here (it mirrors the source CSV headers). The
authoritative transform from bronze → silver is
`warehouse/migrations/0003_create_silver_retail_store_sales.sql`, decided from
`mappings/retail_store_sales/source-map.yaml`.

Key bronze facts that shaped silver:
- Grain verified: `transaction_id` unique across all 12,575 rows (0 nulls/blanks).
- No returns in this source: every measure (`total_spent`, `quantity`,
  `price_per_unit`) is strictly positive and there is no transaction-type or
  return-flag column. Confirmed with the data owner — returns exist in a
  separate figure/system not loaded here (deviation RC8, N/A for this table).
- `item` <-> `category` is 1:1 on the data (0 items map to more than one
  category) — a flat, denormalized product dimension, no fan-out.
- `total_spent == price_per_unit * quantity` holds on 11,362 / 11,362 complete
  rows = 100.00% — fully derivable, kept as an independent landed measure.

---

## silver schema — typed & cleaned

`silver.retail_store_sales` — **11 columns**, grain = **one retail
transaction**, **PK = `transaction_id`**. Built from bronze in migration
`0003`. Indexes: `transaction_date`, `customer_id`, `item`.

| Column | Type | Description |
|--------|------|-------------|
| `transaction_id` | text | Transaction key (`TXN_xxxxxxx`). PK. Unique on the landed data; re-proven unique on the transform (V-RC2). |
| `customer_id` | text | Pseudonymous customer surrogate (`CUST_xx`). **Kept** per data-owner ruling (Q1) — not raw PII, but flagged `pii: true` in the map for governance review. |
| `item` | text | Product natural key (`Item_N_<CAT>`). 9.65% missing in bronze → `NULL` in silver → folds to the gold `-1` member. |
| `category` | text | Product category; 1:1 attribute of `item` (0 fan-out). |
| `price_per_unit` | numeric(12,2) | Unit price. Float-as-text in bronze, cast to exact NUMERIC. |
| `quantity` | numeric(12,2) | Units sold (range 1–10). Kept as NUMERIC, not INT, until confirmed integer-only. |
| `total_spent` | numeric(12,2) | Line total. `= price_per_unit * quantity` on 100% of complete rows; independent landed measure (not recomputed). |
| `payment_method` | text | Cash / Credit Card / Digital Wallet. |
| `location` | text | In-store / Online (transaction channel). |
| `transaction_date` | date | `YYYY-MM-DD`, cast from text. Spans 2022-01-01 → 2025-01-18. |
| `discount_applied` | boolean | Discount FLAG, **not** a return marker. `'true'`/`'false'` cast to boolean; blank is **UNKNOWN → NULL**, deliberately not coerced to `FALSE` (data-owner ruling, Q2). |

### Row filters applied (bronze → silver: 12,575 → 12,575)
No junk-row filter and no zero-value filter: the profile found no junk rows
and no zero/negative measures. Missing measures are kept as `NULL`, not
dropped — a transaction with a blank price/quantity is still a real row.

### Dropped columns (not carried to silver)
None beyond the lineage columns `_source_file`, `_loaded_at` (infrastructure,
recoverable from bronze if needed). All 11 source columns were kept (`decision:
keep` on every column in `source-map.yaml`).

---

## gold schema — Kimball star (Power BI reads here)

Built from silver in migration `0004`. Surrogate `_sk` INT keys (`GENERATED …
IDENTITY`); natural keys retained; every ENTITY dimension has an **Unknown
member at `_sk = -1`** (fact FKs `COALESCE` missing lookups to `-1`); the
**date dimension carries none** — it is a marked date table (rule S8), so an
unmatched fact date fails the load (`date_sk NOT NULL`) rather than landing on
a sentinel. Measures reconcile to the penny vs silver (verdict PASS in
`mappings/retail_store_sales/reconciliation-report.md`).

All gold objects for this table carry an **`_rss` suffix** (retail store
sales) — a namespace convention so more than one star can coexist side by
side in the shared `gold` schema without name collisions. `retail validate`
reads these object names **verbatim** from `source-map.yaml` (it does not
prepend `gold.`), so they must be schema-qualified and match the migration
exactly.

### `gold.fct_sales_rss` — transaction-grain fact (12,575 rows)
PK `fct_sales_rss_sk`. `transaction_id` and `discount_applied` are
**degenerate dimensions** (carried on the fact, no separate dim table). A
`UNIQUE (transaction_id)` constraint enforces the declared business grain
alongside the surrogate PK. 5 FK constraints (all enforced, 0 orphans).

| Column | Type | Description |
|--------|------|-------------|
| `fct_sales_rss_sk` | integer | Surrogate PK. |
| `transaction_id` | text | Degenerate dim — transaction key. `NOT NULL`, unique. |
| `discount_applied` | boolean | Degenerate dim — discount flag. `NULL` = unknown (Q2 ruling). |
| `customer_sk` | integer | FK → `dim_customer_rss`. |
| `product_sk` | integer | FK → `dim_product_rss` (−1 covers the 9.65% missing-`item` rows, 1,213 of them). |
| `payment_method_sk` | integer | FK → `dim_payment_method_rss`. |
| `location_sk` | integer | FK → `dim_location_rss`. |
| `date_sk` | integer | FK → `dim_date_rss` (`YYYYMMDD`). `NOT NULL` — no sentinel fallback. |
| `price_per_unit` | numeric(12,2) | Unit rate. Kept as a fact attribute, **not summed**. |
| `quantity` | numeric(12,2) | Units. Additive measure. Reconciles to **66,276** total vs silver. |
| `total_spent` | numeric(12,2) | Line total. Additive measure. Reconciles to **1,552,071.00** total vs silver. |

### `gold.dim_customer_rss`
`customer_sk` (PK), `customer_id` (NK, pseudonymous surrogate — kept per
owner ruling, Q1; opposite of a "drop PII" default, since `customer_id` here
is not raw PII).

### `gold.dim_product_rss`
`product_sk` (PK), `item` (NK), `category` (flat 1:1 attribute, verified 0
fan-out — `max(category)` is a safe collapse per item). Hierarchy is flat
(denormalized), matching the source's 1:1 item↔category relationship.

### `gold.dim_payment_method_rss`
`payment_method_sk` (PK), `payment_method` (NK: Cash / Credit Card / Digital
Wallet).

### `gold.dim_location_rss`
`location_sk` (PK), `location` (NK: In-store / Online — transaction channel).

### `gold.dim_date_rss` (contiguous calendar, no `-1` member)
`date_sk` (`YYYYMMDD` smart key, PK), `full_date`, `year`, `quarter`, `month`,
`month_name`, `day`, `day_name`, `iso_week`, `is_weekend`. Generated via
`generate_series` for the full 2022-01-01 → 2025-01-18 span so time
intelligence is correct across the whole calendar. **Mark as the date table
in Power BI.** Deliberately carries **no** `-1`/NULL member (rule S8): an
unmatched fact date is rejected by `date_sk NOT NULL` at load time — a
real calendar-coverage bug fails loudly instead of being silently bucketed.

---

## Caveats & known limitations

- **No returns in this source.** All measures (`quantity`, `price_per_unit`,
  `total_spent`) are strictly positive; there is no return/transaction-type
  column. This is a confirmed deviation (RC8, N/A) from the kit's default
  returns rule, not a gap — do not infer returns from sign or absence of a
  flag.
- **`discount_applied` is a flag, not a return marker.** 33.39% of bronze rows
  (4,199 / 12,575) are blank. Blank means **UNKNOWN**, not `FALSE` — a
  data-owner ruling (Q2). Discount metrics must exclude unknowns rather than
  treating a blank as "no discount."
- **`item` is 9.65% missing** (1,213 / 12,575 bronze rows). These rows fold
  correctly to the `dim_product_rss` `-1` UNKNOWN member in gold (Q4 ruling) —
  they are not dropped.
- **`customer_id` is pseudonymous, not raw PII**, and is intentionally
  **kept** (Q1 ruling) — a deliberate deviation from the kit's RC4 auto-drop
  default. It remains flagged `pii: true` in the map for a governance
  decision on downstream publishing, even though it was not dropped at the
  mapping gate.
- **`total_spent` is derivable but not recomputed.** It equals
  `price_per_unit * quantity` on 100% of complete rows, but the 604 blank rows
  are kept as `NULL` rather than backfilled — recomputing them is a future
  analyst decision, not baked into this build.
- **Measure blanks (~4.8% each)** in `price_per_unit`, `quantity`, and
  `total_spent` are kept as `NULL` in silver and gold, not dropped or
  zero-filled — a transaction with an incomplete measure is still a real row.

---

## marts (legacy 2-layer naming)

_No `marts` schema — the deployed DB uses the 3-layer medallion above
(`bronze`/`silver`/`gold`); `gold` is the reporting layer Power BI reads._
