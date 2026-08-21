# Implementation Plan: Studio Operations and Client Review

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development`
> (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Feature**: `specs/141-studio-operations-client-review/` | **Spec**: [spec.md](./spec.md) |
**Research**: [research.md](./research.md) | **Data model**:
[data-model.md](./data-model.md) | **Contract**:
[contracts/export-boundary.md](./contracts/export-boundary.md)

**Goal:** Give technicians a diagnostic view that explains why work cannot proceed, and
clients a review surface that shows approved outcomes without leaking the machinery or
softening a pending fact.

**Architecture:** Four ordered phases. Phase A builds the disclosure primitives -- the
component-state mapping and the allowlist export scrubber -- with no UI. Phase B adds
Operations (US1). Phase C adds run history (US2). Phase D adds client review, responses,
and the support bundle (US3/US4/US5). Every phase is presentation over existing truth: no
new probe, no new event schema, no second decision path.

**Tech Stack:** Python 3.13, FastAPI (existing Studio app), `pyyaml` (the repo's only
YAML dependency), pytest. Frontend follows Foundation's existing Studio asset pipeline.

**Spec status:** `draft`. Phases 0 and 1 (research, design) are complete.
**Implementation MUST NOT begin** until a named human ratifies this package and the sole
active Spec Kit fence points at this plan (FR-141-020). Spec 139 is accepted (2026-08-16)
and spec 140 is accepted (2026-08-21), so the first of the three conditions is met and
the other two are not.

## Global Constraints

Copied from the spec; every task's requirements include these.

- **No aggregate score** of any kind -- health, maturity, confidence, readiness
  (FR-141-002). The data model has no field for one.
- **`deferred` is not failure** (FR-141-003); an unrecognized state fails closed to
  `failed`, never `healthy` (FR-141-006).
- **Recommend, never repair**: a diagnostic may name a recovery action, never execute one
  outside the existing technical-approval and readiness policy (FR-141-005, FR-141-018).
- **Allowlist, never denylist** for every export (FR-141-012).
- **Two redaction layers** on the assembled artifact: `scrub_payload` plus the
  secret-shaped scrub (FR-141-008).
- **`pending commit` renders as pending** (FR-141-021); durable claims cite committed
  state or are `ephemeral` (FR-141-010).
- **Acknowledgement is not approval** (FR-141-011); spec 140 owns the only
  decision-recording route.
- Localhost, single-workspace, authenticated under Foundation's boundary (FR-141-017).
- WCAG 2.2 AA (FR-141-015); no remote assets in any export.
- `pyyaml` only. Do not add `ruamel.yaml` -- the repo has a dependency-freshness gate.
- Test files touching the web stack need `pytest.importorskip("fastapi")`; the CI `unit`
  job installs no app extras. A lazy import in a fixture module must not be hoisted --
  `ruff check --fix` has done that once and re-broken CI.

## Summary

Spec 140 shipped the governed workbench: proposals, the named-human decision route,
scoped apply, and `review_scope`. This feature adds the two surfaces 140 deliberately
excluded -- Operations for technicians, Client Review for clients -- plus the support
bundle.

The security character is different from 140's. 140 guarded a **write** (writing a
decision is not granting one). 141 guards a **disclosure**: each surface shows internal
truth to someone with less context. Softening, leaking, and acting are three distinct
failure modes needing three distinct guards -- see the contract.

## Technical Context

| Concern | Existing | This feature |
| --- | --- | --- |
| Diagnostics | `doctor.py` -> `list[Finding]` (`rule_id`, `severity`, `message`, `locator`) | **maps** findings to a NEW six-state component vocabulary |
| Run events | `studio/events.py` (`StudioEvent`, `ThreadStore`) | reads; no new event schema |
| Receipts | `DecisionWriteReceipt`, `ApplyReceipt` | reads |
| Committed reads | `decision_write.decisions_at_head` | reads |
| Scoped filtering | `studio/review_scope.py` | extends for client scope |
| Redaction | `studio/redaction.py` over `redaction_core.py` | consumes both layers |
| Export precedent | `evidence_pack.py` | follows for the bundle |

**The correction that shapes Phase A**: `doctor.py` has no component-state vocabulary.
`Finding.severity` is only `error`/`warning`/`info`. The six states are introduced here,
so the mapping is new code and needs its own tests -- FR-141-004 forbids a second *probe
set*, not a mapping layer.

## The seam

`studio/operations.py` holds the mapping and the run-history assembly. `studio/exports.py`
holds the allowlist scrubber and bundle assembly. They are separate because they fail
differently: a mapping bug shows a wrong state, an export bug leaks a secret. Keeping the
export surface in one small file means the whole disclosure path is auditable in one read.

Route registration follows `workbench_routes.py`: module-level handlers taking a frozen
`Deps`, so the registrar stays branch-free. That pattern exists because nesting handlers
inside a registrar made its cyclomatic complexity the sum of theirs.

## Constitution Check

| Principle | Compliance |
| --- | --- |
| I -- `check` is the gate | Operations displays `doctor` findings as advisory; never as gate authority |
| V -- never self-grant approval | No recovery action executes without the existing approval; acknowledgement cannot hold a ruling |
| No fabricated confidence | No aggregate score; the model cannot express one |
| Live boundary honesty | `deferred` is a first-class state, distinct from failure |
| Mapping before Silver | Not applicable; this feature writes no warehouse artifact |

## Project Structure

```
src/seshat/studio/
├── operations.py          <- NEW: Finding -> ComponentState mapping, run history
├── exports.py             <- NEW: allowlist scrubber, client artifact, support bundle
├── operations_routes.py   <- NEW: route registrar (module-level handlers + Deps)
└── app.py                 <- MODIFY: register the new router
tests/unit/
├── test_studio_operations.py
├── test_studio_exports.py
└── test_studio_operations_routes.py
```

## Phase 0 -- Research (DONE, see research.md)

R1-R8 established: the prerequisite is genuinely met; `doctor.py` supplies findings but no
component vocabulary; normalized events exist; 140's three-state model must reach the
render layer; two redaction layers are required; allowlist over denylist; `review_scope`
already refuses an absent scope; no aggregate score anywhere.

## Phase 1 -- Design (DONE, see data-model.md and contracts/)

Eight obligations, each with a named proof. The two load-bearing ones (O1 pending stays
pending, O7 durable claims cite committed state) are both "the honest label survives the
render", and both are vacuous without their inverse.

## Implementation phases (BLOCKED on ratification + fence)

### Phase A -- Disclosure primitives, no UI

Tasks A1-A4. The `Finding` -> `ComponentState` mapping and the allowlist export scrubber.
Independently testable with no HTTP surface. **Nothing in later phases may start until
Phase A is green**, because every later phase discloses through it.

### Phase B -- Operations view (US1)

Tasks B1-B3. Component diagnostics with evidence and recovery actions; recovery refused
without approval.

### Phase C -- Run history (US2)

Tasks C1-C3. Ephemeral versus durable, citation required for durable, `pending commit`
carried through.

### Phase D -- Client review, responses, support bundle (US3/US4/US5)

Tasks D1-D5. Draft selection, narrative bounded to selected facts, export artifact,
acknowledgement distinct from approval, atomic bundle with aborting scan.

Task-level steps with test code are in [tasks.md](./tasks.md).

## Verification Strategy

1. **Every negative assertion needs its positive twin.** The recurring defect in this
   repo. "Pending renders as pending" passes on a surface that can only ever render
   pending; assert the committed case beside it.
2. **No absence-assertions on field names.** `"score" not in payload` goes green when the
   value ships as `health_index`. Search for a numeric roll-up across the payload.
3. **Guards proven by removal.** Each contract obligation's test must fail when the guard
   is monkeypatched away or deleted.
4. **Exports scanned as artifacts, not as intentions.** Build the real archive from a
   workspace containing a DSN, an absolute path and a bare GUID, then scan the produced
   bytes.
5. **Cross-platform.** Derive paths with `pathlib`; the CI `unit` job is `ubuntu-latest`
   only, so a POSIX-locked fixture stays green in CI and fails only on Windows (#691).
6. **Gates.** `ruff format --check`, `ruff check`, `pytest -m unit`, `seshat check`,
   `seshat kit-lint` before every commit. After any `ruff check --fix` on a file with a
   deliberate lazy import, `grep -c '^from fastapi'` must still be 0.

## Known Risks

| Risk | Mitigation |
| --- | --- |
| The six-state mapping drifts from what `doctor` actually reports | `ComponentDiagnostic.source_rule_ids` makes every state traceable to the finding it came from; a state no rule supports fails a test |
| A denylist creeps in for convenience | The scrubber takes an allowlist parameter with no default; there is no "scrub everything except" entry point |
| An export leaks a field added upstream later | O2's test adds an unexpected upstream field and asserts absence WITHOUT changing export code |
| `pending commit` softened in the client view | O1's paired test; plus `pending_items`/`blocked_items` are separate model fields, not a filtered view |
| Acknowledgement collapses into approval | `ClientAcknowledgment` has no answer field; posting one writes no decision entry |
| Route registrar accumulates complexity | Follow `workbench_routes.py`: module-level handlers, frozen `Deps`, branch-free registrar |
| A partially scrubbed bundle ships | Atomic staging; scan failure aborts and leaves no artifact |

## Complexity Tracking

Five user stories across three surfaces. Phase A is small and load-bearing; Phase D is the
largest and lowest-priority (US3 P1, US4/US5 P2). If review finds the package too large to
judge as one unit, the clean split is Phase D's support bundle (US5) into a follow-on
spec -- it shares only the scrubber with the rest. Flagged as an open item in
`checklists/requirements.md` rather than decided here.
