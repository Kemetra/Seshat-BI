---
name: consumer-data-dictionary
description: >-
  Compose ONE plain-language consumer data dictionary for ONE table in the
  Seshat BI repo, so an analyst who has access to a published table/report can
  find "what does this column/measure mean" in one place. Use when someone
  asks to "generate the data dictionary for <table>", "explain what these gold
  columns mean", or "give me a plain-language reference for this table's
  metrics". This is a Product Module, artifact-writing: it READS committed
  artifacts only (the table's committed gold migration SQL, its
  source-map.yaml mapping rationale, and its metric-contract YAML files),
  composes one ordered document listing every deployed gold column and every
  metric contract with its meaning cited to a committed source, then STOPS. A
  column or metric with no committed consumer-legible meaning gets an explicit
  GAP marker -- it NEVER invents, infers, or paraphrases a plausible business
  definition. It writes NO upstream artifact, defines NO metric, resolves NO
  mapping question, moves NO readiness stage, opens NO DB/PBIP connection, and
  emits NO numeric score and NO completeness count. Generic across all mapped,
  gold-built tables via a table parameter (no C086 specifics).
---

# consumer-data-dictionary

- **Roadmap feature:** F040 (proposed; the roadmap-ledger row is deferred to
  integration time -- see research.md section 1.4; not yet a confirmed
  ledger entry). **On-disk spec:** `specs/101-consumer-data-dictionary/`.
- **Authority category:** Product Module / `artifact-writing`
  (the F024 enumerated declaration -- see `docs/architecture/product-modules.md`).

Today, "what does this column/measure mean" answers exist but are scattered
across BUILDER-facing artifacts nobody wrote for a self-serve analyst: a gold
column's business meaning lives as a mapping-decision `reason` string inside
`mappings/<table>/source-map.yaml` (written for the mapping-gate reviewer, not
a report reader); a measure's plain-language meaning lives as `formula_intent`
inside `mappings/<table>/metrics/<Metric>.yaml` (already consumer-legible
prose); and the handoff pack's own data-dictionary section exists to satisfy
the Publish Ready gate, not to serve the analyst who later queries the
published model. This skill is the COMPOSER that assembles those scattered,
already-committed artifacts into ONE ordered, plain-language reference for the
CONSUMER. It FILLS the dictionary; it originates no meaning and owns no truth.
Every entry cites the committed source it came from; where no committed
consumer-legible meaning exists, the entry is an explicit GAP, never invented
prose.

## Boundary against neighbouring shipped work (read first)

- **F013 BI Handoff Pack** (`templates/handoff/bi-handoff-pack.md`, item e
  "Data dictionary") is a REQUIRED section of the Publish Ready (Stage 7) gate
  bundle: its audience is the data-owner/governance reviewer deciding whether
  to authorize release, its lifecycle moment is BEFORE publish (gate
  evidence), and a mismatch against the deployed schema FAILS the checklist.
  This module's dictionary is an OPTIONAL companion consumed AFTER a table is
  published, by the analyst querying it self-serve; it adds NO gate, NO
  blocking reason, and NO required section to Publish Ready (following the
  `answerability-summary.md` precedent). It composes from the SAME upstream
  truth but does not edit, re-render, or duplicate-govern F013's item (e).
- **F028 evidence-pack-generator** (`.claude/skills/evidence-pack-generator/`,
  spec 022) composes a late-stage, 10-section READINESS evidence bundle
  (blockers, scorecards, approvals) for the Semantic Model -> Dashboard ->
  Publish window. This module composes a MEANING reference (what a column/
  measure means), not a readiness bundle; it carries no blocker list, no
  stage status, no approval slot, and is not part of any stage's `evidence[]`
  by default. Different output filename (FR-018), no collision.
