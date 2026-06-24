# Feature Specification: data quality control room -- the consolidated cross-table findings + blockers view

**Feature Branch**: `013-data-quality-control-room` (work on the worktree branch per session convention; located via `.specify/feature.json`)

**Created**: 2026-06-24

**Status**: Draft

**Input**: "Roadmap F012 (Layer 4 Validation & Readiness). Advances readiness stage: all stages (a consolidated view). A consolidated VIEW of data-quality findings + blockers across tables, sourced from the existing gates (retail check WARNs, retail validate ERRORs) and the per-table data-issues.md / blocking-reasons.md templates. It AGGREGATES existing evidence; it does NOT introduce new validators or new gates (scope discipline / YAGNI). Every finding carries a measured number as evidence, never an adjective; no fake confidence/score (hard rule #9). Generic (#7). Maps to the readiness spine roll-up."

## Why this feature exists

The kit already records data-quality findings and process blockers PER TABLE -- in
each table's `data-issues.md`, `blocking-reasons.md`, and `readiness-status.yaml`.
What it lacks is the one-screen answer to "across EVERY table, what is broken, how
badly, and what is the next blocker to clear?" Today a human would open N per-table
files and reconcile them by hand. This feature is that consolidated view: a
**read-only roll-up** that aggregates the evidence already committed per table into a
single cross-table control room.

It maps to the readiness spine's cross-cutting roll-up (`readiness-status.yaml` has
top-level `evidence[]` and `blocking_reasons[]` exactly for this). The control room
is the portfolio-level sibling of the per-table `readiness-scorecard.md`: the
scorecard answers "where is THIS table"; the control room answers "where is the whole
portfolio, and which table do I touch next".

## What this feature is NOT (the scope wall)

This is the load-bearing constraint, stated up front so the spec cannot drift:

- **It introduces NO new validator and NO new gate.** It runs no new check. The only
  evidence it shows is evidence that ALREADY EXISTS: `retail check` WARNs,
  `retail validate` ERRORs, and the per-table `data-issues.md` / `blocking-reasons.md`
  / `readiness-status.yaml` rows. Adding a validator here would violate roadmap rule 8
  (docs/templates first), constitution Principle VIII (static-now / live-deferred; the
  rule set is fixed at 26), and YAGNI. (See "Aggregates, never re-derives".)
- **It is read-only.** It never edits a per-table artifact, never clears a blocker,
  never writes a `pass`, never runs SQL, never opens a DB connection. It reads the
  committed per-table evidence (and optionally an interpreted gate run the human
  already triggered) and presents it. Clearing a blocker remains a per-table action by
  the blocker's named owner (Principle V).
- **No fake confidence, no invented score.** Every line carries a MEASURED NUMBER as
  evidence (a row count, an orphan count, a penny delta, an open-blocker count, a
  finding-id) -- never an adjective ("looks mostly clean") and never a fabricated
  health score. This is hard rule #9 / readiness-model "No fake confidence". A numeric
  score is OPTIONAL and DEFERRED until scoring rules exist; the control room MUST NOT
  emit one.
- **Generic.** No worked-example specifics (no billing codes, segments, PII column
  names, per-table grain keys). C086 is a filled instance cited as a reference, never
  baked in (Principle VII / roadmap rule 7).

## Aggregates, never re-derives (the evidence chain)

Every cell in the control room traces back to an existing committed source. The
control room is a JOIN over these, not a new measurement:

| Control-room column | Existing source it aggregates | Severity it carries |
|---------------------|-------------------------------|---------------------|
| static WARNs per table | `retail check` exit + WARN lines (Principle VIII static surface) | `warning` |
| live findings per table | `retail validate` V-RC2 / V-RC15 / V-RC16 ERRORs (the human-triggered live run) | `error` |
| data-quality issues | the table's `data-issues.md` rows (`info`/`warning`/`error`) | as recorded there |
| open blockers | the table's `blocking-reasons.md` "Open blockers" rows | blocking |
| stage + status | the table's `readiness-status.yaml` (`current_stage`, per-stage `status`) | the four statuses |
| next action | the table's `readiness-status.yaml` `next_action` | -- |

If a per-table source is missing, the control room records that table as
`not_started` / "no evidence yet" -- it does NOT invent a status. A `pass` shown in
the control room MUST be backed by the same evidence the per-table file carries; the
control room cannot upgrade a status.

## Architecture (a pure skill + one generic template; no code, no new CLI)

Consistent with features 005/006: the control room is **agent-procedure text**, the
agent is the runtime. Decision: **a pure skill plus one generic roll-up template; NO
new Python, NO new `retail` subcommand, NO codegen.**

