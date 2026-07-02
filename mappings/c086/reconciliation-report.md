# Reconciliation Report -- `C086`

> **SUPERSEDED (2026-07-02).** This live run validated the FIRST build only (the
> 0001/0002 star: `fct_sales` with sales_amount/net_amount/tax/discount). That star
> was replaced by migrations 0005/0006 (2 measures: gross_sales + quantity;
> surrogate `sale_sk` PK); this report's PASS does NOT certify the current star,
> whose live validation is PENDING (see
> [`../sales_c086/reconciliation-report.md`](../sales_c086/reconciliation-report.md)).
> Audit notes: [`./README.md`](./README.md).

> **Filled instance.** The live acceptance run for C086, back-authored from the
> read-only validation of 2026-06-24 (recorded in
> `../../docs/c086-adr0002-compliance.md` SecLIVE). It is the last of the five
> source-mapping gate artifacts -- filled only after silver and gold were built and a
> live DB was reachable. Result: all four live gates PASS.

---

## What this report is (and is not)

This report documents the LIVE acceptance gates for C086: the checks that can only be
proven against a running database. They correspond to the playbook's Phase 5/6
validation gates and to ADR 0002 defaults `RC2`, `RC15`, `RC16`
(`../../docs/decisions/0002-retail-cleaning-defaults.md`).

> The four categories are the LIVE surface (`retail validate`, feature 004): PK
> uniqueness (RC2), date coverage (RC15), 0 orphan FKs (RC16), penny-exact
> reconciliation (RC16). The results below were filled from a read-only analyst/agent
> session against the live DB. The static, CI-able gate is the separate `retail check`
> (it does not cover these -- these need the data).

> **Namespace note (disambiguated -- feature 002):** the ADR ids cited here (`RC2`,
> `RC15`, `RC16`) are ADR 0002 cleaning/modeling defaults ("retail cleaning"), distinct
> from the checker's `D1-D8` TMDL/DAX rules. No collision.

---

## Run header

