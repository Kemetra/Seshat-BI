# Tasks: Seshat Studio Foundation

**Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md),
[data-model.md](./data-model.md), and [contracts](./contracts/).

**Status**: ratified and ACTIVE for implementation as of 2026-08-10. Phase 1
(governance preconditions) and Phase 2 (package and security skeleton) are closed, and
Phase 3 is underway: T009/T010 (the deterministic projection) are done; **T011 (typed
endpoints) is next** and carries the deferred half of Phase 2 plus three items from the
Phase 3 review — see its entry.

Four contract defects were found and fixed before T010 was written, because a truthful
projection could not have validated against the shipped contract: `StageState.status`
declared a status (`ready_for_review`) that exists nowhere in the repository,
`ReadinessStage` dropped the `_ready` suffix from all seven identifiers, `current_stage`
was non-nullable while the upstream authority emits null, and the seven-stage bound
needed its rationale recorded. Both enums are now pinned to
`schemas/agent-status.schema.json` and `status_surface._STAGE_ORDER` by
`tests/unit/test_studio_contract_matches_authority.py`, and every fixture state is
validated against `studio-api.yaml` by
`tests/unit/test_studio_projection_conforms_to_contract.py`.

Regression floor for every later phase, from
[`evidence/t003-baselines.md`](./evidence/t003-baselines.md): 5822 passed / 2
pre-existing environmental failures / 23 skipped at T003. After Phase 2: 5896 passed /
the same 2 failures / 24 skipped. After T009-T010: **5979 passed / the same 2 failures /
24 skipped**.

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
- [x] **T011** Implement typed bootstrap, workspace, table, decision-summary, and
  health endpoints matching `studio-api.yaml`. [FR-034]
  — `seshat.studio.app`. All seven deterministic routes, with the security middleware
  applying the contracted Host -> Origin -> session order; the six `/agent/threads/*`
  routes are Phase 4. Delivered from the deferral list below: (a) middleware, (b)
  problem responses, (c) security headers, (d) time-based cookie expiry (injectable
  monotonic clock), (e) unauthenticated refusal, (f) `authentication_mode`, (g)
  `scrub_payload` at the real response boundary, (i) `with_bound_port`. The launcher
  now serves, with `--no-serve` to exercise startup without a port.
  **STILL NOT DELIVERED: (h)** the security contract's "checks the expected file kind"
  for optional reads. No route dereferences an evidence file yet, so there is nothing
  to check the kind OF; it moves to whichever task first reads an evidence path.
  `EvidenceRef.source_ref` likewise remains the committed string, uncontained, for the
  same reason. Both are recorded here rather than absorbed.
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
- [x] **T012** Create the React/TypeScript shell, generated API types, local design
  tokens, and offline build pipeline; copy build output into the packaged static
  directory through one documented build command. [FR-005, FR-033]
  — `studio-ui/` (Vite + React 19 + TypeScript, strict). Types are GENERATED from
  `studio-api.yaml` by `scripts/generate_studio_types.py` and drift-pinned, so the
  browser cannot hold a different payload shape than the server serves. One command,
  `python scripts/build_studio_frontend.py`, installs, tests, typechecks, bundles, and
  stages `dist/` into `src/seshat/studio/static/`. The bundle is gitignored and
  hatchling honours VCS ignore rules, so `artifacts` in `pyproject.toml` is what makes
  the wheel actually carry it -- without that entry the wheel shipped ZERO frontend
  files while every test stayed green, because they compared paths and read config
  instead of opening a wheel. Now pinned by a test that builds a real wheel and looks
  inside, and by CI's `Build the Studio frontend` step, without which all seven
  FR-005/FR-033 tests skipped and enforced nothing.
  FR-033 is enforced against the BUILT output by asserting on loading mechanisms
  (`src`/`href`, CSS `@import`/`url()`), not by grepping for `https://` -- the bundle
  legitimately carries inert URL strings that are never fetched. Build artifacts are
  gitignored: end users install a wheel, not a checkout.
  **NOT T012's scope, and not done:** the Command Room detail views. The shell renders a
  workspace heading, a first-arrival state, an input-defect list, and a per-table status
  badge, which is the FRAME. T013 owns the table journey, evidence/blocker details, next
  action, and the full first-arrival and input-defect presentations, and T014 owns the
  seven agent-health states.
