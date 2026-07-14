# Contract: Portfolio Watch Summary artifact

**Kind**: read-only output artifact (NOT a gate, NOT a `retail check` rule).
**Producer**: `src/seshat/portfolio_watch.py` (pure composition) via the
`portfolio-watch` skill and, optionally, the one narrow `retail watch --format json`
surface (research D7).
**Consumer**: a human team lead / the agent presenting the recurring summary.

This contract fixes WHAT the summary must contain and the invariants it must hold. It
does NOT fix the concrete serialization (field casing, single-file vs split) -- that is a
tasks-level detail.

## Required content (per FR-001..FR-006, FR-020)

- One entry per governed scope the readiness spine tracks (FR-002), each with:
  - `current_stage` (one of the seven spine stages),
  - `dimensions[]` -- one Covered Dimension Finding per covered dimension, each with a
    truthful `state` (`covered` | `[PENDING LIVE]` | `stale` | `not_applicable_with_reason`
    | `unreadable`), a shipped `class` when `covered`, an optional `measured` magnitude, a
    committed `evidence` citation (required when `covered`), and a `source_surface` citation,
  - `open_blockers[]` relayed from readiness `blocking_reasons`,
  - `requires_human_attention` (bool) -- true when the top-ranked open condition is an
    unmet/invalid approval or a relayed Principle-V drift blocker (FR-006),
  - `prioritized_next_action` -- `{category, action}` where `category` is chosen by the
    shipped `readiness_classify` fixed rank and `action` is the scope's RELAYED
    `next_action` (FR-005),
  - `change_labels[]` -- per-condition `new` / `resolved` / `unchanged` /
    `current_condition_no_baseline` from the snapshot diff.
- A `portfolio` block with measured counts (`scope_count`,
  `scopes_requiring_attention_count`) and `scopes_with_no_evidence[]` (FR-017).
- `generated_at_revision` (current git HEAD) for staleness comparison.
- A `disclosure` block reusing the shipped disclosure-scan shape (SEC-002).

## Invariants (fail the contract if violated)

- **INV-1 (no score)**: no numeric health/confidence/priority/quality value appears.
  Counts and measured magnitudes are allowed; a rolled-up score is not (FR-020).
- **INV-2 (citation)**: every `covered` finding carries a committed `evidence` path; a
  covered finding with no traceable source is a defect (FR-004).
- **INV-3 (truthful degradation)**: any dimension not cleanly readable is one of the four
  non-`covered` states, never silently `covered`/clean (FR-013..FR-016).
- **INV-4 (one next action)**: exactly one `prioritized_next_action` per scope, its
  `category` equal to the highest-ranked open category by the shipped rank; `action` is
  relayed, never synthesized (FR-005, SC-003).
- **INV-5 (no origination)**: every relayed named-human seam (approval / grain / returns /
  PII) names an `owner` and asserts no ruling (FR-021, SC-010).
- **INV-6 (read-only)**: producing the summary writes only the summary + the snapshot; no
  per-scope artifact changes, no approval recorded, no stage promoted (SC-008).
- **INV-7 (no secret)**: no DSN/secret/real host value appears; shipped redaction is
  preserved (SEC-002).
- **INV-8 (determinism)**: identical inputs + identical snapshot -> byte-identical summary
  and change labels (SC-006).

## Explicitly NOT in this contract

- No `pass`/`fail` gate exit; Watch never blocks a commit or PR (it is not a gate, FR-019).
- No live DB read (SEC-001); live-only dimensions are `[PENDING LIVE]`.
- No scheduler trigger (FR-024); "recurring" = re-runnable + baseline-diffable.
