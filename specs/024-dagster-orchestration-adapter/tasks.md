---
description: "Task list for Dagster Orchestration Adapter (F030)"
---

# Tasks: Dagster Orchestration Adapter

**Input**: Design documents from `specs/024-dagster-orchestration-adapter/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Roadmap feature**: F030 (spec-dir 024). When the dir number and the F-number disagree, the
roadmap F-number wins.

**Tests**: This is a planning-only feature (no runtime code, no Dagster files). There are no
unit tests. Verification tasks (five-files-only, ASCII/no-BOM, no-Dagster-file-created,
`retail check` green) stand in for tests and are included explicitly. Every task that names a
PLANNED future deliverable is a PLANNING task ("Author the spec/section for X"), never
"implement X."

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4) or SETUP/FOUND/POLISH
- All paths are repo-relative from the worktree root

## Path Conventions

Planning feature -- no `src/`/`tests/`. The five artifacts live under
`specs/024-dagster-orchestration-adapter/` (spec.md, plan.md, tasks.md, checklists/acceptance.md,
checklists/governance.md). All Dagster files named below are PLANNED future outputs this slice
ENUMERATES and does NOT create.

---

## Phase 1: Setup (Shared Grounding)

**Purpose**: Pin the reusable shapes and the authority boundary before authoring.

- [ ] T001 [SETUP] Confirm the spec-dir (024) / roadmap-F (F030) numbering note is in every
      file header, and the batch mapping is stated (F024=018 .. F033=027).
- [ ] T002 [P] [SETUP] Re-read the reuse shapes: `.claude/skills/retail-orchestrate/SKILL.md`
      (the gate-read + human-seam posture Dagster reuses), `docs/readiness/readiness-model.md`
      (the four-status / no-score vocabulary), and the house style in `specs/010` / `specs/013`.
      Capture the exact gate-read idiom ("you may READ `Gate status`; you may not write
      `CLEARED`") to mirror.

**Checkpoint**: numbering note pinned; the conductor's gate-read posture and the no-score
vocabulary are captured for reuse.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the authority boundary + the asset-graph gate semantics ALL stories depend on.

**CRITICAL**: No user-story acceptance may be authored until the derived-evidence vs authored-
truth boundary and the STOP/HUMAN-SEAM edge classification are fixed, or the stories will drift
into letting Dagster author truth.

- [ ] T003 [FOUND] Write the derived-evidence vs authored-truth boundary as the single source
      of truth to reuse across spec + checklists: Dagster WRITES derived run-evidence (what
      happened) and READS committed approvals (the GO signal); it NEVER writes a readiness
      `pass`, a `Gate status: CLEARED`, an approval, or a metric/mapping/grain/rollup/PII
      ruling. State the reconciling sentence: mechanical stages -> Dagster writes the check
      evidence, Core Authority records the `pass`; human-seam stages -> Dagster reads the
      approval and halts if absent.
- [ ] T004 [FOUND] Fix the asset-graph gate semantics: enumerate the 11 assets and classify
      every edge as a STOP edge (failed gate halts all downstream) or a HUMAN-SEAM edge (reads
      committed approval, halts if absent). State that `publish_execution_evidence` is gated on
      `publish_ready = pass` and only TRIGGERS F016.
- [ ] T005 [FOUND] Fix the closed allowed-vs-forbidden lists: allowed RUN steps (load bronze,
      profile, dbt/SQL migrations, `retail check`, `retail validate`, semantic check, handoff
      pack, write run evidence) vs forbidden (approve mapping/metrics, write `pass`/`CLEARED`,
      define truth, publish Power BI, bypass source-map gate, resolve ambiguity, emit a score).
- [ ] T006 [FOUND] Fix the no-score / ASCII / generic rules to apply to every file: run
      evidence is statuses + measured numbers (no confidence score, Principle IX); ASCII +
      UTF-8 no BOM (`->` arrows, `--` dashes); placeholders only, C086 cited not inlined.

**Checkpoint**: the authority boundary, the asset-graph edge classification, the allowed/
forbidden lists, and the no-score/ASCII/generic rules are fixed and reusable verbatim.

---

## Phase 3: User Story 1 - Failed validation STOPS downstream assets (Priority: P1) MVP

**Goal**: Author the spec content for the fail-closed STOP-edge property.

**Independent Test**: with a forced non-zero gold-validate fixture, no downstream asset
materializes, the run evidence records the failing exit + measured numbers, and no stage flips.

- [ ] T007 [US1] Author in `spec.md` the US1 story + Given/When/Then scenarios: a failed gate
      asset (`retail validate`) fails closed and halts ALL downstream assets; no run-around.
- [ ] T008 [US1] In `spec.md`, tie US1 to FR-005 (fail-closed propagation is a hard graph
      property) and to the asset-graph STOP edges from T004; state the run-evidence record of
      the failure carries measured numbers, not a score.
- [ ] T009 [US1] In `plan.md`, ensure the asset-graph design names the STOP edges at the
      check/validate/semantic-check nodes (no implementation -- planning only).

**Checkpoint**: the fail-closed downstream-stop property is specified and tied to the graph.

---

## Phase 4: User Story 2 - Approval-gate asset reads committed approval; absent -> blocks (Priority: P1)

**Goal**: Author the spec content for the human-seam read-only approval posture.

**Independent Test**: with `Gate status: OPEN`, `silver_tables` does not materialize, the open
mapping blocker + named owner are surfaced, and nothing wrote `CLEARED`; with `CLEARED`, the
silver asset is permitted.

- [ ] T010 [US2] Author in `spec.md` the US2 story + Given/When/Then: human-seam assets READ
      the committed approval (`Gate status`, `approvals[]` owner+date) and HALT if absent;
      never self-grant; never invent a parallel marker (mirror the `retail-orchestrate` idiom
      from T002).
- [ ] T011 [US2] In `spec.md`, enumerate the human-seam assets (`source_map`, `semantic_model`,
      `publish_execution_evidence`) and bind each to the named human approver in the Human
      approval boundary section. [FR-006]
- [ ] T012 [US2] In `spec.md`, add the edge case "source-map gate OPEN at run time -> silver
      asset blocks; records open blocker; nothing approved" (Principle IV).

**Checkpoint**: the read-only approval seam is specified for every human-seam asset.

---

## Phase 5: User Story 3 - Completed run writes evidence and flips no stage (Priority: P1)

**Goal**: Author the spec content for the derived run-evidence record + the no-truth-write rule,
and ENUMERATE the planned run-evidence template.

**Independent Test**: a green run writes a `dagster-run-evidence.md` with per-asset exit codes +
measured numbers + timestamps, AND `git diff` shows zero changes to any readiness `status`,
`Gate status`, or `approvals[]`.

- [ ] T013 [US3] Author in `spec.md` the US3 story + Given/When/Then: a completed run writes
      derived run-evidence (per-asset gate command, exit, measured numbers, timestamp, commit
      sha, blocked reasons + owners) and flips NO stage / writes NO approval. [FR-007]
- [ ] T014 [US3] In `plan.md`, ENUMERATE the planned `templates/dagster-run-evidence.md` shape
      as a FUTURE output (Author the template later -- NOT create it now): run id, commit sha,
      timestamp, per-asset block, blocked-asset block; no score field.
- [ ] T015 [US3] In `spec.md` Evidence-required, state the green-run and blocked-run evidence
      contents and that evidence is append/record-only, never overwriting a human gate field.

**Checkpoint**: the derived-evidence record is specified, the template is enumerated (not
created), and the no-truth-write rule is bound to the story.

---

## Phase 6: User Story 4 - No self-approval: Dagster proposes and runs; gate/Core Authority dispose (Priority: P1)

**Goal**: Author the spec content for the constitutional no-self-approval guardrail and the
F016 publish-trigger-only constraint.

**Independent Test**: no asset in the planned graph can write a stage `pass`, `Gate status:
CLEARED`, an approval, a metric/mapping definition, or a Power BI publish; the Forbidden
operations section enumerates each.

- [ ] T016 [US4] Author in `spec.md` the US4 story + Given/When/Then: a green `retail check`
      asset records exit-0 evidence but does NOT write the stage `pass` (Core Authority records
      it); any judgment call HALTS the asset and escalates (Principle V). [FR-004]
- [ ] T017 [US4] In `spec.md`, author the F016 publish-trigger-only scenario: with
      `publish_ready = pass`, the publish asset TRIGGERS F016 and Dagster opens no Power BI
      connection and publishes nothing (Principle II + hard rule #6).
- [ ] T018 [US4] In `spec.md`, ENUMERATE the planned ADR
      `docs/decisions/0008-dagster-is-orchestration-adapter.md` as a FUTURE output (Author the
      ADR later -- NOT create it now) recording "Dagster runs steps, decides no stage" + the
      authority boundary.

**Checkpoint**: the no-self-approval guardrail and the publish-trigger-only constraint are
specified; the ADR is enumerated (not created).

---

## Phase 7: Cross-Cutting Planning Tasks (enumerate the remaining future deliverables)

**Purpose**: Ensure every PLANNED future output is enumerated in the spec/plan as a planning
task -- never created.

- [ ] T019 [P] In `plan.md`, ENUMERATE the planned project layout as future shape (NOT created):
      `orchestration/dagster/{README.md, pyproject.toml}`,
      `src/tower_bi_orchestration/{definitions.py, assets/, jobs/, sensors/, schedules/}`.
- [ ] T020 [P] In `spec.md`/`plan.md`, ENUMERATE the planned `docs/integrations/dagster-adapter.md`
      and `.claude/skills/dagster-orchestration-adapter/SKILL.md` as future outputs (Author
      later -- NOT create now).
- [ ] T021 [P] In `spec.md`, author the F005 reconciliation: `retail-orchestrate` is the
      conversational conductor; Dagster is the unattended/CI sibling -- same sequence, same
      gate-exit authority, same two human seams, neither self-approving. Cite the F005 sequence,
      do not redefine it. [FR-008]
- [ ] T022 [P] In `spec.md`, author the auto-update posture: pin dagster + dagster-dbt together,
      PR-only, definitions-load smoke (minimum CI gate), small orchestration smoke once impl
      exists, no automerge for Dagster majors; DEFER the shared policy to F031/F033. [FR-009]
- [ ] T023 [P] In `spec.md`, state the dependency roles by F-number: F024 (category parent,
      Execution-Adapter/Maintenance mix), F029 (dbt adapter Dagster orchestrates via
      dagster-dbt), F016 (parked publish adapter the publish asset triggers). Do not invent
      their internals.

**Checkpoint**: all PLANNED deliverables are enumerated as planning content; none is created.

---

## Phase 8: Polish & Cross-Cutting Verification

**Purpose**: Whole-feature gates that span all four stories.

- [ ] T024 Author `checklists/acceptance.md` (spec quality + acceptance): Content Quality,
      Requirement Completeness, Feature Readiness, with [x] CHK items mapped to FR-001..FR-012
      and SC-001..SC-007, plus a Notes section.
- [ ] T025 Author `checklists/governance.md` (Core-Authority gate): Core-vs-adapter authority,
      Principle-V stop-and-ask, no-self-approval, no-fake-confidence, generic (no worked-example
      leak), secrets/paths, allowed-vs-forbidden ops, evidence-required -- [ ] CHK items mapping
      to the spec's Forbidden operations + Human approval boundary.
- [ ] T026 [P] Verify exactly five files exist for this feature and that ZERO Dagster files,
      pyproject, modules, docs, ADR, template, or skill were created by this slice. [SC-001]
- [ ] T027 [P] Grep all five files for non-ASCII characters (expect zero) and confirm UTF-8 no
      BOM and `->`/`--` usage. [FR-011, SC-007]
- [ ] T028 [P] Grep all five files for worked-example leakage (billing codes, segments, PII
      columns, grain keys) -- expect zero; C086 / retail_store_sales only as cited references.
      [FR-010, SC-007]
- [ ] T029 Run `retail check` over the repo: confirm exit 0 and that the diff adds no new rule (this slice
      adds no rule). Confirm repo-relative paths stay short (`<= 200` chars). [Principle VIII, IX]

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately.
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all user stories (fixes the authority
  boundary, the asset-graph edge classification, the allowed/forbidden lists, and the
  no-score/ASCII/generic rules every story reuses verbatim).
- **User Stories (Phase 3-6)**: all depend on Foundational. US1 (P1) is the MVP (fail-closed
  propagation). US2/US3/US4 are all P1 and build on the same fixed boundary; they can be authored
  in sequence within `spec.md` (one file) or split with the cross-cutting Phase 7.
- **Cross-Cutting (Phase 7)**: depends on the stories existing (it enumerates the remaining
  future deliverables and the relationships referenced from the stories).
- **Polish (Phase 8)**: depends on all stories + cross-cutting complete (it authors the two
  checklists and runs the whole-feature gates).

### User Story Dependencies

- **US1 (P1)**: independent after Foundational -- the MVP fail-closed property.
- **US2 (P1)**: independent after Foundational -- the human-seam read-only posture.
- **US3 (P1)**: depends on the boundary (T003) -- the derived-evidence record + no-truth-write.
- **US4 (P1)**: depends on the boundary (T003) + the allowed/forbidden lists (T005).

### Parallel Opportunities

- T002 (read references) runs parallel to T001.
- US1-US4 all edit ONE file (`spec.md`) -- author in passes to minimize edit rounds (not
  parallel within the file); the cross-cutting Phase 7 tasks T019-T023 touch different sections
  / `plan.md` and can be drafted in parallel once the stories exist.
- Polish T026/T027/T028 are independent greps -- parallel.

## Parallel Example: after the stories ship

```
# Phase 7 cross-cutting (different sections / plan.md) -- draft together:
Enumerate planned project layout in plan.md (T019)
Enumerate planned adapter doc + skill (T020)
Author F005 reconciliation (T021) / auto-update posture (T022) / dependency roles (T023)
```

## Implementation Strategy

**MVP first**: Setup -> Foundational -> US1 = the fail-closed STOP-edge property specified. Then
US2 (human seam), US3 (derived evidence), US4 (no self-approval), then Phase 7 enumerates the
remaining PLANNED deliverables, then Phase 8 authors the two checklists and runs the
whole-feature gates.

**Boundary discipline (the load)**: every story carries the same verbatim derived-evidence vs
authored-truth boundary (T003) and the same allowed/forbidden lists (T005); Phase 8 (T026-T029)
proves the five-files-only / no-Dagster-file / ASCII / no-leak / `retail check`-green
properties -- the ways this planning slice could fail its own scope.
