# Ratify Ledger -- 086-shared-checklist-fork (I3)

**STOP.** DEFINED and CHECKED, not APPROVED or IMPLEMENTED. Ratification is a human
edit the workflow is forbidden to make (Principle V, `never_self_grant_approval`).

**Branch**: `086-shared-checklist-fork` (worktree `.worktrees/086-shared-checklist-fork`)
**Feature**: static `@register` rule enforcing that same-basename checklists across
`skills/**/checklists/` are declared `shared` (byte-identical) or `distinct` in a
HUMAN-AUTHORED `docs/quality/shared-spine.yaml`.
**Chain**: agent-driven spec-kit stages (specify -> clarify -> plan -> tasks ->
analyze -> adversarial review -> this ledger).

## Eligibility (verified)

- Git-verified OPEN 2026-07-04; no existing rule does this.
- Hard-principle clean: static/never-execute, no numeric score (#9), never writes
  the manifest / never rules the fork (V), observed-not-declared severity (044).
- Grounding independently confirmed by adversarial reviewer (with a count
  correction: 17 files / 15 unique + 1 pair; single real collision).

## Verdicts

- Analyze: CONSISTENT after fixes.
- Adversarial skeptic: NEEDS-FIX -> **all findings fixed**: [HIGH] count 18->17;
  [MED] bad-enum FR-008b added; [MED] this ledger created; [LOW] SC-004 write-test
  added; [LOW] merge-clash noted.

## OWNER SEAMS -- RATIFIED by Ahmed Shaaban, 2026-07-04 (via AskUserQuestion)

| # | Decision | Recommended | Owner's call (Ahmed Shaaban, 2026-07-04) |
|---|----------|-------------|------------------------------------------|
| **C1** | Rule the existing fork `aggregation-grain-checklist.md`: shared or distinct. | distinct (hypothesis). | **RATIFIED: distinct** (intentional per-layer: distributed vs python). |
| **C2** | Author `docs/quality/shared-spine.yaml`. | Owner authors, or authorizes the shape scaffold. | **AUTHORIZED: agent scaffolds the shape with the owner-confirmed `distinct` value; owner owns future entries.** |
| **C4** | Concrete `@register` id. | `SF1`. | **RATIFIED: SF1.** |

**Spec Status: RATIFIED (Ahmed Shaaban, 2026-07-04).** Fork ruled `distinct`; the
agent is authorized to scaffold `docs/quality/shared-spine.yaml` transcribing that
ruling (the agent transcribes the owner's `distinct` decision -- it does NOT decide
it). Build may proceed from tasks.md.

## To ratify

1. Fill the three cells (name + date).
2. Author `docs/quality/shared-spine.yaml` (C2) with the C1 ruling.
3. Set `spec.md` **Status: Draft -> Ratified (<name>, <date>)**.
4. Then the build may proceed from `tasks.md` (T101 onward) on this branch.

Until steps 1-3 (esp. the authored manifest), the rule has no contract and cannot
land green -- this is the defining blocker, honestly owned.

## Artifacts on this branch
`spec.md` - `clarify.md` - `plan.md` - `tasks.md` - `analysis.md` - `ratify-ledger.md`
(nothing under `src/`/`tests/` yet -- planning-only branch.)
