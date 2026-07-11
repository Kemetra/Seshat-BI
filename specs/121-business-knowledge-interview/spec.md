# Feature Specification: Business Knowledge Interview, Decision Store, and Knowledge Contracts

**Feature Branch**: `121-business-knowledge-interview`

**Created**: 2026-07-11

**Status**: Draft

**Input**: User description: "Create the product-level contract foundation for the agent-guided Database-to-PBIP flow: a Business Knowledge Interview after discovery, a machine-readable project Decision Store with approval metadata, a human-readable interview review artifact, product-level Knowledge Contracts per flow stage, blocking decision gates with pass/warn/blocked verdicts, and integration rules with the existing knowledge and readiness layers. Specify only; do not implement the flow, a PBIP compiler, or any execution surface."

## Overview

### Feature Summary

This feature adds the decision-capture and contract layer that must exist before Seshat BI can safely guide an agent from a discovered database to a PBIP prototype. It introduces four connected capabilities: a **Business Knowledge Interview** that converts database discovery output into targeted business questions; a **project Decision Store** that records every proposed and approved business decision in machine-readable, diffable form; a **human-readable review artifact** that lets a business owner audit interview outcomes without reading YAML; and **Knowledge Contracts** that declare, per flow stage, which knowledge routes are allowed, which decisions block progress, and where each stage must stop and hand off. Unresolved critical decisions produce **blocked** gate verdicts that stop downstream modeling, semantic, dashboard, and PBIP-readiness work.

### Problem Statement

Seshat BI already owns knowledge routing (SQL, DAX, Python, Big-data, Retail KPI), a seven-stage readiness spine, and evidence conventions. What it lacks is a governed place where the *business answers* behind a model live. Today, if an agent discovers a database and starts building, the meaning-critical decisions -- what a KPI means, which columns are PII, what one row of a table represents, how missing financial values are treated -- exist only in conversation. They are not recorded, not approvable, not diffable, and not enforceable. An agent can proceed on an unconfirmed assumption, and nothing downstream can tell an approved fact from a plausible guess. Without this layer, the planned Database-to-PBIP flow would amplify unrecorded assumptions into semantic models and reports.

### Product Goal

Make every meaning-critical decision in the Database-to-PBIP flow **explicit, recorded, human-approved, and enforceable** -- so that downstream stages (Silver/Gold modeling, KPI contracts, DAX, dashboard blueprint, PBIP readiness) can only consume decisions that carry valid approval metadata and evidence, and are truthfully blocked when those decisions are missing.

### Primary Actors

- **Data owner / business owner**: the named human who answers interview questions, approves or rejects critical decisions, and owns PII rulings. Approval authority always traces to a named human with an authority class; the agent never holds it.
- **Implementation agent** (Claude Code / Codex): conducts the interview, proposes decisions with confidence, records outcomes in the Decision Store, generates the review artifact, and obeys gate verdicts.
- **Reviewer / approver**: a human who reads the review artifact and the diffable Decision Store during change review.
- **Seshat governance layer**: the readiness spine, knowledge router, and static checks that consume decision state and enforce gates. It owns pass/block; it never invents answers.

## Clarifications

### Session 2026-07-11

- Q: When an approved decision's cited evidence later changes or goes missing (schema drift), what do dependent gate verdicts become? -> A: Blocked for critical decision types until the owner re-confirms; warn for non-critical decisions.
- Q: Must each critical decision type be approved by a specific authority class? -> A: Yes -- each critical decision type declares the authority class(es) eligible to approve it; an approval from an ineligible class is invalid.
- Q: Can an approved decision be changed after approval? -> A: No -- approved records are immutable; supersession is the only path to change or reverse them.
- Q: Can the owner exclude individual items from a low-risk batch before confirming? -> A: Yes -- item-level exclusion; the remainder is approved in one action and each excluded item becomes an individual pending question.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Answer a Focused Business Interview (Priority: P1)

After database discovery produces a profile (tables, columns, types, candidate grains), a data owner is asked a focused set of business questions -- not one question per column. Obvious low-risk interpretations are presented as a batch for one confirmation; critical decisions (KPI meaning, PII, grain, keys, relationships, missing-value rules for financial fields) are asked individually with profile summaries and masked samples as supporting evidence.

**Why this priority**: The interview is the entry point that produces every decision the rest of the feature stores, reviews, and enforces. Without it there is nothing to govern.

