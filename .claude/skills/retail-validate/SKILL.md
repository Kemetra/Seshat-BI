---
name: retail-validate
description: >-
  Run the LIVE data checks against a materialized retail table and interpret the
  findings. Use after silver + gold exist for a mapped table in the
  Seshat BI repo, when someone asks to validate or reconcile a
  table, or when a V-RC2 / V-RC15 / V-RC16 finding appears. Invoke-and-interpret
  only: this skill runs `retail validate` against a live Postgres DB and maps each
  finding id to its fix. It does NOT build models, write SQL, or auto-fix.
---

# retail-validate

`retail check` proves everything provable from committed text. `retail validate`
proves the four things only a running database can show, on the MATERIALIZED rows
(constitution Principle VIII; `src/seshat/validate.py`). This skill runs it and
maps each finding to the one place to fix it -- the live sibling of
`retail-govern`.

## Scope boundary (read first)

Invoke-and-interpret only. This skill runs the live checks and explains findings;
it does NOT write or fix silver/gold SQL, does NOT call pbi-cli, and does NOT
auto-loop. The live run needs a DB and is the user's call; you report and stop.

## Prerequisites

- silver + gold are materialized for the table.
- A reviewed `mappings/<table>/source-map.yaml` exists (the targets are derived
  from it -- table, PK, FK, measures).
- The optional `db` extra is installed (`pip install 'retail[db]'`) and a DSN is
  configured (`DATABASE_URL` or the `ANALYTICS_DB_*` vars in the gitignored
  `.env`). Never commit a real DSN.

## Run it

```
retail validate --source-map mappings/<table>/source-map.yaml
```

The connection is host-agnostic (any Postgres: local / remote / DigitalOcean /
other) and READ-ONLY (the session is opened read-only; the checks only SELECT).
Exit is non-zero iff any check finds a defect.

## Read a finding

Each is a `Finding(rule_id, severity, message, locator)`. Live findings are
`ERROR` (proven defects -- a real PK duplicate, a real orphan, a real penny
mismatch), unlike the static rules' `WARNING` (suspect patterns). Start at the
locator; the id tells you which fix applies.

## Finding id -> meaning -> where to fix

| Finding | Means | Fix at |
|---------|-------|--------|
| `V-RC2`  | PK not unique, or has a NULL, on the materialized silver table (RC2). | Fix the grain or dedup in the silver SQL; re-verify the map's PK on the TRANSFORMED output (landed uniqueness is not enough). |
| `V-RC15` | The date dimension does not span every fact date -- the calendar has gaps (RC15 coverage; the live half of static rule `S7`). | Widen the `generate_series` bounds in the date-dim build to cover min..max fact date. |
| `V-RC16` (orphan) | A fact FK points outside its dimension (RC16; 0 orphans required). | Fix the FK COALESCE to the `-1` unknown member, or fix the dimension load so the key exists. |
| `V-RC16` (reconcile) | A measure total differs between silver and gold (RC16; must reconcile to the penny). | Fix the gold aggregation (a join fan-out or filter is dropping/duplicating rows) until silver and gold totals match exactly. |

`V-RC15` is the live complement of static `S7`: `S7` proves `dim_date` is BUILT
from `generate_series` (the pattern); `V-RC15` proves the calendar SPANS the data
(coverage). Both halves of RC15 must hold.

## Deferred/live-boundary mode (no DSN or no `db` extra)

If no DSN is configured or the `db` extra is absent, `retail validate` does NOT
traceback and does NOT pretend a run happened -- the live boundary is
user-supplied by design (Principle VIII). Without `--source-map` it reports the
surface is built and how to target a table; without a DSN/driver it prints the
enable steps: `pip install 'retail[db]'`, then set `DATABASE_URL` (or
`ANALYTICS_DB_*`) in the gitignored `.env`. Report that state; do not fake a pass.

## What to do after interpreting

Report the failing ids, their locators, and the one fix each needs. Hand silver
fixes to `warehouse/` SQL and gold/star fixes to the gold build; DAX/PBIP issues
go to the `powerbi-analyst` agent. Then STOP -- re-running `retail validate` to
confirm green is the user's next call, not a loop this skill performs.

## See also

- The checks: `src/seshat/validate.py`; target sourcing:
  `src/seshat/validate_targets.py`.
- Principle VIII (static-first, live deferred): `.specify/memory/constitution.md`.
- The static sibling: the `retail-govern` skill.
- The blank the run fills: `templates/reconciliation-report.md`.

## Orchestration

When a table is being driven end-to-end, the `retail-orchestrate` conductor skill
sequences this verb with the others and runs the self-heal loop against the gate
exit code. This skill stays single-purpose: it does its job and STOPS. The loop
(run gate -> classify findings -> auto-fix mechanical / HARD-STOP judgment calls ->
re-run) lives ONLY in `retail-orchestrate`, never here.
