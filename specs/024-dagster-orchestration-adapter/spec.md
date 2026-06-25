# Feature Specification: Dagster Orchestration Adapter -- the unattended/CI runtime that RUNS approved steps but DECIDES no stage

**Feature Branch**: `024-dagster-orchestration-adapter`  **Roadmap feature**: F030

> Numbering note (spec-dir vs roadmap F-number). The roadmap F-number is the
> authoritative identity. The spec-directory number is the next free on-disk slot.
> This batch: F024=spec 018, F025=019, F026=020, F027=021, F028=022, F029=023,
> F030=024, F031=025, F032=026, F033=027. When the directory number and the
> F-number disagree, the roadmap F-number wins. This feature is roadmap F030,
> authored on disk as spec 024.

**Created**: 2026-06-25   **Status**: Planned (spec only -- no runtime code this slice)

**Input**: "Define how Dagster enters later as an ORCHESTRATION ADAPTER. Dagster RUNS approved
steps; Tower BI decides whether the result passes. Dagster MAY orchestrate: load bronze, profile
source, run dbt or SQL migrations, run retail check, run retail validate, run semantic check,
generate handoff pack, write run evidence. Dagster MUST NOT: approve mapping, approve metrics,
change readiness to pass without evidence/approval, publish Power BI without publish_ready pass,
resolve business ambiguity, bypass the source-map gate. This slice is planning artifacts ONLY: no
Dagster files are created. Generic (Principle VII). No fake confidence (Principle IX)."

## Why this feature exists

The kit already has a conductor that sequences the medallion stages: `retail-orchestrate`
(F005), the agent-conversational Layer-D verb. That conductor is interactive -- a human
is in the loop, the agent reads readiness state, runs the gate, and HARD-STOPS at the two
human seams (mapping approval, Principle-V judgment calls). What the kit lacks is the
**unattended/CI sibling**: a way to run the SAME approved sequence on a schedule or in a
pipeline -- load bronze, profile, build silver/gold, run `retail check` / `retail validate`,
run the semantic check, generate the handoff pack -- without a human re-typing each step,
while still respecting every gate and every human seam the conductor respects.

This feature defines that sibling as an **orchestration adapter**: Dagster. The adapter's
single job is to RUN steps that have already been approved and to RECORD what happened.
It is the execution-side counterpart of the conductor, governed by exactly the same
authority boundary: the gate exit code and the named human are the truth; the orchestrator
proposes and runs, it never decides. Dagster sequences all seven readiness stages but
DECIDES none of them.

This slice writes the SPEC for that adapter (the five Spec-Kit planning files). It creates
NO Dagster files. The asset graph, the project layout, and the run-evidence template below
are ENUMERATED as future outputs a later implementation slice will author -- they are the
shape this spec commits to, not code this spec ships.

## What this feature is NOT (the scope wall)

This is the load-bearing constraint, stated up front so the spec cannot drift:

