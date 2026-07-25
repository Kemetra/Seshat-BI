# Profiling and Source Inspection

Walk this route before cleaning a freshly loaded dataframe. End on
`checklists/dataframe-review-checklist.md`; profiling evidence proposes facts but grants
no readiness.

## Decision this route supports

Determine whether the source's observed structure, grain candidates, and data-quality
risks are understood well enough to plan source preparation.

## Required evidence

- immutable source reference and extraction boundary;
- observed row/column counts;
- full column inventory;
- expected grain or candidate identity;
- source contract or mapping evidence where available.

## Reasoning sequence

**PY-PB-012 — Evidence-first profile**

1. **PY-CN-098 — Capture shape with provenance.** Record counts with source revision,
   not as an isolated screenshot.
2. **PY-CN-099 — Inventory every field.** Record label, storage dtype, non-null count,
   and representative format without exposing sensitive values.
3. **PY-CN-100 — Test candidate identity.** Measure duplicate combinations and null
   keys; do not promote a key from naming alone.
4. **PY-CN-101 — Measure missingness by field and critical segment.** A global null
   rate can hide a fully missing branch or period.
5. **PY-CN-102 — Inspect cardinality and frequency concentration.** Distinguish
   identifiers, categories, constants, and high-cardinality free text.
6. **PY-CN-103 — Inspect ranges and parse validity.** Use business-safe minima/maxima,
   invalid counts, and quantiles; samples alone are insufficient.
7. **PY-CN-104 — Separate observation from expectation.** "Observed unique" and
   "declared primary key" are different evidence.

**PY-BP-010 — Profile before mutation.** Do not trim, coerce, deduplicate, or fill
values until the raw profile is recorded.

## Failure modes

- profiling only `head()`;
- exposing raw PII in examples;
- claiming grain from distinct-count similarity;
- missing segment-level null or freshness gaps;
- cleaning before preserving invalid-value counts.

## Evidence-based verdict

- **CLEAN** — structure, candidate grain, missingness, cardinality, ranges, and
  provenance are recorded.
- **BLOCKED** — source revision, candidate grain, or critical-field evidence is absent.
- **HANDOFF** — route dtype, null, merge, or date findings to the matching resource.

## Stop and handoff

Live database profiling belongs to `seshat profile` and requires a DSN. Without it,
label facts `[PENDING LIVE PROFILE]`; never fabricate observed values.
