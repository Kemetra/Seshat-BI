# Source Ready

Planning (docs/templates; no runtime code).

Stage 1 of the readiness spine. A profiled, understood source exists before any
mapping work begins. Maps to medallion-playbook Phase 1.

## Purpose

Establish that the raw source has been measured and proposed for understanding --
BEFORE a single source-map decision is made. A raw source is **either a DB
`<schema>.<table>` OR a standalone file (CSV / Excel)**; both land in bronze and both
are profiled through the same gate. "Ready" here means the mechanical numbers are
recorded and the semantic profile rows are PROPOSED for human confirmation, never
invented. This is the floor every later stage stands on: no mapping, no silver, no
judgment calls yet.

## Required artifacts

| Artifact | What it must contain |
|----------|----------------------|
| `mappings/<table>/source-profile.md` | `Source kind` (db-table / csv / excel); row count, column count; per-column missingness measured as `'' OR NULL` (not `IS NULL` alone); candidate-key uniqueness proof; returns-column population; PROPOSED semantics. **For a file source (csv/excel):** the File-source addendum too -- format, encoding (`[PROPOSED]`), delimiter/quote (csv), header row, and the enumerated in-scope sheet list (Excel) |

The profile is the ONLY required artifact at this stage. The other four mapping
artifacts (`source-map.yaml`, `assumptions.md`, `unresolved-questions.md`,
`reconciliation-report.md`) belong to Stage 2 (Mapping Ready) and MUST NOT be
authored here.

**Optional strengthening artifacts (Layer 2 -- Source Intelligence).** The semantic
half of the profile may additionally be recorded in two OPTIONAL generic artifacts that
strengthen this stage's `evidence[]` without changing its gate: a Business Meaning
Registry (`templates/business-meaning-registry.md`) and an Arabic<->English retail term
Dictionary (`templates/retail-term-dictionary.md`). They are NOT required and do NOT
add a new gate -- the profile remains the one required artifact and the gate stays a
review. See `docs/source-intelligence.md` for how a filled copy contributes evidence.

## Required checks

| Check | Gate |
|-------|------|
| Profile review | The numbers are recorded AND the semantic rows are PROPOSED (not invented), flagged for human confirmation |

This stage has no `retail check` / `retail validate` gate. The gate is a review:
confirm the mechanical numbers came from a read-only profiling pass over the landed
source, and confirm each semantic proposal is marked as a proposal awaiting sign-off,
not stated as fact.

- For a **DB source**, the numbers come from `profile.py` over a read-only connection.
- For a **file source (csv/excel)**, there is no shipped mechanical profiler yet
  (`profile.py` is DB-only). Until one lands, a file source is profiled in
  deferred-boundary mode: record the File-source addendum + per-column rows as
  `[PENDING LIVE PROFILE]`, mark the detected encoding/delimiter/header `[PROPOSED]`,
  and record `warning` -- never a fabricated `pass`. The file-grain reasoning that
  guides this pass lives in `skills/bi-python-knowledge/` (route: profile a freshly
  loaded source).

## Statuses

| Status | Meaning HERE |
|--------|--------------|
| `not_started` | no `source-profile.md` for `<table>` yet |
| `blocked` | a required number is missing/unmeasurable, or semantics were INVENTED instead of proposed -- see Blocking reasons |
| `warning` | profile recorded but with a noted caveat (e.g. `[PENDING LIVE PROFILE]` rows in deferred-boundary mode) -- does not auto-promote |
| `pass` | every required number recorded from `profile.py`; semantics PROPOSED + flagged; evidence cites `mappings/<table>/source-profile.md` |

## Blocking reasons

- `mappings/<table>/source-profile.md` does not exist.
- Missingness measured with `IS NULL` alone (the `'' OR NULL` trap, RC5) instead
  of `'' OR NULL`.
- Candidate-key uniqueness not tested, or `is_unique` not recorded.
- Returns-column population not recorded.
- Semantic meaning INVENTED (business rollup, PII ruling, or returns column
  asserted) rather than PROPOSED for confirmation.
- Numbers fabricated because the live boundary was unavailable, instead of
  marking them `[PENDING LIVE PROFILE]`.
- **File source only:** `Source kind` is csv/excel but the File-source addendum is
  missing; encoding/delimiter/header ASSERTED as fact instead of `[PROPOSED]`; or (Excel)
  the sheets not enumerated and the profiled sheet not stated -- the first sheet assumed
  silently to be the data.

## Required owner / approval

Analyst confirms the proposed semantics. The mechanical numbers are
self-evidencing (recorded from `profile.py`); the SEMANTIC rows are PROPOSALS and
require the analyst to confirm meaning before this stage can read `pass`.

## Next allowed action

Begin mapping -- Stage 2 (Mapping Ready). Hand the confirmed profile to the
source-mapping workflow to author the source-map decisions.

## What the agent must NOT do

- Write ANY source-map decisions (`source-map.yaml` or sibling artifacts).
- Invent semantic meaning -- no business rollups, no PII rulings, no
  authoritative returns column asserted as fact.
- Touch silver: no `silver.*` SQL, no migrations.
- Emit a confidence number in place of the four explicit statuses.
- Fabricate profile numbers when the DSN / `db` extra is absent -- mark
  `[PENDING LIVE PROFILE]` and record a `warning` instead.

## See also

- `readiness-model.md` -- the four-status state model and the no-fake-confidence rule.
- `readiness-pipeline.md` -- the seven-stage sequence; this is stage 1 of 7.
- `mapping-ready.md` -- the next stage (the source-mapping gate).
- `source-drift.md` -- the companion that re-certifies this stage over time (shape/semantic drift as evidence + blockers).
- `../source-intelligence.md` -- Layer 2: how the OPTIONAL registry + dictionary feed this stage's evidence.
- `../../templates/business-meaning-registry.md`, `../../templates/retail-term-dictionary.md` -- the OPTIONAL semantic-proposal artifacts.
- `../../.claude/skills/source-mapping/SKILL.md` -- the skill that runs this stage; calls `profile.py` as the mechanical profiler.
- `../../src/retail/profile.py` -- the mechanical profiler (row/col counts, `'' OR NULL` missingness, candidate-PK proof).
- `../medallion-playbook.md` -- Phase 1, which this stage maps to.
- C086 is the first worked example -- a filled instance, not the schema: `../worked-examples/c086-pharmacy.md`.