**Independent Test**: Run the interview against a discovery profile from a worked example. Verify that low-risk items arrive as one reviewable batch, critical items arrive as individual questions with masked evidence, and no raw suspected-PII value is displayed.

**Acceptance Scenarios**:

1. **Given** a completed discovery profile for a multi-table source, **When** the interview starts, **Then** questions are grouped into a low-risk batch and individual critical questions, and the total question count is visibly smaller than the column count.
2. **Given** a column suspected to contain PII, **When** the interview presents sample evidence for it, **Then** values are masked by default and the raw values are shown only after an explicit data-owner instruction that is itself recorded as a PII-handling decision scoped to the affected columns.
3. **Given** an ambiguous financial column (for example a price that may be VAT-inclusive), **When** the interview reaches it, **Then** it is asked as an individual critical question with a profile summary, never silently defaulted.
4. **Given** the data owner ends the session early, **When** the interview stops, **Then** every unanswered question is recorded as `pending` or `needs_user_input` and nothing is auto-approved.

---

### User Story 2 - Record Decisions in a Project Decision Store (Priority: P1)

Every interview answer, agent proposal, and owner ruling lands in a machine-readable, project-scoped Decision Store that supports the full decision lifecycle (proposed through approved, rejected, superseded) and separates the agent's confidence from human approval.

**Why this priority**: The store is the single source of truth every other capability projects from. It is co-equal with the interview as the MVP core.

**Independent Test**: Create decision records covering every status and every critical decision type; verify the store round-trips them, rejects records missing required fields, and never treats a high-confidence proposal as approved.

**Acceptance Scenarios**:

1. **Given** an agent proposes a table grain with `confidence: high`, **When** the record is written, **Then** its status is `proposed` and no downstream stage may consume it as approved.
2. **Given** a data owner approves a KPI definition, **When** the approval is recorded, **Then** the record carries approved_by, approved_at, source, evidence, status, confidence, decision_type, and reviewed_scope -- and an approval missing any of these is invalid.
3. **Given** an approved decision is later revised, **When** the new decision is recorded, **Then** the old record becomes `superseded` with a reference from its replacement, and the history remains in the store.
4. **Given** a decision record is malformed or has an unknown status, **When** any consumer reads the store, **Then** the consumer fails closed: the decision is treated as unresolved and affected gates report blocked, never pass.

---

### User Story 3 - Review Interview Outcomes in One Readable Artifact (Priority: P2)

A business owner or reviewer reads a single human-readable review artifact that summarizes what was approved, what is pending, what blocks progress, what was rejected or deferred, how PII is handled, and what the current gate verdict is -- without opening any machine-readable file.

**Why this priority**: Approval is only meaningful if a non-technical owner can see what they approved. This artifact is the audit and review surface for Stories 1-2.

**Independent Test**: Generate the artifact from a Decision Store seeded with decisions in every status; verify each required section is present, accurate, and contains no raw suspected-PII values.

**Acceptance Scenarios**:

1. **Given** a Decision Store with approved, pending, blocking, rejected, and deferred decisions, **When** the review artifact is generated, **Then** it presents each group in its own section together with PII handling, KPI-impacting, grain/relationship, and cleaning/missing-value decisions, the open questions, and the gate verdict.
2. **Given** the Decision Store changes, **When** the artifact is regenerated, **Then** it reflects the store exactly; the artifact holds no state of its own and a stale copy can always be reproduced from the store.
3. **Given** a reviewer reads only the artifact, **When** they look for why a stage is blocked, **Then** the blocking decisions are named concretely with the next question that would unblock each one.

---

### User Story 4 - Route Stages Through Knowledge Contracts (Priority: P2)

An agent entering any stage of the Database-to-PBIP flow consults that stage's Knowledge Contract, which declares the stage's allowed knowledge routes, required inputs and outputs, stop rules, blocking decision categories, handoff target, non-goals, and evidence requirements -- so the agent cannot wander outside the stage's authority.

**Why this priority**: Contracts make the existing routing boundaries enforceable per stage. They depend on the decision vocabulary from Stories 1-2.

**Independent Test**: For each declared stage, verify the contract names its routes and stop rules, and that boundary probes route correctly: a KPI-meaning question inside the DAX stage routes back to Retail KPI knowledge, and a scale-out request without recorded scale evidence routes back to Python.

**Acceptance Scenarios**:

