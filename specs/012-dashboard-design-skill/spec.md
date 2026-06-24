# Feature Specification: dashboard design skill -- design a report FROM approved metric contracts

**Feature Branch**: `012-dashboard-design-skill` (work on `main` per session convention; located via `.specify/feature.json`)

**Created**: 2026-06-24

**Status**: Draft

**Input**: "Roadmap F011 (Layer 6 Dashboard & Delivery). Advances readiness stage: Dashboard Ready. An agent SKILL that designs a dashboard FROM approved metric contracts. HARD GATE (rule #5): no approved metric contracts -> no design; this feature is explicitly gated on F009 (metric-contract-store) and F010 (semantic-model-readiness). Design = layout/visual/metric-binding guidance authored by the agent; it does NOT publish and does NOT invoke pbi-cli/PBIP authoring automation (hard rule #6 -- F016 is last). Docs/skill-first (#8). Generic (#7)."

## Why this feature exists

The readiness spine defines Stage 6, **Dashboard Ready** (`docs/readiness/dashboard-ready.md`):
a report is designed AGAINST approved metric contracts -- never before them. The stage
doc exists, but there is no agent verb that runs it. The `retail-orchestrate` conductor
sequences the medallion phases and parks at the BI half of Phase 7 with no skill to
design a dashboard from the contracts a passing `semantic_model_ready` produced.

This feature fills that hole with a **pure design-guidance skill**. It reads the
approved metric contracts (F009) and the governed PBIP model (F010), then authors
reviewable design guidance -- a layout, a visual list, and a visual->contract binding
map -- so every visual traces to a contract that already exists. It STOPS at the
authoring boundary: it does not publish, does not open Power BI Desktop, and does not
call pbi-cli/PBIP authoring automation (that is F016, the last and gated adapter).