- [x] **T013** Write failing component tests, then implement Command Room, table
  journey, evidence/blocker details, next action, first-arrival, and input-defect
  states without command names or scores. [US1, FR-009, FR-032]
  — `studio-ui/src/components/TableJourney.tsx`, wired into the shell so it is reachable
  rather than dead code. All seven stages in the authority's order as an ORDERED list, so
  a screen-reader user perceives the sequence structurally; the current stage carries
  `aria-current="step"`; evidence shows its `live_state` so a [PENDING LIVE PROFILE]
  reference cannot read as verified; blockers show their concrete message.
  US1 scenario 2's "leaves Silver and later work LOCKED" is expressed WITHOUT inventing
  a fifth status: a gated stage keeps its `not_started` status (FR-008 pins the
  vocabulary) and gains a separate signal derived purely from position, saying "Waiting
  for Mapping to clear". Nothing is locked once the current stage passes -- calling later
  work blocked then would be a fabricated obstacle.
  **The pending decision count US1 names is NOT rendered, and that is deliberate.** An
  interim revision did render it, then a review showed `pending_decision_count` is a
  dataclass DEFAULT of 0 that nothing computes and `/decisions` returns an empty list -- so
  "No decisions are waiting" asserted workspace truth from a hardcoded zero while
  `mappings/finance_gl_actuals/approval-request-model-integrity.md` sat unresolved. Saying
  nothing is honest; asserting none is not. Wiring it to `approval_inbox`'s open-request
  projection is upstream work deferred to a follow-on task, and a test pins the absence so
  the claim cannot return unwired.
  **`forbidden_scope` is not rendered, for the same reason.**
  `projection._journey_for` never sets it, so it is a dataclass default -- empty for all
  four committed tables. A component that rendered it showed nothing in production while
  its test passed on a hand-built fixture.
  `readiness_projection._table_projection` DOES compute the real restrictions (no Silver
  before Mapping, no dashboard before contracts); wiring it into the snapshot is upstream
  work for a follow-on task, and a test pins the absence.
  **`ActionSummary.requires_named_human` is always False for the same reason.**
  `status_surface._project_table` -- the upstream this projection reads -- never emits
  `required_authority`, so an interim "read it from the source" fix looked correct and was
  INERT. `agent_next.build_table_next_document` does expose an authority, as a STRING
  rather than a list; adopting it is new upstream integration with its own contract
  questions, so Studio claims no approval requirement it cannot substantiate.
  FR-032: stage identifiers render as human labels ("Mapping", never `mapping_ready`),
  and every raw source reference sits behind an explicit `<details>` disclosure.
- [x] **T014** Add the seven distinct agent health presentations while retaining all
  deterministic workspace interactions. [US4, FR-024, FR-025]
  — `studio-ui/src/components/AgentHealth.tsx`. All seven contract states
  (`healthy`, `missing`, `signed_out`, `incompatible`, `quota_limited`, `crashed`,
  `disabled`) get a DIFFERENT headline, explanation, and recovery action, pinned by a
  test asserting seven distinct headlines -- "distinct" means an analyst can tell
  signed-out from quota-limited, not that a banner changes colour. The server's wording
  is preferred when it sends any, with local text as the fallback so an empty server
  string never renders as blank.
  FR-025 is enforced by a parametrised shell test over all seven states asserting the
  table journey and stage list are STILL present: the notice is strictly additive and
  never gates, wraps, or replaces the deterministic views. A banner that blanked the page
  on a crash would satisfy FR-024 and break FR-025.
  `role="status"` (implicitly polite) rather than `alert` -- agent health is context, not
  an emergency. The agent version sits behind the FR-032 disclosure.

Phase 3 is COMPLETE. The deterministic Command Room reads one workspace truthfully:
projection, endpoints, frontend, journey, and health.

## Phase 4 - Stable Events and Fake Agent (US2)

- [x] **T015** Write event-state tests for monotonic sequence, bounded retention,
  Last-Event-ID replay, expired replay, duplicate input, late-after-terminal events,
  and interruption. [FR-015, FR-016]
  All seven named cases plus two boundaries the named list does not cover: the
  CONTIGUOUS resume (`last_event_id == lowest_retained - 1`, which must be served, not
  refused — refusing it would break every ordinary reconnect) and a fresh connect to an
  empty thread. The event-type enum is pinned against the contract in BOTH directions:
  instance validation alone catches only this code emitting a bad type, never the
  contract gaining one this module would refuse at record time.
- [x] **T016** Implement immutable event contracts, state machine, redacted buffer,
  thread store, and same-origin SSE endpoint with no database. [FR-015, FR-016,
  FR-035]
  Redaction happens on the way INTO the buffer, since replay reads the buffer and a leak
  stored is a leak eventually served. The stream authenticates on the existing
  `HttpOnly` cookie — `EventSource` cannot set request headers, and the usual
  query-string token workaround would write the credential into access logs and browser
  history; the route takes no exemption from the three enforcement steps.
  **The stream is a finite replay, deliberately** (`SSE_RETRY_MILLISECONDS`): it serves
  what is retained and closes, and the browser reconnects with `Last-Event-ID`, so the
  resume path is exercised on every poll instead of only after a failure. The cost is
  stated rather than hidden — the retry interval IS the perceived reply latency. A
  held-open stream is the alternative and would change `agent_routes` only.

  The client honours that interval by NOT intervening: it registers no `onerror`
  reconnect, because native `EventSource` reconnect already waits the declared interval
  and resends `Last-Event-ID`. A first pass hand-rolled the loop instead, calling
  `close()` and reconnecting synchronously — a zero-delay busy loop that also discarded
  `retry:` entirely, since `close()` permanently cancels native reconnect. The knob was
  documented as the perceived latency while the client could not read it.
