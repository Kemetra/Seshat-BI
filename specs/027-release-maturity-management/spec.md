# Feature Specification: Release & Maturity Management -- evidence-gated release notes + an honest maturity ladder for the kit

**Feature Branch**: `027-release-maturity-management`  **Roadmap feature**: F033
(Numbering note: the roadmap F-number is the authoritative identity; the spec-dir number
is the next free on-disk slot. For this batch F024=spec 018, F025=019, F026=020, F027=021,
F028=022, F029=023, F030=024, F031=025, F032=026, F033=spec 027. When the dir number and
the F-number disagree, the roadmap F-number wins. This feature: dir 027 = roadmap F033.)

**Created**: 2026-06-25   **Status**: Planned (spec only -- no runtime code this slice)

**Input**: "Roadmap F033 (Maintenance Automation / Official Workflow Skill, per the F024
companion-tools taxonomy). A release + maturity management system for the Tower BI Agent
Kit. It produces (a) per-release RELEASE NOTES -- what became possible, what changed,
readiness stages affected, new modules/adapters, known limitations, migration notes, next
best slice -- and (b) an evidence-gated MATURITY LADDER (Level 0 docs-only .. Level 6
official Power BI execution adapter) whose current rung is determined by which evidence
ALL exists, never by marketing. It CONSUMES evidence from F028 (evidence pack) and F032
(compatibility matrix); it does not re-measure them. It advances NO readiness stage (a
product-level release process). No release may claim production capability without
evidence; the ladder is honestly pinned at Level 2-3 today with Levels 4-6 marked NOT
BUILT. Generic (Principle VII), ASCII-only (Principle IX), no fake confidence (hard rule
#9)."

## Why this feature exists

The kit ships in slices (F005-F015 shipped; F016 parked; the F024-F033 companion-tools
batch in flight). Each slice changes WHAT THE KIT CAN DO -- a new skill, a new template, a
new adapter seam -- but the kit has no durable, reviewable record of "what became possible
in this release, and how mature is the capability". Today that answer lives only in commit
messages and the roadmap's delivered ledger; a BI consumer or a maintainer cannot read one
artifact that says "release N made X possible, it is proven on two tables, dbt/Dagster/PBI
execution are NOT yet built". This feature is that record: per-release **release notes**
plus an **evidence-gated maturity ladder**.

The load-bearing reason it must exist as a governed artifact (not a marketing changelog) is
honesty. A maturity claim is exactly where a tool is tempted to round "two worked examples"
up to "production ready". The kit's own no-fake-confidence rule (hard rule #9) forbids that.
So the maturity ladder is defined as an **evidence-gated milestone ladder** -- structurally
the same kind of artifact as the seven numbered readiness stages: each rung has a binary
"this evidence exists or it does not" test, and the kit's level is the HIGHEST rung whose
required evidence ALL exists. It is not a percentage, not a score, not a confidence number.

## What this feature is NOT (the scope wall)

Stated up front so the spec cannot drift:

- **The maturity ladder is NOT a confidence score.** Levels 0-6 are evidence-gated
  milestones (like the seven readiness stages), each with a binary evidence test. The
  generator MUST NOT emit a percentage, a 0-100 health number, an average, or any number
  that reads as confidence (hard rule #9). A rung is reported as "achieved (evidence: ...)"
  or "not achieved (missing: ...)" -- never "73% mature".
- **It claims NO capability without evidence.** A release note may state "X became
  possible" ONLY when the evidence for X exists and is cited. "Production ready" / "GA" /
  "enterprise grade" claims are forbidden unless an evidence rung backs them. Today no rung
  backs a production claim, so the kit makes none.
- **It re-measures NOTHING.** It CONSUMES the F028 evidence pack and the F032 compatibility
  matrix as inputs. It does not run `retail check` / `retail validate`, does not profile a
  source, does not open a DB connection, does not read `powerbi/`. If an input is missing,
  it records "evidence not available" -- it does not fabricate the measurement.
- **It is NOT self-approving.** The generator DRAFTS release notes and ASSESSES the rung
  from evidence; a named human release owner APPROVES the release and CONFIRMS the level.
  The skill cannot self-declare a level bump, self-declare production readiness, or publish.
- **It advances NO readiness stage and adds NO gate.** Release/maturity is a product-level
  process orthogonal to the per-table readiness spine. It adds no `retail check` rule, no
  CLI verb, no validator (Principle VIII / roadmap rule #8 / YAGNI).
- **Generic.** C086 and retail_store_sales are cited as the kit's real track record
  (allowed: they are the evidence FOR the ladder, not baked-in generic logic). The
  templates carry no per-table specifics (Principle VII).

## Relationship to shipped features (scope delta)

Release/maturity is PRODUCT-level and cross-release. It sits ABOVE the per-table features
and consumes their outputs; it never reproduces them.

| Feature | Its scope | This feature's distinct scope |
|---------|-----------|-------------------------------|
| F012 Data Quality Control Room | a point-in-time, cross-TABLE roll-up of findings + blockers | release/maturity is cross-RELEASE and about CAPABILITY, not per-table data quality |
| F013 BI Handoff Pack | a per-table evidence BUNDLE for a BI consumer of one subject area | release notes are a per-RELEASE record for a consumer/maintainer of the whole kit |
| F015 Reconciliation Ledger | durable cross-TIME state of DATA reconciliation results | the maturity ladder is durable cross-time state of KIT CAPABILITY, not data recon |
| F028 Evidence Pack (dep) | assembles the durable evidence bundle for a slice/release | release/maturity CONSUMES that pack as the evidence behind each rung + each note |
| F032 Compatibility Matrix (dep) | which adapter/kit versions interoperate | release notes CITE the matrix for "what changed / migration notes"; never recompute it |
| F024 Companion Tools Architecture (dep) | the taxonomy that classifies this as Maintenance Automation / Official Workflow Skill | this feature is one instance OF that taxonomy; it inherits the Core-Authority rules from F024 |

The discriminator: F012/F013/F015 answer "where is THIS table / THIS data". F033 answers
"what can the KIT do as of release N, and how mature -- by evidence -- is that capability".

## Architecture (planning posture: pure skill + two generic templates + an output dir)

Consistent with F012/F013 and roadmap rule #8: the system is **agent-procedure text; the
agent is the runtime**. Planned shape (FUTURE outputs, enumerated not created here):

- `.claude/skills/release-notes-generator/SKILL.md` -- the authoring + assessment verb. It
  reads the evidence (F028 pack + F032 matrix + the delivered roadmap ledger), DRAFTS a
  release note from `templates/release-notes.md`, ASSESSES the current rung from
  `templates/maturity-report.md`, and STOPS for the named release owner to approve.
- `templates/release-notes.md` -- the generic per-release note shape (the seven required
  content blocks below).
- `templates/maturity-report.md` -- the generic point-in-time ladder snapshot shape (the
  seven rungs, each with its binary evidence test + achieved/not-achieved + cited evidence).
- `docs/releases/` -- the durable home for filled, approved release notes + maturity
  snapshots, one per release (the analogue of the roadmap's delivered ledger, per release).

NO new Python, NO new `retail` subcommand, NO codegen: assessment is a read-fan-out over
already-committed evidence plus a binary rung test -- exactly the read-and-present work the
agent already does in F012. A CLI would add the kit's first release tool, parse the evidence
into code, and track the evidence schema -- maintenance for ~zero gain at this cadence.

## User Scenarios & Testing *(mandatory)*

Actors: the **release owner** (named human who approves a release and confirms its level),
the **maintainer** (drafts/reviews notes), the **BI consumer** (reads "what became
possible"), and the **agent** (drafts notes + assesses the rung from evidence, then stops).

### User Story 1 - Generate evidence-backed release notes for a milestone (Priority: P1)

A maintainer asks "generate the release notes for this milestone". The skill reads the
delivered evidence (the F028 evidence pack for the slice, the F032 compatibility matrix, the
roadmap ledger + commit refs) and DRAFTS a release note containing all seven required
blocks: what became possible, what changed, readiness stages affected, new modules/adapters,
known limitations, migration notes, next best slice. Every "became possible" claim cites the
committed evidence behind it. The draft is unapproved until the release owner signs off.

**Why this priority**: this is the feature's first half -- the per-release record the kit
lacks. Without it there is no durable "what became possible in release N".

**Independent Test**: given a slice with an F028 evidence pack present, the skill emits one
release note filling all seven blocks, where every "what became possible" line names the
committed evidence (file/commit) supporting it, "known limitations" lists at least the
unbuilt rungs, and the note is marked `status: draft -- awaiting release-owner approval`.

**Acceptance Scenarios**:

1. **Given** an evidence pack + matrix for a milestone, **When** the skill runs, **Then** it
   produces one release note with all seven blocks filled and every capability claim cited.
2. **Given** a capability with no supporting evidence, **When** the skill drafts the note,
   **Then** that capability is NOT listed under "what became possible"; if relevant it is
   listed under "known limitations -- not yet evidenced", never asserted.
3. **Given** the draft is produced, **When** a reviewer reads its status line, **Then** it
   reads `draft -- awaiting release-owner approval`; the skill has approved nothing.

### User Story 2 - Assess the kit's maturity level honestly, from evidence (Priority: P1)

A maintainer asks "what maturity level is the kit at?". The skill produces a maturity report:
the seven rungs (L0 docs-only .. L6 official Power BI execution adapter), each with its
binary evidence test and an achieved/not-achieved verdict citing the evidence (or naming the
missing evidence). The reported level is the HIGHEST rung whose required evidence ALL exists.
Levels above that are explicitly NOT achieved with the missing evidence named.

**Why this priority**: this is the feature's second half and its honesty core. An
evidence-gated ladder is the only maturity claim the no-fake-confidence rule permits.

**Independent Test**: run the assessment against today's repo. Assert: L1 achieved (>=1
worked example -- c086), L2 achieved (>=2 worked examples -- c086 + retail_store_sales), L3
reported with its caveat (repeatable silver/gold proven for those two tables; generic
repeatability beyond two is the next evidence), and L4 (dbt adapter), L5 (Dagster
orchestration), L6 (official Power BI execution adapter) each reported NOT ACHIEVED with the
missing artifact named. No rung is reported as a percentage; no production claim is made.

**Acceptance Scenarios**:

1. **Given** two worked examples on disk, **When** the skill assesses, **Then** L2 is
   "achieved" citing both worked examples and the kit's reported level is at least 2.
2. **Given** no dbt adapter, no Dagster project, and no Power BI execution adapter exist,
   **When** the skill assesses, **Then** L4/L5/L6 are each "not achieved" with the exact
   missing artifact named, and the reported level does NOT include them.
3. **Given** a request to "give the kit a maturity score out of 100", **When** the skill
   runs, **Then** it DECLINES, cites no-fake-confidence (hard rule #9), and returns the
   rung verdicts + cited evidence instead.

### User Story 3 - The honesty guard: no marketing, no self-approval, no unbacked claim (Priority: P1)

The system never asserts a capability the evidence does not back, never emits a confidence
number, never bumps a level or approves a release on its own. A release moving from `draft`
to `approved` requires a named release owner; a level the evidence does not support is
refused; a "production ready" claim with no backing rung is refused.

**Why this priority**: this is the constitutional guardrail -- the rule that makes the whole
feature trustworthy. Release/maturity is the single place an agent is most tempted to
overclaim, so the refusal behavior must be specified and testable.

**Independent Test**: (a) ask the skill to mark a release `approved` with no named owner --
it refuses and points at the human approval boundary. (b) ask it to report Level 4 with no
dbt adapter present -- it refuses and names the missing evidence. (c) ask it to call the kit
"production ready" -- it refuses, citing no rung backs the claim. In all three, `git status`
shows no maturity snapshot self-promoted and no release self-approved.

**Acceptance Scenarios**:

1. **Given** a request to approve a release, **When** no named release owner is supplied,
   **Then** the skill leaves status `draft` and states approval is a human action
   (Core Authority / Principle V).
2. **Given** a request to report a level above the evidence-supported rung, **When** the
   skill runs, **Then** it refuses and names the missing evidence for that rung.
3. **Given** a request for a marketing claim ("enterprise grade", "GA", a numeric score),
   **When** the skill runs, **Then** it refuses and returns only evidence-backed rung
   verdicts and cited capability claims.

### Edge Cases

- **No evidence pack yet for a slice**: the release note records "evidence not available --
  cannot assert capability" rather than inventing a claim; the note stays `draft`.
- **A rung's evidence is partial** (e.g. one worked example complete, the second mid-build):
  the rung is "not achieved" with the missing piece named -- never rounded up.
- **F028 / F032 not yet authored** (they are sibling specs in this batch): the skill
  references them by feature id and role and records "consumed input not yet available"
  rather than fabricating the pack's or matrix's contents.
- **Conflicting evidence** (the matrix says an adapter version interoperates but no adapter
  exists in-repo): the skill surfaces the conflict as a finding and does NOT resolve it by
  picking one (Principle V posture).
- **A release owner over-claims** (asks to confirm Level 5 with no Dagster project): the
  skill records the request, refuses the unbacked level, and leaves the decision blocked --
  it recommends, the human decides, but the evidence test is non-negotiable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Plan (do NOT create this slice) a pure skill
  `.claude/skills/release-notes-generator/SKILL.md` (ASCII, UTF-8 no BOM, valid
  frontmatter). NO new Python, NO new `retail` subcommand, NO codegen, NO new gate.
- **FR-002**: Plan TWO distinct generic templates: `templates/release-notes.md` (per-release
  note) and `templates/maturity-report.md` (point-in-time ladder snapshot). They are
  separate artifacts with separate purposes and MUST NOT be merged. ASCII, UTF-8 no BOM,
  placeholders only, no per-table specifics (Principle VII).
- **FR-003**: Plan a durable output home `docs/releases/` for filled, approved release notes
  + maturity snapshots, one set per release.
- **FR-004**: A release note MUST contain all seven blocks: (1) what became possible, (2)
  what changed, (3) readiness stages affected, (4) new modules/adapters, (5) known
  limitations, (6) migration notes, (7) next best slice. Each "what became possible" claim
  MUST cite the committed evidence behind it.
- **FR-005**: The maturity ladder MUST define exactly seven evidence-gated rungs with a
  binary evidence test each: L0 docs only; L1 one worked example; L2 two worked examples; L3
  repeatable silver/gold (proven for the worked tables); L4 dbt transformation adapter; L5
  Dagster orchestration; L6 official Power BI execution adapter. The reported level is the
  HIGHEST rung whose required evidence ALL exists.
- **FR-006**: No-fake-confidence guard: the maturity report MUST NOT emit a percentage,
  0-100 score, average, or any number that reads as confidence. Each rung is reported
  achieved/not-achieved with cited or missing evidence. If asked for a numeric maturity
  score, the skill DECLINES and cites hard rule #9. (Numbered rungs are milestones, like the
  seven readiness stages -- not a score.)
- **FR-007**: Honest current-state requirement: the assessment MUST report the kit at its
  true evidence-backed rung today -- L2 achieved (c086 + retail_store_sales), L3 reported
  with its repeatability caveat -- and L4/L5/L6 each NOT achieved with the missing artifact
  named. No release note may claim a capability whose rung is not achieved.
- **FR-008**: No-unbacked-capability guard: a "what became possible" / "production ready" /
  "GA" / "enterprise grade" claim is permitted ONLY when an evidence rung backs it. With no
  backing rung the claim is forbidden and the skill refuses.
- **FR-009**: Consume-never-re-measure: the skill MUST source its evidence from the F028
  evidence pack, the F032 compatibility matrix, and the committed roadmap ledger + commit
  refs. It MUST NOT run `retail check` / `retail validate`, profile a source, open a DB
  connection, or read `powerbi/`. Missing input -> "evidence not available", never fabricated.
- **FR-010**: Human approval boundary: a release moves `draft -> approved` ONLY with a named
  release owner recorded as `approvals[]`; the skill DRAFTS + ASSESSES but never self-approves
  a release, never self-confirms a level, never publishes (Core Authority / Principle V).
- **FR-011**: Evidence traceability: every capability claim and every rung verdict MUST be
  attributable to a named committed source (file/commit, or the cited F028/F032 artifact). A
  claim or verdict with no traceable source is a defect.
- **FR-012**: Conflict surfacing: when inputs disagree (e.g. matrix asserts an adapter
  version but no adapter exists in-repo), the skill MUST surface the conflict as a finding
  and MUST NOT silently resolve it (Principle V posture).
- **FR-013**: Append an `## Orchestration` pointer so `retail-orchestrate` can invoke the
  generator as the product-level read after a milestone; the generator reads evidence and
  drafts -- it advances no readiness stage.

### Key Entities

- **Release-notes-generator skill** (planned): the draft-and-assess verb; the agent is the
  runtime. Draft-and-stop; never self-approves, never re-measures, never publishes.
- **Release note** (`templates/release-notes.md`, filled under `docs/releases/`): the
  per-release record with the seven required blocks + a `status` (`draft`/`approved`) +
  `approvals[]`.
- **Maturity report** (`templates/maturity-report.md`, filled under `docs/releases/`): the
  point-in-time ladder snapshot -- seven rungs, each with its binary evidence test +
  verdict + cited/missing evidence + the reported level.
- **Consumed inputs (existing/sibling, unchanged)**: F028 evidence pack, F032 compatibility
  matrix, the delivered roadmap ledger + commit refs. INPUTS only; this feature creates no
  evidence of its own.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The five spec-kit artifacts exist for F033 (spec/plan/tasks + two checklists),
  ASCII + no BOM; they ENUMERATE the four future deliverables and CREATE none of them.
- **SC-002**: The spec defines the maturity ladder as evidence-gated milestones (binary test
  per rung, level = highest all-evidence-present rung) and explicitly forbids any numeric
  maturity score -- reconciled against hard rule #9 in both the spec and governance.md.
- **SC-003**: The spec pins the honest current state: L1/L2 achieved (two worked examples),
  L3 with caveat, L4/L5/L6 NOT achieved with missing artifacts named -- and forbids any
  release note claiming an unachieved capability or production readiness.
- **SC-004**: The spec specifies all seven release-note content blocks as FR-004 with
  evidence-citation required, and keeps `release-notes.md` and `maturity-report.md` as two
  distinct planned templates.
- **SC-005**: The human approval boundary is explicit (release owner approves; the skill
  drafts/assesses only; no self-approval, no self-level-bump, no publish), and the
  consume-never-re-measure boundary (F028/F032 inputs; no `retail check`/`validate`, no DB,
  no `powerbi/` read) is stated -- both carried into governance.md CHK items.

## Human approval boundary

- The agent DRAFTS release notes and ASSESSES the maturity rung from committed evidence.
- A named **release owner** (recorded in `approvals[]`) APPROVES the release (`draft ->
  approved`) and CONFIRMS the reported level. This is a Core-Authority truth-creating act
  the module cannot perform.
- The agent recommends; the human decides. Over-claims (a level the evidence does not back)
  are refused by the evidence test regardless of who asks (Principle V).

## Allowed operations

- READ the F028 evidence pack, the F032 compatibility matrix, the roadmap ledger + commit
  refs, the worked-example docs, and the on-disk presence of adapters/projects.
- DRAFT a release note (all seven blocks) and ASSESS the maturity rung, writing DERIVED,
  reviewable artifacts under `docs/releases/` marked `draft` until a human approves.
- SUMMARIZE and CITE evidence; surface conflicts as findings.

## Forbidden operations

- Emitting a numeric maturity score / percentage / averaged confidence (hard rule #9).
- Claiming a capability, "production ready", "GA", or "enterprise grade" with no backing
  evidence rung (FR-008).
- Reporting a level above the highest all-evidence-present rung (FR-005/FR-007).
- Self-approving a release, self-confirming a level, or publishing (FR-010; Core Authority).
- Re-measuring: running `retail check` / `retail validate`, profiling a source, opening a DB
  connection, or reading `powerbi/` (FR-009).
- Adding a `retail check` rule, a CLI verb, a validator, or any new gate (Principle VIII).
- Baking per-table specifics into the templates (Principle VII).

## Evidence required

- For a "what became possible" claim: the committed file/commit (or the cited F028 pack
  entry) that makes it true.
- For a rung verdict: the artifact whose presence/absence the binary test checks (e.g. for
  L2, two worked-example directories under `mappings/`; for L4, a dbt adapter that does not
  yet exist).
- For `approved` status: a named release owner + date in `approvals[]`.
- For "what changed" / "migration notes": the F032 compatibility matrix rows cited.

## Readiness stage affected

NONE directly. Release & maturity management is a cross-cutting, product-level process; it
rolls up capability across releases and does not enter, gate, or advance any of the seven
per-table readiness stages.

## Dependencies

- **F024 Companion Tools Architecture** -- the taxonomy that classifies this as Maintenance
  Automation / Official Workflow Skill and supplies the Core-Authority module rules. (Hard
  dependency; referenced by id + role, not by internal structure -- sibling spec in flight.)
- **F028 Evidence Pack** -- the evidence bundle this feature consumes for each release note
  and rung verdict. (Consumed input; referenced by id + role.)
- **F032 Compatibility Matrix** -- cited for "what changed" + "migration notes". (Consumed
  input; referenced by id + role.)
- The delivered roadmap ledger (`docs/roadmap/roadmap.md`) + commit refs as the release
  history of record.

## Non-goals

- A numeric maturity/health score or a confidence percentage (DEFERRED with scoring rules;
  hard rule #9).
- A `retail release` CLI / programmatic generator (YAGNI at this cadence; DEFERRED).
- Automated publishing of releases (tags, GitHub releases, package registries) -- the
  generator drafts text; release execution stays a human action.
- Building any of the unbuilt rungs (dbt adapter L4, Dagster L5, Power BI execution L6) --
  those are their own features; this feature only records their absence honestly.
- Marketing copy / changelog automation divorced from evidence.

## Assumptions

- Pure skill + two generic templates + an output dir; the agent is the runtime (same posture
  as F012/F013). No new Python, no CLI, no codegen (YAGNI).
- The kit's true maturity TODAY is L2 achieved (c086 + retail_store_sales worked examples on
  disk) with L3 (repeatable silver/gold) proven for those two tables and generic
  repeatability beyond two tables as the next evidence; L4/L5/L6 are unbuilt. The maturity
  model MUST reflect this and not round up.
- F028 and F032 are sibling specs in this same batch; this spec references them by id + role
  and does not depend on their internal structure being finalized.
- Citing c086 and retail_store_sales as the kit's track record is allowed evidence-citation
  (they are the evidence FOR the ladder), distinct from baking per-table logic into a generic
  template (Principle VII forbids the latter, not the former).

## Deferred decisions (future specs / issues -- recorded, not built)

- **A numeric maturity index / score**: DEFERRED until scoring rules are defined in a
  readiness scoring-rules doc (readiness-model "score is OPTIONAL and DEFERRED"). Until then
  the ladder is rung verdicts + cited evidence only.
- **A `retail release` CLI / programmatic generator**: DEFERRED; if release cadence grows
  past hand-authoring, a read-only generator (still no new validator) could assemble notes.
- **Automated release execution** (git tags, GitHub releases, registry publish): DEFERRED;
  out of scope -- this feature drafts the text a human then publishes.
- **A historical maturity TREND view** (rung over time across releases): DEFERRED; the
  maturity report is a point-in-time snapshot. Durable cross-time state of DATA recon is
  F015's domain; a capability-trend view would be a later product-level slice.

## See also

- The taxonomy + Core-Authority rules: `specs/018-companion-tools-architecture/spec.md`
  (F024). The consumed inputs: `specs/022-evidence-pack-generator/spec.md` (F028),
  `specs/026-adapter-compatibility-matrix/spec.md` (F032).
- The release history of record: `docs/roadmap/roadmap.md` (delivered ledger + commit refs).
- The worked examples that ground the ladder: `docs/worked-examples/c086-pharmacy.md`;
  `mappings/c086/`, `mappings/retail_store_sales/`.
- The model + no-fake-confidence rule: `docs/readiness/readiness-model.md`; hard rule #9.
- The read-and-present sibling it mirrors: `.claude/skills/retail-control-room/SKILL.md`,
  `specs/013-data-quality-control-room/spec.md`. The conductor it plugs into:
  `.claude/skills/retail-orchestrate/SKILL.md`.
- Constitution Principles V (stop at judgment calls), VII (C086 is an example), VIII
  (static-first), IX (secrets/ASCII/no-BOM).
