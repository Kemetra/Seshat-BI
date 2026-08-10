# Tasks: Seshat Studio Foundation

**Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md),
[data-model.md](./data-model.md), and [contracts](./contracts/).

**Status**: ratified and ACTIVE for implementation as of 2026-08-10. Phase 1
(governance preconditions) and Phase 2 (package and security skeleton) are closed;
Phase 3 (T009, projection parity tests) is next.

Regression floor for every later phase, from
[`evidence/t003-baselines.md`](./evidence/t003-baselines.md): 5822 passed / 2
pre-existing environmental failures / 23 skipped at T003. After Phase 2: **5896
passed / the same 2 failures / 24 skipped** — 74 tests added, no new failure.

## Phase 1 - Governance Preconditions

- [x] **T001** Record named-human ratification of this exact specification, plan,
  contracts, and task list without agent self-ratification — Ahmed Shaaban,
  2026-08-03. [FR-036]
- [x] **T002** Complete or formally park spec 138 and update the one active Spec Kit
  marker to this plan; run the active-marker contract test. [FR-036] — spec 138 is
  `implemented` (75/75 tasks, US4 deferred by the 2026-08-03 owner amendment);
  `.specify/feature.json` now names `specs/139-seshat-studio-foundation`, both the
  `AGENTS.md` and `CLAUDE.md` SPECKIT fences render that plan, and
  `test_active_spec_kit_markers_agree_and_resolve` passes.
- [x] **T003** Capture baseline results for static dashboard, B1 imports, bundle
  regeneration, package contents, unit tests, and accessibility tooling. [SC-009]
  — recorded in [`evidence/t003-baselines.md`](./evidence/t003-baselines.md):
  5822 passed / 2 pre-existing environmental failures / 23 skipped; dashboard
  92 passed; B1 20 passed; bundles regenerate byte-identically; no `studio` extra and
  no `seshat-studio` script yet. Accessibility tooling is NOT yet available (no
  `studio-ui/`, `npx axe` unavailable) — that arrives with T012, so T032 is blocked
  until then.

## Phase 2 - Package and Security Skeleton

- [x] **T004** Write failing package-contract tests for base-install isolation,
  `studio` extra, `seshat-studio` entry point, static asset inclusion, and missing
  extra/assets diagnostics. [FR-002, FR-005, FR-006]
- [x] **T005** Add the optional dependency and dedicated package/launcher skeleton;
  keep all web imports lazy and outside `seshat.cli`/`seshat.rules`. [FR-002, FR-006]
- [x] **T006** Write failing tests for loopback-only OS-port binding, pinned workspace,
  unsupported workspace, Windows paths, bootstrap exchange, cookie expiry, Host,
  Origin, and unauthenticated access. [FR-001, FR-003, FR-004]
  — 43 assertions in `tests/unit/test_studio_security_boundary.py`, all failing
  first. Covered: loopback-only binding, OS-assigned port, pinned/unsupported
  workspace, Windows and UNC paths, traversal and symlink containment, bootstrap
  exchange and single use, cookie attributes, shutdown invalidation, `Host`, and
  `Origin`. **Two named items are NOT yet covered: time-based cookie EXPIRY and
  UNAUTHENTICATED ACCESS.** Both are HTTP-pipeline behaviours with no surface to
  test until T011 builds the app; `SessionStore` currently invalidates on exchange
  and on explicit shutdown, not on a clock. T011 must add both.
- [x] **T007** Implement immutable launch configuration, session store, security
  middleware, problem responses, and security headers. [FR-001, FR-003, FR-004]
  — **PARTIAL, and deliberately so.** Delivered: the immutable
  `LaunchConfiguration` (one pinned absolute root per process), the digest-only
  `SessionStore` (256-bit token, constant-time compare, one-time exchange), the
  containment resolver, and the `Host`/`Origin` enforcement PREDICATES.
  **NOT delivered: the ASGI middleware, problem responses, and security headers** —
  those need the FastAPI app, which arrives with T011. The predicates are pure and
  stdlib-only so they stay testable without the `studio` extra; T011 must wire them
  into the request pipeline in the contracted order and is not complete until it
  does. Tracked so the remaining half is not mistaken for shipped.
