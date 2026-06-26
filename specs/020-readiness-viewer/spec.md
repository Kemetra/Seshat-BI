# Feature Specification: Readiness Viewer -- the stage-centric lens over readiness-status across sources, tables, and reports

**Feature Branch**: `020-readiness-viewer`  **Roadmap feature**: F026

> Numbering note: the roadmap F-number is the authoritative identity; the spec-dir
> number is the next free on-disk slot. Here spec-dir 020 = roadmap F026. When the dir
> number and the F-number disagree, the roadmap F-number wins. This header states both.

**Created**: 2026-06-25   **Status**: Shipped (readiness-viewer skill landed; spec authored no runtime Python by design)

**Input**: "Roadmap F026 (Product Module, read-only). A module that DISPLAYS readiness across sources / tables / reports by reading the Core Authority artifacts (readiness-status.yaml at mappings/<table>/, ADR 0004) -- current_stage, per-stage status, evidence[], blocking_reasons[], approvals[], next_action. It is the STAGE-CENTRIC lens: a per-stage status matrix across the seven readiness stages, evidence rendered as links/references, an approvals timeline, and the single next_action per table. It does NOT recompute truth, does NOT change readiness state, does NOT infer approvals, and shows missing evidence AS MISSING. Critical overlap: F012 Data Quality Control Room is already a read-only cross-table roll-up of findings + blockers; F026 is scoped strictly as the DELTA (a different view over overlapping inputs), with an explicit recommendation to ship as a stage-view mode of F012 (or merge into F012 if the delta proves thin). Generic (#7). No fake confidence (#9)."

## Clarifications

### Session 2026-06-25

- Q: How does the viewer know which stages REQUIRE an approval, so it flags "approval not recorded" only when one is genuinely missing (not on stages that need none)? -> A: The viewer reads the "Required owner / approval" field of each stage's `docs/readiness/<stage>-ready.md` ("who must sign off, if anyone", per readiness-model.md). A `pass` gate is flagged "approval not recorded" ONLY when that stage doc declares an approval is required AND no matching `approvals[]` entry exists. Where the stage doc records no required approver, an empty `approvals[]` is NORMAL and is not flagged. The viewer never infers the requirement itself -- it reads it from the stage doc.
- Q: Which set of items does the viewer enumerate, and how does it discover them? -> A: It reuses F012's exact fan-out: scan each `mappings/<table>/` directory for a `readiness-status.yaml` (ADR 0004 canonical location); one matrix row per discovered directory. "Sources / tables / reports" are whatever items have a `mappings/<item>/readiness-status.yaml` -- the viewer adds no second discovery path and invents no rows for items without a file (those are simply absent; a named-but-fileless item is the FR-009 "no readiness file" case only when explicitly asked about by name).
- Q: `evidence[]` entries are committed file PATHS (e.g. `mappings/<table>/source-profile.md`); the spec also says render "path, and line/section where recorded" -- is the viewer expected to produce a line number? -> A: The viewer renders each `evidence[]` entry VERBATIM as recorded. If the entry already carries a line/section anchor, it is rendered as-is; if it is a bare path, the viewer renders the bare path and does NOT synthesize a line number. "Line/section where recorded" describes the form an entry MAY take, never a value the viewer computes -- synthesizing a line/anchor not present in the source would be fabricated evidence (Forbidden).

## Why this feature exists

Every table, source, and report in the kit already carries its truth in one Core
Authority artifact: its `readiness-status.yaml` (canonically at
`mappings/<table>/readiness-status.yaml`, ADR 0004). That file records `current_stage`,
a per-stage `status` (`not_started` / `blocked` / `warning` / `pass`), `evidence[]`
(committed file references), `blocking_reasons[]`, `approvals[]` (named owner + date),
and the single `next_action`. The seven-stage spine (Source Ready -> Mapping Ready ->
Silver Ready -> Gold Ready -> Semantic Model Ready -> Dashboard Ready -> Publish Ready)
is fully recorded there.

