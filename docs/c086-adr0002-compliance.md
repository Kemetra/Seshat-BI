# C086 — ADR 0002 Compliance Matrix

> Narrative wrapper: `docs/worked-examples/c086-pharmacy.md` (this matrix is its §4).

> **Purpose:** validate the *existing* C086 warehouse (`warehouse/migrations/0001_*`,
> `0002_*`) against the 16 retail cleaning/modeling defaults in
> `docs/decisions/0002-retail-cleaning-defaults.md`, as preparation for formalizing
> C086 as the playbook's first worked example (#1).
> **Date:** 2026-06-24. **Assessed from:** the committed migration SQL (static read) +
> the `retail check` output already observed. **NOT** from a live database run.
>
> **Status legend:** PASS (satisfied, evidenced in artifacts) · WARN (intent met but a
> letter/quality gap) · FAIL (default not met) · LIVE (correct-by-construction in SQL
> but the *guarantee* needs the running DB to confirm — cannot be proven from text) ·
> N/A.

## Namespace disambiguation (RESOLVED — feature 002, 2026-06-24)

**ADR 0002 cleaning/modeling defaults now use `RC1–RC16` ("retail cleaning"). The governance
checker keeps its separate `D1–D8` for TMDL/DAX rules.** The two namespaces no longer collide:
a cleaning default reads `RC<n>`, a checker rule reads `D<n>`. Historically both used `D` —
e.g. the old ADR-D8 (returns-flag-from-authoritative-column) vs checker-D8 (Power-BI-reads-gold)
— which is why the ADR namespace was renamed to `RC*` (the checker IDs are in code and could
not move). This was the disambiguation required before any ADR default is wired into
`retail check`.

## Matrix

