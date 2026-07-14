---
description: "Task list for 129-agent-verify implementation"
---

# Tasks: Agent Compatibility Certification (`seshat agent verify`)

**Input**: Design documents from `/specs/129-agent-verify/`

**Prerequisites**: plan.md (required), spec.md (required for user stories),
research.md, data-model.md, contracts/

**Tests**: Included. The spec's success criteria (SC-001..SC-007) are
test-backed truthfulness/read-only/no-false-pass guarantees; tests are written
first (RED) and must fail before implementation (GREEN).

**Organization**: Tasks are grouped by user story so each ships as an
independent evidence increment. US1 is the MVP.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency).
- **[Story]**: US1 / US2 / US3 / US4, or SETUP / FOUND / POLISH.
- Exact file paths are in each description.

## Path Conventions

Single project: `src/seshat/`, `tests/unit/` at repository root (per plan.md
Structure Decision). No new dependency; stdlib-only core, lazy `yaml`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package skeleton and design contracts.

- [ ] T001 [SETUP] Create the `src/seshat/agent_verify/` package with
  `__init__.py` (empty public surface) and confirm it imports with no
  module-scope DB/network import (B1/B3 posture).
- [ ] T002 [P] [SETUP] Author `specs/129-agent-verify/research.md` resolving the
  five Phase 0 questions (provenance/drift surface, version/compat source,
  governor invocation contract, scenario id stability, IDE-surface signal),
  each with a citation to shipped code.
- [ ] T003 [P] [SETUP] Author `specs/129-agent-verify/data-model.md` with the
  four entities (VerifyTargetSpec, RequiredCheck, PerCheckResult,
  VerifyEvidenceRecord) and the per-verdict invariants.
- [ ] T004 [P] [SETUP] Author `specs/129-agent-verify/contracts/verify-checks.md`
  (the 11-check table: check_id, foundation, evidence_class (per-target vs
  shared baseline), evidence source, PASS condition, BLOCKED triggers,
  UNAVAILABLE condition) and `contracts/agent-verify-record.schema.json` (closed
  draft-2020-12 schema: three-value verdict enum, the evidence_class enum,
  per-verdict reason fields, no score/rank/overall property).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The model, the target registry, and the record assembly that every
check and story depends on.

**CRITICAL**: No user story work begins until this phase is complete.

- [ ] T005 [FOUND] Implement `src/seshat/agent_verify/model.py`:
  `VERDICTS = ("PASS", "BLOCKED", "UNAVAILABLE")`, frozen `PerCheckResult`
  (with `evidence_class` in {`per_target`, `shared_baseline`} and the invariant
  enforced in `__post_init__`: PASS => non-empty evidence + empty reasons;
  BLOCKED => >=1 blocking reason; UNAVAILABLE => `unavailable_reason`), frozen
  `VerifyTargetSpec`, frozen `VerifyRecord` with a `to_document()` that emits NO
  aggregate field.
- [ ] T006 [FOUND] Implement `src/seshat/agent_verify/targets.py`: a data-driven
  registry mapping `claude` and `codex` to their `VerifyTargetSpec`
  (manifest path, provenance manifest, version source, footprint source,
  `operating_contract` path, `ide_surface` flag). An unknown target name raises
  a typed error the CLI maps to exit 2.
- [ ] T007 [FOUND] Implement `src/seshat/agent_verify/record.py`: assemble a
  `VerifyRecord` from a list of `PerCheckResult`, run the disclosure scan
  (secret / real connection string / local absolute path / possible PII),
  serialize to JSON under `.seshat-output/` via
  `guards.resolve_local_output`, and expose a `publish` path gated by
  `guards.require_publication_intent`.

**Checkpoint**: Foundation ready - checks and CLI can now be built per story.

---

## Phase 3: User Story 1 - Verify one integration end to end (P1) [MVP]

**Goal**: `seshat agent verify --target claude|codex` runs every required
install/discovery/version/IDE/uninstall check and emits a categorical verdict
per check with the stable exit-code contract.

**Independent Test**: Run verify against `claude` and `codex` from a clean
checkout; every required check yields PASS/BLOCKED/UNAVAILABLE with evidence or
reason; the exit code distinguishes all-PASS from any-BLOCKED from any-
UNAVAILABLE-none-BLOCKED.

### Tests for User Story 1 (write first, must FAIL)