- [x] **T017** Implement `FakeAgentBridge` from deterministic scenarios and contract
  tests shared by every bridge implementation. [FR-014]
  The shared suite is `BRIDGE_FACTORIES` in `test_studio_agent_bridge.py`: Phase 5's
  Codex bridge appends itself and inherits every assertion rather than re-deriving them.
  The `read_only` boundary is enforced AT THE BRIDGE, not by filtering downstream — a
  filtered event means the agent already attempted the change and the refusal was
  cosmetic.
- [x] **T018** Write browser tests and implement chat composer, streamed response,
  public plan/tool activity, reconnect, interruption, draft preservation, and final
  workspace refresh. [FR-023]
  A controllable `FakeEventSource` makes reconnect and `Last-Event-ID` assertable; jsdom
  has no `EventSource`, so a looser stub would have left both untested. Events are keyed
  by `sequence` rather than arrival order, because a reconnect may legitimately
  redeliver the boundary event. A tool with no `public_label` falls back to a neutral
  phrase and NEVER to `name` — the `?? payload.name` spelling looks defensive and is the
  FR-032 leak.

  **NOT included, deliberately:** no approval control. `approval_required` and
  `file_change_proposed` render as inert activity with no actionable button, because
  approval semantics are T024–T027; offering one now would let someone believe they had
  approved something. A test pins the absence of any approve/apply/reject control so the
  boundary cannot be crossed before the semantics exist.

## Phase 5 - Codex Subscription Bridge (US2, US4)

- [x] **T019** Record the installed Codex version, generate its app-server JSON
  schemas into a temporary directory, and derive minimal sanitized fixtures covering
  `initialize`/`initialized`, account and rate-limit reads, managed ChatGPT login,
  thread, turn, visible messages, tool events, JSON-RPC-correlated command/file
  approvals, quota, sign-out, incompatible or experimental required methods,
  malformed frames, stderr secrets, and EOF. Do not commit the full generated
  schema bundle. [FR-011 - FR-015, FR-024]
- [x] **T020** Write failing JSON-RPC correlation and normalization tests, then
  implement the version-tolerant stdio client without shell interpolation. [FR-011,
  FR-014, FR-015]
- [x] **T021** Implement Codex process lifecycle, protocol probe, health classifier,
  official login delegation, cancellation, clean shutdown, and crash recovery.
  Record and enforce the tested minimum/maximum Codex CLI range; a version outside
  it is incompatible until its generated schema and handshake fixtures pass.
  [FR-011, FR-012, FR-013, FR-024]
  Shipped as `CodexSession` (three explicit pipes, never inherited and never
  `DEVNULL` per issue #557; stdout feeding `CodexProtocolReader` on its own thread;
  a separately drained and redacted stderr; `close()` bounded by one monotonic
  deadline) and `CodexBridge`, which joins `BRIDGE_FACTORIES` so every shared
  contract assertion runs once per bridge. Crash and EOF classify through
  `classify_health` to `crashed`, never a silent `ready`. Driven throughout by a
  scripted child replaying committed fixtures over a REAL pipe, because a mock
  cannot deadlock and deadlock is this layer's actual risk.
  Two defects were found by tests rather than by reading, both now fixed and
  pinned: a settled turn could be REOPENED by a provider frame arriving after
  `turn/completed`, yielding two terminals for one turn; and
  `CodexProtocolReader` rejected every frame a real Codex build emits, because it
  required a `jsonrpc` field the app-server does not send and its generated schema
  never declares — the committed fixtures carried that field only because they and
  the client were written from the same assumption.
  **Not included:** answering approval server-requests (`item/*/requestApproval`)
  is T024–T027's surface and normalizes to nothing today. The shutdown-versus-
  stderr limit recorded on `close()` is a physical constraint, not an open bug: a
  child terminated before the OS schedules it never writes, so there is nothing to
  capture.
- [x] **T022** Implement context construction for read-only and propose-change modes;
  include current allowed/forbidden scope and never include credentials. [FR-017,
  FR-018, FR-026]
- [ ] **T023** Run the bridge contract suite against fake and production adapters;
  accept every failure state without *automatic* API-key fallback. (Wording aligned
  with FR-013 as amended 2026-08-04: the prohibition is on a silent or automatic
  switch to a billed path, not on the explicitly operator-configured alternate mode
  of T023a.) [SC-003, SC-004]
