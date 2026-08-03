# Feature Outline: Studio Operations and Client Review

**Feature Branch**: future branch derived after Workbench acceptance

**Created**: 2026-08-03

**Status**: program outline; specification and ratification required after spec 140
is accepted. This file is not an active implementation plan.

**Depends on**: accepted Studio Foundation (139) and Governed Analyst Workbench
(140), including stable proposal, decision, apply-receipt, and event contracts.

## Purpose

Complete the Studio program with an operational view for technicians and a polished,
safe review surface for clients. Operations explains installation, agent, gate,
validation, packaging, and run failures without exposing secrets. Client Review turns
approved evidence into a concise decision/outcome story without exposing internal
commands, raw logs, or analyst-only controls.

## Primary Users

- technician/support analyst: diagnoses why Studio, an integration, or a governed
  workflow cannot proceed;
- lead analyst: reviews recent governed runs and prepares client material;
- final client/business owner: understands status, decisions, evidence, and next
  responsibility in clear language.

## User Stories

### US1 - Diagnose Studio and integration health (P1)

A technician opens Operations and sees categorical health for the local Studio
process, package extras, Codex adapter, bundle capability, static gate, optional live
boundary, and frontend assets, each with evidence and a recovery action.

Acceptance intent:

1. No aggregate health score is shown.
2. Diagnostics distinguish missing, misconfigured, incompatible, deferred, failed,
   and healthy states.
3. Credential and workspace data is redacted before display/export.
4. A diagnostic can recommend an action but cannot execute it without the same
   technical approval and readiness policy.

### US2 - Review a redacted run history (P1)

The analyst can inspect recent in-process and optionally committed governed receipts:
what was requested, what tools were proposed, who decided, what changed, which gates
ran, and the categorical result.

Acceptance intent:

1. Run history is reconstructed from normalized events and durable governed receipts,
   not raw provider transcripts.
2. Hidden reasoning, secrets, DSNs, raw prompts marked sensitive, and absolute paths
   never appear.
3. Process-only conversation history is labeled ephemeral and disappears on restart.
4. Durable audit claims cite their committed source.

### US3 - Prepare a client-ready review (P1)

The lead analyst selects approved metrics, decisions, evidence, blockers, and next
responsibilities. Studio previews a simplified client narrative and exports a local,
self-contained review artifact.

Acceptance intent:

1. Only approved/eligible evidence enters the client view.
2. Pending or blocked facts remain visibly pending/blocked and are never softened to
   success.
3. Internal command names, skill names, raw diffs, logs, and absolute paths are absent.
4. The export is accessible, self-contained, reproducible, and uses no remote assets.

### US4 - Let the client respond safely (P2)

Within the authenticated local session, a client can acknowledge a result, request
clarification, or answer a scoped business decision using the Workbench's named-human
boundary.

Acceptance intent:

1. Client actions are explicit, scoped, and revision-bound.
2. Acknowledgment is not treated as approval of a different business judgment.
3. Client feedback becomes a governed prepared item; it does not silently alter
   artifacts or readiness.
4. Expired/stale review packages cannot record decisions.

### US5 - Export a support bundle without secrets (P2)

A technician can generate a local diagnostic bundle containing versions, categorical
health, safe configuration presence, normalized failure events, and gate references,
while excluding credentials and business data.

Acceptance intent:

1. Preview lists every included file/field before export.
2. A secret corpus scan must pass before the bundle is finalized.
3. Raw source data, `.env`, credential files, DSNs, browser cookies, and provider raw
   transcripts are structurally excluded.
4. Export failure leaves no partial archive.

## Provisional Requirements

- **FR-141-001**: Operations MUST present categorical component states with evidence,
  blocker, and recovery action; it MUST NOT calculate a health/readiness score.
- **FR-141-002**: Diagnostics MUST reuse existing `--doctor`, package-contract,
  capability, gate, and adapter probes where available rather than fork checks.
- **FR-141-003**: Diagnostics MUST be read-only until a separately displayed
  technical action receives approval and passes readiness scope.
- **FR-141-004**: Run history MUST use normalized Studio events and governed receipts,
  never hidden reasoning or raw provider protocol logs.
- **FR-141-005**: Ephemeral and durable history MUST be visually and semantically
  distinct.
- **FR-141-006**: Every durable claim in Operations or Client Review MUST cite its
  committed evidence or decision receipt.
- **FR-141-007**: Client Review MUST include only explicitly selected, eligible,
  approved content and preserve blocked/pending categorical wording.
- **FR-141-008**: Client Review MUST hide commands, skills, raw file paths, raw diffs,
  internal logs, provider protocol, and analyst-only controls by default and export.
- **FR-141-009**: Client exports MUST be self-contained local HTML and optionally PDF
  only if a reproducible local renderer is separately accepted; no remote assets.
- **FR-141-010**: Export inputs MUST bind to a workspace revision and become stale
  when governed truth changes.
- **FR-141-011**: Client responses MUST route through spec 140's scoped named-human
  decision/feedback contracts; acknowledgment MUST remain a distinct action.
- **FR-141-012**: Support bundles MUST be assembled from an allowlist of safe fields
  and files, not a redact-after-zipping denylist.
- **FR-141-013**: Support bundles MUST structurally exclude `.env`, data extracts,
  credential stores, cookies, API/auth headers, raw provider transcripts, and
  absolute paths.
- **FR-141-014**: Support-bundle creation MUST be atomic and MUST scan the staged
  content with the existing/new redaction corpus before finalization.
- **FR-141-015**: Accessibility MUST meet WCAG 2.2 AA across technician density,
  client simplicity, print/export, keyboard use, zoom, and reduced motion.
- **FR-141-016**: Responsive layouts MUST preserve the correct primary action and
  decision context from mobile width through large desktop.
- **FR-141-017**: Operations and Client Review MUST remain localhost, single-workspace,
  and authenticated under Foundation's security boundary.
- **FR-141-018**: No diagnostic, export, acknowledgment, or client response may
  advance readiness except through existing authoritative artifacts and gates.
- **FR-141-019**: Existing static dashboard and Foundation/Workbench journeys MUST
  remain backward compatible.
- **FR-141-020**: Implementation MUST NOT begin until specs 139 and 140 are accepted,
  this detailed spec is named-human ratified, and its plan is the sole active fence.

## Provisional Entities

- `ComponentDiagnostic`: categorical state, evidence, blocker, recovery action, and
  safe version/config presence.
- `GovernedRunSummary`: normalized request/outcome timeline plus durable receipt refs.
- `ClientReviewDraft`: revision-bound selection of eligible facts and narrative.
- `ClientReviewArtifact`: self-contained immutable exported review with manifest.
- `ClientAcknowledgment`: scoped acknowledgment distinct from business approval.
- `ClientFeedbackItem`: prepared clarification/feedback routed to analyst workflow.
- `SupportBundleManifest`: allowlisted safe fields/files, hashes, versions, and
  redaction-scan receipt.

## Out of Scope

- SaaS hosting, remote client portal, email delivery, or cloud file sharing;
- organization identity, SSO, RBAC, or cryptographic signer verification;
- raw source-data preview or export;
- arbitrary log download;
- aggregate health, maturity, confidence, or readiness scores;
- automated repair without explicit technical approval;
- redefining metrics, mappings, or readiness in presentation code.

## Promotion Gate

After Workbench acceptance, this outline must be expanded and reviewed from both the
support technician and final-client perspectives. The resulting exact specification,
security/export contracts, plan, and tasks require named-human ratification and the
single active fence. This outline cannot authorize implementation.
