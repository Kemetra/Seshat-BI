# Assumptions -- `finance_gl_budget`

Filled instance of `templates/assumptions.md` (ADR 0003 location). ASCII only.

- **Table id:** `finance_gl_budget`
- **Date:** 2026-07-30
- **Author:** agent
- **Evidence base:** `source-profile.md` (all figures computed from the generated source)

## Defaults adopted as written

| Default | Adopted because |
|---|---|
| RC1 lowest grain | quarter x account x department x version is the lowest grain the plan provides; it is NOT pre-aggregated from anything finer that exists |
| RC2 verify PK on data | the 5-part key is unique (2,688 = 2,688); dropping `budget_version` collides 2:1 |
| RC3 drop no-signal columns | none qualify -- 0 blank cells; `currency_code` is single-valued but kept deliberately |
| RC5 `''` -> NULL | baseline adopted; no blanks exist to coerce |
| RC7 types | `budget_amount` -> `numeric(18,2)`; year/quarter ordinals -> `smallint`; codes -> `text` |
| RC9 independent measure | `budget_amount` kept as landed |
| RC13 idempotent migration | silver ships as a numbered, re-runnable migration |
| RC14 Kimball star | `_sk` keys, `-1` unknown members, FK COALESCE, degenerate dims |
| RC16 reconciliation | declared; live leg `[PENDING LIVE PROFILE]` |

RC12 is not cited: this source has no hierarchy of its own (the account hierarchy is carried by
the conformed account dimension, declared in both maps).

## Deviations (each with its triggering data fact)

### RC8 -- `is_return` is N/A on this source

**Data fact:** a budget is a plan. It has no transaction-type column, no reversal column, and
no postings at all -- all 7 columns are accounted for in `source-map.yaml` and none carries
return semantics. No `is_return` is derived.

### RC15 -- this fact does not reference the contiguous daily calendar

**Data fact:** the source has no date column. Its time grain is (`fiscal_year`,
`fiscal_quarter`) -- 8 distinct periods across 2 years, matching the `fiscal_calendar`
reference file exactly (0 orphan year/quarter pairs).

**Why a deviation is required:** the RC15 calendar is a CLOSED Gregorian contract
(`full_date, year, quarter, month, month_name, day, day_name, iso_week, is_weekend`), and the
template states an off-contract attribute -- naming `fiscal_year` as its own example -- is
REJECTED rather than silently built, because a generated calendar has no source column to
derive it from. There is therefore **no way to put a fiscal period on the date dimension**.

**Resolution:** declare a separate quarter-grain `gold.dim_fiscal_period_fgl` sourced from the
`fiscal_calendar` file, and leave the daily RC15 calendar to the ACTUALS fact (which still
builds it in full). No kit change was made. Recorded as ledger row **L5**.

**Severity note, kept explicit:** this fixture's fiscal calendar is calendar-aligned, so
fiscal quarters coincide with Gregorian quarters and rolling actuals up via the calendar's
`year` + `quarter` gives the correct answer here. For an offset fiscal year (April-March) it
would silently give the WRONG answer. The fixture is masking part of this finding's severity;
that is stated in L5 so the conclusion cannot under-report it.

## Fixture simplifications (not findings)

1. **Single currency** (`USD` on every row). Mixed currency is variant D5.
2. **Two budget versions** (`ORIGINAL`, `REVISION-1`), both fully populated across all 1,344
   combos. Real plans are often partial; partial coverage is exercised by variants, not here.
3. **No missing values** (0 blanks). Note the distinction this table makes load-bearing:
   `budget_amount = 0` is a legitimate plan ("nothing budgeted"), while an ABSENT row means no
   plan exists. FR-015 requires those two to stay distinguishable, and the Missing Budget Flag
   metric detects the second, never the first.
4. **Calendar-aligned fiscal year** -- see the RC15 severity note above.

## Coverage facts a reader should not misread

| Fact | Count | Reading |
|---|---|---|
| Budget combos per version | 1,344 | full coverage of 28 accounts x 6 depts x 8 quarters |
| P&L actual combos absent from `ORIGINAL` | **0** | actuals are fully budgeted once clearing is excluded |
| Budget combos with no posted actuals | **241** | **legitimate business exception**, not a defect |

The 241 are a real business state: a department was budgeted for an account and posted nothing
that quarter. They must surface in the report as an exception. A gate that refuses them is
over-refusing (FR-023), which this example counts as a failure, not as safety.

## Owner rulings applied to this table

| Ref | Ruling (Ahmed Shaaban, 2026-07-30) | Where it lands here |
|---|---|---|
| OD-2 | the variance BASELINE is `budget_version = ORIGINAL` | every variance contract pins ORIGINAL; `REVISION-1` stays in the source to exercise version identity (FR-011) and variant D10, and never moves the headline measures |
| OD-3 | no monthly view derived from quarterly budget | `derived_columns: []` -- no allocation, spreading, or interpolation. A monthly-budget request is refused with the reason named (variant D11) |
| OD-1 | both positive, polarity via `direction_of_good` | `budget_amount` is stored as landed; presentation polarity is a contract concern, not a silver transform |

## What is NOT assumed

- **Nothing is disaggregated.** `budget_amount` is additive at and above its own grain only.
- No live database was opened; every live leg reads `[PENDING LIVE PROFILE]`.
- No approval is recorded. `reviewed_by` / `reviewed_on` are `[PENDING GATE APPROVAL -- OD-4]`
  and `readiness-status.yaml` carries no `approvals[]` entry.
