---
description: "Task list for Semantic Model Readiness -- the model-checking layer"
---

# Tasks: Semantic Model Readiness -- the model-checking layer

**Input**: Design documents from `specs/011-semantic-model-readiness/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: This feature adds NO new Python and NO new checker rule, so there are no
unit-test tasks for new code. Verification is (a) the existing suite + `retail check`
stay green with the new skill present, and (b) the documented acceptance scenarios
hold against the committed RetailGold model with the F009 store absent. Those are
captured as verification tasks, not pytest tasks.

**Organization**: Tasks are grouped by the user stories in spec.md so each story is
independently checkable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 / US2 / US3 (the three spec user stories), or SETUP / POLISH
- All paths are repo-relative from the repo root

## Path Conventions

- The new skill: `.claude/skills/retail-semantic-check/SKILL.md`
- The orchestration edit: `.claude/skills/retail-orchestrate/SKILL.md`
- The authority doc (read-only): `docs/readiness/semantic-model-ready.md`
- The gate it calls: `retail check` (`src/retail/rules/{dax,pbir,g6}.py` -- unchanged)
- The model fixture (read-only): `powerbi/Retailgold.SemanticModel/definition/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the inputs the skill reads exist and ground the procedure.

- [ ] T001 [SETUP] Re-read the stage authority `docs/readiness/semantic-model-ready.md`
  and confirm the skill will IMPLEMENT (not redefine) its required artifacts, checks,
  statuses, blocking reasons, and approver. Note any drift to reconcile in analysis.
- [ ] T002 [P] [SETUP] Inventory the mechanical-gate rules the skill calls and confirm
  each is already shipped: D1-D8 (`src/retail/rules/dax.py`), C1/R1
  (`src/retail/rules/pbir.py`), G6 (`src/retail/rules/g6.py`). No rule is added.
- [ ] T003 [P] [SETUP] Inventory the read-only model fixture
  (`powerbi/Retailgold.SemanticModel/definition/`): relationships, `gold dim_date`,
  the PascalCase measures in display folders. Confirm the F009 metric-contract store is
  ABSENT (the primary acceptance condition).

**Checkpoint**: Inputs confirmed; the skill can be authored against real artifacts.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Author the skill skeleton + frontmatter that all three stories depend on.

**CRITICAL**: No user-story content can be written until the skill file + frontmatter
+ the fixed evaluation order exist.

- [ ] T004 [SETUP] Create `.claude/skills/retail-semantic-check/SKILL.md` with valid
  frontmatter (`name`, a `description` that says READ-ONLY Stage-5 checking, invoke
  after Gold Ready is `pass`), ASCII + UTF-8 no BOM. (FR-001, SC-001)
