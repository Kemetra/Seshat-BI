---
description: "Task list for the worked-example-factory documentation feature"
---

# Tasks: Worked-Example Factory

**Input**: Design documents from `specs/084-worked-example-factory/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`quickstart.md`, `contracts/worked-example-completeness.md` (all present,
Phase 0/1 complete).

**Tests**: This is a documentation feature; "tests" are validation/consistency
checks (cross-artifact review, calibration against retail_store_sales, a
read-only `retail check` dry run), not unit/integration test code. They are
included below and are NOT optional, since spec.md's Evidence Requirements
and Success Criteria depend on them.

**Organization**: Tasks are grouped by user story (spec.md P1 x 3), each
independently reviewable. All tasks in this feature are documentation edits
under `specs/084-worked-example-factory/`; none touch `src/**`, `templates/**`,
or any other directory.

**Hard boundary repeated here for execution safety**: every task below stops
at editing files under `specs/084-worked-example-factory/`. No task creates a
`mappings/<table>/` directory, a migration, a PBIP model, or a
`docs/worked-examples/<new-table>.md` file for any concrete domain. No task
runs `git add -A` (stage exact paths only, if/when a human later commits this
work). No task commits, pushes, opens a PR, or merges.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to, or `SETUP`/`XCUT` for
  shared/cross-cutting work

---

## Phase 1: Setup

**Purpose**: Confirm the worktree and directory structure before any content
task begins.

- [x] T001 [SETUP] Confirm worktree is on branch `spec/worked-example-factory`
      at `C:/Users/user/Documents/GitHub/seshat-spec-worktrees/worked-example-factory`,
      clean, based on `main` @ `760545d` (done via `git status --short` /
      `git branch --show-current` at session start).
- [x] T002 [SETUP] Create `specs/084-worked-example-factory/` with
      `checklists/`, `contracts/`, `analysis/` subdirectories (done).
- [x] T003 [SETUP] Set `.specify/feature.json` `feature_directory` to
      `specs/084-worked-example-factory` (done).

**Checkpoint**: Directory structure exists; safe to author content.

---

## Phase 2: Foundational (blocking prerequisite reading + spec)

**Purpose**: The spec itself, and the source material every user story's
tasks cite. No user-story task may cite a file that was not actually read
here.

- [x] T004 [XCUT] Read and cite: `.specify/memory/constitution.md`
      (Principles I, IV, V, VI, VII, VIII, IX; the Readiness System section),
      `AGENTS.md`, repo `CLAUDE.md`, `README.md`, `RELEASE_NOTES.md` (done,
      Phase 0 research).
- [x] T005 [XCUT] Read and cite: `docs/readiness/readiness-model.md`,
      `docs/worked-examples/retail-store-sales.md`,
      `docs/worked-examples/README.md` (done).
- [x] T006 [XCUT] Read and cite: the five mapping-gate templates
      (`templates/source-profile.md`, `source-map.yaml`, `assumptions.md`,
      `unresolved-questions.md`, `reconciliation-report.md`),
      `templates/readiness-status.yaml`, `templates/maturity-report.md` (done).
- [x] T007 [XCUT] Read the four `.specify/templates/*.md` Spec-Kit templates
      (spec/plan/tasks/checklist) to match this chain's shape to repo
      convention (done).
- [x] T008 [XCUT] Confirm no `specs/083-demo-harness/` directory exists yet on
      this branch, so FR-010's relationship statement is written by name/role
      only, not by reading a nonexistent spec.md (done -- verified via
      directory listing).
- [x] T009 [SETUP] Write `specs/084-worked-example-factory/spec.md` (done).
- [x] T010 [SETUP] Write `specs/084-worked-example-factory/checklists/
      requirements.md` and self-validate spec.md against it (done, Pass 1 of
      <=3 allowed).

**Checkpoint**: spec.md exists, self-validated, zero unresolved
`[NEEDS CLARIFICATION]`. User-story-specific plan/contract tasks may begin.

---

## Phase 3: User Story 1 - Author picks and starts a new domain (P1)

**Goal**: Deliver the domain-selection guidance and the quickstart an author
uses to start.

**Independent Test** (from spec.md): hand a fresh agent only `quickstart.md`
and the five templates; confirm it can name a candidate domain, state which
axis it stresses, and identify the first artifact -- without copying
retail_store_sales' answers or inventing a new template.

### Implementation for User Story 1

- [x] T011 [P] [US1] Write `specs/084-worked-example-factory/research.md` Sec 1
      ("What makes a good generic example domain") -- the genericity-axis table
      and the selection rule, citing `docs/worked-examples/retail-store-
      sales.md`'s own stated axes (done).
- [x] T012 [P] [US1] Write `specs/084-worked-example-factory/research.md` Sec 2
      ("How to keep an example generic") -- citing Constitution Principle VII,
      the RC-defaults-then-deviations discipline, and the
      no-cross-table-template-edit rule (done).
- [x] T013 [US1] Write `specs/084-worked-example-factory/quickstart.md`
      "Before you start" section and the numbered sequence (steps 1-8),
      cross-referencing the exact template file for each step and the exact
      readiness stage it belongs to (done; depends on T011-T012 for the
      selection-rule citation).
- [x] T014 [US1] Write `specs/084-worked-example-factory/quickstart.md`
      "Where the process legitimately stops" section, covering: no live DB, no
      human reviewer, a mid-build judgment call, and a domain needing a new
      rule/default (done; depends on T013).

**Checkpoint**: A fresh reader of `quickstart.md` + the five templates alone
can restate the sequence and the first artifact to fill, satisfying spec.md
SC-001.

---

## Phase 4: User Story 2 - Reviewer judges completeness (P1)

**Goal**: Deliver the acceptance-criteria contract and its artifact-set
inventory, calibrated against retail_store_sales.

**Independent Test** (from spec.md): apply the contract to
`mappings/retail_store_sales/` + its narrative doc; confirm it verdicts
"complete."

### Implementation for User Story 2

- [x] T015 [P] [US2] Write `specs/084-worked-example-factory/data-model.md`
      "Worked-Example Artifact Set" table (the 14-item inventory), citing each
      template file and its committed-location pattern (done).
- [x] T016 [P] [US2] Write `specs/084-worked-example-factory/data-model.md`
      "Completeness Tier" entity -- the repo-only vs. human/live-gated split,
      citing Constitution Principle VIII and AGENTS.md's deferred-mode posture
      (done; depends on research.md Sec 5, T017).
- [x] T017 [US2] Write `specs/084-worked-example-factory/research.md` Sec 5
      ("Repo-only vs. live-DB completeness") establishing the two-tier
      rationale before data-model.md's tier entity is written (done; precedes
      T016 in dependency order though listed after in the file).
- [x] T018 [US2] Write `specs/084-worked-example-factory/contracts/worked-
      example-completeness.md` Tier 1 sections A-H, each item citing a
      template's own stated exit criteria (e.g. `source-profile.md`'s Exit
      Gate checklist, `assumptions.md`'s integrity invariant) rather than
      inventing new criteria (done; depends on T015).
- [x] T019 [US2] Write `specs/084-worked-example-factory/contracts/worked-
      example-completeness.md` Tier 2 section (the five human/live-gated
      items), explicitly naming the four `approvals[]` stages and the live
      `retail validate` requirement (done; depends on T018).
- [x] T020 [US2] Write `specs/084-worked-example-factory/contracts/worked-
      example-completeness.md` "Calibration check (SC-002)" section: apply
      every Tier 1 and Tier 2 item to the real `retail_store_sales` artifacts
      and record the verdict, matching that example's own stated status
      (Dashboard Ready `pass`, Publish Ready `warning`) exactly (done;
      depends on T018-T019; this task IS the SC-002 validation, not merely
      documentation of it).

**Checkpoint**: The completeness contract exists, is internally consistent
with data-model.md's tier definitions, and its calibration check (T020)
passes against retail_store_sales -- satisfying spec.md SC-002.

---

## Phase 5: User Story 3 - Maturity vs. capability distinction (P1)

**Goal**: Make the "docs matured, runtime did not gain a feature" rule
explicit and load-bearing across spec.md, plan.md, and research.md -- not
confined to one paragraph.

**Independent Test** (from spec.md): given a hypothetical release-note
sentence conflating the two, an author using this feature's guidance can
name the violation and rewrite it correctly.

### Implementation for User Story 3

- [x] T021 [P] [US3] Write `specs/084-worked-example-factory/research.md` Sec 3
      ("The maturity ladder"), citing `templates/maturity-report.md`'s L0-L6
      rungs verbatim (not re-derived) and stating which rungs a completed
      second example is evidence for (L2, possibly L3) and which it has zero
      effect on (L4-L6) (done).
- [x] T022 [US3] Ensure `spec.md` FR-005, User Story 3, and SC-005 all state
      the maturity-vs-capability rule in the same terms ("zero `src/retail`
      change, zero new CLI verb, zero new rule") so a reviewer sees one
      consistent rule, not three different phrasings (done; verified by
      re-reading the three sections together during spec authoring).
- [x] T023 [US3] Write `specs/084-worked-example-factory/plan.md`
      "Constitution Check" row for the Readiness System, explicitly stating
      this feature advances no per-table stage but is a precondition for the
      maturity ladder's L2/L3 evidence -- the plan-level expression of the same
      rule (done; depends on T021).

**Checkpoint**: The maturity-vs-capability rule appears, consistently worded,
in spec.md (x3 sections), research.md, and plan.md -- satisfying spec.md
SC-005's "explicit, unambiguous statement" requirement.

---

## Phase 6: Cross-cutting closeout

**Purpose**: Tie the four documents together, run STEP 4 (analyze), and
perform the final validation the task instructions require.

- [x] T024 [XCUT] Write `specs/084-worked-example-factory/plan.md` full
      Technical Context, full Constitution Check table (all 9 principles +
      the Readiness System row), Project Structure, likely-future-files list,
      tests/validation section, operational risks, backwards compatibility,
      repo-only-vs-live-DB recap, forbidden-scope restatement, and an
      (expectedly empty) Complexity Tracking table (done).
- [ ] T025 [XCUT] Attempt `speckit-analyze` against this feature's spec/plan/
      tasks. If it runs cleanly inside this worktree, accept its output as
      `analysis/analyze-report.md` (or attach its findings there). If it does
      not run cleanly (worktree/tooling friction), fall back to a MANUAL
      `analysis/analyze-report.md` and note the fallback explicitly -- do not
      spend more than one retry on the automated path before falling back.
- [ ] T026 [XCUT] In `analysis/analyze-report.md`, check: consistency across
      spec/plan/tasks; no missing acceptance criteria; no ambiguous approval
      boundary; no hidden implementation scope; explicit overlap analysis
      naming `083-demo-harness` (runs vs. defines) and
      `docs/worked-examples/retail-store-sales.md` (the existing example this
      feature generalizes from, not duplicates); no unsafe claim; a dedicated
      FAKE-CONFIDENCE / FABRICATED-METRIC risk assessment (flagged as highest
      for this feature, per the task briefing); a live-validation-claim risk
      assessment; an over-governance risk assessment; dependency conflicts (or
      their absence); and a keep-separate-or-narrow recommendation relative to
      `083-demo-harness`.
- [ ] T027 [XCUT] Run `git -C "<worktree>" status --short` and list every
      created file; confirm the list contains only paths under
      `specs/084-worked-example-factory/` plus the `.specify/feature.json`
      pointer update.
- [ ] T028 [XCUT] Run a read-only `retail check --repo .` (and, if it runs
      without side effects, `retail semantic-check --repo .`) from the
      worktree root; record the exact exit code and any output verbatim in
      the final report. If either command is unavailable (no editable
      install in this worktree) or would require installing dependencies,
      record that as the exact skip reason -- do not claim a result that was
      not observed.
- [ ] T029 [XCUT] Compose the final structured report (spec dir path; files
      created; feature summary; dependency notes; biggest risk; ready-for-
      review yes/no; validation commands + exact results; confirmation of no
      commits/push/PR/merge, no files outside the spec dir, no secrets) -- the
      deliverable of this entire task list.

**Checkpoint**: All four chain documents exist and are internally consistent;
analysis is recorded (automated or manual, noted either way); validation
commands were actually run (or their exact skip reason recorded); the final
report is ready to hand back.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup; blocks all user stories (the
  spec must exist and be self-validated before plan/research/contract tasks
  cite it).
- **User Stories (Phases 3-5)**: all depend on Foundational. Phase 3 (US1) and
  Phase 4 (US2) are independent of each other and could be authored in either
  order or interleaved; Phase 5 (US3) depends on research.md's maturity-ladder
  section (T021) and lightly touches spec.md sections also touched during
  Foundational (T022 is a consistency check, not new content).
- **Cross-cutting closeout (Phase 6)**: depends on Phases 3-5 all being
  complete (plan.md and the analyze step need every other document to exist).

### Task-level notes

- T016 depends on T017 despite the numbering (data-model.md's tier entity
  needs research.md Sec 5's rationale established first) -- sequenced this way in
  the file listing because data-model.md's Phase 1 heading precedes
  research.md's later section in read order, but authored with T017's content
  decided first.
- T018-T020 are strictly sequential (each depends on the previous within the
  same file).
- T025-T026 are sequential (T026 is the content of the report T025 produces or
  falls back to).

### Parallel opportunities

- T011, T012 [P] -- different subsections of research.md, no shared state.
- T015, T016 [P] as listed, though see the T016/T017 ordering note above -- treat T017 as a prerequisite in practice.
- T021 [P] with the Phase 4 tasks -- different files (research.md Sec 3 vs.
  contracts/ and data-model.md).

---

## Implementation Strategy

### Documentation-only MVP

Since this is a single docs feature with no independently deployable slices,
"MVP" means: Phase 1 + Phase 2 + Phase 3 (US1) alone already delivers a usable
quickstart, even before the completeness contract (US2) is fully detailed -- matching the spec's per-story independent-test structure. In practice all
three user stories were authored together in this session since they are
short and cross-reference each other, but each remains independently
reviewable against its own Acceptance Scenarios in spec.md.

### What "done" means for this tasks.md

All of Phase 1-5 tasks are marked done (the four content documents plus the
contract exist and are internally consistent, per the Phase checkpoints
above). Phase 6 (T025-T029) is the remaining work: run the analyze step, run
the validation commands, and compose the final report -- executed next, in this
same session, per the parent task's STEP 4 and VALIDATE-AT-END instructions.

## Notes

- No task in this file creates a file outside `specs/084-worked-example-
  factory/` except T003's `.specify/feature.json` pointer update, which is
  itself a spec-chain bookkeeping file, not a runtime artifact.
- No task stages or commits anything; staging/committing is explicitly out of
  scope for this entire chain (task boundaries: "no commit, push, PR, merge").
- `git add -A` is FORBIDDEN for any future commit of this work -- stage exact
  paths under `specs/084-worked-example-factory/` (and the `.specify/
  feature.json` line) only, never a blanket add.