Deciding reason: the aggregation is a read-fan-out over a handful of committed
Markdown/YAML files plus interpreting two existing exit codes -- exactly the kind of
read-and-present work the agent already does, and the same posture
`retail-validate` ("invoke-and-interpret only") and `retail-orchestrate`
("the conductor reads state") already use. A `retail control-room` subcommand would
add the repo's first reporting CLI, parse the per-table files into code, and have to
track the readiness schema -- maintenance for ~zero gain at one-to-few table volume
(YAGNI). The template gives the skill a stable, reviewable output shape; the skill
gives the agent the procedure to fill it from existing evidence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One consolidated view of every table's findings + blockers (Priority: P1)

A human (or the agent) asks "show me the data-quality control room". The skill scans
the per-table evidence (each `mappings/<table>/`'s readiness + issues + blockers, plus
the most recent interpreted gate runs), and produces ONE consolidated view: a row per
table with its current stage, status, a count of static WARNs, a count of live
findings, a count of open blockers, and its single next action -- every count a
measured number, sorted worst-first.

**Why this priority**: this is the feature -- the one-screen cross-table answer the
kit lacks. Without it, the portfolio view does not exist.

**Independent Test**: with two or more tables having per-table evidence (e.g. the
existing `mappings/c086/` plus a second generic fixture table), the skill emits one
consolidated table whose every numeric cell matches the underlying per-table file
(WARN count = the table's `retail check` WARN lines; open-blocker count = rows in its
`blocking-reasons.md`), and whose ordering puts `blocked` tables above `warning` above
`pass`. No per-table file is modified.

**Acceptance Scenarios**:

1. **Given** N tables each with a `readiness-status.yaml` + `data-issues.md` +
   `blocking-reasons.md`, **When** the skill runs, **Then** it emits one roll-up with
   one row per table, each numeric column a count sourced from that table's files, and
   it modifies nothing.
2. **Given** a table whose `blocking-reasons.md` has 3 open rows, **When** the skill
   runs, **Then** that table's "open blockers" cell reads `3` (the measured count) and
   lists the 3 concrete reasons, never an adjective like "several".
3. **Given** a table with no per-table evidence yet, **When** the skill runs, **Then**
   it shows that table as `not_started` / "no evidence yet" and does NOT invent a
   status or a number.

### User Story 2 - The next blocker to clear, portfolio-wide (Priority: P1)

The control room surfaces, across all tables, the prioritized list of OPEN blockers
(from each `blocking-reasons.md`) with the stage each blocks, the measured evidence,
and the named owner who can clear it -- so a human knows the single most valuable next
action across the whole portfolio, not just within one table.

**Why this priority**: a consolidated view of findings without a "what do I fix next,
and who clears it" is just a wall of numbers. This is the action half of the view, and
it is what advances readiness across all stages.

**Independent Test**: given tables with open blockers at different stages, the skill
lists every open blocker with {table, stage blocked, concrete reason, measured
evidence, named owner}, and a `blocked` Gold-Ready live finding (V-RC2/V-RC15/V-RC16)
sorts above a `warning`-level static WARN. The skill never self-assigns an owner and
never marks a blocker cleared.

**Acceptance Scenarios**:

1. **Given** open blockers across tables, **When** the skill runs, **Then** each is
   listed with its stage, concrete reason, measured evidence, and named owner copied
   from the source `blocking-reasons.md` -- nothing invented.
2. **Given** an approval-type blocker (e.g. Mapping Ready not CLEARED, PII not signed
   off), **When** the skill runs, **Then** it shows the blocker and the required owner
   but the skill itself takes no clearing action (Principle V).
3. **Given** a `warning` data issue and an `error` live finding on the same table,
   **When** the view orders blockers, **Then** the `error` outranks the `warning`
   (severity asymmetry: proven defect > suspect pattern).

### User Story 3 - Aggregation honesty: no new check, no fabricated number (Priority: P1)

