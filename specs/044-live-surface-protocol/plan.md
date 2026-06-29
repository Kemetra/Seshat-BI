# Implementation Plan: Live-Surface Protocol Conformance Test (fake QueryRunner)

**Branch**: `044-live-surface-protocol` | **Date**: 2026-06-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/044-live-surface-protocol/spec.md`

## Summary

Add one new pytest module, `tests/unit/test_live_surface_protocol.py`, that
proves at runtime that the live-validator surface (a) reaches the database only
through the `QueryRunner` Protocol method `.run()` and (b) emits an ERROR
`Finding` (never a silent pass) when a query returns no rows. It introduces a
`RecordingQueryRunner` test fake that satisfies the Protocol with `.run()` alone
and records every invocation, injects it into `check_reconciliation`
(`src/retail/validate.py`) and `check_expected_value` (`src/retail/value_proxy.py`),
and asserts the existing `V-RC16` / `V-L4` ERROR contract. No production code is
modified; no database driver, connection, or credential is involved.

## Technical Context

**Language/Version**: Python 3.11+ (matches the existing `src/retail` package and
`tests/unit` suite).

**Primary Dependencies**: pytest (test runner) and the standard library only.
No new runtime or test dependency is added. The module imports the
already-present `retail.core` (`Finding`, `Severity`), `retail.validate`
(`check_reconciliation`, `ReconcileTarget`), and `retail.value_proxy`
(`check_expected_value`, the expected-value constructor/parser).

**Storage**: N/A. The test opens no database and holds no connection.

**Testing**: pytest, marked `pytest.mark.unit`, run via
`pytest tests/unit/test_live_surface_protocol.py`. Runs with psycopg2 absent.

**Target Platform**: Local dev + CI (Windows-first per repo `CLAUDE.md`;
platform-agnostic Python).

**Project Type**: Single project (library + CLI under `src/retail`, tests under
`tests/`).

**Performance Goals**: N/A (a handful of pure-Python unit assertions).

**Constraints**: Opens no network connection, imports no DB driver, requires no
credentials (FR-011). ASCII / UTF-8 without BOM. No exact-SQL-text assertions
(FR-012). Generic fixtures only (FR-009).

**Scale/Scope**: One test module; one `RecordingQueryRunner` fake; four to six
test functions (two no-rows ERROR cases, conformance assertions, at least one
passing-result control case).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle II (Execution is a separate, gated, last step)**: PASS. The test
  injects a pure-Python fake and opens no connection; it exercises the live
  surface without executing anything against a database.
- **Principle VIII (Static-First Governance, Live Deferred)**: PASS. It
  exercises the BUILT-but-deferred live surface with a fake, exactly as the
  principle permits; the real DB run remains deferred.
- **Anti-fabricated-confidence (constitution line 462)**: PASS. The load-bearing
  assertion is that no-rows yields a proven ERROR non-pass, never a silent or
  fabricated pass. No readiness/confidence number is produced.
- **Severity asymmetry (constitution lines 401-403)**: PASS. The test asserts
  ERROR (proven defect) on no-rows, never WARNING; it adds no new `Severity`.
- **Principle VII (C086 is an example, not the schema)**: PASS. Fixtures use
  generic names and arbitrary canned rows; no C086 value or gold name is copied.
- **Principle IX (Reproducibility / Windows-safe)**: PASS. Pure-Python,
  deterministic, ASCII / UTF-8 no BOM, short path.
- **Test-only, no executor**: PASS. No production module is modified; no DB
  driver, runtime, or adapter is added or assumed (no dependency on the deferred
  F016 Power BI execution adapter or F031-F033 runtimes).

No violations. Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/044-live-surface-protocol/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (the asserted contract, restated)
├── checklists/
│   └── requirements.md  # Spec quality checklist (from /speckit-specify)
├── spec.md              # Feature specification
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/retail/
├── core.py              # Finding, Severity            (READ ONLY -- imported)
├── validate.py          # QueryRunner Protocol,
│                        #   check_reconciliation, ReconcileTarget
│                        #                                (READ ONLY -- exercised)
├── value_proxy.py       # check_expected_value          (READ ONLY -- exercised)
└── rules/
    └── never_execute.py # B1 static AST guard       (NOT touched, NOT depended on)

tests/unit/
├── test_validate.py            # existing FakeRunner + RC clean/mismatch/null tests
├── test_value_proxy.py         # existing FakeRunner + test_check_no_rows_is_error
└── test_live_surface_protocol.py   # NEW -- the only file this feature adds
```

**Structure Decision**: Single-project layout. This feature adds exactly one
file under `tests/unit/` and creates no new source module. The
`RecordingQueryRunner` lives inside the new test module (it is test-only and has
no production consumer); it does not replace the existing per-module
`FakeRunner` classes.

## Phase 0 -- Research (research.md)

Resolve and record (all already grounded against the repo, no open unknowns):

1. The `QueryRunner` Protocol shape and the exact `rule_id` + severity emitted by
   each call-site on no rows (`V-RC16` ERROR in `check_reconciliation`; `V-L4`
   ERROR in `check_expected_value` via its single-value path).
2. The existing `FakeRunner` FIFO scripting pattern to mirror, and the existing
   `test_value_proxy.py::test_check_no_rows_is_error` to reference (not
   duplicate).
3. The minimal generic fixtures needed: a `ReconcileTarget` with generic
   silver/gold/measure names, and a single-value expected-value contract with a
   generic measure name + arbitrary approved value/tolerance.

## Phase 1 -- Design

- **data-model.md**: Describe the `RecordingQueryRunner` (Protocol-satisfying,
  records `.run()` calls, surfaces any non-`.run()` attribute access as a
  failure) and the two generic fixtures.
- **contracts/**: Restate the asserted contract as a checkable list -- (a)
  call-site uses only `.run()`; (b) no-rows -> exactly one ERROR `Finding` with
  the specified `rule_id`; (c) passing result -> no finding; (d) no new
  `Severity`/status; (e) no SQL-text assertion.
- **quickstart.md**: How to run the module (`pytest -m unit
  tests/unit/test_live_surface_protocol.py`) and what each test proves.

### Post-Design Constitution Re-Check

Unchanged from above -- the design adds only a test module and a test-only fake;
no new violation is introduced.

## Complexity Tracking

No constitution violations. Section intentionally empty.
