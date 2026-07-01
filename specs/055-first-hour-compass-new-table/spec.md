# Feature Specification: First-Hour Compass / New-Table Author Onboarding Cockpit

**Feature Branch**: `055-first-hour-compass-new-table` (spec dir renumbered to `055-first-hour-compass-new-table` to avoid the 053 collision across the parallel kraken runs; roadmap F-number wins on any disagreement)

**Created**: 2026-07-01

**Status**: Ratified (advisor-for-Ahmed-Shaaban, 2026-07-01)

**Ratification note**: Ratified by the advisor agent under the explicit, recorded
per-session delegated override granted by the repo owner (info@rahmaqanater.org) for the
2026-07-01 "release the kraken" batch of seven idea-to-spec specs. Provenance: this Ratified
line is AI-authored under recorded human authority; it is NOT a human-typed ratification and
the git author identity does not by itself attest a human reviewer. The four Principle-V seam
carve-outs (grain, PII publish-safety, business rollup/segment, product identity) are resolved
to the conservative surface-only posture (the Compass re-presents the recorded STOP, never
asserts/picks/embeds/clears) -- see the Clarifications section. MVP scope is docs-only: a
generic template + a read-only SKILL.md + a tools doc; the `next_step.py` resolver is DEFERRED
(not a task). No runtime code, no new retail check rule (count stays 38). analyze=clean
(0 critical/0 high); plan-review=PASS-WITH-NOTES. Override is per-session/per-this-set only;
it covers ratification, not merge (normal CI gate still applies).

**Input**: User description: "First-Hour Compass / New-Table Author Onboarding Cockpit"

## Overview

The First-Hour Compass is a READ-ONLY, docs-first, single-table "you-are-here"
orientation surface for a human author onboarding one table through the seven-stage
readiness spine. It reads ONE table's `mappings/<table>/readiness-status.yaml` and
renders an orientation card that answers three questions for that single table:

1. Where am I? -- the current stage (`current_stage`, copied verbatim).
2. What do I produce next? -- the next artifact (the artifact of the FIRST non-pass
   stage in the seven-stage ordering).
3. Which skill produces it? -- the authoring skill for that next stage, from a
   generic stage -> authoring-skill cross-walk.

It is a lens, not a gate and not an executor. It RENDERS recorded state and STOPS.

### The delta (names both shipped parents)

The Compass is a genuine DELTA to two shipped surfaces it explicitly names:

- **Shipped readiness-viewer (F026, `specs/020-readiness-viewer/`)** -- a
  MULTI-TABLE, STATUS-ONLY matrix (one row per table x seven stage status columns).
  It answers "which stage is each table at, with what evidence and approvals". It
  does NOT produce a single-table orientation, a next-artifact pointer, or an
  authoring-skill route. The Compass is the SINGLE-TABLE, STATEFUL, you-are-here +
  next-artifact + authoring-skill presenter -- a different question over the same
  Core Authority input.
- **Static F006 onboarding-checklist (`docs/readiness/onboarding-checklist.md`)** --
  a STATIC definition-of-done for Source Ready -> Mapping Ready. It is not stateful
  and does not read `readiness-status.yaml`. The Compass is the STATEFUL version of
  that static checklist: it reads the recorded per-stage state and reports where the
  author actually is right now.

### Roadmap position (open human decision)

This idea carries NO roadmap F-number. The idea-bank tag `V8 / F7` is a reviewer
Value/Feasibility triage score, NOT a roadmap F-number, and the idea-bank is
explicitly not the roadmap. Whether the Compass enters the roadmap, and under which
stage/layer, is an OPEN decision reserved for a human (see Clarifications). This
spec does NOT invent an F-number.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Orient a single table author (Priority: P1)

A human author has been assigned to move one table through the readiness spine. They
open the Compass for that one table. The Compass reads that table's
`readiness-status.yaml`, tells them the stage they are currently at, names the single
next artifact they must produce, and names the authoring skill that produces it. The
author now knows exactly what to do next without reading all seven stage docs.

**Why this priority**: This is the entire value of the feature -- a stateful,
single-table "you are here / do this next / use this skill" orientation for the
verified-unserved new-table author. Without it, there is no MVP.

**Independent Test**: Point the Compass at one `mappings/<table>/readiness-status.yaml`
whose first non-pass stage is, say, Mapping Ready. Confirm the card renders the
recorded `current_stage`, names the Mapping Ready artifact as the next artifact, and
routes to the mapping authoring skill via the generic cross-walk -- all copied from
recorded fields, none recomputed.

**Acceptance Scenarios**:

