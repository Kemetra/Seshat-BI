# Feature Specification: Studio Governed Analyst Workbench

**Feature Branch**: `spec/140-promote-workbench`

**Created**: 2026-08-03

**Promoted**: 2026-08-21 -- expanded from program outline into this specification

**Status**: ratified -- Ahmed Shaaban (owner), 2026-08-21

**Status history**: program outline 2026-08-03; program DIRECTION ruled by the owner
2026-08-21 (scope agreement, explicitly not implementation authority); promoted to this
full specification 2026-08-21 under the outline's Promotion Gate; **this exact package
-- specification, research, data model, contracts, plan, and task list -- ratified by
Ahmed Shaaban (owner) in session on 2026-08-21.** The agent transcribed the owner's
ruling and did not self-ratify.

Ratification is not activation. FR-140-020 has two conditions and only the first is
now met: the package is ratified, but the **sole active Spec Kit fence must still be
moved to this plan** before implementation begins. Until that fence moves, every task
in `tasks.md` remains blocked.

The scope ratified here is **all five user stories** (US1-US5), per the owner's
decision of 2026-08-21. `plan.md` retains the Phase-D split as a noted contingency; a
split would require a new ratification of the reduced package, not a silent narrowing.

Recorded in the order it happened: outline, then direction ruling, then promotion, then
ratification. Unlike spec 155, no implementation preceded this ratification -- the
package is docs-only and no task has been started.

**Depends on**: accepted `specs/139-seshat-studio-foundation/` (implemented, all 38
tasks complete, accepted by Ahmed Shaaban 2026-08-16), including its security
boundary, workspace projection, AgentBridge, event, and technical-approval contracts.

## Purpose

Turn Foundation's read-only Command Room into a governed analyst workbench where a
person can inspect evidence, understand a proposed mapping/metric/artifact change,
answer a named business question with an explicit identity, and see the resulting gate
state. The workbench must make sophisticated Seshat workflows usable without exposing
command or skill names as the primary journey.

Foundation shipped the *observation* half of this: `GET`-only projection routes, an
`ApprovalEnvelope` that models `named_human` authority and permanently refuses it
(`allow_permitted = authority == TECHNICAL and not reasons`), and a read-only Decision
Store. This specification builds the *authorized path through* that refusal. It does
not add a gate; it adds the only sanctioned way a named human can satisfy one.

## Primary Users

- analyst: investigates evidence, requests changes, and prepares decision material;
- named business owner/reviewer: records an authorized judgment after seeing exact
  impact and provenance;
- technician: opens raw artifact/gate detail only when diagnosing a defect.

## The write boundary -- the load-bearing decision

`decision_store.approval_is_valid` is documented in the shipped source as "The ONE
approval-validity predicate shared by DS2 and the gate", and `store_files()` selects
decision files from the repository's **tracked** paths
(`.seshat/semantic-decisions.yaml`, `.seshat/kpi-contracts.yaml`,
`.seshat/cleaning-rules.yaml`).

Therefore:

**Studio writes a recorded decision into the working tree. Studio cannot make that
decision authoritative.** Authority arrives only when a human commits the file and the
static gate reads it at `HEAD`.

This yields a three-state model, and the third state is mandatory:

| State | Meaning | Who causes it |
| --- | --- | --- |
| `draft` | a proposal exists, no human answer recorded | agent prepares |
| `pending commit` | a named human answered; the file is modified but uncommitted | named human answers in Studio |
| `authoritative` | the decision is committed and read by the gate at `HEAD` | a human commits |

Collapsing `pending commit` into an approved or passed indicator is a defect, not a
cosmetic choice: it would present an agent-writable file as a human ruling. A UI that
shows a recorded-but-uncommitted decision as green has defeated Principle V
(`never_self_grant_approval`) by design rather than by bug.

## User Scenarios & Testing

### US1 - Investigate one table with traceable evidence (P1)

The analyst opens a table and sees its source profile, mapping proposal, unresolved
questions, reconciliation evidence, contracts, and readiness stages as one coherent
journey. Every claim links to its committed source or named pending live boundary.

Acceptance:

1. Stage views preserve categorical truth and show why an item is pass, blocked, or
   ready for review.
2. Missing or malformed evidence appears as an `InputDefect`, not an empty success
   state.
3. Live boundaries remain `[PENDING LIVE PROFILE]` until the existing live validator
   supplies evidence.
4. The primary view uses business labels; raw files and gate payloads are optional
   technical detail.

