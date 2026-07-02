# Feature Specification: Approval Evidence Pack for the Named-Human Stage Gate

**Feature Branch**: `063-approval-evidence-pack`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "J1. Approval Evidence Pack for the Named-Human Stage Gate"

## Overview

The Seshat BI readiness spine (docs/readiness/readiness-model.md) has seven stages;
four of them -- Mapping Ready, Semantic Model Ready, Dashboard Ready, Publish Ready --
require a NAMED-HUMAN approval that the agent is constitutionally forbidden to grant
for itself (Principle V; recorded in each table's `mappings/<table>/readiness-status.yaml`
`approvals[]`). Today, when such a human is asked to sign a stage gate, the evidence they
need to decide is real but SCATTERED: the per-stage readiness doc says what the gate
requires; the table's readiness-status.yaml carries the current four-status state and the
open blockers; the AL1 assumption ledger (surfaced from the metric contracts) may flag an
unresolved judgment call; the parked-on dependency map may show the work is blocked on a
shared bottleneck. The human has no single legible place to SEE all of it before signing.

This feature defines a NEW generic Product Module (authority category: Product Module,
capability level: `artifact-writing`, per the F024 enumeration in
docs/architecture/product-modules.md) that COMPOSES a PRE-approval decision packet for ONE
selected stage gate of ONE table. It is generic across all seven stages via a stage
parameter; it reads only committed artifacts; it surfaces the recorded state, the blockers,
the unresolved assumptions, and the blocking parked-on edges; and it emits an EMPTY
`approvals[]` slot that the named human -- and only the named human -- fills in. The module
is structurally INCAPABLE of writing an approval, moving any stage to `pass`, defining
business meaning, or emitting any numeric confidence/health/maturity score or completeness
count. A missing source is a recorded BLOCKER, never fabricated content.

## Boundary against neighbouring shipped work (read first)

This feature is a genuine EXTENSION of the evidence-pack idea, not a restatement of an
existing tool. Two shipped neighbours must stay distinct:

- **F028 evidence-pack-generator** (.claude/skills/evidence-pack-generator/SKILL.md,
  spec 022) composes a LATE-STAGE, per-table 10-section pack for the Semantic Model ->
  Dashboard -> Publish window only. This feature is a PRE-approval packet generic across
  ALL seven stage gates (stage parameter), scoped to what ONE gate needs. It REUSES F028's
  surface-never-assert discipline and empty-approvals rule; it does NOT edit F028, and it
  does NOT re-render F028's 10 sections.
- **F027 Approval Console** (templates/approval-request.md / approval-decision.md,
  spec 021) packages ONE raised judgment call (one unresolved-questions row / grain-stop /
  control-room blocker) into a decidable request, and TRANSCRIBES a human's answer back
  into the committed artifacts. This feature packages a WHOLE-GATE readiness picture for a
  stage approval (many pieces of evidence, not one question) and WRITES NOTHING BACK -- it
  never transcribes an answer, never appends to `approvals[]`. The two compose: this pack
  is the evidence a human reads before the Approval Console records their signature.

This feature adds NO new readiness stage and NO new `retail check` rule -- it composes
results other tools recorded (the F024 Product Module boundary). It needs a NEW roadmap
F-number (the next Product Module id after F028); the exact number is a roadmap-ledger edit
recorded at plan time, not invented here.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A named human reads one pack before signing a stage gate (Priority: P1)

A metric owner is asked to approve the Semantic Model Ready gate for a table. Instead of
opening a dozen scattered artifacts, they ask for the approval evidence pack for that table
at that stage. They receive one ordered document that states what the Semantic Model Ready
gate requires, shows the recorded four-status readiness state for that stage and the ones
before it, lists every open blocker, surfaces any unresolved assumption the ledger flagged,
lists any blocking parked-on edge, and ends with an EMPTY approval slot for them to sign.
Everything in the pack links back to the committed artifact it came from.

**Why this priority**: This is the whole point of the feature -- give the named human a
single legible, fully-traceable basis for a decision only they may make. Without it, the
feature delivers nothing.

**Independent Test**: For a table with a filled readiness-status.yaml and the selected
stage's readiness doc present, generating the pack for that stage produces an ordered
document whose every claim resolves to a committed path, whose approval slot is empty, and
which contains no numeric score and no completeness count.

