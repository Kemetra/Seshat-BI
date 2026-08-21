# Implementation Plan: Studio Governed Analyst Workbench

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development`
> (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Feature**: `specs/140-studio-governed-workbench/` | **Spec**: [spec.md](./spec.md) |
**Research**: [research.md](./research.md) | **Data model**:
[data-model.md](./data-model.md) | **Contracts**:
[workbench-api.yaml](./contracts/workbench-api.yaml),
[decision-write-boundary.md](./contracts/decision-write-boundary.md)

**Goal:** Give a named human an authorized path to record a business decision in
Studio, with the exact change and its provenance visible first, and without any
component being able to confer its own authority.

**Architecture:** Four ordered phases. Phase 1 builds the Decision Store append path
behind the shipped validators, with no UI. Phase 2 adds the read-only investigation
journey. Phase 3 adds proposals and the single decision-recording route -- the security
core. Phase 4 adds apply/verify and the scoped client-review context. Each phase is
independently shippable and gate-verifiable; the risky write paths land only after the
store's invariants are proven.

**Tech Stack:** Python 3.13, FastAPI (existing Studio app), `pyyaml` (the repo's only
YAML dependency — no round-trip loader is added), pytest. Frontend follows Foundation's
existing Studio asset pipeline.

**Spec status:** **ratified** -- Ahmed Shaaban (owner), 2026-08-21. Phases 0 and 1
below (research, design) are complete.

**Implementation phases remain BLOCKED.** FR-140-020 sets two conditions and only the
first is met: the package is ratified, but the **sole active Spec Kit fence must still
be moved to this plan**. Ratification is not activation — spec 139 carried the same
distinction ("Ratification does not activate implementation"). Until the fence moves,
no task in `tasks.md` may start.

## Global Constraints

Copied verbatim in effect from the spec; every task's requirements include these.

- The gate reads decisions from **tracked files at `HEAD`**. A working-tree write is
  never authority (FR-140-015).
- **One** approval-validity predicate exists in the codebase: the shipped
  `decision_store.approval_is_valid`. No second predicate, wrapper that relaxes it, or
  shadow implementation (FR-140-011).
- `signer`, `declared_authority`, and `answer` are **human-supplied only**, with no
  default anywhere (FR-140-009).
- Studio **never** runs `git add`/`git commit` on a user's behalf (FR-140-023).
- A written-but-uncommitted decision renders as `pending commit`, never approved
  (FR-140-021).
- Decision writes are **append-only and atomic** (FR-140-022).
- Store paths are the three existing `.seshat/` files; no new store path.
- Foundation's redaction, accessibility, no-remote-assets, and credential boundaries
  remain mandatory (FR-140-019).
- Single-file health: keep new modules focused; the repo's CodeScene gate flags files
  approaching ~800 lines.

## Summary

Foundation (spec 139) shipped observation: `GET`-only projection routes, an
`ApprovalEnvelope` that models `named_human` and permanently refuses it, and a
read-only Decision Store. This feature builds the authorized path through that
refusal. It introduces the first domain-mutating routes in Studio, which is why the
write boundary is specified and built before any UI touches it.

## Technical Context

| Concern | Existing | This feature |
| --- | --- | --- |
| Decision validation | `approval_is_valid`, `owner_shape_ok`, `APPROVAL_REQUIRED_FIELDS` | reused, never reimplemented |
| Decision persistence | none (read-only store) | **new**: append-only atomic write |
| Workspace revision | `projection._revision_digest` | reused as `workspace_revision` |
| Evidence/defects | `EvidenceRef`, `InputDefect`, `StageState` | reused for US1 |
| Technical approval | `ApprovalEnvelope`, `forbidden_scope_for` | reused; business decision stays a distinct model |
| Routes | 6 GET + 1 POST bootstrap | +4 routes (see contract) |

## The seam

`decision_write.py` is a new module, deliberately **not** an extension of
`decision_store.py`.

Rationale: `decision_store.py` is the read side that the static gate depends on, and it
is imported by rule code. Adding a write path into it would put mutation and the gate's
read predicate in one file, and would grow a file the health gate already watches.
Keeping the write path separate means the gate's module stays read-only by construction,
and a reviewer can audit the entire mutation surface in one file.

The new module **imports** the validators from `decision_store`; it does not copy them.

## Constitution Check

| Principle | How this plan complies |
| --- | --- |
| I -- `check` is the gate | Readiness recomputed from `HEAD`; Studio never asserts a pass |
| V -- never self-grant approval | `signer`/`answer` have no default; receipt type cannot say approved; no git automation |
| Mapping before Silver | Proposals call the existing engines and respect `forbidden_scope_for` |
| No fabricated confidence | No score anywhere; states are categorical |
| Live boundary honesty | Missing DSN yields `[PENDING LIVE PROFILE]`, never a synthesized pass |

## Project Structure

### Documentation (this feature)

```
specs/140-studio-governed-workbench/
├── spec.md
├── research.md
├── data-model.md
├── plan.md              <- this file
├── tasks.md
├── quickstart.md
├── checklists/requirements.md
└── contracts/
    ├── workbench-api.yaml
    └── decision-write-boundary.md
```

### Source code

```
src/seshat/
├── decision_write.py           <- NEW: append-only atomic decision write
└── studio/
    ├── evidence.py             <- NEW (Phase B): EvidenceBundle view over projection
    ├── proposals.py            <- NEW: ChangeProposal build + hash + staleness
    ├── decision_routes.py      <- NEW: the one recording route
    ├── apply.py                <- NEW (Phase D): scoped apply + receipt
    ├── review_scope.py         <- NEW (Phase D): client-review least privilege
    └── app.py                  <- MODIFY: register new routers