1. **Given** a table whose `readiness-status.yaml` records Source Ready `pass` and
   Mapping Ready `not_started`, **When** the Compass renders the card, **Then** it
   shows the current stage verbatim, names Mapping Ready as the next stage, names the
   Mapping Ready artifact as the next artifact, and routes to the mapping authoring
   skill -- and presents NO downstream stage (Silver Ready and later) as reachable.
2. **Given** a table whose `readiness-status.yaml` records all seven stages `pass`,
   **When** the Compass renders the card, **Then** it reports "all stages pass -- no
   next artifact" and names no further authoring skill (it never invents a next step
   beyond Publish Ready).
3. **Given** a table with no `readiness-status.yaml`, **When** the Compass is asked to
   render, **Then** it reports "no readiness file for `<table>`" and invents no stage
   statuses, no next artifact, and no skill route.

### User Story 2 - Surface who must approve / what is blocked (Priority: P2)

At the next stage, the author needs to know whether a human approval or a recorded
blocker stands in the way. The Compass surfaces, for the current/next stage, the
recorded `blocking_reasons[]`, the `approvals[]` state, and -- read from the stage
doc's "Required owner / approval" field -- whether an approver is required and not yet
recorded. It never populates an approval, never clears a blocker, never advances a
stage.

**Why this priority**: Orientation is incomplete if it hides a STOP. But this is the
Principle-V surface: the Compass must SURFACE the STOP and never resolve it. This is
second only because the core you-are-here/next-artifact orientation (P1) is the MVP.

**Independent Test**: Point the Compass at a table whose next stage records a
`blocking_reason` and whose stage doc requires an approver with no matching
`approvals[]` entry. Confirm the card surfaces the recorded blocker verbatim and flags
"approval not recorded" -- and that `git status` is clean afterward (nothing populated).

**Acceptance Scenarios**:

1. **Given** the next stage records `blocking_reasons: ["<recorded reason>"]`, **When**
   the card renders, **Then** it shows that reason verbatim as a STOP row and proposes
   no resolution.
2. **Given** the next stage's `docs/readiness/<stage>-ready.md` "Required owner /
   approval" field declares an approver IS required AND no matching `approvals[]` entry
   exists, **When** the card renders, **Then** it flags "approval not recorded" and
   NEVER infers, establishes, or back-fills an approver.
3. **Given** the next stage's stage doc declares NO required approver (a mechanical
   gate), **When** the card renders, **Then** an empty `approvals[]` is treated as
   NORMAL and is NOT flagged.

### User Story 3 - Route via a generic stage -> authoring-skill cross-walk (Priority: P3)

The Compass carries a GENERIC stage -> authoring-skill cross-walk: for each of the
seven stages, which authoring skill produces that stage's artifact. This cross-walk is
authored as a generic mapping (`<stage_key>` -> `<skill>` placeholders), never baking in
any one table's stage assignments.

**Why this priority**: The routing is what turns "your next stage is X" into "use skill
Z". It is P3 because P1 already delivers the you-are-here orientation; the cross-walk
enriches it.

**Independent Test**: Read the cross-walk table in isolation and confirm it maps each
of the seven `<stage_key>` values to an authoring skill using placeholders/skill
directory names, with no table-specific (C086/retail_store_sales) stage assignment
inlined.

**Acceptance Scenarios**:

1. **Given** the current/next stage is stage `<stage_key>`, **When** the card renders,
   **Then** it names the authoring skill from the cross-walk row for `<stage_key>`.
2. **Given** the cross-walk table, **When** it is reviewed, **Then** it contains only
   generic `<stage_key>` -> `<skill>` rows and cites C086/retail_store_sales only as a
   filled instance, never as a baked-in assignment.

### Edge Cases

- **All seven stages `pass`**: card reports "all stages pass -- no next artifact"; no
  invented next step beyond Publish Ready.
- **No `readiness-status.yaml`**: "no readiness file for `<table>`"; no invented state.
- **Malformed / partial `readiness-status.yaml`**: "readiness file incomplete:
  `<file>`" for the affected fields; missing statuses are NOT guessed.
- **`current_stage` disagrees with the per-stage statuses** (e.g. `current_stage`
  points past a non-pass stage): the Compass SURFACES the conflict as a flag and does
  NOT resolve it; the next artifact is still computed from the FIRST non-pass stage in
  pipeline order.
- **A `pass` stage with empty `evidence[]`**: surfaced as "pass without evidence", an
  explicit flag; never hidden.
- **An `evidence[]` reference whose file is absent on disk**: rendered marked
  "referenced file not found"; never dropped, never replaced with an invented one.
