# Blocking Reasons -- <schema>.<table>

> GENERIC template. Copy per table. The concrete reasons a readiness stage is
> `blocked` -- each with the stage it blocks, the evidence, and the owner who can
> clear it. A blocker is a fact, not an opinion. See
> `docs/readiness/readiness-model.md`.

## Open blockers

| # | Stage blocked | Reason (concrete) | Evidence / where | Owner to clear | Raised |
|---|---------------|-------------------|------------------|----------------|--------|
| 1 | `<stage_key>` | `<e.g. grain not unique on transformed data>` | `<path or query>` | `<analyst \| governance \| data_owner>` | `<YYYY-MM-DD>` |

## Common blocking reasons by stage (reference)

| Stage | Typical blockers |
|-------|------------------|
| Source Ready | profile missing; semantics unconfirmed; source unreachable |
| Mapping Ready | `Gate status` not CLEARED; open unresolved question; grain not unique on data; `pii:true` column not dropped; rollup not analyst-supplied |
| Silver Ready | mapping not pass; `seshat check` ERROR; Phase-5 build order violated |
| Gold Ready | live finding (V-RC2/V-RC15/V-RC16); reconciliation not penny-exact; no DSN/`db` extra (blocked-deferred) |
| Semantic Model Ready | gold not pass; D/C/R/G6 finding; measure with no metric contract; real host in PBIP params |
| Dashboard Ready | semantic model not pass; visual with no backing metric contract |
| Publish Ready | a prior stage not pass; missing caveats/reconciliation evidence; no publish approval |

## Rules

- A blocker MUST name the stage it blocks and a concrete reason (not "needs work").
- A blocker is cleared only by its named owner; the agent records, it does not
  self-clear an approval-type blocker (Principle V).
- When a blocker is cleared, move it to a "Cleared" log with the date + evidence.

## See also

- The status file: the table's `readiness-status.yaml` (`blocking_reasons[]`).
- Data-quality findings (distinct from process blockers): `data-issues.md`.
