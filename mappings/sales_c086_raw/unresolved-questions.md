# Unresolved questions -- `sales_c086_raw`

> Filled instance for `bronze.sales_c086_raw` (C086 pharmacy branch sales export).
> The open questions that BLOCK the build -- the decisions the agent cannot make alone.
> No `silver.*` SQL is written until every row below is `answered` (or its proposed
> default is explicitly accepted by the named owner) and `Gate status: CLEARED`.
> The agent recommends; the owner decides. ASCII only.
>
> BACK-FILLED 2026-07-18: this mirror is reconstructed from the rulings already recorded
> in `readiness-status.yaml` `approvals[]` (all dated 2026-07-16). It was flagged as a known
> documentation gap in the publish_ready evidence ("unresolved-questions.md not found") and is
> authored here to close that gap and satisfy the governed dbt working-set requirement. Every
> question below traces to an existing named-human approval; NO new decision is introduced.

---

- **Table id:** `sales_c086_raw`
- **Date raised:** 2026-07-16 (retroactively documented 2026-07-18)
- **Raised by:** agent (`retail-onboard-table` -> `source-mapping`)
- **Maps to playbook phases:** Phase 2 (decision points) + Phase 4 (review gate)
- **Gate status:** `CLEARED` -- all questions answered 2026-07-16 (data owner Ahmed Shaaban).
  Approvals recorded in `readiness-status.yaml` `approvals[]` (source_ready x4, mapping_ready,
  silver_ready x2).

---

## Open questions (the build is blocked until these are `answered`)

| ID | Question | Why it blocks | Who must answer | Proposed default (if unanswered) | Status | Resolution |
|----|----------|---------------|-----------------|----------------------------------|--------|------------|
| Q1 | Which column is the grain PK -- `billing_document` or `reference_no` (each with `item_no`)? | The whole model's grain + every downstream join depends on it; a wrong PK silently fans out or collapses rows. | governance | RC2: pick the uniquely-formatted candidate. Agent RECOMMENDS `(reference_no, item_no)` -- `reference_no` is uniform (C086 + 10 digits, embeds site code); `billing_document` mixes a '0'-prefix (215,297) and letter-'O'-prefix (33,809) split that matches the blank-`fi_document_no` population, so it conflates two document/channel types. | `answered` | 2026-07-16 (data owner): PK = `(reference_no, item_no)`. `billing_document` REJECTED (format-split evidence). Re-proven unique on transformed silver (248,593 = 248,593 distinct, 0 null). |
| Q2 | Is landed `net_sales` a trusted measure, or must net sales be derived from first principles? | Every sales/margin metric depends on which "sales" number is authoritative; carrying an unreliable column forward biases all of them. | analyst | RC9: verify the identity before trusting a landed measure. Agent RECOMMENDS REJECT landed `net_sales` -- `gross_sales+dis_tax+add_dis-tax==net_sales` holds on only 90.4%; 7 alternative formulas tested, none better; 80.3% of mismatches are material (non-rounding), uniform across `billing_type`. | `answered` | 2026-07-16 (data owner): landed `net_sales` UNRELIABLE, REJECTED as a derivation source. Later CLOSED: there is NO net-sales measure in the model; `gross_sales` is the sole standing 'sales' measure. Any future net-sales metric is a fresh ruling. |
| Q3 | What do blank `item_cluster` (32.01%) and blank `assignment` (46.88%) mean -- unknown, or a real 'none' category? And what to do with `certification` (67.96% blank)? | The product/attribute handling depends on it; treating unknown as a real category, or vice versa, misclassifies rows in every breakdown. | analyst | RC5/RC6: blank stays unknown unless proven structural. Agent MEASURED `item_cluster` as stable-per-material and `assignment` as credit-account-correlated, but recommends the owner rule the semantics. | `answered` | 2026-07-16 (data owner): `item_cluster` blank -> UNKNOWN/MISSING; `assignment` blank -> UNKNOWN/MISSING (owner ruled unknown, not structural not-applicable, despite the measured patterns); `certification` DROPPED entirely (division-based population pattern not clean enough to rule; owner chose to drop rather than guess). |
| Q4 | How must the PII/near-PII columns be handled: `person_name`, `customer_name`, `insurance_tel`, `insurance_no`? | The customer/staff dimensions and any publish cannot be built until publish-safety is ruled. Deviates from RC4 (auto-drop). | governance | RC4 default = DROP before the BI layer. Agent profiled each and recommends per-column dispositions pending sign-off. | `answered` | 2026-07-16 (data owner, FINAL -- clears source_ready): `person_name` (staff/employee) -> MASK/PSEUDONYMIZE (md5 on `staff_name_masked`, no raw name in silver); `customer_name` (predominantly B2B/institutional) -> LOW RISK, KEEP AS-IS; `insurance_tel` + `insurance_no` (genuine third-party data) -> DROP ENTIRELY from every layer. |
| Q5 | How is a RETURN identified -- by measure sign, or by an authoritative column? | Returns must net in without double-counting; sign-alone misclassifies rows and a wrong rule corrupts every sales total. | data-owner | RC8: prefer an authoritative column over sign. Agent RECOMMENDS deriving `is_return` from `billing_type` (Arabic `mrtja` values); sign-alone would misclassify 2,030 rows. | `answered` | 2026-07-16 (data owner): `is_return` derived from `billing_type` (RC8). Ruled billing_type be TRANSLATED to English (replacing Arabic). BUG CAUGHT: Arabic-prefix match missed 'Pick-Up Order Return' (376 rows already English); fixed by deriving `is_return` from the translated English label (`LIKE '%Return%'`) in a shared CTE. Rate: 12,280/248,593 (4.94%) post-filter. |
| Q6 | Which rows are OUT OF SCOPE for a retail sales-of-goods fact? | A fact of "product sales" must exclude non-sales line items, or every total is inflated by fees/services. | data-owner | RC-scope: keep all rows unless proven out of scope. Agent inspected the low-volume divisions and recommends excluding non-product-sale ones. | `answered` | 2026-07-16 (data owner): EXCLUDE 513/249,106 (0.21%) rows where `division IN ('ARCHIVE','AUX','','EL EZABY SERVICES')`. Each inspected: ARCHIVE (retired/gift lines), AUX (misc), blank (missing), EL EZABY SERVICES (498 = injection fees / WhatsApp / SPECIAL SERVICE -- not product sales). Silver row count is now 248,593, the deliberate row-parity deviation from bronze. |

