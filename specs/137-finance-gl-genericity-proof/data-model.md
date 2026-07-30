# Phase 1 Data Model: Finance GL Budget-vs-Actual Genericity Proof

**Feature**: 137-finance-gl-genericity-proof | **Date**: 2026-07-30

All names are placeholders filled by THIS example; per Constitution Principle VII none of
them may be copied into a generic template.

## 1. Source entities (bronze inputs)

### 1.1 `finance_gl_actuals`

**Grain**: one row per journal entry x journal line (a line is unique within its entry).

**Declared PK**: (`journal_entry_id`, `line_id`).

| Column | Type | Notes |
|---|---|---|
| `journal_entry_id` | text | Deterministically derived (`JE-<fiscal_year>-<seq>`), never a random UUID. |
| `line_id` | integer | 1..N within the entry. |
| `posting_date` | date | Must fall inside a declared fiscal period (see 1.5). |
| `account_code` | text | FK to `accounts.account_code`. |
| `department_code` | text | FK to `departments.department_code`. |
| `cost_center_code` | text | FK to a cost center of that department. |
| `currency_code` | text | Single value in the clean fixture. |
| `debit_amount` | decimal(18,2) | >= 0. |
| `credit_amount` | decimal(18,2) | >= 0. |
| `description` | text | Synthetic, non-personal, ASCII. |

**Validation rules**
1. Exactly one of `debit_amount` / `credit_amount` is non-zero per line.
2. Every entry balances: sum(debit) = sum(credit) across the entry's lines.
3. (`journal_entry_id`, `line_id`) is unique -- duplication is defect variant D6.
4. `posting_date` resolves to exactly one fiscal period -- failure is defect variant D4.
5. P&L accounts only. No balance-sheet snapshot rows (spec 091 boundary).

### 1.2 `finance_gl_budget`

**Grain**: one row per fiscal quarter x account x department x budget version.

**Declared PK**: (`fiscal_year`, `fiscal_quarter`, `account_code`, `department_code`,
`budget_version`).

| Column | Type | Notes |
|---|---|---|
| `fiscal_year` | integer | |
| `fiscal_quarter` | integer | 1..4. |
| `account_code` | text | FK to `accounts.account_code`. |
| `department_code` | text | FK to `departments.department_code`. |
| `budget_version` | text | At least two distinct values exist (e.g. an original and a later revision). Part of identity. |
| `currency_code` | text | |
| `budget_amount` | decimal(18,2) | May be zero -- zero is NOT the same as absent. |

**Validation rules**
1. PK unique; a repeated PK with a different amount is defect variant D7 (grain violation).
2. A new `budget_version` ADDS rows; it never updates or deletes a prior version's rows.
3. Absence of a (quarter, account, department) row is a legitimate business state
   (missing budget), surfaced by the Missing Budget Flag metric -- never auto-filled with 0.

### 1.3 `accounts`

`account_code` (PK), `account_name`, `account_type` (P&L category), `parent_account_code`
(nullable, forms the hierarchy), `sign_convention_note` (informational only -- the actual
sign policy is OD-1 and stays unresolved).

### 1.4 `departments`

`department_code` (PK), `department_name`, plus a cost-center child list
(`cost_center_code`, `cost_center_name`, `department_code`).

### 1.5 `fiscal_calendar`

`fiscal_year`, `fiscal_quarter`, `period_start_date`, `period_end_date`. Contiguous and
non-overlapping across the two years; the clean fixture is calendar-aligned (a recorded
fixture simplification, not a general claim).

## 2. Gold model

```text
dim_date ────────┐
dim_account ─────┼──── fact_gl_actuals   (grain: journal entry x line)
dim_department ──┘
        └────────┴──── fact_gl_budget    (grain: fiscal quarter x account x dept x version)
```

- **Two facts, never merged** (spec SC-004).
- Both facts reference the SAME conformed dimensions with the same surrogate keys and the
  same unknown-member convention already used by the retail star.
- `fact_gl_budget` additionally carries `budget_version` as part of its grain; it is not a
  dimension of `fact_gl_actuals`.
