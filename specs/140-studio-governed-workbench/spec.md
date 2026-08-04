# Feature Outline: Studio Governed Analyst Workbench

**Feature Branch**: future branch derived after Foundation acceptance

**Created**: 2026-08-03

**Status**: program outline; specification and ratification required after spec 139
is accepted. This file is not an active implementation plan.

**Depends on**: accepted `specs/139-seshat-studio-foundation/` with stable security,
workspace projection, AgentBridge, event, and technical-approval contracts.

## Purpose

Turn Foundation's Command Room into a governed analyst workbench where a person can
inspect evidence, understand proposed mapping/metric/artifact changes, answer named
business questions with an explicit identity, and see the resulting gate state. The
workbench must make sophisticated Seshat workflows usable without exposing command
or skill names as the primary journey.

## Primary Users

- analyst: investigates evidence, requests changes, and prepares decision material;
- named business owner/reviewer: records an authorized judgment after seeing exact
  impact and provenance;
- technician: opens raw artifact/gate detail only when diagnosing a defect.

## User Stories

### US1 - Investigate one table with traceable evidence (P1)

The analyst opens a table and sees its source profile, mapping proposal, unresolved
questions, reconciliation evidence, contracts, and readiness stages as one coherent
journey. Every claim links to its committed source or named pending live boundary.

Acceptance intent:

1. Stage views preserve categorical truth and show why an item is pass, blocked, or
   ready for review.
2. Missing/malformed evidence appears as a defect, not an empty success state.
3. Live boundaries remain `[PENDING LIVE PROFILE]` until the existing live validator
   supplies evidence.
4. The primary view uses business labels; raw files and gate payloads are optional
   technical detail.

### US2 - Review a proposed mapping or metric change (P1)

The analyst asks the agent to prepare a change. The workbench shows the exact
artifact diff, field-level provenance, affected stages, downstream impact, validation
result, and decisions still needed before any write approval is offered.

Acceptance intent:

1. Proposal preview is generated from the current workspace revision and invalidates
   when inputs change.
2. Every proposed field distinguishes discovered fact, default, inference, and human
   judgment.
3. Existing mapping and KPI-contract engines remain authoritative; Studio does not
   recreate their validation logic.
4. A failed gate or forbidden stage prevents applying the proposal regardless of
   visual technical consent.

### US3 - Record a named-human business decision (P1)

An authorized person answers an explicit business question after reviewing the exact
proposal and impact. Studio records their stated identity, authority, decision,
proposal hash, workspace revision, timestamp, and affected artifact diff through the
existing Decision Store boundary.

Acceptance intent:

1. The agent can prepare and explain but cannot select an answer or signer.
2. The form distinguishes the human decision from technical permission.
3. A stale proposal/revision is rejected and must be regenerated before signing.
4. Recording succeeds only through existing decision validation and leaves immutable
   provenance.
5. Readiness is recomputed after recording; the UI never predicts that the stage
   passed.

### US4 - Apply and verify an authorized artifact change (P2)

After required decisions exist, the analyst can allow the agent to apply the exact
reviewed scope and then see static/live verification evidence and any remaining
blocker.

Acceptance intent:

1. Applied files and commands cannot exceed the reviewed proposal scope.
2. A changed diff invalidates the prior technical approval.
3. Static success is labeled necessary, not semantic/live correctness.
4. Missing DB extras/DSN use graceful deferred mode and never fabricate live pass.

### US5 - Use the same workbench from client review context (P3)

A client or owner can open a constrained review link within the same local session to
answer only the decisions requiring their authority, with analyst context available
but editing and unrelated technical controls hidden.

Acceptance intent:

1. Review scope is least privilege and session-bound.
2. The reviewer sees question, choices, provenance, impact, and exact affected scope.
3. Decline/request-clarification is always available.
4. Studio does not claim identity assurance beyond the local named-human declaration
   unless a later authentication feature is separately specified.

