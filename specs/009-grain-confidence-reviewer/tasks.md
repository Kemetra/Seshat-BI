---
description: "Task list for the grain confidence + mapping diff reviewer"
---

# Tasks: grain confidence + mapping diff reviewer

**Input**: Design documents from `specs/009-grain-confidence-reviewer/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: this slice adds NO new code (a pure agent-procedure skill that reuses the
existing `PkProof` signal and reads committed files). There is no new unit to test;
acceptance is the rendered card/diff inspected against the spec's FRs on generic
fixtures, plus the existing suite + `retail check` staying green. No new test tasks
are created (consistent with the kit's skill-only slices 005/006).

**Organization**: tasks are grouped by user story so each is independently
deliverable. US1 (grain confidence) and US2 (mapping diff) are the two MVP halves;
US3 (judgment hard-stops) is the cross-cutting Principle-V guard woven through both.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files / sections, no dependency)
- **[Story]**: US1 / US2 / US3, or SETUP / FINAL for shared phases
- Exact paths are included in each task

## Path Conventions

- New skill: `.claude/skills/grain-confidence-reviewer/SKILL.md`
- Edited seam: `.claude/skills/retail-orchestrate/SKILL.md`
- Reused (unchanged): `src/retail/profile.py`, `templates/source-map.yaml`,
  `templates/source-profile.md`, `templates/readiness-status.yaml`,
  `docs/readiness/mapping-ready.md`

---

## Phase 1: Setup (shared)

**Purpose**: create the skill skeleton the user stories fill.

- [ ] T001 [SETUP] Create `.claude/skills/grain-confidence-reviewer/` and an empty
  `SKILL.md` with valid frontmatter (`name: grain-confidence-reviewer`, a
  `description` that says: surface grain-uniqueness confidence as evidence + diff two
  source-map versions for a Mapping Ready reviewer; reads existing signal, renders,
  STOPS; never approves, never fabricates a score). ASCII, UTF-8 no BOM. (FR-001)
- [ ] T002 [SETUP] Write the scope-boundary header: this skill SURFACES evidence and
  STOPS at the human seam; it does NOT write approvals or `Gate status: CLEARED`,
  does NOT edit `source-map.yaml`, does NOT pick a new PK/grain, and does NOT emit a
  numeric confidence score. Cite Principles IV, V, VII, VIII and hard rule #9. (FR-008, FR-010)

**Checkpoint**: skill file exists, registered by the harness, with its guard-rails stated.

---

## Phase 2: User Story 1 - Grain confidence as readiness evidence (Priority: P1) MVP

**Goal**: render the measured PK-uniqueness signal as a status + evidence + blockers
card, never a number.

**Independent Test**: a generic profile with `is_unique=true`/`null_pk=0` yields a
`pass`-eligible card citing the three counts; `is_unique=false` or `null_pk>0` yields
`blocked` with the concrete reason -- and neither emits a score (SC-003).

- [ ] T003 [US1] Write the "Read the measured signal" step: read
  `mappings/<table>/source-profile.md`'s Candidate-grain/PK numbers; OR, at the live
  boundary, re-run `src/retail/profile.py` via `resolve_dsn` + `make_psycopg2_runner`
  (the `db` extra). MUST reuse `PkProof` (`total`, `distinct_pk`, `null_pk`,
  `is_unique`); MUST NOT re-implement the uniqueness query. (FR-002)
- [ ] T004 [US1] Write the grain-confidence CARD format: show `total`,
  `distinct_pk`, `null_pk`, `is_unique` as cited `evidence[]`, plus `blocking_reasons[]`.
  Render exactly ONE of the four readiness statuses. Explicitly forbid a numeric
  score and an auto high/medium/low label in the card text. (FR-003)
- [ ] T005 [US1] Write the explicit status-mapping table: `is_unique=true` AND
  `null_pk=0` -> supports `pass` (state "human approval in approvals[] still
  required"); `is_unique=false` OR `null_pk>0` -> `blocked` + the concrete reason
  ("COUNT(DISTINCT pk) < COUNT(*)" / "NULLs in PK columns"); no live profile ->
  `blocked` + `[PENDING LIVE PROFILE]`; a human-recorded data-justified deviation ->
  `warning` (never auto-`pass`). (FR-004)
- [ ] T006 [P] [US1] Write the "record into readiness status" note: the card's
  evidence/blockers are recorded into the Mapping Ready stage of
  `templates/readiness-status.yaml` (`evidence[]` / `blocking_reasons[]`) -- no new
  state field; any optional `score` must be marked OPTIONAL and cite evidence (default
  omit). (FR-009)
- [ ] T007 [P] [US1] Write the deferred/live-boundary mode: no DSN / no `db` extra ->
  report `[PENDING LIVE PROFILE]`, print the enable steps (`pip install 'retail[db]'`,
  set `DATABASE_URL`/`ANALYTICS_DB_*` in the gitignored `.env`, never commit a DSN),
  and DO NOT fabricate a result. (FR-002, FR-004 scenario 4; Principle VIII)

**Checkpoint**: US1 renders a correct, score-free grain-confidence card for both the
unique and non-unique cases, and degrades safely at the live boundary.

---

## Phase 3: User Story 2 - Reviewable diff between two source-map versions (Priority: P1) MVP

**Goal**: a semantic diff grouped by the load-bearing fields, with a per-change
re-approval flag.

**Independent Test**: two generic `source-map.yaml` versions with a grain edit + a
`pii:` flip + a `gold_placement` move yield exactly those three changes under their
headings, with grain and PII flagged "REQUIRES RE-APPROVAL" (SC-004).

- [ ] T008 [US2] Write the "read two versions" step: identify each
  `source-map.yaml` version by a git ref and/or path; handle the
  no-prior-version edge case ("initial version -- nothing to diff", still render the
  US1 card). (FR-005; spec Edge Cases)
- [ ] T009 [US2] Write the semantic-diff grouping: group changes under `meta.grain`,
  `meta.primary_key`, every column `pii:` flag, and every `gold_placement`; list
  additions / removals / moves per group; list non-load-bearing edits (comments,
  `reason:` wording) separately for the audit trail. (FR-005)
- [ ] T010 [US2] Write the re-approval flag rule: any change to grain, primary_key,
  or a `pii:` flag is flagged "REQUIRES RE-APPROVAL" (invalidates any prior Mapping
  Ready `approvals[]`); non-load-bearing edits state no re-approval is forced. (FR-006)
- [ ] T011 [P] [US2] Write the PII-regression guard in the diff: a `pii:true`
  column whose `decision` is no longer `drop` after the edit is raised as a
  governance blocking_reason, not passed through silently. (FR-006 scenario 4; Principle V)
- [ ] T012 [P] [US2] Cover the remaining diff edge cases in text: PK column renamed
  (surface under primary_key, flag re-approval); composite-PK reorder only (surface,
  note uniqueness unchanged, human confirms); profile stale vs current PK (report the
  mismatch as a blocker); `gold_star` reshape (surface under gold_placement). (spec Edge Cases)

**Checkpoint**: US2 renders a correct semantic diff with re-approval flags and the
PII-regression guard, and handles the listed edge cases.

---

## Phase 4: User Story 3 - Judgment calls hard-stop, never auto-resolved (Priority: P1)

**Goal**: the Principle-V seam holds across US1 and US2 -- the skill surfaces and the
human decides.

**Independent Test**: `is_unique=false` -> STOP and raise the grain question to the
analyst (never auto-pick a PK / widen the grain); an approve request -> STOP and
state approval is the human's `approvals[]` action (SC-005).

- [ ] T013 [US3] Write the fail-loud judgment-stop table: grain not unique on data
  (owner: analyst); a `pii:` flag toward publish or a `pii:true` not `drop` (owner:
  governance); a business-rollup/segment change (analyst-supplied table required); any
  request to approve the gate (human-only `approvals[]`). Each HARD-STOPS and is
  raised to / points at `mappings/<table>/unresolved-questions.md` with the named
  owner; none is satisfiable by a silent default. (FR-007)
- [ ] T014 [US3] Reinforce the never-write / never-resolve guarantees in the
  procedure body: the skill never writes an approval or `Gate status: CLEARED`, never
  edits `source-map.yaml` to clear a finding, never picks a new candidate PK or grain.
  It surfaces and stops. (FR-008)

**Checkpoint**: every judgment call hard-stops with a named owner; no autonomy hole.

---

## Phase 5: Polish & cross-cutting

- [ ] T015 [FINAL] Append the `## Orchestration` pointer to
  `.claude/skills/grain-confidence-reviewer/SKILL.md` (single-purpose: surface +
  diff, then STOP; the self-heal loop lives only in the conductor) and add the seam
  reference in `.claude/skills/retail-orchestrate/SKILL.md` at the Mapping Ready
  review step. (FR-011)