- [ ] T008 [P] [US1] `tests/unit/test_agent_verify_checks.py`: installation &
  discovery check (FR-009/FR-010) - PASS on a resolvable manifest + marketplace
  entry + matching provenance; BLOCKED on a missing/unreadable manifest.
- [ ] T009 [P] [US1] Same file: version-compatibility check (FR-011) - PASS in
  range; BLOCKED naming the incompatible/absent version + the supported range;
  never PASS out of range.
- [ ] T010 [P] [US1] Same file: update-integrity check (FR-018) - PASS when all
  `output_sha256` match; BLOCKED naming a drifted path + expected/observed hash.
- [ ] T011 [P] [US1] Same file: uninstall-integrity check (FR-019) - reports the
  declared footprint as evidence; UNAVAILABLE when the footprint cannot be
  enumerated.
- [ ] T012 [P] [US1] Same file: IDE-surface check (FR-020) - UNAVAILABLE (with
  reason) for a target with no declared IDE surface; never PASS/fail there.
- [ ] T013 [P] [US1] `tests/unit/test_agent_verify_cli.py`: `--target` refusal
  for an unknown target (exit 2 + supported-target list); the exit-code contract
  (0 all-PASS / 1 any-BLOCKED / 2 input defect / 3 any-UNAVAILABLE none-BLOCKED);
  an UNAVAILABLE-only run does NOT exit 0 (SC-002 no-false-pass at the boundary).

### Implementation for User Story 1

- [ ] T014 [US1] Implement the install/discovery, version, update, uninstall,
  and IDE checks in `src/seshat/agent_verify/checks.py` (each a pure function
  `(target_spec, repo_root) -> PerCheckResult`), reusing the provenance manifest
  + exporter drift surface (no re-hash logic invented) and the version source
  from `targets.py`.
- [ ] T015 [US1] Implement `src/seshat/cli/commands/agent_verify.py`
  (`agent_verify_main`): resolve the target, run the required checks, assemble
  the record, print the per-check verdict lines + a truthful summary, and return
  the exit code per the contract.
- [ ] T016 [US1] Wire the parser: add `_add_agent_parser` in
  `src/seshat/cli/parser_ecosystem.py` (an `agent` group with a `verify`
  subcommand: `--target {claude,codex}` required, `--output` defaulting under
  `.seshat-output/`, `--publish` flag), and add the lazy dispatch entry
  `"agent": _lazy(".commands.agent_verify", "agent_verify_main")` in
  `src/seshat/cli/__init__.py`.

**Checkpoint**: US1 is fully functional - verify runs end to end on both targets
with truthful categorical verdicts and the no-false-pass exit contract.

---

## Phase 4: User Story 2 - Confirm the governance contract per target (P2)

**Goal**: The five governance checks (readiness routing, PII refusal, no
self-approval, no silver-before-mapping, no invented metric meaning) each
resolve to a named committed scenario/governor contract and confirm the
reference baseline matches; a missing/mismatched contract is BLOCKED.

**Independent Test**: The per-target contract-presence check reads each target's
own exported operating contract and BLOCKs a target that drops a hard-stop line
(so `claude` and `codex` can differ); each shared-baseline governance check
cites its scenario id / governor contract, PASSes when the reference baseline
matches, and BLOCKs when the cited scenario is removed, malformed, or its
baseline mismatches.

### Tests for User Story 2 (write first, must FAIL)

- [ ] T016a [P] [US2] `tests/unit/test_agent_verify_checks.py`: per-target
  governance-contract-presence check (FR-012a) reads the target's own
  `portable-operating-contract.md`, PASSes when every hard-stop line is present,
  and BLOCKs naming the affected hard stop for a target whose contract drops or
  mutates one; a fixture with `claude` intact and `codex` dropping a hard stop
  yields PASS for `claude` and BLOCKED for `codex` (proves per-target,
  non-vacuous; SC-005).
- [ ] T017 [P] [US2] Same file: PII-refusal check (FR-013, shared baseline)
  cites `rs-pii-exposure`, confirms expected behavior is a refusal, and the
  scripted reference reproduces it (PASS); a removed scenario -> BLOCKED naming
  the missing id (SC-005).
- [ ] T018 [P] [US2] Same file: no-self-approval (FR-014, `hs-self-grant-
  approval`) and no-silver-before-mapping (FR-015, `hs-silver-before-mapping`)
  checks - PASS on baseline match; BLOCKED on mismatch.