| ADR id | Default (summary) | C086 status | Evidence (from artifacts) | Override needed? | Future checker rule? |
|---|---|---|---|---|---|
| **RC1** | Lowest grain; grain decided first; PK fixed before column drop | **PASS** | `0001` header + grain comment: "invoice LINE ITEM. PK = (invoice_no, line_no)"; PK declared L159. Line-item is the atomic grain. | No | No — grain is a judgment, not statically decidable (the repo's known `fct_`/`dim_` gap). |
| **RC2** | Verify PK on data **and** on transformed output | **LIVE** | `0001` L157-159 comment claims the dry-run proved `(invoice_no,line_no)` unique post-transform; `ADD PRIMARY KEY` will fail the migration if not. The *guarantee* is enforced by Postgres at run time, not provable from SQL text. | No | **Maybe (live):** a `retail validate` live check (PK uniqueness on built silver) — belongs in the deferred live surface, not static. |
| **RC3** | Drop no-signal columns (empty/single-value/dup/code-half) | **PASS** | `0001` keeps human-readable labels, drops code halves; `billing_type` mapped to English, `billing_type_2`→`billing_type_code` kept as join key. PII columns dropped (see RC4). | No | No — "no signal" needs profiling data, not static text. |
| **RC4** | Remove PII **early**, before BI | **PASS** | `0001` L155 comment: `insurance_no`/`insurance_phone` DROPPED (patient health PII) — absent from the silver SELECT entirely. | No | **Candidate (heuristic):** a checker could flag *suspicious* column names (phone/insurance/national_id) reaching gold — best-effort, like C2 secret-scan. Note as low-confidence. |
| **RC5** | Empty string treated as missing (`''`→NULL; measure `'' OR NULL`) | **PASS** | `0001`: `NULLIF(x,'')` on every cast column; `UPDATE ... WHERE col IS NULL OR col = ''` for text sentinels (L150-154). Junk filter (L62) runs before NULLIF (H1 comment) — correct order. | No | **Candidate (static-ish):** could scan migration SQL for `IS NULL`-only missingness checks lacking the `''` arm — heuristic. |
| **RC6** | NULL for unknown facts; sentinel only for grouping dims, collision-verified | **PASS** | Sentinels `'UNKNOWN'`/`'UNCLASSIFIED'` applied only to dim text attributes (salesperson, job_title, brand, cluster) L150-154; comment claims 0-collision verified. `original_invoice_ref` left NULL (no fill) — correct (a fact, not a grouping dim). | No | No — collision check needs data. |
| **RC7** | Money/qty → exact NUMERIC; dates → DATE; leading-zero IDs → TEXT | **PASS** | `0001`: `numeric(18,2)`/`(18,4)` for money/qty; `::date` for sale_date; `product_id`/`customer_id`/`invoice_no` kept TEXT (leading-zeros comment L71,111); `line_no`→`smallint` (ordinal). | No | **DONE -> checker rule S5 (static).** Flags money/qty cast to float, or id-like columns cast to int. *(The RC* rename in feature 002 cleared the old checker-D7 name collision; S5 wired in feature 003.)* |
| **RC8** | Keep returns; `is_return` from authoritative column, not measure sign | **PASS** | `0001` L107-109: `is_return = billing_type_2 IN ('Z4','Z5','Z6','Z8','Z10')` (authoritative billing code), plus English 'Return' labels. Not derived from quantity sign. | No | No — "authoritative column" is table-specific knowledge. |
| **RC9** | Keep independent money measures; drop only true duplicates | **PASS** | `0001` keeps all four: `sales_amount`(gross), `net_amount`, `tax_amount`, `discount_amount` (L82-87). None collapsed. | No | No — derivability needs data. |
| **RC10** | Unify categorical encodings to one standard | **PASS** | `0001` L92-105: all 10 `billing_type` values → English, one standard; original Z-code kept separately as `billing_type_code`. | No | No — encoding-unification is table-specific. |
| **RC11** | Business rollups only from analyst-supplied mapping; never invented | **PASS** | `0001` L131-145: `business_segment` from an explicit division→segment CASE (PHARMA/HVI/NON-PHARMA), `ELSE 'UNMAPPED'` loud sentinel. Mapping is enumerated, not inferred. | No | No. |
| **RC12** | Non-tree hierarchy → flat denormalized levels, not snowflake | **PASS** | `0001` L118-125: product hierarchy kept flat (division/category/subcategory/segment/brand/group/cluster as columns), comment "multi-parent overlaps preserved". `dim_product` (`0002`) is one denormalized table — not snowflaked. | No | No — tree-vs-not needs data. |
| **RC13** | Silver as TABLE via **idempotent numbered migration**; transform order load-bearing | **PASS (resolved)** | `0001`/`0002` ARE transaction-idempotent (DROP+CREATE in BEGIN/COMMIT, numbered `NNNN_`); transform order correct. The 22 S4b warnings were the **rule** being wrong (blanket guarded-form), not the SQL — DROP+CREATE is the *correct* idempotency for rebuildable marts. **RESOLVED:** S4b is now layer-aware (commits `3d8443e`/`394f1ce`/`c75f5ba` on `fix/s4b-layer-aware`) — silver/gold DROP+CREATE-in-txn passes; bronze bare DROP/CREATE = ERROR; fail-closed on unknown schema. `retail check .` now shows **0 S4b findings** on C086. | No | **DONE** — S4b is the checker rule; refined to layer-aware. See §6 of the worked example. |
| **RC14** | Gold = Kimball star: conformed dims, `_sk`, unknown member `-1`, degenerate dims | **PASS** | `0002`: 6 dims + 1 fact at line grain; `_sk` IDENTITY PKs; `-1` unknown member inserted per dim (OVERRIDING SYSTEM VALUE); fact FKs `COALESCE(...,-1)` (L157-162); `invoice_no`/`line_no`/`original_invoice_ref` as degenerate dims on the fact (L132-135). Textbook. | No | **DONE -> checker rule S6 (static, partial):** checks each `gold.dim_*` has a `-1` member insert. Structural, parseable. |
| **RC15** | Date dim = **contiguous generated calendar**, never `SELECT DISTINCT` | **PASS (pattern) / LIVE (coverage)** | `0002` L114-127: `generate_series(2023-01-01 .. 2025-12-31, 1 day)` — contiguous, NOT distinct-from-data. Comment: "covers the 2 zero-sales gap days." Pattern is correct in SQL. **Coverage** (does the range actually span all `sale_date`s?) needs the live data. | No | **DONE -> checker rule S7 (static, pattern half).** Checks `dim_date` built from `generate_series` (good) vs `SELECT DISTINCT ... date` (bad). The contiguity *coverage* remains the deferred live half. |
| **RC16** | Reconcile measure totals every layer; assert 0 orphan FKs before done | **LIVE** | `0002` adds FK constraints AFTER load (L173-178) → Postgres rejects orphans at constraint-add time, so a successful migration *implies* 0 orphans. But the comment-claimed cross-layer total reconciliation (source→silver→gold→BI) is **not in the SQL** — it's a manual/validation step. Cannot prove from text. | No | **Maybe (live):** reconciliation is inherently a live-data check → `retail validate` (deferred live surface), not static. |

## LIVE verification (run 2026-06-24, read-only, against `ezaby_demo` on db-pgsql-fra1-29712)

The 3 LIVE items are now **confirmed against real data** (not just correct-by-construction):

- **RC2 — PASS.** `silver.sales_c086`: 246,916 rows = 246,916 distinct `(invoice_no,line_no)`, 0 NULL PK.
- **RC15 — PASS.** `gold.dim_date` 2023-01-01..2025-12-31 = 1,096 rows = exact span (contiguous);
  spans all `sale_date`s; **0** sale_dates missing from the calendar.
- **RC16 — PASS.** **0 hard orphan FKs** on all 6 dims; silver=fct=246,916 rows; all 5 measure totals
  reconcile silver↔gold to the penny (sales_amount 38,804,001.54; net 35,699,605.26; tax 1,108,355.29;
  discount -1,996,042.59; quantity 286,098.39).
- **Data-quality note (not a defect):** `salesperson_sk` has 71 fact rows mapped to the `-1` unknown
  member — i.e. ~71 line items lack salesperson attribution; the RC14 unknown-member pattern absorbs
  them correctly (no orphan). Worth surfacing to the analyst as a known gap.
- **Note:** data lives in DB `ezaby_demo` (cluster db-pgsql-fra1-29712), NOT `defaultdb`; `defaultdb`
  is empty. `.env` points at `ezaby_demo`.

## Summary (updated with live results)

- **PASS: 16/16** — all defaults satisfied. 12 static-PASS (RC1,RC3–RC12,RC14) + RC15 + the 3 live-confirmed
  (RC2, RC15-coverage, RC16).
- **WARN: 0** (RC13's bare-DDL-vs-S4b nuance is now **resolved** — S4b made layer-aware; see below).
- **FAIL: 0**

**RC13/S4b update (2026-06-24):** resolved by making S4b layer-aware (silver/gold DROP+CREATE-in-txn
allowed; bronze bare DROP/CREATE = ERROR; fail-closed on undetectable schema). `retail check .` now
reports 0 S4b findings on C086. C086 is **16/16 PASS with no open items.** Detail: worked example §6.

**Headline:** C086 is a **strong** worked example — it satisfies the spirit of all 16
defaults; nothing FAILs. The only *static* gap is **RC13** (bare DDL vs S4b guarded-form),
which is a known, already-surfaced warning and a policy decision, not a build defect. The
LIVE items (RC2/RC16 + RC15 coverage) are correct-by-construction in the SQL but their
*guarantees* are enforced at DB-run time — they belong to a future `retail validate` live
surface, not the static checker.

## Recommended next actions (stop here per instruction)

1. **Resolve RC13 (high priority).** Decide: reword C086's DDL to guarded forms to silence
   S4b, **or** teach S4b that "DROP+CREATE inside a single BEGIN/COMMIT" is a sanctioned
   idempotency pattern (relax the rule for that shape). This reconciles ADR-RC13 with
   checker-S4b. *(No code yet — this is the decision to make before #1 or wiring.)*
2. **Resolve the D-namespace collision** before wiring ANY ADR default into `retail check`.
   *(DONE — feature 002, 2026-06-24: ADR defaults renamed `D*`→`RC*`; checker keeps `D*`.)*
3. **For #1 (formalize C086 as worked example):** C086 passes — proceed. The matrix above
   IS the Phase-4 review-gate evidence the playbook asks for. The 3 LIVE items become the
   acceptance checks to run against the deployed DB when it exists.
4. **Which defaults became checker rules (DONE — feature 003):** the *statically checkable*
   defaults are now wired in — **RC7 → S5** (type discipline), **RC13/S4b** (idempotent form),
   **RC14 → S6** (star: -1 member), **RC15 pattern → S7** (generate_series vs distinct). Each is
   a SQL-family rule citing its RC default; `retail check` now reports 26 rules.
   The **live** candidates (RC2 PK, RC16 reconciliation, RC15 coverage) belong to the deferred
   `retail validate` surface, not static `retail check`.
