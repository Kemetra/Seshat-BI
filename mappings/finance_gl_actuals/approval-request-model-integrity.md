# Approval Request -- `finance-gl-model-integrity`

**Raised**: 2026-08-07, from the PR #596 review of spec 137.

**Covers**: `finance_gl_actuals` and `finance_gl_budget` jointly -- each sub-decision
below affects the shared gold star (`0008_create_gold_finance_gl_star.sql`), so they
cannot be ruled per-table.

**Status**: OPEN. No option below has been chosen. The agent raised these and may not
resolve any of them (Principle V, `never_self_grant_approval`; and for sub-decision A,
`docs/quality/conformed-dimension-map.yaml`'s own header, which states a cross-star
dimension ruling "is a Principle-V human modelling judgment; HR1 never decides it").

## Decision needed (one sentence)

Three model-integrity questions that the finance domain surfaced and the retail worked
example never could, each blocking a different downstream stage.

---

## Sub-decision A -- the two facts share no conformed TIME dimension *(data-owner / modeller)*

**Ledger**: L19, L19b. **Blocks**: `finance_gl_budget` Gold Ready; T042 and T044.

### Evidence

- `fct_gl_actuals_fgl` is keyed to `dim_date_fgl` (daily `date_sk`).
  `fct_gl_budget_fgl` is keyed to `dim_fiscal_period_fgl` (`fiscal_period_sk`).
  **Neither time dimension filters both facts.**
- Slice the required Actual-vs-Budget trend by quarter and one series repeats its
  unfiltered total for every period -- the spec's central deliverable does not work.
- FR-009 names `dim_date` among the dimensions that MUST be conformed.
- `docs/quality/conformed-dimension-map.yaml` carries a ruling (Ahmed Shaaban,
  2026-07-30) for exactly two names: `dim_account_fgl` and `dim_department_fgl`.
  **No time dimension was ever ruled.**
- Second consequence, verified: `validate_targets.load_targets()` unconditionally
  requires `gold_star.date_dimension` (`src/seshat/validate_targets.py:183`), which the
  budget map omits by design. Loading it raises
  `ValueError: missing required 'date_dimension' in gold_star`, so `retail validate`
  exits before running a single check and the table cannot reach Gold Ready.

### Options

| | Option | Consequence |
| --- | --- | --- |
| **A1** | Add `fiscal_period_sk` to `fct_gl_actuals_fgl` alongside its daily `date_sk` | FR-010 permits aggregating actuals UPWARD to the budget comparison grain, so this direction is allowed. Changes the authored gold SQL. |
| **A2** | Introduce a shared period bridge between `dim_date_fgl` and `dim_fiscal_period_fgl` | Adds a modelling construct the kit has no precedent for. |
| **A3** | Rule the two time dimensions `distinct` and accept no cross-fact time slice | Contradicts the spec's own required trend visual. |

**NOT an option**: adding a daily `date_sk` to the budget fact. That is downward
disaggregation of budget, which **FR-010 forbids** without a named human approval.

### What is being asked

Choose A1, A2 or A3, and record it as a `conformed-dimension-map.yaml` entry naming a
human and a date. Whichever is chosen also settles whether budget needs validator
support, so this single ruling clears both L19 and L19b.

---

## Sub-decision B -- the `-1` unknown member hides the D1/D2 refusal *(data-owner / modeller)*

**Ledger**: L21. **Blocks**: honest live validation of D1/D2.

### Evidence

- The defect matrix requires D1 (row references an absent account) and D2 (unknown
  department) to **`refuse`**.
- `COALESCE(da.account_sk, -1)` rewrites a FAILED natural-key lookup into the valid `-1`
  member the migration itself inserts.
- `check_orphan_fks` is a plain `LEFT JOIN <dim> d ... WHERE d.<pk> IS NULL`
  (`src/seshat/validate.py:236-239`). `-1` is a real dimension row, so the join always
  succeeds and the orphan is **invisible**. A live run would report PASS for the wrong
  reason -- worse than a missing check.
- This is **not** specific to this example: the same pattern is kit-wide, identical in
  `0004_create_gold_retail_store_sales_star.sql:132-135`, and declared here through
  `has_unknown_member: true`.
- Root cause: the convention conflates a legitimately **NULL** source value (retail's
  9.65% NULL item, where collapsing IS correct) with an unknown-but-**PRESENT** natural
  key (which must refuse).

### Options

| | Option | Consequence |
| --- | --- | --- |
| **B1** | Validate the natural-key lookup before coalescing -- refuse when the source key is non-null but unmatched | Changes the kit-wide gold-star convention, affecting the retail star too. |
| **B2** | Preserve evidence of the unresolved reference (reject table or an `is_unresolved` column) so `check_orphan_fks` can see it | A new convention this kit does not have. |
| **B3** | Extend the validator to distinguish sentinel-assigned FKs from genuine matches | Edits a kit module; T025 forbids it inside this spec. |

### What is being asked

Choose B1, B2 or B3, or rule that the convention stands and D1/D2 are permanently
uncatchable by the shipped checks. The defect matrix now reads `[NO CHECK EXISTS]` for
both, so nothing false is committed either way.

---

## Sub-decision C -- independent dim lookups admit a contradictory pair *(data-owner / modeller)*

**Ledger**: L22. **Matrix variant**: D14 (added by this review).

### Evidence

- An actuals row can carry a VALID `department_code` and a VALID `cost_center_code`
  belonging to a **different** department. Both lookups resolve independently.
- `dim_cost_center_fgl` carries `department_code` as a flat denormalized rollup
  (`0008_create_gold_finance_gl_star.sql:98`), so the fact's `department_sk` can
  contradict the cost centre's own department.
- Both FKs are valid, so `check_orphan_fks` -- which only compares each FK against its
  own dimension's PK -- cannot see it. A report grouped by department disagrees with the
  rollup, silently.
- Why it is new: this is a **hierarchical** dimension relationship. The retail star's
  four dimensions are mutually independent, so no committed example needed a
  cross-dimension consistency check and the matrix had no row for the failure class.

### Options

| | Option | Consequence |
| --- | --- | --- |
| **C1** | Join `dim_cost_center_fgl` on both `cost_center_code` AND `department_code` | Contains the fix inside this example's SQL; a mismatched pair then falls to the `-1` member, which interacts with sub-decision B. |
| **C2** | Reject mismatched pairs before loading Gold | Introduces a rejection convention the kit does not have. |
| **C3** | Accept it and document that cross-dimension integrity is not checked | Honest, but leaves D14 permanently uncatchable. |

### What is being asked

Choose C1, C2 or C3. Note C1 and sub-decision B interact: routing a mismatched pair to
`-1` reproduces exactly the invisibility B describes.

---

## What the agent did NOT do

- Did not choose any option above.
- Did not edit `docs/quality/conformed-dimension-map.yaml`.
- Did not change the gold-star `-1` convention or the shipped validator.
- Did not mark any affected stage `pass`.

The only changes made from these findings were **truthfulness corrections** to committed
documents: the defect matrix's Observed column now reads `[NO CHECK EXISTS]` for D1/D2
instead of `[PENDING LIVE PROFILE]`, its "5 of 7 covered" claim is corrected to "3 of 7",
and D14 was added. Those record what is true today; they decide nothing.
