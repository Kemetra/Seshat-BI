# Tasks: Agent Ecosystem Growth

**Input**: Design documents from `specs/120-agent-ecosystem-growth/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required. Every story has contract or integration tests because the specification defines independently testable safety boundaries.

**Organization**: Tasks are grouped by user story. Each story is independently releasable; User Story 1 is the MVP.

## Phase 1: Setup

**Purpose**: Establish versioned contracts and optional dependencies without changing runtime behavior.

- [x] T001 Add the stable optional MCP dependency group and development browser-test dependency policy to `pyproject.toml`
- [x] T002 [P] Publish the readiness-passport contract from `specs/120-agent-ecosystem-growth/contracts/readiness-passport.schema.json` to `schemas/readiness-passport.schema.json`
- [x] T003 [P] Publish the extension-pack contract from `specs/120-agent-ecosystem-growth/contracts/extension-pack.schema.json` to `schemas/seshat-extension-pack.schema.json`
- [x] T004 [P] Publish the benchmark-run contract from `specs/120-agent-ecosystem-growth/contracts/benchmark-run.schema.json` to `schemas/benchmark-run.schema.json`
- [x] T005 [P] Publish the static-projection contract from `specs/120-agent-ecosystem-growth/contracts/static-projection.schema.json` to `schemas/static-readiness-projection.schema.json`
- [x] T006 Add all new generated-output roots to `.gitignore` while preserving tracked reference fixtures in `.gitignore`

---

## Phase 2: Foundational Contracts

**Purpose**: Build shared, read-only projection, identity, compatibility, and disclosure primitives required by all stories.

**CRITICAL**: Complete this phase before starting user-story implementation.

- [x] T007 Write shared schema compatibility and canonical relative-path tests for FR-005, FR-007, and unknown-major behavior in `tests/unit/test_ecosystem_contracts.py`
- [x] T008 [P] Write status/evidence/blocker projection invariant tests for FR-001 through FR-006 in `tests/unit/test_readiness_projection.py`
- [x] T009 [P] Write secret, DSN, PII, raw-value, path-escape, and absolute-path disclosure tests for FR-007 and SC-011 in `tests/unit/test_disclosure.py`
- [x] T010 Implement additive `MAJOR.MINOR` compatibility parsing and fail-closed unknown-major behavior in `src/seshat/ecosystem_contracts.py`
- [x] T011 Implement canonical repository-relative path and SHA-256 artifact identity helpers in `src/seshat/artifact_identity.py`
- [x] T012 Implement the ordered shared readiness projection over existing status/evidence/approval readers in `src/seshat/readiness_projection.py`
- [x] T013 Implement the shared disclosure result and scanner with safe finding messages in `src/seshat/disclosure.py`
- [x] T014 Add shared CLI output-root containment and explicit-publication guards in `src/seshat/cli/guards.py`
- [x] T015 Add schema contract tests that validate reference and seeded-invalid documents against `schemas/readiness-passport.schema.json`, `schemas/seshat-extension-pack.schema.json`, `schemas/benchmark-run.schema.json`, and `schemas/static-readiness-projection.schema.json` in `tests/contract/test_ecosystem_schemas.py`

**Checkpoint**: All consumers can use one disclosure-safe projection; no new user-facing command exists yet.

---

## Phase 3: User Story 1 - Reach a Truthful First Success (Priority: P1) MVP

**Goal**: Extend the installed offline demo with a professional static HTML proof that exposes the seven stages and honest live boundary in five minutes.

**Independent Test**: From a clean supported install, run demo init, run, and HTML report; verify every stage, evidence, blockers, next action, forbidden scope, disclosure result, mobile/desktop rendering, and zero source writes.

- [x] T016 [P] [US1] Write HTML report content, offline-boundary, escaping, and no-score tests for FR-009 through FR-011 in `tests/unit/test_demo_html_report.py`
- [x] T017 [P] [US1] Add DOM, keyboard, accessibility, nonblank-canvas, and disclosure assertions for the generated proof in `tests/integration/test_demo_html_browser.py`
- [x] T018 [P] [US1] Add clean-install five-action and five-minute acceptance coverage extending the existing harness in `scripts/install_smoke_test.py`
- [x] T019 [US1] Implement deterministic disclosure-safe HTML rendering from the shared projection in `src/seshat/demo/html_report.py`
- [x] T020 [US1] Extend demo report format/output handling without changing snapshot authority in `src/seshat/demo/report.py`
- [x] T021 [US1] Add `html` and contained `--output` arguments to the demo report parser in `src/seshat/cli/parser.py`
- [x] T022 [US1] Wire HTML report behavior and stable exit codes through `src/seshat/demo/__init__.py`
- [x] T023 [P] [US1] Create responsive accessible static styles with stable stage dimensions and no nested cards in `src/seshat/demo/assets/demo.css`
- [x] T024 [P] [US1] Add dependency-free filtering and evidence disclosure interactions in `src/seshat/demo/assets/demo.js`
- [x] T025 [US1] Update the public first-success proof, expected blocked boundary, and visual asset in `README.md`
- [x] T026 [US1] Reconcile the extended proof with the existing demo documentation in `docs/demo/demo-harness.md`

**Checkpoint**: MVP is independently releasable and requires no DB, MCP client, GitHub token, or Power BI.

---

## Phase 4: User Story 2 - Add Readiness to Change Review (Priority: P2)

**Goal**: Provide reusable review automation with concise summaries, stable JSON, optional SARIF, and no duplicate comment noise.

**Independent Test**: Run the integration against compliant and silver-before-mapping fixtures; verify exit codes, evidence boundary, job summary, JSON, SARIF, fingerprints, and read-only permissions.

- [x] T027 [P] [US2] Write Finding-to-SARIF 2.1.0 parity, location, severity, and fingerprint tests for FR-015 in `tests/unit/test_sarif.py`
- [x] T028 [P] [US2] Write review digest, changed-state, summary, and static-vs-live boundary tests for FR-014 through FR-017 in `tests/unit/test_review_integration.py`
- [x] T029 [P] [US2] Add clean checkout action tests for compliant, hard-stop, input-defect, and unavailable-SARIF cases in `tests/integration/test_github_action.py`
- [x] T030 [US2] Implement deterministic SARIF 2.1.0 formatting over existing `Finding` records in `src/seshat/sarif.py`
- [x] T031 [US2] Implement normalized review result, digest, stage delta, and compact summary composition in `src/seshat/review_integration.py`
- [x] T032 [US2] Add `sarif` output without changing existing text/JSON parity in `src/seshat/cli/parser.py`
- [x] T033 [US2] Wire review output and stable exit-code behavior in `src/seshat/cli/__init__.py`
- [x] T034 [US2] Define the read-only composite integration inputs, outputs, pinned package installation, and artifact steps in `integrations/github-action/action.yml`
- [x] T035 [US2] Implement the cross-platform action entrypoint and job-summary fallback in `integrations/github-action/entrypoint.ps1`
- [x] T036 [US2] Document immutable version pinning, permissions, SARIF availability, and sample usage in `integrations/github-action/README.md`
- [x] T037 [US2] Add a one-way export verification seam for a future Marketplace wrapper without publishing it in `scripts/export_github_action.py`

**Checkpoint**: Teams can adopt review governance without MCP, packs, passports, or explorer work.

---

## Phase 5: User Story 3 - Govern Other Agent Tools (Priority: P3)

**Goal**: Expose six local read-only governance tools through stable MCP v1 stdio while enforcing hard stops in the transport-neutral service.

**Independent Test**: Call every tool against allowed, blocked, malformed, and unavailable fixtures; verify structured output schemas, refusal detail, sanitized errors, and zero writes across all probes.

- [x] T038 [P] [US3] Write transport-neutral operation and hard-stop tests for FR-018 through FR-022 in `tests/unit/test_governor_service.py`
- [x] T039 [P] [US3] Write MCP list/call, structured-output, error, and stdio purity contract tests from `contracts/agent-governor-tools.md` in `tests/contract/test_mcp_governor.py`
- [x] T040 [P] [US3] Add tracked-file, output-root, DB-writer, PBIP, approval, and readiness-state before/after probes for SC-004 in `tests/integration/test_governor_read_only.py`
- [x] T041 [US3] Implement six transport-neutral governor operations by composing existing status, next, blocker, approval, check, and evidence services in `src/seshat/governor/service.py`
- [x] T042 [US3] Implement local-root containment, request validation, error sanitization, and forbidden-scope responses in `src/seshat/governor/service.py`
- [x] T043 [US3] Implement the optional stable MCP v1 stdio adapter with structured output schemas and read-only annotations in `src/seshat/governor/mcp_server.py`
- [x] T044 [US3] Add the `seshat mcp --repo` parser without importing the optional SDK on other command paths in `src/seshat/cli/parser.py`
- [x] T045 [US3] Add the lazy MCP command handler and missing-extra guidance in `src/seshat/cli/__init__.py`
- [x] T046 [US3] Document host registration, tool boundaries, threat model, and companion relationship to execution MCPs in `docs/ecosystem/agent-governor.md`

**Checkpoint**: The governor is independently usable and cannot execute or approve work.

---

## Phase 6: User Story 4 - Carry Verifiable Readiness Evidence (Priority: P4)

**Goal**: Export and verify portable passports without turning them into approval or readiness authorities.

**Independent Test**: Export from a reference table and verify unchanged, changed, missing, incompatible, and unavailable evidence with no source mutation.

- [x] T047 [P] [US4] Write passport export determinism, disclaimer, scope, and relative-path tests for FR-023, FR-024, and FR-027 in `tests/unit/test_passport_export.py`
- [x] T048 [P] [US4] Write verified, changed, missing, incompatible, and unavailable verification tests for FR-025, FR-026, and SC-005 in `tests/unit/test_passport_verify.py`
- [x] T049 [P] [US4] Add schema and zero-source-write acceptance tests for passport commands in `tests/integration/test_passport_cli.py`
- [x] T050 [US4] Implement passport assembly over the shared projection and artifact identities in `src/seshat/passport.py`
- [x] T051 [US4] Implement non-mutating categorical passport verification and source-revision comparison in `src/seshat/passport.py`
- [x] T052 [US4] Add `passport export` and `passport verify` parsers with contained output handling in `src/seshat/cli/parser.py`
- [x] T053 [US4] Wire passport handlers, stable exit codes, JSON output, and explicit local publication guard in `src/seshat/cli/__init__.py`
- [x] T054 [US4] Document portability, compatibility, approval disclaimer, and verification meanings in `docs/ecosystem/readiness-passport.md`

**Checkpoint**: Passports are portable evidence snapshots, never gate-granting documents.

---

## Phase 7: User Story 5 - Extend Seshat Through Governed Packs (Priority: P5)

**Goal**: Scaffold, validate, and explicitly select declarative local packs with conflicts detected before projection.

**Independent Test**: Validate three category-distinct reference packs and seeded invalid packs for executable content, secrets, stage changes, schema claims, ID conflicts, cycles, and incompatibility.

- [x] T055 [P] [US5] Write manifest parsing, namespace, category, authority, and executable-content rejection tests for FR-028 through FR-031 in `tests/unit/test_pack_validator.py`
- [x] T056 [P] [US5] Write dependency graph, conflict, cycle, duplicate ID, and core-compatibility tests for FR-032 in `tests/unit/test_pack_selection.py`
- [x] T057 [P] [US5] Add scaffold-to-validate and no-pack-core behavior tests for SC-006 in `tests/integration/test_pack_cli.py`
- [x] T058 [US5] Implement immutable pack and selection models in `src/seshat/packs/model.py`
- [x] T059 [US5] Implement explicit local manifest loading with root containment and no executable discovery in `src/seshat/packs/loader.py`
- [x] T060 [US5] Implement schema, authority, secret, artifact, compatibility, dependency, and conflict validation in `src/seshat/packs/validator.py`
- [x] T061 [US5] Implement category-aware declarative pack scaffolding with fixtures, verification, decisions, and non-goals in `src/seshat/packs/scaffold.py`
- [x] T062 [US5] Add `pack scaffold` and `pack validate` parsers with explicit local paths in `src/seshat/cli/parser.py`
- [x] T063 [US5] Wire pack handlers and fail-closed exit codes without global activation state in `src/seshat/cli/__init__.py`
- [x] T064 [P] [US5] Author the generic KPI reference pack and synthetic fixtures in `packs/reference/kpi-basic/seshat-pack.yaml`
- [x] T065 [P] [US5] Author the generic source-vocabulary reference pack and synthetic fixtures in `packs/reference/source-vocabulary-basic/seshat-pack.yaml`
- [x] T066 [P] [US5] Author the generic accessibility reference pack and verification evidence in `packs/reference/accessibility-basic/seshat-pack.yaml`
- [x] T067 [US5] Document pack categories, trust boundary, compatibility, conflicts, and deferred registry in `docs/ecosystem/extension-packs.md`

**Checkpoint**: External content can extend supported knowledge without executing code or changing core authority.

---

## Phase 8: User Story 6 - Make a First Contribution Safely (Priority: P6)

**Goal**: Provide structured reports, evidence-aware PRs, and bounded starter contribution lanes.

**Independent Test**: A newcomer selects a lane, locates scoped files, runs verification, and prepares a PR using no more than three linked documents.

- [x] T068 [P] [US6] Add repository tests for issue-form schema, required triage fields, PR evidence prompts, and lane contracts for FR-034 through FR-037 in `tests/unit/test_contributor_surfaces.py`
- [x] T069 [P] [US6] Create the structured defect report form in `.github/ISSUE_TEMPLATE/bug.yml`
- [x] T070 [P] [US6] Create the capability proposal form in `.github/ISSUE_TEMPLATE/feature.yml`
- [x] T071 [P] [US6] Create the extension-pack proposal form in `.github/ISSUE_TEMPLATE/pack.yml`
- [x] T072 [P] [US6] Create the compatibility report form in `.github/ISSUE_TEMPLATE/compatibility.yml`
- [x] T073 [P] [US6] Create the starter-contribution claim form and issue chooser in `.github/ISSUE_TEMPLATE/starter.yml`
- [x] T074 [US6] Create the readiness evidence and safety pull-request prompt in `.github/pull_request_template.md`
- [x] T075 [US6] Author contribution lanes for KPI contracts, synthetic fixtures, dialect renderings, accessibility checks, and blocker explanations in `docs/contributing/contribution-lanes.yaml`
- [x] T076 [US6] Write the three-link newcomer path and maintainer response expectations in `docs/contributing/first-contribution.md`
- [x] T077 [US6] Reconcile the concise newcomer path with the full contributor contract in `CONTRIBUTING.md`

**Checkpoint**: Contribution discovery no longer requires reading the roadmap or spec archive.

---

## Phase 9: User Story 7 - Compare Agent Safety Behavior (Priority: P7)

**Goal**: Publish a vendor-neutral categorical safety benchmark with a deterministic reference participant and transparent stochastic-run metadata.

**Independent Test**: Run all scenarios against the scripted reference participant and verify expected categories, mismatch/over-refusal visibility, disclosure completeness, and absence of aggregate scores.

- [x] T078 [P] [US7] Write scenario validation, synthetic-data, vendor-neutrality, and expected-behavior tests for FR-038, FR-039, and FR-042 in `tests/unit/test_benchmark_scenarios.py`
- [x] T079 [P] [US7] Write run disclosure, repetition, variation, categorical comparison, over-refusal, and no-score tests for FR-040, FR-041, SC-008, and SC-009 in `tests/unit/test_benchmark_runner.py`
- [x] T080 [P] [US7] Add reference-participant end-to-end and schema tests in `tests/integration/test_benchmark_cli.py`
- [x] T081 [US7] Implement immutable scenario, observation, participant, and run models in `src/seshat/benchmark/model.py`
- [x] T082 [US7] Implement the deterministic scripted reference participant over declared scenario evidence in `src/seshat/benchmark/reference.py`
- [x] T083 [US7] Implement scenario loading, repetition capture, disclosure validation, and categorical comparison in `src/seshat/benchmark/runner.py`
- [x] T084 [US7] Implement human and JSON scenario-matrix renderers with no aggregate score in `src/seshat/benchmark/render.py`
- [x] T085 [US7] Add `benchmark run` and `benchmark report` parsers with contained output in `src/seshat/cli/parser.py`
- [x] T086 [US7] Wire benchmark handlers, incomplete-run behavior, and stable exit codes in `src/seshat/cli/__init__.py`
- [x] T087 [P] [US7] Author synthetic hard-stop scenarios for stage order and human approvals in `benchmark/scenarios/hard-stops.yaml`
- [x] T088 [P] [US7] Author synthetic retail semantic scenarios for grain, PII, fan-out, returns, currency, and metric approval in `benchmark/scenarios/retail-semantics.yaml`
- [x] T089 [US7] Document benchmark participation, result disclosure, scenario contribution, and non-leaderboard policy in `docs/ecosystem/agent-safety-benchmark.md`

**Checkpoint**: The benchmark demonstrates Seshat's boundary model without claiming deterministic LLM proof.

---

## Phase 10: User Story 8 - Explore Readiness Without Runtime Access (Priority: P8)

**Goal**: Generate a professional offline portfolio explorer solely from disclosure-safe committed projections.

**Independent Test**: Generate from worked examples and malformed fixtures; verify table/stage navigation, evidence, blockers, approvals, next actions, lineage, mobile/desktop layout, offline operation, disclosure, and zero source writes.

- [x] T090 [P] [US8] Write portfolio aggregation, missing/malformed/stale/pending evidence, and no-inferred-pass tests for FR-043 through FR-047 and SC-010 in `tests/unit/test_explorer_build.py`
- [x] T091 [P] [US8] Add desktop/mobile DOM, keyboard, accessibility, nonblank rendering, stable-layout, and offline browser tests in `tests/integration/test_explorer_browser.py`
- [x] T092 [P] [US8] Add public-output disclosure and zero-source-write integration tests for SC-011 in `tests/integration/test_explorer_disclosure.py`
- [x] T093 [US8] Implement portfolio and available-lineage aggregation from the shared readiness projection in `src/seshat/explorer/build.py`
- [x] T094 [US8] Implement deterministic self-contained HTML generation that reads only the static projection contract in `src/seshat/explorer/build.py`
- [x] T095 [P] [US8] Create accessible responsive styles with stable stage/table/lineage dimensions and no nested cards in `src/seshat/explorer/assets/explorer.css`
- [x] T096 [P] [US8] Create dependency-free table, stage, blocker, approval, and lineage navigation in `src/seshat/explorer/assets/explorer.js`
- [x] T097 [US8] Add `explorer build` parsing, local-default output, disclosure gating, and explicit publication intent in `src/seshat/cli/parser.py`
- [x] T098 [US8] Wire explorer generation and fail-closed output behavior in `src/seshat/cli/__init__.py`
- [x] T099 [US8] Document local generation, offline hosting, disclosure review, and explicit publication in `docs/ecosystem/readiness-explorer.md`

**Checkpoint**: Non-CLI stakeholders can inspect committed readiness without access to runtime systems.

---

## Phase 11: Polish and Cross-Cutting Verification

**Purpose**: Close shared adoption, documentation, performance, privacy, and release evidence across all independently shipped phases.

- [x] T100 [P] Add 100-table/2,000-evidence performance fixtures and enforce SC-003 response targets in `tests/integration/test_ecosystem_scale.py`
- [x] T101 [P] Add a complete no-network/no-DB regression across MVP, passport, packs, reference benchmark, and explorer in `tests/integration/test_ecosystem_offline.py`
- [x] T102 [P] Add Windows path-length and UTF-8-no-BOM coverage for all new generated and committed artifacts in `tests/unit/test_ecosystem_windows.py`
- [x] T103 Add repository metadata, proof, integration, pack, benchmark, explorer, and contribution launch guidance for FR-012 and SC-012 in `docs/operations/public-repository-launch.md`
- [x] T104 Reconcile built/planned/forbidden capability claims after each shipped phase in `README.md`
- [x] T105 Update the release ledger and truthful per-phase availability in `CHANGELOG.md`
- [x] T106 Run and record the full quickstart acceptance sequence in `specs/120-agent-ecosystem-growth/quickstart.md`
- [x] T107 Run formatting, lint, unit, contract, integration, `retail check`, `retail semantic-check`, and `retail kit-lint` gates and record evidence in `specs/120-agent-ecosystem-growth/checklists/requirements.md`

---

## Dependencies and Execution Order

The task-level DAG, safe concurrency waves, serialized hotspots, and ownership matrix are
defined in [implementation-graph.md](./implementation-graph.md). This section retains the
story-level summary; the graph is authoritative when assigning concurrent implementation
work.

### Phase Dependencies

- Setup (Phase 1) has no dependencies.
- Foundational Contracts (Phase 2) depends on Setup and blocks every user story.
- US1 is the MVP and ships first after Phase 2.
- US2 through US8 are independently implementable after Phase 2, but release order follows priority to keep public claims truthful.
- US8 reuses outputs from US4 and may display pack metadata from US5, but remains functional without either optional enrichment.
- Polish follows the story phases included in the target release; SC-012 is measured post-publication rather than fabricated during implementation.

### User Story Dependency Graph

```text
Setup -> Foundation -> US1 (MVP)
                    -> US2
                    -> US3
                    -> US4 -> US8 (optional passport enrichment)
                    -> US5 -> US8 (optional pack enrichment)
                    -> US6
                    -> US7
                    -> US8
