# PostgreSQL Execution-Plan Reasoning

> Read-only interpretation of a supplied, sanitized
> `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` artifact. This layer does not run SQL,
> change indexes, tune settings, or claim that a sampled plan represents every workload.

## Evidence contract

Before reviewing a plan, record:

- the SQL fingerprint or purpose, with literals and secrets removed;
- PostgreSQL version, relevant table sizes, and whether statistics were current;
- representative parameter class and workload context;
- the complete JSON plan, including planning/execution time and buffer data;
- whether the query was run in a safe non-production or read-only context.

`ANALYZE` executes the statement. The agent must never request it for mutating SQL or run it
itself. Bare SQL, a screenshot, or cost-only `EXPLAIN` can support hypotheses but cannot support a
performance verdict.

## Plan concepts

### EP-001 -- Read the plan as a tree

Each node consumes rows from its children and emits rows to its parent. Start at the root, identify
the largest time/row contributors, then follow the branch that produces them. A visually deep node
is not necessarily expensive.

### EP-002 -- Cost units are estimates, not elapsed time

`Startup Cost` and `Total Cost` are optimizer-relative estimates. Compare alternatives within the
same environment; do not translate cost units into milliseconds or compare them across servers.

### EP-003 -- Compare estimated and actual rows

Cardinality error is the ratio between `Plan Rows` and `Actual Rows`, interpreted with `Actual
Loops`. Large, repeated error can make a reasonable join or scan choice perform badly. Record the
direction and location of the error rather than inventing one universal acceptable ratio.

### EP-004 -- Multiply per-loop work

`Actual Rows` and node time may be reported per loop. Interpret total work with `Actual Loops`;
a cheap inner node repeated hundreds of thousands of times can dominate execution.

### EP-005 -- Scan choice depends on selectivity and locality

Sequential scans can be correct for a large fraction of a table. Index, bitmap, and index-only
scans are useful only when selectivity, visibility, correlation, cache state, and access pattern
support them. A sequential scan alone is not proof that an index is missing.

### EP-006 -- Nested-loop joins amplify repeated inner work

A nested loop is effective when the outer side is small and the inner lookup is cheap. Investigate
when the outer rows or loops greatly exceed estimates, especially if the inner side performs
repeated reads.

### EP-007 -- Hash joins trade memory for one-pass matching

Hash joins suit equality joins when the build side fits available memory. Inspect build-side rows,
`Hash Batches`, memory usage, and temporary I/O. Multiple batches can indicate spill or deliberate
batching; confirm with buffer/temp evidence.

### EP-008 -- Merge joins require ordered inputs

Merge joins can be effective for large ordered inputs and range-compatible conditions. Account for
sort nodes or index order that produce the required ordering; the join node alone does not expose
the full cost.

### EP-009 -- Filters can reveal wasted work

`Rows Removed by Filter` shows rows read and then discarded at that node. Interpret it with loops,
input size, and predicate placement. A high number is a lead to investigate, not an automatic
rewrite instruction.

### EP-010 -- Sort and hash spill require temp evidence

Inspect sort method, memory, disk usage, hash batches, and temp blocks. Recommend a memory or query
change only after confirming concurrency, workload-wide memory risk, and whether the spill is
repeatable.

### EP-011 -- Buffers distinguish logical I/O from elapsed time

Use shared hit/read/dirtied/written and temp read/write blocks to locate I/O pressure. Cache state
changes elapsed time, so compare like with like and retain buffer evidence in before/after reviews.

### EP-012 -- Parallel plans need leader-and-worker context

Inspect planned/launched workers, per-worker rows where available, gather overhead, and skew.
Fewer launched workers than planned or uneven worker output may explain a result, but system-wide
capacity evidence is required before changing parallel settings.

### EP-013 -- Statistics and parameter sensitivity limit generalization

Stale statistics, correlated columns, skew, prepared-statement plan reuse, and atypical parameters
can produce different estimates and choices. A single plan supports a finding for that evidence
case, not a claim about every parameter or time period.

### EP-014 -- A tuning claim needs before/after equivalence

A proposed change is supported only when before/after plans use equivalent results, representative
parameters, comparable cache/load conditions, and reconciliation evidence. Include write/storage
cost before recommending an index. Otherwise return `needs-evidence`.

## Review sequence

1. Confirm the evidence contract and query safety.
2. State input and output grain; correctness still precedes performance.
3. Trace the dominant root-to-leaf branch.
4. Compare estimates, actual rows, and loops.
5. Interpret scans and joins in their cardinality context.
6. Inspect filtered rows, memory/spill, buffers, and parallel workers.
7. Record statistics and parameter limitations.
8. End on `../checklists/postgresql-plan-review-checklist.md`.

Use `../patterns/postgresql-plan-patterns.json` to structure symptoms. Every plausible cause remains
a hypothesis until its confirming evidence is present.
