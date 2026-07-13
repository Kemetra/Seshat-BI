# Metric Contract Checklist

Fill this **before** writing a single line of DAX. A measure with no contract is a guess. Copy it,
answer every field, and record open questions instead of inventing answers. Fields mirror
`patterns/metric-contract-patterns.json` (`contract_field_spec`).

## Identity & intent
- [ ] **`contract_id`** assigned (stable, e.g. `MC-SALES-AMOUNT`).
- [ ] **`intent`** stated in one business sentence: what the metric means and to whom — not the formula.
- [ ] Owner / approver named. A metric's *meaning* is a human decision (Principle V); do not self-grant it.

## Grain & inputs
- [ ] **`grain`** stated: "one value of this metric is per ___" (e.g. per Date × Branch × Product).
- [ ] **`inputs`** listed: the base measures / columns it composes from. Built on base measures, not raw re-aggregation (BP-020).
- [ ] Source grain is **known and validated** (hand-off from `bi-sql-knowledge` / Gold Ready) — additivity reasoning depends on it.

## Additivity & filter behavior
- [ ] **`additivity`** declared: fully additive / semi-additive (over which dimension) / non-additive.
- [ ] Semi-additive or non-additive metrics carry the rule for totals (AR-ADD-001) — no silent additive total.
- [ ] **`filter_behavior`** stated: which filters it respects, which it clears, and why (KEEPFILTERS / REMOVEFILTERS intent — BP-024/025).

## Model prerequisites
- [ ] **`requires_model_features`** listed: marked Date table (BP-001), star schema (BP-003), specific relationships, uniqueness, snapshot table, disconnected param table.
- [ ] Each prerequisite is **confirmed against the model**, not assumed. Missing prerequisite → blocked, not faked (DAX stop rules).

## Output & validation
- [ ] **`output`** format stated: data type, format string, expected range / sign.
- [ ] **`validation_rules`** written: how to prove the number is right (a reconciliation target, a known total, a sanity bound).
- [ ] **`phase_support`** noted: generate / analyze / model_review.

## Verdict
- [ ] Every field above is answered or recorded as an explicit open question — no blanks treated as "fine".
- [ ] If grain, additivity, or filter behavior is unknown → **stop and request it**; do not write DAX (DAX stop rules).
- [ ] Contract handed to measure generation (`INDEX.md` row 3) or recorded as the Semantic-Model-Ready evidence a measure must bind to.
