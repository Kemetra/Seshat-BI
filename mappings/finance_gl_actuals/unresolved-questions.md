# Unresolved questions -- `finance_gl_actuals`

Filled instance of `templates/unresolved-questions.md` (ADR 0003 location). The open decisions
that BLOCK the build -- the things the agent cannot decide alone. ASCII only.

- **Table id:** `finance_gl_actuals`
- **Date raised:** 2026-07-30
- **Raised by:** agent
- **Maps to playbook phases:** Phase 2 (decision points) + Phase 4 (review gate)
- **Gate status:** `OPEN` -- Q3 is unanswered, and the source itself still needs the RS1
  owner confirmation. No `silver.*` SQL may be authored until the gate is CLEARED by a named
  human (spec 137 OD-4).

---

## Open questions

| ID | Question | Why it blocks | Who must answer | Proposed default (if unanswered) | Status | Resolution |
|----|----------|---------------|-----------------|----------------------------------|--------|------------|
| Q1 | How are revenue and expense signs PRESENTED in reporting -- signed accounting convention, or positive magnitudes with polarity carried separately? | Every money measure, variance measure and card on the report reads differently; a wrong choice silently inverts variance interpretation | analyst | positive magnitudes, polarity via each contract's `direction_of_good` | `answered` | **2026-07-30, Ahmed Shaaban (owner): both positive; polarity via `direction_of_good`, never the arithmetic sign.** Implemented as the derived `amount` column; landed debit/credit kept intact. Spec 137 OD-1 |
| Q2 | Does P&L reporting EXCLUDE clearing accounts, and is filtering `dim_account_fgl.account_type <> 'CLEARING'` the right mechanism? | Clearing lines are 2,500 of 5,000 rows. Including them double-counts every entry in any P&L total; dropping them at silver would destroy the provable double-entry balance | data-owner | keep the rows through silver+gold; exclude in reporting via `account_type <> 'CLEARING'` | `open` | |
| Q3 | Is cost-center-level analysis required for actuals, given the budget has no cost-center concept? | Determines whether `dim_cost_center_fgl` is built at all, or whether `cost_center_code` collapses to a degenerate attribute on the fact | analyst | build the actuals-only `dim_cost_center_fgl`; conform to budget at DEPARTMENT level | `open` | |

> Answered rows are never deleted -- `Status` flips and `Resolution` records the decision,
> the date, and who made it.

### Note on Q2's proposed default

The data corroborates the exclusion independently rather than the exclusion being a
convenience: of 1,199 actual (year, quarter, account, department) combos, 96 have no budget
row, and **all 96 are clearing-account combos** (2 accounts x 6 departments x 8 quarters).
Once clearing is excluded, P&L actuals coverage against budget is complete -- 0 gaps. The agent
proposes the mechanism; the owner confirms the business semantics.

---

## Categories considered (none left unconsidered)

The template requires each recurring decision class to be either raised above or explicitly
recorded as adopted/N-A here.

| Category | Disposition |
|---|---|
| **Grain ambiguity** (RC1/RC2) | **No ambiguity.** The composite PK is verified unique on the data (5,000 rows = 5,000 distinct; `journal_entry_id` alone is 2,500). Recorded in `assumptions.md` as RC1/RC2 adopted |
| **PII judgment calls** (RC4, governance) | **N/A -- no PII exists.** No name, contact, address, person identifier, or free-text field capable of carrying one; the finest entity in the source is a cost center. `description` is generated from the account name. Verified column-by-column in `source-profile.md` |
| **Sentinel-vs-null** (RC5/RC6) | **Nothing to decide.** 0 blank cells across all 10 columns, so no grouping sentinel is introduced. RC5 adopted as the baseline |
| **Returns identification** (RC8, data-owner) | **N/A -- recorded as an RC8 deviation.** A P&L journal extract carries no transaction-type, reversal, or return-marker column, and every line is a posting. `is_return` is NOT derived (deriving it from the amount sign would be exactly the RC8 anti-pattern). Data fact in `assumptions.md` |
| **Business-rollup mappings** (RC11, analyst) | **N/A.** No rollup was requested, and none is invented. The account hierarchy that DOES exist is a source-supplied `parent_account_code`, not an analyst-supplied grouping |
| **Hierarchy multi-parent** (RC12) | **Clean tree.** `parent_account_code` gives one parent per account (verified: 4 distinct parents, 5 roots with a blank parent); flat denorm levels adopted |

**Genericity observation (ledger row L3).** Two of the six mandatory categories -- Returns
identification and Business-rollup mappings -- are retail concepts with no finance analogue,
and a third (hierarchy multi-parent) maps only awkwardly onto a chart of accounts. Meanwhile
the categories this domain actually needed are absent from the list: **comparison-baseline
choice**, **sign/presentation convention**, and **cross-grain allocation policy**. All three
were raised anyway (Q1 here; OD-2 and OD-3 on the budget table), so nothing went unasked --
but they were raised because the domain demanded them, not because the template prompted for
them.

---

## See also

- `source-profile.md` -- the measured numbers these questions reference
- `source-map.yaml` -- the machine-readable decisions
- `assumptions.md` -- ADR defaults adopted vs deviated, with triggering data facts
- `readiness-status.yaml` -- stage statuses, blockers, and the (empty) `approvals[]`
- `docs/worked-examples/finance-gl-genericity-ledger.md` -- obstructions met during this walk
