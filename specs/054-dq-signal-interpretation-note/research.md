# Research: DQ-Signal Interpretation Note

**Feature**: `054-dq-signal-interpretation-note` | **Date**: 2026-07-01

Phase-0 decisions. Two load-bearing premise errors the idea's synthesis carried are
CORRECTED here so the plan does not inherit them.

## Decision 1: Where the `-1` unknown-member count actually lives

- **Question**: The synthesis claimed `validate.py` / `run_live_checks` "already
  records the -1 unknown-member counts." Is that true?
- **Finding**: FALSE. `src/retail/validate.py` has four checks (PK, date-coverage,
  orphan-FK `check_orphan_fks` at L216-242, reconciliation), all emitting
  Severity.ERROR on defects. `check_orphan_fks` counts HARD orphans (an FK with no
  matching dim). After the ratified RC14 default `COALESCE(fk, -1)`, rows routed to
  the `-1` unknown member are NOT orphans -- they pass silently. There is no
  `-1`-tally check, no sub-ERROR severity for it. The count (when it exists) is a
  HAND-FILLED `warning` row in the table's `data-issues.md` (template L12/L28-30),
  produced by a separate analyst query.
- **Decision**: The template READS the count by reference from `data-issues.md`. It
  NEVER assumes a tooling-emitted `-1` tally and NEVER runs a query.

## Decision 2: Which readiness stage this advances

- **Question**: The synthesis called it a "Stage 4 GOLD gap." Correct?
- **Finding**: The count is PRODUCED at Stage 4 (Gold Ready live validate,
  `docs/readiness/gold-ready.md`) but the caveat / stakeholder-communication surface
  is Stage 7 Publish Ready (`docs/readiness/publish-ready.md` L30,L57; handoff-pack
  Known-gaps L59-73). The `bi-handoff-pack.md` L70-71 ALREADY mandates surfacing
  "<N> rows land on the -1 unknown member of dim_<x>" with the count.
- **Decision**: Frame the template as the interpretive SOURCE feeding the shipped
  Stage-7 Known-gaps section, produced-at-4 / consumed-at-7. The formal stage-of-
  record + any F-number is a roadmap/governance call left OPEN (spec ##
  Clarifications, Principle V).

## Decision 3: Is the artifact non-duplicative?

- **Finding**: The `signal -> affected KPI -> direction-of-distortion` mapping
  exists NOWHERE today (grounding grep for "direction of distortion" / "affected
  KPI" / "understate" / "overstate" returns zero hits outside the idea backlog).
  `data-issues.md` stops at count + disposition; `bi-handoff-pack.md` surfaces the
  count but not the KPI or direction.
- **Decision**: Build the interpretive layer. `data-issues.md` stays the single
  source of truth for the number; this note references it and does not create a
  second home for the count (spec Q2).

## Decision 4: Template shape

- **Decision**: Mirror the discipline of `reconciliation-report.md` and
  `bi-handoff-pack.md`: a GENERIC banner (copy per table; C086 by reference only;
  ASCII/UTF-8 no BOM; no numeric confidence), a structured per-signal table with
  owner-gated analyst fill-in cells for KPI + direction, an explicit "none recorded"
  path, a PII publish-safety gate for person/customer dims, and a "See also" block.
  No new mechanism, no rule, no executor.

## Decision 5: Scope (spec Q1)

- **Decision**: Scope the template to the `-1` unknown-member signal only, not a
  general "any DQ signal" interpreter (YAGNI). A later spec can widen it; that is a
  reversible, easy expansion.
