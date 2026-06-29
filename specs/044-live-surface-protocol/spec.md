# Feature Specification: Live-Surface Protocol Conformance Test (fake QueryRunner)

**Feature Branch**: `044-live-surface-protocol`

**Created**: 2026-06-29

**Status**: Ratified (Ahmed Shaaban, 2026-06-29)

**Input**: User description: "Live-Surface Protocol Conformance Test (fake QueryRunner)"

## Overview

The live-validator surface (`retail validate` -- the four live checks plus the
value-proxy check) is BUILT and fixture-tested but its live database run is
DEFERRED (constitution Principle VIII). Its driver-free guarantee rests on a
single seam: every call-site talks to the database only through the
`QueryRunner` Protocol method `run(sql, params) -> list[tuple]`, and the real
psycopg2 runner is imported lazily in the CLI handler only. A pure-Python fake
that implements only `.run()` therefore exercises the whole surface while
opening nothing.

This feature adds ONE new unit test module that turns that guarantee into an
executable, regression-proof assertion. It is the runtime/dynamic complement to
the existing static AST guard in `src/retail/rules/never_execute.py` (the "B1"
module-scope-import guard); it neither modifies nor depends on that module.

The test module asserts two contracts that are not yet jointly asserted
anywhere:

1. **Protocol conformance** -- the reconciliation and value-proxy call-sites
   interact with the injected runner ONLY through `.run()`. A recording fake
   that implements nothing else proves the surface opens no connection and
   honors the never-execute posture at runtime.
2. **Anti-fabricated-pass** -- a no-rows result yields an ERROR `Finding`
   (`rule_id` `V-RC16` for reconciliation, `V-L4` for the value check), never a
   silent pass.

This feature is TEST-ONLY. It reads and exercises `src/retail/validate.py` and
`src/retail/value_proxy.py` but modifies neither. It maps to NO roadmap F-row
(stage: unmapped).

### Grounding correction (load-bearing)

The originating idea phrased the no-rows contract as "a no-row result yields a
**blocked-deferred** Finding, never pass." That is NOT how the code works and
this spec MUST NOT inherit it. There is no `BLOCKED` or `DEFERRED` member of the
`Severity` enum. The verified contract is: no-rows -> an **ERROR** `Finding` (a
proven non-pass). `check_reconciliation` emits a `V-RC16` ERROR when a measure
query returns no rows; `check_expected_value` routes to its single-value path
which emits a `V-L4` ERROR when the aggregate returns no rows. This test asserts
against that EXISTING ERROR contract and introduces NO new status or severity.
Introducing a new status would be a behavior change to the production surface,
which would break the test-only / opens-nothing basis on which this work was
adopted.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reconciliation honors the never-execute seam and fails closed on no rows (Priority: P1)

A maintainer changing the reconciliation live check needs an automated proof
that the check (a) reaches the database only through the `QueryRunner` Protocol
method and (b) treats an empty result as a proven defect (ERROR), never as a
silent pass.

**Why this priority**: This is the genuinely-missing coverage. The existing
`test_validate.py` suite covers the clean, mismatch, and NULL-total branches of
reconciliation but has no empty-rows branch test, and no existing test records
runner interaction to prove the call-site stays on the Protocol method. This
story is the core value of the feature.

**Independent Test**: Inject a recording fake (implementing only `.run()`) that
returns an empty result into `check_reconciliation`, then assert (1) the only
runner method the call-site invoked was `.run()`, and (2) the returned findings
contain exactly one ERROR `Finding` with `rule_id` `V-RC16`. Delivers the
no-rows-on-reconciliation regression guard plus the Protocol-conformance proof.

**Acceptance Scenarios**:

1. **Given** a recording fake runner scripted to return an empty result and a
   reconciliation target naming a generic measure, **When** `check_reconciliation`
   runs against it, **Then** it returns exactly one `Finding` whose severity is
   ERROR and whose `rule_id` is `V-RC16`.
2. **Given** the same run, **When** the test inspects how the call-site used the
   runner, **Then** the only Protocol method invoked was `.run()` (the fake
   implements no other database method and none was called).
3. **Given** the test module runs in the standard dev environment, **When** the
   suite executes, **Then** it passes with no database driver installed and
   opens no network connection (the fake holds no connection object).

---

### User Story 2 - Value-proxy honors the never-execute seam and fails closed on no rows (Priority: P2)