What the kit lacks is a **stage-centric reading lens** over that data. Today, to answer
"which of the seven stages has each table reached, what evidence backs each stage, and
who approved the gate that let it advance", a human opens each `readiness-status.yaml`
and reconstructs the stage progression and the approval history by hand. The Data
Quality Control Room (F012, shipped) answers a different question -- "what is broken and
how badly, worst-first" -- and so reads the same files through a findings-and-blockers
lens, not a stage-progression lens.

The Readiness Viewer is that missing lens: a **read-only display** that renders the
seven-stage progression as a status matrix, renders `evidence[]` as navigable
references, renders `approvals[]` as a chronological timeline, and surfaces each table's
single `next_action`. It is a different VIEW over the same Core Authority inputs F012
already reads -- not a new pipeline, not a new measurement, and not a new source of
truth.

## What this feature is NOT (the scope wall)

This is the load-bearing constraint, stated up front so the spec cannot drift:

- **It computes NO truth.** It does not recompute a stage status, does not re-derive
  whether a gate passed, does not run `retail check` / `retail validate`, and does not
  open a DB connection. It renders `current_stage` and the per-stage `status` exactly as
  the `readiness-status.yaml` records them. If the file says a stage is `pass`, the
  viewer shows `pass`; it never decides `pass` itself. (Core Authority owns truth.)
- **It changes NO readiness state.** It never writes a `pass`, never advances a stage,
  never edits a `readiness-status.yaml`, `source-map.yaml`, `assumptions.md`, or any
  per-table artifact. Read-only end to end.
- **It infers NO approval.** It RENDERS recorded `approvals[]` (each a named owner +
  date already written by the approving human); it never establishes, fabricates, or
  back-fills an approval, and never treats an unapproved gate as approved. An approvals
  timeline with a gap shows the gap.
- **It shows missing evidence AS MISSING.** When a stage's `evidence[]` is empty or a
  referenced file is absent, the viewer renders "evidence missing" (and names what is
  expected). It never invents an evidence reference, never fills the gap, and never lets
  a missing-evidence stage read as complete.
