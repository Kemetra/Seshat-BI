# Data Model: Personal-Data-Touch Notice

Phase 1. The composer's in-memory model. All fields are READ from
`mappings/<table>/source-map.yaml`; none is authored.

## Input: source-map.yaml (read-only)

Relevant committed fields (see `templates/source-map.yaml` schema; filled
instance at `mappings/retail_store_sales/source-map.yaml`):

- `columns[]` -- each with:
  - `source_name` (str) -- the column identity.
  - `pii` (bool) -- the PII flag. The composer acts on `pii: true` columns.
  - `decision` (str: `keep` | `drop`) -- the mapping keep/drop decision.
  - `deviation_ref` (str, optional) -- NEW field (ratify OPEN-2): a kept-PII
    column names its governing deviation by exact `id` (e.g. `deviation_ref: RC4`).
    Absent -> the kept-PII column is `undecided` (GAP). Added to
    `templates/source-map.yaml` (generic) and back-filled on the fixture.
  - `reason` (str) -- the mapping rationale; for a DROPPED PII column this
    carries the drop disposition.
- `defaults.deviations[]` -- each with:
  - `id` (str, e.g. `"RC4"`) -- the deviation id.
  - `reason` (str) -- for RC4, the governance disposition string a KEPT PII
    column echoes (e.g. "customer_id is a pseudonymous surrogate ... Q1 RESOLVED
    2026-06-25 (data owner): keep, no raw PII.").
  - `detail_in` (str) -- a pointer (NOT parsed for content; Clarification Q1).

## Entities

### PiiColumnFinding

One per `pii: true` column. The unit the notice renders.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `column` | str | `columns[].source_name` | verbatim |
| `pii` | bool (always true here) | `columns[].pii` | only `true` columns become findings |
| `decision` | str | `columns[].decision` | `keep` \| `drop` \| (absent -> unknown) |
| `disposition` | str \| None | see resolution below | VERBATIM; None -> GAP |
| `disposition_source` | str \| None | in-file location of the disposition | cited path + locus (e.g. `defaults.deviations[RC4].reason`) |
| `state` | enum | derived | `decided_kept` \| `decided_dropped` \| `undecided` \| `inconsistent` |

**Disposition resolution** (D3/D4):
- DROPPED PII column (`decision: drop`) -> `disposition` = the column's own
  `reason`; `state` = `decided_dropped` (a `reason` is expected on a drop).
- KEPT PII column (`decision: keep`) -> `disposition` = the `reason` of the
  `defaults.deviations[]` entry whose `id` EXACTLY matches the column's
  `deviation_ref` field (ratify OPEN-2 RULED 2026-07-09: explicit
  `deviation_ref`, exact id-match, no text heuristic). `state` = `decided_kept`.
  If the column has NO `deviation_ref`, or its `deviation_ref` matches no
  deviation `id` -> `disposition` = None, `state` = `undecided` (GAP). The
  composer NEVER text-matches column names inside deviation prose and NEVER
  guesses -- an unlinked kept-PII column is a GAP, never a false clearance
  (Principle-V hazard). The matched deviation's `reason` is the authoritative
  disposition text (not the column's own `reason`).
- A `pii: true` column whose `source_name` appears in `columns[]` with BOTH a
  `keep` and a `drop` decision (an intra-file contradiction) -> `state` =
  `inconsistent`, rendered as a GAP naming both in-file loci and marked "NOT
  cleared" -- never a silent pick, never a decided disclosure (FR-010).
  Implemented: `_conflicting_columns` computes the contradicted `source_name`
  set; `_finding_for_column` marks those `inconsistent` BEFORE the keep/drop
  branches.

### PiiNotice (the output model)

| Field | Type | Notes |
|-------|------|-------|
| `table` | str | the target table |
| `source_path` | str | repo-relative `mappings/<table>/source-map.yaml` |
| `findings[]` | PiiColumnFinding | ordered by `source_name` as it appears in `columns[]` (stable, no invented ranking) |
| `no_pii` | bool | true when zero `pii: true` columns exist |
| `document_gap` | str \| None | set when `source-map.yaml` is missing/unreadable/columns-block-absent (FR-009) |
| `read_only_proof` | bool (always true) | marker mirroring blocker_explainer |

## State transitions

None -- a pure compose. Each run reads the current committed source-map and
overwrites the one output file idempotently.

## Validation rules (enforced by the verifier tests, FR-011)

- V1 (verbatim): for every finding with `state in {decided_kept, decided_dropped}`,
  the rendered disposition text MUST be a verbatim substring of the committed
  source field it cites (character-for-character; SC-002).
- V2 (never omit): every `pii: true` column in the source appears as exactly one
  finding in the output (FR-004, SC-003) -- count of findings == count of
  `pii: true` columns (+ any document-level gap case).
- V3 (never clear): a finding with `state == undecided` renders as an explicit
  GAP and contains no clearance token ("safe", "cleared", "no PII risk",
  "approved"); the composer authors no such token anywhere (FR-005, SC-004).
- V4 (no score): output contains no numeric score/risk-level/"N of M" token
  (FR-006, SC-004).
- V5 (read-only): after a run, `git status` shows only `pii-touch-notice.md`
  new/modified; no upstream artifact changed (FR-008, SC-005).
- V6 (generic): the composer carries no hardcoded column name / PII category;
  demonstrated on two distinct tables (FR-012, SC-006).