> Do not delete answered rows -- flip `Status` to `answered` and fill `Resolution` so
> review sees the audit trail.

### Categories considered (raised above, or adopted with no ambiguity)

- **Grain ambiguity** (RC1/RC2): raised as Q1 -- genuinely ambiguous between two candidate
  PK columns, resolved by the format-split evidence. Grain = one row = one billing-document line item.
- **PII** (RC4; governance): raised as Q4 (`person_name`, `customer_name`, `insurance_tel`, `insurance_no`).
- **Business-rollup mappings** (RC11; analyst): none invented -- `material`->`category`/`division`/`brand`
  etc. are clean source attributes, not analyst-supplied rollups.
- **Sentinel-vs-null** (RC5/RC6): DEVIATION ruled -- money/quantity stay NULL on blank (protects SUM);
  EVERY text column (incl. natural keys) uses sentinel `'UNKNOWN'`, a deliberate extension beyond RC6's
  grouping-dim-only scope. Blank semantics for specific columns raised as Q3.
- **Returns identification** (RC8; data-owner): raised as Q5. Returns exist and are identified from the
  authoritative `billing_type` column, never from a measure sign.
- **Hierarchy multi-parent** (RC12): DEVIATION -- `mat_group`/`mat_group_2` dropped rather than kept as a
  flat denorm attribute (owner ruling in mapping_ready); no multi-parent rollup invented.
- **Scope filter** (retail sales-of-goods fact): raised as Q6 -- the 513-row division exclusion.

---

## Kit-level open decisions (inherited)

- **[RESOLVED -- ADR 0003] per-table mapping artifact location.** This table's artifacts live together
  under `mappings/sales_c086_raw/`.
- **[RESOLVED -- ADR 0004] readiness state.** Per-table seven-stage status in `readiness-status.yaml`.
- **[N/A for this back-fill] downstream time-intelligence / YTD contracts.** This table has ONE approved
  metric contract (`TotalSales`); no time-intelligence or YTD contracts were authored, so the `_rss`
  H9/YTD kit decisions do not apply here. Future metrics each need their own contract + owner approval.

---

## See also

- Defaults: `../../docs/decisions/0002-retail-cleaning-defaults.md` (RC1-RC16).
- Siblings: `source-profile.md`, `source-map.yaml`, `readiness-status.yaml`; the metric contract:
  `metrics/TotalSales.yaml`; the handoff pack: `handoff/bi-handoff-pack.md`.
