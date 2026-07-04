# Clarifications -- 085-antipattern-parity (B1)

### Session 2026-07-04

The agent reasoned through each ambiguity and recorded the RECOMMENDED answer.
Items marked **[OWNER SEAM]** dictate a change to human-authored prose or a
Principle-V judgment call; they are carried to the ratify ledger for the named
human to confirm -- the agent recommends, never self-clears them.

---

### C1 -- Synonym map vs align-first (resolves a spec self-contradiction) **[OWNER SEAM]**

**Ambiguity**: The draft spec both (a) recommended aligning `visual-qa.md` to
`dashboard-qa.md`'s exact names AND (b) mandated a committed synonym map for
benign variants (FR-007). These are mutually exclusive: if the docs are aligned,
there are no variants to map; if the map is needed, alignment has not happened.
The map's own example ("a page"/"one page") is exactly the delta alignment erases.

**Options**:
- **A (RECOMMENDED) -- align-first, no synonym map.** The owner edits
  `visual-qa.md` so its thirteen names exactly match `dashboard-qa.md`'s (this doc
  edit was ALREADY the recommended owner action for B1 in
  `design-ideas-decisions.md`). The rule then does exact normalized-name equality
  (case-fold + whitespace-collapse ONLY). Simpler rule, true lockstep, no
  map-rot, matches the standing recommendation.
- **B -- ship with a synonym map.** Rule goes green with no doc edit; carries a
  hand-curated variant map. Cheaper now, but philosophically muddy (a parity rule
  that ships a list of "these non-matches are fine") and self-maintaining
  (map-rot risk the spec's own Edge Cases flagged).

**Recommended answer: A (align-first, no map).** Why: it is the clean lockstep,
removes the unbounded map-rot failure mode, and is consistent with the
already-surfaced canonical-side recommendation. It requires one owner prose edit
to `visual-qa.md` BEFORE the rule can land green -- hence [OWNER SEAM].

**Spec impact if A**: FR-007 drops the synonym map; name comparison = case-fold +
whitespace-collapse exact equality. FR-008 (cite relied-on map entry) is removed.
User Story 3 is reframed from "normalize away benign differences" to "the owner
aligns the names first; the rule enforces exact equality thereafter." SC-001's
"with the synonym map" caveat becomes "after the owner aligns visual-qa.md".

---

### C2 -- Severity of a divergence

**Ambiguity**: Is a count/name divergence an ERROR (fail-closed) or a WARNING?

**Recommended answer: ERROR (fail-closed)**, consistent with the other
wiring/lockstep guards (E1, SC1, SC2). Honors ratified spec 044: severity is
emitted per branch at the emit site, NOT declared on `@register`. Not an owner
seam -- this is the house convention for lockstep guards.

---

### C3 -- "Reordered but set-intact" numbering

**Ambiguity**: If both docs keep all thirteen names but in a different order, is
that a failure?

**Recommended answer: ERROR.** The two docs number their entries 1-13 and the
prose cross-references rely on stable numbering ("the last three anti-patterns").
A reorder that changes which number maps to which name breaks those references, so
compare by BOTH number->name mapping AND set membership; a number->name mismatch
is an ERROR naming the number and the two names. Not an owner seam.

---

### C4 -- Rule id

**Ambiguity**: Which `@register` id?

**Recommended answer**: assigned by `retail scaffold` at build time (candidate in
the `AP`/`B` family); the human confirms the concrete id at ratify. Not resolved
now -- deferred to build, consistent with every other scaffolded rule.

---

## Carried to the ratify ledger (owner confirms)

- **C1** -- align-first (A) requires an owner edit to `visual-qa.md` before the
  rule lands green. Owner confirms A vs B and, if A, owns the prose edit.
- **C4** -- concrete rule id at scaffold time.
