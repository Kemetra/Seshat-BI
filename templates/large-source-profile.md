# Large-Source Profile -- `<source-id>`

> **Template.** The deeper, per-source detail filled **only when** the data-volume
> profile (`templates/data-volume-profile.md`) trips a large-source signal. It records
> the scale-relevant shape (partitioning, skew, fan-out, format, latency) a reviewer
> needs to choose between single-node, push-down, and a human scale review. Evidence
> only — it adopts no engine/platform and grants no readiness. Fill every
> `<placeholder>` from measured facts; delete this blockquote when filling it in.

| Field | Value |
|-------|-------|
| Source id | `<source-id>` |
| Date | `<YYYY-MM-DD>` |
| Author | `<name>` |
| Volume profile | `templates/data-volume-profile.md` -> `<filled path>` (the triggering evidence) |
| Triggering signal(s) | `<which large-source signal(s) from the volume profile fired>` |

## Scale-relevant shape (measured)

| Aspect | Value | Note |
|--------|-------|------|
| Natural partition key | `<e.g. sale_date, branch_id, or "none obvious">` | how the data could be split for processing/push-down |
| Skew risk | `<e.g. one branch is 60% of rows / unknown>` | a hot key dominates work at scale |
| Join fan-out risk | `<which joins multiply rows; cardinality if known>` | fan-out is the classic at-scale total inflation |
| Aggregation grain needed | `<the grain the consumer needs, e.g. branch-day>` | aggregating early shrinks the problem |
| File / table format | `<CSV / Parquet / DB table / Delta-Iceberg / unknown>` | columnar/compressed changes the size story |
| Incremental key available? | `<yes (e.g. load_ts) / no / unknown>` | enables incremental instead of full reprocessing |
| Latency gap | `<current vs required, e.g. 35 min vs 10 min SLA>` | quantify the miss, if any |

## Single-node vs push-down vs scale-out (reasoning, not a decision)

| Option | Plausible here? | Why / why not (cite the facts) |
|--------|-----------------|--------------------------------|
| Single-node (chunked / out-of-core Python) | `<yes / no / unsure>` | `<reason from the shape above>` |
| Push-down to SQL / warehouse | `<yes / no / unsure>` | `<is the heavy work a join/aggregation the warehouse can do?>` |
| Distributed / lakehouse (future `analytics-scale-knowledge`) | `<only if the two above are proven insufficient>` | `<the measured reason single-node + push-down fail>` |

> The reasoning layer `skills/bi-bigdata-knowledge/` informs these options (engine
> selection, partitioning, skew). It reasons only — it runs no job. Distributed
> options remain a future, evidence-gated, human-decided step.

## Open blockers / unknowns

List every `unknown` above that must be measured before a confident verdict. Any
material unknown drives the review to `BLOCKED` rather than a guessed verdict.

- `<blocker / unknown>`

## See also

- `templates/data-volume-profile.md` — the upstream volume evidence.
- `checklists/large-source-review-checklist.md` — the review that issues the verdict.
- `docs/big-data/big-data-capability-report.md` — the strategy/boundaries.
