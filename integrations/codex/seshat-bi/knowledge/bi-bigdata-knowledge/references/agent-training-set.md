# Agent Training / Eval Set

Original Q&A pairs to train and evaluate a BI agent's distributed-reasoning. Each item
states the question, the correct reasoning, the artifact it should end on, and the IDs it
exercises. All scenarios use the fictional retail-at-scale schema. Machine-readable form:
`references/agent-training-set.json`.

---

**BD-QA-001** — *One month of one region from a date-partitioned billion-row table. Spark?*
Expected: no — post-pruning it's a few GB; DuckDB/Polars or a warehouse query suffices.
Single-node first. Ends on: engine verdict (SINGLE-NODE / push down). Exercises:
BD-CN-021/022, BD-AP-001.

**BD-QA-002** — *Joining billion-row orders to the small stores dim — best strategy?*
Expected: broadcast the small dimension so orders is never shuffled. Ends on: join/skew
verdict (BROADCAST). Exercises: BD-CN-035, BD-AP-006.

**BD-QA-003** — *Groupby on store_id is 99% done then one task hangs for an hour. Why/fix?*
Expected: flagship-store skew; one task gets the hot key's rows. Fix order: AQE skew-join →
broadcast other side → salt the hot key. Ends on: join/skew verdict. Exercises:
BD-CN-037/039, BD-AP-007.

**BD-QA-004** — *Revenue is too high and the shuffle is huge after joining orders to returns.*
Expected: one-to-many fan-out double-counts and inflates shuffle; pre-aggregate returns to
order-line grain first, then join many-to-one. Ends on: join/skew verdict. Exercises:
BD-CN-009 (PY-CN-051), BD-AP-011.

**BD-QA-005** — *Dashboard needs distinct customers per region; exact count is slow. OK to approximate?*
Expected: yes for a tolerant dashboard — use approx-distinct and label it approximate; use
exact for financial reconciliation. Ends on: aggregation-grain verdict. Exercises:
BD-CN-045, BD-AP-012.

**BD-QA-006** — *Can I .collect() the enriched billion-row frame to check it?*
Expected: no — collect funnels everything to the driver and OOMs it; inspect with count /
limit+sample / aggregates. Ends on: performance/cost verdict. Exercises: BD-CN-010/073,
BD-AP-005.

**BD-QA-007** — *A backfill rerun doubled last week's totals. Why?*
Expected: append-only writes aren't idempotent; switch to partition-overwrite or
merge-on-key; verify by double-run. Ends on: pipeline-review verdict. Exercises:
BD-CN-057/058, BD-AP-015.

**BD-QA-008** — *Yesterday's revenue is understated because mobile orders sync late. Fix?*
Expected: add an idempotent late-data lookback window that reprocesses recent partitions.
Ends on: pipeline-review verdict. Exercises: BD-CN-060, BD-AP-016.

**BD-QA-009** — *The job finished successfully — is the result reconciled?*
Expected: no — success ≠ correctness; compute distributed control totals and match to
source/SQL; hand the record to the gate. Ends on: validation/reconciliation verdict.
Exercises: BD-CN-064/069, BD-AP-018.

**BD-QA-010** — *Should I coalesce(1) to get a single output file?*
Expected: no — it funnels all data through one core, killing parallelism and risking OOM;
right-size partitions or use table-format compaction. Ends on: partitioning/shuffle
verdict. Exercises: BD-CN-030, BD-AP-002.

**BD-QA-011** — *Clickstream partitioned by minute is slow to query. Why/fix?*
Expected: small-files problem from over-partitioning; partition by date/hour and compact.
Ends on: partitioning/shuffle verdict. Exercises: BD-CN-051/052, BD-AP-010.

**BD-QA-012** — *A selective date filter still scans the whole table. Why?*
Expected: the filter isn't pushed down / layout isn't partitioned by date; make the filter
pushable and verify pruning in the plan. Ends on: partitioning/shuffle verdict. Exercises:
BD-CN-032/055, BD-AP-009.

**BD-QA-013** — *Is it fine to sum each region's average basket value across regions at scale?*
Expected: no — averages are non-additive (inherited PY-CN-054); recompute weighted at the
target grain; also defeats partial aggregation. Ends on: aggregation-grain verdict.
Exercises: BD-CN-044, BD-AP-013.

**BD-QA-014** — *Duplicate event_ids appear after dedup. What went wrong?*
Expected: dedup was per-partition; duplicates span partitions, so dedup must be global on
the grain key. Ends on: pipeline-review verdict. Exercises: BD-CN-017/061, BD-AP-017.

**BD-QA-015** — *Engine choice: a heavy join over data already in the warehouse?*
Expected: push the join down to the warehouse (SQL layer) rather than extracting into
distributed Python; keeps data in place and respects the boundary. Ends on: engine verdict
(PUSH DOWN). Exercises: BD-CN-024, cross-layer-map.
