# Tasks: Public capability graph integrity

**Spec**: `specs/143-official-first-graph/spec.md`

**Plan**: `specs/143-official-first-graph/plan.md`

**Status**: Ratified -- Ahmed Shaaban, 2026-08-07; Phase 1 implementation authorized

## Conventions

- Every implementation task remains unchecked until the specification is
  explicitly ratified by a named human.
- Tests are written red first where they exercise a new detector.
- The current phase may touch only the paths named below.
- No bundle regeneration, dependency change, commit, push, or PR is a task.

## Phase 1 -- Baseline and fail-closed tests

- [x] T001 Record the post-ratification baseline commands and results in `specs/143-official-first-graph/evidence/baseline.md`: focused capability/public tests, bundle drift check, `seshat check`, and clean generated-root diff.
- [x] T002 [US1] Add failing constructed-input tests for missing ownership, duplicate explicit ownership, ambiguous same-name skill fallback, explicit-over-fallback precedence, and stale `references.public_skill` links in `tests/unit/test_capability_inventory.py`.
- [x] T003 [P] [US2] Add failing constructed-input tests for missing, escaping, nonexistent, untracked, non-file, and generated canonical sources in `tests/unit/test_capability_inventory.py`.
- [x] T004 [P] [US3] Record the pre-change generated bundle tree digests or equivalent zero-diff baseline in `specs/143-official-first-graph/evidence/baseline.md`.

## Phase 2 -- Ownership graph detector

- [x] T005 [US1] Add an independent shipped-public-skill feeder and deterministic ownership-link detector to `tests/unit/_capability_oracle.py`, using explicit-public-owner then unique-same-name-skill precedence without importing production capability readers.
- [x] T006 [US2] Add repository-relative, containment, regular-file, Git-tracked, and generated-root canonical-source checks to `tests/unit/_capability_oracle.py` for every declared source and require a source on public-linked capabilities.
- [x] T007 [US1] Wire the new detector into `oracle_all_clear` in `tests/unit/_capability_oracle.py` and prove the constructed invalid cases fail while a valid case passes in `tests/unit/test_capability_inventory.py`.

## Phase 3 -- Repair current manifest truth

- [x] T008 [US1] Add `seshat-bi-public-router` and `powerbi-workflows-public-router` capability records with current `seshat-orchestrator` ownership, authored bundle-template canonical sources, and exact `references.public_skill` links in `docs/capabilities/capabilities.yaml`.
- [x] T009 [US2] Correct `pbi-mcp-doctor` canonical source to `distribution/bundle-templates/shared/skills/pbi-mcp-doctor/SKILL.md` in `docs/capabilities/capabilities.yaml`.
- [x] T010 [US1] Document the public-skill ownership and canonical-source invariant, including the current-versus-future `powerbi-workflows` boundary, in `docs/capabilities/README.md`.
- [x] T010A [US1] Close the additional full-oracle findings discovered after T010: add authored canonical sources to the nine fallback-owned public skills and explicitly link the CLI-shaped `retail-validate` owner. This is manifest metadata only and is required by the ratified all-public-skills exit gate.

## Phase 4 -- Exit gates and scope review

- [x] T011 [US1] Run `tests/unit/test_capability_inventory.py` and record the exact result in `specs/143-official-first-graph/evidence/validation.md`.
- [x] T012 [P] [US3] Run public-surface, ship-classification, generated-bundle, Claude plugin, and Codex plugin focused contracts and record exact results in `specs/143-official-first-graph/evidence/validation.md`.
- [x] T013 [US3] Run `python scripts/export_agent_bundles.py --check`, prove generated roots have no diff, and record exact results in `specs/143-official-first-graph/evidence/validation.md`.
- [x] T014 Run `python -m seshat.cli check` and `git diff --check`; classify any finding as new, pre-existing, environmental, or blocked in `specs/143-official-first-graph/evidence/validation.md`.
- [x] T015 Review `git diff --stat`, `git diff --name-only`, and the complete diff against the Phase 1 allowlist; record scope evidence in `specs/143-official-first-graph/evidence/scope-review.md`.
- [x] T016 Update `specs/143-official-first-graph/ratify-ledger.md` with implementation evidence, leave the spec `ratified` until its artifact exists on `main`, clear `.specify/feature.json` and both Spec Kit fences only after every prior task is complete, and rerun the active-fence contract.

## Dependencies

```text
Ratification
  -> T001-T004
  -> T005-T007
  -> T008-T010
  -> T011-T015
  -> T016
```

User Story 1 establishes exact ownership and is the MVP. User Story 2 shares the
same detector but is independently mutation-tested. User Story 3 proves the
metadata-only change did not alter distribution behavior.

## Explicitly not tasks

- Power BI/dbt/Dagster routing or official skill activation.
- Integration installer convergence.
- Evidence-envelope design.
- Spec Kit re-vendoring.
- Public skill edits, generated bundle regeneration, deletion, commit, push, PR,
  merge, or publication.