- [x] **T008** Add credential/path redaction unit and property tests before applying
  redaction to errors, diagnostics, logs, and browser responses. [FR-026]
  — session material, DSNs (delegated to `seshat.redaction_core`), authorization
  headers, credential-shaped assignments, and absolute paths, with over-redaction
  guards proving innocent governed text survives. An external adversarial review
  found the first revision implemented only session material and paths, leaving
  FR-026's named DSN/password/token/authorization classes leaking; that gap is now
  closed and pinned by `tests/unit/test_studio_review_findings.py`.
  **Still outstanding for T011**: applying this at the real HTTP boundary. The
  redactor is exercised by tests and by the launcher's own asset diagnostic, but no
  agent event or browser response exists to redact until the app is built. Two
  contract items are also not implemented: "checks the expected file kind" for
  optional reads (Windows device names such as `NUL`/`CON` and NTFS alternate data
  streams are contained but accepted), and a `LaunchConfiguration` re-pin of the
  OS-assigned port after bind (`port` is still `0` when `host_is_allowed` runs, which
  fails CLOSED, so it is a correctness gap rather than a hole).

## Phase 3 - Deterministic Workspace Foundation (US1, US4)

- [x] **T009** Write projection parity tests against existing ready, blocked, empty,
  pending-live, and malformed workspace fixtures. [FR-007, FR-008, FR-009, FR-010,
  SC-002]
- [x] **T010** Implement `WorkspaceProjectionService` as an adapter over existing
  Seshat Python services with a stable revision digest and containment-safe refs.
  [FR-007, FR-008, FR-010]
  — `seshat.studio.projection`. Adapts `status_surface.build_status_projection`;
  derives no readiness. The revision digest is content-addressed and verified
  PATH-INDEPENDENT. **Deliberate divergence from upstream for FR-010**: upstream skips
  an unparseable file by design ("failing loud is RS1's job"), so the projection
  enumerates committed files independently and reports what upstream dropped. An
  omitted stage block is filled with `not_started` + an explicit unknown-state reason
  plus a defect, honouring the contract's seven-stage bound without letting the gap
  read as genuinely not-started.
  Evidence and blocking reasons are emitted as the contract's `EvidenceRef` /
  `BlockingReason` OBJECTS, with `live_state` carrying the [PENDING LIVE PROFILE]
  signal a plain string could not express. A non-canonical status is REFUSED with a
  named defect rather than projected into the closed enum, and `next_action` plus
  table-level blockers are preserved (FR-008 names both).
  **NOT delivered:** (a) `EvidenceRef.source_ref` is the committed string as-is --
  routing it through `config.resolve_contained_path` moves to T011, where a route
  actually dereferences one; (b) `required_authority` and `forbidden_scope` are empty
  because no committed source populates them yet; (c) `WorkspaceIdentity.branch` is
  null pending a git read. Payload conformance is now pinned by
  `test_studio_projection_conforms_to_contract.py`, which validates every fixture
  state against `studio-api.yaml` -- the check whose absence let three contract
  violations pass 25 green tests.
- [ ] **T011** Implement typed bootstrap, workspace, table, decision-summary, and
  health endpoints matching `studio-api.yaml`. [FR-034]
  **Also carries the deferred half of Phase 2**, which has no testable surface until
  this app exists: (a) the ASGI security middleware applying the contracted
  enforcement ORDER, (b) redacted problem responses, (c) security headers, (d)
  time-based cookie expiry, (e) unauthenticated-access refusal, and (f) the
  `authentication_mode` field required on `BootstrapState` by FR-013a. Items (a)-(c)
  are T007's remainder, (d)-(e) are T006's, and the Phase 2 predicates in
  `seshat.studio.session` are what (a) must wire in. Also from the Phase 2 review:
  (g) apply `seshat.studio.redaction.redact_for_boundary` at the real response and
  event boundary, (h) add the file-kind check the security contract requires for
  optional reads, and (i) re-pin `LaunchConfiguration.port` to the OS-assigned port
  after bind, since `host_is_allowed` is otherwise compared against `0`.
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
  accept every failure state without *automatic* API-key fallback. (Wording aligned
  with FR-013 as amended 2026-08-04: the prohibition is on a silent or automatic
  switch to a billed path, not on the explicitly operator-configured alternate mode
  of T023a.) [SC-003, SC-004]
- [ ] **T023a** Implement the alternate API-key/access-token `AgentBridge` as an
  explicitly operator-configured mode at the existing provider-neutral seam. Assert
  it is never selected by inference, by degradation, or as a response to any bridge
  health state, and that the active authentication mode is named both in the
  interface and in `GET /bootstrap/state`. Subscription sign-in remains the default;
  SC-010 certifies only the subscription path. [FR-013a]

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
- [ ] **T030** Register the capability in the canonical inventory
  (`docs/capabilities/capabilities.yaml`) **and** in the public command surface
  authority (`distribution/public-command-surface.yaml`), then regenerate both
  bundles; verify clean byte-identical regeneration. A capability registered in only
  one of the two surfaces is a half-shipped verb. [FR-027]
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
