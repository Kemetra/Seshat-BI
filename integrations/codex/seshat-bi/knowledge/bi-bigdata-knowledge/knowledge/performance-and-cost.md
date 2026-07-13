# Performance and Cost

Why a distributed job is slow or expensive — and when to stop tuning. At cluster scale,
performance is also *money*, so "fast enough and cheap enough" is the target, not maximum
speed. Schema: `references/retail-bigdata-schema.md`.

---

## BD-CN-071 — Diagnose from the plan and the job UI, not by guessing

Performance work starts with evidence: read the **plan** (stages, shuffles, join types,
whether pruning happens) and the **job UI** (task time distribution, spill, straggler
tasks, shuffle read/write sizes). Identify the dominant cost — usually one shuffle, one
skewed stage, or a scan that didn't prune — then change one thing and re-measure (reuses
the diagnose-first discipline, `PY-CN-074`).

## BD-CN-072 — The usual dominant costs (in order)

1. **Unnecessary shuffles** — wide steps that filtering/broadcast/pre-aggregation could
   remove (BD-CN-028).
2. **Skew** — one straggler task dominating (BD-CN-037).
3. **Reading too much** — no partition/column pruning (BD-CN-032, BD-CN-055).
4. **Spill** — partitions too large or skewed (BD-CN-033).
5. **Driver funneling** — `collect()`/`toPandas()` (BD-CN-010).

Most jobs are fixed by addressing one or two of these, not by micro-tuning configs.

## BD-CN-073 — Never collect to "check" or process

Pulling a distributed result to the driver (`collect()`, `toPandas()`, `count()` in a loop)
collapses cluster-scale data into one process and OOMs it; even when it survives, it
serializes the whole job through the driver. Inspect with distributed ops (aggregate,
`limit`+sample, `show`), and only collect a *small, bounded* result you have sized.
**Anti-pattern (BD-AP-005):** `collect()` on a large frame in a pipeline.

## BD-CN-074 — UDFs defeat the optimizer; prefer built-ins

User-defined functions (especially row-at-a-time Python UDFs) are opaque to the engine's
optimizer and add serialization overhead, breaking vectorized execution. Prefer built-in
column expressions/SQL functions; if a UDF is unavoidable, prefer vectorized/columnar UDFs.
A pipeline leaning on Python UDFs for logic the engine can express natively is a common
slowdown (reuses the vectorize rule, `PY-CN-075`).

## BD-CN-075 — Cache deliberately, release promptly

Caching a frame reused many times avoids recomputation, but cached data competes with
shuffle memory and can cause spill (BD-CN-019). Cache only a frame genuinely reused across
multiple actions; unpersist when done. Caching everything "to be safe" is an anti-pattern
that degrades the whole job.

## BD-CN-076 — Filter and project early; this is most of the win

The cheapest data to process is the data you never read or move. Push filters and column
selection as early as possible so every downstream stage handles less. Combined with
pruning (BD-CN-032), early filter/project is usually a bigger win than any config tuning.

## BD-CN-077 — Cost is a first-class metric

At cluster scale, a faster job can be a more expensive one (more/bigger executors). The BI
priority order extends the Python one: **correct → reconciled → maintainable → fast enough
→ cheap enough.** Evaluate cluster size, runtime, and spend together. A job that runs
slightly slower but at a third of the cost is usually the better BI choice (reuses "don't
optimize past the constraint", `PY-CN-082`).

## BD-CN-078 — Stop at fast-enough-and-cheap-enough

Once the job meets its time budget and cost budget and reconciles, stop. Further tuning
trades maintainability and correctness-traceability for resources nobody needs.
Performance never justifies skipping validation, collecting to the driver, or obscuring
where a number changed.

## BD-PB-007 — Playbook: job is slow / expensive but "works"

1. Read the plan + job UI; find the dominant cost (BD-CN-071/072).
2. Remove unnecessary shuffles (filter/project/broadcast/pre-aggregate).
3. Resolve skew if a straggler dominates (`joins-and-skew.md`).
4. Verify pruning; fix layout/filters if scanning too much.
5. Remove `collect()`/unneeded UDFs/over-caching.
6. Re-measure time **and** cost; confirm reconciliation still passes; stop at budget.

---

## Performance / cost diagnostic verdict (artifact)

State, in order:

1. **Constraint:** time / cost / memory, with the measured number.
2. **Dominant cost:** shuffle / skew / over-reading / spill / driver funneling.
3. **Lever applied:** filter-early / broadcast / pre-aggregate / fix-skew / prune /
   de-cache / remove-UDF — one change.
4. **Re-measure:** runtime and cost, before vs after.
5. **Correctness preserved:** validation/reconciliation still passes (BD-CN-078).

Verdict:

- **WITHIN BUDGET** — meets time and cost; no further tuning warranted.
- **OPTIMIZED** — a measured lever brought it within budget; correctness re-verified.
- **CONSTRAINED** — still over budget; escalate (re-architect, push down to SQL/warehouse,
  or re-evaluate engine choice in `engine-selection.md`).
