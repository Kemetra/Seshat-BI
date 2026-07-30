# Assumptions -- `finance_gl_actuals`

Filled instance of `templates/assumptions.md` (ADR 0003 location). Which ADR-0002 defaults
this table adopts as written, which it deviates from, and the DATA FACT that triggered each
deviation. ASCII only.

- **Table id:** `finance_gl_actuals`
- **Date:** 2026-07-30
- **Author:** agent
- **Evidence base:** `source-profile.md` (all figures computed from the generated source)

## Defaults adopted as written

| Default | Adopted because |
|---|---|
| RC1 lowest grain | journal line is the lowest grain the source provides; nothing is pre-aggregated |
| RC2 verify PK on data | composite (`journal_entry_id`, `line_id`) verified unique: 5,000 rows = 5,000 distinct |
| RC3 drop no-signal columns | none qualify -- 0 blank cells and no single-value column except `currency_code`, which is kept deliberately (see below) |
| RC5 `''` -> NULL | adopted as the baseline; the clean source contains no blanks, so nothing is coerced |
| RC7 types | money -> `numeric(18,2)`; `posting_date` -> `date`; codes -> `text`; `line_id` ordinal -> `smallint` |
| RC9 independent measures | `debit_amount` and `credit_amount` are kept as landed; neither is reconstructed from the other |
| RC12 flat denorm levels | `parent_account_code` and `department_code` are flat attributes, not a snowflake |
| RC13 idempotent migration | silver ships as a numbered, re-runnable migration |
| RC14 Kimball star | `_sk` keys, `-1` unknown members, FK COALESCE, degenerate dims for grain keys |
| RC15 contiguous calendar | daily `generate_series` calendar over 2024-01-01..2025-12-31; full governed attribute set |
| RC16 reconciliation | declared; the live leg is `[PENDING LIVE PROFILE]` -- no database was opened |

## Deviations (each with its triggering data fact)

### RC8 -- `is_return` is N/A on this source

**Data fact:** the source has **no** transaction-type, reversal, or return-marker column.
All 10 columns are accounted for in `source-map.yaml`, and none carries return semantics.
Every line is a posting.

**Why this is a deviation rather than an omission:** RC8 exists to stop `is_return` being
derived from the measure sign, because a sign misses zero-value and edge-case returns. Here
there is no authoritative column to derive from AND no returns to find, so the correct action
is to record RC8 as N/A -- explicitly, with this data fact -- rather than to invent a
derivation. **No `is_return` column is created.**

## Fixture simplifications (recorded so they are never mistaken for findings)

These are properties of the SYNTHETIC source, not claims about finance data in general. Each
is deliberately narrow so the defect variants in Slice B can break exactly one thing.

1. **Single currency.** Every row is `USD`. Mixed currency is isolated to variant D5, so
   currency policy stays a governed decision instead of becoming a modelling default. The
   `currency_code` column is kept (not dropped as single-valued) precisely so a future
   multi-currency source cannot silently mix units.
2. **Calendar-aligned fiscal year.** Fiscal quarters coincide with Gregorian quarters, so
   rolling actuals to the budget's comparison grain via the calendar's `year` + `quarter`
   gives the right answer here. **For an offset fiscal year (e.g. April-March) it would not.**
   That masking is recorded as part of ledger row L5 so the genericity conclusion cannot
   under-report the finding.
3. **No missing values.** 0 blank cells across all 10 columns. Consequently RC5 and RC6 are
   trivially satisfied and no grouping sentinel (`UNKNOWN`) is introduced anywhere -- there is
   nothing to sentinel. Missing-value handling is exercised by the Slice B variants, not here.
4. **Clean referential integrity.** 0 orphan `account_code`, 0 orphan `department_code`, 0
   invalid department/cost-center pairs, 0 posting dates outside a declared period. Each is
   broken by exactly one variant (D1, D2, D4).

## The clearing-account decision (a modelling decision, not an ADR deviation)

**Data fact:** the source carries 30 accounts, of which 2 are `account_type = 'CLEARING'`
(`1900`, `1910`), appearing on exactly **2,500** lines -- one per journal entry. Total debits
equal total credits to the cent (31,135,795.20) **only** because those clearing lines exist.

**Why they exist:** a P&L line cannot be balanced by another P&L line; the offsetting side of
a real journal is normally a balance-sheet account, and balance-sheet/snapshot grain is out of
scope (spec 091). The clearing pair is what lets the fixture be simultaneously
double-entry-balanced and P&L-only.

**The decision taken here:** clearing lines are **KEPT** through silver and gold -- so the
double-entry balance remains provable in the warehouse -- and P&L reporting **excludes** them
by filtering `dim_account_fgl.account_type <> 'CLEARING'`. They are not dropped at silver and
they are not filtered silently.

**Independent data support:** of the 1,199 actual (year, quarter, account, department) combos,
96 have no budget row -- and all **96 are clearing-account combos** (2 accounts x 6
departments x 8 quarters). Once clearing is excluded, P&L actuals coverage against budget is
**complete (0 gaps)**. The data therefore corroborates the exclusion rather than the exclusion
being a convenience.

**What is still open:** whether P&L metric contracts should carry that filter is a business
confirmation, raised as Q3 in `unresolved-questions.md`. The agent proposed the mechanism; the
owner confirms the semantics.

## Owner rulings applied to this table

| Ref | Ruling (Ahmed Shaaban, 2026-07-30) | Where it lands here |
|---|---|---|
| OD-1 | revenue and expenses both PRESENT as positive magnitudes; polarity via `direction_of_good` | the derived `amount` column (magnitude, no sign arithmetic); landed debit/credit kept intact |
| OD-3 | no monthly derivation from quarterly budget | affects the budget map; this table's daily grain is unaffected and rolls UP only |

OD-2 (baseline = `ORIGINAL`) applies to the budget table and the variance contracts, not here.

## What is NOT assumed

- No live database was opened. Every figure came from the committed generator's output; all
  live legs read `[PENDING LIVE PROFILE]`.
- No approval is recorded. `reviewed_by` / `reviewed_on` in `source-map.yaml` are explicitly
  `[PENDING GATE APPROVAL -- OD-4]`, and `readiness-status.yaml` carries no `approvals[]`
  entry. The agent did not self-grant the gate.