- Comparison happens at the budget grain by aggregating actuals UP. Nothing disaggregates
  budget DOWN (FR-010, OD-3).

**State transitions**: none. Both facts are append-only within this example; no SCD
behaviour is modelled (dimension history belongs to spec 088).

## 3. Metric contracts (seven)

| Metric | Shape | Aggregation rule | Blocking ambiguity |
|---|---|---|---|
| Actual Amount | additive | SUM of signed line amounts at any grain | OD-1 (sign convention) |
| Budget Amount | additive at its own grain | SUM; never spread to a finer grain | OD-2 (which baseline) |
| Variance Amount | derived | (Actual aggregated) - (Budget aggregated), both at the comparison grain | OD-1, OD-2 |
| Variance % | non-additive ratio | computed AFTER separate aggregation; averaging precomputed percentages is prohibited | OD-1, OD-2; RAG thresholds NOT invented |
| Actual YTD | additive, period-to-date | SUM over periods from fiscal-year start to the selected period | fiscal-year start is stated by the calendar, not inferred |
| Budget YTD | additive, period-to-date | SUM over quarters to date at budget grain | OD-2 |
| Missing Budget Flag | existence indicator | flags (quarter, account, dept) combinations with actuals but no budget row | must not be confused with zero budget (FR-015) |

Every contract uses the existing `templates/metric-contract.yaml` field set with zero new
or renamed fields (FR-013), records its ambiguities in that template's ambiguity ledger,
and carries blocking reasons until a named human rules.

## 4. Defect variant catalog

Each variant is one deterministic perturbation of the clean fixture and declares ONE
expected outcome from the existing categorical set.

### Structural (mechanically checkable)

| ID | Perturbation | Expected outcome |
|---|---|---|
| D1 | `account_code` present in actuals but absent from `accounts` | `refuse`, naming the offending code (a broken FK is a data fact, not a missing-evidence question) |
| D2 | `department_code` present in actuals but absent from `departments` | `refuse`, naming the offending code |
| D3 | Budget account hierarchy that cannot be reconciled to the actuals hierarchy | `block_for_evidence` |
| D4 | `posting_date` outside every declared fiscal period | `refuse` |
| D5 | Mixed `currency_code` with no approved conversion policy | `request_human_decision` |
| D6 | Duplicate (`journal_entry_id`, `line_id`) | `refuse` |
| D7 | Two budget rows sharing the full PK with different amounts | `refuse` |

### Business judgment (human-owned)

| ID | Situation | Expected outcome | Owner decision |
|---|---|---|---|
| D8 | Debit/credit presentation ambiguous | `request_human_decision` | OD-1 |
| D9 | Revenue sign convention ambiguous | `request_human_decision` | OD-1 |
| D10 | Baseline could mean Original Budget or Latest Forecast | `request_human_decision` | OD-2 |
| D11 | Monthly view requested from quarterly budget, no allocation policy | `refuse` (allocation would invent numbers) | OD-3 |
| D12 | Actuals exist for a (quarter, account, dept) with no budget row | `proceed` -- surface as a business exception, NOT a defect | none |
| D13 | A new budget version would overwrite prior-version rows | `refuse` | OD-2 |

**D12 is the deliberate over-refusal trap.** A department that legitimately has actuals
without a budget row (or a budget without actuals) is a business exception the report must
show. If the gate refuses D12, that is recorded as `over_refusal` -- a failure, not safety
(FR-023). The six rows D8-D13 are the ones registered as benchmark scenarios (FR-022).

## 5. Genericity ledger row

```yaml
location:              # file path (+ line where meaningful)
observed_problem:      # what blocked or misdirected the finance walk
classification:        # no_leak | nominal_leak | documentation_leak | semantic_leak | authority_leak
existing_rule_or_surface:  # which rule/template/skill/doc it belongs to
minimal_resolution:    # smallest change that would clear it
core_change_required:  # true | false
evidence:              # command output, quoted text, or artifact path
```

Rules: one row per distinct obstruction (multiple sightings = multiple cited locations in
ONE row); ties between `nominal_leak` and `semantic_leak` resolve to `semantic_leak`; the
conclusion is categorical, with no count-based threshold and no score of any kind.
