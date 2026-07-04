# Approval Decision -- `H9-time-intel`

- **question_id:** `H9-time-intel`  *(matches the open request `approval-request-H9-time-intel.md`)*
- **selected_option:** `D1=C, D2=A, D3=C`  *(the three sub-decisions the named human chose; transcribed, not picked by the console)*
- **owner:** `Ahmed Shaaban (metric_owner)`  *(the named human; metric_owner is the authority class the request required for these F009 metric-contract policy calls)*
- **date:** `2026-07-05`
- **rationale:** The named metric owner ruled the three planned time-intelligence
  contract policies as follows.
  - **D1 = C (defer same-store).** Same-store / comparable-store eligibility (A11)
    stays owner-pending; author only the two contracts that do not depend on A11
    now. Per the request's Impact analysis for option C: `ytd-net-sales` and
    `net-sales-growth` become authorable; `same-store-sales-growth` stays
    `[planned]` with its **Needs business definition** flag until A11 is ruled.
  - **D2 = A (sale date).** Every time contract compares on the transaction/sale
    date; posting and return dates are flagged as alternatives not used. Grounded
    in this table's confirmed single-date semantic (unresolved-questions.md Q3:
    one row = one single-item transaction; no separate posting/return date column).
  - **D3 = C (both baselines, YoY primary).** Contracts carry year-over-year /
    same-period-last-year as the PRIMARY comparison baseline and the immediately
    prior period as a NAMED SECONDARY baseline; each contract states which visuals
    use which. Consistent with the contracts' pre-existing "SPLY for seasonal
    retail" recommendation, extended to also expose prior-period.

## artifacts_updated

The committed artifacts this decision was written THROUGH to. This decision file is
the durable record (written first); the write-throughs below were applied idempotently.

- `mappings/retail_store_sales/unresolved-questions.md` -- a pointer note added under
  "Kit-level open decisions" recording that H9-time-intel is `answered` here. (The
  Q1-Q4 table is the mapping-stage gate, already `CLEARED`; per the request's own
  `artifacts_to_update` clause this semantic-model-stage decision is recorded off that
  table rather than adding Q-rows to a closed, different-stage gate.)
- `mappings/retail_store_sales/readiness-status.yaml` -- `approvals[]` entry appended:
  `stage: semantic_model_ready`, `owner: "Ahmed Shaaban (metric_owner)"`, `at: 2026-07-05`,
  framed as a POLICY AMENDMENT that unblocks future F009 authoring (NOT a re-pass of
  the already-`pass` stage; its original 5-contract evidence is untouched).

## remaining_blockers

- **D1 = C leaves A11 open:** `same-store-sales-growth` stays `[planned]` /
  **Needs business definition** until the same-store eligibility rule (A11) is ruled
  in a later decision. This is the owner's explicit choice, not a defect.
- **Contract internals not authored by this record:** flipping
  `ytd-net-sales` / `net-sales-growth` from `[planned]` to `[seeded]` (authoring the
  contract files + INDEX/domain rows, and the H6/H10 guards they unblock) is a
  SEPARATE F009 contract-authoring step -- explicitly NOT done by this console
  (per the request's `artifacts_to_update_after_decision`). It requires the owner to
  fire that step.
- **semantic_model_ready stays `pass` on its original evidence.** This ruling is an
  additive policy amendment; it does not re-pass, and does not touch the standing
  `publish_ready = blocked` (the DiscountedTransactionRate re-approval, unrelated).

## The `pass`-flip rule (mechanical, gated -- never discretionary)

No stage flips on this decision. `semantic_model_ready` is already `pass` on its
original 5-contract evidence; this amendment records a policy ruling that unblocks
future contract authoring, and adds no new `pass`. The new time-intelligence contracts
will carry their own `[planned] -> [seeded]` transition when the F009 authoring step
runs against this ruling.

## Conflict + amendment posture

- **Not a contradiction of a prior approval.** The prior `semantic_model_ready`
  approval (2026-06-25) covered five different, existing contracts; this ruling covers
  three new, planned contracts. Recorded as an AMENDMENT with its own `approvals[]`
  entry and surfaced here -- never a silent re-pass (per the template's amendment
  posture for an already-`pass` stage).

## See also

- The decision package this answers: `mappings/retail_store_sales/approval-request-H9-time-intel.md`.
- The ambiguities ruled / left open: `skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md` (A3 ruled = sale date; A11 left open).
- The planned contracts this unblocks for F009 authoring: `skills/retail-kpi-knowledge/contracts/` (`net-sales-growth.md`, `ytd.md`; `same-store-sales-growth.md` stays planned).
- The stage state: `mappings/retail_store_sales/readiness-status.yaml` (`approvals[]`).
- The console verb + boundary: `.claude/skills/approval-console/SKILL.md`, `docs/tools/approval-console.md`.
