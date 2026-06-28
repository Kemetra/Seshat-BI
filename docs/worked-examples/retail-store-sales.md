# Worked Example — retail_store_sales (Kaggle "Retail Store Sales, dirty")

> **The second validated Seshat BI worked example — and the first that traverses the
> FULL seven-stage readiness spine** (Source Ready → … → Dashboard Ready, with Publish
> Ready held at `warning` by design). Where `c086-pharmacy.md` proves the medallion
> *build* (bronze → silver → gold + live validation), this example proves the rest of
> the spine: metric contracts, a governed PBIP model, a dashboard design bound to those
> contracts, a handoff pack, and an honest **approval-retraction** when an approved
> artifact materially changed.
>
> This doc is the **evidence record** that `retail_store_sales` is built and governed
> correctly, and the **reusable second pattern** a future retail table copies. It does
> not restate the source artifacts — it references and summarizes them.

**Verdict:** *retail_store_sales is the kit's first end-to-end-to-Dashboard-Ready table:
12,575 transactions through a clean Kimball star, 5 owner-approved metric contracts, a
governed TMDL model whose every measure binds 1:1 to a contract, and an approved
10-visual dashboard design — with Publish Ready deliberately at `warning` pending a
fresh approval after the DiscountedTransactionRate correction. It is the proof that the
generic kit is genuinely generic: same spine, a different domain, different cleaning
deviations (RC8 N/A; RC4 keep), no C086 specifics leaking in.*

