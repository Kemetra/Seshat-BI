# Feature Specification: Evidence Pack Generator -- assemble the full late-stage evidence pack across all upstream artifacts

**Feature Branch**: `022-evidence-pack-generator`  **Roadmap feature**: F028
(Numbering note: the roadmap F-number is the authoritative identity; the spec-dir
number is the next free on-disk slot. Here dir 022 == F028. When dir number and
F-number disagree, the roadmap F-number wins.)

**Created**: 2026-06-25   **Status**: Shipped (evidence-pack-generator skill landed; spec authored no runtime Python by design)

**Input**: "A product module that ASSEMBLES a single readable evidence pack for any
table or report reaching late readiness stages. The pack has 10 fixed sections
(01-source-profile .. 10-release-notes), each composed from EXISTING committed
evidence. It invents nothing: any missing source becomes a blocker, every section
links back to its source artifact, and the pack MUST NOT make a publish-ready claim
unless publish_ready is pass with a named human approval. It consumes the shipped
F013 BI Handoff Pack as section 08; it never redefines it."

## Why this feature exists

By the time a table or report reaches the late readiness stages (Semantic Model
Ready -> Dashboard Ready -> Publish Ready), its evidence is real but SCATTERED:
the source profile lives with the onboarding artifacts, the map summary in
`source-map.yaml`, the decisions in `assumptions.md`, the contracts under
`mappings/<table>/metrics/`, the validation results in the recorded `retail check`
/ `retail validate` output, the semantic summary in the F010 check, the dashboard
plan in the F011 design, the handoff bundle in F013, the caveats in
`data-issues.md`, and the cross-time reconciliation in the F015 ledger. A reviewer
or data-owner about to authorize publish has no single legible place to SEE all of
it at once, with each claim traceable to its source.

The Evidence Pack Generator is the COMPOSER that assembles those scattered, already
-committed artifacts into one ordered, readable pack of 10 fixed sections. It is the
automation that FILLS the bundle -- it does not originate the evidence and it does
not own any truth. Every section points back at the artifact it summarizes; any
section whose source is missing or unfilled is recorded as a BLOCKER, never papered
over with invented content. The pack surfaces the publish-ready decision; it never
makes it.

## What this feature is NOT (the scope wall)

- **NOT a truth-creator.** It writes DERIVED evidence only -- a composed pack that
  summarizes and links existing artifacts. It does not define business meaning,
  approve a metric or mapping, grant any approval, move a readiness stage to `pass`,
  or publish a report. (Core Authority rule binding all features.)
- **NOT a replacement for F013.** F013 (shipped) is the consumer handoff TEMPLATE;
  this feature CONSUMES F013's filled output and embeds it as section 08. It never
  re-authors or redefines the handoff pack. (See scope-delta section.)
- **NOT an approval recorder.** F028 READS and SURFACES the `publish_ready` approval
  from `readiness-status.yaml`; it never writes one. The approval is owned by the
  Core Authority artifacts (recorded via F013 / publish-ready.md).
- **NOT a validator or a new gate.** It runs no new check, adds no `retail check`
  rule, and defines no new readiness stage. It composes the results other tools
  already recorded.
- **NOT a publisher.** No workspace publish, no Power BI MCP / connection, no PBIP
  authoring, no Fabric deploy. That is F016 (parked, gated on semantic-model-ready,
  execution-only, last).
- **NOT runtime code in this slice.** This is a planning-only spec batch: the 5
  spec-kit files are the entire deliverable now. The generator skill + its docs +
  its templates are ENUMERATED as future outputs, not built here.
