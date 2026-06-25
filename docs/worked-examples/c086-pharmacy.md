# Worked Example — C086 (El Ezaby Pharmacy Sales)

> **The first validated Tower BI medallion worked example.** This is both (a) the
> **evidence record** that C086 is built correctly and (b) the **reusable pattern**
> a future retail table copies. It does not restate the source artifacts — it
> references and summarizes them, and shows the full workflow end to end.

**Verdict:** *C086 is the first validated Tower BI medallion worked example: 16/16 ADR 0002
defaults pass after live DB validation across 246,916 silver rows, with only the RC13/S4b
policy nuance left as a checker-policy decision.*

**Source artifacts (read these for detail; this doc summarizes them):**
- Build: `warehouse/migrations/0001_create_silver_sales_c086.sql`, `0002_create_gold_star.sql`
- Process: `docs/medallion-playbook.md` (the 7-phase method)
- Defaults: `docs/decisions/0002-retail-cleaning-defaults.md` (the RC1–RC16 rulings)
- Compliance: `docs/c086-adr0002-compliance.md` (the static + live matrix)
- Governance: `retail check` (the 23-rule static gate; rules in `src/retail/`)

**How to reuse this for a new table:** copy this section structure, swap C086 for the new
table, run the playbook's 7 phases to produce the answers, then fill §4–§5 with that table's
matrix and live evidence. The *questions and checks* generalize; the *answers* are per-table.

> **Namespace note (disambiguated — feature 002):** "RC1–RC16" below are **ADR 0002 cleaning
> defaults** ("retail cleaning"). The governance checker uses a separate "D1–D8" for TMDL/DAX
> rules. The two no longer collide — a cleaning default reads `RC<n>`, a checker rule reads
> `D<n>`. (Historically both used `D`; the ADR namespace was renamed to `RC*` because the
> checker IDs live in code and could not move.)

---

## 1. Source & silver context

**What C086 did.** El Ezaby pharmacy sales landed in `bronze.sales_c086_raw` as a faithful
all-TEXT table (**249,106 rows**), then was typed and cleaned into `silver.sales_c086`
(**246,916 rows**) at **invoice line-item grain**, PK `(invoice_no, line_no)`. The 2,190-row
reduction is two explicit filters: division-junk (`AUX`/`ARCHIVE`/`EL EZABY SERVICES`/blank)
and zero-value lines (quantity AND gross both zero).

**Rule it proves.** Playbook Phase 1 (connect & profile) + Phase 2.0 (grain-first) + ADR **RC1**
(lowest grain) and **RC2** (PK verified on transformed data).

**Evidence.** `0001` header + grain comment; live: silver = 246,916 rows = 246,916 distinct PK,
0 NULL PK (matrix §LIVE).

**Future tables — copy / watch.** *Copy:* land bronze faithful-as-TEXT, decide grain before
any column drop, state the row math (source → silver) explicitly. *Watch:* "missing" is often
`''` not `NULL` — measure missingness as `'' OR NULL`; verify the candidate PK is unique on the
*transformed* output, not the raw source (TRIM/cast can collapse or null keys).

## 2. ADR 0002 defaults applied

**What C086 did.** Walked the 16 defaults as concrete answers:
- **RC3** drop no-signal columns; **RC4** PII dropped *early* (insurance phone + claim number =
  patient health data, removed before the BI layer, not at review).
- **RC5** `''`→NULL via `NULLIF`; junk filter runs *before* the NULL conversion (so `''` matches).
- **RC6** sentinels (`UNKNOWN`/`UNCLASSIFIED`) only on grouping dim attributes; facts left NULL.
- **RC7** money/qty → exact `NUMERIC`; `product_id`/`customer_id`/`invoice_no` kept **TEXT**
  (leading zeros); `line_no` → `SMALLINT` (ordinal).
- **RC8** `is_return` derived from the authoritative billing code (`Z4/Z5/Z6/Z8/Z10`), not the
  measure sign; billing types mapped Arabic→English with a loud `UNMAPPED` else.
- **RC9** all four money measures kept (gross/net/tax/discount); **RC10** categorical encodings
  unified; **RC11** `business_segment` rollup from an explicit division→segment map (never invented);
  **RC12** product hierarchy kept flat (multi-parent overlaps preserved).

**Rule it proves.** ADR 0002 RC3–RC12; playbook Phase 2 (interactive cleaning decisions).