It is the agent expression of roadmap hard rule 5 ("No dashboard design before metric
contracts") and hard rule 6 ("No pbi-cli/PBIP automation before semantic-model
readiness"): the gate is what makes design safe to automate, and the author/execute
boundary is what keeps this feature out of the publishing engine's territory.

## The hard gate (the load this feature respects)

- **No contracts -> no design (rule 5, Principle V/IV posture).** The skill MUST verify
  that `semantic_model_ready` is `pass` for the table/subject area before authoring any
  design. "Pass" means: approved metric contracts exist (F009) and the governed PBIP
  model binds each measure to one (F010). If `semantic_model_ready` is not `pass`, the
  skill records `dashboard_ready: not_started` (the prior stage is not `pass`) and
  STOPS. It never invents a metric to fill a visual.
- **Design = authoring guidance, not publishing (rule 6, Principle II posture).**
  Authoring design text -- a layout plan, a visual list, a visual->contract binding map,
  and (optionally) a blank PBIR scaffold the human fills -- is in-scope: no side effects,
  no DB connection, no Desktop, the same category as `source-mapping` authoring
  `mappings/` and `retail-build-warehouse` authoring `warehouse/migrations/*.sql`.
  EXECUTING the design -- generating the PBIR report, publishing to a workspace, calling
  pbi-cli/PBIP authoring automation -- is the deferred adapter seam (F016). The skill
  authors, runs static `retail check` on any committed report text, and STOPS.

## Architecture (a pure skill; no codegen, no authoring engine, no CLI)

The skill is `.claude/skills/dashboard-design/SKILL.md` -- agent-procedure text; the
agent is the runtime (same posture as `source-mapping`, `retail-build-warehouse`, and
the other governed verbs). There is NO codegen engine that emits a `.pbir` report, NO
report template that bakes in visuals, and NO `retail design` CLI subcommand -- by
design.

Deciding reason: the value of this stage is the JUDGMENT -- which contract answers which
business question, what visual type fits the contract's grain, how to lay out the page,
and confirming every visual maps to an approved contract with no orphan. That judgment
is what a human reviewer must sign off (the design review). A codegen engine could only
emit boilerplate page chrome while the binding decisions stay hand-authored, and it
would put the kit one step into the F016 publishing engine it is forbidden to enter at
this stage (rule 6). The agent authoring design guidance by reading the contracts is the
right grain (Principle VIII docs-first; roadmap rule 8).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Design a dashboard from approved contracts (Priority: P1)

Given a subject area whose `semantic_model_ready` is `pass` (approved metric contracts
exist and the PBIP model binds to them), an analyst asks the agent to design the
dashboard. The skill reads the approved contracts, authors a layout plan + a visual list
+ a visual->contract binding map where every visual maps to exactly one approved
contract, records `dashboard_ready: warning` (design authored, awaiting review sign-off),
and STOPS before any publishing.

**Why this priority**: binding every visual to an approved contract -- with no metric
invented at design time and no orphan visual -- is the core value of Stage 6 and the
thing the design review signs off.

**Independent Test**: given a generic fixture subject area with `semantic_model_ready:
pass` and N approved contracts, the skill produces a binding map of exactly the visuals
it lists, each citing one approved contract by name; an auditor confirms zero visuals
cite a non-existent or non-approved contract, and zero approved contracts are silently
dropped without a recorded reason.

**Acceptance Scenarios**:

1. **Given** `semantic_model_ready: pass` with approved contracts, **When** the skill
   runs, **Then** it authors the layout plan, the visual list, and a visual->contract
   binding map (every visual -> one approved contract), records `dashboard_ready:
   warning`, and STOPS without publishing or calling any authoring automation.
2. **Given** a visual that has no backing approved contract, **When** the skill drafts
   it, **Then** it does NOT emit the visual -- it records the gap as a blocking reason
   ("orphan visual: no approved contract for <question>") and STOPS.
3. **Given** a committed PBIR report exists for the subject area, **When** the skill
   runs, **Then** `retail check` (R1) stays exit 0 -- the report references the model by
   relative path, not an absolute/remote ref.

### User Story 2 - Refuse to design when the gate is not pass (Priority: P1)

Given a subject area whose `semantic_model_ready` is NOT `pass` (no approved contracts,
or the model does not bind to them), the skill refuses to author any design. It records
`dashboard_ready: not_started` (prior stage not `pass`) with the concrete blocking
reason and STOPS. This is the hard gate (rule 5) and is as important as the happy path.

**Why this priority**: the gate is the feature. Designing a dashboard before its
contracts exist is exactly the failure rules 5 and 8 forbid; refusing is the load-bearing
behavior.

**Independent Test**: given a fixture subject area with `semantic_model_ready` in each
non-`pass` status (`not_started`, `blocked`, `warning`), the skill authors NO design
artifact and the readiness status carries the matching blocking reason; an auditor
confirms no layout/visual/binding file was written.

**Acceptance Scenarios**:

1. **Given** `semantic_model_ready: not_started` or `blocked`, **When** the skill runs,
   **Then** it authors no design, records `dashboard_ready: not_started` with the
   blocking reason, and STOPS.
2. **Given** approved contracts do not yet exist (F009/F010 unbuilt for this subject
   area), **When** the skill runs, **Then** it STOPS with "no approved metric contracts
   -- gate rule 5" and never invents a metric to design against.
3. **Given** `semantic_model_ready: warning` (model clean but contract review not signed
   off), **When** the skill runs, **Then** it STOPS -- a `warning` prior stage does not
   authorize design (the contract approval is the thing being awaited).

### User Story 3 - Stop at the design review and the publish boundary (Priority: P2)

The skill authors the design and then HARD-STOPS at two boundaries it must not cross:
the human design-review sign-off (the visual->contract binding is approved by the BI
report owner -- a Principle V judgment call) and the publish boundary (no pbi-cli/PBIP
automation, no workspace publish -- rule 6, F016). It records the next allowed action
(get the design review signed) and never promotes `dashboard_ready` to `pass` itself.

**Why this priority**: a `pass` requires an owner-recorded approval (the design review);
the skill must surface that boundary, not cross it. It also must never step into the F016
publishing engine.

**Independent Test**: across all runs, the skill never writes `dashboard_ready: pass`
without an `approvals[]` entry, never opens a DB/Desktop connection, and never emits a
pbi-cli/PBIP authoring command; an auditor greps the skill's outputs and finds no publish
verb and no self-granted `pass`.

**Acceptance Scenarios**:

1. **Given** the design is authored and `retail check` is clean, **When** the skill
   finishes, **Then** it records `dashboard_ready: warning` + `next_action: "get the
   design review (visual->contract binding) signed off by the BI report owner"`, never
   `pass`.
2. **Given** any point in the procedure, **When** the skill would need to publish or
   author the PBIR via automation, **Then** it STOPS and names F016 as the owner of that
   step (rule 6).
3. **Given** the design review is signed off (an `approvals[]` entry exists), **When**
   the readiness status is updated by the reviewer (not the skill), **Then**
   `dashboard_ready` may become `pass` and `next_action` points to Stage 7
   (`publish-ready.md`).

### Edge Cases

- **A contract exists but is not approved.** The skill treats only APPROVED contracts as
  bindable (an approval recorded against the contract). An unapproved-but-present contract
  is not a valid binding target -> the visual is an orphan -> STOP.
- **More approved contracts than visuals.** Not every contract must appear on the page,
  but a dropped contract MUST be recorded with a reason (e.g. "covered by Stage 7 handoff
  pack, not the dashboard") so the drop is a decision, not an omission.
- **A contract whose grain does not fit any sensible visual** (e.g. a row-level contract
  asked to be a single KPI card). The skill records the grain mismatch as a design note
  (a `warning`-class item), proposes the grain-appropriate visual, and never silently
  mis-binds.
- **PBIR references the model by absolute/remote path.** R1 fails -> the report is
  `blocked` -> STOP; the relative-reference fix is the human's, surfaced as a blocking
  reason.
- **Subject area spans multiple tables/models.** The skill binds visuals only to
  contracts within the governed model(s) that are `semantic_model_ready: pass`; a visual
  needing an out-of-model metric is an orphan -> STOP.
- **No business questions supplied.** Design is question-driven; with no questions the
  skill asks for them (a Principle V judgment input) rather than inventing a generic page.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The skill MUST verify `semantic_model_ready` is `pass` for the subject area
  before authoring any design. If it is not `pass`, the skill MUST author no design,
  record `dashboard_ready: not_started`, and STOP (hard gate, rule 5).
- **FR-002**: The skill MUST bind every proposed visual to exactly one APPROVED metric
  contract (F009), citing the contract by name. A visual with no backing approved
  contract MUST NOT be emitted; the gap MUST be recorded as a blocking reason (orphan
  visual).
- **FR-003**: The skill MUST NOT invent, define, or alter a metric at design time. It
  binds only to contracts that already exist and are approved; metric definition is
  F009's job, not this skill's.
- **FR-004**: The skill MUST author its output as reviewable design guidance -- a layout
  plan, a visual list, and a visual->contract binding map -- and MUST NOT publish, open a
  DB/Desktop connection, or call pbi-cli/PBIP authoring automation (rule 6; F016 owns
  that step).
- **FR-005**: When a committed PBIR report exists for the subject area, the skill MUST
  confirm `retail check` (R1) stays exit 0 -- the report references the governed model by
  a relative path, not an absolute/remote ref.
- **FR-006**: The skill MUST record `dashboard_ready` state per the readiness model
  (`not_started` / `blocked` / `warning` / `pass`) with `evidence[]` and
  `blocking_reasons[]`, and MUST NOT fabricate a confidence score.
- **FR-007**: The skill MUST NOT write `dashboard_ready: pass` itself. A `pass` requires
  an owner-recorded design-review approval in `approvals[]`; absent that, the highest the
  skill records is `warning` with `next_action` = get the design review signed.
- **FR-008**: The skill MUST stop at Principle V judgment calls -- which business question
  each visual answers, whether a grain mismatch is acceptable, and the design-review
  sign-off -- surfacing them for a human rather than self-answering.
- **FR-009**: The skill MUST be generic (rule 7): no C086/pharmacy specifics in the skill
  text or any committed template; worked values belong only in a per-subject-area
  instance, and C086 is an example, not the schema.
- **FR-010**: The skill MUST record the next allowed action when it stops -- get the
  design review signed (toward `pass`), or resolve the named blocking reason (toward
  unblock) -- consistent with `readiness-model.md`.
- **FR-011**: When more approved contracts exist than visuals on the page, each dropped
  contract MUST be recorded with a reason; an approved contract MUST NOT be silently
  omitted.
- **FR-012**: The skill's outputs MUST be ASCII, UTF-8 without BOM, and MUST NOT bake in
  any real connection host or secret (consistent with the repo secret rules and G6).

### Key Entities

- **Approved metric contract (input, from F009)**: a committed metric definition -- name,
  grain, formula intent, owner -- with a recorded approval. The only valid binding target
  for a visual. This feature consumes it; it does not define it.
- **Governed PBIP model (input, from F010)**: the semantic model whose measures bind to
  approved contracts, `semantic_model_ready: pass`. The model the dashboard references by
  relative path.
- **Layout plan (output)**: the page/section structure -- which business questions the
  page answers, in what reading order -- authored as reviewable text.
- **Visual list (output)**: each proposed visual -- its type, the question it answers, and
  the single approved contract it binds to.
- **Visual->contract binding map (output)**: the committed note proving each visual maps
  to one approved contract (no orphan visual) -- the artifact the design review signs off.
- **Dashboard readiness record (output)**: the `dashboard_ready` stage entry in the
  table's/subject area's readiness status -- status + evidence + blocking reasons +
  next_action (never a fabricated score).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a subject area with `semantic_model_ready: pass`, 100% of visuals the
  skill emits cite exactly one approved metric contract by name; 0 visuals cite a
  non-existent, non-approved, or invented metric.
- **SC-002**: For every non-`pass` `semantic_model_ready` status, the skill authors 0
  design artifacts and records the matching blocking reason -- the hard gate (rule 5)
  holds in 100% of gated cases.
- **SC-003**: Across all runs the skill emits 0 publish/PBIP-authoring commands and opens
  0 DB/Desktop connections -- the author/publish boundary (rule 6) holds 100% of the time.
- **SC-004**: When a committed PBIR exists, `retail check` (R1) stays exit 0 (relative
  model reference) in 100% of design runs that touch report text.
- **SC-005**: The skill writes `dashboard_ready: pass` in 0% of runs lacking an
  `approvals[]` design-review entry -- no self-granted pass.
- **SC-006**: 0 C086/pharmacy specifics appear in the skill text or any committed template
  (generic, rule 7); a reviewer scanning the skill finds only generic placeholders.
- **SC-007**: Every dropped approved contract (more contracts than visuals) carries a
  recorded reason -- 0 silent omissions.

## Assumptions

- **F009 (metric-contract store) and F010 (semantic-model-readiness) are the upstream
  dependencies.** This feature consumes their outputs (approved contracts + a bound
  governed model) and is `not_started` for any subject area until they exist and
  `semantic_model_ready` is `pass`. C086 is the first worked example, not the schema.
- **"Pass" of the prior stage is the entry condition** (`readiness-pipeline.md` hard
  gate): the skill reads the readiness status, it does not re-derive contract approval.
- **The design review (visual->contract binding sign-off) is the BI report owner's** --
  recorded in `approvals[]` as `{stage: dashboard_ready, owner: <bi-report-owner>, at:
  <date>}`. The skill surfaces it; it does not perform it (Principle V).
- **The deferred publishing/authoring engine is F016** (pbi-cli/PBIP adapter, the last
  and gated feature). This skill stops at its boundary and never enters it (rule 6).
- **Reuse over new surface (Principle II, YAGNI):** a pure skill, no codegen engine, no
  report template baking in visuals, no `retail design` CLI subcommand -- consistent with
  the all-skills verb architecture and roadmap rule 8 (docs/templates first).
- **`retail check` rule R1** already validates the relative model reference in committed
  PBIR; this feature relies on it rather than adding a new validator (no new gate).
- **Generic templates carry no pharmacy specifics** (rule 7); worked values live only in
  a per-subject-area instance under the table's mapping/readiness working set.
