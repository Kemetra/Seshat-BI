# Tasks: Seshat BI Public Beta Distribution

**Input**: Design documents from `/specs/125-public-distribution-launch/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Boundary**: This is a future-work list. No task is executed by this specification package. Tasks marked **OWNER-ONLY** require a named human with the stated external authority and MUST NOT be automated, inferred, or self-approved by an agent.

**Tests**: Required because the specification explicitly requires deterministic generation, artifact/install lifecycle proof, and external Claude/Codex acceptance. Within each story, create the failing contract/acceptance test before its implementation task.

**Format**: `[ID] [P?] [Story] Description with exact path`

## Phase 1: Setup — Release Evidence Substrate

**Purpose**: Establish sanitized fixtures and shared evidence conventions without changing public behavior.

- [X] T001 Create the release validation directory map and document generated-versus-canonical ownership in `distribution/README.md`
- [X] T002 [P] Add a fictional ambiguous-grain/PII-shaped retail source plus expected outcome classes in `distribution/synthetic-retail/source.csv` and `distribution/synthetic-retail/expected-outcomes.yaml`
- [X] T003 [P] Add sanitized release-candidate, acceptance-run, and approval-record example fixtures in `tests/fixtures/public_distribution/`
- [X] T004 Add ignore rules for local external-agent profiles, build directories, and unsanitized acceptance evidence in `.gitignore`
- [X] T005 Document the planned evidence filenames, no-score rule, and artifact retention boundary in `docs/operations/release-acceptance-checklist.md`

**Checkpoint**: Tests can use one fictional fixture and one stable evidence vocabulary without real PII, credentials, or client data.

---

## Phase 2: Foundational — Shared Release and Export Contracts

**Purpose**: Implement cross-story validation primitives. This phase blocks all public-surface stories.

### Tests first

- [X] T006 [P] Add failing schema/path/symlink/secret/transitive-reference tests for the allowlist contract in `tests/contract/test_public_knowledge_allowlist.py`
- [X] T007 [P] Add failing deterministic-manifest, unexpected-file, hand-edit, and cross-target provenance tests in `tests/contract/test_generated_agent_bundles.py`
- [X] T008 [P] Add failing governed-location, existing-tag, missing-release-note, and mismatch tests in `tests/contract/test_release_version_sync.py`
- [X] T009 [P] Add failing validation tests for acceptance/approval/rollback record shape and action-scoped authority in `tests/contract/test_release_evidence_models.py`

### Shared implementation

- [X] T010 Define the literal-entry allowlist and reviewed classification schema in `distribution/public-knowledge-allowlist.yaml`
- [X] T011 [P] Create deterministic shared/Claude/Codex template roots and generated-origin policy in `distribution/bundle-templates/shared/`, `distribution/bundle-templates/claude/`, and `distribution/bundle-templates/codex/`
- [X] T012 Implement fail-closed path, media-type, symlink, secret/client marker, transitive-reference, stable-order, and SHA-256 handling in `scripts/export_agent_bundles.py`
- [X] T013 Implement governed version projection discovery and concrete blocker output in `scripts/check_release_versions.py`
- [X] T014 Implement reusable evidence-record validation helpers for candidate, acceptance, approval, and rollback fixtures in `src/seshat/release_evidence.py`
- [X] T015 Make generated-bundle drift and version-sync tests blocking in `.github/workflows/ci.yml`

**Checkpoint**: A missing/unlisted source, unsafe path/content, generated drift, or version mismatch fails closed before any surface-specific work can pass.

---

## Phase 3: User Story 1 — Prove Candidate Consistency (Priority: P1) 🎯 MVP

**Goal**: Audit the completed baseline, resolve release-history contradictions, and produce one evidence-backed blocker verdict without duplicating merged work.

**Independent Test**: Run registry and release audit checks against a clean source revision; `KPI-MC-15` resolves exactly once, all version/history claims agree, and missing evidence yields a concrete blocker rather than a score.

### Tests first

- [X] T016 [P] [US1] Add an explicit failing-then-passing `KPI-MC-15` uniqueness/contract/ID-projection regression to `tests/unit/test_rule_kr1.py`
- [X] T017 [P] [US1] Add failing fixtures for duplicate KPI IDs, missing contracts, conflicting tag/history claims, and unsupported version reuse in `tests/fixtures/public_distribution/release_audit/`
- [X] T018 [US1] Add a failing end-to-end release-blocker audit test in `tests/integration/test_release_candidate_audit.py`

### Implementation

- [X] T019 [US1] Implement the package/registry/bundle/version/docs release-blocker audit and evidence output in `scripts/release_candidate_audit.py`
- [X] T020 [US1] Reconcile the existing annotated `v0.1.0` tag with historical wording in `CHANGELOG.md` and `docs/releases/v0.1.md` without deleting/moving the tag or asserting unverified PyPI history
- [X] T021 [US1] Extend version policy to cover Python, Claude, Codex, generated manifests, changelog, tag, and release while reserving version approval to a named owner in `docs/operations/versioning-policy.md`
- [X] T022 [US1] Record `KPI-MC-15` as present-in-baseline plus the new regression evidence in `docs/operations/release-acceptance-checklist.md`; do not add a registry duplicate
- [X] T023 [US1] Make the candidate audit a blocking, credential-free prerequisite in `.github/workflows/ci.yml`

**Checkpoint**: The repository can truthfully distinguish “baseline issue resolved,” “candidate validated,” and “owner-approved release.”

---

## Phase 4: User Story 2 — Python Install, Upgrade, and Removal (Priority: P1)

**Goal**: Produce complete wheel/sdist metadata and prove the entire clean pipx lifecycle, especially on Windows.

**Independent Test**: Build one wheel and one sdist from clean source, pass strict metadata/content and isolated-sdist rebuild checks, then install/upgrade/uninstall with both commands and project preservation verified.

### Tests first

- [X] T024 [P] [US2] Add failing wheel/sdist metadata, required/prohibited path, dependency, local-path, and secret/content cases in `tests/contract/test_release_artifact_contents.py`
- [X] T025 [P] [US2] Add failing isolated-sdist-rebuild and normalized-wheel parity cases in `tests/integration/test_python_release_artifacts.py`
- [X] T026 [US2] Extend lifecycle tests to fail on missing upgrade, uninstall, command-removal, project-preservation, or optional-dependency checks in `tests/integration/test_python_release_lifecycle.py`
- [X] T027 [P] [US2] Add workflow contract tests for unprivileged build/validation jobs and exact artifact handoff in `tests/contract/test_release_workflow.py`

### Implementation

- [X] T028 [US2] Complete public readme, license-file, project URL, classifier, maintainer, and dependency metadata without ratifying a new version in `pyproject.toml`
- [X] T029 [US2] Implement strict wheel/sdist inventory, metadata comparison, prohibited-content scanning, and isolated-sdist rebuild in `scripts/inspect_release_artifacts.py`
- [X] T030 [US2] Extend clean pipx install/first-success/upgrade/uninstall/command-removal/project-preservation behavior in `scripts/install_smoke_test.py`
- [X] T031 [US2] Keep Windows lifecycle smoke blocking and explicitly classify Linux/macOS evidence status in `.github/workflows/ci.yml`
- [X] T032 [US2] Add a credential-free build/strict-Twine/content/rebuild job and immutable artifact upload in `.github/workflows/release.yml`
- [X] T033 [US2] Rewrite the primary public Python journey and contributor-only alternative in `docs/install/user-install.md`, `docs/install/developer-install.md`, and `README.md`
- [X] T034 [US2] Document supported Python/OS failure behavior, upgrade preservation, uninstall, and command cleanup in `docs/install/user-install.md`

**Checkpoint**: Python release artifacts are independently complete and the full lifecycle passes on blocking Windows without any publication credential.

---

## Phase 5: User Story 5 — Deterministic Canonical Knowledge Export (Priority: P1)

**Goal**: Generate both public agent bundles byte-stably from one explicit allowlist while keeping the five existing Knowledge Bases canonical.

**Independent Test**: Export twice from clean source; path sets and digests are identical, all transitive references resolve, every output has provenance, and unsafe/unlisted/manual edits fail.

### Tests first

- [X] T035 [P] [US5] Add one missing/unlisted transitive-reference fixture for each canonical Knowledge Base under `tests/fixtures/public_distribution/allowlist/`
- [X] T036 [P] [US5] Add secret, PII/client marker, absolute path, traversal, symlink, executable, collision, and nondeterministic-order fixtures under `tests/fixtures/public_distribution/export/`
- [X] T037 [US5] Extend the bundle contract test to assert all five canonical entrypoints and their reviewed transitive closure in `tests/contract/test_generated_agent_bundles.py`

### Implementation

- [X] T038 [US5] Public-review and enumerate every required canonical Knowledge Base/transitive source literally in `distribution/public-knowledge-allowlist.yaml`
- [X] T039 [US5] Add the portable Seshat operating-contract/router templates, generated-origin notices, and platform mappings in `distribution/bundle-templates/shared/`
- [X] T040 [US5] Complete target-specific rendering and stable bundle-manifest generation in `scripts/export_agent_bundles.py`
- [X] T041 [US5] Generate the Claude and Codex knowledge projections and `bundle-manifest.json` files in `integrations/claude-code/seshat-bi/` and `integrations/codex/seshat-bi/`
- [X] T042 [US5] Add a check mode that regenerates into temporary roots and rejects committed hand edits in `scripts/export_agent_bundles.py`
- [X] T043 [US5] Document canonical edit/regenerate/review workflow and prohibit editing generated projections in `distribution/README.md` and `CONTRIBUTING.md`

**Checkpoint**: One canonical edit plus one allowlist review deterministically updates both platform-native bundles; generated copies cannot drift silently.

---

## Phase 6: User Story 3 — External Claude Code Distribution (Priority: P1)

**Goal**: Make the repository-root Claude marketplace and `seshat-bi` plugin installable and governed in a fresh workspace with no `AGENTS.md`.

**Independent Test**: Use an isolated Claude Code profile and external workspace to add/install/update/uninstall the GitHub plugin, inspect the synthetic source, return one truthful governed action, and stop at the human gate.

### Tests first

- [X] T044 [P] [US3] Add failing root-marketplace, plugin-schema, component-path, version, duplicate-marketplace, and external-reference tests in `tests/contract/test_claude_plugin_bundle.py`
- [X] T045 [US3] Add a failing isolated-profile external Claude journey and semantic-outcome classifier in `tests/integration/test_external_claude_acceptance.py`
- [X] T046 [P] [US3] Add stale-cache/update and uninstall-workspace-preservation fixtures in `tests/fixtures/public_distribution/claude/`

### Implementation

- [X] T047 [US3] Finalize the sole public root marketplace entry and synchronized metadata in `.claude-plugin/marketplace.json`
- [X] T048 [US3] Remove the competing integration-local marketplace source at `integrations/claude-code/.claude-plugin/marketplace.json` and update `integrations/claude-code/README.md`
- [X] T049 [US3] Generate/finalize the self-contained Claude manifest, router/knowledge skills, commands, operating guidance, and internal references in `integrations/claude-code/seshat-bi/`
- [X] T050 [US3] Replace development-clone and workspace-`AGENTS.md` assumptions with installed-package detection/defer guidance in `distribution/bundle-templates/claude/`
- [X] T051 [US3] Implement sanitized external-profile execution/evidence capture for the Claude contract in `scripts/external_agent_acceptance.py`
- [X] T052 [US3] Document public GitHub marketplace add/install/refresh/uninstall and fresh-workspace behavior in `docs/install/agent-install.md` and `integrations/claude-code/seshat-bi/README.md`
- [X] T053 [US3] Add the credential-free Claude bundle validator and external-acceptance trigger/matrix to `.github/workflows/ci.yml`

**Checkpoint**: The Claude repository distribution passes from public/candidate Git source with zero development-tree dependency and zero readiness-gate violations.

---

## Phase 7: User Story 4 — External Codex Distribution (Priority: P1)

**Goal**: Add a Codex-native skills-only plugin, repository catalog, `$` invocation, and CLI/IDE acceptance while keeping repository marketplace terminology distinct from OpenAI's public plugin process.

**Independent Test**: Install/discover the plugin in isolated Codex CLI and IDE profiles, invoke `$seshat-bi` and one Knowledge Base skill, and match Claude's governed outcome on the same fixture.

### Tests first

- [X] T054 [P] [US4] Add failing Codex catalog, `.codex-plugin/plugin.json`, skill-frontmatter/layout, version, and no-Claude-field tests in `tests/contract/test_codex_plugin_bundle.py`
- [X] T055 [US4] Add failing isolated Codex CLI/IDE discovery, `$` invocation, semantic-parity, and uninstall tests in `tests/integration/test_external_codex_acceptance.py`
- [X] T056 [P] [US4] Add no-`AGENTS.md`, repository-`AGENTS.md`, and undeclared app/MCP/hook capability fixtures in `tests/fixtures/public_distribution/codex/`

### Implementation

- [X] T057 [US4] Add the current-schema repository Codex catalog pointing at the integration plugin in `.agents/plugins/marketplace.json`
- [X] T058 [US4] Generate/finalize the skills-only manifest, `$seshat-bi` router, five Knowledge Base skills, internal knowledge, and provenance manifest in `integrations/codex/seshat-bi/`
- [X] T059 [US4] Verify and, only where needed, update repository Codex discovery/routing compatibility in `AGENTS.md` and `.agents/skills/`
- [X] T060 [US4] Extend sanitized external-profile execution/evidence capture for Codex CLI and IDE in `scripts/external_agent_acceptance.py`
- [X] T061 [US4] Document repository catalog/plugin installation, `/skills`/`$` invocation, refresh/uninstall, IDE validation, and OpenAI public plugin distinction in `docs/install/agent-install.md` and `integrations/codex/seshat-bi/README.md`
- [X] T062 [US4] Add current Codex schema/skill validation and CLI/IDE acceptance status to `.github/workflows/ci.yml`
- [X] T063 [US4] Add the Claude-versus-Codex outcome-class parity assertion for the shared fixture in `tests/integration/test_external_agent_acceptance.py`

**Checkpoint**: Codex CLI and IDE use a native plugin/skills layout, explicit `$` invocation works, and semantic gates match Claude without workspace guidance.

---

## Phase 8: User Story 6 — Authorization, Verification, and Rollback (Priority: P2)

**Goal**: Finish repository definitions and runbooks that keep configuration, publication, and rollback action-scoped and owner-approved.

**Independent Test**: Review a dry-run evidence pack for an exact candidate. Workflow and docs show five distinct lanes; every irreversible action is blocked without a matching named-owner decision; each surface has public verification and rollback.

### Tests first

- [X] T064 [P] [US6] Extend workflow tests to fail on broad permissions, credentialed build jobs, missing protected environment, mutable/unvalidated artifact input, fork/unprotected ref, or implicit approval in `tests/contract/test_release_workflow.py`
- [X] T065 [P] [US6] Add failing action-scope, candidate/version mismatch, prior-approval reuse, partial-launch wording, and rollback-reapproval cases in `tests/contract/test_publication_authorization.py`
- [X] T066 [US6] Add a failing dry-run release evidence-pack and surface rollback integration test in `tests/integration/test_release_authorization_and_rollback.py`

### Repository implementation

- [X] T067 [US6] Add the protected `pypi` publish job with `id-token: write` only, validated artifact download, exact file/digest checks, and no long-lived token in `.github/workflows/release.yml`
- [X] T068 [US6] Add action-scoped owner-decision placeholders and zero-default-approval checks to `docs/operations/release-acceptance-checklist.md`
- [X] T069 [US6] Rewrite per-surface containment, truthful status, new-version replacement, and reapproval rules in `docs/operations/release-rollback.md`
- [X] T070 [US6] Document actual-availability status fields for Python, repository Claude, repository Codex, Claude catalog, and OpenAI public plugin listing in `README.md` and `docs/install/agent-install.md`
- [X] T071 [US6] Generate a sanitized evidence manifest from the candidate checks without embedding approval in `scripts/release_candidate_audit.py`
- [X] T072 [US6] Validate the no-publication quickstart end to end and record documentation corrections in `specs/125-public-distribution-launch/quickstart.md`

**Checkpoint**: Repository work is mergeable and testable, but every external/irreversible action remains blocked pending its exact owner gate.

---

## Phase 9: PyPI and GitHub Configuration — OWNER-ONLY

**Purpose**: External configuration after repository implementation is merged and all credential-free evidence passes. These actions are not performed by an agent.

- [ ] T073 [US6] **OWNER-ONLY — package identity:** Verify `seshat-bi` name availability/ownership and actual publication history in PyPI; record the result in the private/approved release decision evidence referenced by `docs/operations/release-acceptance-checklist.md`
- [ ] T074 [US6] **OWNER-ONLY — GitHub protection:** Configure tag protections and a `pypi` environment with the named eligible reviewer and no implicit bypass, matching `.github/workflows/release.yml`
- [ ] T075 [US6] **OWNER-ONLY — Trusted Publisher:** Register the exact PyPI identity tuple (`ahmed-shaaban-94/Seshat_BI`, workflow filename, `pypi` environment) and retain sanitized configuration evidence
- [ ] T076 [US6] **OWNER-ONLY — configuration verification:** Review repository settings, workflow permissions, reviewer eligibility, and OIDC binding against `contracts/publication-authorization-boundary.md`; configuration does not approve publication

**Checkpoint**: External identity/protection exists and is evidenced; no version, tag, upload, or release has been authorized by configuration alone.

---

## Phase 10: Claude Publication — OWNER-ONLY

**Purpose**: Separate repository marketplace availability from optional official-catalog submission.

- [ ] T077 [US3] **OWNER-ONLY — repository availability:** Approve the truthful Claude repository marketplace status after a passing public-path External Claude Acceptance record
- [ ] T078 [US3] **OWNER-ONLY — optional public catalog:** Recheck Anthropic's current submission terminology, eligibility, listing, support/privacy/terms, test, and review requirements and assemble—not submit—the evidence referenced by `docs/operations/release-acceptance-checklist.md`
- [ ] T079 [US3] **OWNER-ONLY — submission decision:** Separately approve and, only then, submit the exact Claude candidate; record review status without implying Codex or PyPI authorization

---

## Phase 11: OpenAI Public Plugin Submission — OWNER-ONLY

**Purpose**: Separate repository catalog/plugin availability from OpenAI public submission and review.

- [ ] T080 [US4] **OWNER-ONLY — repository availability:** Approve the truthful Codex repository catalog/plugin status after passing CLI and IDE External Codex Acceptance records
- [ ] T081 [US4] **OWNER-ONLY — eligibility:** Verify Apps Management Write access and developer/business identity matching listing/support/privacy/terms details; retain sanitized eligibility evidence
- [ ] T082 [US4] **OWNER-ONLY — submission package:** Recheck current OpenAI public plugin submission requirements and assemble listing, bundled-skill inventory, starter prompts, tests, country availability, policy attestations, and review evidence
- [ ] T083 [US4] **OWNER-ONLY — submission decision:** Separately approve and, only then, submit the exact Codex plugin; record OpenAI review/listing state without calling it a repository marketplace result

---

## Phase 12: Irreversible Release Actions — OWNER-ONLY

**Purpose**: Execute only after zero blockers, complete external acceptance, external configuration evidence, and an action-scoped named-owner decision for the exact immutable candidate.

- [ ] T084 [US6] **OWNER-ONLY — version decision:** Approve the exact Public Beta SemVer and full source SHA; then authorize a repository implementer to synchronize that value in all locations governed by `contracts/version-synchronization.md`
- [ ] T085 [US6] **AUTHORIZED REPOSITORY IMPLEMENTATION — only after T084:** Project the exact approved value into `pyproject.toml`, both plugin/catalog versions where schema-supported, generated manifests, `CHANGELOG.md`, and `docs/releases/v{version}.md`; run `scripts/check_release_versions.py` and submit the reversible change for normal review
- [ ] T086 [US6] **OWNER-ONLY — final candidate:** Rebuild/revalidate after the approved version projection and bind wheel, sdist, Claude, and Codex digests to the release decision
- [ ] T087 [US6] **OWNER-ONLY — tag:** Grant explicit `create_release_tag` approval and create the immutable `v{version}` tag at the approved SHA
- [ ] T088 [US6] **OWNER-ONLY — PyPI:** Grant explicit `publish_pypi` approval through the protected environment and publish only the previously validated wheel/sdist digests via OIDC
- [ ] T089 [US6] **OWNER-ONLY — GitHub Release:** Grant explicit approval and publish the release for the exact tag/version with truthful per-surface availability
- [ ] T090 [US6] **OWNER-ONLY — public verification:** Repeat clean Python, Claude, and Codex public-path checks only for surfaces actually available and record versions/sources/timestamps
- [ ] T091 [US6] **OWNER-ONLY — containment if needed:** Stop later actions on any failure and authorize only the affected channel's rollback; never overwrite artifacts/move tags, and require a new version/full gate cycle for replacement

---

## Phase 13: Cross-Cutting Completion

- [X] T092 [P] Run full unit, contract, integration, governance, secret, package, and bundle suites and attach sanitized evidence to `docs/operations/release-acceptance-checklist.md`
- [X] T093 [P] Verify every primary install/rollback link and remove development-only commands from public journeys in `README.md` and `docs/install/`
- [X] T094 Confirm every FR/SEC/SC maps to an evidence-producing task and contract in `specs/125-public-distribution-launch/analysis.md`
- [X] T095 Re-run the release requirements checklist in `specs/125-public-distribution-launch/checklists/release-requirements.md`; unresolved items remain blockers

## Dependencies and Execution Order

### Phase dependencies

- **Phase 1** starts first.
- **Phase 2** depends on Phase 1 and blocks all user stories.
- **US1 / Phase 3** establishes the truthful baseline and blocks any version decision.
- **US2 / Phase 4** and **US5 / Phase 5** may proceed after Phase 2 and US1 audit behavior is available.
- **US3 / Phase 6** and **US4 / Phase 7** depend on US5's deterministic export; they may proceed in parallel with each other.
- **US6 / Phase 8** depends on US1, US2, US3, US4, and US5 evidence models/surfaces.
- **Owner Phases 9–11** require merged repository implementation and the applicable passing acceptance evidence; configuration/submission prep can occur independently but authorizes nothing else.
- **Owner Phase 12** requires the exact action's approval and all predecessor evidence. T084 → T085 → T086 → T087; T088/T089 and optional catalog submissions use separate approvals.
- **Phase 13** is the final evidence/traceability check around the desired release state.

### User-story dependencies

```text
Foundation
   ├── US1 baseline audit
   ├── US2 Python artifacts/lifecycle
   └── US5 deterministic export
             ├── US3 Claude distribution
             └── US4 Codex distribution
                         \
                          US6 authorization/rollback
                                   |
                         named-owner-only actions
