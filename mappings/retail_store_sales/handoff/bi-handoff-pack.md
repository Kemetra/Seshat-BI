# BI Handoff Pack -- gold.fct_sales_rss (retail_store_sales)

Filled instance of `templates/handoff/bi-handoff-pack.md` (the second worked example,
after C086). The documentation/evidence bundle for the BI consumer of the
`RetailStoreSales` model. COMPOSES existing committed evidence -- invents nothing. No
publish, no execution adapter (F016 owns live publish/refresh). ASCII, UTF-8 no BOM.

## Header

| Field | Value |
|-------|-------|
| Table / report | `gold.fct_sales_rss` + 5 dims (the `RetailStoreSales` star) |
| Source family | Kaggle "retail store sales (dirty)" -- single CSV, training DB |
| Assembled on | 2026-06-25 |
| Assembled by | agent (dashboard-design sibling; authoring only) |
| Prior-stage gate | stages 1-6 each `pass`? **yes** (readiness-status.yaml: source/mapping/silver/gold/semantic_model/dashboard all pass) |

## Required-section index (each points at an EXISTING committed artifact)

| # | Section | Points at (existing artifact) | Resolved? |
|---|---------|-------------------------------|-----------|
| a | Metric contracts (stage 5, approved) | `../metrics/*.yaml` (5 contracts, all `pass`, owner-approved 2026-06-25) | yes |
| b | Readiness scorecard | `../readiness-status.yaml` (stages 1-6 pass; publish_ready = warning, re-approval pending after the discount-rate correction) | yes |
| c | Reconciliation evidence (stage 4) | `../reconciliation-report.md` (silver<->gold, PASS) + `../reconciliation-bronze-to-gold.md` (bronze->gold tie + grain uniqueness, PASS) | yes |
| d | Known data issues / caveats | `../data-issues`-equivalent + `../assumptions.md` (composed below) | yes |
| e | Data dictionary (deployed schema) | below | yes |
| f | Publish approval | `../readiness-status.yaml` `approvals[]` (prior approval RETRACTED after the discount-rate correction; re-approval pending) | pending |

## Known data issues / caveats (MANDATORY -- all four)

Composed from the source-profile + assumptions + the approved contracts; recorded,
never re-decided.

1. **PII exclusion.** No raw PII in the model. `customer_id` is a pseudonymous
   surrogate (`CUST_xx`, 25 distinct) KEPT as `dim_customer_rss` per the owner ruling
   (Q1) -- no name/phone/email/address exists in the source. No column was dropped for
   PII (none present); the deviation from the RC4 auto-drop is recorded in
   `../assumptions.md`.
2. **Returns handling.** NONE in this source. All measures are strictly positive and
   there is no transaction-type/return column; the data owner confirmed returns live in
   a separate figure/system not loaded here. RC8 is N/A. Do NOT infer returns from a
   measure sign. (`../assumptions.md` deviation 1.)
3. **Known gaps (measured).**
   - `discount_applied` is UNKNOWN (NULL) on **4,199 / 12,575 (33.39%)** of
     transactions. The APPROVED `DiscountedTransactionRate` is the KNOWN-STATUS rate --
     discounted / known-status = 4,219 / 8,376 = **50.37%** (unknowns EXCLUDED, per the
     Q2 ruling). Supporting caveats to surface on any discount visual: the floor (if
     unknowns were treated as not-discounted) is 4,219 / 12,575 = **33.55%**, and the
     unknown-status share is 4,199 / 12,575 = **33.39%**.
   - `item` is missing on **1,213 / 12,575 (9.65%)** of transactions -- these land on
     the `-1` unknown member of `dim_product_rss` (kept, not dropped; Q4).
   - `price_per_unit` / `quantity` / `total_spent` each missing ~4.8% (~604 rows);
     these NULLs are truly unknown (not recoverable from price*qty -- verified) and are
     ignored in the sums (no revenue discarded).
4. **Out of scope.** No margin/profit (no cost data). No returns (above). No customer
   demographics (only a pseudonymous id). No live refresh/publish wiring (F016).

## Data dictionary (against the DEPLOYED `gold` schema)

Every deployed column appears once; business meaning carried from `../source-map.yaml`.

### gold.fct_sales_rss (fact, one row = one transaction)
| Column | Type | Role | Meaning |
|--------|------|------|---------|
| fct_sales_rss_sk | integer | surrogate PK | fact surrogate key |
| transaction_id | text | degenerate dim | the transaction natural key (`TXN_*`) |
| discount_applied | boolean | degenerate dim | discount flag; NULL = unknown (33%, see caveat 3) |
| customer_sk | integer | FK -> dim_customer_rss | |
| product_sk | integer | FK -> dim_product_rss | -1 = unknown product (missing item) |
| payment_method_sk | integer | FK -> dim_payment_method_rss | |
| location_sk | integer | FK -> dim_location_rss | |
| date_sk | integer | FK -> dim_date_rss | YYYYMMDD |
| price_per_unit | numeric | measure (attribute) | unit price |
| quantity | numeric | measure | units sold (TotalQuantity) |
| total_spent | numeric | measure | line total (TotalSales); = price*quantity |

### Dimensions
| Table | Key | Attributes | Meaning |
|-------|-----|------------|---------|
| dim_customer_rss | customer_sk | customer_id | pseudonymous customer (25 + `-1`) |
| dim_product_rss | product_sk | item, category | product (item 1:1 category); `-1` unknown |
| dim_payment_method_rss | payment_method_sk | payment_method | Cash / Credit Card / Digital Wallet |
| dim_location_rss | location_sk | location | In-store / Online |
| dim_date_rss | date_sk | full_date, year, quarter, month, month_name, day, day_name, iso_week, is_weekend | contiguous calendar 2022-01-01..2025-01-18; marked date table |

## Publish approval (named human sign-off; agent never self-grants)

```yaml
approvals:
  - stage: "publish_ready"
    owner: "<data_owner | governance>"   # to be recorded on RE-approval of the corrected pack
    at: "<YYYY-MM-DD>"
```

A publish approval was RECORDED 2026-06-25 and then RETRACTED the same day: it was
given against a pack that framed `DiscountedTransactionRate` as the 33.55% floor, which
was corrected to the approved known-status rate (50.37%). Because the approved artifact
materially changed, the approval no longer applies. The data owner must review THIS
corrected pack and record a fresh `publish_ready` approval -> `publish_ready` becomes
`pass`. Until then it is `warning`. The live publish/refresh ACTION remains F016.

## Readiness verdict for this pack

`warning` -- the pack is assembled and every required section resolves to a committed
artifact, BUT the publish approval is PENDING re-approval after the
`DiscountedTransactionRate` correction (the prior 2026-06-25 approval was retracted).
Stages 1-6 are `pass`; `publish_ready` becomes `pass` only when the owner re-approves
the corrected pack. NO numeric confidence score. The live publish ACTION is F016.

## See also

- The checklist that gates this pack: `handoff-review-checklist.md`.
- The composed evidence: `../metrics/*.yaml`, `../reconciliation-report.md`,
  `../reconciliation-bronze-to-gold.md`, `../readiness-status.yaml`,
  `../assumptions.md`, `../source-map.yaml`,
  `../design/visual-contract-binding-map.md`.
- The stage authority: `../../../docs/readiness/publish-ready.md`. Live publish (out of
  scope) is the F016 execution adapter.
