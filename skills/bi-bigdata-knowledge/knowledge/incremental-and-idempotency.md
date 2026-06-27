# Incremental Processing and Idempotency

Big-data jobs fail, get re-run, and receive late data. A pipeline that isn't idempotent
quietly produces duplicates and wrong totals on every rerun. Schema:
`references/retail-bigdata-schema.md`.

---

## BD-CN-057 — Idempotency: rerunning must not change the result

A job is **idempotent** if running it twice yields the same output as running it once.
Distributed jobs are re-run constantly (transient failures, retries, backfills), so
idempotency is a *design requirement*, not a nice-to-have. The classic violation: a job
that **appends** its output, so each rerun adds another copy of the same rows.

**Best practice (BD-BP-007):** make writes idempotent — overwrite the target partition, or
upsert/merge on a key — so reruns are safe.

## BD-CN-058 — Partition overwrite vs append

- **Append** — adds rows; safe only if the job never reprocesses the same input. Re-running
  an append over the same day **duplicates** that day.
- **Partition overwrite** — replace the specific partition (e.g. one `order_date`) the job
  computed; rerunning that day reproduces, not duplicates.
- **Upsert / merge** (Delta/Iceberg) — insert new keys, update changed ones; idempotent by
  key.

Choose the write mode that makes a rerun a no-op-equivalent, not a duplicator.

## BD-CN-059 — Incremental processing: do only what changed

**Incremental** processing handles only new/changed data instead of reprocessing the whole
history each run — far cheaper and faster. It requires a reliable way to identify the new
slice (a date partition, a high-water-mark timestamp, or a table-format change feed). The
output write must still be idempotent for the slice (BD-CN-058), so a re-run of a slice is
safe.

## BD-CN-060 — Late-arriving data

At scale, events arrive after their period's partition was first written (network delays,
producer retries, offline mobile sync). If yesterday's totals are computed once and frozen,
late events are silently lost or, if appended, double-counted.

Reason about a **late-data policy**: a lookback window that reprocesses recent partitions
(idempotently) to absorb late arrivals, and a rule for how late is too late. Table formats
make this safe via partition overwrite/merge over the lookback window.

**Retail illustration:** an offline mobile order created at 23:55 syncs at 00:30 the next
day. A daily job with a 2-day idempotent lookback reprocesses that store-day and corrects
the total; an append-only job would either miss it or double it.

## BD-CN-061 — Duplicate events and exactly-once thinking

Producers retry, so the same `event_id`/`order_line_id` can land more than once
(BD-CN-017). Deduplicate **globally** on the grain key as part of ingestion (reuses
`PY-CN-035`: declare the key first), and prefer merge-on-key writes so a duplicate input
cannot become a duplicate output. "Exactly once" in practice = idempotent writes +
key-based dedup, not a magic setting.

## BD-CN-062 — Backfills are reruns; design for them

Recomputing history (a logic fix, a new column) is a **backfill** — a deliberate rerun over
many partitions. It is safe only if writes are idempotent per partition (BD-CN-058).
Designing idempotency up front turns a backfill from a dangerous manual operation into a
routine one.

## BD-PB-005 — Playbook: reruns create duplicates

1. Identify the write mode — is it append (BD-CN-058)?
2. Switch to partition overwrite or merge-on-key for the processed slice.
3. Add global dedup on the grain key at ingestion (BD-CN-061).
4. Define a late-data lookback window and reprocess it idempotently (BD-CN-060).
5. Re-run twice and confirm the output is unchanged (the idempotency test).
6. Verdict on `checklists/pipeline-review-checklist.md`.

---

### Ends on

`checklists/pipeline-review-checklist.md` (idempotency/incremental section). Verdict
confirms a rerun is a no-op-equivalent and the late-data policy is explicit.
