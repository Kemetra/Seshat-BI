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
- **Gate status:** `OPEN` -- the build is blocked until every row below is `answered`.

---

## Open questions (the build is blocked until these are `answered`)

| ID | Question | Why it blocks | Who must answer | Proposed default (if unanswered) | Status | Resolution |
|----|----------|---------------|-----------------|----------------------------------|--------|------------|
| Q1 | Is `customer_id` (`CUST_xx`, 25 distinct, pseudonymous) safe to keep + publish as `dim_customer`, or must it be dropped/hashed? | The customer dimension and any per-customer analysis cannot be built until the PII/publish-safety ruling is made. Deviates from RC4 (auto-drop). | governance | RC4 default = DROP before the BI layer. Agent RECOMMENDS keep (already a pseudonymous surrogate, no raw PII), pending sign-off. | `open` | |
| Q2 | What does a BLANK `discount_applied` mean (4,199 / 33.39%): unknown, or implicit False? | Every discount metric downstream depends on it; coercing blank->False silently would bias the discount rate. | analyst | RC5 default = blank stays NULL/`''` (unknown); do NOT coerce to False. | `open` | |
| Q3 | Is a transaction a SINGLE item (one row = one line), or a basket header that could have multiple lines elsewhere? | Confirms the grain semantics. PK is unique either way, but it affects whether `total_spent` is a line total or a basket total, and whether a line dimension is needed. | analyst | one row = one transaction at the lowest grain the source provides (RC1); single-item line assumed pending confirmation. | `open` | |
| Q4 | How to handle the 9.65% (1,213) rows with a missing `item`? | The product dimension build needs a rule: drop the rows, or land them on the `-1` unknown member of `dim_product`. | analyst | RC14 default = keep the rows; FK COALESCE to the `-1` unknown product member (do not drop sales). | `open` | |

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
  `RC1-RC16`; the `retail check` checker keeps `D1-D8`. No collision.
- **[RESOLVED -- ADR 0003] per-table mapping artifact location.** This table's five
  artifacts live together under `mappings/retail_store_sales/`.
- **[NEEDS CLARIFICATION: deferred `retail validate` live surface]** The live
  reconciliation (`reconciliation-report.md`) is filled from a live DB run after silver
  + gold exist. The `training` DB is reachable, so this can run once the build exists.

---

## See also

- Method: `../../docs/medallion-playbook.md` (Phase 2 + Phase 4); the stage:
  `../../docs/readiness/mapping-ready.md`.
- Defaults: `../../docs/decisions/0002-retail-cleaning-defaults.md` (RC1-RC16).
- Siblings: `source-profile.md`, `source-map.yaml`, `assumptions.md`,
  `reconciliation-report.md`; the readiness state: `readiness-status.yaml`.