- [ ] T019 [P] [US2] Same file: no-invented-metric-meaning check (FR-016,
  `rs-metric-without-approval`) - PASS when expected behavior does not proceed
  (blocks for evidence / requests human decision); BLOCKED otherwise.
- [ ] T020 [P] [US2] Same file: readiness-routing check (FR-012) - PASS when the
  read-only governor returns stage/evidence/blockers/next-action/forbidden-scope
  over a fixture with no write; UNAVAILABLE when the governor cannot be invoked.
- [ ] T021 [P] [US2] Read-only assertion (SC-004): running the governance checks
  performs zero tracked-file/DB/model writes and grants no approval.

### Implementation for User Story 2

- [ ] T022a [US2] Implement the per-target governance-contract-presence check in
  `checks.py` (FR-012a): read the target's `operating_contract` path from its
  `VerifyTargetSpec`, assert every hard-stop line is present, tag the result
  `evidence_class="per_target"`, and BLOCK naming the affected hard stop on a
  drop/mutation. Missing contract file -> BLOCKED.
- [ ] T022 [US2] Implement the five shared-baseline governance checks in
  `checks.py`: load the cited scenario via `benchmark.runner.load_scenarios`,
  run the scripted reference participant, and compare via
  `Observation.comparison`; the routing check invokes `governor.service`
  read-only. Tag each result `evidence_class="shared_baseline"`.
  Missing/malformed scenario or a baseline mismatch -> BLOCKED with the concrete
  reason (FR-017); governor un-invokable -> UNAVAILABLE.
- [ ] T023 [US2] Add the six governance checks (one per-target + five shared
  baseline) to the required-check set in `agent_verify_main` so they run
  alongside US1's checks and feed the same record + exit-code contract.

**Checkpoint**: US1 + US2 both work; verify now confirms install integrity AND
the governance contract - the target's own bundle carries every hard stop
(per-target), and each hard stop maps to a committed scenario whose reference
baseline matches (shared baseline).

---

## Phase 5: User Story 3 - Update and uninstall integrity as first-class evidence (P3)

**Goal**: Update and uninstall integrity are surfaced as explicit, reviewable
evidence (provenance match + declared footprint), independently demonstrable.

> Note: the check *functions* land in US1 (T014); US3 hardens them into
> demonstrable release evidence with the seeded-drift and footprint fixtures and
> the quickstart walkthrough.

**Independent Test**: A drift-free target -> update-integrity PASS; a mutated
generated file -> BLOCKED naming the path; the uninstall footprint lists the
installed paths.

### Tests for User Story 3 (write first, must FAIL)

- [ ] T024 [P] [US3] `tests/unit/test_agent_verify_record.py`: a seeded drift
  fixture (one edited generated file) makes update-integrity BLOCKED in the
  assembled record and the record names the drifted path.
- [ ] T025 [P] [US3] Same file: the uninstall-integrity result lists the target's
  declared footprint paths as evidence and is UNAVAILABLE when the footprint is
  unresolvable.

### Implementation for User Story 3

- [ ] T026 [US3] Add the seeded-drift and footprint-enumeration fixtures under
  the test tree and confirm the US1 check functions produce the release-grade
  evidence US3 requires (no new check code; fixtures + assertions only).
- [ ] T027 [US3] Author `specs/129-agent-verify/quickstart.md`: run verify on
  both targets, read the record, and reproduce the seeded BLOCKED (drift) and
  UNAVAILABLE (no IDE) verdicts.

**Checkpoint**: US1 + US2 + US3 work; update/uninstall integrity is demonstrable
release evidence.

---

## Phase 6: User Story 4 - Portable, disclosure-safe evidence record (P4)

**Goal**: Verify writes a disclosure-safe evidence record under
`.seshat-output/` by default; publication/catalog submission is refused without
explicit intent and refused on any disclosure finding.

**Independent Test**: The record carries per-check verdicts + evidence + target
+ tool version + generation time and no aggregate; publication is refused
without `--publish`; a seeded secret/absolute-path blocks publication.

### Tests for User Story 4 (write first, must FAIL)

- [ ] T028 [P] [US4] `tests/unit/test_agent_verify_record.py`: the record
  validates against `contracts/agent-verify-record.schema.json` and contains no
  `score`/`rank`/`pass_rate`/`grade`/`overall`/`certified` key (SC-003
  truthfulness).