**Acceptance Scenarios**:

1. **Given** a table with a committed readiness-status.yaml where `semantic_model_ready` is
   `blocked` with two `blocking_reasons[]`, **When** the pack is generated for the
   `semantic_model_ready` stage, **Then** the pack shows status `blocked`, lists both
   reasons verbatim from the source, and its approval slot is empty.
2. **Given** the same table, **When** the pack is generated, **Then** every evidence line
   cites a committed repo-relative path and the pack contains no numeric
   confidence/health/maturity value and no "N of M" tally.
3. **Given** the pack is generated, **When** it is inspected, **Then** it does not write to
   or modify `readiness-status.yaml`, `approvals[]`, or any source artifact.

---

### User Story 2 - A required source is missing, so the pack records a blocker (Priority: P1)

The human requests a pack for a stage whose readiness doc exists but where the table's
readiness-status.yaml is absent, or the requested stage's status is `not_started`, or a
metric contract the ledger references is unreadable. The pack does NOT fabricate a plausible
state; each missing/unreadable source is recorded as an explicit BLOCKER naming the missing
path, and the approval slot stays empty.

**Why this priority**: The no-fabrication rule is the module's integrity guarantee; a pack
that invents a green state where evidence is absent would actively mislead the one person
whose signature matters. This must hold from day one.

**Independent Test**: Generate the pack for a table whose readiness-status.yaml is missing;
the pack renders with a top-level blocker naming that missing path, no invented status
values, and an empty approval slot.

**Acceptance Scenarios**:

1. **Given** a table with no `mappings/<table>/readiness-status.yaml`, **When** the pack is
   generated, **Then** the pack records a blocker naming that missing path and asserts no
   stage status as fact.
2. **Given** a stage whose readiness-status is `not_started`, **When** the pack is
   generated, **Then** the pack surfaces `not_started` as recorded (it does not treat
   absence of a block as readiness) and the approval slot stays empty.
3. **Given** a metric contract file the ledger references that cannot be read, **When** the
   pack is generated, **Then** the pack records that unreadable path as a blocker rather
   than silently dropping it.

---

### User Story 3 - The same generator serves any of the seven stages (Priority: P2)

An analyst uses the same module, changing only the stage parameter, to produce a pack for
Mapping Ready on one table and for Publish Ready on another. The module selects the correct
per-stage readiness doc under docs/readiness/ for each, and produces a pack whose "what this
gate requires" section reflects that stage -- with no worked-example (C086) specifics baked
into either output.

**Why this priority**: Genericity across all stages (Principle VII, and the stage-param
design) is what makes this a reusable Product Module rather than a one-gate script; but a
single working stage (P1) is already a viable slice, so this is P2.

**Independent Test**: Generate a pack for two different stages of two different tables; each
pack references the correct per-stage readiness doc and contains no C086/pharmacy-specific
label, grain key, or column name.

**Acceptance Scenarios**:

1. **Given** the stage parameter `mapping_ready`, **When** the pack is generated, **Then**
   it references `docs/readiness/mapping-ready.md` as the gate-requirements source.
2. **Given** the stage parameter `publish_ready`, **When** the pack is generated, **Then**
   it references `docs/readiness/publish-ready.md` as the gate-requirements source.
3. **Given** any stage, **When** the pack is generated, **Then** the pack template and any
   fixed section labels contain no worked-example domain specifics (Principle VII).

---

### Edge Cases

- What happens when the requested stage is one of the three MECHANICAL gates (Silver Ready,
  Gold Ready) that carry no named-human approval? The pack must state that this stage has no
  stage approval slot to sign and surface the mechanical gate result instead of emitting a
  human-approval slot -- it must not manufacture an approval seam where the spine defines
  none.
- What happens when the prior stage is not yet `pass`? The pack surfaces that the gate is
  not yet reachable (prior stage not `pass`) as a blocker; it never implies the current gate
  can be signed while an earlier stage is open.
- What happens when `approvals[]` for the selected stage is ALREADY filled (a prior human
  signed)? The pack surfaces the recorded approval read-only (owner + date from the source)
  and does not offer a fresh empty slot to re-sign -- it never overwrites or duplicates a
  recorded approval.
- What happens when the parked-on map lists an edge that blocks this table's stage? The pack
  surfaces that blocking edge (its recorded blocker, doc, and evidence) as a blocker.