A maintainer changing the value-proxy live check needs the same dual proof for
`check_expected_value`: it reaches the database only through `.run()`, and an
empty result is an ERROR, never a silent pass.

**Why this priority**: The no-rows -> ERROR behavior for the value check is
ALREADY proven by `test_value_proxy.py::test_check_no_rows_is_error`. The new,
non-duplicative surface here is the recording-fake Protocol-conformance proof
applied to the value-proxy call-site. The new module references the existing
no-rows test rather than re-deriving it.

**Independent Test**: Inject the recording fake into `check_expected_value` with
a generic single-value expected-value contract and an empty scripted result,
then assert the call-site used only `.run()` and that the result is a single
ERROR `Finding` with `rule_id` `V-L4`.

**Acceptance Scenarios**:

1. **Given** a recording fake scripted to return an empty result and a generic
   single-value expected-value contract, **When** `check_expected_value` runs,
   **Then** the result contains exactly one ERROR `Finding` with `rule_id`
   `V-L4`.
2. **Given** the same run, **When** the test inspects runner usage, **Then** the
   only Protocol method invoked was `.run()`.

---

### Edge Cases

- **Driver absent**: The suite already runs with psycopg2 absent; the recording
  fake holds no connection, so the test must pass with no driver installed and
  must not import any driver. This is part of the proof, not an incidental
  condition.
- **A clean result must still pass**: To make the no-rows ERROR assertion
  meaningful (and to avoid a fixture that always errors for the wrong reason),
  at least one scenario MUST drive the same call-site with a non-empty,
  reconciling/within-tolerance result and assert it produces NO finding -- so
  the test distinguishes "ERROR because no rows" from "ERROR for any input."
- **Unexpected runner attribute access**: If a future change makes a call-site
  reach for a runner attribute other than `.run()` (e.g., `.connection`,
  `.cursor`, `.execute`), the recording fake MUST surface that as a test
  failure rather than silently tolerating it.
- **Severity must be ERROR, not WARNING**: The assertion MUST check for ERROR
  severity specifically; a downgrade of the no-rows finding to WARNING is a
  readiness-gate weakening and MUST fail the test.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST add exactly one new test module at
  `tests/unit/test_live_surface_protocol.py`. It MUST NOT modify
  `src/retail/validate.py`, `src/retail/value_proxy.py`, or
  `src/retail/rules/never_execute.py`.
- **FR-002**: The feature MUST introduce a recording fake runner (a
  `RecordingQueryRunner`) that satisfies the `QueryRunner` Protocol by
  implementing `run(sql, params=()) -> list[tuple]` and that RECORDS each
  invocation, so a test can assert the call-site interacted with it only through
  `.run()`.
- **FR-003**: The recording fake MUST NOT implement, hold, or open any database
  connection, cursor, or driver object; satisfying the Protocol with `.run()`
  alone is the proof that the live surface "opens nothing."
- **FR-004**: A test MUST inject the recording fake into `check_reconciliation`
  with a scripted empty result and assert the result is exactly one `Finding`
  with severity ERROR and `rule_id` `V-RC16`.
- **FR-005**: A test MUST inject the recording fake into `check_expected_value`
  with a scripted empty result for a single-value contract and assert the result
  is exactly one `Finding` with severity ERROR and `rule_id` `V-L4`.
- **FR-006**: For each exercised call-site, a test MUST assert that the only
  Protocol method invoked on the runner was `.run()` (no other attribute or
  method was accessed). The mechanism for detecting any non-`.run()` access is
  an implementation detail of the fake.
- **FR-007**: At least one test MUST drive the same call-site(s) with a
  non-empty, passing result (reconciling totals / within-tolerance value) and
  assert NO finding is produced, so the no-rows ERROR assertion is shown to be
  caused by the empty result and not by the harness.
- **FR-008**: The module MUST NOT introduce, assert, or reference any new
  `Severity` or status value (no `BLOCKED` / `DEFERRED`). It asserts only
  against the existing `Severity.ERROR` and the existing `rule_id` values.
- **FR-009**: All fixtures MUST use generic table, measure, and value names and
  arbitrary canned rows. They MUST NOT copy C086/pharmacy-derived values (for
  example a specific approved total) or any gold table/measure names (Principle
  VII -- C086 is an example, not the schema).
- **FR-010**: The value-proxy no-rows scenario (FR-005) MUST reference the
  existing `test_value_proxy.py::test_check_no_rows_is_error` as the prior art it
  complements (via a code comment) rather than re-deriving identical coverage;
  the new value-proxy assertions add the Protocol-conformance proof, not a
  duplicate no-rows-only test.