- [ ] T016 [P] [FINAL] Add the `## See also` block: `docs/readiness/mapping-ready.md`,
  `docs/readiness/readiness-model.md` ("No fake confidence"), `src/retail/profile.py`
  (`PkProof`), `templates/source-map.yaml`, `templates/source-profile.md`,
  `templates/unresolved-questions.md`, the sibling skills, and constitution
  Principles IV/V/VII/VIII. C086 cited as the filled instance only. (FR-010)
- [ ] T017 [FINAL] Generic-only sweep: confirm NO C086/pharmacy specifics (billing
  codes, segment names, PII columns, per-table grain keys) appear in the skill;
  placeholders are obvious generics. (FR-010; Principle VII)
- [ ] T018 [FINAL] Verify gates: `retail check` exits 0 (27 rules), the full unit
  suite stays green, no new Python, `dependencies = []` unchanged, SKILL.md is ASCII
  + UTF-8 no BOM with valid frontmatter and is registered by the harness. (SC-001, SC-002)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependency; start immediately. Blocks all stories (the
  file must exist).
- **US1 (Phase 2)** and **US2 (Phase 3)**: both depend only on Setup; they edit
  different sections of the same SKILL.md, so sequence them or coordinate edits to
  avoid a write conflict (they are logically independent halves).
