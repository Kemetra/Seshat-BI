# Approval Decision -- `finance-gl-model-integrity`

- **question_id:** `finance-gl-model-integrity`
- **request:** [`approval-request-model-integrity.md`](./approval-request-model-integrity.md)
- **selected_option:** `A1, B1, C1`
- **owner:** `Ahmed Shaaban (data_owner)`
- **date:** `2026-09-15`
- **rationale:**
- **status:** `answered`

## How this decision was given (recorded verbatim)

On 2026-09-15 the owner answered the open request with the exact line:

`A1, B1, C1 — Ahmed Shaaban, data-owner, 2026-09-15`

The agent transcribed that line. No rationale was supplied, so none is invented
here. This is not a blanket authorization: each letter names one option from
`approval-request-model-integrity.md`.

## Rulings

| Sub-decision | Ruling | Effect |
|---|---|---|
| **A / L19** -- time conformance | **A1.** Add `fiscal_period_sk` to `fct_gl_actuals_fgl` alongside daily `date_sk`. | Actuals may aggregate UP to the budget comparison grain (FR-010). Recorded on `dim_fiscal_period_fgl` in `docs/quality/conformed-dimension-map.yaml`. |
| **B / L21** -- `-1` hides unmatched keys | **B1.** Validate the natural-key lookup before coalescing: refuse when the source key is non-null but unmatched. | Entity FKs COALESCE to `-1` only for null/blank source keys. A present unmatched key stays NULL and is refused by the fact NOT NULL. Kit-wide, including the retail star. |
| **C / L22** -- contradictory department/cost-center | **C1.** Join `dim_cost_center_fgl` on both `cost_center_code` AND `department_code`. | A mismatched pair fails the lookup. Combined with B1 it is refused, not absorbed by `-1`. |

## artifacts_updated

- `mappings/finance_gl_actuals/unresolved-questions.md` -- rows L19, L21, L22: `Status` flipped `open` -> `answered`; `Resolution` filled
- `mappings/finance_gl_budget/unresolved-questions.md` -- row L19: `Status` flipped `open` -> `answered`; `Resolution` filled
- `mappings/finance_gl_actuals/readiness-status.yaml` -- `approvals[]` entry appended for the model-integrity ruling; `gold_ready` NOT flipped to `pass`
- `mappings/finance_gl_budget/readiness-status.yaml` -- `approvals[]` entry appended; `gold_ready` NOT flipped to `pass`
- `docs/quality/conformed-dimension-map.yaml` -- `dim_fiscal_period_fgl` recorded `conformed` across both finance stars (A1)
- `approval-request-model-integrity.md` -- status set to answered

## remaining_blockers

- stage evidence absent: `gold_ready` requires a live `retail validate` result before pass. No DSN in this workspace (`[PENDING LIVE PROFILE]`). Apply `0006` AND `0007` THEN `0008`, then `retail validate`.
- `finance_gl_budget` still cannot start `retail validate`: `validate_targets.load_targets()` requires `gold_star.date_dimension`, which this map omits because budget is fiscal-period grain (FR-010 forbids adding a daily `date_sk` to budget). A1 does not invent that date dim.

## What this decision does NOT grant

- It does not flip `gold_ready` to `pass`.
- It does not approve any metric contract.
- It does not authorize publishing or F016 writes.
