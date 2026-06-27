# Joins and Skew

Joins are the most expensive and most failure-prone distributed operation. Correctness
(fan-out, cardinality) is borrowed from `bi-python-knowledge`; this file adds the
distributed concerns: broadcast vs shuffle, and skew. Schema:
`references/retail-bigdata-schema.md`.

---

## BD-CN-034 — Correctness first: cardinality and fan-out still rule

Before any distributed-join tuning, the pandas rules apply unchanged: know each side's
grain and key uniqueness, and the intended cardinality (`PY-CN-045`). A non-unique join key
still causes **fan-out** (`PY-CN-046`) — and at scale it both corrupts sums *and* explodes
shuffle volume (BD-CN-009). The fix is the same: aggregate the many-side to the join grain
first (`PY-CN-051`). Tune only a correct join.

## BD-CN-035 — Broadcast join vs shuffle join

Two ways to bring matching keys together:

- **Broadcast (map-side) join** — copy the *small* side to every executor; the large side
  is never shuffled. Fast, no shuffle. Eligible only when one side is small enough to fit
  in executor memory.
- **Shuffle (sort-merge) join** — shuffle *both* sides by key so matching rows co-locate.
  Necessary when both sides are large. This is where skew bites.

**Best practice (BD-BP-004):** broadcast the small dimension whenever one side is small.

**Retail illustration:** joining `orders` (billions) to `stores` or `products` (small
dimensions) should **broadcast** the dimension — no shuffle of `orders`. Joining `orders`
to `customers` (tens of millions) is usually a **shuffle** join.

## BD-CN-036 — Broadcast eligibility and its limits

An engine auto-broadcasts a side below a size threshold (Spark:
`spark.sql.autoBroadcastJoinThreshold`); a hint can force it. But broadcasting a side that
is too large OOMs every executor. Reason about the *actual* size of the small side
(post-pruning), not its row count alone. Broadcast is a lever with a ceiling, not a
default for every join.

## BD-CN-037 — Skew is the join killer

In a shuffle join, all rows for a key go to one task. If a key is **skewed** (a flagship
`store_id`, a bot `session_id`, a placeholder `sku`), that one task gets a huge share of
rows and becomes a straggler that dominates runtime — while other tasks finish and idle.
Skew shows up as "one task runs forever; the job is 99% done for an hour."

## BD-CN-038 — Detecting skew

Skew is diagnosed, not guessed:

- Inspect per-task/per-partition row counts or runtimes — a few far above the median.
- Profile key frequency: a small number of keys holding a large fraction of rows.
- Watch for a single straggler task in the job UI.

Record the offending keys; the fix depends on knowing them.

## BD-CN-039 — Fixing skew: AQE, broadcast, then salting

In order of preference:

1. **Let AQE split skewed partitions** (`spark.sql.adaptive.skewJoin.enabled`) — handles
   common skew in sort-merge joins automatically (BD-CN-029).
2. **Broadcast** the other side if it is small enough — removes the shuffle entirely
   (BD-CN-035), so skew no longer matters.
3. **Salting** — for pathological skew AQE can't resolve: add a random suffix to the hot
   key on both sides so its rows spread across many tasks, then aggregate the salt away.
   Salting is powerful but adds complexity, so reserve it for genuinely heavy keys.

**Best practice (BD-BP-005):** prefer broadcast or AQE; reach for salting only when a known
hot key still dominates.

## BD-CN-040 — Key hygiene still matters at scale

The pandas key-hygiene rules (`PY-CN-049`) hold: mismatched key dtypes silently drop
matches, and empty-string keys fabricate matches (`PY-CN-040`). At scale these are worse
because a wrong join may run for an hour before the bad result appears. Clean and type keys
before the join, not after.

## BD-CN-041 — Reconcile the join at scale

Row-count reconciliation (`PY-CN-050`) is still the acceptance test, computed as a
distributed aggregate (not by collecting). State the expected result row count from
cardinality; compare actual; investigate unmatched rows with `indicator`-style coverage.
A scaled join that isn't reconciled is not done.

## BD-PB-003 — Playbook: one task runs forever (skew)

1. Confirm the join is correct first (cardinality, no unintended fan-out) — BD-CN-034.
2. Detect skew: per-partition sizes / straggler task / key-frequency profile (BD-CN-038).
3. Can the other side be broadcast? If yes → broadcast, skew gone (BD-CN-035).
4. Else ensure AQE skew-join is on (BD-CN-039 step 1).
5. Else salt the known hot key(s) (BD-CN-039 step 3).
6. Reconcile result row count (BD-CN-041); verdict on the checklist.

---

### Ends on

`checklists/join-skew-checklist.md` — a **join/skew verdict** with the chosen strategy
(broadcast / shuffle+AQE / salted), skew evidence, and the row-count reconciliation.
