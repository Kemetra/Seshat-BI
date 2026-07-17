---
description: "Task list for feature 136 -- governed dependency freshness and co-resolution"
---

# Tasks: Governed Dependency Freshness and Co-Resolution

**Input**: Design documents from `/specs/136-dep-freshness-gate/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Tests ARE requested for this feature (the gate's classification, redaction,
freshness-proposal, and manifest-validation logic must be provable offline). Test
tasks are included and follow TDD (RED before GREEN).

**Organization**: Tasks are grouped by user story so each story can be implemented
and tested independently. US1 (co-resolution proof) is the MVP.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Single project: `scripts/`, `tests/unit/`, `.github/`, repo-root manifest.
- Paths below are repo-relative from the branch worktree root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the committed DATA the gate reads and the test scaffolding.

- [x] T001 [P] Create the committed environments manifest `dependency-environments.yaml`
      at the repo root with the shape in plan.md section 1 (declared environments,
      cross_products, governed_pins). ASCII, UTF-8 no BOM. List the root extras, the
      orchestration project, the root-dbt + orchestration cross-product, and the
      governed pins by DISTRIBUTION name (no version strings -- versions are read
      from pyproject at run time, FR-001/FR-015).
- [x] T002 [P] Add the test module skeleton `tests/unit/test_dep_coresolve.py` with
      the `unit` marker and a fixture that stubs (a) the resolve subprocess and (b)
      the PyPI JSON index, so all Phase-3+ tests are deterministic and offline
      (FR-017). No assertions yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The manifest loader + outcome model every user story depends on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 [US1] Write FAILING unit tests for the manifest loader in
      `tests/unit/test_dep_coresolve.py`: a valid manifest parses into typed
      environment/cross-product/governed-pin records; a manifest pointing at a
      MISSING pyproject or an UNDEFINED extra yields a CONFIG outcome (FR-005).
      Assert RED.
- [x] T004 [US1] Implement the manifest loader + the `ResolveOutcome` classification
      enum (PASS / RESOLUTION / INFRA / CONFIG) in `scripts/dep_coresolve.py` to make
      T003 GREEN. Loader reads pins from the referenced pyproject via `tomllib` (no
      duplicated version strings, FR-015). Classification defaults to RESOLUTION on
      ambiguity (fail-closed); INFRA only on explicit fixture-tested network
      signatures -- add BOTH fixture cases (plan-review D2). Assembled requirement
      strings for repository-local members MUST be LOCAL PATHS, never distribution
      names -- add the pinning unit test (plan-review D1). An ephemeral-venv pip
      too old for `--report` yields CONFIG, not a crash (plan-review D5).
- [x] T005 [US1] Write FAILING unit tests for the resolver-error REDACTION helper:
      a resolver error text carrying a credential-shaped token is masked before it
      is surfaced; a clean conflict message is passed through unchanged (FR-016).
      Reuse the repo's existing C2 secret-shape posture (import from
      `src/seshat/rules/git_meta.py` or a shared helper). Assert RED.
- [x] T006 [US1] Implement the redaction helper in `scripts/dep_coresolve.py`
      (delegating to the existing C2 shapes, not re-implementing them) to make T005
      GREEN.

**Checkpoint**: Manifest is DATA, outcomes are classified, redaction is proven.

---

## Phase 3: User Story 1 - Co-resolution proof (Priority: P1) [MVP]

**Goal**: A fail-closed CI job that proves every declared environment / cross-product
resolves, and fails on the spec-133 / spec-134 conflict shape with the resolver text.

**Independent Test**: Point the gate at a manifest whose cross-product is the
historical dbt-core / dagster-dbt pair -> non-zero exit + resolver text. Point it at
a mutually-compatible manifest -> exit zero.

### Tests for User Story 1 (RED first)

- [x] T007 [P] [US1] Write FAILING unit test: given a stubbed resolve subprocess
      returning a `ResolutionImpossible` error, the resolve function classifies the
      environment as RESOLUTION and captures the (redacted) resolver text (FR-003).
- [x] T008 [P] [US1] Write FAILING unit test: a stubbed successful `--dry-run
      --report` classifies as PASS and records the resolved set; assert the function
      NEVER installs into the current interpreter (the ephemeral-venv path is used,
      SC-002 / FR-002).
- [x] T009 [P] [US1] Write FAILING unit test: a stubbed network/index failure
      classifies as INFRA with a DISTINCT machine-readable status and a DISTINCT
      exit code from RESOLUTION (FR-004, SC-004).
- [x] T010 [P] [US1] Write FAILING unit test: a cross-product unions its members'
      requirement sets and resolves them together as ONE install; the historical
      dbt-core (<1.12 via dagster-dbt) vs ==1.12.0 shape resolves to RESOLUTION.

### Implementation for User Story 1

- [x] T011 [US1] Implement the per-environment ephemeral-venv resolve in
      `scripts/dep_coresolve.py`: create a temp venv, run `pip install --dry-run
      --report`, parse the report, classify PASS/RESOLUTION/INFRA, tear down the
      venv. Make T007-T009 GREEN (FR-002, FR-003, FR-004).
- [x] T012 [US1] Implement cross-product requirement-union resolution to make T010
      GREEN; a cross-product resolves the union of its members' requirement sets.
- [x] T013 [US1] Implement the `--check` entry mode: load the manifest, resolve every
      declared environment + cross-product, print one PASS line per environment,
      print the redacted resolver text for each RESOLUTION/CONFIG, and exit non-zero
      if any RESOLUTION or CONFIG occurred; exit with the distinct INFRA code if only
      INFRA occurred (FR-003, FR-006).
- [x] T014 [US1] Add the `co-resolution` CI job to `.github/workflows/ci.yml` (or a
      new `.github/workflows/dep-integrity.yml`): `ubuntu-latest`, Python 3.13,
      `python scripts/dep_coresolve.py --check`. Do NOT install any optional extra
      into the job interpreter (FR-006, SC-002). Verify the existing `check` job is
      unchanged and still installs only `.[dev]`.

**Checkpoint**: US1 fully functional -- the co-resolution gate catches the incident.

---

## Phase 4: User Story 2 - Advisory freshness proposal (Priority: P2)

**Goal**: A report that proposes latest-stable bumps of governed pins, each with a
solve-proof, changing no pin and opening no PR.

**Independent Test**: Run against a stubbed PyPI index reporting a newer stable for a
governed pin -> report lists current pin, latest stable, and solve-proof result; no
tracked pin changes.

### Tests for User Story 2 (RED first)

- [x] T015 [P] [US2] Write FAILING unit test: latest-stable computation EXCLUDES
      yanked releases and pre-release/dev/rc versions from a stubbed PyPI JSON
      response (FR-007). Include a pin already on a pre-release: reported as such,
      never proposed as stable.
- [x] T016 [P] [US2] Write FAILING unit test: a governed pin behind latest yields a
      PROPOSAL carrying a solve-proof result (PASS/RESOLUTION) for the proposed
      substitution (FR-009).
- [x] T017 [P] [US2] Write FAILING unit test: a proposed bump whose solve FAILS is
      still rendered in the report, marked non-resolving; the report does not crash
      or omit it (FR-010).
- [x] T018 [P] [US2] Write FAILING unit test: an upper-bounded pin (e.g. `<2`) whose
      latest stable sits above the ceiling is reported honestly, notes the ceiling,
      and runs the solve-proof against the ceiling as declared (edge case).
- [x] T019 [P] [US2] Write FAILING unit test: the freshness run mutates NO tracked
      pin value and opens NO PR (assert the reporter is read-only over pyproject
      files; FR-008, FR-012).

### Implementation for User Story 2

- [x] T020 [US2] Implement latest-stable computation over the PyPI JSON API via
      stdlib `urllib` (yanked/pre-release exclusion) to make T015/T018 GREEN
      (FR-007). Yanked semantics are PER-FILE: a release counts as yanked only when
      ALL its files are yanked -- pin with a half-yanked fixture (plan-review D5).
- [x] T021 [US2] Implement proposal generation + solve-proof (reuse the T011 resolve
      with the proposed version substituted) to make T016/T017 GREEN
      (FR-009, FR-010).
- [x] T022 [US2] Implement the `--freshness` entry mode: render JSON + Markdown report
      to an output path; read-only over pyproject files; make T019 GREEN
      (FR-008, FR-011, FR-012).
- [x] T023 [US2] Add the `freshness` CI job (schedule: weekly + `workflow_dispatch`):
      run `--freshness`, upload the report artifact, and gate an OPTIONAL PR comment
      behind an off-by-default repo Actions variable (mirror the existing
      `POST_FRIENDLY_PR_SUMMARY` opt-in pattern; FR-011). The comment is never
      merge-blocking.

**Checkpoint**: US1 + US2 both work independently.

---

## Phase 5: User Story 3 - Dependabot coverage + P2-passing subjects (Priority: P3)

**Goal**: Dependabot watches the orchestration project and emits scope-free subjects
that pass P2 unedited.

**Independent Test**: Inspect `.github/dependabot.yml`: an orchestration pip block
exists and every pip block sets a scope-free commit-message prefix; a produced subject
matches the P2 `SUBJECT_RE`.

### Tests for User Story 3 (RED first)

- [ ] T024 [P] [US3] Write FAILING unit test asserting a Dependabot-produced subject
      of the form `build: bump <dist> from <a> to <b>` matches the P2 `SUBJECT_RE`
      imported from `src/seshat/rules/git_meta.py` (guards FR-014 against P2 drift).
- [ ] T025 [P] [US3] Write FAILING unit test that parses `.github/dependabot.yml` and
      asserts: (a) a pip block for `directory: "/orchestration/dagster"` exists
      (FR-013), and (b) every pip block sets `commit-message.prefix` to a P2-allowed
      type WITHOUT `include: scope` (FR-014).

### Implementation for User Story 3

- [ ] T026 [US3] Edit `.github/dependabot.yml`: add the orchestration pip ecosystem
      block (`directory: "/orchestration/dagster"`, weekly, `dependencies` label) to
      make the T025 coverage assertion GREEN (FR-013). Verify Dependabot accepts the
      orchestration manifest as it exists at implementation time (it may carry a
      repository-local seshat-bi reference after spec 135); if the local reference
      is refused, record the limitation in a manifest comment and keep the directory
      watched for its remaining named pins -- partial coverage recorded honestly
      (plan-review D4).
- [ ] T027 [US3] Edit `.github/dependabot.yml`: add `commit-message: { prefix: "build" }`
      to every pip block (no `include: scope`) to make the T024/T025 subject
      assertions GREEN (FR-014). Confirm against a produced subject that P2 passes.

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish and Cross-Cutting Concerns

- [ ] T028 [P] Add a short doc note (e.g. `docs/tools/dep-integrity.md`) describing
      the manifest shape, the four resolve outcomes, and that governed pins are only
      ever PROPOSED, never auto-bumped. ASCII only.
- [ ] T029 Run `ruff format --check` and `ruff check` over `scripts` and `tests`, and
      run `pytest -m unit` -- confirm GREEN and that CI still installs only `.[dev]`
      (SC-002).
- [ ] T030 Run `retail check --commit-range <base>..HEAD` and confirm exit 0 (P2 on
      the branch's own commits, C2 clean over the new specs/scripts/manifest text).

---

## Dependencies and Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately (T001, T002 in parallel).
- **Foundational (Phase 2)**: depends on Setup. BLOCKS all user stories (the loader,
  outcome model, and redaction are shared).
- **User Stories (Phase 3+)**: all depend on Foundational.
  - US1 is the MVP and should land first.
  - US2 depends on the US1 resolve function (its solve-proof reuses it).
  - US3 is independent of US1/US2 (dependabot + a P2-guard test) and MAY run in
    parallel with them once Foundational is done.
- **Polish (Phase 6)**: depends on the desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: after Foundational. No dependency on US2/US3.
- **US2 (P2)**: after US1 (reuses the resolve function for solve-proofs).
- **US3 (P3)**: after Foundational. Independent of US1/US2.

### Within Each User Story

- Tests are written and FAIL before implementation (RED -> GREEN).
- Loader/model before resolve; resolve before entry modes; entry modes before CI job.
- Story complete before moving to the next priority.

### Parallel Opportunities

- T001 and T002 (Setup) run in parallel.
- T007-T010 (US1 tests) run in parallel; T015-T019 (US2 tests) run in parallel;
  T024-T025 (US3 tests) run in parallel.
- US3 (dependabot + guard test) runs in parallel with US1/US2 after Foundational.

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (US1): the co-resolution gate + CI job.
3. STOP and VALIDATE: the gate fails on the incident shape and passes on a
   compatible manifest, with no optional extra installed into the CI interpreter.

### Incremental Delivery

1. Setup + Foundational -> shared base ready.
2. US1 -> the fail-closed co-resolution proof (MVP).
3. US2 -> the advisory freshness report.
4. US3 -> Dependabot coverage + P2-passing subjects.

---

## Notes

- [P] tasks = different files, no dependencies.
- No checkbox is pre-marked; each is marked only on a verified deliverable.
- Verify tests fail before implementing.
- Governed pins are NEVER auto-bumped -- freshness only PROPOSES (Principle V).
- The co-resolution gate is a CI job, NOT part of offline `seshat check` (Principle
  VIII); no new `seshat` CLI verb is added (ratified Option B).
- Avoid: installing any optional extra into the CI test interpreter (would break the
  lazy-import isolation proof, SC-002).