- **It creates NO Dagster code this slice.** `definitions.py`, `pyproject.toml`, the
  `assets/` / `jobs/` / `sensors/` / `schedules/` packages, the adapter doc, the ADR, the
  run-evidence template, and the adapter skill are FUTURE outputs ENUMERATED in this spec
  (see Allowed operations / the plan's "artifacts this feature PLANS"). This slice writes
  five planning files and nothing else (Principle VIII; roadmap rule #8: docs/planning
  first, automate only after the artifact proves useful).
- **Dagster DECIDES no readiness stage.** It sequences Source -> Mapping -> Silver -> Gold
  -> Semantic Model -> Dashboard -> Publish, but the authority that a stage is `pass` is
  the gate exit code (mechanical stages) or a named human approval (judgment-call stages),
  recorded in Core Authority's `readiness-status.yaml`. Dagster never writes that pass.
- **It does NOT define or own truth.** Dagster does not define a metric, a mapping, a
  grain, a business rollup, a segment, or a PII publish decision. Those are owned by the
  upstream governed artifacts (the source-mapping gate, F009 metric contracts, F010/F011),
  never by the orchestrator (Core Authority rule binding all features).
- **It does NOT bypass the source-map gate (Principle IV).** No silver asset materializes
  until the table's mapping is CLEARED in the committed gate artifacts. Dagster READS that
  approval; it never self-grants it.
- **It does NOT publish Power BI.** Even when `publish_ready` is `pass`, Dagster only
  TRIGGERS the F016 Power BI Execution Adapter (parked, execution-only); Dagster itself
  opens no Power BI connection and runs no publish.
- **No fake confidence.** Run evidence carries explicit `status` + measured numbers +
  `blocking_reasons[]`, never a fabricated health/confidence score (Principle IX, hard
  rule #9). A numeric score is OPTIONAL and DEFERRED until scoring rules exist.

## The derived-evidence vs authored-truth boundary (the line this feature lives or dies on)

The single biggest design risk is conflating "Dagster writes evidence back" with "Dagster
authors truth." They are different writes and this spec keeps them apart explicitly:

- **DERIVED RUN-EVIDENCE (allowed).** When Dagster runs a step, it records WHAT HAPPENED:
  "ran `retail check` on commit `<sha>`, exit 0, 0 violations, <timestamp>"; "ran
  `retail validate`, exit 0, PK unique, 0 orphan FKs, penny-exact reconcile"; "generated
  handoff pack at `<path>`". This is a `dagster-run-evidence.md` record -- a measured,
  timestamped, reproducible log of an execution. Writing this is the same category as the
  reconciliation-report being FILLED by a live run: it is evidence ABOUT a step, not a
  ruling.
- **AUTHORED TRUTH (forbidden).** Flipping a readiness stage to `pass`, writing an
  approval, marking `Gate status: CLEARED`, defining what a metric means, choosing a grain
  or a PII disposition -- these are RULINGS. Dagster MUST NOT write any of them.
- **How the two reconcile (the sentence the reviewer is looking for).** For mechanical
  stages (Silver Ready, Gold Ready) Dagster writes the CHECK evidence (the `retail check` /
  `retail validate` exit + numbers); whether that evidence MARKS the stage `pass` is Core
  Authority's record, written by Core Authority's process, not by Dagster's asset. For
  human-approval stages (Mapping Ready, Semantic Model publish-safety, Publish Ready)
  Dagster READS the committed approval (the `Gate status: CLEARED` field, the `approvals[]`
  owner+date in `readiness-status.yaml`) and HALTS if it is absent -- it never writes the
  approval and never writes a `pass` that depends on one. Dagster proposes and runs; the
  gate exit code and the named human dispose (Principle I, Principle V).

This is exactly the posture `retail-orchestrate` already takes ("you may READ `Gate status`;
you may not write `CLEARED` yourself"). Dagster is the unattended runtime of that same
contract.

## Relationship to shipped features (scope delta)

- **F005 Retail Readiness Model + `retail-orchestrate` conductor (the reconciliation that
  MUST be explicit).** `retail-orchestrate` is the agent-conversational/interactive
  conductor: a human is present, the agent sequences the verb-skills in-context, self-heals
  against the gate, and stops to ask. Dagster is the **unattended/CI sibling**: the SAME
  medallion sequence, the SAME gate-exit authority, the SAME two human seams (mapping gate,
  Principle V), but driven by a scheduler/pipeline instead of a conversation. Two runtimes,
  one sequence, one authority. Neither self-approves. Where the conductor says "I will pause
  and ask," Dagster says "I will halt this asset and surface the open blocker." This spec
  states that relationship and does not duplicate the sequence -- it cites
  `specs/005-layer-d-orchestration/spec.md` as the source of the sequence.
- **F029 dbt Transformation Adapter (spec 023, a dependency).** Where dbt is adopted, the
  silver/gold build steps Dagster orchestrates ARE dbt assets, run via `dagster-dbt`. F029
  owns HOW the transformations are defined and validated; F030 owns the SEQUENCING and
  gate-respecting execution of them. F030 cites F029 by role; it does not redefine dbt's
  internals.
- **F024 Companion-Tools Architecture (spec 018, the category parent, a dependency).** F024
  defines the companion-tool categories (Execution Adapter / Maintenance / Read-only
  surface). Dagster is an **Execution Adapter / Maintenance mix**: it is execution-capable
  (it runs steps), DB-connected (it loads bronze, runs migrations/validate), and it can
  TRIGGER the publish-capable F016 -- but only after `publish_ready` is `pass`. F030 cites
  F024 for the category contract; it does not redefine the categories.
- **F016 Power BI Execution Adapter (parked, execution-only, last).** Dagster's terminal
  publish asset TRIGGERS F016 once `publish_ready` is `pass`; Dagster never publishes
  itself. F016 remains the only feature allowed to materialize/publish a Power BI model.
- **Sibling policy features it references (not dependencies).** The auto-update posture
  (pin dagster + dagster-dbt together, PRs only, definitions-load smoke, no automerge on
  majors) is the cross-adapter maintenance policy owned by F031 (spec 025,
  adapter-maintenance-policy) and the release-maturity policy F033 (spec 027). F030 states
  its adapter-specific update needs and DEFERS the shared policy to those siblings.

## Architecture (planning posture: a planned project shape + an adapter skill; no code this slice)

Consistent with the kit's posture (the agent is the primary surface; adapters are bottom of
the stack, Principle II): when this adapter is built, it ships as a **separate, dependable,
upgradeable Dagster project** -- `orchestration/dagster/` with a `src/tower_bi_orchestration/`
package -- consumed as an external dependency, never forked. The agent-side companion is a
skill (`.claude/skills/dagster-orchestration-adapter/`) that explains when and how to invoke
the adapter and where the human seams are. This slice ENUMERATES that shape (see the plan's
"artifacts this feature PLANS"); it creates none of it.

The suggested asset graph (described by gate SEMANTICS, not just names; full edge semantics
in FR-002 / the plan):

```text
raw_source_file
  -> bronze_<table>              (load bronze; DB write of raw landing)
  -> source_profile              (profile the source; writes profile evidence)
  -> source_map                  [HUMAN SEAM: reads Gate status; HALTS if not CLEARED]
  -> silver_tables               [STOP edge: blocked until source_map gate CLEARED]
  -> gold_tables                 (Kimball star; mechanical -- writes check evidence)
  -> metric_contracts            [reads approved contracts; does not author them]
  -> semantic_model              [HUMAN SEAM: reads semantic-model approval]
  -> dashboard_blueprint         (design evidence; gated on semantic_model_ready)
  -> handoff_pack                (generate the BI handoff bundle; writes evidence)
  -> publish_execution_evidence  [gated on publish_ready = pass; TRIGGERS F016 only]
```

Edges marked `[STOP edge]` halt all downstream assets on a failed gate. Edges marked
`[HUMAN SEAM]` read a committed human approval and halt if it is absent -- they never write
it. The terminal asset TRIGGERS the parked F016 adapter; Dagster never publishes itself.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A failed validation STOPS every downstream asset (Priority: P1)

The orchestrator runs the sequence unattended. When a gate asset fails -- e.g. the
`retail validate` step over `gold_tables` returns a non-zero exit (a PK duplicate, an orphan
FK, a reconciliation penny-mismatch) -- that asset is marked failed and EVERY downstream
asset (`metric_contracts`, `semantic_model`, `dashboard_blueprint`, `handoff_pack`,
`publish_execution_evidence`) does NOT materialize. The run records the failure as evidence
with the measured numbers; it advances no stage.

**Why this priority**: this is the core safety property of an unattended runtime. Without it,
a scheduler would happily build a dashboard and a publish on top of a broken gold star. Fail-
closed, propagated downstream, is the MVP.

**Independent Test**: with a fixture where the gold validate asset is forced to a non-zero
exit, confirm (a) the validate asset is failed, (b) no downstream asset materializes, (c) the
run evidence records the failing exit + the measured finding numbers, and (d) no
`readiness-status.yaml` stage was flipped to `pass`.

**Acceptance Scenarios**:

1. **Given** a `retail validate` asset that returns non-zero, **When** the run executes,
   **Then** that asset is failed and all downstream assets are skipped (not materialized),
   never run around.
2. **Given** the failed run, **When** its evidence is written, **Then** the record carries
   the non-zero exit and the measured finding (e.g. "3 orphan FKs", "reconcile delta 0.07"),
   not an adjective and not a score.
3. **Given** the failure, **When** the run completes, **Then** no readiness stage moved to
   `pass` and no approval was written (fail-closed; no authored truth).

### User Story 2 - An approval-gate asset reads committed approval; absent -> it blocks (Priority: P1)

The `source_map` asset (and every other human-seam asset) does not run the downstream build
until the committed human approval exists. It READS the gate state from disk -- `Gate status:
CLEARED` with zero open rows in `mappings/<table>/unresolved-questions.md`, and the
`approvals[]` owner+date in `readiness-status.yaml`. If the approval is absent, the asset
blocks the silver build and surfaces the open blocker; it NEVER self-grants the approval.

**Why this priority**: this is the human seam (Principle IV / Principle V) enforced by the
unattended runtime. An orchestrator that could approve its own mapping would let a scheduler
write ungoverned grain/PII/rollup decisions into silver -- the exact failure the kit exists to
prevent.

**Independent Test**: with a table whose `Gate status` is OPEN, confirm the `silver_tables`
asset does not materialize, the run surfaces the open mapping blocker with its named owner,
and nothing wrote `CLEARED` or an approval. With `Gate status: CLEARED`, confirm the silver
asset is permitted to run.

**Acceptance Scenarios**:

1. **Given** `Gate status: OPEN` (or any open unresolved row), **When** the run reaches the
   `silver_tables` asset, **Then** it blocks, reports the open blocker + named owner, and
   writes no approval.
2. **Given** `Gate status: CLEARED` with zero open rows, **When** the run reaches the
   `silver_tables` asset, **Then** it is permitted to run (the read of committed approval is
   the only GO signal; Dagster does not invent a parallel marker).
3. **Given** any human-seam asset (mapping, semantic-model publish-safety, publish), **When**
   its approval is absent, **Then** the asset HALTS and the orchestrator self-grants nothing
   (Principle V).

### User Story 3 - A completed run writes run-evidence and flips no stage status (Priority: P1)

When a run completes (whether all-green or partially blocked), Dagster writes a
`dagster-run-evidence.md` record: which assets ran, each step's gate command + exit code +
measured numbers, timestamps, the commit sha, and which assets were blocked/skipped and why.
This record is DERIVED EVIDENCE. The run flips NO readiness stage to `pass`; it advances no
approval; it changes no `Gate status`.

**Why this priority**: the run-evidence record is what makes an unattended run auditable and
is the artifact a human (or the Control Room, F012) reads to see what the scheduler did --
without it, an unattended runtime is opaque. Equally, this is where an orchestrator is most
tempted to "tidy up" by writing a `pass`; the story exists to forbid exactly that.

**Independent Test**: run a green sequence; confirm a `dagster-run-evidence.md` is written
with per-asset exit codes + measured numbers + timestamps, AND that `git diff` shows zero
changes to any `readiness-status.yaml` stage `status`, any `Gate status` field, or any
`approvals[]` entry (evidence written; truth untouched).

**Acceptance Scenarios**:

1. **Given** a completed run, **When** evidence is written, **Then** it records per-asset
   gate command, exit code, measured numbers, timestamp, and commit sha -- a reproducible
   log, no score.
2. **Given** a completed run, **When** its writes are inspected, **Then** no readiness stage
   `status` was changed, no `Gate status` was written, and no approval was added.
3. **Given** a partially blocked run, **When** evidence is written, **Then** each
   blocked/skipped asset is recorded with the concrete `blocking_reason` and the named owner
   who can clear it.

### User Story 4 - No self-approval: Dagster proposes and runs; the gate and Core Authority dispose (Priority: P1)

Across the whole sequence the orchestrator never becomes the authority on whether a step
passed. A mechanical stage advances only on a literal gate exit 0 recorded by Core Authority;
a human-seam stage advances only on a named human approval. Dagster's own asset success means
"the command ran and returned this exit" -- not "the stage is now `pass`."

**Why this priority**: this is the constitutional guardrail binding all features. An
unattended runtime that conflated "my asset succeeded" with "the stage passed" would silently
become Core Authority -- the single thing every feature in the kit forbids.

**Independent Test**: assert that no asset in the planned graph has the capability to write a
`readiness-status.yaml` stage `pass`, a `Gate status: CLEARED`, an `approvals[]` entry, a
metric definition, a mapping, or a Power BI publish; and that the spec's Forbidden operations
enumerate each of these.

**Acceptance Scenarios**:

1. **Given** a green `retail check` asset, **When** it succeeds, **Then** the orchestrator
   records the exit-0 evidence but does NOT write the stage `pass` -- Core Authority's process
   records the stage status from the evidence.
2. **Given** any judgment call surfaced during a run (grain ambiguity, PII publish-safety, a
   business rollup, sentinel-vs-null), **When** the orchestrator encounters it, **Then** it
   HALTS the affected asset and escalates -- it never decides to make a finding go away
   (Principle V).
3. **Given** `publish_ready = pass`, **When** the publish asset runs, **Then** it TRIGGERS the
   F016 execution adapter and Dagster itself opens no Power BI connection and publishes
   nothing.

### Edge Cases

- **Source-map gate OPEN at run time**: the silver asset blocks; the run records the open
  mapping blocker; nothing is approved (US2).
- **A judgment call appears mid-run** (grain/PII/rollup/sentinel): the affected asset HALTS
  and escalates to the named owner; the orchestrator does not auto-resolve it (Principle V).
- **`retail validate` cannot connect** (no creds / DB down): the validate asset reports a
  deferred-boundary result with its timestamp; it does NOT fabricate a pass and does NOT mark
  Gold Ready (Principle VIII -- the live run is gated on creds).
- **`publish_ready` not `pass`**: the publish asset does not run and does not trigger F016;
  it records the missing publish approval as a blocker.
- **A downstream asset is requested directly** (e.g. someone targets `dashboard_blueprint`
  while gold is broken): the upstream STOP edge still blocks it; the dependency cannot be
  run around.
- **Dagster + dagster-dbt version skew**: a definitions-load smoke test fails closed in CI;
  the pinned-together pair (FR-009) prevents a silent partial upgrade.
- **Run evidence write conflicts with a human edit**: evidence is append/record-only and
  never overwrites a human-authored gate field; a conflict surfaces, it is not resolved by
  the orchestrator.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: This slice MUST produce ONLY the five Spec-Kit planning files for this feature
  (spec, plan, tasks, two checklists). It MUST create NO Dagster file, NO `pyproject.toml`,
  NO `definitions.py`, NO asset/job/sensor/schedule module, NO adapter doc, NO ADR, NO
  run-evidence template, and NO adapter skill. Those are FUTURE outputs enumerated here
  (Principle VIII; roadmap rule #8).
- **FR-002**: The spec MUST define the asset graph with gate SEMANTICS, not just names: for
  each edge, whether it is a STOP edge (a failed gate halts all downstream assets) or a HUMAN
  SEAM edge (reads a committed approval and halts if absent). The terminal
  `publish_execution_evidence` asset MUST be gated on `publish_ready = pass` and MUST only
  TRIGGER the F016 adapter -- never publish itself.
- **FR-003**: Dagster MUST be allowed to RUN (orchestrate) exactly these steps: load bronze,
  profile source, run dbt or SQL migrations (silver/gold), run `retail check`, run
  `retail validate`, run the semantic check, generate the handoff pack, and write run
  evidence. The list of allowed runnable steps MUST be explicit and closed.
- **FR-004**: Dagster MUST NOT: approve a mapping, approve a metric contract, define a metric
  / mapping / grain / rollup / segment / PII disposition, change a readiness stage to `pass`
  without the required evidence + named approval, write a `Gate status: CLEARED`, publish a
  Power BI model, publish Power BI without `publish_ready = pass`, resolve a business
  ambiguity, or bypass the source-map gate. The Forbidden operations section MUST enumerate
  each.
- **FR-005**: A failed gate asset MUST fail closed and MUST halt all downstream assets (US1);
  no downstream asset may be run around. Fail-closed propagation is a hard property of the
  graph, not a convention.
- **FR-006**: Every human-seam asset MUST READ the committed approval (the `Gate status`
  field, the `approvals[]` owner+date in `readiness-status.yaml`) as its only GO signal and
  MUST HALT if absent. It MUST NOT write the approval and MUST NOT invent a parallel
  approval marker (US2; same posture as `retail-orchestrate`).
- **FR-007**: Run evidence MUST be DERIVED EVIDENCE only: per-asset gate command, exit code,
  measured numbers, timestamp, commit sha, and the concrete `blocking_reason` + named owner
  for any blocked/skipped asset. It MUST NOT contain a numeric health/confidence score
  (Principle IX) and MUST NOT write any readiness `status`, `Gate status`, or approval (US3).
- **FR-008**: The spec MUST reconcile with F005: state that `retail-orchestrate` is the
  agent-conversational conductor and Dagster is the unattended/CI sibling -- same sequence,
  same gate-exit authority, same two human seams, neither self-approving. It MUST cite the
  F005 sequence rather than redefine it.
- **FR-009**: The spec MUST state the auto-update posture for the planned project: pin
  `dagster` and `dagster-dbt` TOGETHER (no independent bumps), updates via PR only, a
  definitions-load smoke test as the minimum CI gate, a small orchestration smoke test once
  an implementation exists, and NO automerge for Dagster MAJOR versions. It MUST DEFER the
  shared cross-adapter policy to F031 (spec 025) / F033 (spec 027).
- **FR-010**: All artifacts MUST be GENERIC (Principle VII): `<table>`, `<source>`,
  `<MetricName>` placeholders; the C086 / retail_store_sales worked examples may be CITED as
  references but their specifics (billing codes, segments, PII columns, grain keys) MUST NOT
  be baked in.
- **FR-011**: All five files MUST be ASCII only, UTF-8 without BOM, using `->` for arrows and
  `--` for dashes (Principle IX; Windows charmap). No box-drawing, smart quotes, or em-dashes.
- **FR-012**: The spec MUST state that the readiness stage affected is ALL stages (Dagster
  sequences them) but that Dagster DECIDES none -- the gate exit code and the named human are
  the authority for every stage's `pass`.

### Key Entities

- **Orchestration adapter (Dagster)**: the unattended/CI runtime that RUNS approved steps and
  records run-evidence. Execution-capable, DB-connected, can TRIGGER the publish-capable F016
  only after `publish_ready` is `pass`. Decides no stage.
- **Asset**: one orchestrated step (load bronze, profile, build, check, validate, semantic
  check, handoff, publish-trigger). Carries a gate command and an exit; its success means "the
  command ran and returned this exit," not "the stage passed."
- **STOP edge**: a graph dependency where a failed upstream gate halts all downstream assets
  (fail-closed propagation).
- **Human-seam asset**: an asset that reads a committed human approval as its GO signal and
  halts if absent; it never writes the approval.
- **Run-evidence record** (`dagster-run-evidence.md`): the derived, measured, timestamped log
  of a run -- per-asset gate command + exit + numbers + blocked reasons. No score; no authored
  truth.
- **Core Authority (unchanged)**: the owner of truth -- `readiness-status.yaml`, the gate exit
  codes, the named human approvals. Dagster reads it and writes derived evidence about runs; it
  never writes truth into it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Exactly five planning files exist for this feature (spec, plan, tasks,
  checklists/acceptance, checklists/governance); ZERO Dagster files, ZERO `pyproject.toml`,
  ZERO module/doc/ADR/template/skill are created by this slice (FR-001).
- **SC-002**: A reader of the spec can list, unambiguously, the closed set of steps Dagster
  MAY run (FR-003) and the enumerated set it MUST NOT do (FR-004), with no overlap and no
  ambiguity about which is which.
- **SC-003**: The asset graph is specified with per-edge gate semantics: every edge is
  classifiable as a STOP edge or a HUMAN-SEAM edge, and the terminal publish asset is shown
  gated on `publish_ready = pass` triggering F016 only (FR-002).
- **SC-004**: The four named acceptances are each a load-bearing User Story with Given/When/
  Then scenarios: (1) failed validation stops downstream; (2) approval-gate reads committed
  approval, absent -> blocks; (3) completed run writes evidence, flips no stage; (4) no
  self-approval (FR-005..FR-007, US1-US4).
- **SC-005**: The derived-evidence vs authored-truth boundary is resolved in its own
  subsection AND reflected in Allowed/Forbidden operations -- a reviewer can state the one
  sentence that reconciles "writes evidence back" with "never self-approves" (the boundary
  subsection + FR-006/FR-007).
- **SC-006**: The F005 reconciliation is explicit: a reader can state that `retail-orchestrate`
  is the conversational conductor and Dagster is the unattended/CI sibling, same sequence and
  same authority, neither self-approving (FR-008, SC text).
- **SC-007**: 100% generic and ASCII: a reader finds ZERO worked-example specifics baked in
  and ZERO non-ASCII characters in any of the five files (FR-010, FR-011).

## Human approval boundary

Dagster never holds approval authority. Every approval is a named human action recorded in
Core Authority:

- **Mapping Ready** -- the reviewer sets `Gate status: CLEARED` after the source-mapping
  review. Dagster reads it; the silver asset is blocked until it is present.
- **Semantic Model Ready (publish-safety / metric approval)** -- the metric owner / governance
  approves; Dagster reads the approval and never grants it.
- **Publish Ready** -- the named approver signs off the handoff pack; only then may the publish
  asset trigger F016.
- **Any Principle-V judgment call** (grain, PII, rollup, segment, sentinel-vs-null) -- the
  named owner decides; Dagster halts and escalates.

The agent recommends and Dagster runs; the named human (and the gate exit code) decides.

## Allowed operations

- Sequence all seven readiness stages in the planned asset graph (decide none).
- RUN: load bronze, profile source, run dbt or SQL migrations (silver/gold), run
  `retail check`, run `retail validate`, run the semantic check, generate the handoff pack.
- WRITE DERIVED run-evidence (`dagster-run-evidence.md`): per-asset gate command, exit code,
  measured numbers, timestamps, commit sha, blocked/skipped reasons + named owners.
- READ committed approvals and readiness state as the GO signal for human-seam assets.
- TRIGGER the F016 Power BI Execution Adapter -- and ONLY when `publish_ready` is `pass`.
- Halt a failed gate asset and propagate the stop to all downstream assets (fail-closed).
- Escalate any judgment call to the named owner.

## Forbidden operations

- Approve a mapping; write `Gate status: CLEARED`; invent a parallel approval marker.
- Approve or define a metric contract; define a metric, mapping, grain, rollup, segment, or
  PII disposition.
- Change a readiness stage to `pass` without the required evidence + named approval; write any
  readiness `status`.
- Resolve a business ambiguity or any Principle-V judgment call.
- Bypass the source-map gate; materialize a silver asset before the mapping is CLEARED.
- Publish a Power BI model; open a Power BI connection; publish Power BI without
  `publish_ready = pass` (Dagster may only TRIGGER F016).
- Emit a numeric health/confidence score in run evidence (Principle IX).
- Run a gate around a failed upstream gate (no run-around of a STOP edge).
- Create any Dagster file in this planning slice (FR-001).

## Evidence required

- For a green run: a `dagster-run-evidence.md` record with each asset's gate command, exit 0,
  measured numbers (row counts, 0 orphan FKs, penny-exact reconcile), timestamp, commit sha.
- For a blocked run: the same record plus, for each blocked/skipped asset, the concrete
  `blocking_reason` and the named owner who can clear it.
- For a human-seam halt: the committed approval that was read (or recorded as absent), with
  the file + field it was read from.
- For a triggered publish: the `publish_ready = pass` evidence that authorized the trigger and
  the F016 hand-off record (F016 owns the publish evidence itself).

## Readiness stage affected

ALL stages -- Dagster sequences Source -> Mapping -> Silver -> Gold -> Semantic Model ->
Dashboard -> Publish. It DECIDES none: the gate exit code (mechanical stages) and the named
human approval (judgment-call stages) are the authority for every stage's `pass`. Dagster
advances no stage by its own write.

## Dependencies

- **Upstream**: F024 Companion-Tools Architecture (spec 018) -- the category contract (Dagster
  = Execution Adapter / Maintenance mix). F029 dbt Transformation Adapter (spec 023) -- the
  silver/gold transformations Dagster orchestrates via `dagster-dbt`. F005 Retail Readiness
  Model + `retail-orchestrate` (the sequence + the conductor sibling). The readiness spine and
  the constitution (Principles I, II, IV, V, VII, VIII, IX) -- committed.
- **Sibling policy (referenced, not depended on)**: F031 (spec 025, adapter-maintenance-policy)
  and F033 (spec 027, release-maturity) own the shared cross-adapter update/maturity policy.
- **Downstream**: F016 Power BI Execution Adapter -- the parked, execution-only adapter the
  publish asset triggers after `publish_ready` is `pass`.

## Non-goals

- Building any Dagster code, project, or asset in this slice (it is enumerated, not created).
- Defining the dbt model internals (F029) or the Power BI publish mechanics (F016).
- Owning the shared cross-adapter maintenance/maturity policy (F031 / F033).
- Emitting or defining a numeric readiness/health score (deferred; Principle IX).
- Replacing `retail-orchestrate` -- Dagster is its unattended sibling, not its successor.
- Any orchestration of sources outside the Postgres medallion (Postgres-first, Principle III).

## Assumptions

- The medallion sequence and the two human seams are FIXED by F005 / the constitution; this
  feature reuses them, it does not redefine them.
- When dbt is adopted (F029), silver/gold build assets are dbt assets via `dagster-dbt`; when
  it is not, they are SQL-migration assets. Either way the gate semantics are identical.
- The planned Dagster project is a SEPARATE, upgradeable dependency (Principle II): the kit
  depends on Dagster, it never forks it; upgrading Dagster requires no local-patch reapply.
- Run evidence is append/record-only and never overwrites a human-authored gate field.
- The C086 / retail_store_sales worked examples are CITED as filled references only; the
  generic artifacts carry placeholders (Principle VII).

## Deferred decisions

- **The concrete Dagster project + asset code**: DEFERRED to a later implementation slice
  (this slice is the spec; roadmap rule #8 -- planning first).
- **Numeric run scoring / a health number on a run**: DEFERRED until readiness scoring rules
  exist (Principle IX); run evidence stays statuses + measured numbers.
- **Schedules / sensors specifics** (cron cadence, event triggers): DEFERRED to the
  implementation slice; the spec names the `schedules/` and `sensors/` packages as planned
  shape only.
- **The shared cross-adapter auto-update policy**: DEFERRED to F031 (spec 025) / F033
  (spec 027); this spec states only Dagster's adapter-specific needs.

## See also

- The conductor sibling: `.claude/skills/retail-orchestrate/SKILL.md`;
  `specs/005-layer-d-orchestration/spec.md` (the sequence Dagster reuses).
- The category parent: `specs/018-companion-tools-architecture/` (F024).
- The transformation adapter it orchestrates: `specs/023-dbt-transformation-adapter/` (F029).
- The parked publish adapter it triggers: roadmap F016 (Power BI Execution Adapter).
- The maintenance/maturity siblings it references: `specs/025-adapter-maintenance-policy/`
  (F031), `specs/027-release-maturity-management/` (F033).
- The spine + no-fake-confidence rule: `docs/readiness/readiness-model.md`; the stage
  sequence: `docs/readiness/readiness-pipeline.md`.
- The roadmap row + hard rules 6, 7, 8, 9: `docs/roadmap/roadmap.md`. Constitution
  Principles I, II, IV, V, VII, VIII, IX.
