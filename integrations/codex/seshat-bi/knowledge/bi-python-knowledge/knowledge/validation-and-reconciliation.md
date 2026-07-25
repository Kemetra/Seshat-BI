# Validation and Reconciliation

Use this route after preparation and before a SQL/readiness handoff. End on
`checklists/validation-reconciliation-checklist.md`.

## Decision this route supports

Determine whether the dataframe preserves its declared grain, schema, domains, and
control totals relative to an authoritative comparison boundary.

## Required evidence

- input/output grain and source/profile revisions;
- expected schema and critical-field policies;
- authoritative row counts or control totals;
- filters, exclusions, tolerance, and comparison period;
- merge and aggregation verdicts when those operations occurred.

## Reasoning sequence

1. **PY-CN-133 — Validation asks whether a contract holds.** It checks one artifact
   against declared expectations.
2. **PY-CN-134 — Reconciliation compares independent boundaries.** Expected and
   actual values must not come from the same transformation logic.
3. **PY-CN-135 — Grain uniqueness precedes totals.** Correct totals can coexist with
   duplicated identities.
4. **PY-CN-136 — Controls share scope.** Period, filters, exclusions, currency, and
   null policy must match before comparison.
5. **PY-CN-137 — Tolerance is declared before results.** Counts and keys normally
   require exact equality; numeric tolerances require a business/technical basis.
6. **PY-CN-138 — Segment checks localize cancellation.** Global parity can hide one
   overstated and one understated segment.
7. **PY-CN-139 — Samples diagnose; they do not prove population correctness.**
8. **PY-CN-140 — A clean check is evidence, not readiness approval.**

Recommended order: `PY-VP-005` schema -> `006` row count -> `007` grain uniqueness ->
`008` key nulls -> `009` domains/ranges -> `010` unmatched keys -> `011` additive
controls -> `012` segment controls -> `013` null distribution -> `014` date coverage ->
`015` idempotent-result comparison -> `016` evidence handoff.

## Failure modes

- expected totals recomputed with the same buggy dataframe logic;
- aggregate parity checked before uniqueness;
- tolerance selected after seeing the delta;
- global total used to hide segment-level swaps;
- a sample presented as proof;
- Python validation used to skip the readiness gate.

## Evidence-based verdict

- **RECONCILED** — required checks match within predeclared tolerances.
- **OPEN FINDINGS** — localized differences have owners and next checks.
- **NOT RECONCILED** — one or more controls contradict the expected boundary.
- **BLOCKED** — authoritative expectations or comparison scope are missing.

## Stop and handoff

Attach expected, actual, delta, tolerance, evidence source, and one next action. Hand
the record to SQL/readiness; never self-grant a pass.
