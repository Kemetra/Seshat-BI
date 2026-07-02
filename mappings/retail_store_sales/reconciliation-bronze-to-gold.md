# Bronze -> Gold Reconciliation -- `retail_store_sales`

> Live evidence that the RAW bronze source ties to `gold.fct_sales_rss` with NO row
> loss, NO duplication, and penny-exact quantity/amount reconciliation -- across the
> full medallion (bronze faithful landing -> silver typed/cleaned -> gold Kimball star).
> The sibling `reconciliation-report.md` covers silver<->gold (RC16); THIS one crosses
> the cleaning boundary bronze->gold, so it also accounts for how blanks were handled.
> Filled from a READ-ONLY live run against `training` (doctl-derived DSN, never
> committed). Figures are measured, never rounded to reach a verdict. ASCII only.

---

## Run header

| Field | Value |
|-------|-------|
| Table id | `retail_store_sales` |
| Bronze object | `bronze.retail_store_sales` (faithful all-TEXT landing + lineage) |
| Gold object | `gold.fct_sales_rss` (+ 5 dims) |
| Run date | 2026-06-25 |
| DB cluster / database | `<postgres-cluster>` / `training` (host in the gitignored `.env`) |
| Run by | agent (read-only psycopg2 session; SELECT only) |
| Connection | READ-ONLY; credentials from `doctl` at runtime; no writes, none committed |

## 1. Row count -- no loss, no duplication

| Check | Bronze | Gold | Result |
|-------|-------:|-----:|--------|
| row count | 12,575 | 12,575 | MATCH -- every source row survives to the fact |

No row was dropped in cleaning and no join fan-out duplicated rows in the star build.

## 2. Grain -- one transaction = one item (no multi-item transactions)

The fact grain is "one row = one retail transaction." Verified live that this is also
"one item per transaction" -- there are NO multi-item transactions in this source:

| Check | Bronze | Gold | Result |
|-------|-------:|-----:|--------|
| `COUNT(*)` | 12,575 | 12,575 | -- |
| `COUNT(DISTINCT transaction_id)` | 12,575 | 12,575 | MATCH -- transaction_id is UNIQUE |
| duplicate `transaction_id` rows | 0 | 0 | none -- 1 transaction = 1 row = 1 item |
| blank/NULL `transaction_id` | 0 | 0 | none |

Consequence for the measures: because `transaction_id` is unique, `COUNTROWS(fct)` ==
`DISTINCTCOUNT(transaction_id)` == 12,575, so `TransactionCount` (and every ratio that
uses it as a denominator) is exact. And because the fact is one row per transaction,
`SUM(quantity)` / `SUM(total_spent)` cannot be inflated by a join fan-out -- confirmed
by the penny-exact sums in section 3.

## 3. Measure reconciliation -- penny-exact

| Measure | Bronze (numeric rows) | Gold | Result |
|---------|----------------------:|-----:|--------|
| `quantity` SUM | 66,276.00 | 66,276.00 | MATCH (penny-exact) |
| `total_spent` SUM | 1,552,071.00 | 1,552,071.00 | MATCH (penny-exact) |
| non-blank `quantity` rows | 11,971 | 11,971 (non-NULL) | MATCH |
| non-blank `total_spent` rows | 11,971 | 11,971 (non-NULL) | MATCH |

Bronze sums are taken over the rows whose raw TEXT is genuinely numeric
(`NULLIF(btrim(col),'')::numeric`), i.e. exactly the rows that survive as non-NULL in
gold. The totals are identical, which is the whole point of the next section.

## 4. Blank-handling -- NULL, not zero (so SUM ignores, never fabricates)

| Field | Blank in bronze (`'' OR NULL`) | In gold | Effect on the measure |
|-------|-------------------------------:|---------|-----------------------|
| `quantity` | 604 | 604 NULL | ignored by SUM (not summed as 0) |
| `total_spent` | 604 | 604 NULL | ignored by SUM (not summed as 0) |
| `item` | 1,213 | -> `-1` Unknown Product member | row KEPT; its sales still counted |

