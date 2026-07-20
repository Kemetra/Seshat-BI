# Unresolved questions -- `retail_store_sales`

> Filled instance for `bronze.retail_store_sales` (Kaggle retail-store-sales dirty).
> The open questions that BLOCK the build -- the decisions the agent cannot make alone.
> No `silver.*` SQL is written until every row below is `answered` (or its proposed
> default is explicitly accepted by the named owner) and `Gate status: CLEARED`.
> The agent recommends; the owner decides. ASCII only.

---

- **Table id:** `retail_store_sales`
- **Date raised:** 2026-06-25
- **Raised by:** agent (`retail-onboard-table` -> `source-mapping`)
- **Maps to playbook phases:** Phase 2 (decision points) + Phase 4 (review gate)
- **Gate status:** `CLEARED` -- all four questions answered 2026-06-25 (data owner accepted
  the agent recommendations). Approval recorded in `readiness-status.yaml` `approvals[]`.

---

## Open questions (the build is blocked until these are `answered`)

| ID | Question | Why it blocks | Who must answer | Proposed default (if unanswered) | Status | Resolution |
|----|----------|---------------|-----------------|----------------------------------|--------|------------|
| Q1 | Is `customer_id` (`CUST_xx`, 25 distinct, pseudonymous) safe to keep + publish as `dim_customer`, or must it be dropped/hashed? | The customer dimension and any per-customer analysis cannot be built until the PII/publish-safety ruling is made. Deviates from RC4 (auto-drop). | governance | RC4 default = DROP before the BI layer. Agent RECOMMENDS keep (already a pseudonymous surrogate, no raw PII), pending sign-off. | `answered` | 2026-06-25 (data owner): KEEP `customer_id` as `dim_customer` -- it is a pseudonymous surrogate, no raw PII. RC4 deviation stands (recorded in assumptions.md). |
| Q2 | What does a BLANK `discount_applied` mean (4,199 / 33.39%): unknown, or implicit False? | Every discount metric downstream depends on it; coercing blank->False silently would bias the discount rate. | analyst | RC5 default = blank stays NULL/`''` (unknown); do NOT coerce to False. | `answered` | 2026-06-25 (data owner): blank = UNKNOWN -> NULL in silver (RC5). Do NOT coerce to False; discount metrics exclude unknowns. |
| Q3 | Is a transaction a SINGLE item (one row = one line), or a basket header that could have multiple lines elsewhere? | Confirms the grain semantics. PK is unique either way, but it affects whether `total_spent` is a line total or a basket total, and whether a line dimension is needed. | analyst | one row = one transaction at the lowest grain the source provides (RC1); single-item line assumed pending confirmation. | `answered` | 2026-06-25 (data owner): one row = one single-item transaction; `total_spent` is the line total. No separate basket/line dimension. |
| Q4 | How to handle the 9.65% (1,213) rows with a missing `item`? | The product dimension build needs a rule: drop the rows, or land them on the `-1` unknown member of `dim_product`. | analyst | RC14 default = keep the rows; FK COALESCE to the `-1` unknown product member (do not drop sales). | `answered` | 2026-06-25 (data owner): KEEP the rows; FK COALESCE the missing `item` to the `-1` unknown member of `dim_product` (RC14). Do not drop sales. |

> Do not delete answered rows -- flip `Status` to `answered` and fill `Resolution` so
> review sees the audit trail.

### Categories considered (raised above, or adopted with no ambiguity)

- **Grain ambiguity** (RC1/RC2): PK `transaction_id` is unique on the data (12,575 =
  12,575, 0 null) -- grain is NOT ambiguous mechanically. The only semantic openness
  (single-item vs basket) is raised as Q3. Not a hard mechanical blocker.
- **PII** (RC4; governance): raised as Q1 (`customer_id`).
- **Business-rollup mappings** (RC11; analyst): none needed -- `category` is a clean
  source attribute (8 values), not an analyst-supplied rollup; `item`->`category` is 1:1
  on the data. No rollup invented.
- **Sentinel-vs-null** (RC5/RC6): all columns adopt the RC5 `''`->NULL baseline; no
  grouping sentinel proposed. The `discount_applied` blank is Q2 (not auto-coerced).
- **Returns identification** (RC8; data-owner): N/A -- NO returns in this source
  (confirmed with the data owner: returns live in a separate figure). Recorded as a
  deviation in `assumptions.md`; not an open question.
- **Hierarchy multi-parent** (RC12): `item`->`category` is a clean 1:1 (0 multi-parent);
  flat denorm dim_product. No open question.

---

## Kit-level open decisions (inherited)

- **[RESOLVED -- feature 002] D-namespace disambiguation.** ADR cleaning defaults are
  `RC1-RC16`; the `seshat check` checker keeps `D1-D8`. No collision.
- **[RESOLVED -- ADR 0003] per-table mapping artifact location.** This table's five
  artifacts live together under `mappings/retail_store_sales/`.
- **[NEEDS CLARIFICATION: deferred `retail validate` live surface]** The live
  reconciliation (`reconciliation-report.md`) is filled from a live DB run after silver
  + gold exist. The `training` DB is reachable, so this can run once the build exists.
- **[ANSWERED -- 2026-07-05 -- H9-time-intel time-intelligence contract policies]** The
  three planned time-intelligence metric-contract policies were ruled by the named
  metric owner: **D1 = C** (defer same-store; A11 stays open), **D2 = A** (sale date),
  **D3 = C** (both baselines, YoY primary). Recorded off this mapping-stage table (which
  is `CLEARED`) in the durable decision record `approval-decision-H9-time-intel.md`
  answering `approval-request-H9-time-intel.md`; a `semantic_model_ready` policy-amendment
  entry is in `readiness-status.yaml` `approvals[]`. **`net-sales-growth` is now Seeded**
  (D2+D3 were its only open decisions; 2026-07-05).
  `same-store-sales-growth` stays `[planned]` (A11 unruled).
- **[ANSWERED -- 2026-07-05 -- YTD-year-start (the ambiguity H9 did not cover)]** The
  `ytd-net-sales` year-boundary policies were ruled by the named metric owner: **E1 = A**
  (calendar year; no fiscal calendar; seedable on the existing date table), **E2 = C**
  (both partial-period comparisons -- to-date-vs-to-date primary, full-prior-year
  secondary; mirrors D3=C). Recorded in `approval-decision-YTD-year-start.md` answering
  `approval-request-YTD-year-start.md`; a `semantic_model_ready` policy-amendment entry
  is in `readiness-status.yaml` `approvals[]`. **`ytd-net-sales` is now unblocked** for a
  SEPARATE F009 seed step (author `ytd.md` [planned] -> [seeded] resolving to E1=A + E2=C;
  not done by the console). Unblocks the YTD portion of H6/H10.

---

## See also

- Method: `../../docs/medallion-playbook.md` (Phase 2 + Phase 4); the stage:
  `../../docs/readiness/mapping-ready.md`.
- Defaults: `../../docs/decisions/0002-retail-cleaning-defaults.md` (RC1-RC16).
- Siblings: `source-profile.md`, `source-map.yaml`, `assumptions.md`,
  `reconciliation-report.md`; the readiness state: `readiness-status.yaml`.
