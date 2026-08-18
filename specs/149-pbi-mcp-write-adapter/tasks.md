# Tasks: Approval-Gated Power BI MCP Write Adapter (F016 slice 5)

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)
**Data model**: [data-model.md](./data-model.md) | **Contract**: [contracts/cli-contract.md](./contracts/cli-contract.md)
**Branch**: `149-pbi-mcp-write-adapter` | **Date**: 2026-08-18

**Authority**: ADR 0018, RATIFIED by Ahmed Shaaban (owner) 2026-08-18 (commit `ef7f55a0`).
Decision 8 authorizes this task list; the mutation path ships only under this spec's tests and
review.

> **TDD is mandatory here.** Every implementation task has a preceding test task, and the test
> must fail for the right reason before the implementation lands. Two repo-specific bars, both
> earned from real defects:
> - **No absence-assertions.** Never assert a symbol is missing — that goes green when the
>   capability ships in a different shape. Pin the *behavior*.
> - **No vacuous branches.** A test whose precondition became unreachable proves nothing.
>   Precondition tests are hold-three-break-one and the suite asserts a refusal **count**.

---

## Phase 1: Setup

- [ ] T001 Create the adapter package skeleton `src/seshat/pbi_mcp_adapter/__init__.py`, re-exporting the outcome vocabulary imported from `seshat.dagster_adapter` (five values: `materialized`, `failed`, `skipped`, `blocked`, `deferred`) — do NOT redefine the set locally (research R1)
- [ ] T002 [P] Add a unit test `tests/unit/test_pbi_mcp_vocabulary.py` asserting the adapter's outcome set is identical to `seshat.dagster_adapter.OUTCOMES` and that the readiness token `pass` is NOT a member (hard rule #9)
- [ ] T003 [P] Create the stub MCP runtime fixture in `tests/unit/conftest.py` (or a shared fixture module) derived from the **real** `.seshat/powerbi-mcp-preflight.json` shape written by the shipped slice-4 preflight — not hand-invented (research R7, avoids a circular fixture)

---

## Phase 2: Foundational (BLOCKING — must complete before any user story)

These are the two chokepoints every later path runs behind. Nothing that can write may be built
until both are green.

- [ ] T004 Write failing test `tests/unit/test_pbi_mcp_invariants.py::test_bypass_flag_refused_in_every_mode` — parameterized over `readonly` AND `readwrite`, and over both discovery sites (invocation argv, resolved launcher config); assert refusal in every combination (FR-002)
- [ ] T005 [P] Write failing test in the same file asserting `--readwrite` present as a *default* (rather than an explicit opt-in) is also a violation (FR-003)
- [ ] T006 Implement `src/seshat/pbi_mcp_adapter/invariants.py` — the single chokepoint returning `InvariantVerdict(ok, violation)`; stdlib-only, no adapter-internal imports so it can never be circularly bypassed
- [ ] T007 [P] Write failing test `tests/unit/test_pbi_mcp_invariants.py::test_invariant_is_the_sole_chokepoint` — assert every module that can reach the runtime imports `invariants` (grep-by-import coverage, so a new callsite cannot skip it); pin the behavior, not the absence of a symbol

**Checkpoint**: the bypass prohibition holds in every mode, including tests.

---

## Phase 3: User Story 2 — Be refused when authority is missing (Priority: P1)

> **US2 is implemented BEFORE US1 deliberately.** The refusal path is the governance; building
> the write path first would mean a window in which mutation exists without a proven gate.
> This inverts the spec's story order for safety, not convenience.

**Goal**: every write attempt missing any one of the four preconditions is refused, naming the
specific missing authority. Zero refusals expressible as warnings.

**Independent test**: parameterized over each precondition — hold three, break one, assert
refusal every time; plus the fail-closed unreadable-state case.

### Tests first

