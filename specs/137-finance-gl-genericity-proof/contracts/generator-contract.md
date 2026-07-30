# Contract: Finance GL synthetic source generator

**Feature**: 137-finance-gl-genericity-proof | **Date**: 2026-07-30

The generator is the only executable artifact this feature introduces. It is a test/fixture
utility, NOT a product surface: it adds no CLI verb, is not exported from the `seshat`
package, and nothing in `src/` imports it.

## Interface

```text
generate(output_dir: Path, variant: str = "clean") -> dict[str, Path]
```

- `output_dir` -- destination directory (created if absent). Callers pass a temp or
  git-ignored path; the generator never writes outside it.
- `variant` -- `"clean"` or one of the declared defect ids (`D1`..`D13`, where a variant is
  data-expressible). Unknown variant -> raise, never silently fall back to clean.
- Returns a mapping of logical source name -> written file path.

## Determinism obligations

1. One PRNG, constructed as `random.Random(20260730)`; no module-level `random` calls.
2. No `datetime.now()`, no `date.today()`, no `time.*`, no `uuid4()`, no environment
   reads, no network access, no database connection.
3. All dates derive from a hard-coded base date and fixed offsets.
4. Monetary values are `Decimal`, quantized to two places, written with a fixed format
   string (never bare `float` repr).
5. Rows are written in an explicitly declared sort order per file.
6. Newlines are written explicitly as `\n` (`newline=""` on the file handle) so output does
   not vary by platform.
7. Identifiers are derived from the row's own position/keys, never from a counter that
   depends on iteration order of an unordered container.

**Acceptance**: generating twice into two different directories yields byte-identical files
and identical SHA-256 digests per file. This is verified by comparison in a unit test, not
asserted in prose.

## Content obligations

- Synthetic only: no real company data, no personal data, no secrets, no credentials, no
  local absolute paths, no third-party dataset content.
- ASCII-only text fields.
- Amounts and codes are plausible in SHAPE only; no real chart of accounts is reproduced.

## Output set (variant = clean)

| Logical source | File |
|---|---|
| Actuals | `finance_gl_actuals.csv` |
| Budget | `finance_gl_budget.csv` |
| Accounts | `accounts.csv` |
| Departments | `departments.csv` |
| Fiscal calendar | `fiscal_calendar.csv` |

Shape: ~2 fiscal years, 30 accounts, 6 departments, 4-8 cost centers, ~5,000 journal
lines, quarterly budgets, >= 2 budget versions.

## Defect variants

A variant differs from `clean` by exactly ONE intended perturbation, produced by the same
seeded generator (never by hand-editing a copy), so an observed governance outcome
attributes to a single cause. Variants that are NOT data-expressible (a request framed by a
human, e.g. D11's "give me a monthly view") are declared in the benchmark scenario file
rather than as a data variant, and this file records which is which.

## Storage contract

- Full generated output is written to a **git-ignored** directory.
- Only small excerpts (`excerpts/*.head.csv`, tens of rows) are committed, for citation in
  the worked example and for reviewer inspection.
- Rationale is measured, not preferential: the largest committed data fixture in the repo
  today is 1,801 bytes (`tests/fixtures/demo/demo_sample_orders.csv`), so a ~5,000-line
  journal file would be a new bulk-data precedent.

## Non-obligations (explicitly out of scope)

- No schema migration, no DB load, no dbt/Dagster invocation.
- No inference of business policy (sign convention, baseline, allocation) -- the generator
  produces data, never decisions.
- No score, rating, or quality metric emitted about its own output.
