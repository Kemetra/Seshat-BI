# Big Data Operational Evidence Checklist

## Identity and scope

- [ ] Logical run, physical job/stage/task/attempt IDs are recorded.
- [ ] Code/config, engine, input, and output versions are recorded.
- [ ] Intended scope and actual input partition/file manifest are attached.
- [ ] Declared upstream grain and validation contract are referenced, not redefined.

## Failure and publication evidence

- [ ] Retry/speculative-attempt history and deterministic write identity are known.
- [ ] Sink commit protocol and atomic visibility boundary are known.
- [ ] Staged, visible, superseded, and quarantined output manifests are distinguished.
- [ ] Failed attempts cannot leave unaccounted visible rows/files.

## Backfill and evolution evidence

- [ ] Backfill and live windows are explicit, disjoint or coordinated, and owner-assigned.
- [ ] Late-data/watermark policy and reopened partitions are recorded.
- [ ] Old/new partition specs and path-reading consumer compatibility are recorded.
- [ ] Compaction/backfill before-and-after controls preserve logical contents.
- [ ] Atomic publication, rollback version, retention, and catalog/cache actions are named.

## Cost/performance evidence

- [ ] Scheduler wait, compute, shuffle, spill, I/O, retries, skew, and resource usage are separated.
- [ ] Cost comparison uses equivalent work scope and a normalized unit.
- [ ] Proposed changes name confirming evidence and operational tradeoffs.

## Terminal packet

Return `clean`, `needs-evidence`, or `blocked`, followed by:

- run/version identifiers and manifests;
- observed publication state;
- control totals and quarantine evidence;
- operational findings and plausible causes;
- missing evidence/blockers;
- safe next action and named execution owner.

This is evidence presence and diagnostic state, never a health score, readiness pass, approval, or
authorization to run/retry/backfill/compact.