- **The `power-bi-docs` skill family** generates model documentation FROM A
  LIVE, CONNECTED semantic model (`pbi connect` required). This module is
  Principle-VIII static-first: it reads only committed, on-disk artifacts and
  never opens a live Power BI or database connection; any live-schema drift
  against the deployed model is marked PENDING, never silently assumed
  reconciled.

This module adds NO new readiness stage and NO new `seshat check` rule -- it
composes from artifacts other tools already produced (the F024 Product
Module boundary).

## Authority declaration (F024) -- the filled module contract

This module declares EXACTLY ONE of the five F024 authority categories.
Quoted verbatim from `docs/architecture/product-modules.md`: a **Product
Module** is "a focused tool that consumes Core Authority and presents,
summarizes, or derives from it. A module MUST declare exactly one capability
level: `read-only` | `artifact-writing` | `execution-capable`. It never
creates truth." This module's capability level is **`artifact-writing`**: it
derives one committed artifact (the dictionary) from committed evidence, and
-- per the matrix -- MAY write derived evidence but MUST NOT execute.

The filled `templates/module-contract.md` declaration follows.

---

### Module Contract -- Consumer Data Dictionary

- **Authority category:** Product Module
- **Capability level:** `artifact-writing`  *(exactly one)*
- **Product layer:** `6`  *(the functional axis -- see docs/roadmap/roadmap.md; Dashboard & Delivery / BI handoff, the same layer F013's handoff pack and F028's evidence pack occupy)*
- **Roadmap feature:** `F040 (proposed; not yet ledger-confirmed)`  **On-disk spec:** `specs/101-consumer-data-dictionary/`
- **Owner:** the analyst consuming the published table/report (self-serve; no approval seam -- this module names no gate owner because it is not a gate)
- **Status:** Authored (docs/templates; no runtime code -- the agent is the runtime)

#### What it does (one line)

> Composes ONE table's deployed gold columns (from the committed gold
> migration SQL) and its metric contracts (from `mappings/<table>/metrics/`)
> into one ordered, plain-language dictionary, citing every entry to a
> committed source and recording an explicit gap wherever no committed
> consumer-legible meaning exists -- inventing nothing.

#### Core Authority it READS

It reads; it never writes these.

- `warehouse/migrations/*_create_gold_<table>*.sql` -- the committed gold
  migration SQL; the authoritative, static source of the table's DEPLOYED
  gold-star columns (Principle VIII: static, not a live catalog read).