The control room never runs a new validator, never edits a per-table file, and never
emits a number that is not traceable to a committed source. If asked to "score" table
health, it refuses to fabricate a confidence number and instead shows the explicit
statuses + measured counts (no fake confidence, hard rule #9).

**Why this priority**: this is the constitutional guardrail. A roll-up view is exactly
where an agent is tempted to invent a tidy health score or quietly re-run a check;
both are forbidden and must hard-stop.

**Independent Test**: ask the skill for "one health score per table"; assert it
declines and returns the four explicit statuses + measured counts with their source
paths, citing the no-fake-confidence rule -- and that it issued no `retail check` /
`retail validate` run of its own that mutates state and edited no per-table file.

**Acceptance Scenarios**:

1. **Given** a request for a single numeric health/confidence score, **When** the
   skill runs, **Then** it declines, explains "no fake confidence" (readiness-model),
   and shows statuses + measured counts instead.
2. **Given** any control-room cell, **When** a reviewer asks "where does this number
   come from", **Then** the skill can name the exact committed source path/line it was
   read from (every finding traces to evidence).
3. **Given** the skill runs, **Then** `git status` shows no modification to any
   per-table `mappings/<table>/`, `data-issues.md`, or `blocking-reasons.md` file
   (read-only).

### Edge Cases

- **Zero tables with evidence**: the view renders an empty roll-up with a clear "no
  tables onboarded yet" note -- it does not error and does not invent rows.
- **A per-table file is malformed / partially filled**: the skill records that table
  as "evidence incomplete: <file>" rather than guessing the missing counts.
- **`retail check` / `retail validate` has not been run recently for a table**: the
  control room shows the last recorded result with its timestamp from the per-table
  file and marks live findings "not run since <date>" -- it does NOT silently run the
  live check itself (that is the human's call; Principle VIII).
- **Conflicting evidence** (e.g. `readiness-status.yaml` says `pass` but
  `blocking-reasons.md` has an open row): the skill surfaces the conflict as a finding
  and does NOT resolve it by picking one (surface conflicts, never bury them --
  Principle V posture).
- **A blocker with no named owner**: shown with owner "UNASSIGNED" and flagged -- the
  skill never self-assigns.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add `.claude/skills/<control-room-skill>/SKILL.md` (ASCII, UTF-8 no BOM,
  valid frontmatter). NO new Python, NO new `retail` subcommand, NO codegen.
- **FR-002**: Add ONE generic roll-up template (e.g.
  `templates/data-quality-control-room.md`) -- the consolidated view's stable output
  shape. ASCII, UTF-8 no BOM, placeholders only, no worked-example specifics
  (Principle VII).
- **FR-003**: The skill MUST aggregate ONLY existing committed evidence: per-table
  `readiness-status.yaml` (`current_stage`, per-stage `status`, `next_action`,
  top-level `blocking_reasons[]`), `data-issues.md` rows, `blocking-reasons.md` "Open
  blockers" rows, and the recorded results of `retail check` (WARNs) and
  `retail validate` (V-RC2/V-RC15/V-RC16 ERRORs). It MUST run NO new validator and add
  NO new gate.
- **FR-004**: The consolidated view MUST contain one row per table with, at minimum:
  table id, source family, current stage, stage status, count of static WARNs, count
  of live findings, count of open blockers, and the single next action. Every count
  MUST be a measured number traceable to its source (no adjectives).
- **FR-005**: The view MUST include a portfolio-wide OPEN-BLOCKERS list: each open
  blocker with {table, stage blocked, concrete reason, measured evidence, named
  owner}, ordered worst-first (`error`/`blocked` above `warning`).
- **FR-006**: The skill MUST be READ-ONLY: it MUST NOT edit any per-table artifact,
  MUST NOT clear or self-assign a blocker, MUST NOT write a `pass`, MUST NOT open a DB
  connection, MUST NOT run SQL. Clearing a blocker stays a per-table action by its
  named owner (Principle V).
- **FR-007**: No-fake-confidence guard: the skill MUST refuse to emit a numeric
  health/confidence score. If asked, it declines, cites readiness-model "No fake
  confidence", and returns the four explicit statuses + measured counts. Any future
  optional score is DEFERRED and out of scope here.
- **FR-008**: Evidence traceability: every cell in the view MUST be attributable to a
  named committed source (path, and where applicable the row/line). A number with no
  traceable source is a defect.
- **FR-009**: Missing/partial evidence handling: a table with no (or malformed)
  per-table evidence MUST be shown as `not_started` / "evidence incomplete: <file>" --
  never with an invented status or count.
- **FR-010**: Staleness honesty: when the recorded gate result predates the table's
  last change, the view MUST show the recorded result + its timestamp and mark live
  findings "not run since <date>" rather than running the live check itself
  (Principle VIII; the live run is the human's call).
- **FR-011**: Conflict surfacing: when two per-table sources disagree (e.g. status
  `pass` vs an open blocker), the skill MUST surface the conflict as a finding and MUST
  NOT silently resolve it (Principle V posture).
- **FR-012**: Append an `## Orchestration` pointer so `retail-orchestrate` can invoke
  the control room as the portfolio-level read after sequencing a table; the control
  room reads state and reports, it does not advance any stage.

### Key Entities

- **Control-room skill** (`<control-room-skill>`): the read-only aggregation verb; the
  agent is the runtime. Invoke-and-present only.
- **Roll-up template** (`templates/data-quality-control-room.md`): the generic,
  copy-me consolidated output shape -- the portfolio sibling of the per-table
  `readiness-scorecard.md`.
- **Aggregated per-table sources (existing, unchanged)**: `readiness-status.yaml`,
  `data-issues.md`, `blocking-reasons.md` per table; plus the recorded
  `retail check` / `retail validate` results. These are INPUTS; the feature creates no
  new per-table artifact.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `.claude/skills/<control-room-skill>/SKILL.md` and
  `templates/data-quality-control-room.md` exist, ASCII + no BOM, frontmatter valid,
  skill registered by the harness; both generic (no worked-example specifics).
- **SC-002**: `retail check` stays exit 0 at the unchanged rule count (26) with the new
  skill + template; the full unit suite stays green; NO new Python; `dependencies = []`
  unchanged. (The feature adds NO rule and NO validator -- verified by the rule count
  and dependency set being unchanged.)
- **SC-003**: Given two or more tables with per-table evidence, the skill produces one
  consolidated view in which EVERY numeric cell equals the count in the underlying
  per-table source (WARN count, live-finding count, open-blocker count), ordering is
  worst-first, and `git status` shows zero modified per-table files (read-only proven).
- **SC-004**: A request for a single health/confidence score is DECLINED with the
  no-fake-confidence rationale, and every shown number is traceable to a named
  committed source path -- demonstrating aggregation-not-fabrication.

## Assumptions

- Pure skill + one generic template; the agent is the runtime (same posture as
  features 005/006). No new Python, no `retail control-room` CLI, no codegen (YAGNI).
- The per-table evidence files already exist as templates
  (`templates/{readiness-status.yaml,data-issues.md,blocking-reasons.md,readiness-scorecard.md}`)
  and are the authoritative inputs; this feature consumes them, never redefines them.
- The control room reports the LAST RECORDED gate results; it does not trigger a live
  `retail validate` run (that needs creds + the `db` extra and is the human's call,
  Principle VIII).
- A second generic fixture table (or the existing `mappings/c086/` plus a minimal
  generic stub) is available so the multi-table aggregation has an input to test; the
  acceptance test is a measured-cell match against the underlying files.
- "Advances readiness stage: all stages" means the view is cross-stage (it rolls up
  every stage's findings); it does not itself gate or advance any single stage.

## Deferred decisions (future specs / issues -- recorded, not built)

- **A machine-readable roll-up + numeric scoring** (e.g. a `control-room.yaml` and a
  defined health score): DEFERRED until scoring rules are defined in a readiness
  scoring-rules doc (readiness-model "score is OPTIONAL and DEFERRED"). Until then the
  view is human-readable statuses + measured counts only.
- **A `retail control-room` CLI / programmatic aggregator**: DEFERRED. If table volume
  grows past hand-aggregation, a read-only reporter (still no new validator) could
  parse the per-table files; a code surface change for a later slice.
- **A historical trend view** (findings/blockers over time): DEFERRED to feature 015
  (Reconciliation Ledger) which owns durable cross-time state; the control room is a
  point-in-time roll-up, not a ledger.
- **Auto-refresh / scheduled regeneration**: DEFERRED; the view is generated on demand
  by the agent. No cron, no runtime.

## See also

- The cross-cutting roll-up fields this maps to: `templates/readiness-status.yaml`
  (top-level `evidence[]` / `blocking_reasons[]`); the per-table sibling:
  `templates/readiness-scorecard.md`.
- The aggregated sources: `templates/data-issues.md`, `templates/blocking-reasons.md`.
- The model + no-fake-confidence rule: `docs/readiness/readiness-model.md`;
  the stage sequence: `docs/readiness/readiness-pipeline.md`.
- The gates it reads (never re-runs as a new check): the `retail-govern` /
  `retail check` static surface and the `retail-validate` / `retail validate` live
  surface (`src/retail/validate.py`, V-RC2/V-RC15/V-RC16).
- The conductor it plugs into: `.claude/skills/retail-orchestrate/SKILL.md`;
  `specs/005-layer-d-orchestration/spec.md`.
- The roadmap row: `docs/roadmap/roadmap.md` (F012, Layer 4, advances all stages);
  hard rules 7, 8, 9. Constitution Principles V, VII, VIII.
