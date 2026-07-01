# Tasks: Live-validation evidence recorder (validate.py Findings -> readiness-status block)

**Feature**: `053-live-validation-evidence-recorder-validate`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Dependency-ordered, TDD-first. Scope is the pure transform seam only (YAGNI:
seam, not implementation). The file writer and any `status: pass` setting are
DEFERRED behind the FR-012 / FR-013 / FR-014 human rulings and are NOT tasks here.

`[P]` = parallelizable with siblings in the same phase (different files, no
ordering dependency).

## Phase 0 - Setup

- [ ] **T001** Confirm the consumed seams are unchanged and stdlib-only: read
  `src/retail/core.py` (`Finding`, `to_dict`), `src/retail/validate.py`
  (`run_live_checks` return shape), and `src/retail/cli.py::_redact_dsn`. Record
  the exact `Finding` field names and the redaction contract in a short module
  docstring for the new file. No code change. (Grounds FR-001, FR-006, FR-007.)

## Phase 1 - Tests first (RED)

- [ ] **T002** [P] Write `tests/unit/test_readiness_evidence.py` case: a clean
  live run (empty findings, `run_mode=live`) yields a `gold_ready` block with a
  non-empty `evidence[]` naming the table and zero `blocking_reasons[]`, and NO
  `pass` status set by the recorder, and NO numeric score field.
  (SC-001, SC-005, FR-002, FR-005, FR-012 default.)
- [ ] **T003** [P] Add case: a run with N ERROR findings yields exactly N
  `blocking_reasons[]`, each preserving rule_id + message + locator, status
  `blocked`. (SC-002, FR-003.)
- [ ] **T004** [P] Add case: WARNING findings are recorded in `warnings[]`,
  never in `blocking_reasons[]`, never dropped; a WARNING-only run has status
  `warning`. (FR-004.)
- [ ] **T005** [P] Add case: a finding message embedding a DSN/credential is
  scrubbed in the recorded block (no password/username/host/DSN substring
  survives); redaction is idempotent on an already-redacted message. (SC-003,
  FR-006, edge case.)
- [ ] **T006** [P] Add case: `run_mode=deferred` yields status `blocked` with a
  deferred-boundary `blocking_reasons[]` entry and no clean-run evidence.
  (FR-011, Story 3.)
- [ ] **T007** [P] Add case: the recorder never mutates its input findings list
  or Finding objects (assert inputs equal before/after); output is a new dict.
  (FR-007.)
- [ ] **T008** [P] Add case: a missing/blank `table_identity` raises a clear
  error rather than emitting a block with a placeholder identity. (Edge case.)
- [ ] **T009** [P] Add case: same inputs -> identical output on repeated calls
  (deterministic; any timestamp must be an explicit argument, not read from the
  clock). (SC-005.)
- [ ] **T010** Run the suite; confirm every new test FAILS (module/function not
  yet implemented). RED gate.

## Phase 2 - Implement (GREEN)

- [ ] **T011** Create `src/retail/readiness_evidence.py` with a pure,
  stdlib-only `build_gold_ready_block(findings, table_identity, run_mode,
  timestamp=None) -> dict`. No YAML/DB/driver import at module scope. Derive
  status per the plan's Status derivation table; build a NEW dict; reuse the
  redaction contract (import the existing helper lazily inside the function, or
  factor a shared pure scrubber -- must NOT pull a heavy import into the shared
  path). Never set `status: pass`. (FR-001..FR-008, FR-011, FR-012 default.)
- [ ] **T012** Run the suite; confirm all Phase 1 tests PASS. GREEN gate.

## Phase 3 - Guardrails (IMPROVE / verify invariants)

- [ ] **T013** Run the existing import-boundary guard test (B3,
  `tests/unit/test_live_surface_boundary.py`) and `retail check` to confirm no
  new heavy import leaked into the stdlib-only path with the new module present.
  If the recorder becomes reachable from a guarded module, extend that test to
  cover `readiness_evidence`. (SC-004, FR-008.)
- [ ] **T014** [P] Grep the new module + tests for any C086 / pharmacy table,
  column, or measure literal; confirm none are hardcoded (identifiers come only
  from test fixtures / inputs). (FR-009, FR-010.)
- [ ] **T015** [P] Confirm the new module writes nothing to
  `templates/readiness-status.yaml` and contains no file-write of a
  findings-bearing block (emit-only default; writer deferred behind FR-013).
  (FR-010, FR-013 default.)
- [ ] **T016** Run `ruff` + `pytest -m unit` clean; verify the spec's
  [NEEDS CLARIFICATION] markers (FR-012/013/014) are untouched and no `pass`
  status is emitted anywhere. Final gate.

## Out of scope (explicit -- do NOT do in this feature)

- Writing `mappings/<table>/readiness-status.yaml` (deferred behind FR-013).
- Setting `gold_ready.status` to `pass` (deferred behind FR-012).
- Any grain/uniqueness claim from an empty V-RC2 result (deferred behind FR-014).
- Modifying `run_live_checks` or the four live checks.
- Any DB provisioning, ingestion, or orchestrator wiring.
- Any assumption that F016 (Power BI Execution Adapter) or F031-F033 exist.
