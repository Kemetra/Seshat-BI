# Feature Specification: Governed Two-Table Ratio Generation

**Feature**: 156
**Idea**: c19 -- Widen DAX generation to the actual-vs-target two-table shape
**Status**: Ratified by owner Ahmed Shaaban on 2026-08-25

## Goal

Generate and semantically verify an actual-divided-by-target measure whose two
sources are different gold tables, while keeping `binds_to` scalar and recording
the second table in the owner-approved sibling `compares_to` block.

## Functional Requirements

- **FR-156-001**: `templates/metric-contract.yaml` MUST define optional
  `compares_to` with `gold_table`, `columns`, and `pii_sensitive`, matching the
  scalar shape of `binds_to`.
- **FR-156-002**: Existing contracts without `compares_to` MUST retain their
  current behavior and generated output.
- **FR-156-003**: The variance-vs-target pattern MUST use `definition.kind:
  ratio`, with actuals as numerator and target as denominator; no new variance
  formula kind is introduced.
- **FR-156-004**: A shared, stdlib-only validator MUST compare a two-table
  definition with `binds_to` and `compares_to` and return deterministic refusal
  reasons without raising on malformed input.
- **FR-156-005**: A two-table ratio MUST bind the numerator table to
  `binds_to.gold_table` and denominator table to `compares_to.gold_table`.
- **FR-156-006**: Every source and filter column used by either definition side
  MUST appear in that side's binding `columns`; `count_rows` has no source
  column but still contributes its filter columns.
- **FR-156-007**: Both tables MUST be non-empty `gold.*` strings, both column
  collections MUST be non-empty string lists, and each optional
  `pii_sensitive` MUST be boolean.
- **FR-156-008**: `seshat generate` MUST validate the complete contract before
  emission and refuse with exit 1 and empty stdout on disagreement.
- **FR-156-009**: The approved metric-contract inventory MUST use the same
  validator so `seshat semantic-check` cannot report a false pass.
- **FR-156-010**: Valid output MUST round-trip through
  `check_measure_drift(...).status == "pass"` before it is returned.
- **FR-156-011**: The feature MUST NOT execute DAX, connect to a database,
  write under `powerbi/`, choose grain/threshold/missing-target policy, or grant
  an approval.

## Acceptance Scenarios

1. A contract whose numerator reads `gold.fct_actuals` and denominator reads
   `gold.fct_targets`, with matching bindings, emits a verified
   `DIVIDE(SUM(...), SUM(...))` measure.
2. Missing `compares_to`, mismatched tables, missing columns, malformed lists,
   non-gold tables, and malformed booleans are refused without traceback.
3. The generator CLI and approved-contract inventory report consistent reasons
   for the same disagreement.
4. Existing one-table base and ratio fixtures produce unchanged output.

## Source Design

The approved architecture, exclusions, and lifecycle are defined in
`docs/superpowers/specs/2026-08-25-adopted-ideas-completion-design.md`.