**Evidence.** `0001` SELECT + `UPDATE` sentinel statements + the two `CASE` maps; matrix §RC3–RC12 (PASS).

**Future tables — copy / watch.** *Copy:* the default set IS the starting point — confirm each
default, record only *deviations* (with the triggering data fact) in the table's own ADR.
*Watch:* PII is irreversible once in a published BI dataset — decide it in Phase 2.2, not at review;
never invent a business rollup, require an analyst-supplied mapping.

## 3. Gold star-schema design

**What C086 did.** A Kimball star in `gold`: **1 fact** (`fct_sales`, line-item grain, 246,916
rows) + **6 conformed dimensions** (product, customer, salesperson, billing_type, branch, date).
Surrogate `_sk` IDENTITY keys; an **unknown member at `_sk = -1`** in every ENTITY dim; fact FKs
`COALESCE(...,-1)`; `invoice_no`/`line_no`/`original_invoice_ref` as **degenerate dimensions** on
the fact; `dim_date` a **contiguous generated calendar** that deliberately carries **no `-1`
member** (a marked date table -- rule S8 -- rejects nulls; an unmatched fact date fails via
`date_sk NOT NULL`).

**Rule it proves.** ADR **RC14** (Kimball star + `-1` member + degenerate dims), **RC15** (contiguous
date dim); playbook Phase 6.

**Evidence.** `0002` (dim/fact DDL, `-1` inserts, `COALESCE` joins, `generate_series` calendar);
live: 0 orphan FKs, contiguous dim_date (matrix §LIVE).

**Future tables — copy / watch.** *Copy:* one fact at silver grain; conformed dims; `-1` unknown
member + FK-COALESCE pattern; transaction ids as degenerate dims; date dim from `generate_series`,
never `SELECT DISTINCT date`. *Watch:* FK constraints added *after* load (so `-1` members and rows
exist first); the `-1` member absorbs unresolved keys without breaking the join — check how many
land there (see §5, the salesperson note).

## 4. Static compliance matrix

**What C086 did.** Every ADR default assessed against the committed migration SQL (no DB needed).
**12 static-PASS** (RC1, RC3–RC12, RC14) + the static halves of RC15; the remainder marked LIVE
(provable only against the running DB) or WARN (RC13).

**Rule it proves.** The static surface of the governance approach — what is checkable from
committed text alone.

**Evidence.** `docs/c086-adr0002-compliance.md` (the full RC1–RC16 table). Not duplicated here —
read it for the per-rule evidence and status legend.

**Future tables — copy / watch.** *Copy:* produce this matrix per table; it IS the playbook's
Phase-4 review-gate artifact. *Watch:* honestly separate PASS (provable from text) from LIVE
(needs the DB) — a comment claiming uniqueness/reconciliation is *not* proof; mark it LIVE until
a query confirms it.

## 5. Live DB validation evidence

**What C086 did.** A **read-only** validation run against `ezaby_demo` (cluster
`db-pgsql-fra1-29712`, fra1) confirmed the three LIVE items on real data:
- **RC2 — PASS:** `silver.sales_c086` 246,916 rows = 246,916 distinct `(invoice_no,line_no)`, 0 NULL PK.
- **RC15 — PASS:** `gold.dim_date` 2023-01-01..2025-12-31 = 1,096 rows = exact span (contiguous);
  spans all `sale_date`s; **0** sale_dates missing from the calendar.
- **RC16 — PASS:** **0 hard orphan FKs** across all 6 dims; silver = fct = 246,916 rows; all five
  measure totals reconcile silver↔gold **to the penny** (sales 38,804,001.54; net 35,699,605.26;
  tax 1,108,355.29; discount −1,996,042.59; quantity 286,098.39).

**Data-quality note (not a defect).** `salesperson_sk` has **71 fact rows mapped to the `-1`
unknown member** — ~71 line items lack salesperson attribution. The RC14 unknown-member pattern
absorbs them correctly (no orphan); surface this to the analyst as a known gap.

**Rule it proves.** ADR **RC2, RC16, RC15-coverage**; playbook Phase 5/6 validation gates.

**Evidence.** Live read-only run 2026-06-24 (recorded in `docs/c086-adr0002-compliance.md`
§LIVE). Note: the data lives in DB **`ezaby_demo`**, not `defaultdb` (which is empty).