- [ ] T008 [P] [US2] Write failing test `tests/unit/test_pbi_mcp_gate.py::test_hold_three_break_one` — parameterized across all four preconditions; assert refusal in each case AND that the reported blocker names the specific missing item; assert the total refusal **count** equals the parameter count so a never-taken branch is visible (FR-009)
- [ ] T009 [P] [US2] Write failing test `test_unreadable_state_refuses` — readiness state absent, malformed, and unreadable are three separate cases; each must refuse (FR-005). An unreadable gate is NEVER a passing gate
- [ ] T010 [P] [US2] Write failing test `test_approval_must_name_target_whole_token` — TWO cases: an approval naming `sales_model` must **refuse** target `sales_model_v2` (prefix case), and must **clear** target `sales_model` (exact-token case). This is the data-model rule that stops a loosely-worded note widening its own scope (FR-006)
- [ ] T011 [P] [US2] Write failing test `test_target_not_allowlisted_refuses` and `test_target_allowlisted_but_absent_on_disk_refuses` — the second must refuse as an undefined artifact, never invent it (FR-007, FR-011)
- [ ] T012 [P] [US2] Write failing test `test_dirty_tree_without_declared_backup_refuses` (FR-008)
- [ ] T013 [P] [US2] Write failing test `test_refusal_is_never_a_warning` — assert the refusal type has no warning-level representation; a `GateVerdict` with non-empty `blockers` is always blocking (FR-009)

### Implementation

- [ ] T014 [US2] Implement `src/seshat/pbi_mcp_adapter/gate.py` — read-only by contract, mirroring `src/seshat/dagster_adapter/gate.py`; exposes NO write path; returns frozen `GateVerdict` with typed `blockers`; fail-closed on unreadable state
- [ ] T015 [US2] Implement the target-naming matcher in `gate.py` — whole-token match (delimited by string bounds, whitespace, or punctuation), NOT a substring `in` check
- [ ] T016 [P] [US2] Implement `src/seshat/pbi_mcp_adapter/target.py` — allowlist resolution returning `ResolvedTarget(target_id, path, exists, report_in_scope)`
- [ ] T017 [P] [US2] Implement `src/seshat/pbi_mcp_adapter/git_safety.py` — clean-tree-or-declared-backup check, reusing the committed git-state helper rather than shelling out anew
- [ ] T018 [US2] Write and pass the **fail-open proof** `test_gate_is_what_produces_the_refusal` — monkeypatch out ONLY the gate and assert the old permissive verdict returns; proves the guard causes the refusal rather than incidental behavior

**Checkpoint**: US2 is independently shippable — the adapter can refuse correctly and cannot yet write at all.

---

## Phase 4: User Story 1 — Apply an approved change through the governed path (Priority: P1)

**Goal**: with all four preconditions cleared, apply the change, validate, and record — without
advancing any readiness stage.

**Independent test**: stubbed runtime + a fixture repo with passing stage and target-naming
approval; assert the artifact changed, evidence was written, and no stage moved.

### Evidence before execution (so the runner has somewhere honest to report)

