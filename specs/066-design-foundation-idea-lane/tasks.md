---
description: "Task list for Design-Foundation Idea Lane + Backlog Seed (G1)"
---

# Tasks: Design-Foundation Idea Lane + Backlog Seed (G1)

**Input**: Design documents from `/specs/066-design-foundation-idea-lane/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/design-lane.md

**Tests**: This feature is docs + a small JS render edit; verification is read-only
inspection plus the existing `retail check` gate. No new pytest module is added
(no `src/retail` change). Verification tasks are inspection tasks, not test code.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 / US2 / US3, or SETUP / POLISH

## Blocking human decisions (Principle V -- must be ruled before the affected task)

- **D-A (grain, FR-011)**: lane grain (section vs tag vs filter view) blocks T101.
- **D-B (ledger schema, FR-012)**: schema-change-vs-reuse blocks T201.
- **D-C (F-row)**: whether G1 gets a roadmap F-row (default off-spine, `none`).

These are recorded OPEN in spec.md ## Clarifications. Implementation of the tasks
they gate MUST NOT proceed until a human rules them; the default column notes the
conservative fallback if a human accepts it.

---

## Phase 1: Setup

- [ ] T001 [SETUP] Confirm the four target files exist and are the current seams
  (read-only): `docs/roadmap/idea-backlog.md`, `docs/roadmap/shipped-ideas.yaml`,
  `.claude/workflows/idea-engine.js`, `.claude/skills/powerbi-dashboard-design/SKILL.md`.
- [ ] T002 [SETUP] Confirm no `src/retail/rules/` design module and no reconciler
  exist, and record that this feature will add neither (FR-009 boundary).

---

## Phase 2: User Story 1 -- Design ideas have a lane to land in (P1)

**Goal**: A first-class design-foundation grouping in the backlog.

**Independent test**: Read the rendered backlog; the grouping is present,
design-layer ideas are attributed to it, and no numeric score is attached.

- [ ] T101 [US1] (BLOCKED on D-A grain) Add the design-foundation grouping to
  `docs/roadmap/idea-backlog.md` at the human-ruled grain (default if accepted:
  a new categorical `## ` section grouping the `strengthens_layer = design-system`
  ideas). Categorical only -- no score (C2).
- [ ] T102 [US1] Edit `.claude/workflows/idea-engine.js` render/routing so the
  existing `design` lens + `design-foundation` reviewer output is grouped/rendered
  under the grouping via the existing `design-system` signal. Routing/rendering
  ONLY -- no scoring, no Memory-contract change, no authoring (C5, FR-007).
- [ ] T103 [P] [US1] Verify (read-only): grouping present, design ideas attributed,
  non-design ideas not forced in, empty-state renders present-but-empty, zero
  numeric score (SC-001, SC-002; C1, C2).

**Checkpoint**: US1 delivers a viable minimum on its own.

---

## Phase 3: User Story 2 -- Shipped design idea gets the same shipped-row link (P2)

**Goal**: The ledger contract accommodates a design-layer ship (shape-only now).

**Independent test**: The existing `{ status, pr_sha, f_row }` shape can carry a
design-layer key and validates under the human-curated read-only contract.

- [ ] T201 [US2] (BLOCKED on D-B schema) Confirm/annotate `docs/roadmap/shipped-ideas.yaml`
  so a design-layer ship reuses the existing `{ status, pr_sha, f_row }` shape
  (default if accepted: reuse unchanged; no schema field added). Do NOT add any
  design entry now -- no design idea has shipped (Clarify Q2, C4).
- [ ] T202 [US2] Verify (read-only): ledger stays human-curated + engine-read-only,
  no fabricated entry, no F-row self-assignment; header invariant intact
  (SC-003; C3, C4).

**Checkpoint**: US2 pays off only when a design idea actually ships.

---

## Phase 4: User Story 3 -- A design author can find the lane (P3)

**Goal**: A "See also" pointer from the design skill to the lane.

**Independent test**: The skill's `## See also` names the lane and points to it.

- [ ] T301 [US3] Add a "See also" pointer in
  `.claude/skills/powerbi-dashboard-design/SKILL.md` to the design-foundation lane
  in `docs/roadmap/idea-backlog.md` (C6, FR-008).
- [ ] T302 [P] [US3] Verify (read-only): the pointer is present and resolves to the
  lane's backlog location (SC-006).

---

## Phase 5: Polish + cross-cutting

- [ ] T401 [POLISH] Grep the full change set for worked-example specifics
  (pharmacy/c086 paths, hexes, metric names, sample data) -> expect none
  (SC-005; C7, FR-010).
- [ ] T402 [POLISH] Confirm no `src/retail/rules/` module and no reconciler were
  added (SC-004; C8, FR-009).
- [ ] T403 [POLISH] ASCII + UTF-8 no-BOM check on every authored artifact (rule IX:
  `--` and `->`, no glyphs).
- [ ] T404 [POLISH] Run `retail check` -> expect Passed.

---

## Dependencies

- T001, T002 (Setup) precede all.
- T101 blocked on human decision D-A; T201 blocked on D-B.
- T102 depends on T101 (grouping must exist before routing renders into it).
- T103 depends on T101 + T102; T202 depends on T201; T302 depends on T301.
- Polish (T401-T404) runs after US1/US2/US3 edits land.

## Parallel opportunities

- T103, T302 are independent verifications ([P]).
- US3 (T301) touches a different file than US1/US2 and can be authored in parallel
  with T102/T201 once the grouping location is known.
