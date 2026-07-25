# Joins, Merge Cardinality, and Fan-Out

Use this route before and after any dataframe merge. End on
`checklists/merge-fanout-checklist.md`.

## Decision this route supports

Decide whether a proposed merge preserves the intended grain and whether its unmatched
and multiplied rows are acceptable under the source contract.

## Required evidence

- left/right row meaning and declared grain;
- join keys and null-key counts;
- key multiplicity on both sides;
- expected relationship (`1:1`, `1:m`, `m:1`, or intentionally `m:m`);
- before/after row counts and additive controls.

## Reasoning sequence

- **PY-CN-117 — State both input grains.**
- **PY-CN-118 — Cardinality is a contract, not an observation after failure.**
- **PY-CN-119 — Test key uniqueness on the side expected to be one.**
- **PY-CN-120 — Fan-out factor measures multiplication.** Compare matched output rows
  with matched input identities, overall and by key.
- **PY-CN-121 — Unmatched keys are evidence.** Record left-only/right-only counts and
  representative non-sensitive patterns.
- **PY-CN-122 — Null keys need explicit treatment.** Do not let missing identities
  become a synthetic match.
- **PY-CN-123 — Overlapping columns need lineage.** Suffixes do not resolve which
  field is authoritative.
- **PY-CN-124 — Reconcile after merge.** Recheck target grain, row counts, and additive
  totals that should be conserved.

**PY-PB-015 — Pre-merge cardinality review:** declare grains, profile keys, and state
the expected relationship.
**PY-PB-016 — Post-merge fan-out diagnosis:** localize multiplicity by key, compare
controls, and identify which side violates the contract.

**PY-BP-013 — Use explicit merge validation** when the dataframe engine supports it.

## Failure modes

- joining on a descriptive label instead of a governed key;
- many-to-many merge treated as harmless;
- measures from the one-side repeated at the many-side grain;
- unmatched rows silently dropped by an inner join;
- suffix columns retained with unclear authority.

## Evidence-based verdict

- **CLEAN** — expected cardinality holds, grain is preserved or intentionally changed,
  and controls reconcile.
- **BLOCKED** — join key, cardinality, or unmatched-key disposition is unknown.
- **HANDOFF** — route upstream key defects to mapping/SQL; route distributed join
  topology to Big Data.

## Stop and handoff

Do not aggregate away fan-out evidence. Resolve the merge contract first.