- [ ] T019 [P] [US1] Write failing test `tests/unit/test_pbi_mcp_evidence.py::test_evidence_written_on_both_paths` — one record on success AND one on every failure path (FR-015)
- [ ] T020 [P] [US1] Write the **score-free proof** `test_evidence_carries_no_score` — scan every emitted record for any numeric/maturity/confidence field; assert none (FR-017, hard rule #9)
- [ ] T021 [P] [US1] Write failing test `test_no_stage_moves_on_success` — capture readiness stage state before and after a successful write; assert byte-identical, and specifically that `publish_ready` is unchanged (FR-018)
- [ ] T022 [P] [US1] Write the **redaction proof** `test_no_sensitive_token_survives` — assert no host, tenant, credential, or user path survives into a committed record, **including the whole `key=value` span**, not just the bare value (research R5)
- [ ] T023 [US1] Implement `src/seshat/pbi_mcp_adapter/evidence.py` — frozen `RunEvidence` with fixed `authority` label and typed `blockers`; redact via **derive-then-replace**: `conninfo_component_values()` / `uri_component_values()` to derive scrubbable forms, THEN `replace_fragments()`. NEVER pass a bare secret value to `replace_fragments` (research R5)

### Runner

- [ ] T024 [P] [US1] Write failing test `tests/unit/test_pbi_mcp_runner.py::test_runner_refuses_uncleared_gate` — call the runner with an uncleared `GateVerdict`; assert refusal, so a future callsite cannot reach the runtime around the gate
- [ ] T025 [P] [US1] Write failing test `test_stall_becomes_typed_blocked_not_a_hang` — the stub runtime hangs; assert a bounded wait produces a typed `blocked` outcome
- [ ] T026 [US1] Implement `src/seshat/pbi_mcp_adapter/runner.py` — `npx`-invoked official MCP over stdio; `stdin=subprocess.DEVNULL` plus its **own workload-sized** timeout constant, following `src/seshat/dagster_adapter/runner.py:142`. Do **NOT** use `gitutil.run_subprocess` — its docstring explicitly excludes execution runners because its shared cap would abort long user workloads (research R4). Never call `subprocess` bare
- [ ] T027 [P] [US1] Write failing test `test_runner_never_passes_bypass_flag` — assert the constructed argv cannot contain the bypass flag even if a caller requests it

### Wire the happy path

- [ ] T028 [US1] Implement the orchestration entry that sequences invariant → gate → target → git safety → execute → validate → evidence, per the data model's state machine; every terminal state emits exactly one evidence record
- [ ] T029 [US1] Write failing test `test_successful_write_reports_materialized` — assert outcome `materialized`, artifact changed, and evidence present

**Checkpoint**: US1 + US2 together are the MVP — a governed write that refuses correctly.

---

## Phase 5: User Story 3 — Recover safely when a write leaves the artifact invalid (Priority: P2)

**Goal**: post-write validation failure is blocking, carries rollback guidance, and is recorded.

**Independent test**: force a validation failure against an already-mutated fixture; assert
blocking, guidance present, evidence written for the failed run.

- [ ] T030 [P] [US3] Write failing test `tests/unit/test_pbi_mcp_validation.py::test_validation_failure_is_blocking_with_rollback` — assert blocking (never a warning) AND non-empty rollback guidance (FR-014)
- [ ] T031 [P] [US3] Write failing test `test_guidance_cannot_be_forgotten` — constructing a `ValidationOutcome` with non-empty `failed` and empty `rollback_guidance` must raise; the invalid state is unrepresentable
- [ ] T032 [P] [US3] Write failing test `test_runtime_reported_success_but_touched_nothing` — validation still runs; the no-op is reported honestly, not as an applied change
- [ ] T033 [P] [US3] Write failing test `test_evidence_exists_for_failed_run` — the failure path also writes exactly one record (FR-015)
- [ ] T034 [US3] Implement `src/seshat/pbi_mcp_adapter/validation.py` — runs the `seshat check` R-family; binding validation when `report_in_scope`; value validation when an expected value exists and a data leg is available (else `deferred`, not silently skipped)
- [ ] T035 [US3] Write failing test `test_rollback_restores_pre_write_state` — apply the printed guidance and assert the artifact returns to its pre-write validating state

**Checkpoint**: failures are now safe and recoverable.

---

## Phase 6: User Story 4 — Detect vendor preview drift (Priority: P3)

**Goal**: capability/flag/schema drift is a blocker before anything is trusted.

- [ ] T036 [P] [US4] Write failing test `tests/unit/test_pbi_mcp_drift.py::test_capability_drift_is_a_blocker` — feed a profile whose detected capabilities differ from the supported record; assert blocker, not warning (FR-019)
- [ ] T037 [P] [US4] Write failing test `test_unknown_range_is_never_compatible` — a `supported_range` of `unknown` must never be treated as compatible (FR-020)
- [ ] T038 [US4] Implement the `RuntimeCapabilityProfile` comparison, extending the shipped read-only preflight rather than duplicating its detection

---

## Phase 7: CLI surface

The existing vocabulary is **closed** and lazily imported. Both constraints are inherited.

- [ ] T039 [P] Write failing contract test `tests/unit/test_pbi_mcp_cli_contract.py::test_exit_code_matrix` — assert each of `0/1/2/3` is reachable and produced by its intended cause; `2` (validation failed) and `3` (indeterminate) must stay **distinct**
- [ ] T040 [P] Write failing test `test_no_escape_hatch_flag_registered` — assert no `--force`, `--yes`, or `--skip-*` flag exists on either leg; pin the parser's actual accepted arguments (behavior), not the absence of a constant
- [ ] T041 [P] Write failing test `test_refusal_leaves_artifact_byte_identical` — on exit `1`, the target file is unchanged
- [ ] T042 [P] Write failing test `test_lazy_import_boundary_holds` — importing the root CLI must NOT import `seshat.pbi_mcp_adapter`
- [ ] T043 [P] Write failing test `test_emitted_commands_are_executed` — actually RUN the emitted commands; string-shape assertions go green while the command is broken
- [ ] T044 Add the `plan-write` leg to `src/seshat/cli/parser_pbi_mcp.py` (dry run: evaluates everything, mutates nothing, writes no evidence) and register it in the closed list
- [ ] T045 Add the `apply` leg to `src/seshat/cli/parser_pbi_mcp.py` with `--target`, `--operation`, `--backup-declared`, `--json`
- [ ] T046 **Update the `pbi-mcp` group help text** — it currently claims "F016 stays parked -- no mutation path exists here", which becomes FALSE the moment a write leg registers. A help string that misdescribes the tool's authority is a governance defect, not cosmetic
- [ ] T047 Update the closed-vocabulary sync test deliberately to include the two new legs (never regex-sweep it — see the repo's bulk-checkbox lesson)
- [ ] T048 Implement the command handlers in `src/seshat/cli/commands/pbi_mcp.py`, returning the contract's exit codes and the JSON payload shape

---

## Phase 8: Skill and documentation

- [ ] T049 [P] Author `.claude/skills/pbi-mcp-write-adapter/SKILL.md` following the dbt/dagster adapter skill precedent — the agent-facing surface; must state that it never self-grants the approval
- [ ] T050 [P] Update `docs/integrations/pbi-mcp-adapter.md` to document the write path and its four preconditions
- [ ] T051 [P] Update the F016 row in `docs/roadmap/roadmap.md` from "NOT BUILT" once this ships — **and not before**; the five `parked_on: F016` edges in `docs/quality/parked-on.yaml` must be reconciled in the same change
- [ ] T052 Reconcile the vendoring language in `templates/pbi-mcp-adapter-contract.md` — it still says "the **vendored** ... binary (`tools/powerbi-modeling-mcp/`)", which contradicts ADR 0018's rejection of vendoring (research R6). **Owner-facing**: this template binds other features, so confirm scope before editing

---

## Phase 9: Polish & full gate set

- [ ] T053 Run `ruff format --check src/ tests/` and `ruff check src/ tests/` — both must be clean (format-check is the CI gate, not just `ruff check`)
- [ ] T054 Run `pytest -m unit -x -q` — all green; verify no new test SKIPPED silently (the CI unit job runs without app extras, so guard optional imports with `importorskip` and confirm the guard does not make the test vacuous)
- [ ] T055 Run `seshat check` — exit 0, and confirm **no new rule** was added and **no readiness stage** was introduced
- [ ] T056 Run `seshat semantic-check` — clean; the RS1 warning must never be silenced
- [ ] T057 Re-verify the three feature-specific proofs still hold after all wiring: fail-open (T018), score-free (T020), redaction (T022)
- [ ] T058 Confirm nothing in the diff lets a tool result advance an approval or move a stage — grep the diff for any write to `approvals[]` or a stage field; there must be none

---

## Dependencies & story order

```text
Phase 1 (Setup)
   └─► Phase 2 (Foundational: the invariant chokepoint) ── BLOCKING
          └─► Phase 3 (US2: refusal)      ◄── build FIRST, it is the gate
                 └─► Phase 4 (US1: the governed write)   ◄── MVP completes here
                        ├─► Phase 5 (US3: recovery)
                        └─► Phase 6 (US4: drift)
                               └─► Phase 7 (CLI)
                                      └─► Phase 8 (skill/docs)
                                             └─► Phase 9 (gate set)
```

**Story independence**: US2 ships alone (an adapter that only refuses is safe and useful as a
pre-check). US1 requires US2. US3 and US4 are independent of each other and both require US1.

**MVP scope**: Phases 1–4 (US2 + US1). That is a governed write with a proven refusal path.

## Parallel opportunities

- **Phase 1**: T002, T003 together.
- **Phase 3 tests**: T008–T013 are six independent files/cases — all `[P]`.
- **Phase 4 evidence tests**: T019–T022 together, before T023.
- **Phase 5**: T030–T033 together.
- **Phase 7 tests**: T039–T043 together, before the implementation tasks T044–T048.
- **Phase 8**: T049, T050, T051 together (T052 is owner-gated).

Implementation tasks touching the **same file** are never parallel: T014/T015 (both `gate.py`)
are sequential, and T044–T048 all touch the CLI parser/handler pair.

## Task count

**58 tasks** — Setup 3, Foundational 4, US2 11, US1 11, US3 6, US4 3, CLI 10, Docs 4, Polish 6.

## Out of scope (do not add tasks for these)

- Slice 6, the remote query-only server (ADR decision 7).
- Any new `seshat check` rule or readiness stage.
- Anything that lets a tool result grant, imply, or advance an approval.
- Advancing the F032 supported-version range beyond `unknown` (externally blocked until
  Microsoft publishes a release and a smoke run passes).
- Live database provisioning or tenant-state changes.
