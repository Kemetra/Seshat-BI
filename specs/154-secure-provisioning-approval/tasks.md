# Tasks: Secure integration provisioning approval

**Feature**: `specs/154-secure-provisioning-approval/` | **Spec**: ratified 2026-08-20 | **Plan**: [plan.md](./plan.md)

**Issue**: #671 | **Blocks**: spec 153 implementation

TDD order throughout: the failing test comes before the code that satisfies it.
A task is done only when its test was seen RED, then GREEN.

## Phase 0 -- Research (no code)

- [x] **T001** Confirm `contracts/provisioning-approvals.yaml` filename against
  `contracts/` conventions (`pbi-mcp-write-targets.yaml` is the top-level
  precedent) and prove no `.gitignore` rule shadows it. R1 already disqualified
  `.seshat/integrations/` (gitignored, `.gitignore:127`). Record in `research.md`.
- [x] **T002** Decide scope identity (R2): profile name, explicit component-id
  set, or both. Define "materially identical" (FR-012a) precisely in that
  representation. Record in `research.md` with the catalog evidence.
- [x] **T003** Determine how to reuse `approval_is_shape_valid` WITHOUT copying it
  (R3, FR-003). Its `stage` field is readiness-specific -- establish whether a
  provisioning record supplies a `stage`-equivalent or whether the reuse seam is
  `_owner_is_valid` + `_parse_iso_date` promoted to a public surface. **Forking
  the predicate is forbidden.** Record in `research.md`.
- [x] **T004** Confirm `gitstate.is_tracked_and_clean` / `committed_text`
  semantics and import path from `seshat.integrations` without a cycle (R4).
- [x] **T005** Decide revocation representation (R5) and how the gate reports
  `revoked` distinctly from `absent`.
- [x] **T006** Determine the minimum extension to approval-console (F027) /
  approval-evidence-pack (F035) for a project-scoped target (R6, FR-017). Confirm
  it is an extension, not a third write path.

## Phase 1 -- Design (no production code)

- [x] **T007** Write `data-model.md`: `ProvisioningApproval`, `ApprovedScope`,
  `ApprovalVerdict` (the eight categorical outcomes), each verdict carrying a next
  action.
- [x] **T008** Write `contracts/` refusal-reason enumeration so FR-014's
  machine-readable reasons are fixed and testable.
- [x] **T009** Write `quickstart.md`: a human records an approval; an operator
  provisions under it. No secret in any shown output.

## Phase 2 -- The gate (TDD; US1 = the security boundary)

- [x] **T010** [RED] `tests/unit/test_integrations_approval.py`: absent approval →
  verdict `absent`, not authorized. (FR-013)
- [x] **T011** [RED] Approval present in worktree but UNCOMMITTED → `uncommitted`,
  not authorized. A separate test from T010, not a variant. (FR-002)
- [x] **T012** [RED] Approval committed but on a dirty path → refused. (FR-002)
- [x] **T013** [RED] Malformed shapes, one test each: missing decider, missing
  authority class, unparseable date, bare role token as name → `invalid_shape`.
  Fixtures built from the real artifact shape, never a hand-written dict.
  (FR-003, FR-004)
- [x] **T014** [RED] Authority class other than `governance` → `wrong_authority`.
  (FR-004a)
- [x] **T015** [RED] Unparseable YAML → `unparseable`, and NOT distinguishable in
  any way that could read as a pass. (FR-013)
- [x] **T016** [GREEN] Implement `src/seshat/integrations/approval.py`: read-only
  gate, HEAD-only via `is_tracked_and_clean` + `committed_text`, reusing the
  canonical validator per T003. **The gate accepts NO caller-supplied boolean.**
  Its inputs are repo root + requested scope, both derived. (FR-001, FR-002,
  FR-003, FR-005)

## Phase 3 -- Scope binding (US2)

- [x] **T017** [RED] Approved scope covering the request → `authorized`. (FR-010)
- [x] **T018** [RED] Approved scope naming a different set → `scope_mismatch`,
  naming BOTH scopes in the reason. (FR-011)
- [x] **T019** [RED] Capability added after the approval → not authorized.
  (FR-012)
- [x] **T020** [RED] Superset approved scope vs subset request → authorized
  (settled in spec edge cases).
- [x] **T021** [GREEN] Implement scope comparison per T002.

## Phase 4 -- Lifetime (standing-until-scope-change)

- [x] **T022** [RED] Retry after partial failure, same scope → authorized, no new
  approval. (FR-012b)
- [x] **T023** [RED] Repeat run after success, same scope → authorized; the
  approval is standing, not single-use. (FR-012a)
- [x] **T024** [RED] Material scope change → refused pending new approval.
  (FR-012c)
- [x] **T025** [RED] Revoked / removed / replaced → ceases to authorize.
  (FR-012d)
- [x] **T026** [RED] Old approval, unchanged scope → age alone does NOT refuse.
  (FR-012e)
- [x] **T027** [GREEN] Implement lifetime + revocation per T005.

## Phase 5 -- CLI seam

