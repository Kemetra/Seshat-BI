# Implementation Plan: 087-decision-aid-layer

**Branch**: `087-decision-aid-layer` (worktree ZEUS) | **Spec**: `spec.md` | **Clarify**: `clarify.md`
**Status**: Draft (stops at ratify ledger; NOT approved, NOT implemented)

## Approach

Purely ADDITIVE template authoring. Add decision-readiness fields to the metric
contract, a narrative block to the page blueprint, driver-visual enum entries to
the visual spec, and one new driver-decomposition template. No `retail check`
rule, no scaffold, no 5-place wiring, no DAX/SQL/PBIR (DEFINE-only). All values
are generic placeholders.

## Constitution / boundary check

| Principle / boundary | How honored |
|---|---|
| No numeric score (#9 / never_fabricate) | thresholds are categorical band boundaries in the metric's own unit; explicit comment forbids a 0-100 score |
| DEFINE / CHECK boundary (F009/F011A) | adds template FIELDS only; no rule, no `powerbi/` read, no DAX/SQL |
| Reference-by-name (VII / four-surface) | narrative + drivers cite contract NAMES; never inline a formula/DAX/gold column |
| Agent stops at judgment calls (V) | direction/target/bands/action/narrative are owner-supplied placeholders; unfilled-on-approved = blocking condition, never agent-invented |
| Gold-only (III) | drivers reference contracts (which bind gold); no new data path |
| Schema safety | verified: AL1/AL2 read metric-contract keys tolerantly + exempt the template; ADL-block precedent (spec 058). No rule-scope change. |

## Components

1. **`templates/metric-contract.yaml`** (+3 blocks, additive):
   - `direction_of_good: higher|lower|target_band` (placeholder + Principle-V note)
   - `thresholds:` `{target, good, warn, critical}` -- named band boundaries, unit-
     of-the-metric, NO score (comment enforces)
   - `action_on_breach:` `{by band}` -- plain-language owner action
   - Authoring note: unfilled direction/target on a `pass` = blocking condition.
2. **`templates/dashboard-page-blueprint.yaml`** (+1 block, alongside sections/visuals):
   - `narrative:` `{headline, so_what, recommended_action, key_exception}` --
     reference-by-name, no inlined formula/DAX; orphan-reference note.
3. **`templates/visual-spec.yaml`** (enum extension):
   - `visual_type` gains `key_influencers | decomposition_tree | smart_narrative`
     with a "design intent; F016 renders" note.
4. **`templates/driver-decomposition.md`** (NEW artifact):
   - a metric = factor x factor relation in plain INTENT; each factor a contract
     name; NO DAX/number; header states the boundary (mirrors metric-contract's
     define/check + no-inline discipline).

## What this does NOT touch (scope guards)

- No `retail check` rule (FR-010; optional enforcement deferred).
- No backfill of filled contracts/blueprints under `mappings/` or
  `reports/blueprints/` or `skills/retail-kpi-knowledge/contracts/` (FR-011;
  business-value = Principle V, owner-gated separate step).
- No DAX generator / definition-block change.

## Test strategy

DEFINE-only, so "tests" = validity + boundary checks, not rule fixtures:
- YAML validity of each edited template (parses; placeholders intact).
- A grep-level boundary assertion: the new `thresholds`/narrative blocks contain no
  DAX-ish tokens (SUM(/DIVIDE(/gold. column refs) and no 0-100 score field. (Can be
  a tiny test or a manual review item -- no @register rule.)
- `retail check` stays green (no rule added; template exempted from contract scans).

## Sequencing

One PR. US1 (contract fields) -> US2 (narrative) -> US3 (driver vocab + artifact).
No registry/count change, so no serialization point (unlike B1/I3). See tasks.md.

## Risks

- **Scope creep into backfilling real KPIs** -> explicitly out (FR-011); the ratify
  ledger states template-only.
- **A reviewer reading "thresholds" as a score** -> the comment + SC-001 assert
  categorical-bands-not-score; the adversarial reviewer confirms.
- **Combined ratify spans 3 governed artifacts** -> the ratify ledger lists all
  three (clarify C2).