- **US3 (Phase 4)**: weaves the Principle-V guard through US1 + US2; author after
  both halves exist so the stop-table references real steps.
- **Polish (Phase 5)**: after all stories; T018 is the final gate check.

### Within each story

- US1: T003 (read signal) -> T004 (card) -> T005 (status map); T006/T007 are [P].
- US2: T008 (read versions) -> T009 (grouping) -> T010 (re-approval); T011/T012 [P].
- US3: T013 -> T014.

### Parallel opportunities

- T006, T007 (US1) are independent sub-sections -> [P].
- T011, T012 (US2) are independent sub-sections -> [P].
- T016 (See also) is independent of T015/T017 -> [P].
- US1 and US2 can be drafted in parallel by different contributors IF they
  coordinate the single SKILL.md (different sections); otherwise sequence US1 then US2.

---

## Implementation Strategy

### MVP (the two P1 halves + the guard)

1. Phase 1 Setup (the skill skeleton + guard-rails).
2. Phase 2 US1 (grain confidence card) -- STOP and validate against SC-003.
3. Phase 3 US2 (mapping diff) -- STOP and validate against SC-004.
4. Phase 4 US3 (judgment hard-stops) -- validate against SC-005.
5. Phase 5 Polish + final gate (SC-001/SC-002).

US1 alone is a shippable increment (grain confidence surfaced as evidence); US2 adds
the diff; US3 hardens the human seam across both. Each validates independently.

## Notes

- No new code in this slice -> no test tasks; acceptance is rendered-output
  inspection against the FRs + the existing suite/`retail check` staying green.
- [P] = different file or independent SKILL.md section, no dependency.
- Keep every edit ASCII + UTF-8 no BOM; short paths (Windows 260 limit).
- Commit after each phase or logical group.
- The forbidden outputs (a numeric score; a written approval; an auto-resolved grain)
  are the things to re-check at T017/T018 before claiming done.
