# Cross-Artifact Analysis: Secure integration provisioning approval

**Feature**: `specs/154-secure-provisioning-approval/` | **Date**: 2026-08-20

**Scope**: non-destructive consistency check across `spec.md` (ratified),
`plan.md`, and `tasks.md`. No production code was read for correctness here and
none was written.

## Coverage

Measured mechanically, not by inspection:

| Metric | Result |
|---|---|
| Spec functional requirements | 28 |
| FRs referenced by plan + tasks | **28 / 28** |
| Uncovered FRs | **none** |
| Spec success criteria | 15 |
| Tasks | 47 |
| Duplicate task ids | none |
| Task checkboxes | 49 unchecked, 0 checked |

## Gaps found and closed during this pass

The first coverage run reported three uncovered FRs. All three were real
omissions in `tasks.md`, not measurement artifacts:

1. **FR-004b** (the `governance` authority must never be inferred, synthesized, or
   self-granted) had no task. Added **T033a**: assert no agent-reachable input --
   flag, env var, stdin, config -- can produce an `authorized` verdict without a
   committed file naming a human. This is the FR that most directly encodes the
   #671 defect class, so its absence mattered.
2. **FR-009** (the network and write flags retain their current independent
   behavior) had no task. Added **T033b**: `--apply` without `--refresh` still
   refuses for missing exact pins, and the default run stays network-free and
   write-free. Without this, a reviewer could not tell whether the change
   *tightened* or merely *relocated* the existing preconditions.
3. **FR-020** (this feature must amend spec 144 FR-010 in spec 144's artifact) had
   no task. Added **T047**, which verifies rather than re-does the work: the
   annotation was authored in PR #675 and T047 confirms it merged and says the
   right thing.

## Consistency findings

- **No contradiction** between spec, plan, and tasks on the two ruled owner
  decisions. Both appear consistently: per-project `contracts/` artifact with the
  `governance` class, and standing-until-scope-change lifetime with no time-based
  expiry.
- **Plan settles one research question early.** R1 (approval artifact path) was
  decided during planning on hard evidence rather than deferred:
  `.seshat/integrations/` is gitignored (`.gitignore:127`), so an approval there
  could never satisfy `is_tracked_and_clean` and the gate would refuse forever.
  `contracts/` is tracked and already holds governed contract state
  (`contracts/knowledge/approval-authority.yaml`,
  `contracts/pbi-mcp-write-targets.yaml`). Decision:
  `contracts/provisioning-approvals.yaml`.
- **Five research questions remain open** (R2-R6) and are correctly sequenced as
  Phase 0 tasks T002-T006. Each is a repository question with a decidable answer,
  not an owner judgment call. Neither ruled owner decision is reopened anywhere.
- **Known test debt is carried forward explicitly.** Both `plan.md` and `tasks.md`
  (T033) name `tests/unit/test_integrations_setup.py:321`, which currently asserts
  `refresh=True, apply=True, yes=True` returns exit 0 -- the defect as expected
  behavior. Both artifacts state the rule: assert the new secure form, never relax
  the guard to keep the old test green.
- **Verification is treated as a phase, not an afterthought.** Phase 6 (T034-T038)
  requires proving the gate is what refuses (monkeypatch only the gate and assert
  the pre-fix verdict returns), a non-vacuity sweep on every absence assertion, a
  platform-vacuity check (no hardcoded `.exe`, since CI is Linux), a secret-shape
  sweep, and an authorization-is-not-verification test.

## Constitution alignment

`plan.md`'s Constitution Check passes with no principle weakened. Principle V
(agent stops at judgment calls) is not merely respected but *implemented* by this
feature. Principle VIII is reinforced: the gate is pure static committed-text
reading, and it constrains the live action more tightly than before.

## Residual risks

1. **Scope comparison (R2) is the complexity centre.** If "materially identical"
   grows elaborate, FR-011 and FR-012c become hard to test. `plan.md`'s Complexity
   Tracking already directs the narrowest sufficient representation, deferring
   richer matching.
2. **`approval_is_shape_valid` reuse (R3) is the main design risk.** Its `stage`
   field is readiness-specific. If a provisioning record cannot supply a
   `stage`-equivalent, the correct move is promoting `_owner_is_valid` +
   `_parse_iso_date` to a public seam -- **not** forking the predicate, which
   FR-003 forbids and T040 tests against.
3. **PR #675 and #676 were unmerged when this analysis ran.** `origin/main` still
   showed `Status: Draft` for this spec. Implementation must not begin until the
   ratification is on `main`; T047 covers the amendment half.

## Verdict

Artifacts are internally consistent, fully cover the ratified requirements, and
are ready for implementation **once the ratification (PR #676) is merged to
`main`**. No unresolved owner decision remains. No code was written.