- **NOT a confidence score.** Readiness is expressed as the four explicit statuses
  (`not_started` / `blocked` / `warning` / `pass`) + `evidence[]` + `blocking_reasons[]`.
  The pack never emits a fabricated health/confidence number (hard rule #9).

## Relationship to shipped F013 (scope delta)

F013 (BI Handoff Pack, shipped commit `f00ff13`, on-disk dir 014) and F028 both
"compose existing evidence," so the boundary must be stated sharply and repeated:

- **F013 = the handoff TEMPLATE.** It defines the SHAPE and content of the one
  bundle a BI consumer receives at Publish Ready: metric contracts, readiness
  scorecard, reconciliation evidence, known data issues, data dictionary, and the
  recorded publish approval. It is a copy-per-table template + a human-walked
  completeness checklist at `templates/handoff/bi-handoff-pack.md` and
  `templates/handoff/handoff-review-checklist.md`. F013 OWNS the recorded publish
  approval (the named human sign-off in `readiness-status.yaml` `approvals[]`).

- **F028 = the GENERATOR / COMPOSER.** It assembles the FULL 10-section evidence
  pack across ALL upstream stages (source -> publish) and EMBEDS F013's filled
  handoff bundle as section 08. F028 is the automation that FILLS a pack; it is not
  a competing bundle.

- **The relationship is one-directional: F028 consumes F013, never redefines it.**
  Section 08 of the pack REFERENCES / INCLUDES the table's filled
  `templates/handoff/bi-handoff-pack.md` instance and links to it. F028 never edits
  that instance, never re-authors the handoff template, and never records the
  publish approval (F013 / Core Authority does that). If the F013 handoff is missing
  or incomplete, F028 records section 08 as a BLOCKER -- it does not synthesize a
  substitute handoff.

In one line: **F013 is what a complete handoff looks like; F028 is the tool that
gathers everything (including that handoff) into one traceable pack and tells you,
section by section, what is present and what is still blocking.**

## Architecture (planning posture)

Category: **Product Module, artifact-writing (derived evidence only).** When built,
the module composes COMMITTED evidence into a pack -- it never creates truth, never
reads a live database or PBIP model, and never publishes. Planned shape (future,
not created this slice):

- A **skill** `.claude/skills/evidence-pack-generator/SKILL.md` -- the invoke-and-
  compose verb: read the upstream artifacts, render the 10-section pack index +
  summary, record per-section status (present / blocker / warning), and STOP.
- A **tool doc** `docs/tools/evidence-pack-generator.md` -- what the module does,
  the 10-section contract, the source-artifact map, the allowed/forbidden ops, and
  the missing-source-is-a-blocker rule.
- Two **templates**: `templates/evidence-pack-index.md` (the ordered 10-section
  index, each row pointing at a source artifact) and `templates/evidence-pack-summary.md`
  (the one-page readiness summary that surfaces, not decides, the publish state).

This slice writes ONLY the 5 spec-kit files. The four artifacts above are
enumerated as PLANNED outputs (see plan.md "Repository artifacts this feature PLANS
(not created)").

## Clarifications

### Session 2026-06-25

- Q: Should the base pack contract include an optional numeric "N of 10 sections present" completeness tally? -> A: No -- the base contract carries the four-status per-section record plus rolled-up blockers only; no count is emitted (safest distance from hard rule #9). A labeled factual tally may be added later as a reversible-easy addition, never as confidence.
- Q: Where do per-table FILLED evidence packs live -- `mappings/<table>/` or a new top-level `packs/` dir? -> A: `mappings/<table>/` -- reuse the established per-table working-set home (ADR 0003 / constitution v1.5.0); no new top-level directory.
- Q: What is the pack export format for this contract -- markdown only, or markdown plus an additional rendered form? -> A: Markdown only (the index + summary) is the base contract; any additional rendered form is a later additive slice (hard rule #8, Principle IX).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compose the 10-section pack from existing evidence (Priority: P1)

A reviewer is preparing a table that has reached Dashboard Ready / Publish Ready for
a data-owner sign-off. They invoke the generator, which reads each upstream artifact
and assembles the ordered 10-section pack: 01-source-profile, 02-source-map-summary,
03-assumptions-and-decisions, 04-metric-contracts, 05-validation-summary,
06-semantic-model-summary, 07-dashboard-summary, 08-handoff-pack, 09-known-limitations,
10-release-notes. Every section summarizes and links back to its committed source.

**Why this priority**: This is the feature. Without one ordered, traceable pack, the
late-stage evidence stays scattered and a reviewer cannot see the whole picture in
one place. This is the MVP: the 10-section index + summary composed from existing
artifacts.

**Independent Test**: For a generic `<schema>.<table>` whose upstream artifacts are
committed, run the generator and confirm the pack renders all 10 sections in order,
each section links to the exact source artifact path it summarizes, and no section
contains content that is not derivable from a committed source.

**Acceptance Scenarios**:

1. **Given** a generic table with all 10 upstream sources committed, **When** the
   pack is composed, **Then** all 10 sections render in fixed order and each links
   back to its source artifact path.
2. **Given** the composed pack, **When** any section is inspected, **Then** its
   content is a SUMMARY or REFERENCE of an existing committed artifact -- it adds no
   data, metric, decision, or confidence number that the source does not contain.
3. **Given** the pack index, **When** a reviewer follows any section link, **Then**
   it resolves to a real committed artifact (or to a recorded blocker for a missing
   source) -- never to fabricated or placeholder evidence presented as real.

---

### User Story 2 - Missing or unfilled source becomes a blocker, never invented (Priority: P1)

A reviewer composes the pack for a table whose semantic-model summary (section 06)
has not yet been produced, and whose reconciliation ledger (feeding section 10) is
unfilled. The generator does NOT invent those sections. It records each missing
source as an explicit BLOCKER in that section and rolls the blockers up into the
pack summary; the pack cannot claim "complete."

**Why this priority**: Co-equal P1 with US1. A composer that fills gaps with invented
content is worse than no composer -- it ships unstated fiction to a decision-maker.
The "missing -> blocker, never invented" rule is the feature's integrity guarantee.

**Independent Test**: Remove (or leave unfilled) one section's source artifact, run
the generator, and confirm that section is recorded as a `blocked` status with a
`blocking_reasons[]` entry naming the missing source, the pack summary reflects the
blocker, and NO substitute content is synthesized for that section.

**Acceptance Scenarios**:

1. **Given** section N's source artifact is missing or unfilled, **When** the pack
   is composed, **Then** section N is recorded as `blocked` with a blocking reason
   naming the missing source, and the pack summary cannot read "complete."
2. **Given** a section source that exists but is in a `warning` state upstream,
   **When** the pack is composed, **Then** section N carries that `warning` verbatim
   and the warning does NOT auto-promote to `pass`.
3. **Given** any missing source, **When** the pack is composed, **Then** the
   generator NEVER fabricates that section's content -- the gap is recorded, not
   filled (no invented profile rows, contracts, totals, or summaries).

---

### User Story 3 - Surface (never assert) the publish-ready state (Priority: P1)

A data-owner reads the pack to decide whether to authorize publish. The pack's
summary SURFACES the `publish_ready` state and the recorded approval (if any) read
from `readiness-status.yaml`. The pack MUST NOT print a publish-ready claim unless
`publish_ready: pass` with a named human approval is recorded. The generator never
writes the approval and never moves a stage.

**Why this priority**: Co-equal P1. The late-stage pack exists to support a publish
decision; if it could assert "ready to publish" without the recorded `pass` +
approval, it would manufacture authority the module does not have (Core Authority /
Principle V). This is the feature's hardest guardrail.

**Independent Test**: Compose the pack for (a) a table with `publish_ready: pass` +
a recorded approval and (b) a table at `dashboard_ready: pass` but
`publish_ready: blocked`. Confirm (a) surfaces the recorded approval and may state
publish-ready, and (b) shows publish-ready as `blocked` with the upstream reason --
never a publish-ready claim. Confirm the generator wrote no approval and changed no
stage in either case.

**Acceptance Scenarios**:

1. **Given** `publish_ready: pass` with a named approval in `readiness-status.yaml`,
   **When** the pack is composed, **Then** the summary surfaces the recorded approval
   (owner + date) and cites `readiness-status.yaml` as the source.
2. **Given** `publish_ready` is not `pass`, **When** the pack is composed, **Then**
   the summary shows publish-ready as `blocked`/`warning` with the upstream blocking
   reasons -- it MUST NOT print a publish-ready claim.
3. **Given** any pack composition, **When** it completes, **Then** the generator has
   written NO approval, moved NO readiness stage to `pass`, and edited NO source
   artifact -- it only wrote the derived pack.

---

### User Story 4 - In-progress pack at an earlier late stage (Priority: P2)

A team wants the pack as a living artifact from Semantic Model Ready onward, not only
at the final gate. The generator composes an IN-PROGRESS pack: the sections whose
sources exist render and link; the sections not yet produced are recorded as
blockers; the summary states the table's current stage. The pack is useful as a
work-in-progress checklist without ever claiming a stage it has not reached.

**Why this priority**: P2. US1-US3 already deliver the pack at the final gate; this
story makes the pack valuable earlier as a progress view. It is additive, not
required for the MVP, and it must not weaken the publish-ready guardrail.

**Independent Test**: Compose the pack for a table at `semantic_model_ready: pass`
with downstream sections (07 dashboard, 08 handoff) not yet produced; confirm the
present sections render, the absent sections are blockers, the summary states the
current stage honestly, and no downstream stage is claimed as reached.

**Acceptance Scenarios**:

1. **Given** a table at an intermediate late stage, **When** the pack is composed,
   **Then** present sections render and absent downstream sections are blockers --
   the pack is explicitly marked in-progress.
2. **Given** the in-progress pack, **When** the summary is read, **Then** it states
   the current stage and the blocking reasons for the unreached stages -- it claims
   no stage the table has not reached.

---

### Edge Cases

- **A source artifact exists but is the blank template, not a filled instance.** The
  generator treats an unfilled template as a missing source -> blocker; it does not
  summarize placeholder text as if it were real evidence.
- **F013 handoff (section 08) is incomplete.** Section 08 is recorded as a blocker;
  the generator does not synthesize a substitute handoff or re-author F013's template.
- **Two upstream sources disagree (e.g. a contract count differs between the metric
  store and the semantic-model summary).** The generator surfaces both with their
  source links and records the discrepancy as a `warning` for human resolution
  (Principle V); it does not pick a winner or reconcile silently.
- **A numeric confidence/health score is requested for the pack.** Refused. The pack
  carries the four explicit statuses + evidence + blockers only (hard rule #9).
- **Live data or a PBIP model is requested as a section source.** Out of scope: the
  generator reads only committed artifacts. Any live signal must already be recorded
  as committed evidence (e.g. by `retail validate`) before the pack can cite it.
- **Worked-example (C086 / retail_store_sales) specifics.** The generator, its
  templates, and its docs stay generic; worked-example values live only in that
  example's own filled artifacts (Principle VII).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The module MUST compose a pack of exactly 10 fixed, ordered sections:
  01-source-profile, 02-source-map-summary, 03-assumptions-and-decisions,
  04-metric-contracts, 05-validation-summary, 06-semantic-model-summary,
  07-dashboard-summary, 08-handoff-pack, 09-known-limitations, 10-release-notes.
- **FR-002**: Each section MUST be COMPOSED from an existing committed source
  artifact and MUST link back to that artifact's repo-relative path. The pack
  composes; it invents no section content.
- **FR-003**: Any section whose source artifact is missing, unfilled, or still a
  blank template MUST be recorded as `blocked` with a `blocking_reasons[]` entry
  naming the missing source. The generator MUST NOT fabricate substitute content.
- **FR-004**: Section 08 MUST embed / reference the table's FILLED F013 handoff pack
  (`templates/handoff/bi-handoff-pack.md` instance). The generator MUST NOT
  re-author, edit, or redefine the F013 handoff; if it is incomplete, section 08 is
  a blocker. (Scope delta vs F013.)
- **FR-005**: The pack summary MUST surface the `publish_ready` status and recorded
  approval READ from `readiness-status.yaml`. The module MUST NOT write an approval,
  MUST NOT move any readiness stage to `pass`, and MUST NOT edit any source artifact.
- **FR-006**: The pack MUST NOT print a publish-ready CLAIM unless `publish_ready:
  pass` with a named human approval is recorded in `readiness-status.yaml`.
- **FR-007**: Each section's status MUST be one of the four explicit statuses
  (`not_started` / `blocked` / `warning` / `pass`) with `evidence[]` and
  `blocking_reasons[]`. A `warning` MUST NOT auto-promote to `pass`. NO numeric
  confidence/health score is emitted anywhere (hard rule #9). The base contract
  emits NO completeness count either; the four-status per-section record plus the
  rolled-up blockers convey completeness. (Clarifications 2026-06-25.)
- **FR-008**: The pack MUST be composable as an IN-PROGRESS artifact from an
  intermediate late stage: present sections render, absent ones are blockers, and
  the summary states the current stage without claiming an unreached one.
- **FR-009**: Where two upstream sources disagree, the module MUST surface BOTH with
  their source links and record the discrepancy as a `warning` for human resolution
  (Principle V); it MUST NOT silently reconcile or choose a winner.
- **FR-010**: The module MUST read ONLY committed artifacts. It MUST NOT read a live
  database or PBIP model, MUST NOT call the Power BI execution adapter (F016), and
  MUST NOT publish or deploy.
- **FR-011**: The module, its skill, its doc, and its templates MUST stay generic --
  no C086 / retail_store_sales specifics; the worked example is cited by reference
  only (Principle VII).
- **FR-012**: All delivered artifacts MUST be ASCII, UTF-8 without BOM, and use
  short repo-relative paths within the Windows `MAX_PATH` budget (Principle IX).
- **FR-013**: The module MUST NOT add a `retail check` rule, define a new readiness
  stage, or alter any gate. It composes results other tools already recorded.

### Key Entities *(include if feature involves data)*

- **Evidence Pack** (`templates/evidence-pack-index.md` filled instance): the
  ordered 10-section index for a `<schema>.<table>`. Each row: section id + title,
  status (one of four), source artifact path(s), and a one-line summary or blocker.
  Composes; invents nothing.
- **Pack Summary** (`templates/evidence-pack-summary.md` filled instance): the
  one-page readiness summary that surfaces the current stage, the `publish_ready`
  state, the recorded approval (if any), and the rolled-up open blockers. Surfaces;
  decides nothing.
- **Section source artifacts** (referenced, not created here): source-profile.md
  (01), source-map.yaml (02), assumptions.md / unresolved-questions.md / ADRs (03),
  `mappings/<table>/metrics/` contracts (04), recorded `retail check` / `retail
  validate` + F012 roll-up (05), F010 / `retail semantic check` output (06), F011 /
  F011A dashboard design (07), F013 filled handoff pack (08), `data-issues.md` +
  caveats (09), F015 reconciliation ledger + F014 drift + `approvals[]` (10).
- **`readiness-status.yaml`** (Core Authority artifact, read-only here): the source
  of stage status and recorded approvals the pack summary surfaces.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can obtain one ordered 10-section pack for a generic table
  in which every present section links back to a committed source artifact, with zero
  invented data, metrics, decisions, or confidence numbers.
- **SC-002**: 100% of the pack's sections resolve to either an existing committed
  source artifact OR an explicit recorded blocker -- there is no section the pack
  originates from nothing.
- **SC-003**: For any missing/unfilled source, the corresponding section is recorded
  as `blocked` (not fabricated) and the pack summary cannot read "complete."
- **SC-004**: The pack prints a publish-ready claim only when `publish_ready: pass`
  with a named recorded approval exists; in every other case it shows the upstream
  blocking reasons -- verified across a `pass` and a non-`pass` table.
- **SC-005**: The generator writes only the derived pack -- across all runs it has
  recorded NO approval, moved NO stage to `pass`, and edited NO source artifact
  (including the F013 handoff).
- **SC-006**: The delivered skill + doc + templates contain no worked-example
  specifics, add no `retail check` rule, read no live DB/PBIP, and pass the kit's
  docs conventions (ASCII, UTF-8 no BOM, short repo-relative paths, links resolve).

## Human approval boundary

The named human (data-owner / governance reviewer) decides whether to authorize
publish. The generator only SURFACES the recorded `publish_ready` state and approval;
it never grants, writes, or implies an approval, and it never moves a readiness stage
to `pass`. Discrepancies between upstream sources, grain/PII/rollup ambiguities, and
sentinel-vs-null questions surfaced in the pack are stop-and-ask items for the human
(Principle V) -- the pack records them, it does not resolve them.

## Allowed operations

- READ committed upstream artifacts (the 10 section sources) and `readiness-status.yaml`.
- SUMMARIZE and LINK each section to its committed source.
- WRITE the DERIVED evidence pack (index + summary) as a composed artifact.
- RECORD per-section status (present / `warning` / `blocked`) with evidence + blockers.
- EMBED / reference the F013 filled handoff pack as section 08.
- SURFACE the recorded `publish_ready` status and approval (read-only).

## Forbidden operations

- Inventing or fabricating any section's content when its source is missing.
- Writing, granting, or implying a publish approval; moving any readiness stage to `pass`.
- Editing, re-authoring, or redefining any source artifact (including the F013 handoff).
- Emitting a numeric confidence / health score (hard rule #9).
- Reading a live database or PBIP model; calling the Power BI execution adapter (F016).
- Publishing / deploying to any workspace or Fabric.
- Adding a `retail check` rule, defining a new readiness stage, or altering a gate.
- Silently reconciling disagreeing sources or choosing a winner (Principle V).
- Inlining C086 / retail_store_sales specifics into the generic artifacts.

## Evidence required

- Per section: the source artifact path(s) it summarizes, its status (one of four),
  `evidence[]`, and `blocking_reasons[]` for any gap.
- Pack summary: the current readiness stage, the `publish_ready` status, the recorded
  approval (owner + date) when present, and the rolled-up open blockers -- each
  traceable to `readiness-status.yaml` or a section source.
- Provenance: every claim in the pack links back to a committed artifact; nothing is
  asserted without a source link.

## Readiness stage affected

**Publish Ready** (stage 7 of 7) primarily; the pack may be composed in-progress from
**Semantic Model Ready** (stage 5) onward (US4). The generator advances NO stage; it
composes evidence and surfaces the state the Core Authority artifacts already record.

## Dependencies

- **Depends on F024** (Companion Tools Architecture) for the product-module posture,
  the Core-vs-Module authority rule, and the allowed/forbidden-ops vocabulary.
- **Overlaps and CONSUMES F013** (BI Handoff Pack, shipped) as section 08 -- never
  redefines it.
- **Consumes outputs of** F008 (Grain Confidence + Mapping Diff Reviewer; the
  source-map.yaml it reviews feeds section 02), F009/F010 (metric contracts + semantic
  model), F011/F011A (dashboard design), F012 (data-quality roll-up for validation
  summary), F014 (drift), and F015 (reconciliation ledger, feeding release notes).
- **Reads** the Core Authority `readiness-status.yaml` (and `mappings/<table>/`
  artifacts) for stage status and approvals.

## Non-goals

- Building the generator runtime, skill, doc, or templates in this slice (planning only).
- Recording or owning the publish approval (F013 / Core Authority owns it).
- Running any validation, defining any gate, or adding a `retail check` rule.
- Any live DB / PBIP read, publish, or Power BI execution (F016, parked).
- Any numeric confidence/health scoring of the pack.

## Assumptions

- **Pack artifacts live under `templates/` and `docs/tools/`.** Consistent with the
  existing template home (alongside `templates/handoff/`) and the tool-doc home.
  (Auto-decision; reversible-easy.)
- **Per-table FILLED packs live under `mappings/<table>/`.** Reuse the established
  per-table working-set home (ADR 0003 / constitution v1.5.0) rather than a new
  top-level `packs/` dir, keeping all per-table derived evidence in one folder.
  (Clarifications 2026-06-25; reversible-easy -- a path move.)
- **Pack export format is markdown only.** The base contract is the markdown index
  + summary; any rendered form is a later additive slice (hard rule #8).
  (Clarifications 2026-06-25.)
- **The 10-section contract is fixed and ordered.** The section list and order are a
  stable contract so packs are comparable across tables. (Auto-decision.)
- **Upstream artifacts are committed before a pack is composed.** The pack assumes
  filled instances exist; if not, the gap is recorded as a blocker, not waited on.
  (Auto-decision.)
- **F013's filled handoff pack is the section-08 source.** The generator references
  that filled instance; it does not re-run the handoff checklist. (Auto-decision.)
- **The `publish_ready` approval is read from `readiness-status.yaml` `approvals[]`.**
  Reusing the existing approval record; no new approval store. (Auto-decision.)

## Deferred decisions

- **Optional numeric "completeness" indicator.** RESOLVED (Clarifications
  2026-06-25): the base contract emits NO count -- the four-status per-section
  record plus rolled-up blockers convey completeness. A labeled factual tally
  ("N of 10 sections present") may be added later as a reversible-easy addition,
  and if added MUST read as a tally, never as confidence (hard rule #9).
- **Per-table pack storage path.** RESOLVED (Clarifications 2026-06-25): filled
  packs live under `mappings/<table>/` -- the established per-table working-set
  home (ADR 0003 / constitution v1.5.0). No new top-level `packs/` dir. (Cheaply
  reversible -- a path move.)
- **Pack export format.** RESOLVED (Clarifications 2026-06-25): markdown only (the
  index + summary) is the base contract. Any additional rendered form is a later
  additive slice (hard rule #8, Principle IX).

## See also

- F013 BI Handoff Pack -- `specs/014-bi-handoff-pack/spec.md` (section 08 source;
  scope delta above).
- F024 Companion Tools Architecture -- `specs/018-companion-tools-architecture/`
  (product-module posture + Core-vs-Module authority).
- Readiness spine -- `docs/readiness/readiness-model.md`, `docs/readiness/publish-ready.md`.
- Section sources (shipped): F008/F009/F010/F011/F011A/F012/F014/F015 specs under
  `specs/`; `templates/handoff/bi-handoff-pack.md`; `templates/readiness-status.yaml`.
