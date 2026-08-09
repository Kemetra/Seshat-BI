# Tasks: Self-Protecting Official-First Architecture

**Status**: ratified -- Ahmed Shaaban, 2026-08-10. Implementation is authorized
only for the tasks below.

## Phase 1 - Baseline

- [x] T001 Confirm the active spec is human-ratified by a named human and the
      implementation worktree is on `152-self-protecting-architecture`, never
      `main`.
- [x] T002 Re-run the clean focused baseline and record command, exit code,
      result, and classification.
- [x] T003 Re-confirm the real manifest has no upstream-backed Seshat-owned
      entry with a blank delta and that the five `speckit-git-*` paths are still
      absent from both provenance manifests. If repository truth changed, stop
      and amend or supersede this spec.

## Phase 2 - Protect the Seshat delta (TDD)

- [x] T004 Add failing constructed-input tests for an upstream-backed
      `seshat-orchestrator` with absent, empty, and whitespace-only deltas.
- [x] T005 Add parameterized coverage proving every `seshat-*` owner token is
      subject to FR-001 when upstream-backed, without introducing a second
      manually maintained owner-token set.
- [x] T006 Add negative coverage proving official-upstream, vendored-upstream,
      internal Seshat capabilities without an upstream project, and the
      existing adapter-only rule retain their intended behavior.
- [x] T007 Extend the existing ownership detector with the smallest change that
      makes T004-T006 pass. Do not change manifest data that is already valid.

## Phase 3 - Close KF-2 provenance (TDD)

- [x] T008 Add the failing contract that derives the fourteen expected skill
      paths from `speckit-workflow-skills.references.skill` and reconciles them
      exactly with `.specify/integrations/claude.manifest.json`.
- [x] T009 Add failure tests for missing/unexpected entries, duplicate or blank
      capability references, unsafe/untracked/non-file/symlink paths, malformed
      hashes, content drift, and disagreement among the three version claims.
- [x] T010 Add LF-normalization tests proving CRLF-only input hashes identically
      while a semantic byte change fails.
- [x] T011 Compute LF-normalized hashes for the five `speckit-git-*` files and
      add them to the existing Claude manifest. Do not edit skill bodies or add
      another manifest.
- [x] T012 Prove detection in a temporary fixture: clean -> pass; remove one
      manifest entry -> fail; restore; change one skill byte -> fail; restore;
      clean -> pass.

## Phase 4 - Truthful closeout

- [x] T013 Update only the `speckit-workflow-skills` update policy so it names
      fourteen-of-fourteen coverage and the enforcing contract.
- [x] T014 Append a dated Phase 11 note to `ownership-audit.md` classifying KF-2
      `CLOSE-NOW -> ALREADY-CLOSED` only after T012 passes. Preserve the
      historical Phase 9 record.
- [x] T015 Run the focused official-delegation, truth-separation, readiness,
      approval, spec-status, bundle, and static governance validations from the
      plan. Classify every result.
- [x] T016 Review the diff file-by-file and verify the forbidden-scope list is
      absent. Confirm `.specify/feature.json` was not silently changed.

No task may be checked before its deliverable and test evidence exist. Do not
implement unratified tasks, push, open a PR, merge, publish, or continue into the
Final Architecture Audit in the same state transition.
