# DAX Semi-Additive and Blank Semantics

> The approved metric contract owns additivity, snapshot selection, and blank/zero meaning. This
> resource diagnoses whether DAX implements that policy; it never chooses the policy.

## Required evidence

- metric contract with entity grain, time grain, additivity, and display semantics;
- snapshot/event fact grain, date relationship, coverage, and late-arrival behavior;
- measure DAX plus the detail and total contexts that reproduce the symptom.

If "last", "average", "sum", blank, and zero have no approved business meaning, stop with a policy
blocker.

### DX-SA-001 -- Additivity is dimension-specific

A balance can be additive across accounts and non-additive across time. State additivity for each
relevant dimension instead of labeling a measure simply additive/non-additive.

### DX-SA-002 -- Snapshot grain precedes DAX

Identify what one snapshot row represents and whether snapshots are periodic or accumulating.
Measure logic cannot repair an unknown or mixed snapshot grain.

### DX-SA-003 -- Last date is not always last date with data

The last visible calendar date may have no observation. Apply the contract's policy for last
available observation, exact period-end observation, or blank.

### DX-SA-004 -- Entity-level last observations may differ

Different entities can have different last observation dates. A single global maximum date can
drop valid entities or mix periods; confirm the approved consolidation policy.

### DX-SA-005 -- Totals re-evaluate the measure

DAX totals calculate in total filter context; they do not necessarily sum displayed rows. Diagnose
whether the contract expects re-evaluation, explicit iteration, weighted behavior, or no total.

### DX-SA-006 -- Ratios are non-additive

Sum numerators and denominators at the approved grain, then divide. Adding row-level percentages or
averaging them without weights is usually a semantic defect.

### DX-SA-007 -- BLANK means absence or non-applicability

`BLANK()` can mean no observation, unsupported comparison, suppressed result, or not applicable.
Preserve it unless the contract explicitly states that absence is a numeric zero.

### DX-SA-008 -- Zero is an observed numeric state

Zero participates in averages, counts, conditional formatting, and totals. Coercing blanks to zero
changes populations and must be treated as a policy change, not cosmetic formatting.

### DX-SA-009 -- Display behavior can reveal or hide blanks

"Show items with no data", axes, and formatting affect what users see. Separate a missing row, a
blank measure, and a formatted blank before changing DAX.

### DX-SA-010 -- Reconcile coverage as well as value

Validate both numeric controls and observation coverage: entity count, period count, last-observed
date distribution, blank count, and zero count.

## Diagnostic sequence

1. Confirm time/entity grain and dimension-specific additivity.
2. Confirm snapshot coverage and the approved observation-selection policy.
3. Compare detail, subtotal, and grand-total contexts.
4. Separate no row, blank result, numeric zero, and display suppression.
5. Reconcile values plus population/coverage.
6. Stop if snapshot/date or blank/zero policy is undecided.
7. End on `../checklists/dax-diagnostic-checklist.md`.
