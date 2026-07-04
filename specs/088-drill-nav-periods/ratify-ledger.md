# Ratify Ledger -- 088-drill-nav-periods

**STOP.** DEFINED and CHECKED, not APPROVED or IMPLEMENTED. Ratification is a human
edit the workflow is forbidden to make (Principle V, `never_self_grant_approval`).

**Branch**: `088-drill-nav-periods` (worktree ZEUS)
**Feature**: DEFINE-only next gap wave -- #4 drill/nav INTENT + #5 period-over-period
contract STRUCTURE. Two feature areas, two risk stories (see below).
**Chain**: agent-driven spec-kit (specify -> clarify -> plan -> tasks -> analyze ->
adversarial review -> this ledger).

## Eligibility (verified)

- Both gaps git-verified OPEN 2026-07-04.
- **Adversarial verdict: NEEDS-FIX -> RESOLVED.** One CRITICAL (A3 miscitation) +
  one LOW (structure-only authorship) FIXED in-spec; AD1 mechanics verified
  non-blocking. Final: CONSISTENT.
- Boundaries honored: DEFINE-only; #4 intent-not-execution; #5 Principle-V
  (baseline + A11 owner-ruled, agent writes no definition, prose citation not a
  false A-code); AD1-legal growth contracts; no score; reference-by-name.

## Two risk stories the owner signs (be explicit -- clarify C4)

| Area | Feature | Risk story |
|------|---------|-----------|
| **#4 drill/nav** | F011A | INTENT vs EXECUTION -- captures design intent only; F016 renders. Verified no field crosses into runtime. |
| **#5 period-over-period** | F009 | PRINCIPLE V -- growth-contract STRUCTURE only; the comparison-baseline (UN-CODED) + A11 same-store stay owner-ruled; the agent writes NO baseline/comparable-store definition. |

## Artifacts this spec CHANGES

| Artifact | Feature | Change |
|----------|---------|--------|
| `templates/visual-spec.yaml` | F011A | +`drill_through`, +`drill_down` (intent) |
| `templates/report-composition.yaml` (NEW) | F011A | report-level page/nav layer (gated on C2) |
| `skills/retail-kpi-knowledge/contracts/net-sales-growth.md` (NEW) | F009 | Non-additive growth-contract structure; baseline uncoded, flagged |
| `.../same-store-sales-growth.md` (NEW) | F009 | + A11 same-store flagged; definition owner-pending |
| `.../ytd.md` (NEW) | F009 | Non-additive/period-accumulation; baseline flagged |
| `reports/blueprints/executive-summary.yaml` | F011A | comment annotation only |

## OWNER SEAMS -- RATIFIED by Ahmed Shaaban, 2026-07-04 (via AskUserQuestion)

| # | Decision | Recommended | Owner's call (Ahmed Shaaban, 2026-07-04) |
|---|----------|-------------|------------------------------------------|
| **C1 [BLOCKING]** | #5 = growth-contract STRUCTURE only; you rule baseline + A11 later. | A: structure only. | **RATIFIED: A -- structure only; owner rules the comparison-baseline + A11 later; agent writes no definition.** |
| **C2** | Add `report-composition.yaml` vs defer US2. | A: add it. | **RATIFIED: A -- add report-composition.yaml.** |
| **C4** | Ratify across F011A (#4) + F009 (#5). | Proceed combined. | **RATIFIED: proceed combined** (owner knowingly signs both risk stories). |

**Spec Status: RATIFIED (Ahmed Shaaban, 2026-07-04).** Build may proceed from
tasks.md (DEFINE-only). Structure only: RULING the comparison-baseline + A11,
filling real values, and any enforcement rule remain separate owner-gated
follow-ups (FR-011 / FR-010).

## To ratify

1. Fill the three cells (name + date).
2. Set `spec.md` **Status: Draft -> Ratified (<name>, <date>)**.
3. Then the build may proceed from `tasks.md` (DEFINE-only) on this branch.

Note: template/structure only. RULING the comparison-baseline + A11, filling real
drill/nav/growth values, and any enforcement rule are SEPARATE owner-gated
follow-ups (FR-011 / FR-010).

## Artifacts on this branch
`spec.md` · `clarify.md` · `plan.md` · `tasks.md` · `analysis.md` · `ratify-ledger.md`
(nothing under `templates/`/`contracts/` changed yet -- planning-only branch.)
