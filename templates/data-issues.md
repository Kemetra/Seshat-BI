# Data Issues -- <schema>.<table>

> GENERIC template. Copy per table. A log of DATA-QUALITY findings (distinct from
> process blockers in `blocking-reasons.md`). A data issue is about the data
> itself -- missingness, drift, a known gap -- and may be a `warning` (recorded,
> non-fatal) rather than a hard block. See `docs/readiness/readiness-model.md`.

## Issues

| # | Severity | Stage seen | Issue (concrete) | Measured (evidence) | Disposition |
|---|----------|------------|------------------|---------------------|-------------|
| 1 | warning | `<stage_key>` | `<e.g. N rows map to the -1 unknown member of dim_<x>>` | `<count / query>` | `<accepted gap \| to fix \| escalated>` |

## Severity

| Severity | Meaning | Effect on readiness |
|----------|---------|---------------------|
| `info` | recorded fact, no action | none |
| `warning` | non-fatal data issue (accepted gap, suspect pattern) | stage may be `warning`, not blocked |
| `error` | a proven defect (live-check failure) | stage is `blocked` -> see `blocking-reasons.md` |

## How issues relate to the gates

- **Static `seshat check`** WARNs on suspect patterns (ADR "override when"
  clauses) -> typically a `warning` data issue.
- **Live `retail validate`** ERRORs on proven defects (PK dup, orphan FK, penny
  mismatch) -> a `blocked` stage, logged here AND in `blocking-reasons.md`.
- A known, accepted gap (e.g. some rows on a dim's `-1` unknown member) is a
  `warning` with disposition "accepted gap" + the count as evidence -- never
  hidden, never silently a `pass`.

## Rules

- Measure missingness as `'' OR NULL`, never `IS NULL` alone.
- Every issue carries a measured number (evidence), not an adjective.
- An accepted gap MUST record who accepted it and why.

## See also

- Process blockers: `blocking-reasons.md`. Status: `readiness-status.yaml`.
- The reconciliation evidence: `mappings/<table>/reconciliation-report.md`.
