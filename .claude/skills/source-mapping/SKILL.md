---
name: source-mapping
description: >-
  Drive a raw retail source table through the source-mapping gate before any
  silver SQL exists. Use when someone asks to map, model, profile, or onboard a
  new bronze table toward Power BI in the Seshat BI repo -- profile
  the source, decide grain/PK, fill the five mapping artifacts into
  mappings/<table>/, and stop at the gate. This skill ENFORCES the rule that no
  silver.* SQL is written until the map is reviewed and approved. It profiles and
  authors and stops; it does NOT write silver/gold SQL and does NOT build the
  Power BI model.
---

# source-mapping

The source-mapping gate is the kit's one load-bearing rule (constitution
Principle IV): **before any `silver.*` SQL is written, the source MUST be
profiled and mapped into committed, reviewed artifacts.** This skill runs that
gate: profile -> author the five artifacts -> stop at judgment calls -> hard-stop
before silver. It formalizes Phases 1-4 of `docs/medallion-playbook.md`; the
playbook stays authoritative on HOW to decide, the templates on WHAT to record.

## Scope boundary (read first)

This skill profiles a source and authors the mapping artifacts, then STOPS. It
does NOT write `silver.*` or `gold.*` SQL, does NOT call pbi-cli or Power BI
Desktop, and does NOT decide the judgment calls Principle V reserves for a human.
Silver is downstream of an APPROVED map -- approval is the reviewer's action, not
this skill's.

## The five artifacts (copy blanks from templates/ into mappings/<table>/)

Per [ADR 0003](../../../docs/decisions/0003-mapping-artifact-location.md), a
table's filled set lives in `mappings/<table>/`:

1. `source-profile.md` -- Phase 1 numbers (this skill fills the mechanical ones).
2. `source-map.yaml` -- the machine-readable spine (grain+PK first, per-column
   keep/drop/rename/type/PII/gold-placement, the gold star, derived columns).
3. `assumptions.md` -- which RC1-RC16 defaults were ADOPTED vs DEVIATED (each
   deviation cites its triggering data fact).
4. `unresolved-questions.md` -- the build-blocking judgment calls + who answers.
5. `reconciliation-report.md` -- the blank the later live run fills (RC16).

## Cleaning chain (canonical order -- the HYBRID walk)

A fixed, dependency-ordered chain. The shape is **hybrid**: order-sensitive steps run as
GLOBAL passes, intra-column steps run PER-SURVIVOR (each kept column resolved in one
bundle), cross-row steps run as a GLOBAL tail. The agent recommends a default at every
step; the human decides (Principle V). NONE advance to silver -- the gate (D) is the stop.

**Per-step loop:** present the step (purpose + default + its behavior on the table) ->
human chooses keep / enhance / change the STEP -> apply -> next. The walk both cleans the
table AND lets the pipeline itself be refined.

**A. GLOBAL-FIRST (decide across ALL columns):**
1. **Keep / Drop** (Phase 2.1 / RC3) -- FIRST. One global pass over the inventory.
2. **Grain & PK** (Phase 2.0 / RC1, RC2) -- VALIDATES that the key survived step 1; ERROR
   (or surface) if a needed key column was dropped. May choose a GENERATED SURROGATE key
   over the natural grain (first-class option); if so, keep the natural key SILVER-ONLY
   for the uniqueness/dedup proof and expose only the surrogate to gold (a bare surrogate
   is unique by construction and cannot detect a double-load).
3. **PII** (Phase 2.2 / RC4) -- EARLY. A flagged NAME is NOT auto-PII: distinguish
   individual/patient data (sensitive -> drop default) from STAFF names (KPI dimensions)
   and COMPANY names (B2B org) -- the latter two are legitimate non-sensitive attributes.

**B. PER-SURVIVOR (one kept column at a time, decided TOGETHER):**
4. **Rename** (2.3) + **Type** (2.5 / RC7) + **Missing-value** (2.4 / RC5,RC6) + **Gold
   placement**. Missing-value is decided HERE, per column (no global `''->NULL` baseline),
   and ONLY for columns whose profiled `missing_count > 0` (skip 0-blank columns). A
   present-but-wrong value (e.g. a site code in a customer id) is a VALUE REMAP in a
   derived column, NOT a missing-value sentinel.

**C. GLOBAL-TAIL (cross-row):**
5. **Row filters** (2.6) -- which rows to drop (junk/zero-value); state the count and
   reconcile (`source - dropped = silver`, accounting for OVERLAP). ORDERING (load-bearing):
   a filter that targets BLANKS must evaluate PRE-sentinel (before step B's sentinel
   substitution), else `trim(col)=''` matches 0 rows and those rows wrongly survive.
6. **Derive** (2.7-2.8 / RC8, RC11, RC12) -- is_return from the AUTHORITATIVE column;
   value remaps; surrogate keys (generate the fact SK AFTER filters so it numbers
   surviving rows); analyst-supplied rollups; flat hierarchy. The date dim carries NO
   `-1`/unknown/sentinel member (so Power BI can mark it a date table, S8); an unmatched
   fact date fails via `Date_SK NOT NULL`.

