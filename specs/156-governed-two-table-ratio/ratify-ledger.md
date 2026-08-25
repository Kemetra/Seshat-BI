# Ratify Ledger -- 156-governed-two-table-ratio

## Owner action

| Authority | Named ratifier | Date | Decision |
|---|---|---|---|
| owner | Ahmed Shaaban | 2026-08-25 | RATIFIED -- implement FR-156-001 through FR-156-011 |

The owner authorized the approved c19 design: keep `binds_to` scalar, add the
optional scalar sibling `compares_to`, reuse `definition.kind: ratio`, and make
generation plus approved-contract inventory fail closed on incoherent two-table
bindings.

Spec 141 is paused while this singleton fence is active. It is not completed,
rejected, superseded, or otherwise reclassified by this ratification.

## Boundaries retained

- No database or DAX execution.
- No Power BI write.
- No target value, grain, threshold, missing-target ruling, or approval is
  inferred or self-granted.
- Existing one-table contracts retain their current behavior.
