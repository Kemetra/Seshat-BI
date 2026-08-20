# Implementation Plan: Secure integration provisioning approval

**Branch**: `154-secure-provisioning-approval` | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/154-secure-provisioning-approval/spec.md` (ratified -- Ahmed Shaaban, 2026-08-20)

## Summary

Replace the caller-supplied provisioning approval in
`src/seshat/cli/commands/integrations.py` with a committed, named-human approval
read at HEAD, scope-bound to the capability set being provisioned. The single
behavioral seam is `_approved()`: today it returns True for
`Namespace(apply=True, yes=True)`; after this change authority comes only from a
committed record validated by the existing canonical shape validator.

Nothing else in the provisioning path moves. The catalog, resolvers,
compatibility policy, installer, lockfile, and discovery surfaces are untouched.

## Technical Context

**Language/Version**: Python 3.13 (repo floor 3.11)

**Primary Dependencies**: none added. Reuses `seshat.rules.readiness_status`
(`approval_is_shape_valid`, `_owner_is_valid`), `seshat.gitstate`
(`is_tracked_and_clean`, `committed_text`), and `yaml.safe_load` (already a
dependency).

**Storage**: one new committed YAML artifact, per project, at a path decided in
Phase 0 research. NOT `mappings/<table>/readiness-status.yaml` (spec FR-001a).

**Testing**: pytest. Unit (`tests/unit/`) for the gate and the CLI seam; contract
(`tests/contract/`) for the approval-shape reuse invariant.

**Target Platform**: cross-platform CLI (Windows dev, Linux CI). No platform
branch may make an assertion vacuous -- CI runs Linux.

**Project Type**: CLI within an existing library.

**Performance Goals**: N/A. The gate reads one small committed file.

**Constraints**: The default run stays network-free and write-free. The gate
itself performs no network access and no writes.

**Scale/Scope**: ~1 new module (~120 lines), 1 CLI function rewritten, ~10 new
tests, 1 existing test corrected. No new CLI verb, no new flag.

## Constitution Check

*GATE: passes.*

| Principle | Assessment |
|---|---|
| I. Agent-First, Gate-Enforced | REINFORCED. Adds a gate the agent cannot satisfy by itself; the exit code remains the authority. |
| II. Depend, Never Fork | Unaffected. No upstream provider is forked, vendored, or reimplemented; this changes only who may authorize installing them. |
| V. Agent Stops at Judgment Calls | **This feature is a direct implementation of Principle V.** Provisioning becomes a named-human decision the agent cannot self-grant. |
| VIII. Static-First, Live Deferred | REINFORCED. The gate is pure static committed-text reading -- no DB, no network. It gates the live action more tightly than before. |
| IX. Secrets and Reproducibility | Honored: FR-015 forbids any secret in refusal, evidence, or JSON output. |

No principle is weakened. No amendment to the constitution is required. The one
ratified-requirement amendment (spec 144 FR-010) is already recorded in spec
144's artifact.

## Project Structure

### Documentation (this feature)

```text
specs/154-secure-provisioning-approval/
├── spec.md              # ratified
├── plan.md              # this file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── tasks.md             # /speckit-tasks output
└── checklists/
    └── requirements.md
```

### Source Code

```text
src/seshat/integrations/
├── approval.py          # NEW -- the committed-approval gate (read-only)
└── ...                  # catalog/installer/resolvers/lockfile: UNTOUCHED

src/seshat/cli/commands/
└── integrations.py      # _approved() rewritten to consult the gate

tests/unit/
├── test_integrations_approval.py   # NEW -- gate behavior
└── test_integrations_setup.py      # CORRECTED (see Known Test Debt)

