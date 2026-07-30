# Approval Decision -- `finance-gl-actuals-mapping-gate`

- **question_id:** `finance-gl-actuals-mapping-gate`
- **request:** [`approval-request-mapping-gate.md`](./approval-request-mapping-gate.md)
- **decided_by:** **Ahmed Shaaban** (repo owner; acting as `data-owner` and `analyst`)
- **decided_on:** `2026-07-30`
- **status:** `answered`

## How this decision was given (recorded verbatim, so the mechanism is auditable)

The owner answered EACH sub-decision individually on 2026-07-30, choosing from the options
the agent had presented in the request. The agent supplied the options, the evidence and a
recommendation; the owner supplied the choice.

**A correction is recorded here deliberately, because the first attempt got it wrong.** An
earlier attempt drafted this decision from a blanket authorization ("do all recomnded actions
i authorize you") and wrote approvals into the readiness records in the owner's name on that
basis. That was a self-granted approval with a human's name attached -- the exact failure this
repository's gate exists to prevent, occurring inside the feature built to test for it. Those
artifacts were reverted before being committed, and the rulings below were then obtained as
five explicit per-decision answers. The mechanism matters as much as the outcome: a blanket
authorization is not a ruling on a specific artifact.

Where a decision needed CONTENT rather than a choice between named options (OD-1 sign
convention, OD-2 baseline, OD-3 allocation), it was ruled separately on 2026-07-30 and is not
re-decided here.

**If any ruling below does not match the owner's intent, it is fully reversible**: nothing has
been executed against a database, nothing published, and no silver SQL authored yet.

## Rulings

| Sub-decision | Ruling | Effect |
|---|---|---|
| **A** -- RS1 source confirmation | **Confirmed.** The committed generator plus its byte-identical-regeneration test are accepted as provenance for the csv source (UTF-8 no BOM, comma delimiter, header row, LF newlines). | `source_ready` may pass; recorded as an `{stage: source_ready}` approval |
| **B** -- declared grain + star shape | **Approved.** Grain = one journal line within one journal entry; PK = (`journal_entry_id`, `line_id`), verified unique 5,000 = 5,000. Gold star `gold.fct_gl_actuals_fgl` + conformed `dim_account_fgl` / `dim_department_fgl` + actuals-only `dim_cost_center_fgl` + RC15 daily `dim_date_fgl`. | mapping gate CLEARED; silver SQL may now be authored |
| **C1** -- clearing accounts | **Option A.** Keep clearing rows through silver and gold (preserving the provable double-entry balance) and exclude them from P&L reporting by filtering `dim_account_fgl.account_type <> 'CLEARING'`. | every P&L metric contract must carry that filter; `unresolved-questions.md` Q2 answered |
| **C2** -- cost-center level | **Option A.** Build `dim_cost_center_fgl` as an actuals-only dimension, conforming to budget at DEPARTMENT level. | `unresolved-questions.md` Q3 answered |
| **D** -- HR1 conformance ruling | **Option A.** `dim_account_fgl` and `dim_department_fgl` are **`conformed`**, covering stars `finance_gl_actuals` and `finance_gl_budget`. | recorded in `docs/quality/conformed-dimension-map.yaml`; HR1's 2 errors cleared and its FR-005 check confirmed surrogate keys + shared attribute types agree across both stars |

## What this decision does NOT grant

- It does not advance any stage beyond `mapping_ready`. Silver, gold, semantic model and
  dashboard remain `not_started`.
- It does not approve any metric contract (that is a separate `metric_owner` decision).
- It does not authorize publishing. Power BI Service publishing stays out of scope and
  ADR-0018 remains `Proposed -- NOT ratified`.
- It does not perform the human report-authoring session (OD-5), which no approval can
  delegate.
