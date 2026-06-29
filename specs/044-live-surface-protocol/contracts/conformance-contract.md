# Asserted Contract: Live-Surface Protocol Conformance

This is the checkable contract the new test module pins. It restates verified
production behavior; it is NOT a new contract on the production surface.

## C1 -- Protocol conformance (call-site uses only `.run()`)

For each exercised call-site (`check_reconciliation`, `check_expected_value`):
the only `QueryRunner` Protocol method invoked on the injected runner is
`.run()`. Any access to another database-shaped attribute (`connection`,
`cursor`, `execute`, ...) is a failure. (FR-006, FR-003, SC-003)

## C2 -- No-rows yields an ERROR Finding (never a silent pass)

- `check_reconciliation` with a no-rows result -> exactly one `Finding` with
  `severity == Severity.ERROR` and `rule_id == "V-RC16"`. (FR-004, SC-002)
- `check_expected_value` (single-value) with a no-rows result -> exactly one
  `Finding` with `severity == Severity.ERROR` and `rule_id == "V-L4"`. (FR-005,
  SC-002)

## C3 -- Passing result yields no finding (control)

Driving the same call-site(s) with a reconciling / within-tolerance result
yields NO finding -- proving the ERROR in C2 is caused by the empty result, not
by the harness. (FR-007)

## C4 -- No new Severity / status

The module asserts only against the existing `Severity.ERROR` and the existing
`rule_id` values. It introduces / references no `BLOCKED` or `DEFERRED` value.
(FR-008, SC-005)

## C5 -- No SQL-text coupling

Conformance is asserted via `.run()`-only usage plus the `Finding` contract, NOT
by matching exact SQL strings. (FR-012)

## C6 -- Opens nothing

The module imports no DB driver, opens no connection, and needs no credentials;
it passes with the `db` extra absent. (FR-011, SC-001)

## C7 -- Generic fixtures

No C086/pharmacy value or gold name appears in the module. (FR-009, SC-005)
