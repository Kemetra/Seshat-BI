---
name: retail-control-room
description: >-
  Show the consolidated, cross-table data-quality control room for the
  Seshat BI repo -- one worst-first roll-up of every table's stage,
  status, static WARNs, live findings, open blockers, and next action, plus a
  portfolio-wide open-blockers list. Use when someone asks "show the control room",
  "what is broken across all tables", or "which table do I fix next". READ-ONLY and
  invoke-and-present only: it AGGREGATES evidence that already exists (per-table
  readiness-status.yaml / data-issues.md / blocking-reasons.md + recorded retail check
  / retail validate results); it runs NO new validator, edits NO per-table file, clears
  NO blocker, and emits NO fabricated health/confidence score (every cell is a measured
  number traceable to a committed source).
---

# retail-control-room

The per-table scorecard answers "where is THIS table"; the control room answers "where
is the WHOLE portfolio, and which table do I touch next". It is a read-only JOIN over
evidence that already exists per table -- the portfolio-level sibling of
`readiness-scorecard.md`. It introduces no new validator and no new gate (roadmap rule
8; Principle VIII); it aggregates and presents, then STOPS.

## Scope boundary (read first)

- **Aggregates, never re-derives.** The only evidence shown is evidence already
  committed: `retail check` WARNs, `retail validate` ERRORs (V-RC2/V-RC15/V-RC16), and
  the per-table `data-issues.md` / `blocking-reasons.md` / `readiness-status.yaml` rows.
  It runs NO new check.
- **Read-only.** It never edits a per-table artifact, never clears a blocker, never
  writes a `pass`, never runs SQL, never opens a DB connection. Clearing a blocker stays
  a per-table action by its named owner (Principle V).
- **No fake confidence.** Every line carries a MEASURED NUMBER as evidence (a row count,
  an orphan count, a penny delta, an open-blocker count, a finding-id) -- never an
  adjective, never a fabricated health score (roadmap rule #9). A numeric score is
  OPTIONAL and DEFERRED; the control room MUST NOT emit one.
- **Every cell traces to a committed source.** A number with no traceable source path
  (and row/line where applicable) is a defect.
- **Generic.** No worked-example specifics (billing codes, segments, PII column names,
  per-table grain keys). C086 is a filled instance cited as a reference, never baked in.
- ASCII only, UTF-8 no BOM.

## Aggregates, never re-derives (the evidence chain)

Every cell traces back to an existing committed source -- a JOIN, not a measurement:

| Control-room column | Source it aggregates | Severity |
|---------------------|----------------------|----------|
| static WARNs per table | recorded `retail check` exit + WARN lines | `warning` |
| live findings per table | recorded `retail validate` V-RC2/V-RC15/V-RC16 ERRORs | `error` |
| data-quality issues | the table's `data-issues.md` rows | as recorded |
| open blockers | the table's `blocking-reasons.md` "Open blockers" rows | blocking |
| stage + status | the table's `readiness-status.yaml` (`current_stage`, per-stage `status`) | the four statuses |
| next action | the table's `readiness-status.yaml` `next_action` | -- |

If a per-table source is missing, record that table as `not_started` / "no evidence
yet" -- do NOT invent a status or a number. The control room cannot UPGRADE a status; a
`pass` it shows must be backed by the same evidence the per-table file carries.

## Run it -- produce the consolidated view

Render `templates/data-quality-control-room.md` filled from the per-table evidence.

### 1. Per-table roll-up (one row per table, worst-first)
Scan each `mappings/<table>/`. For each table emit a row: table id, source family,
current stage, stage status, count of static WARNs, count of live findings, count of
open blockers, single next action. Every count is a MEASURED number copied from the
source (e.g. open-blocker count = the number of "Open blockers" rows in that table's
`blocking-reasons.md`; never "several"). Sort `blocked` above `warning` above `pass`.

### 2. Portfolio open-blockers list (the action half)
List EVERY open blocker across all tables with {table, stage blocked, concrete reason,
measured evidence, named owner} copied from the source `blocking-reasons.md`, ordered
worst-first: an `error`-level live finding (V-RC2/V-RC15/V-RC16) outranks a `warning`
static WARN (proven defect > suspect pattern). Never self-assign an owner; a blocker
with no owner is shown "UNASSIGNED" and flagged.

### 3. Traceability
For every cell, be able to name the exact committed source path (and row/line). If
asked "where does this number come from", answer with the path -- not a recomputation.

## No fake confidence (the guardrail)

If asked for "a health score per table" or "one confidence number", DECLINE: cite
readiness-model "No fake confidence" and return the four explicit statuses + the
measured counts with their source paths instead. A roll-up is exactly where a tidy
invented score is tempting; it is forbidden.

## Honest-state rules (never invent, never silently re-run)

| Situation | What the control room does |
|-----------|----------------------------|
| Zero tables with evidence | render an empty roll-up + a clear "no tables onboarded yet" note; do not error, do not invent rows |
| A per-table file malformed / partial | show that table "evidence incomplete: `<file>`"; do not guess the missing counts |
| A gate result predates the table's last change | show the recorded result + its timestamp; mark live findings "not run since `<date>`"; do NOT run the live check itself (Principle VIII -- the human's call) |
| Two sources disagree (status `pass` vs an open blocker) | SURFACE the conflict as a finding; do NOT resolve it by picking one (Principle V) |
| A blocker with no named owner | show owner "UNASSIGNED" and flag it; never self-assign |

## Read-only proof

The skill modifies nothing: after a run, `git status` shows zero modified per-table
`mappings/<table>/`, `data-issues.md`, or `blocking-reasons.md` files. It triggers no
state-mutating `retail check` / `retail validate` run of its own.

## See also

- The output shape: `templates/data-quality-control-room.md`; the per-table sibling:
  `templates/readiness-scorecard.md`.
- The aggregated sources: `templates/data-issues.md`, `templates/blocking-reasons.md`,
  `templates/readiness-status.yaml` (top-level `evidence[]` / `blocking_reasons[]`).
- The model + no-fake-confidence rule: `docs/readiness/readiness-model.md`; the stage
  sequence: `docs/readiness/readiness-pipeline.md`.
- The gates it reads (never re-runs as a new check): the `retail-govern` /
  `retail check` static surface, the `retail-validate` / `retail validate` live surface
  (`src/seshat/validate.py`, V-RC2/V-RC15/V-RC16).
- The conductor it plugs into: `.claude/skills/retail-orchestrate/SKILL.md`.
- The roadmap row + hard rules: `docs/roadmap/roadmap.md` (F012, Layer 4; #7/#8/#9);
  Principles V, VII, VIII. A filled worked example lives under
  `docs/worked-examples/`.

## Orchestration

When tables are driven end-to-end, the `retail-orchestrate` conductor may invoke the
control room as the portfolio-level READ after sequencing a table -- to see the whole
board and the next blocker to clear. This skill reads state and reports; it advances no
stage and clears no blocker. The self-heal loop and any per-table fix live in
`retail-orchestrate` / the per-table owner, never here.