| Field | Value |
|-------|-------|
| Table id | `C086` (silver.sales_c086 + the gold star) |
| Silver object | `silver.sales_c086` |
| Gold objects | `gold.fct_sales` + `gold.dim_product` / `dim_customer` / `dim_salesperson` / `dim_billing_type` / `dim_branch` / `dim_date` (1 fact at line grain + 6 conformed dims) |
| Run date | `2026-06-24` |
| DB cluster | from gitignored `.env` (not committed) |
| Database | from gitignored `.env` (a dedicated logical DB; the cluster's `defaultdb` is empty; not committed) |
| Run by | back-authored from committed 0001/0002 (live-validated) |
| Connection | **READ-ONLY.** Credentials from the git-ignored `.env` (never committed; Power BI uses parameters, not baked-in strings). No writes performed. |

> **Read-only is a hard requirement.** This was an acceptance run, not a build run.

---

## 1. PK uniqueness (ADR RC2)

**Gate:** the silver table's row count equals the count of distinct primary-key tuples,
and there are zero NULL PK values. Verified on the transformed (silver) rows.

| Check | Expected | Observed |
|-------|----------|----------|
| Silver row count | `246,916` | `246,916` |
| Distinct PK tuples `(invoice_no, line_no)` | `246,916` (= row count) | `246,916` |
| NULL PK values | `0` | `0` |

**Result:** `246,916` rows = `246,916` distinct `(invoice_no, line_no)`, `0` NULL PK ->
**PASS**.

---

## 2. Date-dim coverage (ADR RC15)

**Gate:** the gold date dimension is a contiguous generated calendar (from
`generate_series`, never `SELECT DISTINCT date`) spanning every real fact date, with
zero real dates missing.

| Check | Expected | Observed |
|-------|----------|----------|
| Calendar span | `2023-01-01` .. `2025-12-31` | `2023-01-01` .. `2025-12-31` |
| Calendar row count | `1,096` (= exact contiguous span, no gaps) | `1,096` |
| Contiguous (no missing interior days) | yes | yes |
| Real fact dates outside the calendar | `0` | `0` |

**Result:** calendar spans every `sale_date`, contiguous, `0` missing -> **PASS**.

> The pattern half of RC15 (generate_series vs distinct) is statically checked by
> `retail check` rule S7; the coverage half above is the live half (cannot be proven
> from text).

---

## 3. Orphan FKs (ADR RC16)

**Gate:** zero hard orphan FKs across all dimensions -- every fact FK resolves to a real
dimension surrogate key. The `-1` unknown-member pattern (RC14) absorbs unresolved keys
without creating an orphan. Rows landing on each `-1` member are not orphans but a
data-quality signal.

| Dimension | Hard orphan FKs (expected `0`) | Rows on `-1` unknown member (DQ signal) |
|-----------|--------------------------------|-----------------------------------------|
| `dim_product` | `0` | `0` |
| `dim_customer` | `0` | `0` |
| `dim_salesperson` | `0` | `71` |
| `dim_billing_type` | `0` | `0` |
| `dim_branch` | `0` | `0` |
| `dim_date` | `0` | `0` |

**Result:** `0` hard orphan FKs across all 6 dims -> **PASS**.
**DQ signals:** `dim_salesperson` has `71` fact rows on `-1` (~71 line items lack
salesperson attribution; the RC14 unknown-member pattern absorbs them -- a known gap,
not a defect; surface to the analyst).

---

## 4. Cross-layer measure reconciliation (ADR RC16)

**Gate:** every measure total matches to the penny across layers. All five measures
reconciled silver<->gold; the BI column is `n/a` until an Import-mode model exists.

| Measure | Source | Silver | Gold | BI | Match? |
|---------|--------|--------|------|----|--------|
| `sales_amount` | (faithful landing) | `[masked]` | `[masked]` | `n/a` | yes |
| `net_amount` | (faithful landing) | `[masked]` | `[masked]` | `n/a` | yes |
| `tax_amount` | (faithful landing) | `[masked]` | `[masked]` | `n/a` | yes |
| `discount_amount` | (faithful landing) | `[masked]` | `[masked]` | `n/a` | yes |
| `quantity` | (faithful landing) | `[masked]` | `[masked]` | `n/a` | yes |
| Row count | `249,106` (raw) | `246,916` | `246,916` | `n/a` | yes (silver = gold) |

> Source totals are the faithful all-TEXT landing (`249,106` raw rows); the `2,190`-row
> reduction to silver is the two documented filters (division-junk + zero-value lines),
> after which silver and gold reconcile to the penny on all five measures.

**Result:** all `5` measures reconcile to the penny silver<->gold (fact row count equal
across silver and gold) -> **PASS**.

---

## Verdict

| Category | ADR | Playbook | Result |
|----------|-----|----------|--------|
| 1. PK uniqueness | RC2 | Phase 5 | PASS |
| 2. Date-dim coverage | RC15 | Phase 6 | PASS |
| 3. Orphan FKs | RC16 | Phase 6 | PASS |
| 4. Cross-layer reconciliation | RC16 | Phase 5/6 | PASS |

**Overall:** **PASS** -- all four live gates pass; 1 DQ signal noted (71 fact rows on
the salesperson `-1` unknown member, a known attribution gap for analyst follow-up).

> The gate is CLEARED: 16/16 ADR 0002 defaults satisfied, with the three live items
> (RC2, RC15-coverage, RC16) confirmed on real data.

---

## See also

- **Method:** `../../docs/medallion-playbook.md` -- Phase 5 (build silver) and Phase 6
  (build gold); the validation gates these four categories enforce.
- **Defaults:** `../../docs/decisions/0002-retail-cleaning-defaults.md` -- RC2 (PK on
  transformed data), RC15 (contiguous generated date dim), RC16 (cross-layer
  reconciliation + 0 orphan FKs).
- **Architecture:** `../../docs/architecture/tower-bi-agent-kit.md` -- Sec 5 (this is the
  Phase 5/6 gate artifact), Sec 7 (LIVE validator categories).
- **Static gate:** `retail check` (`src/retail/`) -- complementary to these live gates.
- **Sibling gate artifacts:** `source-profile.md`, `source-map.yaml`, `assumptions.md`,
  `unresolved-questions.md`.
- **Worked example + compliance:** `../../docs/worked-examples/c086-pharmacy.md` Sec5 +
  `../../docs/c086-adr0002-compliance.md` (246,916 rows; penny-exact across 5 measures;
  71 rows on the salesperson `-1` member).