**D. GATE (hard stop; Principle IV):**
7. **Named-human review** -- recording the judgment-call ANSWERS is NOT map approval. No
   `silver.*` SQL until the full map is reviewed.

**Naming:** warehouse SQL identifiers are **snake_case** (`product_id`, `gross_sales`,
`sale_sk`) -- rule **S1** flags quoted non-snake_case columns (a quoted mixed-case name
forces a case-sensitive Postgres column, a footgun). PascalCase is a **Power BI
model-layer** display choice (rename in the semantic model), NEVER a SQL identifier.

> Per-column vs global is by DEPENDENCY, not preference: global when a decision is
> table-wide (PII policy) or cross-row (filters); per-column when it depends only on that
> column's own keep decision. See `docs/medallion-playbook.md` Phase 2 for the rationale.

## Procedure

### 1. Locate
Confirm the bronze `schema.table` exists. Ask the analyst/agent for the candidate
PK column(s) to test (grain is decided FIRST, Phase 2.0 / RC1).

### 2. Profile (mechanical) -- via profile.py
Run the mechanical profiler over a read-only connection and record the numbers
into `mappings/<table>/source-profile.md`:

```python
import os
from retail.validate import resolve_dsn, make_psycopg2_runner
from retail.profile import profile

dsn = resolve_dsn(dict(os.environ))     # DATABASE_URL or ANALYTICS_DB_* parts
runner = make_psycopg2_runner(dsn)      # read-only; needs the `db` extra
result = profile(runner, "bronze.<table>", ("<pk_a>", "<pk_b>"))
```

`result` gives: `row_count`, `column_count`, per-column `missing_count` /
`missing_pct` (measured `''OR NULL`, NEVER `IS NULL` alone -- the load-bearing
trap, RC5) / `distinct_cardinality`, and the candidate-PK proof (`total`,
`distinct_pk`, `null_pk`, `is_unique`). Write each into the source-profile table
and the Candidate grain & PK section.

### 3. Profile (semantic) -- PROPOSE, do not invent (Principle V)
The semantic rows -- code<->label 1:1 rate, dimension fan-out (`id -> name`),
hierarchy multi-parent, the AUTHORITATIVE returns column, money-relationship
identities, cross-file drift -- need the table's MEANING. profile.py does NOT
compute these. PROPOSE each from the data + column names, then raise it as an
`unresolved-questions.md` entry for human confirmation. Never invent a business
rollup, a PII ruling, or the returns column.

### 4. Author the map and assumptions
Starting from the RC1-RC16 defaults, fill `source-map.yaml` (grain+PK first, then
per-column decisions, the gold star, derived columns) and `assumptions.md`
(adopted vs deviated, each deviation citing its triggering data fact). Keep all
text ASCII, snake_case silver names, short paths (Windows 260 limit).

### 5. Stop-and-ask (Principle V)
Raise `unresolved-questions.md` entries, each with a who-must-answer owner, for:
business-rollup mapping (analyst supplies the full value->group table), PII
publish-safety (governance sign-off; default drop), grain ambiguity (candidate PK
not unique on the data), sentinel-vs-null choice, and any build-blocking question.

### 6. GATE -- hard stop (Principle IV)
Emit the `reconciliation-report.md` blank and STOP. State plainly: no `silver.*`
SQL may be written until the map is reviewed and approved. Hand the filled set to
the reviewer; do not proceed to silver.

## Deferred/live-boundary mode (no DSN or no `db` extra)

If `resolve_dsn(...)` returns None or psycopg2 is not installed, do NOT traceback
and do NOT pretend a profile ran. The live boundary is deferred BY DESIGN:
credentials + the optional `db` extra are user-supplied under constitution
Principle VIII. In this mode:

- Report the boundary and print the exact enable steps:
  `pip install 'retail[db]'`, then set `DATABASE_URL` (or the `ANALYTICS_DB_*`
  vars) in the gitignored `.env`. Never commit a real DSN.
- STAY USEFUL: copy the five template blanks into `mappings/<table>/`, fill their
  STRUCTURE, mark the mechanical profile numbers `[PENDING LIVE PROFILE]`, still
  drive the semantic stop-and-ask (Step 3) and the gate (Step 6).

## See also

- Gate + principles: `docs/architecture/tower-bi-agent-kit.md` Sec 5;
  `.specify/memory/constitution.md` Principles IV, V.
- Method / defaults: `docs/medallion-playbook.md`;
  `docs/decisions/0002-retail-cleaning-defaults.md` (RC1-RC16).
- Live half (after silver/gold exist): the `retail-validate` skill.
- A filled instance: a filled worked example under `docs/worked-examples/` (an
  example, never the universal schema).

## Orchestration

When a table is being driven end-to-end, the `retail-orchestrate` conductor skill
sequences this verb with the others and runs the self-heal loop against the gate
exit code. This skill stays single-purpose: it does its job and STOPS. The loop
(run gate -> classify findings -> auto-fix mechanical / HARD-STOP judgment calls ->
re-run) lives ONLY in `retail-orchestrate`, never here.