- What happens when a stage's evidence would require re-stating a business-rule ruling (a
  metric's grain / rollup / segment) or a PII publish-safety ruling? See FR-013 and the
  Clarifications carve-out -- the pack LINKS and SUMMARISES the committed ruling and never
  re-decides or re-states it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The module MUST accept a target table identifier and a stage parameter (one of
  the seven readiness stage keys) and produce exactly one ordered evidence pack for that
  (table, stage) pair.
- **FR-002**: The module MUST read only already-committed artifacts. It MUST NOT connect to
  a database, read a live Power BI/PBIP surface, or invoke any deferred execution adapter
  (F016) or spec-only runtime (F031-F033).
- **FR-003**: The pack MUST surface, for the selected stage, what that gate requires, read
  from the corresponding per-stage readiness doc under `docs/readiness/`.
- **FR-004**: The pack MUST surface the recorded four-status readiness state
  (`not_started | blocked | warning | pass`) for the selected stage and the stages before
  it, read verbatim from `mappings/<table>/readiness-status.yaml`, and MUST NOT assert any
  status the source does not record.
- **FR-005**: The pack MUST list every open blocker for the selected stage, read from the
  source `blocking_reasons[]` (per stage and cross-cutting), each traceable to its source.
- **FR-006**: The pack MUST surface any unresolved assumption relevant to the table by
  reading the AL1 assumption-ledger signal from the table's metric contracts
  (`mappings/<table>/metrics/*.yaml`); it MUST NOT resolve the assumption (Principle V) and
  MUST NOT re-run or re-implement the AL1 rule -- it surfaces the recorded contradiction.
- **FR-007**: The pack MUST surface any blocking parked-on edge for the table's work by
  reading `docs/quality/parked-on.yaml`, citing each edge's recorded blocker, doc, and
  evidence.
- **FR-008**: The pack MUST surface the table's PENDING contracts as an input.
  [NEEDS CLARIFICATION: "pending contracts" has no single confirmed on-disk artifact --
  does it resolve to the set of `mappings/<table>/metrics/*.yaml` contracts whose
  `readiness.status` is not `pass`, to the Seeded/Planned markers in the KPI knowledge
  layer, or to a new per-stage pending list? A human must fix this input definition
  (Principle IV/V mapping-gate territory).]
- **FR-009**: The pack MUST end with an EMPTY `approvals[]` slot for the selected stage that
  the named human fills. The module MUST be structurally incapable of populating that slot,
  appending to `approvals[]`, or writing back to any source artifact.
- **FR-010**: The module MUST NOT move any stage to `pass`, grant any approval, or define or
  approve any business meaning (metric, mapping, rollup, segment) -- these are named-human /
  Core Authority actions (Principle V; F024 forbidden-operations matrix).
- **FR-011**: When a required source is missing, unfilled, a blank template, or unreadable,
  the module MUST record it as an explicit BLOCKER naming the missing/unreadable path and
  MUST NOT fabricate the input's content or a plausible status.
- **FR-012**: The pack MUST NOT emit any numeric confidence / health / maturity score and
  MUST NOT emit a completeness count or "N of M" tally (hard rule #9; Clarifications
  2026-06-25). Readiness is expressed only as the four explicit statuses + evidence +
  blockers.
