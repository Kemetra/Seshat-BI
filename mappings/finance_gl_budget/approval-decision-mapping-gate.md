# Approval Decision -- `finance-gl-budget-mapping-gate`

- **question_id:** `finance-gl-budget-mapping-gate`
- **request:** [`approval-request-mapping-gate.md`](./approval-request-mapping-gate.md)
- **decided_by:** **Ahmed Shaaban** (repo owner; acting as `data-owner`)
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
| **A** -- RS1 source confirmation | **Confirmed.** Generator + determinism test accepted as provenance for the csv source. | `source_ready` may pass; `{stage: source_ready}` approval recorded |
| **B** -- declared grain, `budget_version` as identity | **Approved.** Grain = one budgeted amount per account per department per fiscal quarter per budget version; 5-part PK verified unique (2,688 = 2,688), and dropping `budget_version` collides exactly 2:1 -- so a version ADDS rows and never overwrites a prior version (FR-011). Second fact `gold.fct_gl_budget_fgl` at quarter grain, sharing the two conformed dims, keyed on `dim_fiscal_period_fgl`, with the RC15 deviation accepted. | mapping gate CLEARED; silver SQL may now be authored |
| **C** -- 241 budgeted combos with no actuals | **Option A.** Expected business state. They surface as a report exception (the mirror of the Missing Budget Flag metric), never as a mapping failure or data-quality blocker. | `unresolved-questions.md` Q3 answered. Consequence for the gate: a check that REFUSES these rows is **over-refusing**, which spec 137 FR-023 counts as a failure -- variant D12 exists to observe exactly that |
| **D** -- HR1 conformance ruling | **Option A** (`conformed`), ruled once for both stars in the actuals decision record. | see `mappings/finance_gl_actuals/approval-decision-mapping-gate.md` |

## Already ruled elsewhere (not re-decided here)

| Ref | Ruling (Ahmed Shaaban, 2026-07-30) |
|---|---|
| OD-1 | revenue and expenses both PRESENT as positive magnitudes; polarity via `direction_of_good` |
| OD-2 | the variance baseline is `budget_version = ORIGINAL` |
| OD-3 | no monthly view derived from the quarterly budget; such a request is refused |

## What this decision does NOT grant

No stage beyond `mapping_ready`; no metric contract; no publishing; and not the human
report-authoring session (OD-5).
