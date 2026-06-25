---
description: "Task list for PR Readiness Reviewer (F025)"
---

# Tasks: PR Readiness Reviewer

**Input**: Design documents from `specs/019-pr-readiness-reviewer/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Numbering note**: roadmap feature F025; spec-dir `019` is the next free on-disk slot. The
roadmap F-number is authoritative.

**Tests**: This is a planning/docs-only slice (no runtime code). There are no unit tests.
The "verification" tasks (generic-check, source-traceability, blocker-vs-warning rule,
read-only / no-score holds, no new `retail check` rule added) describe what the FUTURE
deliverables must satisfy when built; here they are recorded as planning checks, not run.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3) or SETUP/POLISH
- All paths are repo-relative from the worktree root

## Path Conventions

Planning/docs slice -- no `src/`/`tests/`. This slice writes the five Spec-Kit files under
`specs/019-pr-readiness-reviewer/`. The three FUTURE deliverables
(`.claude/skills/pr-readiness-reviewer/SKILL.md`, `templates/pr-readiness-report.md`,
`docs/tools/pr-readiness-reviewer.md`) are ENUMERATED here as "author spec for X" planning
tasks, NOT implemented in this slice.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Pin the reference shapes and the single source of truth this feature reuses.

- [ ] T001 [P] Re-read the read-only aggregator references -- `specs/013-data-quality-control-room/spec.md`
      + the `retail-control-room` skill ("aggregates, never re-derives") and the
      `retail-validate` skill ("invoke-and-interpret only") -- and capture the
      read-and-report posture + frontmatter idiom the future SKILL.md will match.
- [ ] T002 [P] Re-read the readiness vocabulary -- `docs/readiness/readiness-model.md` +
      `templates/readiness-status.yaml` -- and pin the four statuses + evidence + blockers +
      no-score rule the verdict reuses; note the `mappings/<table>/readiness-status.yaml`
      location (ADR 0004) and the `approvals[]` / `source-map.yaml` approval-metadata fields.

**Checkpoint**: the read-only posture + readiness vocabulary the spec reuses are pinned.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the load-bearing definitions ALL three stories depend on, so no artifact
drifts into ACTING (merge/approve/stage-move) or into a SCORE.

**CRITICAL**: The verdict field set, the gating rule, the read-only boundary, and the
Principle-V routing must be fixed before any story text or future-deliverable shape is
authored, or the module will drift into self-approval or a confidence number.

- [ ] T003 Fix the verdict field set (single source of truth) reused across the spec,
      template, and doc: `merge_ready` (yes/no boolean), `blockers[]`, `warnings[]`,
      `required_human_decisions[]`, `evidence[]`, one `next_action`. [FR-004]
- [ ] T004 Fix the gating rule verbatim: `merge_ready` is `no` while ANY `blockers[]` OR ANY
      open `required_human_decisions[]` exists; `warnings[]` do NOT alone flip it;
      `required_human_decisions[]` is a SEPARATE gating class from blockers and BOTH gate
      `merge_ready: yes`. [FR-005]
- [ ] T005 Fix the read-only boundary statement (verbatim across all three files): the module
      cannot merge, approve, resolve/reply to a thread, push/amend a commit, edit a PR body,
      or move/upgrade a readiness stage -- it observes and reports only (F024 Core Authority;
      Principle V). [FR-009]
- [ ] T006 Fix the no-fake-confidence rule: `merge_ready` is a derived boolean, never a
      number; a score request is declined citing rule #9. And fix the evidence-traceability
      rule: every blocker/warning/required-decision carries a cited PR fact or committed
      source. [FR-010, FR-011]
- [ ] T007 Enumerate the Principle-V `required_human_decisions[]` triggers to embed in every
      artifact: publish approval requested too early; PII publish-safety; grain ambiguity;
      sentinel-vs-null; business rollup/segment mapping. Each routes to a named owner; the
      module recommends, never rules. [FR-008]

**Checkpoint**: field set + gating rule + read-only boundary + no-score/traceability rule +
Principle-V trigger list are fixed and ready to drop into each file identically.

---

## Phase 3: User Story 1 - One structured "is this PR safe to merge" verdict (Priority: P1) MVP

**Goal**: Specify the verdict and the read-fan-out it is built from -- the spec's US1 plus the
shapes of the future template + skill that emit it.

**Independent Test**: a PR with one failing required CI check + one unresolved review thread
yields a verdict where the check is a `blocker` (check name + conclusion as evidence), the
thread is a `warning`, `merge_ready` is `no`, `next_action` names one step, and no action is
taken on the PR.

- [ ] T008 [US1] In spec.md, specify US1 (the structured verdict) with its acceptance
      scenarios and the observed-PR-facts read-fan-out (state, mergeable, CI/workflow,
      threads, comments). [FR-006]
- [ ] T009 [US1] Author the spec's "Aggregates and observes, never re-derives or gates"
      evidence-chain table: each verdict input -> source it observes/reads -> default
      severity. This is the reproducibility backbone of the future template. [FR-006, FR-011]
- [ ] T010 [US1] Enumerate (do NOT create) the future `templates/pr-readiness-report.md`
      shape in plan.md Phase 1: header + the six fields + the embedded severity table +
      generic placeholders. Author spec for the template; do not author the template.
      [FR-002, FR-014]
- [ ] T011 [US1] Enumerate (do NOT create) the future
      `.claude/skills/pr-readiness-reviewer/SKILL.md` procedure in plan.md Phase 1: identify
      PR -> observe -> read evidence -> cross-check -> classify -> apply gating rule -> fill
      template -> STOP. Author spec for the skill; do not author the skill. [FR-001]

**Checkpoint**: the verdict, its inputs, and the shapes of the two future deliverables that
emit it are fully specified. MVP of the planning slice.

---

## Phase 4: User Story 2 - Blocker vs warning, made operational (Priority: P1)

**Goal**: Specify the blocker/warning distinction and the gating rule so acceptance.md can
test it.

**Independent Test**: a PR with one blocker + one warning is `merge_ready: no` (blocker);
remove the blocker and with only the warning it is `merge_ready: yes`, warning still listed.

- [ ] T012 [US2] In spec.md, specify US2 with acceptance scenarios proving warnings do not
      alone gate, blockers do, and ambiguous severities default per the evidence-chain table
      (and record why, never silently promote/demote). [FR-004, FR-005, FR-006]
- [ ] T013 [US2] In spec.md Key Entities, define Blocker, Warning, and Required-human-decision
      distinctly (severity + gating effect + cited-source requirement), keeping
      required-human-decision a SEPARATE class that also gates `merge_ready`. [FR-005]
- [ ] T014 [US2] In plan.md / doc shape, record that the future doc states the gating rule
      explicitly (blocker OR open required-decision -> `no`; warnings surface only) so the
      built doc is unambiguous. [FR-003, FR-005]

**Checkpoint**: the blocker/warning/required-decision taxonomy and the gating rule are
operationalized and testable.

---

## Phase 5: User Story 3 - PR-body drift, readiness/approvals consistency, too-early publish (Priority: P1)

**Goal**: Specify the novel surface F025 owns -- the cross-check between PR CLAIMS and
committed readiness evidence -- and the Principle-V routing for the too-early-publish guard.

**Independent Test**: a PR body asserting "Publish Ready" while `readiness-status.yaml` shows
Semantic Model Ready not `pass` yields a `required_human_decision` (routed to a named owner),
`merge_ready: no`, the cited `readiness-status.yaml` field, and NO stage move or approval.

- [ ] T015 [US3] In spec.md, specify US3: readiness-stage consistency vs
      `mappings/<table>/readiness-status.yaml`, approvals consistency vs `approvals[]`,
      source-map approval metadata vs `source-map.yaml`, and general PR-body drift. A claim
      asserting a stage `pass` unsupported by evidence is a blocker; a lesser unsupported
      claim is a warning. [FR-007]
- [ ] T016 [US3] In spec.md, specify the "publish approval requested too early" guard as a
      `required_human_decision` (Principle V) that routes to a named owner and sets
      `merge_ready: no` until resolved -- the module never approves the publish or moves the
      stage. [FR-008]
- [ ] T017 [US3] In spec.md, specify the "decline to act" scenario: asked to approve/merge or
      mark a stage `pass`, the skill declines, states it is read-only and cannot create truth
      (F024 / Principle V), and returns the verdict. [FR-009]
- [ ] T018 [US3] In spec.md edge cases, specify missing/pending/conflicting evidence handling
      (unknown line names its missing source; pending CI is a blocker for `yes`; conflicts
      are surfaced, not resolved) and the secret-in-diff blocker with the STOP-rotate-sweep
      recommendation (flag, never edit). [FR-012, IX]

**Checkpoint**: the claim-vs-evidence cross-check and the Principle-V routing are specified;
the constitutional guardrails (no self-approval, no stage move, no score) are explicit.

---

## Phase 6: Polish & Cross-Cutting Verification

**Purpose**: Whole-feature gates that span all three stories (planning-level checks of the
five files; future-deliverable checks recorded for when they are built).

- [ ] T019 Complete spec.md's required sections: Why / What-it-is-NOT / Relationship-to-shipped
      (F012, the gates, the Codex review) / Architecture / Requirements (FR-001..FR-014) /
      Success Criteria (SC-001..SC-006) / Human-approval-boundary / Allowed-ops /
      Forbidden-ops / Evidence-required / Readiness-stage-affected (cross-cutting) /
      Dependencies (F024 upstream) / Non-goals / Assumptions / Deferred / See-also.
- [ ] T020 Complete plan.md: Summary, Technical Context (Language/Version: None), the
      Constitution Check table (Principles I-IX -> PASS), Project Structure (the 5 files +
      the 3 PLANNED deliverables), Phase 0/1, Phase-1 re-check, empty Complexity Tracking.
- [ ] T021 Complete checklists/acceptance.md (Content Quality / Requirement Completeness /
      Feature Readiness + Notes) and checklists/governance.md (Core-vs-Module authority,
      Principle-V stop-and-ask, no-self-approval, no-fake-confidence, generic, secrets/paths,
      allowed-vs-forbidden ops, evidence-required), each item mapping to the spec.
- [ ] T022 [P] Confirm all five files are ASCII + UTF-8 no BOM, use `->`/`--` (no Unicode
      symbols, no smart quotes), carry no secret/DSN/token/local path, and stay generic (no
      C086 / `retail_store_sales` specifics; cited-not-inlined). [VII, IX]
- [ ] T023 [P] Confirm the scope wall held: exactly the five Spec-Kit files were written; the
      three future deliverables are ENUMERATED, not created; no runtime code, no new gate, no
      `retail check` rule, no CI workflow was added. [VIII, FR-013]

---

## Phase 7: Future deliverables (enumerated -- NOT built in this slice)

**Purpose**: record the planned outputs so a later slice can author them; each is a separate
"author X" task gated on this spec, NOT part of this planning slice.

- [ ] T024 (FUTURE) Author `templates/pr-readiness-report.md` from the plan Phase-1 shape:
      generic verdict template with the six fields + embedded severity table + read-only and
      no-score header. Gated on this spec.
- [ ] T025 (FUTURE) Author `.claude/skills/pr-readiness-reviewer/SKILL.md` from the plan
      Phase-1 procedure: read-only observe-read-cross-check-classify-gate-report skill with
      the boundary + no-score frontmatter and an `## Orchestration` pointer. Gated on T024.
