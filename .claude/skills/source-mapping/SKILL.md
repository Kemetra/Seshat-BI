---
name: source-mapping
description: >-
  Drive a raw retail source table through the source-mapping gate before any
  silver SQL exists. Use when someone asks to map, model, profile, or onboard a
  new bronze table toward Power BI in the Retail_Tower_analytics repo -- profile
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
- A filled instance: `docs/worked-examples/c086-pharmacy.md` (an example, never
  the universal schema).
