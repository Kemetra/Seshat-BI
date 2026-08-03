# Tasks: Seshat Studio Foundation

**Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md),
[data-model.md](./data-model.md), and [contracts](./contracts/).

**Status**: planned, not authorized for implementation. T001 and T002 are hard
preconditions; no later task may start while either is open.

## Phase 1 - Governance Preconditions

- [ ] **T001** Record named-human ratification of this exact specification, plan,
  contracts, and task list without agent self-ratification. [FR-036]
- [ ] **T002** Complete or formally park spec 138 and update the one active Spec Kit
  marker to this plan; run the active-marker contract test. [FR-036]
- [ ] **T003** Capture baseline results for static dashboard, B1 imports, bundle
  regeneration, package contents, unit tests, and accessibility tooling. [SC-009]

## Phase 2 - Package and Security Skeleton

- [ ] **T004** Write failing package-contract tests for base-install isolation,
  `studio` extra, `seshat-studio` entry point, static asset inclusion, and missing
  extra/assets diagnostics. [FR-002, FR-005, FR-006]
- [ ] **T005** Add the optional dependency and dedicated package/launcher skeleton;
  keep all web imports lazy and outside `seshat.cli`/`seshat.rules`. [FR-002, FR-006]
- [ ] **T006** Write failing tests for loopback-only OS-port binding, pinned workspace,
  unsupported workspace, Windows paths, bootstrap exchange, cookie expiry, Host,
  Origin, and unauthenticated access. [FR-001, FR-003, FR-004]
- [ ] **T007** Implement immutable launch configuration, session store, security
  middleware, problem responses, and security headers. [FR-001, FR-003, FR-004]
- [ ] **T008** Add credential/path redaction unit and property tests before applying
  redaction to errors, diagnostics, logs, and browser responses. [FR-026]

## Phase 3 - Deterministic Workspace Foundation (US1, US4)

- [ ] **T009** Write projection parity tests against existing ready, blocked, empty,
  pending-live, and malformed workspace fixtures. [FR-007, FR-008, FR-009, FR-010,
  SC-002]
- [ ] **T010** Implement `WorkspaceProjectionService` as an adapter over existing
  Seshat Python services with a stable revision digest and containment-safe refs.
  [FR-007, FR-008, FR-010]
- [ ] **T011** Implement typed bootstrap, workspace, table, decision-summary, and
  health endpoints matching `studio-api.yaml`. [FR-034]
- [ ] **T012** Create the React/TypeScript shell, generated API types, local design
  tokens, and offline build pipeline; copy build output into the packaged static
  directory through one documented build command. [FR-005, FR-033]
- [ ] **T013** Write failing component tests, then implement Command Room, table
  journey, evidence/blocker details, next action, first-arrival, and input-defect
  states without command names or scores. [US1, FR-009, FR-032]
- [ ] **T014** Add the seven distinct agent health presentations while retaining all
  deterministic workspace interactions. [US4, FR-024, FR-025]

## Phase 4 - Stable Events and Fake Agent (US2)

- [ ] **T015** Write event-state tests for monotonic sequence, bounded retention,
  Last-Event-ID replay, expired replay, duplicate input, late-after-terminal events,
  and interruption. [FR-015, FR-016]
- [ ] **T016** Implement immutable event contracts, state machine, redacted buffer,
  thread store, and same-origin SSE endpoint with no database. [FR-015, FR-016,
  FR-035]
- [ ] **T017** Implement `FakeAgentBridge` from deterministic scenarios and contract
  tests shared by every bridge implementation. [FR-014]
- [ ] **T018** Write browser tests and implement chat composer, streamed response,
  public plan/tool activity, reconnect, interruption, draft preservation, and final
  workspace refresh. [FR-023]

## Phase 5 - Codex Subscription Bridge (US2, US4)

- [ ] **T019** Record the installed Codex version, generate its app-server JSON
  schemas into a temporary directory, and derive minimal sanitized fixtures covering
  `initialize`/`initialized`, account and rate-limit reads, managed ChatGPT login,
  thread, turn, visible messages, tool events, JSON-RPC-correlated command/file
  approvals, quota, sign-out, incompatible or experimental required methods,
  malformed frames, stderr secrets, and EOF. Do not commit the full generated
  schema bundle. [FR-011 - FR-015, FR-024]