- [x] **T028** [RED] `--apply --yes` with no committed approval → refused, no
  filesystem or network mutation. This is the #671 reproduction, now inverted into
  a regression test. (FR-001, FR-005)
- [x] **T029** [RED] TTY confirmation answered yes, no committed approval →
  refused. (FR-006)
- [x] **T030** [RED] stdin-supplied answer, no committed approval → refused.
  (FR-006)
- [x] **T031** [RED] Valid committed approval + non-interactive run → proceeds
  without prompting; the non-interactivity flag supplies no authority. (FR-008)
- [x] **T032** [GREEN] Rewrite `_approved()` in
  `src/seshat/cli/commands/integrations.py` to consult the gate. `--apply` remains
  intent (FR-007); `--yes` becomes prompt-suppression only and is **never passed
  to the gate** (FR-008). Preserve exit codes and JSON shape (FR-019).
- [x] **T033** **CORRECT** `tests/unit/test_integrations_setup.py:321` --
  currently asserts `refresh=True, apply=True, yes=True` → exit 0, which encodes
  the defect as expected behavior. Rewrite to expect refusal absent a committed
  approval, and add a case where a valid committed approval permits the run.
  **Assert the new secure form; do NOT relax the guard to keep the old test
  green.** Keep lines 243, 283 (existing refusals) and 300 (`--yes` alone does not
  apply) intact.

## Phase 6 -- Verification that the gate actually gates

- [x] **T033a** [RED] Prove the `governance` authority cannot be synthesized: no
  code path may construct, default, or infer an approval record at runtime. Assert
  that an agent-reachable input (flag, env var, stdin, config) cannot produce an
  `authorized` verdict without a committed file naming a human. (FR-004b)
- [x] **T033b** [RED] Confirm `--refresh` (network) and `--apply` (write) retain
  their current independent behavior: `--apply` without `--refresh` still refuses
  for missing exact pins, and the default run is still network-free and
  write-free. This feature ADDS authorization; it relaxes no existing
  precondition. (FR-009)
- [x] **T034** Prove the fail-open is closed: monkeypatch ONLY the gate to return
  `authorized` and assert the pre-fix verdict returns. Proves the gate is what
  refuses, not incidental surrounding code.
- [x] **T035** Non-vacuity sweep: for every absence-assertion added, remove the
  guard and confirm the test FAILS. A test that passes with the guard gone proves
  nothing. **Commit before poking the guard** so the restore cannot discard work.
- [x] **T036** Platform-vacuity check: no assertion may depend on a hardcoded
  platform string (e.g. `.exe`) -- CI runs Linux and such an assertion goes
  vacuous there.
- [x] **T037** Secret-shape sweep: assert no refusal, evidence, or JSON output
  contains a credential, connection string, or token. (FR-015)
- [x] **T038** Verification-vs-authorization: valid approval + failing provider
  verification → capability NOT reported ready, run NOT reported successful.
  (FR-016)

## Phase 7 -- Reuse and non-duplication

- [x] **T039** Extend approval-console / approval-evidence-pack per T006 for the
  project-scoped target. No third write path. (FR-017)
- [x] **T040** [RED] `tests/contract/test_provisioning_approval_contract.py`:
  assert exactly ONE approval-shape validator exists in the source tree, and that
  the provisioning gate uses it rather than a copy. (FR-003)
- [x] **T041** Confirm catalog, resolvers, compatibility policy, installer,
  lockfile, and discovery are unchanged by diff. (FR-018)

## Phase 8 -- Gates

- [x] **T042** `ruff format --check src/ tests/` and `ruff check src/ tests/`
  (format-check is the CI gate, not just `ruff check`).
- [x] **T043** `pytest -m unit` full suite green. Note CI's unit job runs WITHOUT
  app extras -- do not rely on an extras-only import.
- [x] **T044** `seshat check` exit 0 and `seshat semantic-check` as applicable.
- [x] **T045** CodeScene: measure with `cs review` on every changed file (it is
  tokenless). Refactor any flagged function to health 10.0 rather than suppress.
- [x] **T046** Confirm the diff contains no `plan.md`/`tasks.md`-only drift and no
  unrelated file.
- [x] **T047** Verify **FR-020 / SC-011** are satisfied: spec 144's artifact
  records the FR-010 amendment. Authored in PR #675 (`docs: record spec 154's
  amendment of spec 144 FR-010`) -- confirm it MERGED to `main` and that the
  annotation names spec 154 and issue #671, marks the approval-prompt clause
  narrowed, and lists the other five clauses as unamended. If #675 is unmerged at
  implementation time, this task BLOCKS ratification-completeness, not the code.

## Out of scope for these tasks

- Spec 153's derivation, strength, or presentation work (blocked until this lands;
  its FR-018 boundary is permanent regardless).
- Any change to the catalog, installer, resolver, compatibility, lockfile, or
  discovery behavior beyond what the trust boundary requires.
- A second capability registry, approval vocabulary, shape validator, or
  approval-writing path.
- Time-based approval expiry (explicitly excluded by FR-012e).
