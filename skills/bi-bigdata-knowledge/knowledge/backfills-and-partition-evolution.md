# Backfills and Partition Evolution

> Review supplied plans and evidence for distributed historical rewrites. Do not start a backfill,
> rewrite partitions, compact files, or change a table specification.

## Required evidence

- declared backfill scope, source watermark/history, live-processing window, and ownership;
- existing and proposed partition specifications plus table-format/version history;
- immutable input/output manifests and atomic publication/rollback mechanism;
- late-data policy, deduplication/write identity, controls, and downstream consumer compatibility.

### BD-BF-001 -- A backfill is a versioned historical correction

Record why the history changes, exact affected business periods/keys, source revision, code
revision, and intended output version. "Rerun everything" is not an evidence boundary.

### BD-BF-002 -- Separate live and backfill ownership

Define whether live ingestion pauses, writes a disjoint window, or coordinates through versioned
publication. Overlap without coordination can make the newest result depend on arrival order.

### BD-BF-003 -- Use half-open windows and explicit watermarks

Represent adjacent processing intervals without double inclusion and record the watermark used.
The upstream time/grain contract owns semantics; this card owns safe distributed scope.

### BD-BF-004 -- Late data needs a bounded reopening policy

Document which historical partitions may reopen, how late arrivals are discovered, and when a
period becomes immutable. An unbounded rewrite loop is not a policy.

### BD-BF-005 -- Backfill writes must be idempotent

Stable business/version keys plus replace/merge/atomic-swap semantics prevent repeated backfill
attempts from duplicating output. Validate with attempt and manifest evidence.

### BD-BF-006 -- Partition evolution changes physical layout, not business grain

Record old/new partition specs and which files use each. Table formats may support mixed specs;
path-reading consumers may not. The logical result contract must remain unchanged.

### BD-BF-007 -- Partition values are not source truth

When historical files were written under different specs or derivations, validate partition
metadata against row/table statistics and source versions before pruning or rewriting.

### BD-BF-008 -- Compaction must preserve table contents

Compaction changes file layout, not logical rows. Compare table snapshot/version, row count,
declared-grain uniqueness, null/quarantine counts, and additive controls before/after.

### BD-BF-009 -- Optimize-file size with workload evidence

Target file size/partition count depends on engine, scan pattern, object-store overhead,
concurrency, and write cadence. Thousands of tiny files are evidence; one universal size is not.

### BD-BF-010 -- Publish and rollback are part of the review

Name the atomic publication point, downstream cache/catalog refresh, validation gate, rollback
version, retention implications, and owner action. A technically complete rewrite is not safe
until consumers can see one coherent version.

## Review sequence

1. Freeze exact historical and live windows.
2. Bind source/code/table versions and manifests.
3. Check retry/write identity and publication atomicity.
4. Compare old/new partition specs and consumer behavior.
5. Reconcile logical content before/after backfill or compaction.
6. Record rollback evidence and named execution owner.
7. End on `../checklists/operational-evidence-checklist.md`.