tests/contract/
└── test_provisioning_approval_contract.py  # NEW -- shape-reuse invariant
```

## Phase 0 -- Research (open questions to settle before design)

Each item below is a repository question with a decidable answer, not an owner
judgment call. The two owner decisions were ruled at ratification.

1. **R1 -- Approval artifact path. SETTLED during planning: use `contracts/`.**
   Spec FR-001 requires a dedicated per-project committed artifact. Evidence:
   - `.seshat/integrations/` is **gitignored** (`.gitignore:127`), as are
     `.seshat/watch/`, `.seshat/dagster/`, and `/.seshat/dbt/`. An approval placed
     under the integrations path could never be tracked, so
     `is_tracked_and_clean` could never pass and the gate would refuse forever.
     **`.seshat/integrations/` is DISQUALIFIED** -- it is machine-local installer
     state by design, the opposite of committed governance state.
   - `contracts/` is tracked on `origin/main` and is already the repository's
     governed committed-contract directory (it holds
     `contracts/knowledge/approval-authority.yaml`, referenced by the readiness
     spine).

   **Decision**: `contracts/provisioning-approvals.yaml`. Remaining sub-question
   for implementation: confirm the exact filename against any existing
   `contracts/` naming convention, and confirm no `.gitignore` rule shadows it.

2. **R2 -- Scope identity.** FR-010/FR-011 need a request scope comparable to an
   approved scope. The catalog gives stable component ids and profile names. Decide
   whether scope is expressed as a profile name, an explicit component-id set, or
   both, and define "materially identical" (FR-012a) precisely in terms of that
   representation.

3. **R3 -- Reuse of `approval_is_shape_valid`.** It is currently module-private in
   effect and keyed to readiness stage semantics (`stage` field). Determine whether
   it can be imported as-is, whether its `stage` requirement fits a provisioning
   record, and how to reuse the validator WITHOUT copying it (FR-003 forbids a
   second validator). If the `stage` field does not fit, the fix is to reuse
   `_owner_is_valid` + `_parse_iso_date` through a public seam, not to fork the
   predicate.

4. **R4 -- `gitstate` helper semantics.** Confirm `is_tracked_and_clean` and
   `committed_text` behave as the PBI MCP gate assumes (HEAD-only, dirty-path
   refusal) and that they are importable from the integrations package without a
   cycle.

5. **R5 -- Revocation representation.** FR-012d requires revoke/remove/replace to
   end authority. Decide whether revocation is absence (record deleted), an
   explicit `revoked: true`, or replacement by a newer record -- and how the gate
   distinguishes "revoked" from "never existed" for reporting purposes.

6. **R6 -- Extending the approval-authoring surfaces.** FR-017 forbids a third
   write path. Determine the minimum change to approval-console (F027) /
   approval-evidence-pack (F035) so they can target a project-scoped artifact,
   and confirm that is an extension rather than a new path.

## Phase 1 -- Design

**data-model.md** will define:
- `ProvisioningApproval` -- decider, authority class (`governance`), ISO date,
  approved scope, optional revocation marker.
- `ApprovedScope` -- the R2 representation plus the "materially identical"
  comparison.
- `ApprovalVerdict` -- a categorical outcome: `authorized`, `absent`,
  `invalid_shape`, `wrong_authority`, `scope_mismatch`, `uncommitted`,
  `unparseable`, `revoked`. Each carries a next action (FR-014).

**contracts/** will hold the refusal-reason vocabulary as a fixed enumeration, so
FR-014's machine-readable reasons are testable and cannot drift.

**quickstart.md** will show a human recording an approval and an operator running
provisioning under it -- with no secret in any output.

### Design invariants (each maps to a spec FR)

- The gate is **read-only**: no writes, no network. (FR-013)
- The gate reads **HEAD only** via `committed_text` after `is_tracked_and_clean`.
  A dirty or untracked path is a refusal, not a fallback. (FR-002)
- The gate takes **no boolean from the caller** that could stand in for approval.
  Its inputs are the repo root and the requested scope -- both derived, never
  asserted. (FR-005, and the "a precondition the caller supplies is not a gate"
  failure mode.)
- `--yes` is passed to the gate **never**; it survives only as a prompt
  suppressor. (FR-008)
- Every refusal is categorical, with a next action, and secret-free.
  (FR-014, FR-015)

## Known Test Debt (must be corrected, not preserved)

`tests/unit/test_integrations_setup.py:321` asserts:

```python
assert integrations_main(_args(root, refresh=True, apply=True, yes=True)) == 0
```

This encodes the defect as expected behavior. Keeping it green would silently
defeat the fix. It MUST be rewritten to expect a refusal absent a committed
approval, plus a new case where a valid committed approval permits the run.
Lines 243 and 283 already assert refusals and are expected to survive; line 300
(`--yes` alone does not apply, guarded by `pytest.fail("--yes enabled apply")`)
also survives and should be kept.

**This is the "security hardening breaks old-behavior tests" case: assert the new
secure form, never revert the guard to satisfy the old test.**

## Verification Strategy

The gate must be proven to actually gate -- a passing suite is not evidence.

1. **Prove the fail-open is closed**: monkeypatch ONLY the gate to return
   `authorized`, and assert the pre-fix verdict returns. This proves the gate,
   not the surrounding code, is what refuses.
2. **Prove the HEAD-only read**: write a valid approval to the worktree WITHOUT
   committing, and assert refusal. Then commit it and assert authorization. The
   uncommitted case must be a distinct test, not a variant.
3. **Non-vacuity**: every absence-assertion test must be shown to fail if the
   guard is removed. No hardcoded platform string (e.g. `.exe`) may appear in an
   assertion, or it goes vacuous on Linux CI.
4. **Fixture honesty**: build approval fixtures from the real artifact shape, not
   from a hand-written dict that only the test believes in.

## Complexity Tracking

One new module, one rewritten function, no new dependency, no new CLI surface, no
new approval vocabulary. The chief complexity risk is scope comparison (R2); if it
threatens to grow, prefer the narrowest representation that satisfies FR-011 and
FR-012c and defer richer matching.