- [ ] T029 [P] [US4] Same file: `require_publication_intent` refuses publication
  without `--publish`; a seeded secret / real connection string / local absolute
  path makes the disclosure scan fail and publication is refused (SC-006).
- [ ] T030 [P] [US4] Same file: output containment - the record is written only
  under `.seshat-output/`; an uncontained `--output` raises and maps to exit 2.

### Implementation for User Story 4

- [ ] T031 [US4] Finalize `record.py` serialization + disclosure scan + publish
  path against the schema; wire the `--publish` flag in `agent_verify_main` to
  the publication-intent + disclosure gate (default: local-only write).
- [ ] T032 [US4] Add a text truthfulness assertion in
  `tests/unit/test_agent_verify_cli.py`: the human summary output contains no
  score/rank/percentage/"certified" token in any verdict combination (SC-003).

**Checkpoint**: All four stories work; verify produces a portable,
disclosure-safe, score-free evidence record with owner-controlled publication.

---

## Phase 7: Polish and Cross-Cutting

- [ ] T033 [P] [POLISH] Offline guarantee test (SC-007) in
  `tests/unit/test_agent_verify_checks.py`: run every required check with no DB /
  network / IDE and assert completion, with UNAVAILABLE where a surface is
  absent.
- [ ] T034 [P] [POLISH] Add a short `docs/ecosystem/agent-verify.md` describing
  the verb, the three verdicts, the check-to-foundation map, and the
  static-vs-live boundary (mirrors `docs/ecosystem/agent-safety-benchmark.md`
  tone; generic, no client specifics).
- [ ] T035 [POLISH] Run the gate set: `ruff format --check src tests`,
  `ruff check src tests`, `pytest -m unit -q`, `retail check`, and
  `retail semantic-check`; fix any finding. Confirm `retail check` rule count is
  unchanged (this feature adds no static rule).
- [ ] T036 [POLISH] Run `quickstart.md` end to end against the shipped `claude`
  and `codex` targets and confirm the documented verdicts and exit codes.

---

## Dependencies and Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependency; start immediately.
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all user stories.
- **US1 (Phase 3)**: depends on Foundational. MVP.
- **US2 (Phase 4)**: depends on Foundational; adds governance checks to the same
  record + exit contract US1 establishes (T015/T016).
- **US3 (Phase 5)**: depends on US1's check functions (T014); adds fixtures +
  quickstart, no new check code.
- **US4 (Phase 6)**: depends on Foundational's `record.py` (T007); hardens
  serialization/disclosure/publish.
- **Polish (Phase 7)**: depends on all desired stories.

### Within Each User Story

- Tests are written first and must FAIL before implementation (RED -> GREEN).
- Model + registry + record (Phase 2) before any check.
- Check functions before CLI dispatch.
- Commit after each task or logical group.

### Parallel Opportunities

- T002/T003/T004 (Setup docs) run in parallel.
- All [P] test tasks within a story run in parallel (distinct assertions, shared
  file - coordinate the single file's edits if staffed in parallel).
- US2 and US4 can proceed in parallel after Foundational (different check group
  vs record hardening); US3 waits on US1's T014.

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1 Setup -> Phase 2 Foundational -> Phase 3 US1.
2. STOP and VALIDATE: verify runs on both targets with truthful install/version/
   update/uninstall/IDE verdicts and the no-false-pass exit contract.

### Incremental Delivery

1. Setup + Foundational -> foundation ready.
2. US1 -> install integrity evidence (MVP).
3. US2 -> governance contract evidence.
4. US3 -> release-grade update/uninstall evidence.
5. US4 -> portable disclosure-safe record + owner-controlled publication.

---

## Notes

- [P] = different files / independent assertions, no dependency.
- No new dependency; stdlib-only core, lazy `yaml`; no module-scope DB/network
  import (B1/B3).
- This feature adds NO new `retail check` static rule and grants NO approval /
  advances NO readiness stage (Principle V; hard rule #9).
- Every verdict is one of {PASS, BLOCKED, UNAVAILABLE}; no score/rank/rollup in
  any output (FR-003; enforced by SC-003 tests).
- Commit after each task or logical group; keep the branch PR-ready but do not
  merge/push (owner-gated).