1. **Given** the semantic-model/DAX stage receives a question about what a KPI *means*, **When** the contract is consulted, **Then** the question is routed to Retail KPI knowledge and the DAX stage does not invent the meaning.
2. **Given** a data-processing task with no recorded evidence that the data exceeds single-node capacity, **When** a route is selected, **Then** Python is the route and Big-data is refused until scale evidence is recorded.
3. **Given** a stage's required inputs include an approved decision that is still `pending`, **When** the agent attempts to enter the stage, **Then** the contract's stop rule halts entry and names the unresolved decision.
4. **Given** an execution adapter participates in any stage, **When** its contract is read, **Then** it grants no authority to define meaning, mapping, metrics, semantic logic, or approval.

---

### User Story 5 - Enforce Blocking Gates with Clear Verdicts (Priority: P3)

Anyone (human or agent) can ask whether a requested stage is ready and receive one of three verdicts -- pass, warn, or blocked -- computed from the Decision Store and its evidence, with blocked verdicts naming the concrete unresolved decisions.

**Why this priority**: Verdicts turn stored decisions into enforcement. They are last because they project over everything Stories 1-4 produce.

**Independent Test**: Seed decision states for each blocking rule (pending PII, pending grain, pending KPI meaning, missing evidence, unapproved blueprint) and verify each produces blocked for the correct downstream stages and pass once resolved.

**Acceptance Scenarios**:

1. **Given** a table whose grain decision is `pending`, **When** readiness for Silver/Gold modeling is requested, **Then** the verdict is blocked and names the grain decision.
2. **Given** a KPI whose meaning is unapproved, **When** readiness for KPI contracts, DAX, dashboard design, or PBIP prototype is requested, **Then** each verdict is blocked citing the KPI-meaning decision.
3. **Given** an approved decision whose cited evidence is missing or unresolvable, **When** any dependent verdict is computed, **Then** the approval is treated as invalid and the verdict is blocked, never pass.
4. **Given** all critical decisions for a stage are approved with valid metadata and only non-fatal issues remain (for example an accepted deviation), **When** the verdict is computed, **Then** it is warn -- progress is allowed and the issues are listed.

### Edge Cases

- A critical decision is smuggled into a low-risk batch: batch sets must refuse critical decision types; a batch containing one is invalid as a whole and no member is approved.
- Two decision records cover the same scope with conflicting answers and neither supersedes the other: the conflict is a blocking condition for every stage that consumes that scope until one record supersedes the other.
- Upstream discovery evidence changes after approval (schema drift): the approval is flagged as stale; for critical decision types dependent verdicts become blocked until the owner re-confirms or supersedes the decision, for non-critical decisions the staleness is listed under warn -- never a silent pass.
- The owner declines to decide: the decision is `deferred`; if its decision type is in a blocking category, dependent stages stay blocked -- deferral is not approval.
- A suspected-PII column is ruled "not PII" by the owner: the ruling is itself a recorded critical decision with evidence; until then the column stays masked.
- `needs_sample` cannot be satisfied (no live access): the decision remains `needs_sample` and dependent verdicts report blocked with that reason, never a silent pass.
- The Decision Store is absent or empty: all decision-dependent verdicts truthfully report blocked/not-started; nothing infers a pass from absence.
- An agent writes an approval on its own authority: the record lacks a valid named-human approver and is invalid; the never-self-grant hard stop applies.
- An approval is recorded by a named human whose authority class is not eligible for that decision type (for example a report owner approving a PII ruling): the approval is invalid and the decision remains unresolved.
- The interview is run twice on the same source: existing decisions are presented for confirmation or supersession, not silently overwritten.

## Requirements *(mandatory)*

### Functional Requirements

#### Shared Product Contract (integration rules)

- **FR-001**: All artifacts introduced by this feature (decision records, contracts, review artifact, verdicts) MUST remain projections of or inputs to the existing seven-stage readiness spine; this feature MUST NOT create a second readiness state engine or alter stage order.
- **FR-002**: No capability in this feature may grant, infer, or fabricate a human approval; approvals exist only when recorded from a named human. Confidence, static-check success, and batch grouping never substitute for approval.
- **FR-003**: The feature MUST preserve the existing knowledge-layer ownership boundaries: Retail KPI owns business meaning and metric contracts; SQL owns SQL reasoning, grain/join/validation/reconciliation/transformation review; Python owns single-node dataframe and source-prep reasoning; Big-data owns distributed/larger-than-memory reasoning only when justified; DAX owns measure implementation and semantic-model prerequisites from approved contracts; Readiness owns gates and pass/block; Dashboard design owns visual/page planning after contracts are approved.
- **FR-004**: Execution adapters MUST NOT define meaning, mapping, metrics, semantic logic, or approval anywhere in this feature's artifacts or contracts.
- **FR-005**: No committed artifact of this feature may contain secrets, credentials, connection strings, or raw suspected-PII values.

