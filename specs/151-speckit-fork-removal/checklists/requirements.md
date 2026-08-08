# Requirements checklist: spec 151

Ratification aid. Every box must be answerable from the spec artifacts, not from
memory. Unchecked boxes are open questions for the owner, not defects.

## Is the problem real?

- [x] The fork still exists on `main` -- `git diff 1eb0c98 HEAD` = +11/-1
- [x] The upstream baseline is recoverable -- committed at `1eb0c98`
- [x] The modification is deliberate, not accidental -- `f35612f`, backed by ADR-0019
- [x] The ADR behind it is owner-ratified -- Ahmed Shaaban, 2026-07-30
- [x] The dependency graph was measured, not assumed -- one content reader, a test

## Is the scope honest?

- [x] The corpus census is published in the spec -- 139 specs, 110 outside vocabulary
- [x] The feature does not silently become corpus-wide enforcement -- FR-023
- [x] The capability is still built and tested -- FR-024
- [x] Deferred items are named -- Out of Scope section
- [ ] **Owner accepts that 110 specs stay non-conforming after this feature**
- [ ] **Owner accepts corpus migration as a separate, later decision**

## Does the fork actually go away?

- [x] The template returns to upstream content -- FR-013
- [x] No copy of upstream template content lives anywhere in Seshat -- FR-016/FR-017
- [x] No patch file is maintained -- FR-016
- [x] A normal upgrade needs no manual reapplication -- Success Criterion 8
- [x] The diff is checked for relocation -- T015

## Does the governance survive?

- [x] Closed vocabulary preserved -- FR-005
- [x] Invalid values rejected -- FR-006
- [x] `implemented` still needs artifact + SC1 claim -- FR-007
- [x] `ratified` still needs a named human and date -- FR-008
- [x] Agents still cannot self-ratify -- FR-008, FR-020
- [x] Status-history convention preserved -- FR-009
- [x] Fail-closed on absent/unparseable/unreadable -- FR-018, FR-019

## Are the known traps handled?

- [x] Scaffold seeds an invalid status after restoration -- FR-025 + T008-scaffold
- [x] Third grammar in `idea-to-spec.js` -- FR-026 + T008d
- [x] History-line regression from naive widening -- FR-012a + T008a-history
- [x] Vacuous proof gate -- T008 rewritten with three concrete sub-gates
- [x] CRLF false positives -- FR-021, measured 5 of 6
- [x] Checker validating itself from its own target -- FR-004

## Is the order safe?

- [x] The authority exists before the template is restored -- T006 before T009
- [x] Consumers are migrated before restoration -- T007/T008 before T009
- [x] Grammars are reconciled before restoration -- Phase 4 before Phase 5
- [x] Loss is proved absent after restoration -- T010
- [x] No step makes invalid status temporarily acceptable -- plan migration table

## Internal consistency

- [x] FR-006 carries no exception list -- the seeded `Draft` is normalized at
      scaffold time, not excused in the vocabulary rule
- [x] FR-025's resolution does not contradict FR-006
- [x] The normalization step is not the fork relocated -- it acts on scaffolded
      OUTPUT, contains no upstream content, and needs no post-upgrade re-run

## Decisions recorded (agent recommendations, owner may overrule)

- [x] **FR-025**: normalize post-scaffold, rather than accept `Draft` as a
      synonym. Reason: keeps FR-006 a single testable rule.
- [x] **H3**: widen additively, rather than make the ADR form the only form.
      Reason: cannot invalidate an already-ratified spec; avoids pulling corpus
      migration into this feature.

## Open for the owner

- [ ] **Ratification.** The one seam the agent cannot clear. `implement.js`
      verifies by git blame that a human authored the Ratified line.
- [ ] **Overrule either recommendation above**, if preferred.
- [ ] **Accept that 110 specs stay non-conforming** after this feature, with
      corpus migration as a separate later decision.

Note: "do it now" and "defer" produce the same immediate state -- the package
sits awaiting ratification either way -- so that is not a separate question.