**Why a second example matters (hard rule #7).** *"C086 is the first worked example, not
the universal schema."* A single example can't prove genericity. This table was chosen
to differ from C086 on exactly the axes that catch a leaked assumption: **no returns**
(C086's RC8 return-detection is N/A here), a **kept pseudonymous customer key** (an RC4
deviation, where C086 dropped PII early), an **unknown-status discount nuance** absent
from C086, and an English-only Kaggle source (no Arabic↔English mapping). The kit
absorbed all four without a C086-specific rule firing.

**Source artifacts (read these for detail; this doc summarizes them):**
- Mapping set: `mappings/retail_store_sales/` (`source-profile.md`, `source-map.yaml`,
  `assumptions.md`, `unresolved-questions.md`, `reconciliation-report.md`)
- Build: `warehouse/migrations/0003_create_silver_retail_store_sales.sql`,
  `0004_create_gold_retail_store_sales_star.sql`
- Metrics: `mappings/retail_store_sales/metrics/*.yaml` (5 contracts)
- Semantic model: `powerbi/RetailStoreSales.SemanticModel` (governed TMDL)
- Design: `mappings/retail_store_sales/design/` (layout, visual list, binding map)
- Handoff: `mappings/retail_store_sales/handoff/` (pack + review checklist)
- Readiness state: `mappings/retail_store_sales/readiness-status.yaml` (the spine record)
- Process: `docs/medallion-playbook.md`; the spine: `docs/readiness/readiness-model.md`
- Governance: `retail check` (static gate) + `retail validate` (live surface)

**How to reuse this for a new table:** copy this section structure, swap
`retail_store_sales` for the new table, walk the seven stages, and fill each section's
**Evidence** from that table's own artifacts. The *questions and checks* generalize; the
*answers* are per-table. For the build-only first half, `c086-pharmacy.md` remains the
canonical reference; for the contracts → model → dashboard → handoff second half, this
doc is the reference.

> **Namespace note.** "RC1–RC16" are the **ADR 0002 cleaning defaults**
> (`docs/decisions/0002-retail-cleaning-defaults.md`). The static governance checker uses a separate
> `S*`/`D*`/`C*`/`G*`/`R*` rule namespace (in `src/retail/rules/`). A cleaning default
> reads `RC<n>`; a checker rule reads e.g. `S8`. The two do not collide (feature 002).

---

## Readiness at a glance

The per-table spine record (`mappings/retail_store_sales/readiness-status.yaml`) at the
time of writing:

| # | Stage | Status | One-line evidence |
|---|-------|--------|-------------------|
| 1 | Source Ready | **pass** | 12,575 rows, 11 cols profiled; PK `transaction_id` unique; semantics + PII ruling confirmed by data owner |
| 2 | Mapping Ready | **pass** | grain/PK/PII mapped; gate CLEARED; Q1–Q4 answered; owner approval recorded |
| 3 | Silver Ready | **pass** | `0003_*.sql` applied; 12,575 silver rows; `retail check` exit 0; PK re-proven (V-RC2) |
| 4 | Gold Ready | **pass** | `0004_*.sql` applied; `retail validate` exit 0; 0 orphan FKs; penny-exact reconcile |
| 5 | Semantic Model Ready | **pass** | 5 approved contracts; governed TMDL; every measure binds 1:1; `retail-semantic-check` = pass |
| 6 | Dashboard Ready | **pass** | 10-visual design; all 5 contracts bound, 0 orphan visuals; design review approved |
| 7 | Publish Ready | **warning** | handoff pack complete + reviewable; **fresh publish approval pending** (see §7) |

No stage was entered before the prior stage was `pass`. Publish Ready is `warning`, not
`pass`, **on purpose** — that is the governance lesson of §7, not a defect.

---

## 1. Source Ready — profile & semantics

**What this table did.** The Kaggle "retail store sales (dirty)" CSV landed faithfully
as all-TEXT into `bronze.retail_store_sales` (**12,575 rows**, 11 source columns + 2
lineage). `retail.profile` measured every column over a **read-only** connection, with
missingness as `'' OR NULL` (a faithful landing writes `''`, so `IS NULL` alone reports
zero). Semantics were *derived from the data, not field names*: `item ↔ category` is
**1:1** (0 fan-out); `total_spent == price_per_unit * quantity` holds on **11,362/11,362
= 100%** of complete rows; **no returns exist** (all measures strictly positive, no
return-flag column — confirmed with the data owner). Grain ratio: 12,575 rows / 12,575
distinct `transaction_id` = **1.00**.

**Rule it proves.** Playbook Phase 1 (profile) + RC1 (grain first) + RC2 (PK on landed
data, re-proven later on the transform). The Source Ready gate's "semantics PROPOSED, not
asserted" discipline: the profile shipped as `warning` until the owner confirmed.

**Evidence.** `mappings/retail_store_sales/source-profile.md` (per-column missingness +
the measured 1:1 and money-identity rates); the four open questions in
`unresolved-questions.md`, all answered 2026-06-25 by the data owner.

**Future tables — copy / watch.** *Copy:* land bronze faithful-as-TEXT; derive
semantics by measuring (the 1:1 and the money identity are *checked*, never assumed);
state the grain ratio explicitly. *Watch:* "missing" is `''` not `NULL` after a faithful
landing; never assert a returns rule from a field name — confirm it against the data and
the owner; don't promote a source profile to `pass` while a PII or grain semantic is
still open.

## 2. Mapping Ready — the gate, and two deliberate RC deviations

**What this table did.** `source-map.yaml` decided grain first (one transaction), PK
`transaction_id` → degenerate dim, and placed every one of the 11 columns into the gold
star. It adopted the RC defaults **and recorded two explicit deviations** — the
genericity test:
- **RC8 (returns) = N/A.** No returns in this source; `is_return` is not derived.
  Recorded as a deviation with the data fact (strictly-positive measures, no
  return column) in `assumptions.md`.
- **RC4 (auto-drop a customer key) = deviated → KEEP.** `customer_id` is a pseudonymous
  surrogate (`CUST_xx`, 25 distinct), not raw PII, so it is **kept** as `dim_customer`,
  flagged `pii: true` for governance, and the keep was the owner's Q1 ruling.

**Rule it proves.** The source-mapping gate (hard rule #2: no source goes to silver
until Mapping Ready passes) + RC1/RC2 + the "record deviations, never silently diverge"
discipline. Crucially it proves the gate is **domain-agnostic**: C086's PII default was
*drop early*; here the same default was *deviated to keep*, with a recorded reason — the
kit did not force C086's answer.

**Evidence.** `source-map.yaml` (`defaults.deviations[]` for RC8/RC4; per-column
placement), `assumptions.md`, `unresolved-questions.md` (Gate status: **CLEARED**;
Q1–Q4 answered), and the `mapping_ready` approval in `readiness-status.yaml` `approvals[]`
(data_owner, 2026-06-25).

**Future tables — copy / watch.** *Copy:* the RC default set IS the starting point —
confirm each, and record only *deviations* with their triggering data fact. *Watch:* PII
is a governance judgment (Principle V), not an agent decision — `customer_id` was kept
*because the owner ruled it*, and the column stays `pii: true` so publish-safety is
re-examined downstream.

## 3. Silver Ready — typed/cleaned flat table

**What this table did.** `0003_*.sql` built `silver.retail_store_sales` (12,575 rows) as
an idempotent `DROP+CREATE` inside one transaction. It TRIMs every text column, converts
`''`→NULL via `NULLIF` (RC5), casts money/qty to exact `NUMERIC(12,2)` and the date to
`DATE` (RC7), and keeps the `TXN_`/`CUST_` ids as **TEXT**. The discount flag encodes the
**Q2 ruling**: `CASE lower(NULLIF(discount_applied,'')) … ELSE NULL` — a blank is
**UNKNOWN → NULL**, never coerced to `False`. No junk-row or zero-value filter (the
profile found none); missing measures stay NULL (a transaction with a blank price is
still a real row).

**Rule it proves.** RC5/RC7 + RC13 (idempotent numbered migration) + the layer-aware S4b
policy (DROP+CREATE-in-txn on a rebuildable `silver.*` is the sanctioned pattern, not a
finding). `retail check` exits 0 on the migration.

**Evidence.** `0003_create_silver_retail_store_sales.sql`; `readiness-status.yaml`
`silver_ready` (exit 0, S1–S7; PK re-proven unique on the transform via V-RC2).

**Future tables — copy / watch.** *Copy:* one typed/cleaned silver per source at the
declared grain; `NULLIF` before any cast; keep id-like keys TEXT (leading zeros). *Watch:*
bake the owner's semantic rulings into SQL *exactly* — the blank-discount `ELSE NULL` is
the whole Q2 ruling in one line; coercing it to `False` would silently change every
discount metric.

## 4. Gold Ready — Kimball star + live validation

**What this table did.** `0004_*.sql` built the gold star sharing the `gold` schema with
C086 (so the objects carry an **`_rss` suffix**): **1 fact** `gold.fct_sales_rss` (12,575
rows, transaction grain) + **4 entity dims** (customer, product, payment_method,
location) + **`dim_date_rss`**. Every entity dim carries a **`-1` UNKNOWN member**; fact
FKs `COALESCE(…, -1)`; `transaction_id` and `discount_applied` are **degenerate dims** on
the fact. `dim_date_rss` is a **marked date table built from `generate_series`**
(2022-01-01..2025-01-18, contiguous) and **deliberately carries no `-1` member** (rule
S8) — an unmatched fact date is rejected by `date_sk NOT NULL`, never bucketed. The
**9.65% missing `item`** (1,213 rows) lands correctly on the product `-1` member (the Q4
ruling).

**Rule it proves.** RC14 (star + `-1` member + FK-COALESCE + degenerate dims), RC15
(contiguous date dim), S8 (marked date table carries no sentinel). `retail validate`
exits 0.

**Evidence.** `0004_create_gold_retail_store_sales_star.sql`;
`mappings/retail_store_sales/reconciliation-report.md` (verdict **PASS**) and
`readiness-status.yaml` `gold_ready`, from a read-only `retail validate` run against the
`training` DB (cluster `db-pgsql-fra1-29712`): PK unique on the transform, date coverage
complete, **0 orphan FKs across all 5 dims**, penny-exact reconciliation (quantity
**66,276**; total_spent **1,552,071.00**), and the 1,213 missing-item rows confirmed on
the `-1` member.

**Future tables — copy / watch.** *Copy:* suffix-namespace a second star sharing a schema
(`_rss`) so it never collides with the first; add FK constraints *after* load so the `-1`
members and rows exist; run PK-uniqueness + date-coverage + 0-orphans + penny-exact
reconcile before declaring Gold Ready. *Watch:* `retail validate` reads the gold object
names from `source-map.yaml` **verbatim** (it does not prepend `gold.`), so the names
there must be schema-qualified and match the migration exactly.

## 5. Semantic Model Ready — contracts + a governed model

**What this table did.** Five **metric contracts** were authored and owner-approved
(`mappings/retail_store_sales/metrics/`): `TotalSales`, `TotalQuantity`,
`TransactionCount`, `AvgTransactionValue`, `DiscountedTransactionRate`. A governed PBIP
model was authored as **TMDL** (`powerbi/RetailStoreSales.SemanticModel`): 5 dims +
`fct_sales_rss`, a **marked date table**, and a **parameterized connection (no real
host committed)**. `retail-semantic-check`'s 5-step verdict is **pass**: `retail check`
exit 0 (D1–D8/C1/R1/G6), `gold_ready` is `pass`, and **every model measure binds 1:1 to
an approved contract**.

**Rule it proves.** Hard rule #5 (no dashboard before contracts) is *upstream-enforced
here*: contracts and the governed model exist and bind before any design. F009 (contract
store) + F010 (semantic-model readiness) + the `metric_drift` machine-readable
definition that ties a contract's numerator/denominator to the DAX.

**Evidence.** the 5 `mappings/retail_store_sales/metrics/*.yaml`;
`powerbi/RetailStoreSales.SemanticModel` (TMDL);
`readiness-status.yaml` `semantic_model_ready` + the `approvals[]` entry (data_owner,
2026-06-25).

**Future tables — copy / watch.** *Copy:* one contract per measure, each with grain +
formula intent + owner; bind every model measure to exactly one contract (no orphan
measures, no orphan contracts); parameterize the connection — never commit a host or
connection string. *Watch:* a non-additive ratio (here `DiscountedTransactionRate`) must
state its denominator in the contract — that single decision is what §7 turns on.

## 6. Dashboard Ready — design bound to contracts

**What this table did.** The `dashboard-design` verb produced a **single executive
overview page** (`mappings/retail_store_sales/design/`): a KPI strip (4 headline
numbers), a TotalSales trend, category/channel/payment diagnostics, and a top-customers
exception table — **10 measure-bearing visuals**, each bound to **exactly one** of the 5
approved contracts (**zero orphan visuals**). Dimension slicers (date/category/location/
payment_method) are not contract-bound and so are excluded from the binding map. The
design review was **APPROVED by the data owner** (binding-map sign-off block).

**Rule it proves.** Hard rule #5 enforced at the gate: **no contract → no visual**. F011
(design-from-contracts) + F011A (the four-surface visual foundation). The design is
**authoring only** — no publish, no Power BI Desktop, no DB, no execution adapter
(that is the deferred, gated F016).

**Evidence.** `mappings/retail_store_sales/design/` (`dashboard-layout.md`,
`visual-list.md`, `visual-contract-binding-map.md`); `readiness-status.yaml`
`dashboard_ready` + `approvals[]` (data_owner, 2026-06-25).

**Future tables — copy / watch.** *Copy:* one business question per page region; every
measure-bearing visual binds to one contract; keep detail cross-tabs to a single
diagnostic/exception table (F011A). *Watch:* the design records what is **out of
answerable scope** (here: margin — no cost data; returns — none in this source) instead
of inventing a metric to fill a visual.

## 7. Publish Ready — `warning` by design: an honest approval retraction

**What this table did — the governance lesson.** The BI handoff pack is assembled and
reviewable (`mappings/retail_store_sales/handoff/`), every required section resolves to a
committed artifact, and a publish approval **was** recorded on 2026-06-25 — **then
retracted the same day**. The retraction is the point: the original pack framed
`DiscountedTransactionRate` as **33.55%** (denominator = *all* transactions). The owner's
**Q2 ruling** is that a blank discount status is **UNKNOWN and excluded**, making the
approved rate **50.37%** (4,219 / 8,376 known-status transactions; 33.55% is only a
*floor* caveat, 33.39% is the unknown-status coverage gap). When the contract was
corrected to the ruling, **the approved artifact materially changed**, so the prior
approval no longer applied and was retracted as stale. Publish Ready therefore sits at
**`warning`**: pack complete and reviewable, but `pass` requires a **fresh** publish
approval against the corrected pack.

**Rule it proves.** Principle V / hard rule #9: **no self-granted approval, no fake
confidence.** An approval is bound to the *exact artifact* it was given against; change
the artifact materially and the approval is void until a named human re-approves. The
agent records the `warning` and the `next_action` — it does **not** advance the stage.

**Evidence.** `readiness-status.yaml` `publish_ready` (`status: warning`, the
`blocking_reasons[]` explaining the retraction, and the `approvals[]` note recording the
retracted approval); `mappings/retail_store_sales/metrics/DiscountedTransactionRate.yaml` (the corrected
formula_intent + the `expected_value` 0.5037 the `retail value-check` L4 proxy asserts).

**Future tables — copy / watch.** *Copy:* when a contract changes, walk *forward* and
re-examine every approval that cited it; record retractions explicitly with the reason
and the next allowed action. *Watch:* a ratio's denominator is a semantic ruling, not a
formula detail — get it wrong and the published headline number is wrong; the `metric_drift`
+ `value-check` checks exist precisely to pin the approved denominator. **Live publish to
a Power BI workspace remains the deferred, gated F016 execution adapter** — out of scope
here by design.

---

## What this example adds over C086 (the genericity proof)

| Axis | C086 (pharmacy) | retail_store_sales | What it proves |
|------|-----------------|--------------------|----------------|
| Spine depth | build + live validation (to Gold) | full spine to Dashboard Ready (+ Publish `warning`) | the contracts→model→design→handoff half of the spine works end-to-end |
| Returns (RC8) | derived from an authoritative billing code | **N/A** (no returns; recorded deviation) | the kit doesn't force a returns rule where none exists |
| Customer PII (RC4) | dropped early (patient data) | **kept** (pseudonymous surrogate; owner ruling) | the same default resolves either way, per the owner — no C086 answer baked in |
| Language | Arabic↔English mapping | English-only Kaggle source | no Arabic-dictionary assumption leaks into a generic run |
| A ratio metric | n/a | `DiscountedTransactionRate` denominator ruling + retraction | non-additive contracts + the approval-retraction governance path |

## See also

- The first example (build half, canonical): `docs/worked-examples/c086-pharmacy.md`.
- The spine: `docs/readiness/readiness-model.md` and the seven
  `docs/readiness/<stage>-ready.md` stage docs.
- Method: `docs/medallion-playbook.md` (the 7 phases).
- The table's own artifacts: `mappings/retail_store_sales/` and
  `powerbi/RetailStoreSales.SemanticModel`.
- Governance: `retail check` / `retail validate` (`src/retail/`); the rule meanings:
  the `retail-govern` skill.
