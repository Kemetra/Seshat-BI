# Adversarial Plan-Review: 044-live-surface-protocol

A single default-adverse skeptic over spec.md, plan.md, tasks.md (read-only),
checked against the constitution along five axes. Run 2026-06-29.

## Verdict: PASS

All required artifacts exist (spec, clarify block, plan, tasks, analyze). No
critical or high finding on any axis. The one load-bearing exact-string
assertion that was inherited rather than directly verified (the value-check
rule_id) has now been verified against source.

## Axis 1 -- hidden-principle-violation

PASS. The deliverable is one pytest module that injects a pure-Python fake and
opens no connection. It executes nothing against a database (Principle II),
exercises the BUILT-but-deferred live surface without a DB exactly as Principle
VIII permits, asserts a proven ERROR non-pass rather than a fabricated pass, and
asserts ERROR (not WARNING) severity per the severity-asymmetry clause. It
self-grants no approval and modifies no production gate. No violation found.

## Axis 2 -- assumes-deferred-capability

PASS. The plan and tasks depend only on already-present code: the `QueryRunner`
Protocol and `check_reconciliation` (validate.py), `check_expected_value` plus
`ExpectedValue`/`parse_expected_value` (value_proxy.py, both verified present),
and `Finding`/`Severity` (core.py). tasks.md Notes explicitly disclaim any
dependency on F016 (Power BI execution adapter) or F031-F033. No deferred
capability is assumed.

## Axis 3 -- c086-leak

PASS. Every C086/pharmacy mention across the artifacts is a prohibition, never
an adopted value. The illustrative fixture names are generic (`silver.widgets`,
`gold.fct_widgets`, measure `amount`, value `100.00`). FR-009, SC-005, and T012
mandate generic-only fixtures and a reviewer check. The grounding's noted risk
(copying the existing `Decimal('1552071.00')` or gold names) is explicitly
forbidden, not inherited.

## Axis 4 -- fabricated-confidence

PASS. No readiness or confidence number is produced. The load-bearing assertion
is categorical (no-rows -> exactly one ERROR Finding). The analysis.md
"Coverage: 100%" is a verifiable task-to-requirement mapping fact, not a
readiness score. Status is "Draft" in every artifact; no self-granted pass.

## Axis 5 -- over-scope

PASS. Scope is exactly one new file (`tests/unit/test_live_surface_protocol.py`)
plus a test-only `RecordingQueryRunner` inside it. No production module is
modified; no new source module, dependency, or harness is introduced. The
genuinely-new surface (recording-conformance fake + reconciliation no-rows
coverage) is narrow and the already-covered value-check no-rows case is
referenced, not duplicated (FR-010/T008). YAGNI respected.

## Verification note (resolved)

The value-check rule_id assertion (`V-L4`, used in FR-005, research R1,
data-model, contract C2, tasks T008, analysis SC-002) was initially inherited by
analogy. It is now directly verified: `src/retail/value_proxy.py:42` defines
`_RULE_ID = "V-L4"`, and `_error` (line 171) emits it with `Severity.ERROR`. The
reconciliation rule_id `V-RC16` was verified directly at `validate.py:268`. Both
load-bearing exact-string assertions are correct.

## Outstanding for the human (ratification)

None blocking. Ratification (flipping Status from Draft) remains a human action
this workflow does not perform.