- `mappings/<table>/source-map.yaml` -- each gold column's committed mapping
  rationale (the `reason` field, matched by `source_name` or the `gold_star`
  dimension's attribute name -- see Compose Step 2).
- `mappings/<table>/metrics/*.yaml` -- every metric contract's `formula_intent`
  and its recorded `readiness.status`, approved and pending alike.

#### Derived evidence it WRITES

Composed FROM committed evidence; never a new metric definition, mapping
decision, or stage change.

- `mappings/<table>/consumer-data-dictionary.md` -- one filled copy of
  `templates/consumer-data-dictionary.md` for the target table. This is the
  ONLY file the module writes.

#### Approved step it EXECUTES

- none (capability is `artifact-writing`, not `execution-capable`; it
  composes and STOPS, touching no DB and publishing nothing).

#### Forbidden operations (the matrix says NO)

These hold for EVERY Product Module regardless of capability level:

- MUST NOT create truth: no defining/approving/paraphrasing business meaning
  (a metric's formula, grain, or a column's business definition), no
  resolving an open mapping question (Principle V).
- MUST NOT write to, modify, or append to `source-map.yaml`, any
  `metrics/*.yaml` contract, the gold migration SQL, `readiness-status.yaml`,
  `unresolved-questions.md`, or the handoff pack.
- MUST NOT add a `blocking_reasons[]` or `approvals[]` entry, or move any
  readiness stage; its existence or absence is never a gate requirement.
- MUST NOT connect to a DB or external service, read a live Power BI/PBIP
  surface, or invoke a deferred execution adapter (F016) or spec-only
  runtime (F031-F033).
- MUST NOT emit a numeric / maturity / confidence score (hard rule #9), and
  MUST NOT emit a completeness / "N of M" count.

#### How it handles a missing input

When a required Core Authority input is absent, unfilled, or unreadable, the
module SURFACES it as an explicit GAP marker naming the missing/unreadable
path and stops treating that source as content -- it never fabricates the
input, never generates a plausible meaning to fill the gap, and never
silently drops the entry (Principle V; stop-and-ask, expressed here as
"gap-and-cite" rather than a hard stop, since the dictionary as a whole still
composes around the gap).

---

## The input contract (committed-only)

The dictionary composes EXACTLY these committed sources -- no live DB, no
PBIP model, no Power BI execution adapter (F016), no spec-only runtime
(F031-F033), no network. Any live signal must already be recorded as
committed evidence before the dictionary can cite it.

1. `warehouse/migrations/*_create_gold_<table>*.sql` -- the deployed gold
   columns, in `CREATE TABLE` column-definition order (section 1).
2. `mappings/<table>/source-map.yaml` -- each column's committed mapping
   rationale (section 1).
3. `mappings/<table>/metrics/*.yaml` -- every metric contract's
   `formula_intent` and `readiness.status`, in lexical filename order
   (section 2).

No fourth artifact family is read. This module does not read TMDL
(`powerbi/*.SemanticModel/definition/tables/*.tmdl`) and does not read a
dashboard visual-contract binding map -- neither is part of "what a column or
measure means," which is this module's sole subject.

## Compose steps (numbered; do not reorder)

### 1. Resolve the table's deployed gold columns
Resolve `warehouse/migrations/*_create_gold_<table>*.sql` (the committed gold
migration SQL for the target table). Read every `CREATE TABLE` statement it
contains and enumerate each declared column, in that statement's own
column-definition order, as the `column_entries[]` source (FR-001, FR-003).
If NO such file exists for this table (the table has not reached Gold
Ready), do NOT fabricate a column list from a design or profiling document:
record ONE document-level `GAP: document -- no_gold_migration_found` marker
naming the path pattern checked, and proceed to compose the rest of the
document around that gap (FR-014).

### 2. Resolve each column's committed meaning
Resolve `mappings/<table>/source-map.yaml`. For each gold column from Step 1,
find its matching entry by the source-map's own recorded `source_name`
(fact / degenerate-dim columns) or by the `gold_star` dimension's listed
attribute name (dimension attributes) -- NEVER by position in the `CREATE
TABLE` statement and NEVER by fuzzy or approximate string matching on the
column name (FR-005, Clarification Q5). When a match is found and it carries
a `reason`, cite that `reason` text VERBATIM with its exact source-map
location -- never paraphrased, never simplified, never generated (FR-005;
see the OPEN Q1 carve-out below). When NO matching `source_name`/`gold_star`
attribute entry exists at all (e.g. a surrogate key generated only in the
gold migration, or an RC15 calendar-derived `dim_date` attribute such as
`month_name`, `day_name`, or `is_weekend`), or a matching entry exists but
records no `reason`, emit a `GAP:` marker instead (reason_code
`no_source_map_entry` or `no_reason_recorded`) naming the column and the path
checked -- do NOT generate, infer, or paraphrase a plausible business
definition to fill it (FR-008).

### 3. Apply the PII / deployed-only filter
Before listing a column, confirm it is actually present in the gold
migration SQL read in Step 1. A column marked `pii: true` and dropped in
`source-map.yaml` (never reaches gold), or any other column never
materialized to gold, MUST NOT appear in the dictionary at all -- not even as
a gap. The dictionary describes the DEPLOYED gold star only (FR-010).

### 4. Detect and record gold-SQL-vs-source-map disagreement
While matching columns in Step 2, if the gold migration SQL and
`source-map.yaml` disagree on a column's presence or name (a column in one
source has no reasonable counterpart in the other), record the discrepancy
as a `drift_note` / `GAP:` marker (reason_code `source_disagreement`) naming
both paths checked. NEVER silently prefer one source as authoritative.
Live-schema reconciliation against the actually-deployed database stays out
of scope (Principle VIII; PENDING) -- this module detects only a STATIC
disagreement between two already-committed files (FR-019).

### 5. Resolve every metric contract
Resolve every file under `mappings/<table>/metrics/*.yaml`, in lexical
(alphabetical) filename order. For each file found, carry forward its
`formula_intent` text VERBATIM and surface its recorded `readiness.status`
as-is; list approved AND pending contracts alike -- never filtered to
`pass`-only -- each clearly marked with its own status so a non-`pass`
contract is never presented as if it were approved (FR-004, FR-006,
Clarification Q4). When a metric contract file referenced under
`mappings/<table>/metrics/` is missing or unreadable, record a `GAP:` marker
(reason_code `contract_missing_or_unreadable`) citing the attempted path --
never a silent drop of that metric from the listing (User Story 2 Acceptance
Scenario 3).

### 6. Cite every entry
Bind every entry (column and metric alike) to at least one repo-relative
committed source path it was composed from, matching the template's field
shape (FR-007). An entry with no citable path is itself a contradiction --
it must be a `GAP:` marker, never an uncited assertion.

### 7. Assemble in fixed order
Render the document as: Header, then Gold Column Entries (gold-migration-SQL
column definition order), then Metric Entries (lexical metrics-folder
filename order), then Document-Level Gaps (FR-001, Clarification Q2). Do not
invent a business-relevance ranking or any other ordering.

### 8. Apply the no-score / no-count rule
The generated document MUST NOT contain a numeric confidence/health/maturity
score or a completeness count / "N of M" tally anywhere -- gaps are named
markers only (hard rule #9, FR-013).

### 9. Write and STOP
Write EXACTLY ONE file: `mappings/<table>/consumer-data-dictionary.md`
(FR-018), table-co-located under the table's mappings folder, distinct from
the handoff pack's item (e) and any F028 evidence-pack filename. Regenerating
overwrites only this module's own output path. The module MUST NOT write to,
modify, or append to `source-map.yaml`, any `metrics/*.yaml` contract, the
gold migration SQL, `readiness-status.yaml`, `unresolved-questions.md`, or
the handoff pack; it MUST NOT add a `blocking_reasons[]` or `approvals[]`
entry or move any readiness stage; it MUST NOT define, approve, revise, or
resolve any metric's formula, grain, or business meaning, or resolve any
open mapping question (FR-009, FR-011, FR-012). Any judgment call surfaced
in the dictionary -- a source disagreement, an unreadable contract, a
business-meaning gap -- is recorded as a GAP for a human to resolve
elsewhere; this module never resolves it itself (Principle V).

## Principle-V carve-out -- FR-008 / Clarification Q1 (OPEN, do not resolve)

When a gold column's only committed meaning is a TECHNICAL source-map
`reason` written for the mapping-gate reviewer (e.g. "the grain key; unique
on the data -> degenerate dim on the fact (RC14)"), whether this module MAY
GENERATE a simplified, consumer-plain paraphrase of that rationale (e.g.
"a unique identifier for each transaction"), or MUST always fall back to
verbatim-cite-or-gap, is **OPEN** -- a Principle-V question for the retail-kpi
/ data-owner (named human TBD at plan/approval time) to rule on. This skill
does NOT resolve Q1 and does NOT build a paraphrase-generation capability.
Until a named human rules, Compose Step 2 above applies the verbatim-cite-
or-gap default ONLY: quote the `reason` as recorded, or mark an explicit gap
-- never a generated gloss.

## No score, no count (hard rule #9)

The dictionary emits NO numeric confidence / health / maturity value and NO
completeness or "N of M" count anywhere (FR-013, SC-003). Gaps are expressed
only as explicit `GAP:` markers with a closed `reason_code` and
`checked_paths[]` (see the Gap Marker shape below). If a score or count is
requested, refuse and return the cited-or-gap picture instead.

## Gap marker shape (Clarification Q3, fixed -- do not invent a new format)

Every gap is a `GAP:` line carrying exactly:

- `label` -- the fixed, greppable prefix `GAP:` (enables `grep -n "GAP:"`
  verification).
- `subject` -- the column name, metric name, or `"document"` (for a
  table-wide gap).
- `reason_code` -- one of the closed enum: `no_source_map_entry` |
  `no_reason_recorded` | `contract_missing_or_unreadable` |
  `no_gold_migration_found` | `source_disagreement`. A sixth, ad hoc reason
  is out of scope for this version (Principle VI: extend deliberately, not
  silently).
- `checked_paths[]` -- a non-empty list of the repo-relative path(s) that
  were checked and found missing, empty, unreadable, or disagreeing.

A gap marker never contains a percentage, a count, or any numeric
confidence/health/maturity value.

## Honest-state rules (never invent, never silently reconcile)

| Situation | What the composer does |
|-----------|------------------------|
| No committed gold migration SQL exists for the table | ONE document-level `GAP: document -- no_gold_migration_found`; no fabricated column list from a design/profiling doc (FR-014) |
| A gold column has no matching `source-map.yaml` `source_name`/`gold_star` attribute entry | `GAP: <column> -- no_source_map_entry`, never matched positionally or by fuzzy name (FR-005/FR-008, Clarification Q5) |
| A matched source-map entry records no `reason` | `GAP: <column> -- no_reason_recorded` (FR-008) |
| A gold column is marked `pii: true` and dropped in `source-map.yaml` | omit the column entirely -- it is not in the deployed gold star, and it is not even a gap (FR-010) |
| The gold migration SQL and `source-map.yaml` disagree on a column's presence or name | `drift_note` / `GAP: document -- source_disagreement` naming both paths checked; never silently prefer one source (FR-019) |
| A metric contract file is missing or unreadable | `GAP: <metric> -- contract_missing_or_unreadable` citing the attempted path; never a silent drop (User Story 2 Acceptance Scenario 3) |
| A metric contract's `readiness.status` is not `pass` | list it anyway, clearly marked as NOT YET APPROVED; never presented as if approved (FR-006, Clarification Q4) |
| Whether a technical source-map `reason` may be paraphrased into consumer-plain prose | OPEN (FR-008/Q1); apply verbatim-cite-or-gap only until a named human rules |
| A numeric confidence/health score or an "N of M" count is requested | refuse; return the cited-or-gap picture instead (hard rule #9, FR-013) |
| Live data or a PBIP model is requested as a source | out of scope; the composer reads only committed artifacts (FR-002) |

## Generic only (Principle VII)

The template (`templates/consumer-data-dictionary.md`) and every fixed
section label in this skill carry NO worked-example (C086 / retail_store_
sales) column name, grain key, or metric name. `retail_store_sales` appears
in this doc and in `quickstart.md` only as a CITED FILLED INSTANCE (e.g. its
`transaction_id` column's `reason` field, illustrating the verbatim-cite
behavior) -- never inlined into the template body or a fixed label. The
module resolves a generic `mappings/<table>/` and gold-migration path per
table (FR-015, SC-006).

**Illustrative example (cited, not baked in):** in the committed
`mappings/retail_store_sales/source-map.yaml`, the `transaction_id` column's
`reason` reads "the grain key; unique on the data -> degenerate dim on the
fact (RC14)" -- a technical mapping rationale. A dictionary entry for this
column quotes that `reason` verbatim with its source path; it does not
rewrite it into "a unique identifier for each transaction" (that rewriting
is exactly the OPEN FR-008/Q1 question above, and this module does not
perform it).

ASCII only, UTF-8 no BOM (use `--` and `->`, no glyphs); short repo-relative
paths (Windows 260-char budget) -- FR-016.

## Composes-only proof

After a run, `git status` shows the only new/modified file is the one
derived dictionary at `mappings/<table>/consumer-data-dictionary.md`. No
source artifact (`source-map.yaml`, any `metrics/*.yaml`, the gold migration
SQL, `readiness-status.yaml`, the handoff pack) is modified, and no
readiness stage moved. The skill triggered no `seshat check` / `retail
validate` run of its own and opened no DB connection (FR-011, SC-004).

## What the agent must NOT do

- Do NOT generate, infer, or paraphrase a plausible business definition for a
  column whose only committed meaning is a technical source-map `reason` --
  FR-008/Q1 is OPEN; always fall back to verbatim-cite-or-gap.
- Do NOT omit a deployed gold column because it lacks a committed meaning --
  record a `GAP:` marker instead; never silently drop it.
- Do NOT list a column that source-map.yaml marks `pii: true` and dropped, or
  any column never materialized to gold.
- Do NOT filter metric entries to `pass`-only -- list every contract found,
  clearly marking non-`pass` ones as not yet approved.
- Do NOT silently drop a missing/unreadable metric contract -- record a
  `GAP:` marker citing the attempted path.
- Do NOT silently prefer the gold migration SQL or `source-map.yaml` when
  they disagree -- record the disagreement as a gap.
- Do NOT write, modify, or append to `source-map.yaml`, any `metrics/*.yaml`
  contract, the gold migration SQL, `readiness-status.yaml`,
  `unresolved-questions.md`, or the handoff pack.
- Do NOT add a `blocking_reasons[]` or `approvals[]` entry, or move any
  readiness stage; do NOT treat this module's existence/absence as a gate
  requirement.
- Do NOT define, approve, revise, or resolve any metric's formula, grain, or
  business meaning, or resolve any open mapping question.
- Do NOT emit a numeric confidence/health/maturity score or a completeness
  count/percentage.
- Do NOT read a live database or PBIP model; do NOT call the Power BI
  execution adapter (F016) or any spec-only runtime (F031-F033).
- Do NOT add a `seshat check` rule, define a new readiness stage, or alter a
  gate.
- Do NOT inline C086 / retail_store_sales specifics into the template or a
  fixed section label.

## See also

- The output shape: `../../../templates/consumer-data-dictionary.md` (the
  generic copy-me dictionary).
- The neighbours it stays distinct from: F013 BI Handoff Pack
  (`../../../templates/handoff/bi-handoff-pack.md` item e) and F028 Evidence
  Pack Generator (`../../../.claude/skills/evidence-pack-generator/SKILL.md`).
- The authority contract: `../../../docs/architecture/product-modules.md`
  (the five categories + the matrix), `../../../templates/module-contract.md`
  (the copy-me declaration filled above).
- The upstream sources it reads: `../../../warehouse/migrations/` (gold
  migration SQL), `../../../templates/source-map.yaml` (schema; filled copy
  at `mappings/<table>/source-map.yaml`), `../../../templates/metric-
  contract.yaml` (schema; filled copies at `mappings/<table>/metrics/*.yaml`).
- The spec: `../../../specs/101-consumer-data-dictionary/spec.md`. A cited
  filled instance of its inputs lives at
  `../../../mappings/retail_store_sales/`.

## Orchestration

When a table has reached Gold Ready and an analyst wants a self-serve
reference, the conductor may invoke this skill AFTER Gold Ready and
independently of any later stage (Semantic Model Ready, Dashboard Ready,
Publish Ready) -- it is never a prerequisite for any of them. This skill
stays single-purpose: it composes the dictionary for one table, cites every
entry to a committed source, records an explicit gap wherever no committed
meaning exists, and STOPS. Defining or revising a metric's meaning is the
metric-contract-store's own gate (F009), never here; recording a stage
approval is the Approval Console (F027) / Core Authority, never here.