- **FR-013**: For any evidence whose underlying artifact records a business-rule ruling (a
  metric contract's grain / rollup / segment) or a PII publish-safety ruling, the pack MUST
  only LINK and SUMMARISE the committed ruling; it MUST NOT re-decide or re-state the ruling
  in its own words in a way that could read as a fresh judgment.
  [NEEDS CLARIFICATION: confirm that summarising a committed grain / rollup / segment / PII
  ruling for the packet does not risk republishing a business-rule or PII judgment the named
  human owns -- a human must rule on the safe summarisation boundary (Principle V).]
- **FR-014**: The module and its template MUST stay generic (Principle VII): the worked
  example (C086 / retail_store_sales) may appear only as a cited filled instance, never
  inlined into the template or a fixed section label; the module MUST resolve a generic
  `mappings/<table>/` path.
- **FR-015**: When the selected stage is a mechanical gate with no named-human stage approval
  (per readiness-model.md), the pack MUST state that no stage-approval slot applies and
  surface the mechanical gate result instead of emitting a human-approval slot.
- **FR-016**: When `approvals[]` for the selected stage already records a human sign-off, the
  pack MUST surface it read-only (owner + date from source) and MUST NOT offer a fresh empty
  slot or overwrite the recorded approval.
- **FR-017**: All authored artifacts MUST be ASCII, UTF-8 without BOM (use `--` and `->`, no
  glyphs), and MUST use short repo-relative paths (Windows 260-char budget) (rule IX).

### Key Entities

- **Approval Evidence Pack**: the derived, ordered document this module writes for one
  (table, stage) pair. Composed from committed evidence; owns no truth; carries an empty
  approval slot; carries no score.
- **Stage parameter**: one of the seven readiness stage keys selecting which per-stage
  readiness doc and which readiness-status.yaml stage record the pack targets.
- **Readiness status record**: the per-stage `status` + `evidence[]` + `blocking_reasons[]`
  read from `mappings/<table>/readiness-status.yaml` (never written).
- **Assumption-ledger signal**: the AL1 contradiction surfaced from the table's metric
  contracts (read-only; never resolved).
- **Parked-on edge**: a dependency-edge record from `docs/quality/parked-on.yaml` that may
  block the table's stage.
- **Empty approval slot**: the un-filled `approvals[]` entry for the selected stage that
  only the named human completes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A named human can obtain, in one artifact, every piece of committed evidence
  needed to decide one stage gate for one table, with each item traceable to its source path
  (no separate hunt across artifacts).
- **SC-002**: 100% of evidence lines in a generated pack resolve to a committed repo-relative
  path; 0 lines assert a status or value not present in a source artifact.
- **SC-003**: 0 generated packs contain a numeric confidence/health/maturity score or a
  completeness count.
- **SC-004**: 0 generated packs write to, append to, or modify any source artifact,
  `readiness-status.yaml`, or `approvals[]` (the module is verifiably read-only apart from
  writing its own pack).
- **SC-005**: The same module, with only the stage parameter changed, produces a correct pack
  for each of the seven stages (mechanical gates included, per FR-015).
- **SC-006**: 0 generic artifacts (template, fixed section labels) contain a worked-example
  (C086/pharmacy) domain specific.

## Assumptions

- The seven per-stage readiness docs under `docs/readiness/` and `readiness-model.md` are the
  authoritative source for what each gate requires and which gates carry a named-human
  approval; the module reads them rather than encoding gate rules itself.
- `mappings/<table>/readiness-status.yaml` is the canonical state artifact (ADR 0004); the
  module reads the table's filled copy.
- The AL1 assumption-ledger rule (spec 059, `src/retail/rules/assumptions.py`) is the source
  of the assumption-contradiction signal; the module surfaces its recorded result rather than
  re-implementing the rule.
- `docs/quality/parked-on.yaml` is the parked-on dependency-edge map (DF1, spec 051); the
  module reads it for blocking edges.
- This module is docs/skill/template only (the agent is the runtime, per the F028 precedent);
  it adds no runtime executor and no new `retail check` rule.
- The new roadmap F-number is assigned at plan time via a roadmap-ledger edit; the spec does
  not invent one.
- The dashboard-specific evidence variant is OUT OF SCOPE for this feature (left to idea C1);
  this feature is strictly the generic multi-gate generator.

## Clarifications

<!-- Principle-V carve-out questions recorded here for a human ruling; the workflow is
     forbidden to answer these. Session answers to non-Principle-V ambiguities are added
     under a dated session heading by /speckit-clarify. -->

### Open for human ruling (Principle V -- NOT answered by this workflow)

- **Q-PENDING-CONTRACTS (FR-008)**: What exactly does "pending contracts" resolve to on
  disk -- the `mappings/<table>/metrics/*.yaml` contracts whose `readiness.status` is not
  `pass`, the Seeded/Planned markers in the KPI knowledge layer, or a new per-stage pending
  list? This defines a mapping-gate input and is a named-human ruling.
- **Q-BUSINESS-RULE-SUMMARY (FR-013)**: For a packet that summarises a committed grain /
  rollup / segment ruling or a PII publish-safety ruling, confirm the safe summarisation
  boundary so the pack never republishes a business-rule or PII judgment the named human
  owns.
