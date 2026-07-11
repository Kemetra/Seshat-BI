# Medallion Cleaning Playbook — Standard Plan for Any Retail Table

A repeatable, analyst-interactive method for taking a raw retail table from a
faithful landing through to a Power-BI-ready star schema. It is the **corrected**
version of the process used to build the C086 pharmacy warehouse — the detours we
hit (grain decided too late, PII caught only at review, returns flag added only
after) are fixed here so they don't recur.

**Scope.** Generic to any retail sales table. C086 (El Ezaby pharmacy) is the worked
example throughout. The playbook generalizes the *questions and checks* — never the
*answers*. "Unify categorical encodings to one standard," not "Arabic → English."

**How to read this.** Each phase has: **Goal → Steps → Analyst decision points
(ready-to-ask) → Traps & checks → Exit gate.** An agent can drive the decision
points as a live Q&A with the analyst; a human can run them as a checklist.

**Mechanics this builds on (don't re-derive):** Kimball dimensional modeling and
medallion mechanics live in the `data-warehouse-pipeline` skill. This playbook adds
the *interactive decision protocol* and the *retail trap-checklist* on top.

**Worked example:** see `docs/worked-examples/retail-store-sales.md` — the fully-instantiated
reference: the 7 phases carried out on the `retail_store_sales` table, continued past the
build through the full readiness spine (metric contracts → governed model → dashboard design
→ handoff).

---

## Interaction protocol (how to run the Q&A)

These are the hard-won rules for the analyst conversation itself:

- **One decision topic at a time.** Don't bundle unrelated decisions into one question.
- **Recommend, then let the analyst decide.** Every decision point carries a flagged
  recommended default. The analyst overrides or accepts; you never decide silently.
- **Offer concrete choices, not open prose.** For "which columns to drop," present
  *every* column as a selectable option, not a summary the analyst must reply to.
- **One column / one item per question** when the analyst asks for that granularity.
- **Wide lists exceed a 4-option picker** — fall back to a written table the analyst
  edits (a markdown file with a blank decision column) when there are many items.
- **Assemble decisions into a durable ruleset as you go.** The ruleset is the artifact;
  defer *how to materialize* (view vs table) until the rules are agreed.
- **Surface conflicts, don't bury them.** If an answer contradicts an earlier one or a
  data fact, stop and reconcile before proceeding.

---

## Phase 1 — Connect & profile

**Goal:** know the table's shape, quality, and semantics before any decision.

**Steps**
1. Connect read-only to the source (credentials from a secrets manager / vault at
   runtime; never hardcode). Confirm row count, column count, schemas.
2. **Profiling pass A — shape & quality:** per-column missingness, numeric/date
   parse-ability, distinct cardinality, candidate-key uniqueness, duplicates.
3. **Profiling pass B — semantics:** column redundancy/derivability, code↔label pairs,
   dimension fan-out (id → name 1:1?), hierarchy nesting, the returns population,
   encoding corruption, outliers.

**Analyst decision points** — usually none yet; profiling informs later phases.

**Traps & checks**
- **"Missing" is often the empty string `''`, not SQL `NULL`.** A landing loader that
  writes `'' if value is None` makes `COUNT(*) WHERE col IS NULL` return 0 for every
  column — a false "no missing data." Measure missingness as `trim(col) = '' OR col IS NULL`.
- **Derive relationships from the data, not from field names.** Don't infer that two
  money columns are equal because their SAP names look related — compute the row-level
  equality/violation rate. (C086: `gross == net+tax` held on only 34% of rows.)
- **Check for cross-file schema drift.** If the landing was assembled from multiple
  files padded to one header, a column-order change in one file silently misaligns
  values. Profile low-cardinality categoricals grouped by source file.
- **Report violation counts, not averages.** Two columns can have identical means yet
  disagree on thousands of rows.

**Exit gate:** you can state the grain, the candidate keys, the returns rule, and the
top data-quality issues — with numbers.

---

## Phase 2 — Cleaning decisions (interactive, GRAIN-FIRST)

**Goal:** agree every cleaning rule with the analyst. Order matters — **grain is
decided first** because it dictates which columns are structural keys before you
decide anything else.

**The HYBRID walk (how to sequence the steps below).** Run grouped by dependency, not
strictly one-global-pass-per-step. Per-step loop: present step → keep/enhance/change the
step → apply → next (the walk both cleans the table and refines the pipeline).

- **A. Global-first (decide across ALL columns):** **2.1 keep/drop FIRST** → **2.0 grain/PK
  which VALIDATES the key survived** (and may choose a generated surrogate key, keeping the
  natural key silver-only for the proof) → **2.2 PII** (a flagged *name* is not auto-PII:
  individual/patient data is sensitive → drop default; staff names and B2B company names
  are legitimate non-sensitive attributes).
- **B. Per-survivor (decide these TOGETHER, one kept column at a time):** 2.3 rename +
  2.5 type + 2.4 missing-value + gold placement. Missing-value is per-column (NO global
  `'' → NULL` baseline) and only for columns where profiled `missing_count > 0`. A
  present-but-wrong value is a *value remap* in a derived column, not a sentinel.
- **C. Global-tail (across all rows):** 2.6 row filters (reconcile source − dropped =
  silver, accounting for OVERLAP; a blank-targeting filter must run PRE-sentinel) →
  2.7/2.8 derived columns (generate the fact surrogate AFTER filters), rollups, hierarchy.
- **D. Gate:** Phase 4 review. Recording the judgment-call answers is NOT map approval —
  no silver SQL until the full map is reviewed.

The rule is **per-column vs global by dependency**: global when a decision is table-wide
(PII policy) or cross-row (filters); per-column when it depends only on that column's own
keep. Naming: warehouse SQL identifiers are snake_case (`product_id`, `gross_sales`,
`sale_sk`) -- rule S1 flags quoted non-snake_case columns; PascalCase is a Power BI
model-layer display choice, never a SQL identifier. The date dim carries no
`-1`/sentinel member (markable as a Power BI date table).

### 2.0 Grain (FIRST — do not skip or defer)

**Ask:** *"What does ONE ROW represent? Confirm with the data: how many rows vs how
many of the candidate business entity (e.g. invoices)?"*
- Recommend the **lowest grain the source provides** (e.g. invoice line item) — you can
  always roll up later, never down. (C086: line-item grain, 2.42 lines/invoice.)
- Then confirm the **primary key** and verify it is unique *on the data*.
- **Consequence rule:** the PK columns are now non-droppable. Decide grain before the
  column filter so you don't drop a key and then have to reverse it.

### 2.1 Column filter

**Ask (per column, every column offered as a choice):** *"Keep or drop?"* with a
flagged recommendation and the evidence (missingness %, cardinality, redundancy).
- Recommend dropping: 100%-empty columns, single-value columns, verified duplicates
  (≥95% equal to another), code halves of 1:1 code↔label pairs.
- Flag for analyst judgment: high-null-but-meaningful, finance/SAP refs, sparse classes.
- **Keep the PK columns** (from 2.0) regardless.

### 2.2 Governance / PII scan (EARLY — not at review)

**Ask:** *"Do any kept columns contain personal or sensitive data that will reach the
BI layer?"* Phone numbers, national/insurance IDs, names linked to behavior.
- Recommend **dropping PII outright** unless there's a stated need; a published BI
  dataset is effectively irreversible (cached tiles, exports). (C086: insurance phone
  + claim number were patient health data → dropped.)
- If a need exists: hash/mask, or isolate in a restricted dataset — never rely on
  row-level security to hide a *column*.

### 2.3 Renaming

**Ask (per column):** recommended `snake_case` analyst-friendly name / keep original /
type your own. Fix typos and opaque source codes; leave already-clear names alone.

### 2.4 Missing-value handling

This step splits across the hybrid walk: the **baseline is global**, the **sentinel
choice is per-column** (bundled with rename/type/placement in phase B).
- **Baseline (global, phase A):** convert `''` → NULL on **all** columns first, so
  missingness is honest before any row filter runs.
- **Sentinel-vs-NULL (per column, phase B):** for each kept column, decide NULL
  (genuinely-unknown) vs a sentinel (`'UNKNOWN'`, `'UNCLASSIFIED'`) for dimension
  attributes that must group cleanly; verify the sentinel doesn't collide with a real
  value. Facts stay NULL (a sentinel would corrupt sums). This is a per-column judgment,
  decided with that column's rename/type/placement — not one global toggle.

### 2.5 Data types

**Ask:** confirm numeric precision, date vs timestamp, and **IDs stay TEXT**.
- Money → `NUMERIC(p,s)` (exact, never float). Quantities → `NUMERIC`.
- Dates → `DATE` if no real time component.
- **IDs/codes → TEXT** when they have leading zeros (casting to int corrupts them).
  Ordinal line numbers with no leading zeros → small integer (sorts correctly).

### 2.6 Row filters

**Ask:** which row populations to drop vs keep+flag.
- **Returns:** recommend **keep + a derived `is_return` boolean** from the *authoritative
  column* (e.g. billing type), never the quantity sign alone. Returns near-always need
  to be separable for net-of-returns analysis.
- Junk/non-product rows (test codes, blank keys): drop, listing the count.
- Zero-value / adjustment lines: decide explicitly; note the count dropped.

### 2.7 Categorical standardization & business rollups

**Ask:** *"Unify categorical encodings to one standard?"* (e.g. one language, one case).
**Ask:** *"Add a business rollup? Provide the mapping."* — a higher-level grouping the
analyst supplies (the playbook never invents the mapping). (C086: `business_segment`
PHARMA/HVI/NON-PHARMA from divisions.)

### 2.8 Hierarchy modeling

**Ask:** *"Is the category hierarchy a clean tree, or does a child appear under multiple
parents?"* Verify on data.
- If not a clean tree, recommend **flat denormalized levels** (one path per row, totals
  don't double-count) over a snowflake. Forcing a single parent destroys real overlap.

**Exit gate:** every topic above has a recorded decision.

---

## Phase 3 — Assemble the ruleset

**Goal:** one durable spec capturing every Phase-2 decision.

- Write it to a file: dropped columns + reasons, rename map, missing-value rules, type
  map, row filters, standardizations, derived columns, the PK, and a flagged-caveats list.
- State the **final shape** explicitly: source rows → cleaned rows (show the filter math),
  and final column count (reconcile: source cols = dropped + kept; + derived).
- **Defer materialization** (view vs table) to Phase 5 — agree *what*, not *how*, here.

**Exit gate:** the analyst signs off on the ruleset.

---

## Phase 4 — Review gate (before building)

**Goal:** catch modeling flaws and build bugs while they're cheap.

- Review the ruleset from multiple lenses: dimensional modeling, data quality, the
  business domain, the BI consumer, document self-consistency, governance, build safety.
- **Verify every material finding against the live data** — default a claim to "refuted"
  until a query confirms it. (Plausible-but-wrong findings waste cycles.)
- Re-decide anything the review proves was based on a wrong premise.

**Exit gate:** GO / GO-WITH-CHANGES, with all CRITICAL findings resolved.

---

## Phase 5 — Build silver (typed & cleaned)

**Goal:** materialize the cleaned table, correctly the first time.

**Build order inside the transform (this order is load-bearing):**
1. `TRIM` all text columns.
2. Fix encoding (strip/whitelist garbage characters) on display columns.
3. Junk-row filters that match `''` — run **before** `''`→NULL (NULL never matches `IN`).
4. `''` → NULL.
5. Numeric/date casts via `NULLIF(trim(x),'')::type`.
6. Numeric-based row filters — on the **cast** value, not text (`'0.0' ≠ '0'`).
7. Derived columns (return flag, business rollup with an `ELSE 'UNMAPPED'` default).

**Materialize as a TABLE** (not a view) so it can carry a declared PK for the gold FKs.
Use an idempotent numbered migration: `DROP TABLE IF EXISTS … CREATE TABLE AS SELECT …
ADD PRIMARY KEY … CREATE INDEX …` in one transaction. UTF-8, no BOM.

**Traps & checks**
- **Dry-run the PK on the TRANSFORMED output, not raw source.** Raw uniqueness can break
  after `TRIM`/cast (two raw-distinct keys collapse, or a cast yields NULL). Run the full
  SELECT read-only and assert: row count = target, `COUNT(*) = COUNT(DISTINCT pk)`, no
  NULL in PK columns, no `'UNMAPPED'`, before you `ADD PRIMARY KEY`.
- **Validate after build:** row count, PK uniqueness, no orphan NULLs in measures,
  business invariant (e.g. `net ≤ gross` on sales), and **measure totals reconcile to
  the source**.

**Exit gate:** all validation checks pass.

---

## Phase 6 — Design & build gold (Kimball star)

**Goal:** the Power-BI-ready star. (Mechanics: `data-warehouse-pipeline` skill.)

**Storage:** gold lives in **DigitalOcean Postgres** (same DB as bronze/silver) — **not**
Parquet. Power BI connects to Postgres gold in **Import mode** (VertiPaq caches it columnar
at refresh, so reports are fast regardless of source format; a Parquet copy would be a
redundant second source of truth). Add a Parquet export only later if a non-Power-BI columnar
consumer, a volume problem, or an immutable-snapshot need appears — never as a default. This
matches the shipped governance rule **RC8** ("Power BI reads `gold`"): one canonical gold.

- One fact at the silver grain + conformed dimensions (one per business entity).
- Surrogate `_sk` keys; keep natural keys as attributes.
- **Unknown member at `_sk = -1`** in every ENTITY dim; fact FKs `COALESCE` missing
  lookups to -1. The DATE dim is the EXCEPTION (rule S8): it carries NO -1 member (a
  marked date table rejects nulls), and an unmatched fact date fails via `date_sk NOT
  NULL` rather than a sentinel.
- Transaction identifiers with no attributes (invoice no, line no) → **degenerate
  dimensions** on the fact, not their own dim.
- **Date dimension is a CONTIGUOUS generated calendar** over the full span — never
  `SELECT DISTINCT date` (missing days break time-intelligence).
- Flat hierarchy denormalized onto the product dim (per 2.8).

**Traps & checks**
- After load: **0 orphan FKs** (except intentional `-1`), FK constraints enforced, fact
  PK still unique, and **measures reconcile to the penny against silver**.

**Exit gate:** referential integrity clean + measures reconcile.

---

## Phase 7 — Data dictionary & BI model

- **Data dictionary:** document every layer against the *deployed* schema (types,
  grain, PK), the mappings (encodings, rollups), and the caveats (PII excluded,
  returns handling, out-of-scope items). The caveats are the highest-value part.
- **BI model:** build measures with returns separated by default
  (`Gross = sales WHERE NOT is_return`; net-of-returns = sum over all). Mark the date
  table. Build the drill hierarchy from the flat columns. Key dimensions on IDs, never
  on names. Verify measures live, reconciling to the warehouse totals.

---

## Appendix A — Retail trap-checklist (reusable assertions)

Run these on every table; each is a hard-won check, not a nicety.

1. Missingness measured as `'' OR NULL`, never `IS NULL` alone.
2. Column relationships derived from row-level data, not field names.
3. Candidate keys verified unique **on the data** before declaring grain.
4. Cross-file schema drift checked (categoricals by source file).
5. PII identified and removed/masked **before** the BI layer.
6. Returns flagged from the authoritative column, not the measure sign.
7. PK uniqueness re-verified on the **transformed** output, not raw source.
8. Junk-row filters run before `''`→NULL; numeric filters on cast values.
9. IDs with leading zeros kept as TEXT.
10. Date dimension contiguous (generated), not distinct-from-data.
11. Measure totals reconcile across **every** layer (source → silver → gold → BI).
12. Document counts reconcile (source cols = dropped + kept + derived).

### Tool-robustness rules (the live surface, not the data)

Hard-won when the first table was driven end-to-end against a real DB (ADR 0005);
these guard the TOOL against arbitrary data, distinct from the cleaning traps above.

13. **Type-branch auto-discovered columns.** Any check that applies a text-only
    function (`trim`, `''`) to every column of an auto-discovered table MUST branch
    on `data_type`: TEXT -> `''OR NULL`; non-text (timestamptz/numeric/boolean, a
    lineage column) -> plain `IS NULL`. (`trim()` on a timestamptz crashes.)
14. **Never bank a live exit code without its evidence.** A `retail validate` exit 0
    is a pass ONLY with the "running live checks" banner + a per-check result. Run the
    `retail` console script (not `python -m seshat.cli`); export `.env` first. An exit
    code alone is not proof a check ran.
15. **Schema-resolve artifact names at the read boundary.** A table/object name read
    from a `source-map.yaml` and spliced into SQL must be schema-qualified when read
    (a `gold_star` name -> the `gold` schema), bare or already-qualified both handled.
16. **Comment-strip before token/identifier rules.** A SQL rule that scans for
    identifiers MUST run over comment-stripped text, or quoted prose in a `--`/`/* */`
    comment will false-trip it.

Hard-won when an independent reviewer (Codex) reviewed the first end-to-end PR and
found nine defects a green self-test + green `retail check` + green `retail validate`
all missed (ADR 0006). These continue the tool-robustness set:

17. **A comment-stripper feeding an identifier rule MUST be quote-aware.** A `--` or
    `/* */` inside a `'...'` string literal or `"..."` quoted identifier is DATA, not
    a comment marker -- copy it through. A quote-blind stripper opens a phantom comment
    on a `'--'` literal and BLANKS the rest of the line, hiding any real bad identifier
    after it (a silent false NEGATIVE -- worse than a false positive in a checker).
18. **A marked date table carries NO unknown/sentinel member.** Every OTHER gold dim
    gets a `-1 'UNKNOWN'` member (trap: RC14); the DATE dim is the EXCEPTION. It becomes
    a marked date table (`dataCategory: Time`), which Power BI validates as
    unique/contiguous/NO-nulls -- a `-1, NULL` member breaks refresh / time-intelligence
    even though the SQL succeeds. Rule `S8` (ERROR) enforces this; `S6` exempts the date
    dim. An unmatched/NULL FACT date is handled OUTSIDE the calendar (fail-loud via
    `date_sk NOT NULL`, or a nullable FK + DAX), NEVER absorbed by a `-1` date member.
19. **Never COALESCE a real-but-unmatched key to the unknown member.** `COALESCE(
    dd.date_sk, -1)` over a hard-coded calendar span silently buckets a real out-of-span
    date to Unknown -- and the coverage/orphan checks stay green (the `-1` member is a
    valid FK target). Debare the join and let `NOT NULL` reject the unmatched row: a
    coverage gap must FAIL the load, not masquerade as "Unknown".
20. **Count parsed RECORDS, not physical lines; fail loud on ragged rows.** When
    reconciling a CSV load, count with the SAME parser COPY consumes (a quoted embedded
    newline is ONE record across many lines). Reserve GENERATED dedup names (a real
    header can collide with a previously-generated suffix). A row WIDER than the header
    must fail loud (truncating it corrupts faithful landing); a SHORT row is padded.
    Lazy-load the optional DB driver so `--help` / pure helpers work without the `db`
    extra.

## Appendix B — SQL skeletons

```sql
-- NULLIF before cast (empty string -> NULL -> typed)
NULLIF(trim(col), '')::numeric(18,2)

-- junk filter BEFORE ''->NULL (so '' is matched)
WHERE trim(category) NOT IN ('JUNK_A', 'JUNK_B', '')

-- zero-value filter on the CAST value, not text
WHERE NOT (NULLIF(trim(qty),'')::numeric = 0 AND NULLIF(trim(amt),'')::numeric = 0)

-- idempotent materialized build with PK, one transaction
BEGIN;
  DROP TABLE IF EXISTS silver.tbl;
  CREATE TABLE silver.tbl AS SELECT ...;
  ALTER TABLE silver.tbl ADD PRIMARY KEY (key_a, key_b);
  CREATE INDEX idx_tbl_date ON silver.tbl (date_col);
COMMIT;

-- unknown member, then real rows (Postgres IDENTITY)
INSERT INTO gold.dim_x OVERRIDING SYSTEM VALUE VALUES (-1, 'UNKNOWN', 'Unknown');
INSERT INTO gold.dim_x (nk, name) SELECT nk, max(name) FROM silver.tbl GROUP BY nk;

-- contiguous date dimension
INSERT INTO gold.dim_date
SELECT to_char(d,'YYYYMMDD')::int, d::date, extract(year FROM d)::smallint, ...
FROM generate_series(DATE '2023-01-01', DATE '2025-12-31', INTERVAL '1 day') g(d);

-- fact FK lookups COALESCE to the unknown member
COALESCE(dx.x_sk, -1)
```
