---
description: "Task list for CVD (Colorblind) Simulation Evidence Aid implementation"
---

# Tasks: CVD (Colorblind) Simulation Evidence Aid

**Input**: Design documents from `specs/118-cvd-simulation-evidence/`

**Prerequisites**: plan.md, spec.md. (The finer companion docs -- research.md,
data-model.md, contracts/ -- are OPTIONAL implement-time outputs, not authored in
this spec-only slice; the data model -- palette-colour -> simulated-colour ->
per-pair delta_e76 -- and the evidence/verifier contract are fixed inline in
plan.md's Summary + Technical Context and in the task descriptions below.)

**STATUS**: SPEC-ONLY. These tasks are NOT implemented in this slice (mirrors the
spec-only pattern of specs 116/117, commits #239/#240). Every box stays unchecked;
an implementer runs `/speckit-implement` (or works the list by hand) when a human
gives the go. Nothing here advances a readiness stage or registers a gate.

**Tests**: INCLUDED. The evidence-faithfulness verifier IS the feature's mechanical
guarantee (the reason this is a Python runtime surface, not a skill), and the repo
mandates TDD -- so test tasks are first-class, written before the code they verify.
The verifier sits ON the evidence OUTPUT, independent of the composer (MEMORY:
"verifier must sit on the risk"; never read ground truth from the code under test).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no incomplete-task dependency)
- **[Story]**: US1 / US2 / US3 (maps to spec.md user stories)
- Paths are repo-relative; single-project layout (`src/retail`, `tests/unit`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: fixtures + module skeletons every story leans on.

- [ ] T001 [P] Add CVD fixtures under `tests/unit/fixtures/cvd_evidence/`: `redgreen.theme.json` (a categorical `dataColors` palette containing a red/green pair well-separated under normal vision, for the headline under-deuteranope collapse case), `ramps.theme.json` (a palette PLUS declared sequential/diverging ramp stops), `single.theme.json` (a one-colour palette, no pair), `empty.theme.json` (no/empty `dataColors`), `malformed.theme.json` (invalid JSON), and `badtoken.theme.json` (a palette with one unreadable colour token beside valid hex). ASCII, UTF-8 no BOM; generic colour values only, no brand/C086 palette baked in (Principle VII).
- [ ] T002 [P] Create the evidence-composer skeleton `src/retail/cvd_evidence.py` with the public signatures `compose_cvd_evidence(repo_root, theme_path) -> dict` and `render(evidence, fmt) -> str` (bodies raise `NotImplementedError`), plus a private `_load_theme(theme_path)` helper (stdlib `json` read; returns an explicit unreadable/absent marker on OSError / JSON error, never raising). No DB/driver/network import at module load (driver-free import path, Principle VIII).

**Checkpoint**: fixtures exist; module imports; no DB/driver import at load.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the three deterministic CVD transforms in `color.py`, the under-simulation measurement core, and the evidence-faithfulness verifier every story's tests use.

CRITICAL: no user-story test can assert evidence until the transforms, the measurement core, and the verifier exist.

- [ ] T003 [US-shared] Add the three deterministic CVD simulation transforms to `src/retail/color.py` BESIDE the shipped `delta_e76` (`color.py:83`): `simulate_protanope(hex) -> hex`, `simulate_deuteranope(hex) -> hex`, `simulate_tritanope(hex) -> hex` -- each a closed-form colour-space projection using a fixed published matrix (a widely-cited Brettel/Vienot-style set; the specific matrices are the one bounded implement-time research choice named in plan.md Phase 0). Pure functions, no I/O, no randomness, no new dependency; reuse `color.py`'s existing hex/RGB helpers. Same input -> byte-identical output (FR-002/FR-012).
- [ ] T004 [P] [US-shared] In `tests/unit/test_color.py` (edit, or new if absent), add fixed-input unit tests for the three transforms: each transform maps a set of published reference colours to their published expected simulated values (within a tight documented tolerance), and is deterministic across two calls. These tests pin the transform maths independent of any evidence composition. Assert FAIL before T003 lands.
- [ ] T005 [US-shared] Implement the under-simulation measurement core in `src/retail/cvd_evidence.py`: read the theme's `dataColors` palette (and, when present, declared ramp stops) via `_load_theme`; for EACH simulation type, apply the matching transform to every colour and compute the pairwise `delta_e76` between every colour PAIR on the SIMULATED colours (a MEASUREMENT, FR-003). Return an evidence dict carrying, per simulation type: the simulated swatch per colour, the per-pair deltaE, and the pairs ordered by the measured deltaE (a presentation of the measured values, NOT a computed rank, FR-004). Carry `read_only: True` and a BLANK reviewer/decision slot. NO rolled-up score / verdict / ranking / safe-unsafe statement anywhere (hard rule #9, FR-004). An unreadable colour token is named + skipped, never guessed (edge case). `render` still stubbed.
- [ ] T006 [US-shared] Write the reusable evidence-faithfulness verifier helper `assert_evidence_is_faithful(output_text_or_obj, theme)` in `tests/unit/test_cvd_evidence.py` (the verifier contract fixed inline in plan.md's Summary): (V1) every reported simulated swatch is reproducible by applying the named transform to the named committed colour; (V2) every reported deltaE is reproducible by applying the named transform + `delta_e76` to the two named committed colours (no fabricated value, FR-007); (V3) all three simulation types are present when a palette exists; (V4) NO rolled-up-score / pass-fail / ranking / percentage / "is/is-not colorblind-safe" token appears in the output (FR-004); (V5) the reviewer/decision slot is BLANK (no pre-filled pass/verdict/score, FR-005). The verifier recomputes ground truth from the FIXTURE THEME, NOT from the composer under test (independence). TEST helper only -- NO `@register` rule, NO manifest change (FR-009).

**Checkpoint**: the three transforms are pinned by fixed-input tests; `compose_cvd_evidence` returns a correct evidence dict for the palette fixtures; verifier helper importable and independent of the composer.

---

## Phase 3: User Story 1 - Reviewer gets CVD simulation evidence for the OPEN checkbox (Priority: P1) -- MVP

**Goal**: for a committed theme, emit the simulated swatches + under-simulation pairwise deltaE for all three deficiency types, closest-collapsing pairs surfaced, no rolled-up score, checkbox/stage untouched.

**Independent Test**: run against `redgreen.theme.json`; the under-deuteranope deltaE for the red/green pair is materially smaller than its normal-vision distance; all three simulation types present; no "CVD score" / safe-unsafe verdict anywhere; the OPEN checkbox and `colorblind_considerate_categoricals` untouched.

### Tests for User Story 1 (write first, must FAIL)

- [ ] T007 [P] [US1] In `tests/unit/test_cvd_evidence.py`, add `test_all_three_simulations_present` and `test_redgreen_collapses_under_deuteranope` against `redgreen.theme.json`; each composes the evidence and runs `assert_evidence_is_faithful`; assert all three simulation types appear, the red/green pair's under-deuteranope deltaE is smaller than its normal-vision deltaE, and (SC-002) no rolled-up-score/verdict/ranking token appears. Assert FAIL before T010.
- [ ] T008 [P] [US1] Add `test_no_rollup_no_verdict` (SC-002 / FR-004): assert the composed output contains ONLY per-pair measured distances + simulated swatches -- no single "CVD score", no pass/fail, no theme ranking, no "is/is not colorblind-safe" statement. Assert FAIL before T010.
- [ ] T009 [P] [US1] Add `test_ramp_stops_reported_separately` against `ramps.theme.json` (edge case): ramp stops are simulated + measured and reported in a section distinct from the categorical palette; never conflated. Assert FAIL before T010.

### Implementation for User Story 1

- [ ] T010 [US1] Implement `render` in `src/retail/cvd_evidence.py` for text/markdown + `--format json`: a section per simulation type (simulated swatches + per-pair deltaE, closest-collapsing pairs first as a reading aid), a distinct ramp-stops section when present, an explicit "measured evidence for a human decision" preamble naming the `- [ ] **CVD distinguishability** -- OPEN` checkbox and the theme path it supports, and the BLANK reviewer/decision slot. ASCII `--`/`->`, no glyphs, no rolled-up-score/verdict/ranking token (FR-004/FR-014).
- [ ] T011 [US1] Add the CLI verb `src/retail/cli/commands/cvd_evidence.py` (`retail cvd-evidence --theme <path> [--format text|json] [--out <path>]`) mirroring `cli/commands/pii_notice.py` / `approver_view.py` (the durable-evidence-writer verbs); it composes + renders + writes the SINGLE evidence file to the THEME-ADJACENT default path `themes/<theme-name>.cvd-simulation-evidence.md` (derived from the theme filename, NOT from a table -- there is no theme -> table resolution, Clarification Q4/FR-006), or to `--out <path>` when supplied (e.g. a reviewer placing it into `mappings/<table>/design/`); always returns exit 0 (FR-009). It ticks no checkbox, sets no theme value, touches no `readiness-status.yaml` (FR-005).
- [ ] T012 [US1] Register + dispatch the `cvd-evidence` subcommand in `src/retail/cli/parser.py` and the CLI dispatch table (`src/retail/cli/__init__.py`), following the shipped `pii-notice`/`approver-view` wiring.

**Checkpoint**: MVP -- `retail cvd-evidence --theme themes/<t>.theme.json` writes the evidence file with all three simulations + per-pair deltaE and a blank reviewer slot; US1 tests green.

---

## Phase 4: User Story 2 - Durable evidence with a blank reviewer slot (Priority: P1)

**Goal**: exactly one durable companion evidence file is written with a BLANK named-reviewer/decision slot; every measured value is corpus-derived and reproducible; two runs are byte-identical.

**Independent Test**: run the aid; confirm exactly one file at the theme-adjacent default `themes/<theme-name>.cvd-simulation-evidence.md` (or the `--out` path when supplied), a blank reviewer slot (no pre-filled verdict), every deltaE reproducible from the named theme colours, and a byte-identical second run.

### Tests for User Story 2 (write first, must FAIL)

- [ ] T013 [P] [US2] In `tests/unit/test_cvd_evidence.py`, add `test_single_durable_file_blank_slot` (FR-006 / SC-003): the aid writes exactly one evidence file (+ optional json), the reviewer/decision slot is blank, no pass/verdict/score is pre-filled, and no OTHER file is written (the theme, `readiness-status.yaml`, and the checkbox are untouched). Assert FAIL before T015.
- [ ] T014 [P] [US2] Add `test_deterministic_byte_identical` (FR-012 / SC-007): two runs on the unchanged theme produce byte-identical evidence files (no randomness, no wall-clock timestamp in the measured body; every `delta_e76` value formatted at a FIXED decimal precision so byte-identity holds across platforms; tie ordering uses a fixed lexical secondary order). Assert FAIL before T015.

### Implementation for User Story 2

- [ ] T015 [US2] Add the durable evidence template `templates/cvd-simulation-evidence.md` (mirroring `templates/design-review-evidence.md`, the DL4 precedent): the per-simulation swatch/deltaE sections, the theme + OPEN-checkbox reference, and the BLANK named-reviewer/decision slot. Wire `render`/the CLI verb to fill ONLY the measured body and leave the reviewer slot blank; ensure the written body carries no wall-clock timestamp and a fixed tie order (FR-006/FR-012). No `@register` rule, no manifest change (FR-009).

**Checkpoint**: the evidence is a durable, auditable, blank-slot artifact; two runs identical; US1 + US2 green.

---

## Phase 5: User Story 3 - No-palette / unreadable theme surfaced, not fabricated (Priority: P2)

**Goal**: a theme with no palette (or fewer than two colours), or a malformed/unreadable theme, yields an honest "no palette/pair to simulate" (or "could not read") signal naming the path, never fabricated swatches or a distinguishability result.

**Independent Test**: point at `empty.theme.json` / `single.theme.json` -> "no palette/pair to simulate at <path>", no fabricated swatch; point at `malformed.theme.json` -> "could not read theme at <path>", no fabricated evidence.

### Tests for User Story 3 (write first, must FAIL)

- [ ] T016 [P] [US3] In `tests/unit/test_cvd_evidence.py`, add `test_empty_palette_honest_absence`, `test_single_colour_no_pair`, and `test_malformed_theme_unreadable` (FR-008 / SC-005): assert the aid names the path checked, states there is no palette/pair to simulate (or that the theme could not be read), fabricates no swatch/pair/deltaE, and never presents the absence/unreadability as "simulated and found distinguishable". Assert FAIL before T017.

### Implementation for User Story 3

- [ ] T017 [US3] Extend `compose_cvd_evidence`/`render` for the absent/thin/unreadable theme: return the explicit honest-absence marker with the checked path; never present it as a distinguishability result and never fabricate a swatch, pair, or deltaE (reuses the `_load_theme` unreadable marker from T002).

**Checkpoint**: all three stories independently functional; every fixture covered.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T018 [P] Add the tool doc `docs/tools/cvd-evidence.md` mirroring the shipped `docs/tools/*.md`: what it is, how to run, the scope wall, and what it will NOT do -- names the neighbours it complements (CT1 contrast / CT2 = `design_categorical_distinctness` / CT3 = `design_ramp_deltae`, all normal-vision maths) and the DL4 design-review-evidence artifact it mirrors, and states it fills the `theme_gen.py:569` OPEN checkbox without ticking it.
- [ ] T019 [P] [US-shared] Add the single-write proof test (SC-003): run the CLI verb against a temp theme; assert the ONLY new/modified file is the one evidence file (via `git status` on a temp copy), that the theme JSON and `readiness-status.yaml` are byte-unchanged, and that the composer module contains no write call other than the evidence-file write (grep-verifiable).
- [ ] T020 [P] [US-shared] Add the generic proof test (SC-006): run the SAME composer over two distinct committed themes with no per-theme branch in the composer; confirm correct evidence for both.
- [ ] T021 Run the end-to-end check against a committed theme: confirm all three simulations + per-pair deltaE, the blank reviewer slot, honest absence on an empty theme, and zero rolled-up-score/verdict/ranking tokens. Run `ruff format --check src tests` + `ruff check src tests` + `pytest tests/unit/test_cvd_evidence.py tests/unit/test_color.py -q`; confirm `retail check` still exits 0 and the rules-manifest count is UNCHANGED (proves no gate was added, FR-009).

---

## Dependencies & Execution Order

### Phase dependencies

- Setup (Phase 1) -> Foundational (Phase 2) -> User Stories (3-5) -> Polish (6).
- Phase 2 BLOCKS all stories (the three transforms, the measurement core, and the
  verifier are shared).

### Story dependencies

- US1 (P1): after Phase 2. The MVP (the measured evidence for all three simulations).
- US2 (P1): after Phase 2; adds the durable template + write path (shares T010's
  `render` and T011's CLI verb, so sequence after them to avoid a same-file conflict).
- US3 (P2): after Phase 2; extends `compose_cvd_evidence`/`render` (sequence after
  T010/T015 for the same reason).

### Within each story

- Test first (must FAIL) -> implementation -> checkpoint.
- The three transforms (T003) + measurement core (T005) before any render
  (T010/T015/T017).

### Parallel opportunities

- T001 fixtures + T002 skeleton are [P] with each other (distinct files).
- T004 (transform maths tests) is [P] with T001/T002.
- The per-story TEST tasks (T007/T008/T009, T013/T014, T016) are [P] within a story
  (distinct test functions), but each precedes its own implementation task.
- Polish tasks T018/T019/T020 are [P] (distinct files); T021 is the final serial gate.
- NOTE: T010, T015, T017 all edit `render`/the compose core in one file -> NOT
  parallel; run in story-priority order.

---

## Implementation Strategy

### MVP first (US1 only)

1. Phase 1 Setup -> Phase 2 Foundational -> Phase 3 US1.
2. STOP and validate: `retail cvd-evidence --theme themes/<t>.theme.json` writes an
   evidence file with all three simulations + per-pair deltaE and a blank reviewer
   slot; the red/green pair collapses under deuteranope; US1 tests green.

### Incremental delivery

- +US2 (durable template + blank-slot + determinism) -> +US3 (honest absence) ->
  Polish (tool doc, single-write + generic proofs, full gate run).

---

## Notes

- [P] = different files, no incomplete-task dependency.
- The verifier (T006) is TEST-only -- no `@register` rule, no manifest change
  (FR-009 forbids a gate). It recomputes ground truth from the fixture theme, NOT
  from the composer under test (independence; MEMORY "verifier must sit on the
  risk").
- A per-pair `delta_e76` under a named simulation is a MEASUREMENT (allowed, reused
  from the shipped metric); NO rolled-up "CVD score" / verdict / ranking /
  safe-unsafe statement anywhere (hard rule #9, FR-004).
- This feature WRITES exactly ONE durable evidence file and adds a `templates/`
  companion (unlike spec 116's print-only posture), mirroring the DL4
  design-review-evidence precedent -- because the CVD evidence is a durable
  design-review artifact a reviewer cites (Clarification Q4). The theme JSON, the
  OPEN checkbox, and `readiness-status.yaml` are never written.
- ASCII only, UTF-8 no BOM in every authored file (Principle IX).
- Commit after each task or logical group; each checkpoint is independently testable.
- FR coverage: FR-001 (T005), FR-002 (T003/T004), FR-003 (T005), FR-004
  (T005/T006/T008/T010), FR-005 (T006/T011/T015), FR-006 (T013/T015), FR-007
  (T006), FR-008 (T016/T017), FR-009 (T006/T021), FR-010 (T002/T011/T019), FR-011
  (T001/T020), FR-012 (T003/T014/T015), FR-013 (T018), FR-014 (T010), plus SC-001
  (T007), SC-002 (T008), SC-003 (T013/T019), SC-004 (T007), SC-005 (T016), SC-006
  (T020), SC-007 (T014).