- **A downstream stage recorded `pass` while an upstream stage is not `pass`**: the
  card SURFACES the ordering conflict as a flag and still treats the FIRST non-pass
  stage (in pipeline order) as the current position; it never presents a downstream
  stage as reachable on the strength of an out-of-order `pass`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Compass MUST read exactly ONE table's
  `mappings/<table>/readiness-status.yaml` (ADR 0004 canonical location) and render a
  single-table orientation card. It reads that one file; it opens no DB connection and
  runs no validator.
- **FR-002**: The card MUST render the recorded `current_stage` VERBATIM as the
  "you are here" position. It MUST NOT recompute or upgrade the stage.
- **FR-003**: The card MUST compute the "next artifact" as the artifact of the FIRST
  non-pass stage in the fixed seven-stage pipeline order (Source Ready -> Mapping Ready
  -> Silver Ready -> Gold Ready -> Semantic Model Ready -> Dashboard Ready -> Publish
  Ready). It MUST NOT present any stage later than the first non-pass stage as
  reachable (readiness-pipeline ordering: no stage is entered before the prior stage is
  `pass`).
- **FR-004**: When all seven stages are `pass`, the card MUST report "all stages pass
  -- no next artifact" and name no further authoring skill.
- **FR-005**: The card MUST name the authoring skill for the next stage using a GENERIC
  stage -> authoring-skill cross-walk keyed by `<stage_key>`. The cross-walk MUST be
  generic (placeholder/skill-directory rows), never baking in a table-specific stage
  assignment (Principle VII).
- **FR-006**: The card MUST surface, for the current/next stage, the recorded
  `blocking_reasons[]` VERBATIM as STOP rows. It MUST NOT clear, resolve, or rephrase a
  blocker.
- **FR-007**: The card MUST flag "approval not recorded" for the next stage ONLY when
  BOTH hold: (a) that stage's `docs/readiness/<stage>-ready.md` "Required owner /
  approval" field declares an approver IS required, AND (b) no matching `approvals[]`
  entry exists. Where the stage doc declares no required approver, an empty
  `approvals[]` is NORMAL and MUST NOT be flagged. The Compass reads the requirement
  from the stage doc; it NEVER decides the requirement itself and NEVER infers,
  establishes, or back-fills an approver (Principle V; no-self-approval).
- **FR-008**: The Compass MUST NEVER populate an approval, clear a blocker, advance a
  stage, write a `pass`, or edit `readiness-status.yaml` or any per-table artifact. It
  is read-only: after a run, `git status` shows zero modified files (renders,
  never re-derives).
