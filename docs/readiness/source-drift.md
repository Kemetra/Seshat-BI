# Source Drift

Planning (docs/templates; no runtime code) -- DESIGN ONLY (roadmap F014, "Later" tier).

A Source-Ready COMPANION doc. Source Ready (stage 1) certifies a source ONCE; this
re-certifies it OVER TIME. It defines what "the source no longer matches its recorded
profile" means as a first-class, measurable readiness signal -- surfaced as evidence +
blockers that can move a table's Source Ready status from `pass` to `warning` or
`blocked`. It generalizes the narrow "Cross-file schema drift" check already in
`templates/source-profile.md` across time/versions.

## Scope -- DESIGN ONLY (the measure/judge boundary)

- **In scope (this slice):** the drift taxonomy, the `source-drift-report.md` template,
  the re-profile/compare checklist (`docs/checklists/source-drift.md`), the Source Ready
  status mapping, and the forbidden-actions list. Reviewable text, no side effects.
- **Out of scope (deferred seam):** a drift-detection RUNTIME -- opening a connection,
  re-profiling live rows, diffing two profiles programmatically. There is NO `retail
  drift` CLI and NO comparator in `src/retail/` here. The mechanical re-profile reuses
  the existing deferred-live `profile.py` path (Principle VIII) WHEN that seam is built.
  Absent the live boundary, a run is `[PENDING LIVE RE-PROFILE]` + `warning`, never a
  fabricated comparison.
- **Always a human seam where it touches grain/identity/returns/PII** (Principle V) --
  automation MEASURES and CLASSIFIES; it NEVER self-grants a re-`pass` on those classes.

## What drift is

Drift = a measured difference between a **baseline source profile** (the committed
`mappings/<table>/source-profile.md` that earned `pass`) and an **observed re-profile**
of the same `<schema>.<table>` taken later, using the SAME measures (`'' OR NULL`
missingness RC5; candidate-PK uniqueness `COUNT(*) = COUNT(DISTINCT pk)` with 0 NULL PK,
RC2; returns from the authoritative billing column, RC8 -- never a measure sign).

## The drift taxonomy (nine classes)

| Class | What changed | Default severity | Why |
|-------|--------------|------------------|-----|
| **Column added** | a column present now, absent in baseline | `warning` | new signal may be wanted or noise; never auto-adopted |
| **Column removed** | a baseline column now absent | `blocked` | a mapping/silver cast may reference it; build breaks |
| **Column retyped** | landed type differs | `warning` (auto) / `blocked` (if it touches a key/measure) | a cast may now lose data or fail |
| **Missingness shift** | `'' OR NULL` rate moved beyond a recorded tolerance | `warning` | population change can break grain or measure totals |
| **Cardinality shift** | distinct count moved beyond tolerance | `warning` | drop/keep + dimension-build decisions hinge on this |
| **Grain/PK drift** | the recorded candidate PK is no longer unique, OR the row-vs-entity ratio moved | `blocked` | **Principle-V human seam** -- grain is never auto-rejudged |
| **Returns-rule drift** | the authoritative returns column changed population/meaning, or disappeared | `blocked` | **Principle-V human seam** -- returns identity is a judgment call |
| **Semantic-pair drift** | a baseline 1:1 code/label (or id->name) pair is no longer 1:1 | `warning` (auto) / `blocked` (if it underpins identity) | dimension build + identity may be wrong |
| **PII surface drift** | a column now appears that looks like PII, or a dropped-PII column reappeared | `blocked` | **Principle-V human seam** -- PII publish-safety is never auto-decided |

Two firm rules over the whole taxonomy:

1. **No fake confidence (#9).** A drift report carries the MEASURED signal (the
   before/after numbers and the class) + a status + blocking reasons -- never a single
   rolled-up drift "score". A per-class magnitude (e.g. "missingness 3.1% -> 11.7%") is
   a MEASUREMENT and is allowed; a "drift score: 0.62" is FORBIDDEN until scoring rules
   are defined (`readiness-model.md`).
2. **Grain / identity / returns / PII drift is a Principle-V human seam.** The detector
   MEASURES and CLASSIFIES and raises a blocker; it does NOT re-decide grain, re-rule
   PII, or re-pick the returns column. Those land in `unresolved-questions.md` for the
   named owner.

## Source Ready status mapping (the four spine statuses only)

| Drift outcome | Source Ready status |
|---------------|---------------------|
| No material drift (every class within recorded tolerance) | `pass` -- evidence cites the drift report; `next_action`: "no re-mapping needed; baseline still valid" |
| Only non-fatal classes present | `warning` -- evidence cites the report; does NOT auto-promote |
| Any fatal class present (removed column, or any Principle-V class) | `blocked` -- `blocking_reasons[]` enumerate the fatal classes |
| No baseline `source-profile.md` exists | not "drifted" -- the table is `not_started`/awaiting first profile; the detector does NOT run |
| Re-profile unavailable (no DSN / no `db` extra) | `[PENDING LIVE RE-PROFILE]` + `warning`; never a fabricated comparison |

## Downstream-invalidation rule

A `blocked`/`warning` drift at Source Ready makes downstream `pass` stages
(Mapping/Silver/Gold/...) SUSPECT and requiring RE-confirmation against the new shape.
The detector FLAGS this; it MUST NOT silently demote or auto-`pass` any downstream stage
-- the human/agent re-runs the stage gate.

## Forbidden actions (Principle-V seams; never auto-resolved)

- NEVER propose a new grain / candidate PK when `grain/PK drift` fires -> raise it for
  the analyst.
- NEVER re-pick the returns column or re-rule a return when `returns-rule drift` fires
  -> raise it for the analyst.
- NEVER make a publish-safety ruling when `PII surface drift` fires -> raise it for
  governance; the default stays `drop` (a reappeared dropped-PII column is the most
  dangerous case and is called out explicitly).
- NEVER auto-assert entity identity when `semantic-pair drift` underpins identity ->
  raise it for the analyst / data-owner.
- NEVER emit a rolled-up drift "score" -> statuses + measured magnitudes + blockers only.
- NEVER fabricate a comparison when the live boundary is absent -> `[PENDING LIVE
  RE-PROFILE]` + `warning`.

## See also

- The stage this advances: `source-ready.md` (the one-time certification this
  re-certifies over time); the model: `readiness-model.md` ("No fake confidence"); the
  sequence: `readiness-pipeline.md`.
- The blank a drift run fills: `../../templates/source-drift-report.md`; the
  re-profile/compare checklist: `../checklists/source-drift.md`.
- The machine-readable findings contract (seam only; the JSON shape a future detector
  emits -- same nine classes, same forbid-score / Principle-V rules, no runtime wired to
  it yet): `../../schemas/source-drift-findings.schema.json`.
- The baseline it drifts FROM: `../../templates/source-profile.md` (its "Cross-file
  schema drift" check is the narrow seed this generalizes); the Principle-V handoff:
  `../../templates/unresolved-questions.md`.
- The measures reused: `../decisions/0002-retail-cleaning-defaults.md` (RC2/RC5/RC8); the
  deferred-live profiler the runtime will reuse: `../../src/retail/profile.py`.
- The roadmap row: `../roadmap/roadmap.md` (F014, Layer 2, "Later"; filed under spec dir
  015). A filled worked example under `../worked-examples/` is a baseline, an example
  not the schema.