- [x] **T023a** Implement the alternate API-key/access-token `AgentBridge` as an
  explicitly operator-configured mode at the existing provider-neutral seam. Assert
  it is never selected by inference, by degradation, or as a response to any bridge
  health state, and that the active authentication mode is named both in the
  interface and in `GET /bootstrap/state`. Subscription sign-in remains the default;
  SC-010 certifies only the subscription path. [FR-013a]

## Phase 6 - Technical Approval Boundary (US3)

- [x] **T024** Write failing tests for paused approval, exact scope display,
  allow-once, deny, readiness-prohibited allow, stale/repeated decisions, and
  prepared business judgment. [FR-018, FR-019, FR-020, FR-021, FR-022, SC-005]
- [x] **T025** Implement provider approval normalization and readiness
  forbidden-scope evaluation before an allow control is exposed. [FR-018, FR-021]
- [x] **T026** Implement the accessible technical approval panel and one-time relay;
  browser code performs no side effect. [FR-019, FR-020]
- [x] **T027** Implement read-only prepared decision summaries with no mutation route
  and assert OpenAPI contains no business-approval endpoint. [FR-022]

  **T027 closed 2026-08-13** (after being unchecked earlier the same day on an
  adversarial review). The refuted half now ships: `PendingApprovals`
  `.prepared_for_named_human()` reads the LIVE `named_human` envelopes the ledger
  was already collecting, and `approvals.prepared_summary()` projects each into the
  contract's five-field `PreparedDecisionSummary`. `/decisions` returns them
  through the same `_redact` boundary pass every other projection uses, because
  `affected_scope` carries readiness sentences whose fail-closed branch can name a
  path. Suite: `tests/unit/test_studio_prepared_summaries.py` (7). Falsified:
  removing the `named_human` filter fails
  `test_a_technical_approval_is_not_a_business_decision` and nothing else.

  **Phase 6 evidence 2026-08-13 (backend only — every box above left unchecked).**
  Built on branch `studio-2` from `46243b5`; design at
  `docs/superpowers/specs/2026-08-13-studio-technical-approval-boundary-design.md`,
  plan at `docs/superpowers/plans/2026-08-13-studio-technical-approval-boundary.md`.

  Shipped: `src/seshat/studio/approvals.py` (authority split, fail-closed readiness
  lookup, decide-once ledger) and the contract's `respondToToolApproval` route in
  `agent_routes.py`. **`technical_approvals` stays `False`** — see the delivery gap
  below; `business_decision_recording` remains const `False`.

  Suites: `tests/unit/test_studio_approvals.py` (19) and
  `tests/unit/test_studio_approval_routes.py` (15) — **34 passed**. Full Studio
  sweep **474 passed**; `pytest -m unit` **5686 passed**; `ruff format --check` and
  `ruff check` clean; `seshat check` exits 0; `seshat semantic-check` 0 findings.

  Invariants proven, each in its positive form: a `named_human` approval normalizes
  to `allow_permitted is False` and the route answers **403**; an unknown or missing
  `required_authority` degrades to `named_human`, never `technical`; a readiness
  lookup that raises returns a refusal sentence rather than an empty tuple; any
  decision burns the id, so a deny cannot be resubmitted as an allow; an
  unrecognized `decision` value is refused **422** and leaves the approval live; an
  approval is not decidable through another thread's URL; and no mutating verb
  reaches any decision path, asserted by HTTP METHOD rather than path name
  (`/decisions` legitimately exists as a contract-specified GET). The readiness
  chain is proven end to end without monkeypatch in
  `test_a_real_readiness_gate_blocks_an_allow_end_to_end`: the real
  `build_table_next_document` forbids 9 scopes on a fresh workspace, and one of its
  own sentences reaches the analyst in the 403 body.

  **Why these tasks stay open.** Four gaps, none of them cosmetic:
  - **The decision is ACCEPTED but never DELIVERED — this is the big one.** The
    route validates a decision and burns its id, but nothing sends it to a provider:
    `AgentBridge` exposes `run_turn` and `describe` and no respond seam. Real Codex
    sends `item/*/requestApproval` as a JSON-RPC **server request carrying an `id`**
    (`tests/fixtures/codex_app_server/approvals.jsonl`) and waits for a response
    keyed to it, so a real turn driven this way would hang. The 204-then-409
    sequence the tests assert is the ledger's own bookkeeping, not an observable
    provider effect. `technical_approvals` is therefore still `False`, and
    `test_the_bridge_protocol_has_no_respond_seam_yet` will fail the moment a seam
    lands — forcing the flag to be reconsidered in the same change.
  - **No UI.** T026 names an *accessible approval panel*; this is the backend route
    only. The frontend belongs to Phases 7–8, and `studio-ui/` has no
    `node_modules` here, so `Conversation.test.tsx:242` — the Phase 4 test pinning
    the ABSENCE of an actionable control — could not be run. It is unaffected by
    construction (no frontend file was touched), which is an argument, not a
    measurement.
  - **The pause is registration, not a state transition.** An emitted approval is
    registered so the relay can decide it, and `awaiting_technical_approval` is
    confirmed present in the contract's enum, but no code yet reports a thread as
    being in that state.
  - **Approval lifetime is bounded by COUNT, not by turn.** `_finish_turn`
    deliberately does not drop a thread's approvals: Phase 4 streams
    `approval_required` as inert activity beside a `turn_completed` in the SAME turn,
    so an approval outliving its turn is normal, and evicting there made a
    just-streamed approval undecidable the instant it appeared. `abandon_thread`
    exists and is tested, unused until a real paused-turn model needs it.
  - **Two pre-existing failures**, both proven red on clean `46243b5` before this
    work and both untouched by it: `test_studio_generated_types` (regenerating
    strips two unrelated comments from another session's `authentication_mode`
    change, so it was deliberately not regenerated) and
    `test_cli_identity_version` (installed `0.8.1` vs source `0.8.2`).

  A human closes these boxes.

  **Phase 6 status re-verified 2026-08-13 (later the same day, on `e069e46d`).**
  The record above was written before #626, #628, and #630 merged. Three of its
  five gaps are now closed and one of its two "pre-existing failures" no longer
  reproduces. Superseding facts, each measured rather than argued:

  - **Delivery closed.** `approval_delivery.deliver_decision` answers the
    `item/*/requestApproval` server request on the `id` Codex blocks on;
    `approval_routes.py` burns the ledger id and *then* delivers, so a provider
    write is attempted at most once per approval. `technical_approvals` is now
    `True` (`app.py:136`), asserted together with the seam in
    `test_the_advertised_capability_is_backed_by_a_reachable_delivery_seam`. The
    tripwire `test_the_bridge_protocol_has_no_respond_seam_yet` is gone, as its
    own design intended.
  - **The paused turn survives.** #630 discriminated "provider wedged" from
    "provider waiting on a human": `idle_timeout` (30s) and `approval_timeout`
    (300s) are separate windows, and a paused timeout reports
    `approval_not_decided`, not `provider_error`.
  - **Approval suites green.** `test_studio_approvals` + `test_studio_approval_routes`
    + `test_studio_approval_reachability` + `test_studio_approval_pause` —
    **50 passed**.
  - **`test_cli_identity_version` no longer fails, but is not fully verified
    either.** It is a FILE of 6 tests: 5 pass and
    `test_version_resolver_matches_pyproject_when_installed` **SKIPS** with
    "seshat-bi is not installed in this environment". The version-resolution
    assertion therefore never executed. Recorded as "not red" rather than
    "passing": claiming a skipped assertion as a pass is the same
    stale-global-install phantom that produced the original 0.8.1-vs-0.8.2
    report.
  - **`test_studio_generated_types` is still red, and the diagnosis above is
    right but incomplete.** Regenerating does drop two comment blocks — because
    `types.ts` was hand-edited after generation and
    `scripts/generate_studio_types.py` emits no per-field comments at all. The
    red is therefore permanent by construction, not a transient conflict. The
    prose is not lost by regenerating: `studio-api.yaml:392,400` already carries
    the same reasoning as `description:` on `agent_provider` and
    `agent_provider_detail`. Regeneration is semantically lossless (field
    reorder + comments; TS ignores field order).

  **T025 is checked on this evidence.** Its normalization and fail-closed
  readiness evaluation ship in `approvals.py:106-145`. "Before an allow control
  is exposed" is an ORDERING constraint on when the evaluation runs, not a
  dependency on a control existing, and `approval_routes.py:68-74` documents
  that ordering.

  **T027 was checked here in an earlier revision of this block and has been
  UNCHECKED.** An adversarial review refuted it and the refutation holds. T027
  has two clauses and only one ships:

  - The no-mutation-route half is real, asserted by HTTP METHOD rather than
    path name, and `business_decision_recording` is const `False` (FR-022).
  - **"Read-only prepared decision summaries" do not exist.** The entire
    implementation is `return {"items": []}` (`app.py:320-322`) — a hardcoded
    empty list with zero producers anywhere in `src/`. Meanwhile
    `studio-api.yaml:84-100` defines a full `PreparedDecisionSummary` schema.
    The contract promises a shape the code never builds.

  That is this repo's `tests-pass-code-unreachable` class: 50 green tests beside
  an unimplemented clause. Checking it would have committed, in the very commit
  that documents the defect class, the defect it documents.

  **T024, T026, and T027 stay open, for reasons the earlier record could not
  have seen:**

  - **T024's "exact scope display" is unproven against the real payload.** Two
    producers emit incompatible shapes. `FakeAgentBridge` sends
    `{approval_id, question, required_authority}`; real Codex sends
    `{approval_id, required_authority, action, target, reason, scope, risk,
    provider_request_id}` and **no `question`**. The renderer narrows on
    `question` only (`eventPayload.ts:74-75`), so every real Codex approval
    renders the fallback "A decision is being prepared." A scope-display test
    written against the fake proves nothing about the path that matters.
  - **T026 is blocked on a contract gap, not just on missing UI.** FR-021
    requires the allow control to be ABSENT when readiness forbids the scope,
    but `ApprovalEnvelope.allow_permitted` and `.forbidden_reasons` never cross
    the wire — the browser receives only `required_authority`. A panel on
    today's payload could discover a forbidden scope only by offering Allow and
    rendering the 403, which inverts the requirement. The payload must be
    widened first.
  - **The Phase 6 boundary test does not guard the boundary.** The assertion at
    `Conversation.test.tsx:265` (inside the `it(...)` declared at `:242`)
    queries for no button matching `/approve|apply|reject/i`, but the decision
    enum is `allow_once`/`deny`. A panel labelled "Allow once"/"Deny" passes it
    untouched. T026 must rewrite that test deliberately; it will not fail as a
    natural signal.

  Design for the remaining work:
  `docs/superpowers/specs/2026-08-13-studio-approval-panel-design.md`.
  A human still closes T024 and T026.

  **Superseded 2026-08-13 (later, on merged `main`): every blocker above is now
  closed, and T024/T026 are checked.** The three reasons were written when the panel
  did not exist; each was answered by work that has since merged, so leaving the boxes
  open would now misreport the opposite direction — the same defect this record was
  written to correct.

  - **T026's contract gap closed (#632).** `allow_permitted` and `forbidden_reasons`
    now cross the wire, and `provider_request_id` is stripped from the stream.
    `test_studio_approval_wire_payload` (11) pins it, falsified by neutering the pump
    caller.
  - **T024's exact-scope display is proven against the REAL payload (#633).** The
    panel renders `action`/`target`/`scope`/`risk` and no longer depends on the fake
    bridge's `question`; one test drops `question` entirely and asserts the scope still
    renders. `ApprovalPanel.test.tsx` (19) + 4 routing tests in
    `Conversation.test.tsx`.
  - **The boundary test was rewritten deliberately, not waited on (#633).** It
    asserted no button matching `/approve|apply|reject/i` while the enum is
    `allow_once`/`deny`, so a panel labelled "Allow once"/"Decline" would have passed
    it untouched. Four routing tests replace it, each pinning which approvals become
    decidable — live yes; late, id-less, and `file_change_proposed` no.

  FR-021 is enforced as ABSENCE rather than a disabled control, falsified by weakening
  `mayAllow` to the authority half alone (fails exactly the 2 tests that pin it, and
  one `Conversation` test after an adversarial review found the allow path had no
  integration coverage). Frontend suite **133 passed**; studio suite **565 passed** on
  merged `main`.

## Phase 7 - Agent-First Launch and Distribution (US5)

- [x] **T028** Write failing capability and bundle contracts for the new
  `seshat-studio` consumer skill and its optional-dependency requirement. [FR-027]
- [x] **T029** Author the canonical Studio skill with natural-language launch,
  workspace validation, single-instance reuse, two-lane missing-extra remedy, and
  technical troubleshooting detail. [FR-027, FR-028]
- [x] **T030** Register the capability in the canonical inventory
  (`docs/capabilities/capabilities.yaml`) **and** in the public command surface
  authority (`distribution/public-command-surface.yaml`), then regenerate both
  bundles; verify clean byte-identical regeneration. A capability registered in only
  one of the two surfaces is a half-shipped verb. [FR-027]
- [x] **T031** Test Codex full launch and Claude deterministic launch/native handoff;
  assert no Claude credential bridge is present. [FR-029]

  **Phase 7 closed 2026-08-13, merged as #634.** `.claude/skills/seshat-studio/SKILL.md`
  ships in both generated bundles, classified `ships: true` +
  `consumer-capability` — the first such combination in the inventory, and permitted by
  design rather than by omission (`test_classification_invariants_hold` constrains
  ships-direction only for `development-only`, `upstream-integration`, and
  `compass-verb`).

  Suites: `test_studio_consumer_skill` (9) + `test_studio_claude_handoff_boundary` (9)
  + 3 added to `test_studio_package_contract` — **21 passed** re-verified on merged
  `main`. FR-028 is ENFORCED rather than intended:
  `test_natural_language_launch_is_stated_before_any_command` compares POSITIONS in the
  body, so a skill that led with the console command would fail. FR-029 is proven
  structurally — `AGENT_PROVIDERS` is a closed two-value enum read off the BUILT parser,
  so a Claude provider would have to appear there first.

  **The trap worth carrying forward: a capability lives in THREE files, and the export
  validates only one of them.** `docs/capabilities/capabilities.yaml` and
  `distribution/public-command-surface.yaml` are authored;
  `distribution/public-knowledge-allowlist.yaml` is GENERATED and must never be
  hand-edited — but `export_agent_bundles.py` checks only `canonical_roots` against a
  fresh derivation and reads `entries` from the COMMITTED allowlist. A
  `consumer-capability` never appears in `canonical_roots`, so with both authored files
  correct the export printed "PASS: generated bundles match reviewed inputs" while the
  skill was absent from BOTH bundles and eleven contract tests failed. The allowlist had
  to be regenerated from `derive_allowlist` directly. That blind spot is described, not
  fixed: widening a shared export gate deserves its own review.

## Phase 8 - Accessibility, Packaging, and Acceptance

- [ ] **T032** Run keyboard, focus, contrast, reduced-motion, non-color status,
  responsive layout, and axe browser acceptance over all critical states; fix every
  critical or serious finding. [FR-031, SC-007]

  **Partial 2026-08-13 — axe now RUNS; the box stays open.** `axe` was absent from
  `studio-ui/package.json` entirely, so SC-007 could not have been satisfied by any
  run of the suite. `studio-ui/src/accessibility.test.tsx` adds `vitest-axe` and
  covers every state SC-007 names — Command Room, empty, blocked, approval — plus the
  approval REFUSAL branch, which renders a different DOM rather than the same tree
  minus a button. Only `critical` and `serious` fail, matching the criterion's own
  wording. **5 passed.**

  Falsified: an `<img>` with no alt in the approval panel fails exactly the two
  approval tests with `critical image-alt`, so the checker is live rather than
  decorative.

  Why the box is open, in two parts:
  - **jsdom does not paint**, so axe reports `color-contrast` as `incomplete`, never
    as a pass. Contrast is unverified by automation here.
  - **Keyboard, focus, reduced-motion, and responsive layout are untested.** T032
    names browser acceptance over the RUNNING app; this is a component-level audit of
    the structural rules jsdom can decide. It is a floor, not the measurement.
- [ ] **T033** Build sdist/wheel and test clean base and Studio-extra installs with no
  Node runtime and no remote asset fetch. [SC-008]

  **Partial 2026-08-13 — the RELEASE path is fixed; the box stays open.** Issue #623
  found the published wheel shipping the `seshat-studio` console script with no UI:
  `release.yml` went from installing validators straight to `python -m build`, with
  no frontend build step, and `src/seshat/studio/static/` is gitignored generated
  output. `pyproject.toml`'s `artifacts` re-include had nothing to collect.

  Fixed by adding the build step AFTER "Verify source identity" (that step asserts a
  clean tree). Proven at the artifact level rather than by reading YAML: a real
  `python -m build --wheel` now yields a wheel containing
  `seshat/studio/static/index.html` plus both hashed assets, confirmed by opening the
  zip. `tests/unit/test_studio_frontend_build.py` — **10 passed**, where the same
  tests SKIPPED before the assets existed, which is precisely why CI stayed green
  over a broken release.

  Still unverified, and why the box is open: SC-008's "clean base and Studio-extra
  installs with no Node runtime" has not been exercised. That needs a fresh
  interpreter installing the built wheel two ways and launching, which is a
  packaging-acceptance run rather than a workflow edit.
- [x] **T034** Run security-boundary negative tests and verify response/log/event
  corpus contains no injected secret, token, absolute path, or workspace content.
  [SC-006]

  **T034 closed 2026-08-13.** `tests/unit/test_studio_boundary_corpus.py` (7) drives
  a real app through every refusal SC-006 names — no session, foreign origin, wrong
  host, traversal, unknown table, unknown thread — plus every successful read and a
  real turn, then scans the ENTIRE response corpus for injected nonces. That is the
  property a sweep has and the existing per-field suites structurally cannot: a new
  endpoint that leaks is caught without anyone remembering to test it.

  Falsified rather than assumed: interpolating `workspace_root` into the 404 problem
  detail fails `test_no_absolute_workspace_path_appears_anywhere_in_the_corpus` and
  nothing else. Absence-assertions that have never fired prove nothing.

  Two over-redaction guards balance the four absences — `display_name` and the
  analyst's prompt are pinned PRESENT, so a redactor that swallowed them would fail
  here instead of reading as extra safety.

  **One scoped decision recorded in the test, not silently encoded in a fixture:** a
  credential the analyst types into their OWN prompt is echoed back on their own
  authenticated loopback thread, and that is not an SC-006 disclosure. FR-026 governs
  credentials Studio handles and paths it resolves, not analyst prose; scrubbing bare
  token-shaped strings would hand-roll a match class beside `redaction_core`'s
  hardened decomposition. Credential-shaped values in ROUTING positions (path segment,
  `selected_table_id`, bootstrap `token`) are tested and must not echo. If that
  reading is wrong it is an owner's call and belongs in an issue.
- [x] **T035** Run existing dashboard and full repository regression gates; reconcile
  generated bundles and run `seshat check` and `semantic-check`. [FR-030, SC-009]

  **T035 measured 2026-08-13/14.** SC-009 asks that the existing gates "remain green
  after Studio is added", which is a COMPARISON, so the baseline was established first
  — a full run on clean `main` before measuring any branch. Without that, seven
  pre-existing environmental failures would have been attributed to this work.

  | Run | Result |
  |---|---|
  | clean `main` | **6612 passed, 7 failed, 38 skipped** (8m47s) |
  | Studio stack (`feat/studio-accessibility-axe`, deepest) | **6631 passed, 6 failed** |

  **The stack is strictly better than the branch point**: +19 passing, one FEWER
  failure. The one that disappears is `test_studio_generated_types`, red on `main`
  since a hand-edit of generated `types.ts` and fixed by #632.

  All 7 baseline failures are ENVIRONMENTAL, each diagnosed rather than assumed:
  - `test_real_wheel_sdist_and_isolated_rebuild` — `twine` not installed here.
  - `test_agent_verify_version_compatibility` and
    `test_issue_regression_489_command_safety` — both spawn `python -I`, which
    isolates away `PYTHONPATH=src`, so the child cannot import `seshat`. The
    documented stale-global-install class.
  - `test_studio_codex_real` (2) — `OSError [WinError 193]`, no valid Codex binary.
  - `weekly_change_points` — the `stats-change` optional extra is not installed;
    the code reports `STAT_DEPENDENCY_UNAVAILABLE` correctly.

  The named gates, all clean on the Studio stack:
  - **dashboard: 92 passed**, 8 skipped — exactly the T003 baseline (FR-030: existing
    static dashboard behaviour unchanged).
  - `export_agent_bundles.py --check` — PASS, both bundles byte-identical.
  - `seshat check` — unchanged from baseline (the one pre-existing RS1 warning, which
    names a human recomputation and is not a Studio finding).
  - `seshat semantic-check` — **0 findings**.
  - `seshat kit-lint` — no projection drift.
- [ ] **T036** Run external signed-in Codex acceptance and record versioned,
  redacted subscription evidence with no API credential. [SC-001, SC-003, SC-010]
- [ ] **T037** Map SC-001 through SC-010 to fresh evidence, review every FR and edge
  case, and request independent code review before claiming Foundation complete.

  **Mapped 2026-08-13/14; the box stays OPEN because two criteria are unmet and one
  is owner-gated.** T037 is the claim that Foundation is complete, so it cannot be
  checked by the agent that built the work — and three rows below are honestly
  incomplete regardless.

  | SC | Status | Evidence |
  |---|---|---|
  | SC-001 first-time analyst, authenticated Codex | **OWNER-GATED** | needs T036 |
  | SC-002 every stage/evidence/blocker projected | met | `test_studio_projection_*`, fixture parity |
  | SC-003 ordered streamed turn | **OWNER-GATED** for the real provider | fake path green; `test_studio_codex_real` cannot run here (no Codex binary) |
  | SC-004 seven agent health states | met | `AgentHealth` suite |
  | SC-005 approval paused until allow/deny, decide-once | met | 50 approval tests + `test_studio_approval_pause` |
  | SC-006 refused requests disclose nothing | met | `test_studio_boundary_corpus` (7), falsified by planting a `workspace_root` leak |
  | SC-007 no critical/serious a11y violations | **PARTIAL** | axe over 5 states; jsdom cannot decide contrast, and keyboard/focus/reduced-motion/responsive need the running app (T032) |
  | SC-008 wheel opens Studio with Python + browser only | **PARTIAL** | wheel now CONTAINS the built UI (#636, verified by opening the zip); clean-base and Studio-extra installs unexercised (T033) |
  | SC-009 existing gates stay green | met | T035 above: stack is +19 passing / one fewer failure than `main` |
  | SC-010 external subscription acceptance | **OWNER-GATED** | needs T036 |

  **FR sweep — the ones this session touched or changed:** FR-005 (#636), FR-018/019/
  020/021 (#632, #633), FR-022 (#635), FR-026 (#637 corpus + the redaction-scope
  ruling), FR-027/028/029 (#634), FR-031 (#637 partial), FR-034 (#638). The rest are
  unchanged from their own phase evidence.

  **Independent review**: each PR in #631-#638 was gated by an adversarial external
  reviewer before opening. Two findings were REFUTED and acted on — T027 was
  wrongly checked and got unchecked; a `provider_request_id` stripping claim was
  narrowed to the stream it actually covers. That is per-PR review, NOT the
  end-of-Foundation review this task asks for, which belongs to a named human who did
  not build the work.

  **What a human must do to close T037**: run T036, decide the two PARTIAL rows
  (accept as-is or require the browser/packaging passes), and review the scoped
  redaction ruling recorded under T034.

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
