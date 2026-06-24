# Tasks: Tower BI Agent Kit -- Foundation (Phase 0/1)

**Feature**: `001-retail-bi-agent-kit` | **Date**: 2026-06-24
**Plan**: [`plan.md`](./plan.md) | **Spec**: [`spec.md`](./spec.md)

> **Read this first.** Feature 001 is a **docs-and-methodology foundation whose deliverables
> are already implemented and committed** (`7a691e0` foundation files; `1eb0c98` Spec-Kit
> init + constitution v1.1.0). So most tasks below are checked done `[X]` -- they record
> *what was built*, organized by the spec's user stories, with the committed file as the
> evidence. The genuinely-open work is in Phase 6 (commit the plan artifacts) and the
> "Out of scope / future slices" section (the four deferred decisions). Tests here are
> documentation-quality gates (adversarial review + deterministic checks), not code tests.

**Task ID legend**: `[P]` = parallelizable | `[US1/2/3]` = maps to the spec's user stories |
`[X]` = already complete (committed) | `[ ]` = open.

---

## Phase 1: Setup

- [X] T001 Initialize Spec-Kit into the repo (`specify init --here --integration claude --script ps`) -> `.specify/templates/`, `.specify/scripts/powershell/`, `.claude/skills/speckit-*` (commit `1eb0c98`)
- [X] T002 Create the feature directory `specs/001-retail-bi-agent-kit/` with `spec.md` (commit `7a691e0`)
- [X] T003 Confirm Postgres-first, gold-only substrate and no new dependencies (constitution Principle III; plan Technical Context)

## Phase 2: Foundational (blocking prerequisites for all stories)

- [X] T004 Author the keystone architecture map `docs/architecture/tower-bi-agent-kit.md` (agent-first D->C->A->engine->substrate; places existing pieces; defines the source-mapping gate) (commit `7a691e0`)
- [X] T005 Author the constitution `.specify/memory/constitution.md` (9 principles, MUST/SHOULD + Rationale, Governance, Sync Impact Report) and amend to v1.1.0 for the Spec-Kit init (commits `7a691e0`, `1eb0c98`)
- [X] T006 [P] Establish ASCII-only + UTF-8-no-BOM + cross-link discipline across all foundation files (constitution Principle IX; verified by deterministic scan)

## Phase 3: User Story 1 (P1) -- Source mapped and reviewed before any silver SQL exists

**Goal**: the source-mapping gate exists as a hard, mandatory rule with committed artifacts.
**Independent test**: a reviewer confirms, from committed files alone, that mapping is
required before silver and that the profile/map templates capture grain-first decisions.

- [X] T007 [US1] State the source-mapping gate as mandatory ("before any `silver.*` SQL") in `docs/architecture/tower-bi-agent-kit.md` Sec 5, `.specify/memory/constitution.md` Principle IV, and `specs/001-retail-bi-agent-kit/spec.md` FR-001/US1
- [X] T008 [P] [US1] Author `templates/source-profile.md` (Phase 1 profiling; missingness as `'' OR NULL`; candidate grain + PK verified on data)
- [X] T009 [P] [US1] Author `templates/source-map.yaml` (the spine: grain+PK first, per-column keep/drop/rename/type/PII/gold-placement, gold star, derived columns; valid YAML; dim refs resolve)
- [X] T010 [US1] Reconcile the gate with the medallion playbook as a *formalization* of Phases 1/2/4 (not a competing method) -- architecture Sec 5, constitution Principle IV

## Phase 4: User Story 2 (P2) -- Decisions traceable: defaults adopted vs deviations + stop-and-ask

**Goal**: per-table decisions are reviewable as a diff against ADR 0002 defaults, and the
agent's stop-and-ask boundaries are encoded.
**Independent test**: a reviewer sees `assumptions.md` distinguishes adopted vs deviation
(+ triggering data fact) and `unresolved-questions.md` enumerates the stop-and-ask classes
with a who-must-answer owner.

- [X] T011 [P] [US2] Author `templates/assumptions.md` (RC1-RC16 adopted-vs-deviated; deviation requires a triggering data fact; references ADR 0002 by path)
- [X] T012 [P] [US2] Author `templates/unresolved-questions.md` (build-blocking questions; who-must-answer column; the five stop-and-ask decision classes)
- [X] T013 [US2] Encode the agent stop-and-ask duty as a constitution principle (V. Agent Stops at Judgment Calls) and a functional requirement (spec FR-016) + US2 acceptance scenario -- *(added by the v1.0.0 adversarial review, Gate 7)*