- **No fake confidence, no invented score.** Readiness is the four explicit statuses +
  evidence + blockers. The viewer MUST NOT emit a numeric health/confidence score or a
  "percent ready" number that reads as confidence (hard rule #9). A score is OPTIONAL
  and DEFERRED until scoring rules exist; the viewer must not be the place one appears.
- **Generic.** No worked-example specifics (billing codes, segments, PII column names,
  per-table grain keys). C086 / retail_store_sales are filled instances cited as
  references, never baked into the module or its template (Principle VII).

## Relationship to shipped F012 (scope delta)

This section is load-bearing: F012 (Data Quality Control Room, shipped, commit
`e9a3264`, skill `.claude/skills/retail-control-room/`) is ALREADY a read-only
cross-table roll-up of findings + blockers, worst-first, no-fake-confidence, reading the
same per-table `readiness-status.yaml`. F026 must be the DELTA, not a re-spec.

**Same inputs, different view.** Both modules read the same Core Authority files. F026
introduces NO new input, NO new measurement, and NO new pipeline. The difference is the
lens:

| Dimension | F012 Control Room (shipped) | F026 Readiness Viewer (this feature) |
|-----------|-----------------------------|--------------------------------------|
| Organizing question | "What is broken, how badly, worst-first?" | "Which of the 7 stages has each item reached, with what evidence and approvals?" |
| Stage rendering | `current_stage` + its one status, in a worst-first list | a per-stage MATRIX across all 7 stages (each stage's status per item) |
| `evidence[]` rendering | summarized as MEASURED COUNTS (WARNs, findings, open blockers) | rendered as NAVIGABLE REFERENCES (the committed file path/line per stage) |
| `approvals[]` rendering | not read by F012 | rendered as a chronological TIMELINE (who approved which gate, when) |
| Primary axis | severity (findings + blockers, descending) | the stage spine (Source Ready .. Publish Ready) |
| `next_action` | already surfaced by F012's per-table roll-up | also surfaced (NOT a differentiator -- shared) |

The three genuine deltas are exactly: (1) the per-stage status matrix across all seven
stages (F012 shows only `current_stage` + one status), (2) `evidence[]` rendered as
references/links rather than as counts, and (3) the `approvals[]` timeline (F012 does
not read `approvals[]` at all). `next_action` is shared with F012 and is NOT claimed as
a delta.

**Recommended shape (a named decision, not a mention):**

- **(a) Preferred -- ship as a stage-view MODE that reuses F012's aggregation.** The
  Readiness Viewer should reuse F012's existing read-fan-out over the per-table files
  rather than re-implement the scan. F026 adds the stage-matrix / evidence-reference /
  approvals-timeline rendering on top; F012 keeps owning the findings-and-blockers
  roll-up. One aggregation, two lenses.
- **(b) Fallback -- merge into F012 if the delta proves thin.** If, during planning, the
  three deltas reduce to "a re-sorted control room" (i.e. the stage matrix adds no
  reader value beyond `current_stage`, evidence-as-reference is cosmetic, and the
  approvals timeline is rarely populated), then F026 should NOT ship as a separate
  module -- it should be folded into F012 as an optional stage-view section. The
  thinness criterion is explicit: **if the only durable difference is sort order and
  column labels, merge.** If the stage matrix + evidence references + approvals timeline
  each give a reader something the control room cannot, ship as mode (a).

This humility is part of the spec's correctness: a viewer that duplicates F012 is waste,
and the spec must make the merge option a first-class outcome.

## Architecture (planning posture: pure skill + one generic template; no code this slice)

Consistent with F012 and the shipped F005-F015 slices: the viewer is **agent-procedure
text + one generic output template**, and the agent is the runtime. Planned decision:
**a pure skill (or a mode of the F012 skill) plus one generic stage-view template; NO
new Python, NO new `retail` subcommand, NO codegen** in this slice.

Deciding reason: the work is a read-fan-out over a handful of committed YAML files plus
re-rendering their already-recorded fields through a stage lens -- exactly the
read-and-present posture F012 (`retail-control-room`) and `retail-validate`
("invoke-and-interpret only") already use. The open architectural choice -- a NEW
`readiness-viewer` skill vs. a MODE of `retail-control-room` -- is the same decision as
the (a)/(b) recommendation above and is resolved in plan.md's Phase 0; either way the
posture is pure-skill + one template, reusing F012's aggregation. A `src/retail/tools/
readiness_viewer.py` CLI is enumerated as an OPTIONAL FUTURE deliverable (a later
read-only reporter, still no new validator), deferred and not built here.

This feature sits under the Product Module / companion-tools category established by
F024 (Companion Tools Architecture, spec-dir 018) -- the read-only module contract that
binds modules to READ / SUMMARIZE / VISUALIZE / write-DERIVED-evidence / EXECUTE-approved
without creating truth. F024 defines that contract; F026 is an instance of it. (F024 is
a sibling spec in this batch; it is cited as the dependency that establishes the
category, not detailed here.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The seven-stage status matrix across all items (Priority: P1)

A human (or the agent) asks "show me the readiness viewer". The module reads each item's
`readiness-status.yaml` and renders ONE matrix: a row per item (table / source / report)
and a column per stage (Source Ready, Mapping Ready, Silver Ready, Gold Ready, Semantic
Model Ready, Dashboard Ready, Publish Ready), each cell showing that stage's recorded
`status` (one of the four words). The item's `current_stage` is marked, and its single
`next_action` is shown. Every cell is the status the file records -- never a recomputed
or upgraded one.

**Why this priority**: this is the feature -- the stage-progression view the kit lacks
and that F012 does not provide (F012 shows only `current_stage` + one status). Without
it, the seven-stage lens does not exist.

**Independent Test**: with two or more items each having a `readiness-status.yaml`, the
module emits one matrix whose every cell equals the per-stage `status` in that item's
file, with `current_stage` marked and `next_action` shown, and modifies nothing. A stage
the file records as `pass` shows `pass`; a stage it records as `not_started` shows
`not_started`; no cell is computed by the viewer.

**Acceptance Scenarios**:

1. **Given** N items each with a `readiness-status.yaml` recording per-stage status,
   **When** the module runs, **Then** it emits one matrix (item rows x seven stage
   columns) where each cell is the recorded status, `current_stage` is marked, and
   nothing is modified.
2. **Given** an item whose file records Source/Mapping/Silver as `pass` and Gold as
   `blocked`, **When** the module runs, **Then** the matrix shows exactly those statuses
   and does NOT infer the later stages as anything other than their recorded value
   (typically `not_started`).
3. **Given** an item whose `readiness-status.yaml` is absent, **When** the module runs,
   **Then** it shows that item's row as "no readiness file" and does NOT invent stage
   statuses (missing shown as missing).

### User Story 2 - Evidence rendered as navigable references, missing shown as missing (Priority: P1)

For a chosen item (or for every stage of every item), the module renders each stage's
`evidence[]` as the committed reference(s) backing that stage -- the file path (and
line/section where the source records it) -- so a reviewer can navigate from "Gold Ready
= pass" to the exact evidence file that backs it. Where a stage has no evidence, the
module renders "evidence missing" and names what the stage expects; it never fabricates
a reference.

**Why this priority**: a stage matrix without "what backs each cell" is unverifiable.
Rendering evidence as references (not as F012's counts) is one of the three genuine
deltas, and it is what lets a reviewer audit a `pass` rather than trust it.

**Independent Test**: given an item whose Gold Ready stage lists two evidence files, the
module renders both as references the reviewer can open; given a stage with empty
`evidence[]`, the module renders "evidence missing" with the expected artifact named --
and in neither case does it invent or fill a reference.

**Acceptance Scenarios**:

1. **Given** a stage with a populated `evidence[]`, **When** the module renders it,
   **Then** each evidence entry appears as its committed reference (path, and line/section
   where recorded), navigable, copied verbatim from the source.
2. **Given** a stage marked `pass` but with empty `evidence[]`, **When** the module
   renders it, **Then** it shows "evidence missing for a pass stage" as an explicit flag
   (a `pass` without evidence is surfaced, never hidden) and does NOT fabricate evidence.
3. **Given** an `evidence[]` entry whose referenced file no longer exists on disk,
   **When** the module renders it, **Then** it shows the reference marked "referenced
   file not found" -- it does not drop the entry and does not invent a replacement.

### User Story 3 - The approvals timeline (Priority: P2)

For a chosen item, the module renders its `approvals[]` as a chronological timeline: for
each recorded approval, the gate/stage it approved, the named owner who approved it, and
the date -- in order. Gaps (a stage that advanced with no recorded approval, where the
stage's gate requires one) are shown as gaps. The module RENDERS recorded approvals; it
never establishes, infers, or back-fills one.

**Why this priority**: the approvals timeline is the third genuine delta (F012 does not
read `approvals[]`). It answers "who let this item advance, and when" -- the governance
audit view. It is P2 because the stage matrix (US1) is already a usable lens without it.

**Independent Test**: given an item with three recorded approvals at different stages,
the module lists all three in date order with {stage approved, named owner, date} copied
from the source; given a `pass` stage whose gate requires approval but whose
`approvals[]` has no matching entry, the module shows that gate as "approval not
recorded" -- and it adds no approval of its own.

**Acceptance Scenarios**:

1. **Given** an item with recorded `approvals[]`, **When** the module renders the
   timeline, **Then** each approval appears as {stage/gate, named owner, date} in
   chronological order, copied verbatim -- nothing invented.
2. **Given** a stage that reads `pass` whose `docs/readiness/<stage>-ready.md` declares a
   required approver and whose `approvals[]` lacks a matching entry, **When** the timeline
   renders, **Then** it shows "approval not recorded for this gate" and does NOT infer an
   approver (no-self-approval; Principle V). **Given** a `pass` stage whose stage doc
   declares NO required approver, an empty `approvals[]` is NOT flagged.
3. **Given** the module runs, **Then** `git status` shows zero modification to any
   `readiness-status.yaml` or per-item artifact (read-only proven), and no `approvals[]`
   entry was added by the viewer.

### Edge Cases

- **Zero items with a readiness file**: the viewer renders an empty matrix with a clear
  "no items onboarded yet" note -- it does not error and does not invent rows.
- **A `readiness-status.yaml` is malformed / partially filled**: the viewer renders that
  item's row as "readiness file incomplete: `<file>`" for the affected fields rather than
  guessing the missing stage statuses or evidence.
- **`current_stage` disagrees with the per-stage statuses** (e.g. `current_stage:
  gold_ready` but Silver Ready recorded `blocked`): the viewer SURFACES the conflict as a
  flag and does NOT resolve it by picking one (surface conflicts, never bury them;
  Principle V posture). It is a viewer, not an arbiter.
- **A stage is `pass` with empty `evidence[]`**: surfaced as "pass without evidence", an
  explicit flag (a `pass` must carry evidence per the readiness model); never hidden.
- **An approval references a stage the matrix shows as `not_started`**: shown as a
  conflict flag; the viewer does not reconcile or delete the stray approval.
- **A request for "one readiness score / percent-ready per item"**: DECLINED with the
  no-fake-confidence rationale; the viewer returns the four explicit statuses across the
  seven stages instead (hard rule #9).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add the viewer as `.claude/skills/readiness-viewer/SKILL.md` (ASCII, UTF-8
  no BOM, valid frontmatter) OR as a documented stage-view MODE of the existing
  `retail-control-room` skill -- the choice is the (a)/(b) decision recorded in plan.md.
  Either way: NO new Python, NO new `retail` subcommand, NO codegen this slice.
- **FR-002**: Add ONE generic stage-view template (`templates/readiness-view.md`) -- the
  module's stable output shape (the seven-stage matrix + evidence-reference block +
  approvals timeline). ASCII, UTF-8 no BOM, placeholders only, no worked-example
  specifics (Principle VII).
- **FR-003**: The module MUST read ONLY existing Core Authority inputs: each item's
  `readiness-status.yaml` (`current_stage`, per-stage `status`, `evidence[]`,
  `blocking_reasons[]`, `approvals[]`, `next_action`). It MUST run NO validator, open NO
  DB connection, and add NO new gate. It reuses F012's read-fan-out over these files
  rather than re-implementing the scan (recommended shape (a)). Item discovery is exactly
  F012's fan-out: scan each `mappings/<item>/` directory for a `readiness-status.yaml`
  (ADR 0004 canonical location) and emit one matrix row per discovered file. The viewer
  adds NO second discovery path and invents NO row for an item that has no file; a
  named-but-fileless item surfaces only as the FR-009 "no readiness file" case when a
  reader asks about it by name (Clarification 2026-06-25).
- **FR-004**: The view MUST render a per-stage status MATRIX across all seven stages
  (Source Ready -> Publish Ready) -- one row per item, one column per stage, each cell
  the recorded `status`. `current_stage` MUST be marked and the single `next_action`
  shown. This is the F012 delta: F012 shows only `current_stage` + one status.
- **FR-005**: The module MUST render each stage's `evidence[]` as NAVIGABLE REFERENCES,
  copied VERBATIM from the source -- not as F012's measured counts. Each entry is rendered
  in exactly the form it is recorded: if the entry carries a line/section anchor it is
  rendered with that anchor; if it is a bare committed path it is rendered as a bare path.
  The viewer MUST NOT synthesize a line number or section anchor that the source does not
  record (that would be fabricated evidence; Clarification 2026-06-25). A stage with empty
  `evidence[]` MUST render "evidence missing" with the expected artifact named; a
  referenced file absent on disk MUST render "referenced file not found". Evidence is NEVER
  fabricated or filled in (FR maps to the scope-wall "shows missing evidence AS MISSING").
- **FR-006**: The module MUST render `approvals[]` as a chronological TIMELINE: each
  approval as {stage/gate, named owner, date}, in date order, copied verbatim. It MUST
  NOT establish, infer, or back-fill an approval. A gate that reads `pass` is flagged
  "approval not recorded" ONLY when an approval is genuinely required and absent: the
  viewer reads the "Required owner / approval" field of that stage's
  `docs/readiness/<stage>-ready.md` ("who must sign off, if anyone", per readiness-model.md)
  and flags only when the stage doc declares an approver is required AND no matching
  `approvals[]` entry exists. Where the stage doc records no required approver, an empty
  `approvals[]` is NORMAL and MUST NOT be flagged. The viewer reads the requirement from
  the stage doc; it never infers the requirement itself (no-self-approval; Clarification
  2026-06-25).
- **FR-007**: The module MUST be READ-ONLY: it MUST NOT recompute a stage status, MUST
  NOT advance a stage, MUST NOT write a `pass`, MUST NOT edit any `readiness-status.yaml`
  or per-item artifact, MUST NOT add an approval, MUST NOT run SQL or `retail check` /
  `retail validate`. Truth stays in the Core Authority files; the viewer renders it.
- **FR-008**: No-fake-confidence guard: the module MUST refuse to emit a numeric
  health / confidence / percent-ready score. If asked, it declines, cites readiness-model
  "No fake confidence", and returns the four explicit statuses across the seven stages.
  Any future optional score is DEFERRED and out of scope here.
- **FR-009**: Missing / partial input handling: an item with no `readiness-status.yaml`
  MUST render "no readiness file"; a malformed/partial file MUST render "readiness file
  incomplete: `<file>`" for the affected fields -- never an invented stage status,
  evidence reference, or approval.
- **FR-010**: Conflict surfacing: when `current_stage` disagrees with the per-stage
  statuses, when a `pass` stage has empty `evidence[]`, or when an approval references a
  `not_started` stage, the module MUST surface the conflict as a flag and MUST NOT
  resolve it (surface, never bury; Principle V posture).
- **FR-011**: The module MUST state its relationship to F012 in its own SKILL/mode text:
  same inputs, different lens; F012 owns findings + blockers (worst-first), F026 owns the
  stage matrix + evidence references + approvals timeline; `next_action` is shared and
  not a delta. It MUST reuse F012's aggregation (shape (a)) or be a section of F012
  (shape (b)).
- **FR-012**: Append an `## Orchestration` pointer so `retail-orchestrate` can invoke the
  viewer as the stage-progression READ after sequencing an item; the viewer reads state
  and reports, it advances no stage and clears no blocker.

### Key Entities

- **Readiness Viewer** (`readiness-viewer` skill, or a stage-view mode of
  `retail-control-room`): the read-only stage-centric rendering verb; the agent is the
  runtime. Invoke-and-present only. Creates no truth.
- **Stage-view template** (`templates/readiness-view.md`): the generic, copy-me output
  shape -- the seven-stage matrix + evidence-reference block + approvals timeline. The
  stage-lens sibling of F012's `templates/data-quality-control-room.md`.
- **Readiness status (existing Core Authority input, unchanged)**: each item's
  `readiness-status.yaml` (`current_stage`, per-stage `status`, `evidence[]`,
  `blocking_reasons[]`, `approvals[]`, `next_action`). The INPUT; the feature creates no
  new per-item artifact and edits none.
- **The seven-stage spine (existing)**: Source Ready -> Mapping Ready -> Silver Ready ->
  Gold Ready -> Semantic Model Ready -> Dashboard Ready -> Publish Ready. The columns of
  the matrix; defined by the readiness model, rendered (not redefined) here.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `.claude/skills/readiness-viewer/SKILL.md` (or the documented F012
  stage-view mode) and `templates/readiness-view.md` exist, ASCII + no BOM, frontmatter
  valid, registered by the harness; both generic (no worked-example specifics).
- **SC-002**: `retail check` stays exit 0 and no new rule is added with the new skill
  + template; the full unit suite stays green; NO new Python; the static rule set and
  validator surface are unchanged. (The feature adds NO rule and NO validator.)
- **SC-003**: Given two or more items with a `readiness-status.yaml`, the module produces
  one matrix in which EVERY cell equals the per-stage `status` recorded in that item's
  file, `current_stage` is marked, `next_action` is shown, and `git status` shows zero
  modified per-item files (read-only proven).
- **SC-004**: Evidence renders as references: for an item with populated `evidence[]`,
  every entry appears as its committed reference; a `pass` stage with empty `evidence[]`
  is flagged "evidence missing"; an absent referenced file is flagged "referenced file
  not found" -- with zero fabricated references.
- **SC-005**: The approvals timeline renders recorded `approvals[]` in date order with
  {stage, owner, date} verbatim; a `pass` gate lacking its required approval is flagged
  "approval not recorded"; the viewer adds no approval (no-self-approval proven).
- **SC-006**: The F012 delta holds: a reader of the spec + artifacts can state, without
  ambiguity, that F026 reads the SAME inputs as F012, differs only in the three named
  deltas (stage matrix / evidence references / approvals timeline), shares `next_action`
  with F012, and that the recommended shape is a stage-view mode reusing F012's
  aggregation -- with the merge fallback and its thinness criterion stated.
- **SC-007**: A request for a single readiness / confidence / percent-ready score is
  DECLINED with the no-fake-confidence rationale; the four explicit statuses across the
  seven stages are returned instead (rule #9).

## Human approval boundary

The viewer establishes NO approvals and grants NONE. Approvals are created by named
humans and recorded in `approvals[]` by the Core Authority flow (the gate the approval
belongs to). The viewer RENDERS those recorded approvals as a timeline and FLAGS gates
whose required approval is absent. Moving a stage to `pass`, recording an approval, and
clearing a blocker all remain Core Authority actions by the named owner -- never the
viewer (Principle V; no-self-approval).

## Allowed operations

- READ each item's `readiness-status.yaml`, the files its `evidence[]` references, and the
  "Required owner / approval" field of each `docs/readiness/<stage>-ready.md` (to know
  which gates require an approval before flagging a missing one).
- SUMMARIZE / VISUALIZE the recorded state as a stage matrix, an evidence-reference
  block, and an approvals timeline (the rendering this feature exists to do).
- REUSE F012's existing read-fan-out over the per-item files (recommended shape (a)).
- SURFACE conflicts and missing evidence/approvals as explicit flags.
- STOP and report; emit the rendered view and the single `next_action` per item.

## Forbidden operations

- Recompute, re-derive, or upgrade a stage `status`; decide a gate `pass`/`fail`.
- Advance a stage, write a `pass`, or edit any `readiness-status.yaml` or per-item
  artifact.
- Establish, infer, or back-fill an `approvals[]` entry; treat an unapproved gate as
  approved (no-self-approval).
- Fabricate or fill in a missing `evidence[]` reference; hide a missing-evidence `pass`.
- Run `retail check` / `retail validate` as a new check, run SQL, or open a DB
  connection.
- Emit a numeric health / confidence / percent-ready score (hard rule #9).
- Inline C086 / retail_store_sales specifics into the skill or template (Principle VII).
- Resolve a conflict between `current_stage` and per-stage statuses by picking one.

## Evidence required

- The module renders, per item: the seven-stage status matrix (each cell = recorded
  `status`), the per-stage `evidence[]` as navigable references (with "evidence missing"
  / "referenced file not found" where applicable), the `approvals[]` timeline (with
  "approval not recorded" flags), and the single `next_action`. Every rendered value
  traces to a named committed source (path, and line/section where applicable) in the
  item's `readiness-status.yaml` or the file it references. A rendered value with no
  traceable source is a defect.

## Readiness stage affected

Cross-stage (all seven). The viewer is a stage-progression LENS over every stage; it
does not itself gate or advance any single stage. It mirrors F012's "advances readiness
stage: all stages (a consolidated view)" posture -- a view, not a gate.

## Dependencies

- **Upstream**: F024 (Companion Tools Architecture, spec-dir 018) -- the Product Module /
  read-only companion-tools category and the read-only module contract this feature is an
  instance of. The readiness spine (F005: `docs/readiness/`,
  `templates/readiness-status.yaml`) -- the seven stages + the status schema the viewer
  renders. F012 (Data Quality Control Room, shipped) -- the aggregation the recommended
  shape (a) reuses and the module this could merge into (shape (b)).
- **Downstream**: none required. The viewer is a leaf read-only lens.

## Non-goals

- Any new `retail check` rule, Python module, or CLI verb in this slice (the optional
  `src/retail/tools/readiness_viewer.py` is a deferred FUTURE deliverable, not built
  here).
- Re-implementing F012's findings-and-blockers roll-up (the viewer reuses it or is a mode
  of it).
- Recomputing, gating, or advancing any readiness stage.
- A numeric readiness score (deferred; rule #9).
- A historical trend / cross-time readiness view (that durable cross-time state is F015
  Reconciliation Ledger's domain; the viewer is point-in-time).

## Assumptions

- Pure skill (or a mode of `retail-control-room`) + one generic template; the agent is
  the runtime (same posture as F012 / features 005-006). No new Python, no CLI, no
  codegen this slice (roadmap rule #8).
- The Core Authority input -- each item's `readiness-status.yaml` with `current_stage`,
  per-stage `status`, `evidence[]`, `blocking_reasons[]`, `approvals[]`, `next_action` --
  already exists as the committed schema (`templates/readiness-status.yaml`, ADR 0004)
  and is the authoritative input; this feature consumes it, never redefines it.
- F012's read-fan-out over the per-item files is reusable as the aggregation layer
  (recommended shape (a)); the viewer adds rendering, not scanning.
- "Cross-stage / all stages" means the view spans every stage (it renders the seven-stage
  progression); it does not itself gate or advance any single stage.

## Deferred decisions

- **Skill-vs-mode (a)/(b)**: whether F026 ships as a new `readiness-viewer` skill reusing
  F012's aggregation, or as a stage-view section folded into `retail-control-room` -- to
  be settled in plan.md Phase 0 against the stated thinness criterion. Recommended:
  shape (a) unless the delta proves thin.
- **A `src/retail/tools/readiness_viewer.py` CLI / programmatic renderer**: DEFERRED. If
  item volume outgrows hand-rendering, a read-only reporter (still no new validator) could
  parse the files and emit the matrix; a code surface change for a later slice.
- **A machine-readable view export** (e.g. a `readiness-view.json`) for a future UI:
  DEFERRED until a consumer exists.
- **A numeric readiness score / percent-ready**: DEFERRED until scoring rules are defined
  in the readiness model (rule #9). The viewer must not be where one first appears.

## See also

- The headline overlap it is the delta of: F012 Data Quality Control Room --
  `.claude/skills/retail-control-room/SKILL.md`,
  `templates/data-quality-control-room.md`, `specs/013-data-quality-control-room/spec.md`.
- The Core Authority input it renders: `templates/readiness-status.yaml` (`current_stage`,
  per-stage `status`, `evidence[]`, `blocking_reasons[]`, `approvals[]`, `next_action`);
  ADR 0004 (canonical `mappings/<table>/readiness-status.yaml` location).
- The module category + read-only contract: F024 Companion Tools Architecture
  (`specs/018-companion-tools-architecture/`).
- The model + no-fake-confidence rule: `docs/readiness/readiness-model.md`; the stage
  sequence: `docs/readiness/readiness-pipeline.md`.
- The conductor it plugs into: `.claude/skills/retail-orchestrate/SKILL.md`.
- The roadmap row + hard rules: `docs/roadmap/roadmap.md` (F026 in the post-F016 batch;
  rules #7/#8/#9); Constitution Principles V, VII, VIII, IX. C086 / retail_store_sales are
  cited filled instances: `docs/worked-examples/c086-pharmacy.md`.
