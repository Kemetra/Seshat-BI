# Contract: Finance GL fixture file schemas

**Feature**: 137-finance-gl-genericity-proof | **Date**: 2026-07-30

Column order below is the WRITTEN order and is part of the determinism contract. Types are
logical; every file is CSV with a header row, UTF-8 without BOM, `\n` newlines.

## `finance_gl_actuals.csv`

| # | Column | Type | Constraint |
|---|---|---|---|
| 1 | `journal_entry_id` | text | derived, stable |
| 2 | `line_id` | integer | 1..N within entry |
| 3 | `posting_date` | date `YYYY-MM-DD` | inside a declared fiscal period |
| 4 | `account_code` | text | FK -> `accounts` |
| 5 | `department_code` | text | FK -> `departments` |
| 6 | `cost_center_code` | text | FK -> department's cost centers |
| 7 | `currency_code` | text | ISO-like 3 chars |
| 8 | `debit_amount` | decimal 2dp | >= 0 |
| 9 | `credit_amount` | decimal 2dp | >= 0 |
| 10 | `description` | text | ASCII, non-personal |

Sort order: `journal_entry_id`, `line_id`.

## `finance_gl_budget.csv`

| # | Column | Type | Constraint |
|---|---|---|---|
| 1 | `fiscal_year` | integer | |
| 2 | `fiscal_quarter` | integer | 1..4 |
| 3 | `account_code` | text | FK -> `accounts` |
| 4 | `department_code` | text | FK -> `departments` |
| 5 | `budget_version` | text | part of PK |
| 6 | `currency_code` | text | |
| 7 | `budget_amount` | decimal 2dp | zero allowed and meaningful |

Sort order: `fiscal_year`, `fiscal_quarter`, `account_code`, `department_code`,
`budget_version`.

## `accounts.csv`

`account_code`, `account_name`, `account_type`, `parent_account_code`,
`sign_convention_note`. Sort: `account_code`. The hierarchy is a single parent chain; no
ragged depth beyond what the matrix visual needs.

## `departments.csv`

`department_code`, `department_name`, `cost_center_code`, `cost_center_name`. One row per
cost center (the department repeats). Sort: `department_code`, `cost_center_code`.

## `fiscal_calendar.csv`

`fiscal_year`, `fiscal_quarter`, `period_start_date`, `period_end_date`. Contiguous,
non-overlapping, covering both years. Sort: `fiscal_year`, `fiscal_quarter`.

## Variant expression map

| ID | Expressed as | Notes |
|---|---|---|
| D1 unknown account | data variant | actuals row references a code absent from `accounts.csv` |
| D2 unknown department | data variant | as above for `departments.csv` |
| D3 irreconcilable hierarchy | data variant | budget rows posted at a parent level that no actuals hierarchy path reaches |
| D4 invalid fiscal period | data variant | one `posting_date` outside all periods |
| D5 mixed currency | data variant | a subset of rows in a second `currency_code` |
| D6 duplicate line id | data variant | one repeated (`journal_entry_id`, `line_id`) |
| D7 budget grain violation | data variant | duplicate budget PK with a different amount |
| D8 debit/credit presentation | benchmark scenario | a framing question, not a data defect |
| D9 revenue sign convention | benchmark scenario | as above |
| D10 baseline ambiguity | data + scenario | two `budget_version` values exist; the QUESTION is which is the baseline |
| D11 monthly-from-quarterly | benchmark scenario | a request, not a data state |
| D12 actuals with no budget row | data variant | **legitimate**; expected `proceed` (over-refusal trap) |
| D13 version overwrite | benchmark scenario | an attempted action, not a data state |

Every data variant differs from `clean` in exactly one respect; every scenario-expressed
variant declares one expected behaviour from the existing categorical set and cites its
observable evidence.
