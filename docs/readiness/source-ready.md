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
| `mappings/<table>/source-profile.md` | row count, column count; per-column missingness measured as `'' OR NULL` (not `IS NULL` alone); candidate-key uniqueness proof; returns-column population; PROPOSED semantics. **`Source kind` defaults to `db-table` when absent** (existing DB profiles need no change); set it to `csv`/`excel` ONLY for a standalone file source, and then also fill the File-source addendum -- format, encoding (`[PROPOSED]`), delimiter/quote (csv), header row, and the enumerated in-scope sheet list (Excel) |

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

This stage has no `seshat check` / `retail validate` gate. The gate is a review:
confirm the mechanical numbers came from a read-only profiling pass over the landed
source, and confirm each semantic proposal is marked as a proposal awaiting sign-off,
not stated as fact.

- For a **DB source**, the numbers come from `profile.py` over a read-only connection.
- For a **file source (csv/excel)**, the numbers come from `file_profile.py` -- the
  read-only file profiler. It computes the same mechanical set (row/col count,
  `'' OR NULL` missingness, distinct cardinality, candidate-PK proof) from the file's
  raw cells; CSV uses the stdlib (no extra), Excel uses the optional `files` extra
  (`pipx inject seshat-bi openpyxl` or `pip install "seshat-bi[files]"`). The
  file-grain reasoning that guides the read
  (encoding, delimiter, header row, sheet selection) lives in
  `skills/bi-python-knowledge/` (route: profile a standalone file source).

  **A file source reaches `pass` like a DB source does -- with one extra gate, and
  that gate is ENFORCED, not just prose.** The mechanical numbers self-evidence
  (recorded from `file_profile.py`). BUT a file has no declared schema, so the detected
  **encoding** (and, for CSV, the delimiter and header-row) is a `[PROPOSED]` inference
  that every text column rests on: a wrong encoding silently corrupts every label
  (PY-CN-082). Encoding-confirmation is therefore a GATING semantic proposal -- treated
  exactly like the semantic rows: the data owner must confirm the encoding (and
  delimiter/header) before this stage can read `pass`.

  This is machine-checked by **rule RS1**: mark the `source_ready` stage block with
  `source_kind: csv` (or `excel`) in `readiness-status.yaml`, and RS1 will REFUSE a
  `pass` on that stage until a matching `{stage: source_ready}` entry is recorded in
  `approvals[]` (the owner's encoding-confirmation). A DB source omits `source_kind`
  and is unaffected. Until confirmed, record `warning`, not `pass`. If no reader is
  available at all (Excel without the `files` extra), fall back to deferred-boundary
  mode: `[PENDING LIVE PROFILE]` + `warning`, never a fabricated `pass`.

## Statuses

| Status | Meaning HERE |
|--------|--------------|
| `not_started` | no `source-profile.md` for `<table>` yet |
| `blocked` | a required number is missing/unmeasurable, or semantics were INVENTED instead of proposed -- see Blocking reasons |
| `warning` | profile recorded but with a noted caveat (e.g. `[PENDING LIVE PROFILE]` rows in deferred-boundary mode; or a **file source** whose encoding/delimiter/header is still `[PROPOSED]`, unconfirmed by the owner) -- does not auto-promote |
| `pass` | every required number recorded from `profile.py` (DB) or `file_profile.py` (file); semantics PROPOSED + flagged; **for a file source, the owner has CONFIRMED the encoding (and delimiter/header)**; evidence cites `mappings/<table>/source-profile.md` |

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
- `../../src/seshat/profile.py` -- the mechanical profiler for a DB table (row/col counts, `'' OR NULL` missingness, candidate-PK proof).
- `../../src/seshat/file_profile.py` -- the mechanical profiler for a CSV/Excel file source (same measures, driver-free; CSV on the stdlib, Excel via the `files` extra).
- `../medallion-playbook.md` -- Phase 1, which this stage maps to.
- A filled worked example under `../worked-examples/` shows a completed instance, not the schema.
