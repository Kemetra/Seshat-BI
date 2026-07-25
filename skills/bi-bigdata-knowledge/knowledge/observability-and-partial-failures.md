# Observability and Partial Failures

> Distributed operational reasoning only. Reuse the declared grain and reconciliation rules from
> upstream contracts; do not redefine them here. This layer reads supplied evidence and never runs
> or retries a job.

## Required evidence

- pipeline/job/run identifiers, engine/version, code/config revision, and attempt identifiers;
- input and output dataset/table versions plus partition/file manifests;
- stage/task/executor status, retry/speculation history, and error/quarantine records;
- commit protocol and visibility boundary;
- control totals and validation results at the declared grain;
- duration, compute, I/O, shuffle, spill, and cost evidence when assessing efficiency.

### BD-OPS-001 -- A job ID is not a run identity

Record pipeline, scheduled run, engine job, stage, task, and attempt identifiers. Retries can share
logical work while producing different physical attempts; evidence must keep them distinguishable.

### BD-OPS-002 -- Bind evidence to code and input versions

A run is reproducible only when code/config revision and immutable input/table versions are known.
Wall-clock paths alone do not prove which data was read.

### BD-OPS-003 -- Input manifests define observed scope

Capture partitions/files/table snapshots actually read, not only the intended date range. Missing,
duplicated, or late-discovered inputs explain many apparent calculation defects.

### BD-OPS-004 -- Output manifests expose partial publication

List staged and visible output files/partitions/table versions. A successful subset of tasks may
leave visible data even when the logical run fails, depending on the sink and commit protocol.

### BD-OPS-005 -- Commit visibility is a correctness boundary

Document whether publication is atomic at file, partition, table, or transaction level. Never infer
all-or-nothing behavior from an engine's final job status.

### BD-OPS-006 -- Attempt history is required for retry diagnosis

Record original, retried, and speculative attempts plus their write identities. A later successful
attempt does not prove an earlier attempt left no visible output.

### BD-OPS-007 -- Retry safety depends on deterministic write identity

Retries need stable target/version keys, idempotent overwrite/merge semantics, or an atomic commit.
Random filenames and append-only retry behavior can duplicate logical output.

### BD-OPS-008 -- Quarantine is evidence, not silent loss

Rejected records/partitions need counts, reasons, source identities, and reconciliation treatment.
An uncounted dead-letter path makes a "successful" output incomplete.

### BD-OPS-009 -- Stage success does not equal dataset completeness

Compare expected and observed partition manifests plus control totals. Green task status cannot
substitute for data completeness evidence.

### BD-OPS-010 -- Performance evidence separates wait from work

Record scheduler delay, compute time, shuffle read/write, spill, remote I/O, retries, and skew.
Elapsed time alone cannot identify the expensive resource or whether failures inflated cost.

### BD-OPS-011 -- Cost claims need a normalized unit

Tie cost to stable work such as input bytes, output rows, partition count, or business period under
comparable service/engine settings. Do not compare raw currency across unequal scope.

### BD-OPS-012 -- Terminal evidence is a packet, not a health score

Return identifiers, manifests, attempts, publication state, controls, observations, blockers, and
next action. Use categorical findings; never collapse distributed uncertainty into a score.

## Partial-output diagnosis

1. Bind the logical run to every physical attempt.
2. Compare intended input scope with the observed input manifest.
3. Determine the sink's commit/visibility boundary.
4. Compare visible output objects across failed and successful attempts.
5. Reconcile logical keys/control totals and quarantine counts.
6. Classify `clean`, `needs-evidence`, or `blocked`; do not rerun.
7. End on `../checklists/operational-evidence-checklist.md`.