- [ ] **T020** Write failing JSON-RPC correlation and normalization tests, then
  implement the version-tolerant stdio client without shell interpolation. [FR-011,
  FR-014, FR-015]
- [ ] **T021** Implement Codex process lifecycle, protocol probe, health classifier,
  official login delegation, cancellation, clean shutdown, and crash recovery.
  Record and enforce the tested minimum/maximum Codex CLI range; a version outside
  it is incompatible until its generated schema and handshake fixtures pass.
  [FR-011, FR-012, FR-013, FR-024]
- [ ] **T022** Implement context construction for read-only and propose-change modes;
  include current allowed/forbidden scope and never include credentials. [FR-017,
  FR-018, FR-026]
- [ ] **T023** Run the bridge contract suite against fake and production adapters;
  accept every failure state without API-key fallback. [SC-003, SC-004]

## Phase 6 - Technical Approval Boundary (US3)

- [ ] **T024** Write failing tests for paused approval, exact scope display,
  allow-once, deny, readiness-prohibited allow, stale/repeated decisions, and
  prepared business judgment. [FR-018, FR-019, FR-020, FR-021, FR-022, SC-005]
- [ ] **T025** Implement provider approval normalization and readiness
  forbidden-scope evaluation before an allow control is exposed. [FR-018, FR-021]
- [ ] **T026** Implement the accessible technical approval panel and one-time relay;
  browser code performs no side effect. [FR-019, FR-020]
- [ ] **T027** Implement read-only prepared decision summaries with no mutation route
  and assert OpenAPI contains no business-approval endpoint. [FR-022]

## Phase 7 - Agent-First Launch and Distribution (US5)

- [ ] **T028** Write failing capability and bundle contracts for the new
  `seshat-studio` consumer skill and its optional-dependency requirement. [FR-027]
- [ ] **T029** Author the canonical Studio skill with natural-language launch,
  workspace validation, single-instance reuse, two-lane missing-extra remedy, and
  technical troubleshooting detail. [FR-027, FR-028]
- [ ] **T030** Register the capability in the canonical inventory and regenerate both
  bundles; verify clean byte-identical regeneration. [FR-027]
- [ ] **T031** Test Codex full launch and Claude deterministic launch/native handoff;
  assert no Claude credential bridge is present. [FR-029]

## Phase 8 - Accessibility, Packaging, and Acceptance

- [ ] **T032** Run keyboard, focus, contrast, reduced-motion, non-color status,
  responsive layout, and axe browser acceptance over all critical states; fix every
  critical or serious finding. [FR-031, SC-007]
- [ ] **T033** Build sdist/wheel and test clean base and Studio-extra installs with no
  Node runtime and no remote asset fetch. [SC-008]
- [ ] **T034** Run security-boundary negative tests and verify response/log/event
  corpus contains no injected secret, token, absolute path, or workspace content.
  [SC-006]
- [ ] **T035** Run existing dashboard and full repository regression gates; reconcile
  generated bundles and run `seshat check` and `semantic-check`. [FR-030, SC-009]
- [ ] **T036** Run external signed-in Codex acceptance and record versioned,
  redacted subscription evidence with no API credential. [SC-001, SC-003, SC-010]
- [ ] **T037** Map SC-001 through SC-010 to fresh evidence, review every FR and edge
  case, and request independent code review before claiming Foundation complete.

## Dependencies

```text
T001 -> T002 -> T003 -> package/security -> deterministic workspace
     -> events/fake bridge -> Codex bridge -> approvals -> launch/distribution
     -> accessibility/package/external acceptance -> requirement review
```

- Frontend component work depends on typed deterministic endpoints but may proceed
  before the real Codex bridge by using the fake bridge.
- Codex bridge work depends on stable event and bridge contracts.
- Technical approvals depend on both readiness scope and provider event mapping.
- Bundle generation depends on the Studio launcher and install remedy being final.
- External acceptance is evidence for the implementation, never a substitute for
  deterministic tests.