### US2 - Review a proposed mapping or metric change (P1)

The analyst asks the agent to prepare a change. The workbench shows the exact artifact
diff, field-level provenance, affected stages, downstream impact, validation result,
and decisions still needed before any write approval is offered.

Acceptance:

1. Proposal preview is generated from the current `workspace_revision` and invalidates
   when inputs change.
2. Every proposed field distinguishes discovered fact, existing decision, default,
   inference, and new human judgment.
3. Existing mapping and KPI-contract engines remain authoritative; Studio does not
   recreate their validation logic.
4. A failed gate or forbidden stage prevents applying the proposal regardless of
   visual technical consent.

### US3 - Record a named-human business decision (P1)

An authorized person answers an explicit business question after reviewing the exact
proposal and impact. Studio writes their stated identity, authority, decision,
proposal hash, workspace revision, timestamp, and affected artifact diff into the
Decision Store file through the store's existing validation predicates.

Acceptance:

1. The agent can prepare and explain but cannot select an answer or a signer.
2. The form distinguishes the human decision from technical permission.
3. A stale proposal or stale revision is rejected and must be regenerated before
   signing.
4. Writing succeeds only when `approval_is_valid` and `owner_shape_ok` accept the
   entry; a rejected entry is not partially written.
5. The recorded decision displays as `pending commit` and readiness does not move.
6. Readiness is recomputed from `HEAD` after a commit; the UI never predicts a pass.

### US4 - Apply and verify an authorized artifact change (P2)

After required decisions are authoritative, the analyst can allow the agent to apply
the exact reviewed scope and then see static and live verification evidence plus any
remaining blocker.

Acceptance:

1. Applied files and commands cannot exceed the reviewed proposal scope.
2. A changed diff invalidates the prior technical approval.
3. Static success is labeled necessary, not semantic or live correctness.
4. Missing DB extras or DSN use graceful deferred mode and never fabricate a live
   pass.
5. An apply attempted against a decision that is only `pending commit` is refused.

### US5 - Use the same workbench from client review context (P3)

A client or owner can open a constrained review scope within the same local session to
answer only the decisions requiring their authority, with analyst context available
but editing and unrelated technical controls hidden.

Acceptance:

1. Review scope is least privilege and session-bound.
2. The reviewer sees question, choices, provenance, impact, and exact affected scope.
3. Decline and request-clarification are always available.
4. Studio does not claim identity assurance beyond the local named-human declaration
   unless a later authentication feature is separately specified.

## Requirements

- **FR-140-001**: Workbench MUST consume Foundation's authenticated same-origin API
  and one pinned workspace; it MUST NOT introduce remote multi-user hosting.
- **FR-140-002**: Evidence views MUST cite committed source references and preserve
  pending-live state.
- **FR-140-003**: Mapping workflows MUST call the existing source-mapping and
  onboarding services and MUST stop before Silver unless Mapping is cleared.
- **FR-140-004**: Metric workflows MUST call the shipped KPI-contract engine and MUST
  NOT design dashboards before metric contracts exist.
- **FR-140-005**: Every proposal MUST carry a canonical `proposal_hash` and the
  `workspace_revision` from which it was prepared.
- **FR-140-006**: Every proposed field MUST expose provenance as discovered fact,
  existing decision, default, inference, or new human judgment.
- **FR-140-007**: Exact artifact diffs and downstream impact MUST be visible before a
  technical write approval.
- **FR-140-008**: Proposal scope MUST be immutable after review; any change creates a
  new proposal and invalidates approval.
- **FR-140-009**: The agent MUST NOT provide, choose, or infer a named-human answer.
- **FR-140-010**: Business-decision recording MUST require signer name, declared
  authority, exact answer, proposal hash, workspace revision, timestamp, and affected
  scope.
- **FR-140-011**: This feature MUST establish the Decision Store write path under the
  store's EXISTING validation model -- `approval_is_valid`, `owner_shape_ok`, and
  `APPROVAL_REQUIRED_FIELDS` -- and MUST NOT introduce a Studio-only decision database
  or a second approval-validity predicate.

  *Promotion note*: the outline required reuse of an "existing persistence model". The
  shipped store is read-only (`load_*` and validation predicates only, no write path),
  so that requirement was unsatisfiable as written. This feature supplies the
  persistence while reusing the validation. The prohibition on a second predicate is
  the part that carries the security weight and is preserved verbatim in spirit.
- **FR-140-012**: A stale proposal, stale revision, authority mismatch, or missing
  required field MUST fail closed before writing.
