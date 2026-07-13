# DAX Model Review Checklist

Run when checking a semantic model for the DAX prerequisites a contract or measure needs (the
`model_review` phase). Copy it, check each box against the actual model, and record any unmet
prerequisite as a blocker — never assume it. References point to best practices (`BP-*`) and
analyzer rules (`AR-*`).

## Date & time foundation
- [ ] A dedicated **Date table** exists, is contiguous (every day across all referenced years), with a unique Date column (BP-001, AR-TI-002).
- [ ] The Date table is **Marked as Date Table** (BP-001) and Auto Date/Time is disabled (BP-002, AR-TI-003).
- [ ] Role-playing dates (e.g. Order vs Ship date) have inactive relationships activated via `USERELATIONSHIP` where needed (AR-REL-001).

## Schema shape
- [ ] **Star schema**: attributes pushed into dimensions, fact kept narrow (BP-003).
- [ ] Relationships are single-direction by default; any bi-directional one is justified, not a crutch (AR-BIDI-001).
- [ ] Helper / key columns used only for sort/relationship are hidden (BP-004).

## Keys, grain & uniqueness
- [ ] Each dimension's key is **verified unique** (hand-off evidence from `bi-sql-knowledge` / Gold Ready) — not believed.
- [ ] Fact grain is stated and matches what the measures assume (additivity depends on it).
- [ ] Snapshot facts are modeled as snapshot tables where a metric is semi-additive (not frozen into calculated columns — BP-012).

## Contract binding (Semantic Model Ready)
- [ ] Every measure binds to an **approved metric contract** (`metric-contract-checklist.md`); orphan measures are findings.
- [ ] Each contract's `requires_model_features` are present in this model (date table, relationships, param tables, config-table integrity).
- [ ] Disconnected parameter / what-if tables exist where a contract needs them, with `SELECTEDVALUE` defaults (AR-PARAM-001).
- [ ] Segmentation config tables have contiguous, non-overlapping ranges (AR-SEG-001).

## Verdict
- [ ] Result is a **model-review verdict**: prerequisites met vs missing, each missing one a named blocker.
- [ ] Any unmet prerequisite → the model is **not** Semantic Model Ready; record the blocker and stop. Do not fake a date table, relationship, uniqueness, or grain (DAX stop rules).
- [ ] When met, the model is the hand-off to dashboard design (measures bound to approved contracts).
