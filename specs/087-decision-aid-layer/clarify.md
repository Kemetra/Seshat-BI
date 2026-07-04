# Clarifications -- 087-decision-aid-layer

### Session 2026-07-04

Recommended answers recorded. **[OWNER SEAM]** items are Principle-V / cross-feature
judgment calls carried to the ratify ledger -- the agent recommends, never
self-clears.

---

### C1 -- `action_on_breach` placement: on the contract, or a sibling? **[OWNER SEAM]**

**Ambiguity**: `direction_of_good` + `thresholds` are close to metric DEFINITION
(semantic: which way is good, what value is the target). `action_on_breach` is an
operational RESPONSE POLICY (what to DO). Bundling all three on the definition
contract couples two concerns the repo may prefer to keep apart.

**Options**:
- **A (RECOMMENDED) -- keep all three on `metric-contract.yaml`.** The gap analysis
  and the owner's acceptance placed decision-readiness on the contract; a breach
  action is meaningless without the band it responds to, so co-locating keeps the
  decision-ready unit atomic and reviewable in one place. Precedent: the contract
  already carries lifecycle (`readiness`) and governance (`ambiguities`) blocks, so
  it is not purely definitional today.
- **B -- split**: `direction_of_good`+`thresholds` on the contract; `action_on_breach`
  in a sibling `metric-response-policy` artifact. Cleaner concern-separation, but a
  second file per KPI + a cross-reference to maintain.

**Recommended answer: A (keep on the contract).** Atomic decision-ready unit,
matches the contract's existing multi-concern shape, one review surface. If the
owner later wants operational policy separated, `action_on_breach` can be extracted
without changing the semantic fields. Owner confirms A vs B.

---

### C2 -- Combined ratification across THREE separately-governed artifacts **[OWNER SEAM]**

**Ambiguity**: this one spec modifies F009's `metric-contract.yaml` AND F011A's
`dashboard-page-blueprint.yaml` + `visual-spec.yaml`, plus adds a new
`driver-decomposition.md`. The repo partitions features hard. The owner chose the
COMBINED spec-dir mode, so the coupling is intended -- but ratifying it clears a
seam that spans three governance areas at once.

**Recommended answer**: proceed combined (owner's explicit mode choice), and the
ratify ledger EXPLICITLY lists the three artifacts touched so the owner is
knowingly ratifying all three governance surfaces in one signature. No feature-
boundary GUARD is crossed (this is additive template fields + one new template; no
rule reads across features, verified). Confirmed at ratify.

---

### C3 -- `direction_of_good` enum shape

**Ambiguity**: is a two-valued `higher|lower` enough, or is a `target_band` (good
only inside a range, e.g. stock-cover days, on-hand vs safety stock) needed?

**Recommended answer**: three values `higher | lower | target_band`. Retail has
genuine target-band KPIs (inventory cover, price-index vs competitor). `target_band`
requires the `thresholds` block to express a two-sided band (edge case in spec).
Not an owner seam per se -- but the owner confirms the enum is complete for their
KPI set at ratify.

---

### C4 -- Optional enforcement rule: now or deferred?

**Ambiguity**: should a `retail check` rule make these fields REQUIRED on an
approved contract / filled blueprint?

**Recommended answer**: DEFER (FR-010). Keep this spec purely additive + boundary-
clean (DEFINE-only, no rule). A future spec can add the enforcement rule once the
fields exist and a few real contracts are filled (so the rule has true targets).
Adding a rule now would gate a state nothing has reached yet. Not an owner seam;
noted for the roadmap.

---

## Carried to the ratify ledger (owner confirms)

- **C1** -- `action_on_breach` on-contract (A) vs sibling (B). Recommend A.
- **C2** -- combined ratification spans metric-contract.yaml (F009) +
  dashboard-page-blueprint.yaml + visual-spec.yaml (F011A) + new
  driver-decomposition.md. Owner knowingly signs all three surfaces.
- **C3** -- `direction_of_good` enum completeness for the owner's KPI set.