**Future tables — copy / watch.** *Copy:* run exactly these three checks against the built DB
before declaring done — PK uniqueness, date coverage + contiguity, 0-orphans + penny-exact
cross-layer reconciliation. *Watch:* connect **read-only**; reconcile *every* measure, not a
sample; count rows landing on each `-1` member as a data-quality signal.

## 6. RC13 / S4b policy — RESOLVED (layer-aware S4b implemented)

**What C086 did.** Both migrations are idempotent at the transaction level (DROP+CREATE inside
one `BEGIN/COMMIT`, numbered `NNNN_`) and re-runnable after a bronze reload — satisfying ADR
**RC13's intent**. They use **bare** `CREATE TABLE` / `ALTER TABLE` / `CREATE INDEX`, which is the
*correct* idempotency for rebuildable marts (`CREATE TABLE IF NOT EXISTS` would wrongly preserve a
stale schema). The original blanket S4b warned on this (22 warnings) — so the **rule** was wrong,
not the SQL.

**Resolution (implemented, not just recommended).** S4b is now **layer-aware** (`src/retail/sql.py`
`schema_zone()` + `src/retail/rules/sql.py`). The encoded policy:
> **DROP+CREATE inside a `BEGIN/COMMIT` transaction is ALLOWED (no finding) for derived/rebuildable
> `silver.*` / `gold.*` objects** — they regenerate from bronze, so a destructive rebuild is safe.
> **A bare DROP/CREATE/ALTER on `bronze.*` (source-of-truth) is an ERROR** that blocks the build —
> a blind DROP there risks destroying the only copy of source data. A bare silver/gold DDL **not**
> in a transaction is a WARNING. **Fail-closed:** any target whose schema can't be detected
> (unqualified name, `search_path`) is treated strictly (WARNING), never silently allowed.

**Severity is now asymmetric by design:** bronze destructive op = ERROR (the catastrophe the gate
exists to prevent); silver/gold non-idempotent-but-recoverable = WARNING; correct silver/gold
rebuild-in-txn = pass. This makes S4b *stricter* where it matters and *quieter* where it doesn't.

**Rule it proves.** ADR **RC13** (idempotent rebuildable marts) + the governance layer's layer-aware
enforcement. Verified: `retail check --repo .` now reports **0 S4b findings** on C086's silver/gold
migrations (the 22 warnings resolved), with no new bronze ERROR (C086 has no bronze DROP).

**Future tables — copy / watch.** *Copy:* keep silver/gold migrations as DROP+CREATE-in-one-
transaction — it's the sanctioned, S4b-clean idempotency pattern. *Watch:* **never** bare-DROP a
`bronze.*`/landing object (S4b will ERROR and block); qualify your DDL targets (`silver.x`, not a
bare `x` after `SET search_path`) or S4b fails closed to a WARNING.

## 7. Which validations are STATIC checker rules (now wired in)

Statically checkable from committed text — these are now **wired into `retail check`**
(feature 003, as SQL-family rules that cite the RC default they enforce):
- **RC7 → S5** — type discipline: money/qty not cast to float; leading-zero ids not cast to int.
- **RC13 / S4b** — idempotent migration *form* (already a checker rule; layer-aware per §6).
- **RC14 → S6** — star structure: each `gold.dim_*` has a `-1` unknown member (static, partial).
  S6 EXEMPTS `dim_date*` (the date dim is a marked date table and carries none).
- **(date) → S8** — the inverse of S6: a marked `gold.dim_date*` must carry **no** `-1`/NULL
  member (ERROR); an unmatched fact date fails via `date_sk NOT NULL`, never a sentinel.
- **RC15 → S7** — `dim_date` built from `generate_series`, not `SELECT DISTINCT date`.

These are *structural / textual* — parseable from the migration SQL without a database. The
checker now reports **26 rules**; on C086 they all pass (the migrations satisfy the defaults).

## 8. Which validations require LIVE DB validation

Provable only against a running database — belong to the deferred **`retail validate`** live
surface, NOT static `retail check`:
- **RC2** — PK uniqueness on the *materialized* transformed rows.
- **RC15 (coverage half)** — the generated calendar actually spans every real `sale_date`.
- **RC16** — 0 orphan FKs + source→silver→gold→BI measure-total reconciliation.

These need the data; a comment or DDL shape cannot prove them. They are the acceptance checks to
run (read-only) against the deployed DB for every table — as done for C086 in §5.