```

### Parallel opportunities

- T002/T003, T006–T009, T016/T017, T024/T025/T027, T035/T036, T044/T046, T054/T056, and T064/T065 touch distinct fixtures/tests and may run in parallel.
- After US5, Claude and Codex implementation/testing may run in parallel because they have separate generated roots and platform contracts.
- Python artifact hardening may run in parallel with allowlist/export implementation after the common audit/version primitives exist.
- Owner catalog-submission preparation may run in parallel only after each corresponding external acceptance passes; approvals and submissions remain separate actions.

## Requirement Traceability

| Requirement area | Primary tasks |
|---|---|
| FR-001--FR-005 baseline/audit | T016–T023 |
| FR-006--FR-012 Python artifacts | T024–T034 |
| FR-013--FR-018 knowledge export | T006–T012, T035–T043 |
| FR-019--FR-023 Claude | T044–T053, T077–T079 |
| FR-024--FR-029 Codex | T054–T063, T080–T083 |
| FR-030--FR-036 versions/publication | T008, T013, T064–T076, T084–T089 |
| FR-037--FR-041 verification/rollback | T026, T045, T055, T063–T072, T090–T091 |
| FR-042--FR-048 contracts | T006–T015 plus all contract-linked story tests |
| SEC-001--SEC-005 | T002–T004, T006–T012, T024, T035–T043, T064–T076 |
| SC-001--SC-012 | T092–T095 plus the linked story checkpoints |

## Implementation Strategy

1. Deliver audit/evidence primitives first so existing contradictions block truthfully.
2. Harden Python and deterministic export as independently testable P1 increments.
3. Generate and externally validate Claude and Codex as distinct platform bundles.
4. Merge protected workflow definitions and rollback/status documentation without configuring or publishing.
5. Hand the evidence pack to named owners. Execute each external/irreversible task only after its exact approval.

## Notes

- `[P]` means files and immediate dependencies permit parallel work; it does not imply permission to publish.
- Generated bundle content is changed through canonical source/allowlist/templates and regeneration, never hand edits.
- A passing static/governance check is necessary but not sufficient for semantic or public-install acceptance.
- Any missing evidence, unknown platform schema, or changed public submission rule becomes a concrete blocker.
- The likely `0.2.0` proposal is not embedded as an approved task value; T084 owns the human decision.