tests/unit/
├── _workbench_fixtures.py      <- NEW (Task 1.0): shared fixtures; builds on
│                                  _studio_workspace_fixtures.py, never a bespoke fake
├── test_workbench_fixtures.py
├── test_decision_write.py
├── test_studio_evidence.py
├── test_studio_proposals.py
├── test_studio_decision_routes.py
├── test_studio_apply.py
└── test_studio_review_scope.py
```

**Reuse, do not reinvent**: `tests/unit/_studio_workspace_fixtures.py` already ships
`write_ready_table`, `write_pending_live_table`, `write_malformed_table` and siblings,
and `tests/unit/test_studio_approval_reachability.py::_client` is the house
authenticated-client pattern. Task 1.0 wraps those; a hand-rolled readiness document
would make the suite green while proving nothing about the shipped readers.

**Dependency constraint**: the repo is `pyyaml`-only by design (`pyproject.toml` pins
`pyyaml>=6` and notes the static core stays dependency-light). The decision append is a
validated text append plus a merged-document re-parse, not a round-trip loader — adding
`ruamel.yaml` would trip the dependency-freshness gate and is not permitted here.

## Phase 0 -- Research (DONE, recorded in research.md)

R1-R7 established: routes are GET-only; `allow_permitted` refuses named-human; the
store is read-only with one shared predicate; the store is read from tracked files;
provenance/revision primitives exist; 139's ratification precedent; 139 accepted 38/38.

## Phase 1 -- Design (DONE, recorded in data-model.md and contracts/)

Three-state model (`draft` / `pending commit` / `authoritative`), entity shapes derived
from validators rather than from a sample file, and seven write-boundary obligations
each with a named proof.

### Design invariants (each maps to a spec FR)

| Invariant | FR | Proof lives in |
| --- | --- | --- |
| Reuse shipped predicates only | FR-140-011 | Task 1.4 |
| Validate before write, atomic | FR-140-022 | Task 1.2, 1.3 |
| Append-only, round-trip safe | FR-140-022 | Task 1.3 |
| No default signer/answer | FR-140-009 | Task 3.3 |
| No git automation | FR-140-023 | Task 1.5 |
| Receipt cannot claim approval | FR-140-021 | Task 3.4 |
| Readiness reads HEAD | FR-140-015 | Task 3.5 |

## Implementation phases (BLOCKED on ratification)

### Phase A -- Decision Store write path (no UI)

Tasks 1.1-1.5. Deliverable: `decision_write.py` that appends a validated decision
atomically, and refuses everything the shipped validators refuse. Independently
testable with no HTTP surface. **Nothing in later phases may begin until Phase A's
tests are green**, because every later phase depends on these invariants.

### Phase B -- Investigation journey (US1)

Tasks 2.1-2.3. Read-only. Extends the existing projection into an `EvidenceBundle`
view. No new mutation. Low risk; ships value on its own.

### Phase C -- Proposals and decision recording (US2, US3) -- the security core

Tasks 3.1-3.6. Adds `POST /proposals` and the single `POST /decisions/record`. This is
where review attention belongs.

### Phase D -- Apply and client review (US4, US5)

Tasks 4.1-4.4. Scoped apply with receipt, and the least-privilege review scope.

Task-level steps with test code are in [tasks.md](./tasks.md).

## Verification Strategy

1. **Every guard proven by removal.** Each obligation's test must fail if the guard is
   deleted or monkeypatched away. An absence-assertion (grepping that a string is
   missing) does not count on its own.
2. **The readiness test needs both halves.** Assert an uncommitted decision moves
   nothing **and** that committing it does move the stage. The first alone passes
   vacuously if readiness is never recomputed at all.
3. **Fixtures validated by shipped code.** No hand-written expected YAML as the
   assertion. Assert `approval_is_valid(entry, authority) == (True, None)` for valid
   entries and the exact refusal reason for each invalid one. The repo tracks no real
   store file, so a self-consistent fake is the main vacuity risk here.
4. **Cross-platform.** No POSIX-only path shapes in fixtures; the CI `unit` job runs
   `ubuntu-latest` only, so a Windows-locked fixture would be invisible in CI (issue
   #691 is the precedent).
5. **Gates.** `ruff format --check`, `ruff check`, `pytest -m unit`, `seshat check`,
   `seshat kit-lint` before every commit.

## Known Risks

| Risk | Mitigation |
| --- | --- |
| YAML round-trip loses comments/order on append | Phase A Task 1.3 asserts comment + entry survival explicitly; choose a round-trip loader, not `safe_dump` |
| A reviewer reads `pending commit` as approved | Single-member enum makes the false state unrepresentable; quickstart Journey 3 makes the check explicit |
| Scope creep from five user stories in one ratification | Phased so A-C deliver the core; the checklist raises the split question to the ratifier |
| Second predicate creeps in via a helper | Task 1.4 greps for it and monkeypatches the real one to prove reachability |
| Studio gains a git call later | Task 1.5 asserts the write path succeeds with the git runner raising |
| Apply exceeds reviewed scope | Task 4.2 widens scope and asserts refusal |

## Complexity Tracking

Five user stories plus a new persistence path is a large single ratification --
benchmarked against 139 (37 FRs, 38 tasks, ~2,200 lines). The owner chose all-five
scope on 2026-08-21. Phasing is the mitigation: A-C form a coherent shippable core, and
D can be deferred at execution time without invalidating the ratified spec. If review
finds the package too large to judge as one unit, the clean split is Phase D into a
follow-on spec -- flagged as an open item in `checklists/requirements.md`.
