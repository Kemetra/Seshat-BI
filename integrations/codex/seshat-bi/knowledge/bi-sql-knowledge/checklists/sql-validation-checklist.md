# SQL Validation Checklist

Build a validation gate set for a table (source, silver, or gold). Each gate has an explicit
**pass condition**; a gate with no evidence is `blocked`, never `pass` (never fake a pass). Gate
shapes live in `patterns/sql-validation-patterns.json` (VP-*).

## Decide scope first
- [ ] Grain of the table stated in one sentence (SC-003).
- [ ] The columns that define row identity (the key) named and verified (SC-004).

## Core gates (pick the ones that apply)
- [ ] **Uniqueness** -- key has no duplicates (VP-UNIQUE). Pass: `GROUP BY key HAVING COUNT(*)>1`
      returns 0 rows.
- [ ] **Not-null** -- required columns are non-null (VP-NOTNULL). Pass: null count = 0 on each.
- [ ] **Referential integrity** -- no orphan facts (VP-REFINTEGRITY). Pass: anti-join to the
      dimension returns 0 rows (use `NOT EXISTS`, SC-012).
- [ ] **Row count** -- count within expected bounds vs prior run / source (VP-ROWCOUNT).
- [ ] **Range / domain / outlier** -- values within allowed bounds (VP-RANGE).
- [ ] **Dedup / idempotency** -- `COUNT(*) = COUNT(DISTINCT key)`; a reload keeps counts and totals
      identical (VP-DEDUP).

## Freshness & completeness (for periodic loads)
- [ ] **Freshness** -- `MAX(date)` meets the SLA (VP-FRESHNESS).
- [ ] **Completeness** -- every expected period/segment present, checked against a **date spine**,
      not the fact itself (VP-COMPLETENESS, SC-060).

## Scale (many tables)
- [ ] **Metadata-driven profile** -- generate per-column profiles from `information_schema` and
      compare to expectations / prior runs to catch drift (VP-PROFILE, SC-068..070).

## Record the result
- [ ] Each gate has: the SQL shape, the explicit pass condition, and the actual result.
- [ ] Overall status = worst gate (`blocked` if any blocking gate fails, else `warning` /
      `not_started` / `pass`), with `evidence[]` and `blocking_reasons[]`. Never a numeric score.
- [ ] Missing inputs (SLA, expected bounds, key constraints) -> **stop and request them**; mark the
      gate `blocked` with the reason, do not invent the expectation.
