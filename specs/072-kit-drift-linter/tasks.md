# Tasks: Kit Projection-Drift Linter (Compass-Driven Phase-2)

**Feature**: `072-kit-drift-linter` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Tests ARE included: SC-001..SC-006 name concrete pass/fail guarantees (projection drift
detected, not-bootstrapped, parse-error, no-constitution-read, read-only) that require
unit coverage. Paths relative to repo root. `[P]` = parallelizable.

---

## Phase 1: Setup

- [x] T001 Create `src/retail/kit_lint.py` skeleton with the module docstring stating the invariant: standalone (not a `retail check` rule), read-only, MAY import pyyaml lazily, reads NO constitution, no numeric score

---

## Phase 2: Foundational

- [x] T002 Implement the two check functions in `src/retail/kit_lint.py`: `check_yaml_projection` (wrap `compass_project.check_yaml_drift`) + `check_prose_projection` (wrap `compass_project.check_prose_drift(load_source(repo), fence.read_fence_body(path))` per governed file). Each returns a `CheckResult` (data-model E1)
- [x] T003 Implement `lint(repo)` returning a `LintReport` (E2): not-bootstrapped → `bootstrapped=False, ok=True`; else run the two checks. Wrap `load_source` in try/except → a `source_parse` failing `CheckResult`, never a traceback (R4). `report.ok` maps to the exit code

---

## Phase 3: User Story 1 — projection drift fails loud (P1) 🎯

- [x] T004 [P] [US1] Test `tests/unit/test_kit_lint.py`: mutated `compass.yaml` → `check_yaml_projection` not ok + detail names it; in-sync → ok (SC-001)
- [x] T005 [P] [US1] Test `tests/unit/test_kit_lint.py`: mutated `AGENTS.md` fenced body → `check_prose_projection` not ok + detail names the file; in-sync → ok (SC-001)
- [x] T006 [P] [US1] Test `tests/unit/test_kit_lint.py`: a broken/unparseable source → `lint` returns a named `source_parse` failing check + exit 1, NOT a raw traceback (FR-008)
- [x] T007 [US1] Add the `kit-lint` subcommand to `src/retail/cli.py` (thin parser → lazy `_run_kit_lint`; `--repo` default `.`); print per-check pass/fail + details; return `0 if report.ok else 1`

---

## Phase 4: User Story 2 — CI enforcement + dogfood (P2)

- [x] T008 [US2] Add a `retail kit-lint` step to `.github/workflows/ci.yml` AFTER the `retail semantic-check` step (FR-007), with a comment: standalone (parses yaml), projection drift → exit 1
- [x] T009 [US2] Dogfood test `tests/unit/test_kit_lint.py`: this repo's committed `.seshat/` + fenced regions pass `lint(REPO_ROOT).ok` (SC-004)
- [x] T010 [P] [US2] Test `tests/unit/test_kit_lint.py`: an un-bootstrapped tmp repo (no `.seshat/`) → `lint` returns `bootstrapped=False, ok=True` (exit 0), with a note (SC-003)

---

## Phase 5: Polish & Cross-Cutting

- [x] T011 [P] Rule-count guard: confirm `retail check` rule count unchanged at 47 (no new gate rule) after adding the subcommand (SC-002) — verify via the existing wiring test
- [x] T012 [P] Test `tests/unit/test_kit_lint.py`: a `LintReport` / `CheckResult` carries no numeric score field; a drift report names specifics, not "drift found" (SC-005, FR-008)
- [x] T013 [P] Test `tests/unit/test_kit_lint.py`: `kit_lint` reads no constitution file — a matched, bootstrapped tmp repo with NO `.specify/memory/constitution.md` still lints ok (SC-006, FR-010)
- [x] T014 [P] Run `ruff format --check src tests` + `ruff check src tests` + `pytest -m unit` + `retail check` + `retail kit-lint` in the worktree; fix any finding at its locator
- [x] T015 Verify boundary: `kit_lint` imports no DB/network module and no constitution path (FR-010), and WRITES NO FILE during a lint run (read-only, FR-004 — assert via source inspection / a tmp-repo run leaving files unchanged; mirrors the 070 no-DB guard)

---

## Dependencies & execution order

- Setup (T001) → Foundational (T002–T003) → user stories.
- US1 (T004–T007) depends on Foundational; T004–T006 are `[P]` (independent assertions).
- US2 (T008–T010) depends on the CLI handler (T007) + `lint` (T003).
- Polish (T011–T015) last.

## Parallel opportunities

- T004/T005/T006 (US1 tests), T010 (US2), T011/T012/T013 (polish) each `[P]`.

## Implementation strategy

**MVP = Phase 1 + 2 + 3 (US1)** — the projection-drift gate on the CLI. US2 wires CI +
dogfoods. Boundary discipline (standalone step, no gate rule, reads no constitution) is a
first-class acceptance gate, not polish (T011, T013, T015). The source-vs-constitution
check was CUT (see spec scope-cut note) and is deferred as a human-shaped governance
slice — NOT in this feature.
