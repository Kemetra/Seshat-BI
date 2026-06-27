# Partitioning / Shuffle Checklist

Artifact for the partitioning, shuffle, and file-format routes. Ends on a verdict with
before/after evidence.

## A. Partition sizing (BD-CN-027)

- [ ] Partition count/size assessed against data size and cluster cores.
- [ ] No partitions so large they spill; none so tiny they add only overhead.

## B. Shuffle minimization (BD-CN-028)

- [ ] Wide steps (shuffles) listed; each justified.
- [ ] Filters applied before wide steps (row pruning).
- [ ] Unused columns dropped before wide steps (column pruning).
- [ ] Broadcast / pre-aggregation used where it removes a shuffle.

## C. Adaptive execution (BD-CN-029)

- [ ] AQE enabled (`spark.sql.adaptive.enabled`).
- [ ] Coalesce partitions and skew-join handling on.
- [ ] Understood that AQE handles common, not pathological, skew.

## D. Repartition / coalesce / pruning (BD-CN-030..032)

- [ ] repartition used only to increase parallelism / co-locate by key.
- [ ] coalesce used only to shrink partitions cheaply; **no `coalesce(1)`** to force one file.
- [ ] On-disk partitioning serves the dominant downstream operation.
- [ ] Partition pruning verified in the plan (date/key filters actually prune).

## E. Spill (BD-CN-033)

- [ ] Spill checked; if present, traced to sizing or skew (not silenced).

## Verdict

- **EFFICIENT** — shuffles justified, partitions right-sized, pruning works, no avoidable
  spill.
- **SKEW SUSPECTED** — uneven task times; go to `checklists/join-skew-checklist.md`.
- **OVER/UNDER-PARTITIONED** — adjust partition count and re-measure.
- **SMALL-FILES** — output fragmented; see `knowledge/file-formats-and-storage.md`.

Attach: shuffle count, partition sizing, and before/after runtime or spill evidence.
