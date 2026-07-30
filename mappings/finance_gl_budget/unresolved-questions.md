# Unresolved questions -- `finance_gl_budget`

Filled instance of `templates/unresolved-questions.md` (ADR 0003 location). ASCII only.

- **Table id:** `finance_gl_budget`
- **Date raised:** 2026-07-30
- **Raised by:** agent
- **Maps to playbook phases:** Phase 2 (decision points) + Phase 4 (review gate)
- **Gate status:** `OPEN` -- Q3 is unanswered and the source still needs the RS1 owner
  confirmation. No `silver.*` SQL until a named human clears the gate (spec 137 OD-4).

---

## Open questions

| ID | Question | Why it blocks | Who must answer | Proposed default (if unanswered) | Status | Resolution |
|----|----------|---------------|-----------------|----------------------------------|--------|------------|
| Q1 | Which budget version is the BASELINE for variance -- `ORIGINAL`, a later revision, or both as separate metrics? | Every variance measure changes meaning. With 2 versions in the source, an unpinned query sums the plan TWICE (268.3M instead of 136.4M) | analyst | `ORIGINAL` -- the plan of record | `answered` | **2026-07-30, Ahmed Shaaban (owner): `ORIGINAL`.** `REVISION-1` stays in the source to exercise version identity (FR-011) and variant D10, and never moves the headline measures. Spec 137 OD-2 |
| Q2 | May a MONTHLY view be derived from the quarterly budget, and if so under what allocation policy? | A monthly budget number does not exist in the source; any derivation invents precision the plan never had | analyst | refuse -- no allocation policy exists and none may be inferred | `answered` | **2026-07-30, Ahmed Shaaban (owner): NO.** Monthly actuals may display; budget and variance stay quarter-grain. A monthly-budget request is refused with the reason named (variant D11). Spec 137 OD-3 |
| Q3 | Are the 241 budgeted (quarter, account, department) combos with NO posted actuals expected business states, or do they indicate missing actuals data? | Determines whether they surface as a report exception or as a data-quality blocker -- and whether the gate refusing them would be correct or an over-refusal | data-owner | expected business state; surface as a report exception, never as a mapping failure | `open` | |

> Answered rows are never deleted -- `Status` flips and `Resolution` records the decision, the
> date, and who made it.

### Note on Q3

This is the mirror of the Missing Budget Flag metric and it matters for correctness of the
GATE, not just the report. If the proposed default is right, a gate that refuses these rows is
**over-refusing**, which spec 137 FR-023 counts as a failure rather than as safety. Variant D12
is built to observe exactly this behaviour. The agent cannot decide whether a budgeted line
with no activity is normal for this business -- only the data owner can.

---

## Categories considered (none left unconsidered)

| Category | Disposition |
|---|---|
| **Grain ambiguity** (RC1/RC2) | **Resolved by measurement.** The 5-part key is unique (2,688 = 2,688); dropping `budget_version` collides exactly 2:1 (1,344 of 2,688), which is the data-side proof that a version is part of IDENTITY, not an attribute (FR-011) |
| **PII judgment calls** (RC4, governance) | **N/A -- no PII.** The finest entity is a department; there is no person-level data of any kind |
| **Sentinel-vs-null** (RC5/RC6) | **Nothing to sentinel** (0 blanks). One distinction IS load-bearing though: `budget_amount = 0` means "nothing planned" while an ABSENT ROW means "no plan exists". FR-015 requires those to stay distinguishable, so a missing row is never backfilled with 0 |
| **Returns identification** (RC8, data-owner) | **N/A -- recorded as an RC8 deviation.** A plan has no transaction type and no postings |
| **Business-rollup mappings** (RC11, analyst) | **N/A.** No rollup requested or invented; the account hierarchy is source-supplied |
| **Hierarchy multi-parent** (RC12) | **N/A for this source** -- it carries no hierarchy. The account hierarchy lives on the conformed `dim_account_fgl`, declared identically in both maps |

**Genericity observation (ledger row L3).** As with the actuals table, the template's mandatory
category list is retail-shaped (Returns, Business rollups) while the classes this source
genuinely needed -- **comparison baseline** (Q1), **cross-grain allocation policy** (Q2), and
**version identity** -- appear nowhere in it. All were raised anyway.

**A second observation (ledger row L5).** The RC15 deviation this table records is not a
preference: the governed calendar contract is a closed Gregorian set that cannot carry a fiscal
period, so a fiscal-quarter-grain fact has no conformed calendar to key on and must declare its
own period dimension. The retail example hit the same wall earlier and settled it by choosing
the calendar year -- an option a fiscal-reporting domain does not have.

---

## See also

- `source-profile.md` -- the measured numbers, including the 1,344 / 1,103 / 241 coverage table
- `source-map.yaml` -- the machine-readable decisions and the two RC deviations
- `assumptions.md` -- adopted vs deviated, with triggering data facts
- `readiness-status.yaml` -- stage statuses, blockers, and the (empty) `approvals[]`
- `docs/worked-examples/finance-gl-genericity-ledger.md` -- obstructions met during this walk