- **FR-011**: The module MUST NOT open a network connection, import a database
  driver, or require any database credentials; it MUST pass in the standard dev
  environment with no `db` extra installed.
- **FR-012**: Assertions on runner usage MUST NOT assert exact SQL text.
  Conformance is "the call-site stays on `.run()` and produces the contracted
  `Finding`," not a match against query strings (which would couple the test to
  query wording and make it brittle).

### Key Entities

- **RecordingQueryRunner**: A test-only fake satisfying the `QueryRunner`
  Protocol. Returns scripted rows for each `.run()` call (FIFO, like the
  existing `FakeRunner`s) and additionally records every invocation so a test
  can assert the call-site used only `.run()`. Holds no connection/cursor/driver.
- **Generic reconciliation fixture**: A reconciliation target using generic
  silver/gold names and a generic measure name, paired with a scripted empty
  result (for the ERROR case) and a scripted reconciling result (for the pass
  case).
- **Generic single-value expected-value fixture**: An expected-value contract
  using a generic measure name and an arbitrary approved value/tolerance, paired
  with a scripted empty result (ERROR case) and a within-tolerance result (pass
  case).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With no database driver installed and no credentials configured,
  the new test module runs and passes (it opens no connection).
- **SC-002**: When a no-rows result is injected into the reconciliation
  call-site, the test observes exactly one ERROR finding identified as `V-RC16`;
  the value-proxy call-site likewise yields exactly one ERROR `V-L4`.
- **SC-003**: If a maintainer changes a covered call-site to reach the runner
  through anything other than `.run()`, at least one test in the module fails.
- **SC-004**: If a maintainer downgrades a covered no-rows finding from ERROR to
  WARNING, at least one test in the module fails.
- **SC-005**: A reviewer can confirm the module contains no C086/pharmacy
  values or gold names and no new `Severity`/status value by reading the module
  top to bottom.

## Assumptions

- The `QueryRunner` Protocol shape (`run(sql, params=()) -> list[tuple]`), the
  `V-RC16` and `V-L4` `rule_id` values, and the `Severity.ERROR` member are
  stable; the test asserts against them as the existing contract. If any
  changes, this test is the intended place for that change to surface.
- The existing per-call FIFO `FakeRunner` pattern (in `test_validate.py` and
  `test_value_proxy.py`) is the model for scripting results; the recording fake
  extends that pattern with invocation recording rather than replacing it.
- "Protocol conformance" is verified at the call-site/runtime level (the
  surface uses only `.run()`), complementing -- not replacing -- the static AST
  guard in `never_execute.py`.
- This feature advances no specific roadmap readiness stage; it hardens an
  already-built surface and is recorded as unmapped.

## Clarifications

### Session 2026-06-29

- Q: Should the no-rows result be asserted against the existing ERROR `Finding`
  contract, or should the test pursue the originating idea's literal
  "blocked-deferred Finding" outcome?
  A: Assert against the existing ERROR contract (`V-RC16` / `V-L4`,
  `Severity.ERROR`). There is no `BLOCKED`/`DEFERRED` `Severity` member, and the
  production surface emits ERROR on no rows. Pursuing a "blocked-deferred"
  outcome would require introducing a new status -- a behavior change to the
  live surface that contradicts the test-only / opens-nothing basis on which
  this work was adopted. The test corrects the idea's phrasing; it does not
  implement it. (Reversible: easy -- a test-only assertion choice; reflected in
  FR-004, FR-005, FR-008.)
- Q: Should the recording fake assert ONLY that the call-site stays on the
  `QueryRunner.run` Protocol method, or also assert the exact SQL text each
  call-site emits?
  A: Assert Protocol conformance (the call-site uses only `.run()`) plus the
  `Finding` contract (severity and `rule_id`). Do NOT assert exact SQL text:
  coupling the test to query wording is brittle and adds no governance value
  beyond the conformance + Finding assertions. (Reversible: easy -- the SQL-text
  assertion can be added later if a concrete need arises; reflected in FR-006,
  FR-012.)

### Deferred to human ruling (Principle V)

- None. This feature is test-only over generic fixtures against an
  already-built surface; it touches no real data and raises no grain /
  uniqueness, PII publish-safety, business rollup/segment, or product-identity
  question.