- [ ] T026 (FUTURE) Author `docs/tools/pr-readiness-reviewer.md`: when to run, field meanings,
      the explicit gating rule, the Principle-V routing, the read-only boundary, and the
      spine mapping (cross-cutting). Gated on T024/T025.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately.
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all user stories (fixes the field set,
  the gating rule, the read-only boundary, the no-score/traceability rule, and the
  Principle-V trigger list every artifact reuses verbatim).
- **User Stories (Phase 3-5)**: all depend on Foundational. US1 (P1) is the MVP (the verdict
  itself + the two future-deliverable shapes). US2 (P1) operationalizes the blocker/warning
  split. US3 (P1) specifies the novel claim-vs-evidence cross-check + Principle-V routing.
- **Polish (Phase 6)**: depends on all three stories complete (it completes + verifies the
  five files).
- **Future deliverables (Phase 7)**: gated on this spec; explicitly out of this slice.

### User Story Dependencies

- **US1 (P1)**: independent after Foundational -- the atomic deliverable (the verdict).
- **US2 (P1)**: builds on US1's verdict (it classifies the verdict's findings); soft
  dependency.
- **US3 (P1)**: builds on US1's verdict + US2's classification (the claim-vs-evidence checks
  feed blockers/warnings/required-decisions); soft dependency.

