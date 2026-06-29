# Quickstart: Live-Surface Protocol Conformance Test

## Run it

```bash
pytest -m unit tests/unit/test_live_surface_protocol.py
```

Runs with no database driver installed and opens no connection.

## What each test proves

- **Reconciliation conformance + no-rows ERROR**: injects a `RecordingQueryRunner`
  with an empty scripted result into `check_reconciliation`; asserts the
  call-site used only `.run()` and that the result is one `Severity.ERROR`
  `Finding` with `rule_id` `V-RC16`.
- **Value-proxy conformance + no-rows ERROR**: same for `check_expected_value`
  (single-value contract), asserting one ERROR `V-L4`. References the existing
  `test_value_proxy.py::test_check_no_rows_is_error` as prior art it complements.
- **Passing control(s)**: drives the same call-site(s) with a reconciling /
  within-tolerance result and asserts NO finding -- so the no-rows ERROR is
  shown to be caused by the empty result.

## What it intentionally does NOT do

- Does not modify `validate.py`, `value_proxy.py`, or `never_execute.py`.
- Does not assert exact SQL text.
- Does not introduce a new `Severity`/status (no "blocked-deferred").
- Does not use any C086/pharmacy value or gold name.
- Does not open a connection, import a driver, or need credentials.
