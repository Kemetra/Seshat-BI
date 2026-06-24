# Implementation Plan: data quality control room

**Branch**: `013-data-quality-control-room` | **Date**: 2026-06-24 | **Spec**: `specs/013-data-quality-control-room/spec.md`

**Input**: Feature specification from `specs/013-data-quality-control-room/spec.md`

## Summary

Ship a **read-only, cross-table consolidated view** of data-quality findings and
process blockers, sourced ENTIRELY from existing committed evidence (per-table
`readiness-status.yaml`, `data-issues.md`, `blocking-reasons.md`, plus the recorded
`retail check` WARNs and `retail validate` ERRORs). The deliverable is one agent skill
(`.claude/skills/<control-room-skill>/SKILL.md`) plus one generic roll-up template
(`templates/data-quality-control-room.md`) -- the portfolio-level sibling of the
per-table `readiness-scorecard.md`. The feature adds NO new validator, NO new gate, NO
new Python, and NO new `retail` subcommand: it aggregates evidence and presents it,
with every cell a measured number traceable to a committed source and no fabricated
confidence score (hard rule #9). Technical approach mirrors features 005/006: the
agent is the runtime; the skill is agent-procedure text; the template is the stable
output shape.

## Technical Context

**Language/Version**: None added. Markdown (SKILL.md, template) only; ASCII, UTF-8 no
BOM. The static checker stays Python 3 stdlib-only with `dependencies = []` -- this
feature touches no `src/retail/` code.

**Primary Dependencies**: None added. Reads existing artifacts only. The agent harness
runs the skill; `retail check` (static) and `retail validate` (live, human-triggered)
are existing surfaces whose RECORDED results the view reads -- it invokes neither as a
new check.

**Storage**: Files only. Inputs: per-table `mappings/<table>/` + the per-table
readiness/issues/blockers files. Output: an on-demand consolidated view rendered from
`templates/data-quality-control-room.md`. No DB connection, no writes to inputs.

**Testing**: The existing unit suite must stay green; `retail check` must stay exit 0
at the unchanged rule count (current). Feature acceptance is a measured-cell-match replay:
given >= 2 tables with per-table evidence, every numeric cell in the view equals the
count in its underlying source, ordering is worst-first, and `git status` shows zero
modified per-table files (read-only proven). No new test framework.

**Target Platform**: The Claude Code agent harness on Windows (repo dev platform);
generic across any retail source table. No platform-specific code.

**Project Type**: Single repo, agent-skill + template slice (docs/skills layer), not a
service or app. Same shape as features 005/006.

**Performance Goals**: N/A -- a read-fan-out over a handful of committed files at
one-to-few table volume. No throughput target. (If table volume ever forces
programmatic aggregation, that is the DEFERRED `retail control-room` reporter -- out of
scope here.)

**Constraints**: Read-only (no input mutation, no DB, no SQL). No new validator / gate
(roadmap rule 8, Principle VIII). No fabricated confidence number (hard rule #9). Every
cell traceable to a committed source. Generic, no worked-example specifics (Principle
VII). ASCII + UTF-8 no BOM; repo-relative paths short (Principle IX, Windows MAX_PATH).

**Scale/Scope**: One skill, one template, an `## Orchestration` pointer, and a
multi-table acceptance replay. No code, no migrations, no schema change.

## Constitution Check

*GATE: must pass before and after design. Source: `.specify/memory/constitution.md` v1.6.0.*

| Principle / rule | Gate | This plan |
|------------------|------|-----------|
| I -- Agent-First, Gate-Enforced | the gate exit code is the authority; the agent proposes | PASS -- the view READS recorded gate results; it never claims a pass the gate did not produce, and it adds no competing authority. |
| II -- Depend, Never Fork | no pbi-cli vendoring | PASS -- not touched. |
| III -- Medallion, Gold-Only | no new read surface | PASS -- reads committed text only; no DB, no schema. |
| IV -- Source Mapping Before Silver | mapping gate unchanged | PASS -- the control room reports Mapping-Ready status; it never grants it. |
| V -- Agent Stops at Judgment Calls | blockers/approvals are named-human actions | PASS -- read-only; never clears a blocker, never self-assigns an owner, surfaces conflicts rather than resolving them (FR-006, FR-011). |
| VI -- Defaults Then Deviations | RC defaults unchanged | PASS -- not touched. |
| VII -- C086 Is An Example | generic templates only | PASS -- skill + template are generic; C086 cited as a filled instance, never baked in (FR-002, SC-001). |
| VIII -- Static-First, Live Deferred | NO new validator; live run is the human's call | PASS (load-bearing) -- adds NO rule (count stays 26) and NO validator; shows RECORDED live results and marks stale ones "not run since <date>" rather than running them (FR-003, FR-010, SC-002). |
| IX -- Secrets & Reproducibility | no secrets; UTF-8 no BOM; short paths | PASS -- no DSN, no `.env` read; artifacts ASCII/UTF-8 no BOM; short paths. |
| Roadmap rule 8 (docs/templates first) | automate only after artifacts prove useful | PASS -- ships a template + skill, not a code reporter (the CLI is DEFERRED). |
| Roadmap rule 9 / readiness "No fake confidence" | explicit status + evidence + blockers, never a score | PASS (load-bearing) -- refuses to emit a confidence/health score; measured counts + four statuses only (FR-007, SC-004). |

**Result**: PASS, no violations. Complexity Tracking is empty (nothing to justify).

## Project Structure

### Documentation (this feature)

```text
specs/013-data-quality-control-room/
  spec.md          # the feature spec (done)
  plan.md          # this file
  tasks.md         # the task breakdown (speckit-tasks)
  analysis.md      # cross-artifact analyze findings (speckit-analyze)
```

No `research.md` / `data-model.md` / `quickstart.md` / `contracts/`: there is no new
data model, no API, and no open technical unknown to research -- the inputs are
existing templates and the output is one new template. (Recorded here so their absence
is a decision, not an omission.)

### Source Code (repository root)

```text
.claude/skills/<control-room-skill>/
  SKILL.md                           # NEW: the read-only aggregation verb (agent-procedure text)

templates/
  data-quality-control-room.md       # NEW: the generic consolidated roll-up shape
                                      #      (portfolio sibling of readiness-scorecard.md)

# READ-ONLY INPUTS (existing, unchanged by this feature):
templates/readiness-status.yaml      # current_stage, per-stage status, next_action, blocking_reasons[]
templates/data-issues.md             # per-table data-quality findings (info/warning/error)
templates/blocking-reasons.md        # per-table open blockers (stage, reason, evidence, owner)
templates/readiness-scorecard.md     # per-table human view (this template is its portfolio peer)
mappings/<table>/                    # where a real table's filled evidence lives
src/retail/                          # the static checker -- NOT modified (no new rule)
src/retail/validate.py               # the live surface -- NOT modified (no new check)
```

**Structure Decision**: Single repo, agent-skill + template slice. Two NEW files only
(`SKILL.md` + the template) plus an `## Orchestration` pointer wired into
`retail-orchestrate`. No `src/retail/` change, no migration, no new dependency. This is
the same minimal footprint features 005/006 used and is what keeps SC-002 true (rule
count 26, `dependencies = []`, suite green).

## Design notes (the load-bearing decisions)

1. **Pure skill + one template, no code** (mirrors feature 006's deciding reason). The
   aggregation is a read-fan-out over committed Markdown/YAML + interpreting two
   existing exit codes -- the exact invoke-and-interpret posture `retail-validate` and
   `retail-orchestrate` already use. A `retail control-room` subcommand would be the
   repo's first reporting CLI, would have to parse the per-table files and track the
   readiness schema, and buys ~zero at one-to-few table volume (YAGNI). DEFERRED.

2. **Read-only, aggregates-not-re-derives.** Every column is a JOIN over an existing
   source (spec "Aggregates, never re-derives" table). The skill runs no new check,
   edits no input, opens no DB. This is what keeps Principle VIII and roadmap rule 8
   intact -- the feature's whole value is presentation, not measurement.

3. **No fabricated number.** The output is the four explicit statuses + MEASURED counts
   (WARN count, live-finding count, open-blocker count, penny delta, row count), each
   traceable to a committed source path/line. A health/confidence score is refused
   (FR-007) and DEFERRED to a future scoring-rules doc (readiness-model).

4. **Honest about staleness and gaps.** Recorded gate results are shown with their
   timestamp; a stale live result is marked "not run since <date>" (FR-010), missing
   evidence is "evidence incomplete: <file>" (FR-009), and source conflicts are
   surfaced as findings (FR-011) -- never silently resolved.

5. **Plugs into the conductor, advances nothing.** An `## Orchestration` pointer lets
   `retail-orchestrate` call the control room as a portfolio-level read after
   sequencing a table. The control room reports state; it does not advance a stage
   (consistent with readiness-pipeline "the conductor executes; the readiness status
   records").

## Complexity Tracking

> No Constitution Check violations. No entries.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| -- | -- | -- |
