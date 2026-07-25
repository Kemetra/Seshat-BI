# Dataframe Mental Model for BI

Use this route before profiling, merging, or aggregating when the dataframe's role is
unclear. End on `checklists/dataframe-review-checklist.md`.

## Decision this route supports

Decide whether a dataframe has a declared business row meaning, stable identity, and
enough evidence to enter source preparation.

## Required evidence

- source artifact and extraction boundary;
- one-row meaning stated in business terms;
- candidate identity columns;
- observed shape, labels, dtypes, and sample-independent distributions;
- upstream metric contract when metric fields are involved.

## Reasoning sequence

1. **PY-CN-086 — A dataframe is a labeled relation.** Rows are observations, columns
   are attributes, and the index is an alignment mechanism. The index is not a
   business key unless the source contract says it is.
2. **PY-CN-087 — Row meaning precedes operations.** State "one row represents ..."
   before selecting, joining, sorting, or grouping.
3. **PY-CN-088 — Shape is not grain.** `(rows, columns)` reports size; grain reports
   identity. Ten thousand rows can still contain duplicate business observations.
4. **PY-CN-089 — Labels, storage dtypes, and business meaning differ.** A column named
   `sales` does not establish net/gross meaning; an `int64` code is not a measure.
5. **PY-CN-090 — Alignment can change results.** Series operations align by index.
   Positional-looking expressions can introduce nulls or mismatches when indexes differ.
6. **PY-CN-091 — Mutation has provenance cost.** In-place edits obscure before/after
   evidence. Preserve the raw landing and record each derived frame boundary.

**PY-BP-008 — Declare dataframe role before transformation:** `raw landing`,
`profiled source`, `cleaned source`, `joined working set`, or `aggregated output`.

## Failure modes

- RangeIndex treated as a durable business key.
- Row count presented as proof of uniqueness.
- Column names used to infer metric meaning.
- Mixed-grain rows in one frame.
- Index alignment silently changing arithmetic.
- A cleaned frame overwriting the only raw evidence.

## Evidence-based verdict

- **CLEAN** — row meaning, candidate identity, role, and provenance are declared.
- **BLOCKED** — row meaning or authoritative source is missing.
- **HANDOFF** — continue to profiling; if the data cannot fit safely on one machine,
  hand off to `bi-bigdata-knowledge`.

## Stop and handoff

Do not define KPI policy here. Route unclear metric meaning to
`retail-kpi-knowledge`; route source mapping or approval to readiness.
