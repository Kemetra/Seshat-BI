---
description: "Task list for DF1 Parked-On Map"
---

# Tasks: Parked-On Map / Parked-On Dependency Map (DF1)

**Input**: Design documents from `specs/051-parked-on-map/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/df1-rule-contract.md

**Tests**: TDD is mandatory for this repo (rule modules ship with unit tests + a live
guard). Test tasks are included and precede implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency)
- **[Story]**: the user story the task serves (US1-US4)
- Exact file paths are given.

## Path Conventions

Single project: `src/retail/`, `tests/unit/`, `docs/quality/`, `docs/rules/` at repo root.

---

## Phase 1: Setup (shared)

- [ ] T001 Read the SC1 sibling end-to-end as the shape to mirror:
  `src/retail/rules/status_claims.py`, `docs/quality/status-claims.yaml`,
  `tests/unit/test_status_claims.py`. Confirm `RuleContext`, `Finding`, `Severity`,
  `@register`, and the lazy-`import yaml` pattern in `src/retail/core.py` +
  `src/retail/registry.py`. (No file change.)

---

## Phase 2: Foundational (blocking prerequisites)

- [ ] T002 [P] Author the seed manifest `docs/quality/parked-on.yaml` with top-level
  `edges:` and the five v1 F016-cluster edges from data-model.md (pbi-tools-extract,
  l3-new-operators, f031-maintenance-policy, f032-compatibility-matrix,
  f033-release-maturity). Each: `id`, `blocked`, `parked_on: "F016"`,
  `doc: "docs/roadmap/roadmap.md"`, a byte-literal `anchor` sentence copied verbatim
  from `docs/roadmap/roadmap.md`, and the tracked `evidence` path. No
  `shipped_when_tracked` for any v1 edge. Generic only (no C086 facts). ASCII +
  UTF-8-no-BOM.
- [ ] T003 [P] Verify each edge's `anchor` is literally present in
  `docs/roadmap/roadmap.md` and each `evidence` path is in `git ls-files` BEFORE
  writing the rule (so the live guard will pass). Adjust anchors to match the committed
  roadmap text exactly.

---

## Phase 3: US1 + US2 -- the reconciler (Priority: P1)

**Goal**: DF1 fails loud on a parked-but-shipped contradiction (US1) and on a
nonexistent/unresolvable blocker or absent anchor (US2).

### Tests first (RED)

- [ ] T004 [US1/US2] Create `tests/unit/test_parked_on.py` mirroring
  `test_status_claims.py`: a `_stage(tmp_path, manifest_text, docs, evidence,
  shipped)` helper building a real `RuleContext`, and an `_edge(...)` helper. Write
  failing tests for:
  - honest park (evidence tracked, anchor present, no shipped artifact) -> no finding;
  - parked-but-shipped (`shipped_when_tracked` present in tracked set) -> one ERROR
    naming the edge (US1, FR-007);
  - unresolved evidence (evidence not tracked) -> one ERROR (US2, FR-006);
  - untracked doc -> one ERROR (US2, FR-005);
  - absent anchor -> one ERROR (US2, FR-005);
  - every finding is `rule_id=="DF1"`, `severity is Severity.ERROR` (FR-015);
  - no confidence score field anywhere on the finding (FR-008).
  Run `pytest tests/unit/test_parked_on.py -m unit` and confirm RED (import error /
  missing module).

### Implementation (GREEN)

- [ ] T005 [US1/US2] Create `src/retail/rules/parked_on.py`: module docstring (mirror
  SC1's), `_MANIFEST = "docs/quality/parked-on.yaml"`, `_REQUIRED_FIELDS = ("id",
  "blocked", "parked_on", "doc", "anchor", "evidence")`, a `_finding(message,
  locator)` helper emitting `Severity.ERROR`, and
  `@register("DF1", "Parked-on dependency edges reconcile with tracked-file evidence")`
  decorating `check_parked_on(ctx) -> Iterable[Finding]`. Implement the manifest-level
  branches (missing/untracked, lazy `import yaml` + `YAMLError`, wrong-shape) per
  contracts/df1-rule-contract.md branches 1-3. Run the P1 tests; iterate to GREEN.
- [ ] T006 [US1/US2] Implement the per-edge branches (contract 5-10): not-a-mapping,
  missing required field, untracked doc, absent anchor, unresolved evidence, and the
  optional `shipped_when_tracked`-present parked-but-shipped ERROR. One finding per
  defect; independent across edges. Run the P1 tests to GREEN.

---

## Phase 4: US3 -- fail loud on missing/malformed manifest (Priority: P2)

### Tests first (RED)

- [ ] T007 [US3] Add to `tests/unit/test_parked_on.py` failing tests for: missing/
  untracked manifest -> one ERROR naming the manifest path; malformed YAML -> one
  ERROR; wrong shape (no `edges` list) -> one ERROR; missing-field edge -> one ERROR;
  non-mapping edge entry -> one ERROR; AND a present-but-empty `edges: []` manifest ->
  ZERO findings (spec Q4, clean pass). Confirm the empty-manifest case is RED only if
  branch 4 is not yet implemented.

### Implementation (GREEN)

- [ ] T008 [US3] Confirm/extend the manifest-level branches in
  `src/retail/rules/parked_on.py` so an empty `edges:` list returns no finding while
  missing/malformed/wrong-shape/missing-field all fail loud. Run the US3 tests to GREEN.

---

## Phase 5: US4 -- wire and count the rule (Priority: P2)

- [ ] T009 [US4] Edit `src/retail/rules/__init__.py`: add `parked_on` to the
  side-effecting import tuple and to `__all__` (keep alphabetical/existing order).
- [ ] T010 [US4] Edit `tests/unit/test_rules_wiring.py`: add `"DF1"` to
  `EXPECTED_RULE_IDS` (37 -> 38) with a short comment. Do NOT touch any hard-coded
  count -- the count assertion is `len(EXPECTED_RULE_IDS)`-derived. Run
  `pytest tests/unit/test_rules_wiring.py -m unit` to GREEN.
- [ ] T011 [US4] Regenerate the rule inventory: run `retail manifest --repo .` to
  rewrite `docs/rules/rules-manifest.json` (37 -> 38 entries, DF1 present). Run the
  rule-registry snapshot test to GREEN.

---

## Phase 6: Ship-green + polish

- [ ] T012 Add the live-manifest-vs-real-repo guard test to
  `tests/unit/test_parked_on.py` (mirror SC1's): shell `git ls-files`, build a real
  `RuleContext`, assert `check_parked_on` yields zero findings against the seeded
  `docs/quality/parked-on.yaml`. Run to GREEN (FR-013, SC-005).
- [ ] T013 Add a ledger row to `docs/roadmap/roadmap.md` recording DF1 + the 37->38
  expected-id move. Keep it a generic governance note; do NOT alter any sentence used
  as a manifest `anchor` (re-verify anchors still match after editing).
- [ ] T014 Full local gate: `ruff check`, `pytest -m unit`, `retail check`,
  `retail semantic-check`. Confirm all green and DF1 runs inside `retail check`. Fix
  any ASCII/BOM or formatting issues (Principle IX).

---

## Dependencies & ordering

- T001 before everything (orientation).
- T002, T003 (manifest + anchor verification) before T012 (live guard) and before T013
  (which must not break anchors). T002/T003 are [P] with the Phase 3 test authoring but
  the live guard (T012) needs them done.
- T004 (RED tests) before T005-T006 (GREEN). T007 before T008.
- T009 before T010 before T011 (discovery -> expected-id -> manifest regen).
- T014 last (full gate).

## Independent test criteria (per story)

- **US1**: parked-but-shipped edge -> one DF1 ERROR; honest park -> none (T004).
- **US2**: unresolved evidence / untracked doc / absent anchor -> one DF1 ERROR each
  (T004).
- **US3**: missing/malformed manifest -> ERROR; empty `edges:` -> clean (T007).
- **US4**: expected-id set grows by exactly one; snapshot + wiring tests pass; would
  fail closed if DF1 were registered-but-uncounted (T010, T011).

## Scope guard (do NOT do)

- Do NOT add, wire, start, or vendor F016 or any F031-F033 runtime (FR-014, hard rule
  #6). The only new code is `parked_on.py` + its manifest + the wiring/snapshot edits +
  the roadmap ledger row.
- Do NOT emit any confidence/readiness score (FR-008, hard rule 9).
- Do NOT free-scan roadmap prose (FR-009) -- only manifest-listed edges are checked.
- Do NOT bake C086/pharmacy facts into the rule or manifest (FR-012, Principle VII).
