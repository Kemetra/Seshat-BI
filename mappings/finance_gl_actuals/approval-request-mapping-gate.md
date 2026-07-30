# Approval Request -- `finance-gl-actuals-mapping-gate`

- **question_id:** `finance-gl-actuals-mapping-gate`
- **stage:** `mapping_ready` (plus the `source_ready` RS1 confirmation, below)
- **subject:** clear the source-mapping gate for `finance_gl_actuals` -- confirm the csv
  source, rule the two open questions, and approve the declared grain + gold star shape
- **owner_required:** `data-owner` for A and C1; `analyst` for C2
- **status:** `open` *(a request is `open` until a named human answers it in an
  `approval-decision-*.md`; it never answers itself, and the agent may not record the answer
  on the owner's behalf -- Principle V)*

## Decision needed (one sentence)

> Confirm the csv source (RS1), rule whether P&L reporting excludes clearing accounts and
> whether cost-center-level analysis is required, and approve the declared grain
> (`journal_entry_id` + `line_id`) and gold star so silver SQL may be authored.

---

## Sub-decision A -- RS1 source confirmation (`source_ready`)

### Evidence

- This is a standalone FILE source, so `source_kind: "csv"` is declared and RS1 requires a
  named owner to confirm the encoding/delimiter/header before `source_ready` can read `pass`.
  (source: `mappings/finance_gl_actuals/readiness-status.yaml`)
- The source is not a found file: it is emitted by a committed generator from a single seeded
  PRNG with no clock, no UUID, no network and no database, and regeneration is byte-identical
  (verified by comparing bytes AND per-file SHA-256).
  (source: `tests/fixtures/finance_gl/generate.py`;
  `tests/unit/test_finance_gl_generator.py::test_regeneration_is_byte_identical`)
- Encoding is therefore declared and tested: UTF-8 without BOM, comma delimiter, header row,
  `\n` line endings, fixed column order.
- The mismatch between "a human confirms an inferred encoding" and "a test proves a declared
  encoding" is recorded as ledger row **L2** and was deliberately NOT resolved by exempting
  this fixture. (source: `docs/worked-examples/finance-gl-genericity-ledger.md`)

### What is being asked

Confirm that the generator + determinism test are acceptable provenance for this source, or
state what additional confirmation you want. Either way the answer is yours to record.

---

## Sub-decision B -- the declared grain and star shape (`mapping_ready`)

### Evidence (measured)

- Grain: **one row = one journal line within one journal entry**.
- The composite PK (`journal_entry_id`, `line_id`) is unique on the landed data: **5,000 rows =
  5,000 distinct**. `journal_entry_id` ALONE is only **2,500** distinct, so a single-column key
  would be wrong. (source: `mappings/finance_gl_actuals/source-profile.md`)
- Double entry balances exactly: total debits = total credits = **31,135,795.20**; 0 entries
  where the sides disagree; 0 lines with both sides zero or both non-zero.
- Referential integrity is clean: 0 orphan `account_code`, 0 orphan `department_code`, 0
  invalid department/cost-center pairs, 0 posting dates outside a declared fiscal period.
- Gold star: one fact `gold.fct_gl_actuals_fgl` at line grain, plus conformed
  `dim_account_fgl` / `dim_department_fgl` (shared with the budget map), an actuals-only
  `dim_cost_center_fgl`, and the RC15 daily `dim_date_fgl`.
  (source: `mappings/finance_gl_actuals/source-map.yaml`)

### What is being asked

Approve the grain, the PK, and the star shape -- or name what should change. Until this is
recorded, `reviewed_by` / `reviewed_on` stay `[PENDING GATE APPROVAL -- OD-4]` and **no
`silver.*` SQL may be authored** (hard stop `no_silver_before_mapping_cleared`).

---

## Sub-decision C1 -- do clearing accounts leave P&L reporting? *(data-owner)*

### Evidence

- The source has 30 accounts, 2 of them `account_type = 'CLEARING'` (`1900`, `1910`), on
  exactly **2,500** lines -- one per entry.
- Those lines are why the extract balances at all: a P&L line cannot be offset by another P&L
  line, and balance-sheet grain is out of scope (spec 091).
- Independent data support for excluding them: of 1,199 actual (year, quarter, account,
  department) combos, 96 have no budget row -- and **all 96 are clearing combos** (2 x 6 x 8).
  Once clearing is excluded, P&L coverage against budget is **complete (0 gaps)**.

### Options

- **A.** Keep clearing rows through silver and gold; exclude them in reporting by filtering
  `dim_account_fgl.account_type <> 'CLEARING'`. *(agent's proposal -- preserves the provable
  balance in the warehouse, keeps the exclusion visible in every contract)*
- **B.** Drop clearing lines at silver. *(simpler queries; destroys the double-entry balance
  proof and makes the warehouse un-reconcilable to the source)*
- **C.** Keep them and include them in P&L totals. *(double-counts every entry -- stated only
  for completeness)*

---

## Sub-decision C2 -- is cost-center-level analysis required? *(analyst)*

### Evidence

- Actuals carry `cost_center_code` (8 distinct across 6 departments). The **budget source has
  no cost-center concept at all**, so the two facts can only meet at DEPARTMENT level.
- The map therefore declares `dim_cost_center_fgl` as an **actuals-only** dimension, with
  `department_code` denormalized onto it as the rollup to the conformed level.

### Options

- **A.** Build `dim_cost_center_fgl` as declared. *(agent's proposal -- keeps cost-center
  analysis available for actuals-only reporting; costs one small dimension)*
- **B.** Collapse `cost_center_code` to a degenerate attribute on the fact. *(one fewer
  dimension; loses `cost_center_name` and clean cost-center grouping)*

---

## How to answer

Record your decision in `mappings/finance_gl_actuals/approval-decision-mapping-gate.md`,
naming yourself and the date, and add the matching `approvals[]` entries to
`readiness-status.yaml` (`{stage: source_ready}` for A, `{stage: mapping_ready}` for B/C).
This request records nothing. Spec 137's ratification on 2026-07-30 approved THE SPEC and
granted neither of these stage approvals.
