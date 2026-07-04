# Ratify Ledger -- 087-decision-aid-layer

**STOP.** DEFINED and CHECKED, not APPROVED or IMPLEMENTED. Ratification is a human
edit the workflow is forbidden to make (Principle V, `never_self_grant_approval`).

**Branch**: `087-decision-aid-layer` (worktree ZEUS)
**Feature**: a DEFINE-only decision-aid layer covering the keystone 3
presenting-gaps -- KPI decision-readiness, page narrative arc, driver vocabulary.
**Chain**: agent-driven spec-kit stages (specify -> clarify -> plan -> tasks ->
analyze -> adversarial review -> this ledger).

## Scope (owner-accepted)

- Owner accepted the 2026-07-04 gap analysis and requested "more specs to cover
  gaps in visualizing and business logics."
- Owner chose (AskUserQuestion): **keystone 3** gaps, **one combined spec dir**.

## Eligibility (verified)

- All 3 gaps git-verified OPEN 2026-07-04 (no shipping commit, no in-flight spec).
- **Adversarial reviewer verdict: SHIP-AS-SPEC** -- 10 load-bearing claims verified
  TRUE (schema-guard safe, no-score holds, cross-feature safe, Principle-V sound,
  FR<->task bijection complete, driver template distinct). 3 minor findings folded
  in.
- Hard boundaries honored: DEFINE-only (no rule, no DAX/SQL/PBIR), no numeric score
  (#9), reference-by-name (VII), agent-stops-at-judgment (V).

## Artifacts this spec CHANGES (three governed surfaces -- clarify C2)

| Artifact | Feature | Change |
|----------|---------|--------|
| `templates/metric-contract.yaml` | F009 | +`direction_of_good`, +`thresholds`, +`action_on_breach` |
| `templates/dashboard-page-blueprint.yaml` | F011A | +`narrative` block |
| `templates/visual-spec.yaml` | F011A | +3 driver `visual_type` convention values |
| `templates/driver-decomposition.md` (NEW) | F011A | new factor-attribution artifact |

## OWNER SEAMS -- RATIFIED by Ahmed Shaaban, 2026-07-04 (via AskUserQuestion)

| # | Decision | Recommended | Owner's call (Ahmed Shaaban, 2026-07-04) |
|---|----------|-------------|------------------------------------------|
| **C1** | `action_on_breach` on the contract vs sibling. | A: on the contract. | **RATIFIED: A -- on the contract.** |
| **C2** | Ratify a spec spanning 3 governed artifacts. | Proceed combined. | **RATIFIED: proceed combined** (owner knowingly signs all 3 surfaces). |
| **C3** | `direction_of_good` enum complete? | Yes. | **RATIFIED: complete (higher\|lower\|target_band).** |

**Spec Status: RATIFIED (Ahmed Shaaban, 2026-07-04).** Build may proceed from
tasks.md (T101 onward, DEFINE-only). Template fields only; backfilling real KPIs
(FR-011) + the enforcement rule (FR-010) remain separate owner-gated follow-ups.

## To ratify

1. Fill the three cells (name + date).
2. Set `spec.md` **Status: Draft -> Ratified (<name>, <date>)**.
3. Then the build may proceed from `tasks.md` (T101 onward, DEFINE-only) on this
   branch.

Note: this ships the TEMPLATE fields only. Backfilling real KPIs/blueprints with
values (FR-011) and the optional enforcement rule (FR-010) are SEPARATE owner-gated
follow-ups, not part of this spec.

## Artifacts on this branch
`spec.md` · `clarify.md` · `plan.md` · `tasks.md` · `analysis.md` · `ratify-ledger.md`
(nothing under `templates/` changed yet -- planning-only branch.)
