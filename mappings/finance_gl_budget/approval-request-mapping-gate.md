# Approval Request -- `finance-gl-budget-mapping-gate`

- **question_id:** `finance-gl-budget-mapping-gate`
- **stage:** `mapping_ready` (plus the `source_ready` RS1 confirmation)
- **subject:** clear the source-mapping gate for `finance_gl_budget` -- confirm the csv source,
  rule the budgeted-with-no-actuals semantics, and approve the declared 5-part grain (with
  `budget_version` as part of identity) and the second-fact star shape
- **owner_required:** `data-owner`
- **status:** `open` *(open until a named human answers it in an `approval-decision-*.md`; the
  agent may not record the answer -- Principle V)*

## Decision needed (one sentence)

> Confirm the csv source (RS1), rule whether the 241 budgeted combos with no posted actuals are
> expected business states, and approve the declared grain including `budget_version` so silver
> SQL may be authored.

---

## Sub-decision A -- RS1 source confirmation (`source_ready`)

Same evidence as the actuals request: a committed, seeded generator with byte-identical
regeneration (`tests/fixtures/finance_gl/generate.py`,
`tests/unit/test_finance_gl_generator.py`), declared UTF-8 without BOM, comma delimiter, header
row, `\n` newlines. `source_kind: "csv"` is declared, so RS1 requires your confirmation before
`source_ready` can pass. Ledger row **L2** records why this was honoured rather than exempted.

---

## Sub-decision B -- the declared grain, and `budget_version` as IDENTITY

### Evidence (measured)

- Grain: **one row = one budgeted amount per account per department per fiscal quarter per
  budget version**.
- The 5-part key is unique: **2,688 rows = 2,688 distinct**.
- Dropping `budget_version` collapses it to **1,344 distinct of 2,688 -- an exact 2:1
  collision**. That is the data-side proof that a version is part of budget IDENTITY, not an
  attribute: a new version must ADD rows and may never update, overwrite, or supersede a prior
  version's rows (spec 137 FR-011).
- Consequence worth stating plainly: any query that does not pin a version sums the plan twice
  -- **268,338,142.04** instead of `ORIGINAL`'s **136,402,896.13**.
  (source: `mappings/finance_gl_budget/source-profile.md`)
- Star: a SECOND fact `gold.fct_gl_budget_fgl` at quarter grain, sharing conformed
  `dim_account_fgl` / `dim_department_fgl` with the actuals fact, plus a quarter-grain
  `dim_fiscal_period_fgl`. It does NOT reference the daily calendar -- an RC15 deviation forced
  by the calendar contract being closed to Gregorian attributes (ledger row **L5**).

### What is being asked

Approve the grain, the 5-part PK, and the two-fact/shared-dimension shape -- or name what
should change. Until recorded, no `silver.*` SQL may be authored.

---

## Sub-decision C -- are 241 budgeted combos with no actuals expected? *(data-owner)*

### Evidence

| Measure | Count |
|---|---|
| Budget combos per version (year x quarter x account x dept) | 1,344 |
| P&L actual combos | 1,103 |
| P&L actual combos missing from `ORIGINAL` | **0** |
| Budget combos with **no** posted actuals | **241** |

### Why this is a gate question, not just a report question

If these are normal, then a gate that refuses them is **over-refusing** -- which spec 137
FR-023 counts as a failure rather than as safety, and which defect variant D12 is built to
observe. The agent cannot judge whether a budgeted line with no activity is normal for this
business.

### Options

- **A.** Expected business state -- surface as a report exception (the mirror of the Missing
  Budget Flag metric), never as a mapping failure or data defect. *(agent's proposal)*
- **B.** Indicates missing actuals -- treat as a data-quality blocker until the actuals source
  is completed.
- **C.** Depends on the account or department -- supply the rule.

---

## Sub-decision D -- the HR1 conformed-dimension ruling *(data-owner; BLOCKS CI)*

Identical to sub-decision D in `mappings/finance_gl_actuals/approval-request-mapping-gate.md`
-- one ruling covers both stars, so please answer it once there rather than twice.

In short: `seshat check` fires 2 HR1 errors because `dim_account_fgl` and `dim_department_fgl`
appear in both stars and are undeclared in `docs/quality/conformed-dimension-map.yaml`. The
registry reserves that `conformed` / `distinct` ruling for a human and HR1 never decides it, so
the agent has not written the entries. The declared intent in both maps is ONE shared dimension
per name. HR1 had never fired in this repository before -- this is the first two-fact case to
reach it.

## Already ruled (recorded, not re-asked)

| Ref | Ruling (Ahmed Shaaban, 2026-07-30) |
|---|---|
| OD-2 | the variance baseline is `budget_version = ORIGINAL`; `REVISION-1` never moves headline measures |
| OD-3 | no monthly view derived from the quarterly budget; a monthly-budget request is refused with the reason named |
| OD-1 | revenue and expenses both present as positive magnitudes; polarity via `direction_of_good` |

---

## How to answer

Record your decision in `mappings/finance_gl_budget/approval-decision-mapping-gate.md`, naming
yourself and the date, and add the matching `approvals[]` entries to `readiness-status.yaml`.
This request records nothing.