#### Business Knowledge Interview

- **FR-006**: The interview MUST run after database discovery and MUST ground every question in discovery evidence (profile summaries, candidate grains, column types), asking targeted business questions rather than generic ones.
- **FR-007**: The interview MUST support hybrid questioning: obvious low-risk interpretations are grouped into a batch presented for a single owner confirmation; critical decisions are asked individually and require explicit per-decision approval.
- **FR-008**: The interview MUST use profile summaries and masked samples as question evidence. Raw values of suspected-PII columns MUST NOT be displayed by default; unmasking requires an explicit owner instruction recorded as a PII-handling decision scoped to the affected columns.
- **FR-009**: The interview MUST NOT walk every column one-by-one unless the owner requests it or unresolved ambiguity requires it; question effort concentrates on KPI inputs, PII, table grain, keys, relationships, missing-value rules, and ambiguous financial/quantity/date columns.
- **FR-010**: Every interview outcome -- answered, unanswered, refused, or deferred -- MUST land in the Decision Store; no decision may exist only in conversation.
- **FR-011**: The interview MUST be pausable and resumable; interrupting it leaves unanswered questions as `pending` or `needs_user_input` and approves nothing.
- **FR-012**: Re-running the interview over an existing Decision Store MUST present existing decisions for confirmation or supersession rather than overwriting them.

#### Decision Store

- **FR-013**: The product MUST define a machine-readable, project-scoped Decision Store that is plain-text, versionable, and diffable in change review. The working proposal is `.seshat/semantic-decisions.yaml`, `.seshat/kpi-contracts.yaml`, and `.seshat/cleaning-rules.yaml`; exact file names and split may be finalized at plan time following existing `.seshat/` and `templates/` conventions, without weakening any behavior specified here.
- **FR-014**: Every decision record MUST carry exactly one status from: `proposed`, `approved`, `rejected`, `pending`, `needs_user_input`, `needs_sample`, `blocked`, `deferred`, `superseded`.
- **FR-015**: Every proposed decision MUST carry a confidence value of `low`, `medium`, or `high` describing the agent's proposal confidence only.
- **FR-016**: Confidence MUST NOT equal approval: a `high`-confidence critical decision still requires explicit named-human approval, and no confidence value may be presented as a readiness or approval signal.
- **FR-017**: Approved decisions are immutable: they MUST NOT be edited in place or re-statused directly; the only path to change or reverse an approved decision is a superseding record. Superseding a decision MUST retain the superseded record with a reference from its replacement, preserving decision history.
- **FR-018**: The store MUST recognize these critical decision types: KPI definition, PII handling, table grain, primary key, relationship/cardinality, missing-value rule for KPI/financial/quantity/date fields, data exclusion, financial policy ruling (VAT/returns/discount/cost), dashboard blueprint approval, and publish/export decision.
- **FR-019**: Every decision record MUST declare its scope (the tables, columns, KPIs, or artifacts it governs) so consumers can resolve which decisions apply to a requested stage.

#### Approval Metadata

- **FR-020**: Every approved critical decision MUST record: approved_by, approved_at, source, evidence, the identity of each cited evidence artifact captured at approval time (enabling stale-evidence detection), status, confidence, decision_type, and reviewed_scope.
- **FR-021**: `approved_by` MUST follow the existing named-human-plus-authority-class convention (a name with a declared authority class); a bare role token, an anonymous entry, or an agent identity does not satisfy it. Each critical decision type MUST declare the authority class(es) eligible to approve it (for example: PII handling and publish/export require the data owner; KPI definition requires the metric owner; dashboard blueprint approval requires the report owner); an approval whose authority class is not eligible for the decision type is invalid.
- **FR-022**: An approval missing any required metadata field, or citing evidence that is missing or unresolvable, is invalid: the decision is treated as unresolved and dependent gates fail closed.
- **FR-023**: A batch approval MUST record which decisions were in the batch and the evidence presented for the batch; critical decision types are never batch-approvable. The owner MAY exclude individual items from a batch before confirming: the remaining items are approved in one action, each excluded item becomes an individual `pending` question, and the exclusions are recorded with the batch.

