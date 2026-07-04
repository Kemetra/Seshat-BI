# Ratify Ledger -- 085-antipattern-parity (B1)

**STOP.** This spec is DEFINED and CHECKED, not APPROVED or IMPLEMENTED.
Ratification is a human edit the workflow is structurally forbidden to make
(Principle V, `never_self_grant_approval`). Nothing below is built until the named
owner ratifies.

**Branch**: `085-antipattern-parity` (worktree `.worktrees/085-antipattern-parity`)
**Feature**: static `@register` rule enforcing that `visual-qa.md` and
`dashboard-qa.md` carry the same thirteen anti-patterns in lockstep.
**Chain run by**: agent, direct spec-kit stages (specify -> clarify -> plan ->
tasks -> analyze -> adversarial review -> this ledger). NOT via a plan workflow
(per owner rule: ask before firing; owner said "make by your own").

---

## Eligibility (verified)

- **Git-verified OPEN** 2026-07-04: no shipping commit; `045-output-parity` is an
  unrelated feature; no existing rule in `src/retail/rules/` does this.
- **Hard-principle clean**: static/never-execute, no numeric score (#9), never
  edits a doc / never self-grants (V), observed-not-declared severity (044).
- **Grounding independently confirmed** by the adversarial reviewer (both docs'
  13-in-format, the wording deltas, count 52, importable core symbols).

## Verdicts

- **Analyze**: CONSISTENT after fixes (0 critical, 0 high remaining).
- **Adversarial skeptic**: NEEDS-FIX -> **all findings fixed** in-spec:
  - [HIGH] `__init__.py` import wiring omitted (silent-no-op risk) -> FR-009
    rewritten + tasks T101b/T101c added.
  - [HIGH] fabricated "IL1" citation -> corrected to `test_wiring_meta_gate.py` /
    `test_rule_count_claims.py` across all artifacts.
  - [MEDIUM] scaffold filename mismatch -> T101a rename step.
  - [MEDIUM] hardcoded 13 brittleness -> FR-013 documents it.
  - [LOW] this ledger now exists.

## OWNER SEAMS -- RATIFIED by Ahmed Shaaban, 2026-07-04 (via AskUserQuestion)

| # | Decision | Recommended | Owner's call (Ahmed Shaaban, 2026-07-04) |
|---|----------|-------------|------------------------------------------|
| **C1** | Synonym map vs align-first. | A: align-first, no map. | **RATIFIED: A (align-first, no map).** |
| **C4** | Concrete `@register` rule id. | `AP1`. | **RATIFIED: AP1.** |
| **Landing posture** | Same PR vs xfail-pending. | Same PR. | **RATIFIED: same PR** (rule + visual-qa.md alignment edit together). |

**Spec Status: RATIFIED (Ahmed Shaaban, 2026-07-04).** Build may proceed from
tasks.md (T101 onward). The agent may draft the visual-qa.md name-alignment edit
(mechanical: rename 2 headings to the canonical names) for the owner's review in
the same PR -- transcribing the ratified align-first decision, not making a new one.

## To ratify

1. Fill the three "Your call" cells above (name + date).
2. Set `spec.md` **Status: Draft -> Ratified (<name>, <date>)**.
3. If C1=align-first: make the `visual-qa.md` name-alignment edit (T000) -- YOUR
   prose edit, not the agent's.
4. Then the build may proceed from `tasks.md` (T101 onward) on this branch.

Until step 1-2, no implementation task runs.

## Artifacts on this branch
`spec.md` - `clarify.md` - `plan.md` - `tasks.md` - `analysis.md` - `ratify-ledger.md`
(nothing under `src/` or `tests/` yet -- this is a planning-only branch.)