- [ ] T005 [SETUP] Write the "Scope boundary (read first)" section: read-only;
  CHECKS the model, never DEFINES contracts (F009), never AUTHORS TMDL or calls
  pbi-cli (F016 deferred, hard rule #6). (FR-008; Principle II)
- [ ] T006 [SETUP] Encode the fixed 5-step evaluation order from plan.md Phasing
  (ordering gate -> mechanical gate -> structural facts -> contract-binding ->
  verdict) as the skill's procedure spine. (FR-002..FR-007)

**Checkpoint**: Skill skeleton ready; story content can be filled in.

---

## Phase 3: User Story 1 - Compute the Semantic Model Ready verdict (Priority: P1)

**Goal**: The skill emits ONE Stage-5 status with evidence + blockers, then STOPS.

**Independent Test**: against the committed RetailGold model with NO F009 store, the
skill emits `blocked` (missing metric-contract store), cites the green `retail check`
as mechanical-pass-only, and does NOT emit `pass`.

- [ ] T007 [US1] Write the ORDERING-GATE step: read the readiness status; if Gold
  Ready != `pass`, emit `not_started` + STOP (hard gate, Principle VIII). (FR-002,
  Acceptance 1)
- [ ] T008 [US1] Write the MECHANICAL-GATE step: run `retail check`; map any
  D1-D8 / C1 / R1 / G6 finding to a `blocking_reason`; record exit 0 as
  MECHANICAL-pass-only. (FR-003, Acceptance 2)
- [ ] T009 [US1] Write the VERDICT step: emit exactly one
  `not_started`|`blocked`|`warning`|`pass`, shaped to
  `templates/readiness-status.yaml`, with `evidence[]` + `blocking_reasons[]`; a
  `pass` MUST carry evidence; never a fabricated number. (FR-007, hard rule #9)
- [ ] T010 [US1] Write the NECESSARY-not-sufficient rule explicitly: a green
  `retail check` alone is NOT a `pass`. (FR-006, Acceptance 3, SC-004)

**Checkpoint**: US1 verdict logic complete and independently checkable.

---

## Phase 4: User Story 2 - The contract-binding criterion (Priority: P1)

**Goal**: Every measure binds to an approved F009 contract with recorded owner
approval; gaps are named blockers; the skill never invents/edits/approves a contract.

**Independent Test**: with a fixture store covering only SOME measures, each unmatched
measure is a distinct `blocking_reason`; with all matched but owner approval missing,
`blocked` ("owner approval not recorded"), never `pass`.

- [ ] T011 [US2] Write the CONTRACT-BINDING step: read the F009 store; for each model
  measure confirm a matching APPROVED contract + recorded owner approval. (FR-005)
- [ ] T012 [US2] Write the gap rules: unmatched measure -> named `blocking_reason`;
  matched-but-unapproved -> `blocked` ("owner approval missing", Principle V);
  store ABSENT -> `blocked` ("nothing to bind to"). (FR-005, Acceptance 1-2)
- [ ] T013 [US2] Write the F009/F010 boundary note: this skill CONSUMES contracts; it
  never creates, edits, or approves one (F009 owns contract identity). (spec
  check/define boundary)
- [ ] T014 [US2] Write the ambiguous-mapping HARD-STOP: a measure name that does not
  map cleanly to a contract key STOPS for a human, never a guessed match. (FR-009,
  Acceptance 3)

**Checkpoint**: US2 binding criterion complete; combines with US1 verdict.

---

## Phase 5: User Story 3 - Read-only, author-nothing honesty (Priority: P1)

**Goal**: The skill reads only; it never writes TMDL, never edits the model, never
calls pbi-cli / PBIP automation, never writes an unbacked `pass`.

**Independent Test**: given a fixable finding, the skill REPORTS it + the human
remediation step (edit in Power BI Desktop, re-save PBIP) and edits nothing.

- [ ] T015 [US3] Write the read-only contract: writes no TMDL, edits no measure /
  relationship / date marker, opens no DB connection, invokes no pbi-cli, modifies no
  file under `powerbi/`. (FR-008, Acceptance 2)
- [ ] T016 [US3] Write the human-remediation pattern: each fixable finding is reported
  with the Power BI Desktop edit + re-save-PBIP step; the skill never self-edits.
  (FR-008, Acceptance 1)
- [ ] T017 [US3] Write the fail-loud judgment-stop table (F009 store absent; name not
  mappable; warning-vs-blocked ambiguity; owner identity unclear) -- each a HARD-STOP,
  not a silent default; grain / PII / business-rollup / product-identity NOT decided
  here. (FR-009; Principle V)

**Checkpoint**: All three P1 stories complete and mutually consistent.

---

## Phase 6: Wiring & Cross-links

**Purpose**: Connect the skill into the conductor and the stage authority.

- [ ] T018 Append a `## Orchestration` section to the skill and EDIT
  `.claude/skills/retail-orchestrate/SKILL.md` to reference `retail-semantic-check`
  at the Phase-7 model `[SEAM]` row. (FR-010)
- [ ] T019 Add a `## See also` block to the skill cross-linking
  `docs/readiness/semantic-model-ready.md` (the authority),
  `docs/readiness/readiness-pipeline.md`, the `retail-govern` / `retail-validate`
  siblings, and the roadmap hard rules (#4, #5, #6, #9). (FR-011)

---

## Phase 7: Polish & Verification

**Purpose**: Prove the success criteria.

- [ ] T020 [P] [POLISH] Verify `retail check` stays exit 0 and the full unit suite
  stays green with the new skill present; confirm no new Python and `dependencies = []`
  unchanged. (SC-002)
- [ ] T021 [P] [POLISH] Verify the skill file is ASCII + UTF-8 no BOM, has valid
  frontmatter, is registered by the harness, and carries the `## Orchestration`
  pointer. (SC-001)
- [ ] T022 [POLISH] Walk the central acceptance scenario manually: against the
  committed RetailGold model with NO F009 store, confirm the skill's procedure yields
  `blocked` (missing store), cites green `retail check` as mechanical-pass-only, and
  does NOT yield `pass`. (SC-003, the central correctness property)
- [ ] T023 [POLISH] Confirm the skill text states NECESSARY-not-sufficient + authors
  nothing + pbi-cli/PBIP deferred to F016. (SC-004)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; T002/T003 are [P].
- **Foundational (Phase 2)**: depends on Phase 1; BLOCKS all stories (the skill file
  must exist with its spine before story content is written).
- **User Stories (Phases 3-5)**: all depend on Phase 2. US1/US2/US3 touch the SAME
  file (`SKILL.md`), so they are written in priority order (P1 all), not in parallel.
- **Wiring (Phase 6)**: depends on the stories being authored.
- **Polish (Phase 7)**: depends on Phases 2-6; T020/T021 are [P].

### Within Each User Story

- The evaluation-order spine (T006) precedes all step content.
- US1 (verdict frame) precedes US2 (binding) precedes US3 (read-only honesty) because
  later stories reference earlier sections of the same file.

### Parallel Opportunities

- Setup: T002 + T003 in parallel.
- Polish: T020 + T021 in parallel.
- Story tasks are NOT parallel (single shared file `SKILL.md`).

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup -> Phase 2 Foundational (skill skeleton + spine).
2. Phase 3 US1: the verdict logic (ordering gate + mechanical gate + verdict +
   necessary-not-sufficient).
3. STOP and VALIDATE: against the RetailGold model with F009 absent, the skill yields
   `blocked`, not `pass`. This MVP already delivers the central correctness property.

### Incremental Delivery

1. Setup + Foundational -> skill skeleton ready.
2. US1 -> the verdict (MVP; the `blocked`-not-`pass` outcome is provable).
3. US2 -> the contract-binding criterion (the governance the stage adds).
4. US3 -> read-only / author-nothing honesty.
5. Wiring + Polish -> conductor reference + success-criteria verification.

---

## Notes

- [P] = different files, no dependencies. The three stories share `SKILL.md`, so they
  are sequential.
- No new Python, no new checker rule, no CLI subcommand (plan Structure Decision).
- The skill is read-only; pbi-cli / PBIP authoring stays deferred to F016 (hard rule
  #6); metric-contract definition stays owned by F009 (the F009/F010 boundary).
- Commit after each phase or logical group; keep paths short (Windows `MAX_PATH`).
- Verify before claiming: green `retail check` + green suite are necessary-not-
  sufficient for the feature's value, which is the correct `blocked` verdict.