#### Human-Readable Review Artifact

- **FR-024**: The product MUST define a human-readable interview review artifact (working proposal: `evidence/business-interview-review.md` within the project workspace; exact location may follow existing evidence-pack conventions) that is generated from the Decision Store and holds no independent state.
- **FR-025**: The review artifact MUST summarize: approved decisions, pending decisions, blocking decisions, rejected assumptions, deferred decisions, PII handling, KPI-impacting decisions, grain and relationship decisions, cleaning and missing-value decisions, the next open questions, and the current gate verdict.
- **FR-026**: The review artifact MUST be readable by a non-technical business owner and MUST show masked values only.

#### Knowledge Contracts

- **FR-027**: The product MUST define product-level Knowledge Contracts covering the Database-to-PBIP flow stages (discovery, domain guess, scope proposal, business knowledge interview, KPI contracts, Silver/Gold model planning, semantic model + DAX, report intent, dashboard blueprint, PBIP prototype readiness, evidence pack). Each contract MUST declare: stage name, allowed knowledge routes, required inputs, required outputs, stop rules, blocking decision categories, handoff target, non-goals, and evidence requirements. Working proposal locations: `contracts/knowledge/database-to-pbip-flow.yaml`, `contracts/interview/business-knowledge-interview.yaml`, `contracts/report/dashboard-blueprint.yaml`; exact paths may follow repo conventions at plan time.
- **FR-028**: Contracts MUST route by existing knowledge boundaries: a KPI-meaning question arising in any implementation stage (including DAX) routes back to Retail KPI knowledge; DAX implements only approved contracts and never defines meaning.
- **FR-029**: The Big-data route MUST NOT be a default: contracts require recorded scale evidence before Big-data is an allowed route, and route back to Python when the work fits a single node.
- **FR-030**: Contract stop rules MUST prevent stage entry while any decision in the stage's blocking categories is unresolved, and MUST name the unresolved decisions when stopping.
- **FR-031**: Contracts MUST reference the existing knowledge routes (router, SKILL/INDEX two-hop) and MUST NOT duplicate or rewrite the SQL, DAX, Python, Big-data, or Retail KPI knowledge bases.

#### Blocking Gates and Gate Verdicts