## Provisional Requirements

- **FR-140-001**: Workbench MUST consume Foundation's authenticated same-origin API
  and one pinned workspace; it MUST NOT introduce remote multi-user hosting.
- **FR-140-002**: Evidence views MUST cite committed source references and preserve
  pending-live state.
- **FR-140-003**: Mapping workflows MUST call the existing source-mapping and
  onboarding services and MUST stop before Silver unless Mapping is cleared.
- **FR-140-004**: Metric workflows MUST call the shipped KPI-contract engine and
  MUST NOT design dashboards before metric contracts exist.
- **FR-140-005**: Every proposal MUST carry a canonical `proposal_hash` and the
  `workspace_revision` from which it was prepared.
- **FR-140-006**: Every proposed field MUST expose provenance as discovered fact,
  existing decision, default, inference, or new human judgment.
- **FR-140-007**: Exact artifact diffs and downstream impact MUST be visible before
  a technical write approval.
- **FR-140-008**: Proposal scope MUST be immutable after review; any change creates a
  new proposal and invalidates approval.
- **FR-140-009**: The agent MUST NOT provide, choose, or infer a named-human answer.
- **FR-140-010**: Business-decision recording MUST require signer name, declared
  authority, exact answer, proposal hash, workspace revision, timestamp, and affected
  scope.
- **FR-140-011**: Decision recording MUST use the existing Decision Store validation
  and persistence model rather than a Studio-only database.
- **FR-140-012**: A stale proposal, stale revision, authority mismatch, or missing
  required field MUST fail closed before recording.
- **FR-140-013**: Technical approval and business decision MUST remain distinct
  models, labels, endpoints, and audit events.
- **FR-140-014**: Applying a reviewed proposal MUST be limited to its exact file/tool
  scope and current readiness forbidden scope.
- **FR-140-015**: After every apply/decision action, readiness MUST be recomputed from
  artifacts and gates.
- **FR-140-016**: Static check success MUST NOT be presented as live or semantic
  correctness.
- **FR-140-017**: When a DB boundary is unavailable, Workbench MUST provide the
  repository's two-lane enable steps, mark numbers `[PENDING LIVE PROFILE]`, and
  continue useful artifact preparation.
- **FR-140-018**: Client review mode MUST expose only decisions in its explicitly
  selected scope and MUST not expose tool approval or unrelated artifact controls.
- **FR-140-019**: All Foundation redaction, accessibility, no-remote-assets, and
  credential boundaries remain mandatory.
- **FR-140-020**: Implementation MUST NOT begin until Foundation is accepted, this
  detailed spec is named-human ratified, and its plan is the sole active fence.

## Provisional Entities

- `EvidenceBundle`: grouped committed facts, gate results, and pending boundaries.
- `ChangeProposal`: immutable proposed scope, diff, provenance, validations, hash,
  and originating workspace revision.
- `FieldProvenance`: source kind, source reference, author/agent, and timestamp.
- `ImpactSummary`: affected artifacts, stages, metrics, decisions, and client outputs.
- `BusinessDecisionRequest`: exact question, allowed answers, required authority, and
  proposal link.
- `NamedHumanDecision`: signer declaration, answer, proposal/revision binding, and
  existing Decision Store receipt.
- `ApplyReceipt`: exact applied scope plus verification evidence; never readiness
  authority by itself.

## Out of Scope

- unattended business approval or inferred identity;
- free-form artifact editor that bypasses Seshat engines;
- remote collaboration, organization accounts, RBAC, or cloud persistence;
- dashboard design before approved metric contracts;
- Power BI execution adapter before semantic-model readiness;
- Operations history and polished client export, owned by spec 141.

## Promotion Gate

After Foundation acceptance, this outline must be expanded through product/design
review into a full spec, research, data model, contracts, plan, and task list. A named
human then ratifies that exact package and moves the single active fence. This outline
cannot be cited as implementation permission.
