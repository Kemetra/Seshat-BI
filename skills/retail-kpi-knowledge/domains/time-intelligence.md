# Time Intelligence Domain

Cumulative and comparison views over time. Needs a properly marked date table and care
with additivity (cumulative measures are semi-additive).

## KPIs in this domain

| KPI | Contract | Status |
|-----|----------|--------|
| YTD Net Sales | `contracts/ytd.md` | Seeded (calendar year-start, E1=A) |
| Net Sales Growth % (period-over-period) | `contracts/net-sales-growth.md` | Seeded |

## Decision questions this domain answers

Enter from the business question; each routes to a seeded contract or an honest
planned marker. These views need a marked date table; the year-start is the calendar
year (E1=A) unless a fiscal year is later declared.

| Decision question | Routes to | Status |
|-------------------|-----------|--------|
| How are we doing so far this (calendar) year? | `contracts/ytd.md` | Seeded |
| How does this period compare to the last? | `contracts/net-sales-growth.md` | Seeded |

## Key ambiguities (see knowledge/kpi-ambiguities.md)

- Fiscal vs calendar year — RULED: calendar year (1 January year-start, E1=A);
  revisit only if the business later declares a fiscal year (Finance owns that call).
- A3 Which date drives the axis (sale vs posting) — RULED: sale date (H9 D2=A).
- Comparison baseline: same period last year vs previous period — RULED: both, SPLY/YoY
  primary + prior-period secondary (H9 D3=C).
- Partial vs full period comparisons — RULED for YTD: both, to-date primary + full
  prior-year secondary (labelled) (YTD-year-start E2=C).

## Owner questions

Ask these before this domain's contracts are handed off. Each card is the owner-facing
form of an ambiguity listed above: it names the question in business language, the
silent breakage if it goes unanswered, and the `decision_type` under which the answer is
recorded in the Decision Store. The **layer default** is context shown to the owner, never
a recorded ruling -- an unanswered card stays `pending` and this domain stays blocked
(`knowledge/kpi-ambiguities.md`, Resolution rule: this layer never invents a policy to
make a number appear).

Every ambiguity listed above has a card here UNLESS it is already marked **RULED** (a
settled decision -- re-asking invites a contradicting answer) or states a grain/handling
instruction rather than a question only the owner can answer. Those exclusions are named
in the row list below rather than left silent.

| # | Ask the owner | If unanswered | Layer default (context only) | Records as |
|---|---------------|---------------|------------------------------|------------|
| A3 | Which date drives period comparisons: sale date or posting date? | Growth and prior-period comparisons do not reconcile between reports | None -- each contract must name its primary date | `kpi_definition` |

## Owner

Finance and BI.

## Notes

YTD is **semi-additive**: it is already cumulative, so YTD values must not be summed
across months (KPI-AP-10 logic). Growth % is non-additive. Both are now **Seeded**
(YTD year-start = calendar 1 January per E1=A — no fiscal attribute required; growth
baseline per H9 D3=C). They need a marked date table to implement.