## Phase 5: User Story 3 (P3) -- Build acceptance-checked against a reconciliation report

**Goal**: a generic reconciliation-report blank documents the live-acceptance categories.
**Independent test**: a reviewer confirms `reconciliation-report.md` covers PK uniqueness,
date coverage, 0 orphan FKs, and penny-exact reconciliation as *categories* (no validator
logic), citing C086 as a filled instance.

- [X] T014 [P] [US3] Author `templates/reconciliation-report.md` (live-acceptance categories only: PK uniqueness, date coverage, orphan FKs, penny-exact reconciliation; C086 cited)
- [X] T015 [US3] Document the static-vs-live validator split (static = `retail check`; live = deferred `retail validate`) -- constitution Principle VIII, spec FR-005, architecture Sec 7

## Phase 6: Plan artifacts + verification (the open work)

- [X] T016 Generate the plan `specs/001-retail-bi-agent-kit/plan.md` with the 9-principle Constitution Check (9/9 PASS; discharges the deferred-Constitution-Check note)
- [X] T017 [P] Generate `research.md` (design decisions D-001..D-006; the four deferred items recorded as deferred-by-design, NOT resolved)
- [X] T018 [P] Generate `data-model.md` (the five mapping-gate artifacts as a document model) and `quickstart.md` (how a new table flows through the kit)
- [X] T019 Run the adversarial review (7 gates) + deterministic checks (ASCII, YAML, cross-links, principle renumber) over all foundation files -- 9 findings applied/triaged
- [X] T020 Commit the plan artifacts (plan/research/data-model/quickstart/tasks) on `main` and push -- done in commit `4bd7081`. *(The "CLAUDE.md plan pointer" here is the `<!-- SPECKIT START -->` marker block that `specify init` created and `/speckit-plan` updates to reference the plan path -- a standard Spec-Kit mechanism, in scope as part of running the chain. It is NOT the constitution-at-a-glance pointer the constitution Sync Impact Report marks out-of-scope; those are different blocks.)*

## Phase 7: Polish & cross-cutting

- [X] T021 [P] Cross-link the 8 foundation files to each other and to the existing authoritative docs (playbook, ADR 0002, worked example, governance spec) -- verified all paths resolve (SC-003)
- [X] T022 [P] Verify SC-001..SC-006 hold (mapping-before-silver stated; 0 pharmacy tokens in templates; files cross-link; nothing re-decided; 1:1 template<->phase mapping; exactly four `[NEEDS CLARIFICATION]`)

---

## Out of scope -- future slices (NOT tasks for 001)

These are deferred **by design** (constitution v1.1.0; research.md Q-1..Q-4). They are named
here so the boundary is explicit, and each is a candidate next feature spec:

- **(DONE in feature 002) Resolve the D-namespace collision** -- ADR defaults renamed `D1-D16` -> `RC1-RC16`; checker keeps `D1-D8`. Unblocks wiring any ADR default into `retail check`.
- **(future) Decide per-table mapping-artifact location** (`mappings/<table>/` vs alongside migration vs `docs/`).
- **(future) Layer-D agent orchestration** -- the runtime that drives the playbook and self-heals against the gate.
- **(future) `retail validate` live-surface spec** -- implement the live-validator categories (needs a live DB harness).
- **(future) Next worked example** -- run a new retail table end to end through the kit (exercises every template).

---

## Dependencies & execution order

- **Phase 1 -> Phase 2 -> Phases 3/4/5**: setup and the keystone (architecture + constitution) precede the templates; the three user-story phases are otherwise independent of each other (US1/US2/US3 templates were authored in parallel).
- **Phase 6** depends on Phases 1-5 (the plan documents the committed work).
- **All tasks complete** (T020 closed in commit `4bd7081`). The feature-001 foundation slice is fully delivered.

## Implementation strategy

MVP = User Story 1 (the source-mapping gate) -- already delivered. US2 (traceability +
stop-and-ask) and US3 (reconciliation categories) are delivered increments on top. The kit
is usable now for documenting a table's mapping; the forward chain (build + validate +
orchestrate) is the future-slices list above.

## Summary

- **Total tasks**: 22 | **Complete `[X]`**: 22 | **Open `[ ]`**: 0 (T020 closed in commit `4bd7081`).
- **Per story**: US1 = 4 (T007-T010) | US2 = 3 (T011-T013) | US3 = 2 (T014-T015).
- **Parallel opportunities**: the five templates (T008/T009/T011/T012/T014) were authored in parallel; plan artifacts (T017/T018) likewise.
- **MVP**: US1 (the gate) -- delivered.