`12,575 = 11,971 valued + 604 blank` holds on BOTH the bronze and the gold side for
each measure. A blank raw measure value (`''` in faithful bronze) becomes a true `NULL`
in gold -- it is NEVER fabricated as `0`. Postgres `SUM` (and the DAX `SUM` measures)
ignore NULL, so the 604 truly-unknown rows contribute nothing rather than dragging the
total down with phantom zeros. This is why the bronze and gold sums match exactly: the
cleaning was lossless for every REAL value and honest about every missing one.

The 1,213 rows with a blank `item` are KEPT (not dropped): their `product_sk` resolves
to the `-1` "Unknown" member of `dim_product_rss` (per Q4), so their `quantity` /
`total_spent` still count toward `TotalSales` / `TotalQuantity` while showing as
"Unknown" in any by-product view.

## 5. Discount status -- the APPROVED rate is known-status (not the floor)

`discount_applied` is a boolean flag, blank (UNKNOWN) on a large share of rows. Per the
Q2 owner ruling (`unresolved-questions.md`), a blank is UNKNOWN and is EXCLUDED from
discount metrics -- it is NOT coerced to False. The component counts (live):

| Component | Count | Of 12,575 |
|-----------|------:|----------:|
| `discount_applied = TRUE` (numerator) | 4,219 | -- |
| `discount_applied = FALSE` | 4,157 | -- |
| KNOWN status (`NOT NULL`) = denominator | 8,376 | -- |
| UNKNOWN status (`NULL`) | 4,199 | -- |
| (consistency: 4,219 + 4,157 + 4,199 = 12,575) | 12,575 | OK |

| Rate | Definition | Value | Status |
|------|------------|------:|--------|
| **DiscountedTransactionRate** | discounted / KNOWN-status = 4,219 / 8,376 | **50.37%** | **APPROVED metric** (Q2 ruling) |
| Floor rate | discounted / ALL = 4,219 / 12,575 | 33.55% | supporting caveat only (a lower bound) |
| Unknown-status rate | unknown / ALL = 4,199 / 12,575 | 33.39% | supporting caveat only (coverage gap) |

The approved `DiscountedTransactionRate` is the **known-status 50.37%**. The 33.55%
floor and the 33.39% unknown-rate are recorded as context/caveats, NOT as the approved
metric and NOT as separate governed measures (a future contract would be required to
make either a live measure). See `metrics/DiscountedTransactionRate.yaml`.

> 2026-06-25 correction: an earlier draft of the contract + DAX framed the rate as the
> 33.55% floor (denominator = all transactions). That contradicted the Q2 ruling
> (exclude unknowns) and was corrected to the approved known-status 50.37%. Because the
> previously-approved handoff pack carried the 33.55% framing, the publish approval was
> retracted and `publish_ready` returned to `warning` pending re-approval of the
> corrected pack.

## Verdict

**PASS (bronze -> gold).** Row counts tie (12,575 = 12,575) with zero duplication and a
unique transaction grain; both measures reconcile to the penny (66,276.00 and
1,552,071.00); blank raw values are NULL (ignored by SUM), never fabricated as zero;
the 1,213 missing-item rows land on the `-1` Unknown Product member with their sales
intact. The discount metric is the approved known-status 50.37% (floor 33.55% /
unknown 33.39% recorded as caveats). No figure was rounded to reach this verdict.

## See also

- The silver<->gold half (RC16): `reconciliation-report.md`.
- The corrected metric: `metrics/DiscountedTransactionRate.yaml`; the ruling it follows:
  `unresolved-questions.md` Q2.
- The readiness state (publish_ready = warning, re-approval pending): `readiness-status.yaml`.
- The gold build: `../../warehouse/migrations/0004_create_gold_retail_store_sales_star.sql`.