### Parallel Opportunities

- T001 and T002 (read references) run in parallel.
- US1/US2/US3 all edit the SAME file (`spec.md`) -- author in one pass to minimize edit
  rounds (not parallel within spec.md); the checklists (acceptance.md / governance.md) are
  DIFFERENT files and can be authored in parallel after the spec stabilizes.
- Polish T022/T023 are independent checks -- parallel.

## Parallel Example: after spec.md stabilizes

```
# The two checklists touch different files -- author together:
Author checklists/acceptance.md (Content/Requirement/Feature-readiness + Notes)
Author checklists/governance.md (Core-Authority / Principle-V / no-score / generic gates)
```

## Implementation Strategy

**MVP first**: Setup -> Foundational -> US1 = a fully specified verdict + the two
future-deliverable shapes (template + skill). Then US2 (blocker/warning gating rule) and US3
(claim-vs-evidence cross-check + Principle-V routing) complete the spec, then Phase 6
completes + verifies the five files. Phase 7 (the three deliverables) is a later, gated slice.

**Boundary discipline (the load)**: every file carries the same verbatim read-only boundary
(T005), gating rule (T004), and no-score/traceability rule (T006); Phase 6 (T022/T023) proves
no Unicode, no leak, no C086, and that the scope wall held (5 files only; 3 deliverables
enumerated, not built) -- the ways this slice could fail its own scope.
