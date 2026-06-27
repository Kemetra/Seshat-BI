# Big-Data Retail Examples

Original worked examples on the Meridian Outfitters fictional schema at scale
(`references/retail-bigdata-schema.md`). Each shows the reasoning, the artifact it ends on,
and the rule it illustrates. Code is minimal, standard idiom — never a source listing
(`references/copyright-and-sources.md`).

---

## BD-EX-001 — Choosing not to scale out

**Situation:** an analyst wants daily revenue for one region for one month from
date-partitioned `orders`.

**Reasoning:** post-pruning, that's one region × ~30 day-partitions — a few GB, not the
whole billion-row table. It fits DuckDB/Polars on one machine (or a warehouse query). A
Spark cluster is unwarranted.

**Ends on:** engine verdict = SINGLE-NODE → route to `bi-python-knowledge` / push down.
**Illustrates:** BD-CN-021/022 / guards BD-AP-001.

---

## BD-EX-002 — Broadcast the store dimension

**Situation:** join billion-row `orders` to the small `stores` dimension to add `region`.

**Reasoning:** `stores` is tiny; broadcasting it copies the dim to every executor and avoids
shuffling `orders` at all. A shuffle join here would move a billion rows for nothing.

**Idiom:**
```python
from pyspark.sql.functions import broadcast
enriched = orders.join(broadcast(stores), "store_id", "left")
```
**Ends on:** join/skew verdict = BROADCAST; row count == orders row count.
**Illustrates:** BD-CN-035 / guards BD-AP-006.

---

## BD-EX-003 — Flagship store skew

**Situation:** a groupby/join on `store_id` runs 99% fast then one task hangs for an hour.

**Reasoning:** a few flagship stores hold a huge share of rows (skew). Fix order: ensure
AQE skew-join is on; if the other side is small, broadcast it; for the residual hot store,
salt the key and combine partial aggregates.

**Ends on:** join/skew verdict = SHUFFLE+AQE (or SALTED) with straggler evidence.
**Illustrates:** BD-CN-037/039 / guards BD-AP-007.

---

## BD-EX-004 — Returns fan-out explodes the shuffle

**Situation:** joining `orders` to `returns` (one-to-many) then summing revenue — the job
both over-counts revenue and shuffles far more rows than expected.

**Reasoning:** fan-out duplicates order lines (correctness) *and* inflates shuffle volume
(performance). Pre-aggregate `returns` to one row per `order_line_id` first, then join
many-to-one.

**Idiom:**
```python
ret = returns.groupBy("order_line_id").agg(F.sum("return_qty").alias("return_qty"))
m = orders.join(ret, "order_line_id", "left")  # now many-to-one
```
**Ends on:** join/skew verdict = sound; revenue reconciles.
**Illustrates:** BD-CN-009 (reuses PY-CN-051) / guards BD-AP-011.

---

## BD-EX-005 — Approximate distinct customers for a dashboard

**Situation:** a daily dashboard needs "distinct customers per region"; exact
`COUNT(DISTINCT)` is slow and skewed.

**Reasoning:** the dashboard tolerates ~1–2% error, so approximate distinct (HyperLogLog)
is the right call — fast and cheap — but it must be **labeled approximate**. The monthly
finance reconciliation that must tie out uses exact.

**Idiom:**
```python
daily = orders.groupBy("region").agg(F.approx_count_distinct("customer_id").alias("approx_customers"))
```
**Ends on:** aggregation-grain verdict; distinct-count method recorded as approximate.
**Illustrates:** BD-CN-045 / guards BD-AP-012.

---

## BD-EX-006 — Driver OOM from collect()

**Situation:** a pipeline calls `.collect()` on the enriched `orders` frame to "check it",
and the driver crashes.

**Reasoning:** collecting billions of rows funnels the whole dataset into the driver.
Inspect with distributed ops (a count, an aggregate, a small `limit` sample) instead.

**Idiom:**
```python
enriched.count()                # distributed
enriched.limit(20).show()       # bounded sample
```
**Ends on:** performance/cost verdict; driver funneling removed.
**Illustrates:** BD-CN-010/073 / guards BD-AP-005.

---

## BD-EX-007 — Non-idempotent append duplicates a backfill

**Situation:** the daily `orders` aggregation appends to the target; a backfill rerun of
last week doubles last week's totals.

**Reasoning:** append + rerun = duplicates. Switch to partition-overwrite (replace the
processed `order_date` partitions) or merge-on-key, so a rerun reproduces rather than
duplicates. Verify by running twice and comparing totals.

**Ends on:** pipeline-review verdict; idempotency rerun check (BD-VP-006) passes.
**Illustrates:** BD-CN-057/058/062 / guards BD-AP-015.

---

## BD-EX-008 — Late mobile orders and the lookback window

**Situation:** offline mobile orders sync hours late; yesterday's revenue is understated.

**Reasoning:** a frozen daily total misses late events. Add an idempotent 2-day lookback
that reprocesses recent `order_date` partitions via partition-overwrite, absorbing late
arrivals without double-counting.

**Ends on:** pipeline-review verdict; late-data policy explicit.
**Illustrates:** BD-CN-060 / guards BD-AP-016.

---

## BD-EX-009 — Control-total reconciliation at scale

**Situation:** before handoff, the distributed `orders` revenue total must match the
warehouse/source figure for the period.

**Reasoning:** compute the additive total as a distributed aggregate (cheap via partial
aggregation) on both sides; compare within a declared penny tolerance. Equal → evidence,
recorded. Hand the reconciliation record to readiness; do not self-approve.

**Idiom:**
```python
bd_rev = enriched.select(F.sum(F.col("unit_price")*F.col("quantity") - F.col("discount_amt"))).first()[0]
```
**Ends on:** validation/reconciliation verdict; record handed to gate.
**Illustrates:** BD-CN-064/069 (reuses PY-CN-068) / guards BD-AP-018.

---

## BD-EX-010 — Small-files problem from over-partitioning

**Situation:** clickstream written partitioned by minute produces millions of tiny files;
queries start slowly.

**Reasoning:** per-minute partitioning is too fine. Partition by date (and maybe hour),
compact existing small files, and let the table format manage file sizes.

**Ends on:** partitioning/shuffle verdict; small-files resolved.
**Illustrates:** BD-CN-051/052 / guards BD-AP-010.

---

### Note

These examples are the source pool for the training/eval set
(`references/agent-training-set.md`).