- **FR-009**: The Compass MUST NOT emit a numeric health / percent-ready / confidence /
  maturity score (hard rule #9). Orientation is the recorded stage + the next artifact
  + explicit status + evidence + blockers. A score request MUST be DECLINED, citing
  `docs/readiness/readiness-model.md` "No fake confidence".
- **FR-010**: Every rendered value MUST trace to a recorded source field copied
  VERBATIM (the `current_stage`, each stage `status`, each `evidence[]` entry, each
  `blocking_reasons[]` entry, each `approvals[]` entry) or to a committed doc field
  (the stage doc's "Required owner / approval"). A rendered value with no traceable
  source is a defect. The Compass synthesizes no line number, anchor, status, or
  approver the source does not record.
- **FR-011**: When a required input is absent, the Compass MUST surface the gap as a
  gap and never fabricate it: missing file -> "no readiness file for `<table>`";
  malformed/partial file -> "readiness file incomplete: `<file>`" for the affected
  fields; empty `evidence[]` on a `pass` stage -> "pass without evidence" flag; an
  `evidence[]` reference whose file is absent -> "referenced file not found".
- **FR-012**: The Compass MUST surface, never resolve, any conflict it detects
  (`current_stage` disagreeing with per-stage statuses; an out-of-order `pass`; an
  approval referencing a `not_started` stage). It is a lens, not an arbiter
  (Principle V; surface, never bury).
- **FR-013**: The card MUST NOT be a new gate. The gate exit code remains the authority
  (Principle I); the Compass reads readiness state to orient and reports -- it never
  becomes an enforcement mechanism, never adds a `retail check` rule, and never blocks.
- **FR-014**: The four Principle-V human seams (grain/uniqueness, PII publish-safety,
  business rollup/segment, product identity) MUST be surfaced ONLY as recorded STOP
  rows (from `blocking_reasons[]` / the stage doc's required-owner field). The Compass
  MUST NEVER propose, pick, assert, or resolve any of them. See Clarifications --
  these are reserved for a human and left as [NEEDS CLARIFICATION] markers.
- **FR-015**: The MVP deliverables MUST be docs/template/skill ONLY (Principle VIII;
  hard rule #8): (1) a generic single-table orientation card template
  `templates/first-hour-compass.md` (mirroring `templates/readiness-view.md`); (2) a
  read-only skill `.claude/skills/first-hour-compass/SKILL.md` (mirroring the
  readiness-viewer read-only contract); (3) a usage+boundary doc
  `docs/tools/first-hour-compass.md` (mirroring `docs/tools/readiness-viewer.md`); (4)
  the generic stage -> authoring-skill cross-walk table authored within those
  artifacts. No runtime validator, no DB connection, no live recompute in this slice.
- **FR-016**: The proposed `next_step.py` resolver/scaffolder MUST be DEFERRED and
  ENUMERATED-not-built. This slice adds the seam (docs/template/skill), not a code
  executor. The spec MUST record `next_step.py` as an optional future additive
  read-only slice only.
- **FR-017**: All authored artifacts MUST be generic (Principle VII): `<table>` /
  `<stage_key>` / `<skill>` placeholders; C086 / retail_store_sales cited ONLY as a
  filled instance, never inlined (no billing codes, no segments, no PII column names,
  no per-table grain key). ASCII only, UTF-8 no BOM (`--` and `->`, no glyphs).

### Key Entities *(include if feature involves data)*

- **readiness-status.yaml (Core Authority input, read-only)**: the per-table state the
  Compass reads -- `current_stage`, `stages.<stage>.{status, evidence[],
  blocking_reasons[]}`, `approvals[]`, `next_action`. Canonical location
  `mappings/<table>/readiness-status.yaml` (ADR 0004). The Compass never writes it.
- **Orientation card (rendered output)**: the single-table you-are-here view --
  current stage, next stage, next artifact, authoring skill, STOP rows (blockers +
  approval-required flags), conflicts. Every field traces to a recorded source.
- **Stage -> authoring-skill cross-walk (generic mapping)**: seven `<stage_key>` ->
  `<skill>` rows naming the authoring skill that produces each stage's artifact.
  Generic; C086 cited only as a filled instance.
- **Stage gate doc (`docs/readiness/<stage>-ready.md`, read-only)**: the per-stage gate
  + "Required owner / approval" field the cross-walk and the approval-flag rule read.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any single table with a well-formed `readiness-status.yaml`, the
  Compass renders the correct current stage, the correct next artifact (the artifact of
  the first non-pass stage in pipeline order), and the correct authoring skill for that
  stage in 100% of cases -- every value traceable to a recorded source field.
- **SC-002**: The Compass never presents a downstream stage as reachable when an
  upstream stage is not `pass`: in 100% of inputs, the named next artifact belongs to
  the FIRST non-pass stage in the fixed seven-stage order.
- **SC-003**: The Compass produces zero writes: after any run, `git status` shows zero
  modified `readiness-status.yaml` files and zero modified per-table artifacts, and
  zero `approvals[]` entries added.
- **SC-004**: The Compass emits zero numeric readiness/confidence/percent-ready scores;
  a score request is declined and the explicit statuses + next artifact are returned
  instead (hard rule #9).
- **SC-005**: All authored artifacts are generic: a reviewer confirms zero
  worked-example specifics (billing codes, segments, PII column names, per-table grain
  keys) are inlined; C086 / retail_store_sales appear only as cited filled instances
  (Principle VII).
- **SC-006**: A new-table author, given only the Compass card for their table, can name
  their current stage, their next artifact, and the authoring skill to use -- without
  reading all seven stage docs.

## Assumptions

- The Compass mirrors the shipped readiness-viewer's read-only contract, discovery, and
  honest-state rules; it introduces no new input, no new measurement, and no new
  pipeline (Principle VIII).
- The seven-stage pipeline order is fixed and authoritative from
  `docs/readiness/readiness-pipeline.md` (a stage is entered only when the prior stage
  is `pass`).
- The "next artifact" for a stage is the artifact that stage's
  `docs/readiness/<stage>-ready.md` gate expects (the per-stage evidence/artifact the
  author must produce). The Compass names it from the stage doc; it does not invent an
  artifact.
- The generic stage -> authoring-skill cross-walk maps each stage to one of the
  existing authoring skill directories
  (`retail-onboard-table`, `source-mapping`, `retail-build-warehouse`,
  `retail-semantic-check`, `dashboard-design`, `powerbi-dashboard-design`,
  `retail-orchestrate`); the exact per-stage assignment is authored generically in the
  MVP artifacts and is subordinate to the roadmap/human decision on roadmap position.
- C086 / retail_store_sales is the only filled `readiness-status.yaml` instance today;
  it is cited as an example, never baked into the generic template or cross-walk
  (Principle VII).
- `next_step.py` does not exist and is out of scope for this slice (deferred, additive,
  read-only if ever built).

## Clarifications

The following are reserved for a human decision and are intentionally NOT answered in
this spec. The four Principle-V human seams are hard carve-outs (the Compass surfaces
the recorded STOP only; it never proposes or resolves them). The roadmap-position and
MVP-scope items are resolved in Session 2026-07-01 below where an advisor default is
appropriate; the Principle-V seams remain open.

### Session 2026-07-01

Advisor-resolved (recommended answers, reasoning, reversibility recorded). These do
NOT touch the four Principle-V seams below, which stay open.

- **Q1 -- Roadmap position (Impact: high, Uncertainty: high)**: Does the Compass enter
  the roadmap with an F-number in this slice? **Recommended answer: NO -- ship as an
  idea-bank-sourced spec with no invented F-number; roadmap admission (and its
  stage/layer) is deferred to a human roadmap-owner decision.** Reasoning: the idea has
  no F-row and the idea-bank is explicitly not the roadmap; the shipped readiness-viewer
  sibling itself carries a real F-number (F026) assigned by a human, not self-minted.
  Inventing an F-number here would fabricate roadmap provenance. The spec proceeds as a
  Product Module / read-only surface with roadmap position left OPEN. Reversibility:
  easy (a human can assign an F-number later without changing any artifact).
- **Q2 -- MVP scope: docs-card vs next_step.py (Impact: high, Uncertainty: low)**: Is
  the MVP the thin docs-card slice, or does it include the `next_step.py`
  resolver/scaffolder? **Recommended answer: docs-card only (template + skill + tools
  doc + generic cross-walk); `next_step.py` deferred and enumerated-not-built.**
  Reasoning: Principle VIII / hard rule #8 (static-first; automate only after artifacts
  prove useful) and the idea itself flags the thin docs-card as the cheaper first
  slice. A code executor is a later additive read-only slice, not the seam. Reversibility:
  easy (the deferred resolver can be added later without reworking the docs artifacts).
- **Q3 -- Generic cross-walk per-stage assignment (Impact: medium, Uncertainty: medium)**:
  How concrete may the stage -> authoring-skill cross-walk be without violating
  Principle VII? **Recommended answer: the cross-walk maps each `<stage_key>` to a named
  authoring SKILL DIRECTORY (a generic capability, e.g. mapping_ready -> source-mapping),
  which is generic kit structure, NOT a table-specific assignment; it MUST NOT inline any
  one table's stage values, grain key, segment, or PII columns.** Reasoning: naming which
  skill authors which stage is generic repo architecture (the same for every table);
  Principle VII forbids only baking in a specific TABLE's data/choices. Reversibility:
  easy (cross-walk rows are editable docs). This resolves the business rollup/segment and
  product-identity concerns at the cross-walk level; the per-table SEAMS themselves stay
  open below.
- **Q4 -- Next-artifact resolution under a recorded conflict (Impact: medium,
  Uncertainty: low)**: When `current_stage` disagrees with the per-stage statuses, which
  drives the "next artifact"? **Recommended answer: the FIRST non-pass stage in fixed
  pipeline order drives the next artifact; the `current_stage`/status disagreement is
  ALSO surfaced as a conflict flag but is never silently reconciled.** Reasoning: pipeline
  ordering (no stage entered before the prior is `pass`) is the authority; honoring a
  `current_stage` that skips a non-pass upstream stage would present an unreachable stage
  (violating readiness-pipeline ordering + Principle V surface-never-resolve). Already
  encoded in FR-003 and FR-012; recorded here for traceability. Reversibility: easy.

The four Principle-V human seams below are HARD CARVE-OUTS. Ruled 2026-07-01 (human
ratifier, recorded per-session override): each is confirmed to the conservative
surface-only posture -- the Compass RE-PRESENTS the recorded STOP and never asserts,
picks, embeds, or clears. This confirms the boundary; it does not answer the underlying
business judgment (which stays the analyst's per-table call).

- **Grain / uniqueness seam** -- RULED: confirmed. The Compass only re-presents the
  recorded grain `blocking_reason`; it never proposes, picks, or asserts a grain.
- **PII publish-safety seam** -- RULED: confirmed. The Compass only surfaces the recorded
  publish-safety blocker / approval requirement; it never asserts a column is publish-safe.
- **Business rollup / segment seam** -- RULED: confirmed. The stage -> authoring-skill
  cross-walk stays generic and embeds no rollup/segment assumption.
- **Product identity seam** -- RULED: confirmed. The cross-walk embeds no product-identity
  assumption.