- **FR-032**: The following unresolved decisions MUST block the named downstream stages: pending PII handling blocks cleaning and any report exposure of the affected columns; pending table grain blocks Silver/Gold modeling of the affected table; pending primary key or relationship/cardinality blocks modeling that depends on them; pending KPI meaning blocks that KPI's contract, DAX measure, dashboard use, and PBIP readiness; a pending financial policy ruling (VAT/returns/discount/cost) blocks the KPI contracts it affects; unapproved dashboard blueprint blocks the PBIP prototype; missing or unresolvable evidence invalidates the affected approval and blocks whatever depended on it. Evidence that has changed since approval marks the approval **stale**: for critical decision types, dependent stage verdicts are blocked until the owner re-confirms or supersedes the decision; for non-critical decisions, staleness is listed under warn.
- **FR-033**: Readiness for a requested stage MUST be classified as exactly one of: **pass** -- every required decision for the stage is approved with valid metadata and resolvable evidence, and no blocking condition applies; **warn** -- progress is allowed, but non-fatal issues exist (accepted deviations, stale evidence on non-critical decisions, open low-risk questions) and are listed; **blocked** -- at least one required decision is unresolved, invalid, in conflict, or missing evidence; the verdict names each concrete blocking decision.
- **FR-034**: Gate verdicts MUST be recomputable deterministically from committed artifacts (Decision Store plus evidence) with no hidden state, and MUST align with the existing readiness status vocabulary (warn corresponds to the spine's non-fatal `warning`; blocked stops the next stage; pass requires evidence). A pass with no citable evidence is a defect.
- **FR-035**: Verdicts MUST fail closed: malformed records, unknown statuses, unknown decision types in a blocking category, and unreadable stores all produce blocked, never pass.

#### Future PBIP Safety

- **FR-036**: This slice MUST NOT generate PBIP artifacts. PBIP Prototype generation comes in a later slice and MUST NOT be built freehand by the agent; the future path is Blueprint, then Compiler, then Validation.
- **FR-037**: This slice's obligation to that future work is exactly: the decisions and contracts a PBIP prototype depends on (approved KPI meanings, grains, keys, relationships, PII rulings, missing-value rules, approved dashboard blueprint) exist, carry valid approval metadata, and gate PBIP readiness as specified in FR-032.
- **FR-038**: Publish/export remains a critical human decision; the Power BI execution adapter (F016) remains deferred and gated, and nothing in this feature advances it.

### Non-Functional Requirements

- **NFR-001**: All decision-store and contract artifacts are plain text, reviewable and diffable in ordinary change review, with stable ordering so diffs reflect real changes.
- **NFR-002**: The review artifact is regenerable deterministically: the same Decision Store always produces the same artifact content.
- **NFR-003**: Interview effort is proportionate: for a typical multi-table source, the number of question rounds is bounded by the count of critical decisions plus one batch round, not by column count.
- **NFR-004**: All consumers of the Decision Store fail closed on malformed or unknown content; no consumer skips an unreadable record silently.
- **NFR-005**: Vocabulary is consistent with the existing glossary and readiness statuses; this feature introduces no synonym for an existing term.
- **NFR-006**: The feature's artifacts function without a live database connection; live samples are an optional input (`needs_sample` marks their absence truthfully).

### Key Entities

- **Decision Record**: One recorded business decision with scope, decision_type, status, confidence, evidence, and (when approved) full approval metadata; immutable once approved, supersedable, and never silently deleted.
- **Decision Store**: The project-scoped, machine-readable collection of Decision Records that is the single source of truth for business decisions.
- **Approval Record**: The named-human approval attached to a critical decision: approved_by (name plus authority class), approved_at, source, evidence, evidence identity captured at approval time, reviewed_scope; valid only when the approver's authority class is eligible for the decision type.
- **Interview Question**: A discovery-grounded question bound to the decision(s) it resolves, carrying profile summaries and masked samples as evidence.
- **Batch Approval Set**: A group of low-risk decisions presented for one confirmation; excludes critical decision types by construction and supports item-level exclusion by the owner, with excluded items becoming individual pending questions.
- **Review Artifact**: The generated human-readable summary of the Decision Store for owners and reviewers.
- **Knowledge Contract**: A per-stage declaration of allowed knowledge routes, required inputs/outputs, stop rules, blocking decision categories, handoff target, non-goals, and evidence requirements.
- **Gate Verdict**: The pass/warn/blocked classification of a requested stage, computed from the Decision Store and evidence, with named blocking decisions when blocked.
- **Blocking Rule**: The mapping from an unresolved decision category to the downstream stages it blocks.
- **Masked Sample**: A sample value display with suspected-PII content obscured; the default evidence form for PII-suspect columns.

## Acceptance Criteria

1. **AC-001**: A valid Decision Store schema/contract is specified: records carry scope, decision_type, one of the nine statuses, a confidence value, and (for approved critical decisions) the full approval metadata (FR-013 to FR-020).
2. **AC-002**: A human-readable review artifact is specified with all eleven required summary sections and no independent state (FR-024 to FR-026).
3. **AC-003**: Blocking decisions are clearly defined: every critical decision type maps to the downstream stages it blocks when unresolved (FR-018, FR-032).
4. **AC-004**: Approved decisions require metadata: an approval missing any required field or citing unresolvable evidence is invalid and fails closed (FR-020 to FR-022).
5. **AC-005**: Pending KPI meaning blocks that KPI's contract, DAX measure, dashboard use, and PBIP readiness (FR-032).
6. **AC-006**: Pending PII handling blocks cleaning and report exposure of the affected columns (FR-032).
7. **AC-007**: Pending table grain blocks Silver/Gold modeling of the affected table (FR-032).
8. **AC-008**: Knowledge Contracts route KPI/DAX meaning questions back to Retail KPI knowledge; DAX never invents meaning (FR-028).
9. **AC-009**: Big-data is not the default route: it requires recorded scale evidence and routes back to Python otherwise (FR-029).
10. **AC-010**: No PBIP compiler, PBIP generation, or Power BI publish work is included in this slice (FR-036 to FR-038, Non-Goals).

## Non-Goals and Out of Scope

### Explicit Non-Goals

- No PBIP compiler implementation.
- No Power BI publish implementation.
- No report visual implementation.
- No database connector implementation.
- No live database query execution.
- No rewrite of the SQL, DAX, Python, or Big-data knowledge bases.
- No expansion of the Retail KPI catalog.
- No full dashboard engine.
- No broad refactors.
- No new CLI commands beyond what existing spec conventions already require.

### Out of Scope for This Slice

- Automating discovery, domain guessing, or scope proposal (the interview consumes discovery output; producing it is a separate concern).
- Executing any stage of the Database-to-PBIP flow end to end; this slice defines the contracts and decision foundation only.
- Numeric readiness or confidence scoring of any kind (the existing no-fake-confidence rule stands).
- Approval workflow tooling (notification, delegation, expiry policies) beyond recording valid approvals.
- Migrating or restating existing readiness artifacts; the spine and its stage docs are consumed as-is.

## Future Slices

The Database-to-PBIP direction continues after this foundation, in separately specified slices:

1. **Discovery and domain-guess assistance** -- producing the profile the interview consumes.
2. **KPI contract production at flow scale** -- binding approved KPI meanings into governed metric contracts via the existing Retail KPI layer.
3. **Silver/Gold model planning** -- consuming approved grains, keys, and relationships.
4. **Semantic model + DAX generation** -- implementing approved contracts through the DAX layer.
5. **Report intent and dashboard blueprint** -- design bound to approved contracts, ending in the blueprint-approval decision this slice already gates on.
6. **PBIP prototype via Blueprint -> Compiler -> Validation** -- never freehand; entered only when this slice's gates report pass.
7. **Evidence pack integration** -- folding interview and decision evidence into the existing evidence-pack surfaces.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a worked-example source of at least 5 tables and 50 columns, the interview completes with question rounds bounded by critical-decision count plus one batch round, and a data owner can answer it in a single sitting (under 30 minutes in a moderated walkthrough).
- **SC-002**: 100% of approved critical decisions in conformance fixtures carry complete approval metadata; every seeded incomplete approval is detected as invalid and fails closed.
- **SC-003**: Seeded gate scenarios (pending grain, pending PII, pending KPI meaning, pending policy, unapproved blueprint, missing evidence, conflicting records, malformed store) each produce blocked for exactly the specified downstream stages, and produce pass once resolved -- with zero false passes.
- **SC-004**: A reviewer reading only the review artifact can correctly identify, for a seeded store, every approved, pending, blocking, rejected, and deferred decision and the current gate verdict, without opening a machine-readable file.
- **SC-005**: 100% of boundary probes route correctly: KPI-meaning questions reach Retail KPI knowledge, scale-out requests without scale evidence stay on Python, and no contract grants an execution adapter meaning or approval authority.
- **SC-006**: Zero raw suspected-PII values, secrets, or connection strings appear in any committed decision, contract, or review artifact across all fixtures.
- **SC-007**: The slice ships no PBIP generation, compiler, or publish capability, verified by inspection of its delivered artifacts.
- **SC-008**: All feature artifacts remain projections: deleting every generated review artifact and recomputing from the Decision Store reproduces identical content, and no readiness stage state exists outside the existing spine.

## Assumptions

- The knowledge router (`docs/knowledge-map.md`) and the five knowledge layers (SQL, DAX, Python, Big-data, Retail KPI) exist and are consumed as-is; this feature adds contracts above them without modifying their content.
- The seven-stage readiness spine remains the single authority for stage state; this feature's gate verdicts are decision-level projections that feed it (interview decisions land in the Source Ready / Mapping Ready neighborhood; blueprint approval feeds Dashboard Ready; publish/export feeds Publish Ready), and warn maps to the spine's `warning`.
- The named-human-plus-authority-class approval convention from the readiness model applies to `approved_by` unchanged.
- Discovery/profile input comes from the existing onboarding surfaces (the Stage-1 read-only profile of `retail-onboard-table` or an equivalent committed profile); this slice does not build discovery.
- Exact artifact paths (`.seshat/*.yaml`, contract file locations, review-artifact location) are working proposals to be finalized at plan time against existing `.seshat/`, `templates/`, and evidence-pack conventions; the behavior specified here does not depend on the final paths.
- Decision-store enforcement follows the repo's existing pattern of docs/templates/contracts plus static checks; whether a new lint rule is added is a plan-time decision, not assumed here.
- Artifacts are English plain text, consistent with the existing repo.