```

### Parallel Opportunities

- T002-T005 publish independent schemas.
- T008-T009 test independent foundational boundaries.
- Within each story, `[P]` tests and independent assets/fixtures can proceed concurrently before integration.
- US2, US3, US4, US5, US6, and US7 have disjoint primary write scopes after Foundation.
- US8 begins after its projection contract is stable; optional enrichment waits for US4/US5 only when included.

## Parallel Examples

### User Story 1

```text
T016 demo renderer unit contract
T017 browser/accessibility contract
T018 clean-install acceptance extension
T023/T024 static assets
```

### User Story 3

```text
T038 governor service behavior
T039 MCP protocol contract
T040 read-only mutation probes
```

### User Story 5

```text
T055 validator tests
T056 selection/conflict tests
T064-T066 three reference packs
```

### User Story 8

```text
T090 projection/build tests
T091 browser tests
T092 disclosure/write tests
T095/T096 static assets
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundation.
2. Deliver US1 only.
3. Verify the five-minute offline proof and disclosure boundary.
4. Publish no claims for US2-US8 until their checkpoints pass.

### Incremental Delivery

Each subsequent story ships behind its own documented availability claim and contract
suite. No story waits for the complete ecosystem, and no generated artifact is treated as
authoritative readiness state.

### Task Format Validation

All 107 tasks use the required checkbox, sequential ID, optional `[P]`, required user-story
label inside story phases, actionable description, and explicit file path.
