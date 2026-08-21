# Feature Specification: Studio Operations and Client Review

**Feature Branch**: `spec/141-promote-operations`

**Created**: 2026-08-03

**Promoted**: 2026-08-21 -- expanded from program outline into this specification

**Status**: ratified -- Ahmed Shaaban (owner), 2026-08-21

**Status history**: program outline 2026-08-03; program DIRECTION ruled by the owner
2026-08-21 (scope agreement, explicitly not implementation authority); promoted to this
full specification 2026-08-21 once its prerequisite was satisfied. The agent transcribed
the owner's rulings and has not self-ratified.

**Prerequisite SATISFIED**: FR-141-020 required specs 139 and 140 *accepted*, not merely
ratified. Spec 139 was accepted 2026-08-16 (38/38 tasks); spec 140 was implemented,
merged (`421c8f4d`, PR #695) and accepted by Ahmed Shaaban 2026-08-21. The contracts this
spec consumes therefore exist in the tree rather than on paper -- see "What this spec
builds on" below.

**Ratified 2026-08-21 by Ahmed Shaaban (owner), in session.** The owner first asked to
ratify spec 141 while it was a one-page outline; that could not be honoured, for the same
reason it could not be honoured for spec 140 hours earlier -- the Promotion Gate requires
a named human to ratify the *exact package*, and there was none. This package is that
expansion, and this ratification is of it: specification, research, data model, contracts,
plan, task list, quickstart and checklist as they stand at this commit. The agent
transcribed the ruling and did not self-ratify.

**Scope ratified**: all five user stories, including US5 (support bundle). The checklist
raised the option of splitting US5 into a follow-on spec; the owner ruled for the whole
package on 2026-08-21. A later narrowing would need a new ratification, not a silent
reduction.

**FR-141-020 is now fully satisfied**: 139 and 140 accepted, this package ratified, and
the owner moved the sole active Spec Kit fence to this plan on 2026-08-21. Implementation
is authorized. Moving the fence parked spec 140 -- delivered and accepted, so nothing is
abandoned -- while spec 149 remains parked with four tasks open, including the
owner-facing T053.

## Purpose

Complete the Studio program with two surfaces the Workbench deliberately left out: an
operational view that explains why something cannot proceed, and a client review surface
that turns approved evidence into a decision story without leaking the machinery.

Both are **presentation over existing truth**. Neither may compute readiness, redefine a
metric, or soften a blocked fact. That constraint is the feature: a support view that
invents a diagnosis, or a client view that renders "pending" as "done", would be worse
than no view at all.

## Primary Users

- technician/support analyst: diagnoses why Studio, an integration, or a governed
  workflow cannot proceed;
- lead analyst: reviews recent governed runs and prepares client material;
- final client/business owner: understands status, decisions, evidence, and the next
  responsibility in clear language.

## What this spec builds on (verified in the tree, 2026-08-21)

| Need | Shipped seam |
| --- | --- |
| Component diagnostics | `seshat/doctor.py` -- categorical findings, grouping, repair hints |
| Normalized run events | `studio/events.py` -- `StudioEvent`, `ThreadEvents`, `ThreadStore` |
| Durable governed receipts | `decision_write.DecisionWriteReceipt`, `studio/apply.ApplyReceipt` |
| Committed decision reads | `decision_write.decisions_at_head` |
| Scoped review filtering | `studio/review_scope.py` -- server-side scope, withheld fields |
| Redaction | `studio/redaction.py` (`scrub_payload`, `redact_credentials`, `redact_paths`) over `seshat/redaction_core.py` |
| Evidence export precedent | `seshat/evidence_pack.py` |

This spec adds no second implementation of any of these. Where a need overlaps a shipped
seam, it consumes it; a second diagnostic engine or a second redaction path would be the
defect, not the feature.

## The two boundaries that carry this feature

**1. A diagnostic recommends; it never repairs.** Operations may name a recovery action.
Executing one goes through the same technical-approval and readiness policy as any other
mutation (FR-141-018). A support surface that can fix things is a mutation surface with a
friendly name.

**2. A client view may only narrow, never soften.** Every fact reaching Client Review is
already approved and already committed. `pending` and `blocked` render as themselves. The
export is built from an **allowlist** of safe fields, never a denylist applied after
assembly -- because a denylist fails open on the field nobody thought of.

## User Scenarios & Testing

### US1 - Diagnose Studio and integration health (P1)

A technician opens Operations and sees categorical health for the local Studio process,
package extras, Codex adapter, bundle capability, static gate, optional live boundary,
and frontend assets -- each with evidence and a recovery action.

Acceptance:

1. **No aggregate health score.** Seven components each carry their own state; there is
   no roll-up number, because a single score invites "we're at 80%" reasoning about
   things that are individually pass or fail.
2. States are distinct and exhaustive: `missing`, `misconfigured`, `incompatible`,
   `deferred`, `failed`, `healthy`. `deferred` is not a failure and must not render as
   one.
3. Credential and workspace data is redacted before display and before export.
4. A diagnostic may recommend an action; it cannot execute one without the existing
   technical approval and readiness policy.
5. An unreadable component reports `failed` with its reason, never `healthy` by absence
   of evidence.

### US2 - Review a redacted run history (P1)

The analyst inspects recent in-process and committed governed receipts: what was
requested, what tools were proposed, who decided, what changed, which gates ran, and the
categorical result.

Acceptance:

1. History is reconstructed from normalized `StudioEvent` records and durable receipts,
   never from raw provider transcripts.
2. Hidden reasoning, secrets, DSNs, prompts marked sensitive, and absolute paths never
   appear.
3. Process-only conversation history is labelled **ephemeral** and disappears on
   restart; the label is part of the contract, not a UI nicety.
4. A durable audit claim cites its committed source. A claim that cannot cite one is
   shown as ephemeral rather than promoted to durable.
5. A decision still in `pending commit` appears as pending, never as a completed ruling
   -- the same three-state honesty spec 140 established.

### US3 - Prepare a client-ready review (P1)

The lead analyst selects approved metrics, decisions, evidence, blockers, and next
responsibilities. Studio previews a simplified narrative and exports a local,
self-contained review artifact.

Acceptance:

1. Only approved and eligible evidence enters the client view; eligibility is read from
   committed state at `HEAD`.
2. Pending or blocked facts remain visibly pending or blocked, never softened.
3. Internal command names, skill names, raw diffs, logs, and absolute paths are absent.
4. The export is self-contained, reproducible, accessible, and references no remote
   asset.
5. The narrative is generated from selected facts only; it may not add a claim absent
   from that selection.

### US4 - Let the client respond safely (P2)

Within the authenticated local session a client can acknowledge a result, request
clarification, or answer a scoped business decision through the Workbench's named-human
boundary.

Acceptance:

1. Acknowledgement is a **distinct action** from a business approval and is recorded as
   such.
2. A scoped business answer routes through spec 140's `POST /decisions/record`; this
   spec adds no second recording path.
3. Decline and request-clarification are always available.
4. A client response never advances readiness by itself.

### US5 - Assemble a support bundle (P2)

A technician exports a bundle a maintainer can read without the workspace present.

Acceptance:

1. Built from an **allowlist** of safe fields and files.
2. Structurally excludes `.env`, data extracts, credential stores, cookies, auth
   headers, raw provider transcripts, and absolute paths.
3. Creation is atomic, and the staged content is scanned with the existing redaction
   corpus before finalization.
4. A scan failure aborts the bundle; it never ships a partially scrubbed archive.

## Requirements

- **FR-141-001**: Operations MUST report the seven components categorically with
  evidence and a recovery action for each.
- **FR-141-002**: No aggregate health, maturity, confidence, or readiness score may be
  computed or displayed.
- **FR-141-003**: Component states MUST distinguish missing, misconfigured,
  incompatible, deferred, failed, and healthy; `deferred` MUST NOT render as failure.
- **FR-141-004**: Diagnostics MUST consume the shipped `seshat/doctor.py` findings rather
  than implement a second diagnostic engine.
- **FR-141-005**: A diagnostic MAY recommend a recovery action and MUST NOT execute one
  outside the existing technical-approval and readiness policy.
- **FR-141-006**: An unreadable or unavailable component MUST report `failed` with its
  reason; absence of evidence MUST NOT read as healthy.
- **FR-141-007**: Run history MUST be reconstructed from normalized events and durable
  receipts, never from raw provider transcripts.
- **FR-141-008**: Hidden reasoning, secrets, DSNs, sensitive prompts, and absolute paths
  MUST NOT appear in any Operations or Client Review surface or export.
- **FR-141-009**: Process-only history MUST be labelled ephemeral and MUST NOT survive a
  restart.
- **FR-141-010**: A durable audit claim MUST cite its committed source; an uncitable
  claim MUST be presented as ephemeral.
- **FR-141-011**: Client responses MUST route through spec 140's scoped named-human
  decision contracts; acknowledgement MUST remain a distinct action.
- **FR-141-012**: Support bundles MUST be assembled from an allowlist of safe fields and
  files, not a redact-after-assembly denylist.
- **FR-141-013**: Support bundles MUST structurally exclude `.env`, data extracts,
  credential stores, cookies, API/auth headers, raw provider transcripts, and absolute
  paths.
- **FR-141-014**: Support-bundle creation MUST be atomic and MUST scan staged content
  with the existing redaction corpus before finalization; a scan failure MUST abort.
- **FR-141-015**: Accessibility MUST meet WCAG 2.2 AA across technician density, client
  simplicity, print/export, keyboard use, zoom, and reduced motion.
- **FR-141-016**: Responsive layouts MUST preserve the correct primary action and
  decision context from mobile width through large desktop.
- **FR-141-017**: Operations and Client Review MUST remain localhost, single-workspace,
  and authenticated under Foundation's security boundary.
- **FR-141-018**: No diagnostic, export, acknowledgement, or client response may advance
  readiness except through existing authoritative artifacts and gates.
- **FR-141-019**: Existing static dashboard and Foundation/Workbench journeys MUST remain
  backward compatible.
- **FR-141-020**: Implementation MUST NOT begin until specs 139 and 140 are accepted,
  this detailed spec is named-human ratified, and its plan is the sole active fence.

  *Promotion note*: the first condition is now met -- 139 accepted 2026-08-16, 140
  accepted 2026-08-21. The remaining two are not.
- **FR-141-021**: Client Review MUST render a `pending commit` decision as pending; it
  MUST NOT present one as a completed ruling.
- **FR-141-022**: The client narrative MUST be derived only from the selected facts and
  MUST NOT introduce a claim absent from that selection.

## Key Entities

- `ComponentDiagnostic`: categorical state, evidence, blocker, recovery action, and safe
  version/config presence.
- `GovernedRunSummary`: normalized request/outcome timeline plus durable receipt
  references.
- `ClientReviewDraft`: revision-bound selection of eligible facts and narrative.
- `ClientReviewArtifact`: self-contained immutable exported review with manifest.
- `ClientAcknowledgment`: scoped acknowledgement, distinct from business approval.
- `ClientFeedbackItem`: prepared clarification routed to the analyst workflow.
- `SupportBundleManifest`: allowlisted safe fields/files, hashes, versions, and the
  redaction-scan receipt.

## Success Criteria

- **SC-141-001**: No surface or export exposes an aggregate score, proven by a test that
  searches every payload for a numeric roll-up.
- **SC-141-002**: A deferred component renders as deferred and not as failure, with its
  inverse asserted so the test cannot pass by treating everything as deferred.
- **SC-141-003**: A support bundle built from a workspace containing `.env`, a DSN, and
  an absolute path contains none of them, proven by scanning the produced archive.
- **SC-141-004**: A pending-commit decision appears as pending in Client Review, proven
  alongside the committed case so the assertion is not vacuous.
- **SC-141-005**: A recovery action cannot execute without technical approval, proven by
  attempting it and asserting refusal.
- **SC-141-006**: Ephemeral history is absent after a restart, proven by asserting it was
  present before.

## Assumptions

- Operations reads the shipped `doctor.py` findings; this spec adds no new probe.
- Run history uses the existing `ThreadStore`/`StudioEvent` records; no new event schema.
- The support bundle follows `evidence_pack.py`'s precedent for a self-contained export.
- Client Review reuses spec 140's `review_scope` filtering rather than a parallel one.

## Out of Scope

- SaaS hosting, remote client portal, email delivery, or cloud file sharing;
- organization identity, SSO, RBAC, or cryptographic signer verification;
- raw source-data preview or export;
- arbitrary log download;
- aggregate health, maturity, confidence, or readiness scores;
- automated repair without explicit technical approval;
- redefining metrics, mappings, or readiness in presentation code;
- a second decision-recording path (spec 140 owns the only one).

## Promotion Gate -- expansion delivered, ratification required

The outline required expansion "from both the support technician and final-client
perspectives" into an exact specification with security/export contracts, plan, and
tasks, after which "the resulting exact specification ... require[s] named-human
ratification and the single active fence."

The expansion is delivered by this package. The ratification is not: a named human must
ratify this exact specification, plan, contracts, and task list, and the fence must move
to its plan. Until both happen, no agent may write the ratified line and no task may
start.