- **FR-140-013**: Technical approval and business decision MUST remain distinct
  models, labels, endpoints, and audit events.
- **FR-140-014**: Applying a reviewed proposal MUST be limited to its exact file and
  tool scope and the current readiness forbidden scope from `forbidden_scope_for`.
- **FR-140-015**: After every apply or commit, readiness MUST be recomputed from
  artifacts and gates read at `HEAD`; an uncommitted decision MUST NOT advance any
  stage.
- **FR-140-016**: Static check success MUST NOT be presented as live or semantic
  correctness.
- **FR-140-017**: When a DB boundary is unavailable, Workbench MUST provide the
  repository's two-lane enable steps, mark numbers `[PENDING LIVE PROFILE]`, and
  continue useful artifact preparation.
- **FR-140-018**: Client review scope MUST expose only decisions in its explicitly
  selected scope and MUST NOT expose tool approval or unrelated artifact controls.
- **FR-140-019**: All Foundation redaction, accessibility, no-remote-assets, and
  credential boundaries remain mandatory.
- **FR-140-020**: Implementation MUST NOT begin until Foundation is accepted, this
  detailed spec is named-human ratified, and its plan is the sole active fence.
- **FR-140-021**: A decision written but not committed MUST render as `pending commit`
  and MUST NOT render as approved, passed, or complete.
- **FR-140-022**: The Decision Store write MUST be atomic and MUST NOT mutate or
  delete an existing decision entry; recording is append-only.
- **FR-140-023**: Studio MUST NOT commit to git on a user's behalf as part of
  recording a decision; committing remains a human act outside the write path.

## Key Entities

- `EvidenceBundle`: grouped committed facts, gate results, and pending boundaries.
- `ChangeProposal`: immutable proposed scope, diff, provenance, `proposal_hash`, and
  originating `workspace_revision`.
- `FieldProvenance`: source kind, source reference, author or agent, and timestamp.
- `ImpactSummary`: affected artifacts, stages, metrics, decisions, and client outputs.
- `BusinessDecisionRequest`: exact question, allowed answers, required authority, and
  proposal link.
- `NamedHumanDecision`: signer declaration, answer, proposal and revision binding, and
  the resulting Decision Store entry.
- `DecisionWriteReceipt`: what was written, to which file, and its `pending commit`
  state -- never a readiness claim.
- `ApplyReceipt`: exact applied scope plus verification evidence; never readiness
  authority by itself.

## Success Criteria

- **SC-140-001**: An analyst can trace every displayed claim for one table to a
  committed source reference or a named pending-live boundary.
- **SC-140-002**: A named human can record a business decision that the existing gate
  accepts as valid once committed, with no new approval predicate introduced.
- **SC-140-003**: An uncommitted recorded decision moves no readiness stage, proven by
  a test that records a decision and asserts the stage is unchanged.
- **SC-140-004**: An agent cannot produce a valid recorded decision without a
  human-supplied signer and answer, proven by a test that attempts it.
- **SC-140-005**: An apply cannot exceed its reviewed proposal scope, proven by a test
  that widens the scope and asserts refusal.
- **SC-140-006**: A stale proposal hash or revision is refused before any write.

## Assumptions

- The three Decision Store files under `.seshat/` remain the canonical decision
  location; this feature adds no new store path.
- `workspace_revision` uses the projection's existing revision digest rather than a
  new versioning scheme.
- Client review (US5) reuses the same local authenticated session; no new identity or
  auth system is introduced, per FR-140-019 and US5 acceptance 4.
- Operations history and the polished client export remain owned by spec 141.

## Out of Scope

- unattended business approval or inferred identity;
- free-form artifact editor that bypasses Seshat engines;
- remote collaboration, organization accounts, RBAC, or cloud persistence;
- dashboard design before approved metric contracts;
- Power BI execution adapter before semantic-model readiness;
- Operations history and polished client export, owned by spec 141;
- git commit automation on a user's behalf (FR-140-023).

## Promotion Gate -- expansion delivered, ratification still required

The outline required expansion "through product/design review into a full spec,
research, data model, contracts, plan, and task list", after which "a named human then
ratifies that exact package and moves the single active fence."

The expansion is delivered by this package. The ratification is NOT: a named human
must still ratify this exact specification, plan, contracts, and task list, and the
sole active Spec Kit fence must move to this plan. Until both happen, this package
does not authorize implementation, and no agent may write the ratified line.
