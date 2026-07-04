# Clarifications -- 086-shared-checklist-fork (I3)

### Session 2026-07-04

Recommended answers recorded. **[OWNER SEAM]** items are Principle-V judgment
calls carried to the ratify ledger -- the agent recommends, never self-clears.

---

### C1 -- Rule the existing aggregation-grain-checklist fork: shared or distinct? **[OWNER SEAM]**

**Ambiguity**: `aggregation-grain-checklist.md` exists in `bi-bigdata-knowledge`
and `bi-python-knowledge` with DIFFERENT content (verified divergent). Is this an
intentional per-layer specialization (`distinct`) or accidental drift from a
meant-to-be-shared spine (`shared`, and the drift is a defect)?

**Options**:
- **A -- distinct**: the two are legitimately different (one "at scale"/distributed,
  one groupby/python); declare `distinct`, keep both. Rule passes.
- **B -- shared**: they were meant to be one spine; declare `shared`, then the owner
  reconciles them to byte-identical (or refactors one to reference the other).

**Recommended answer: A (distinct), with a caveat.** The two files read as
genuinely different-scope artifacts (distributed vs single-node), so `distinct` is
the likelier honest call. BUT this is squarely the owner's judgment (it asserts the
two routes' checklists SHOULD differ) -- the agent must NOT set it. Recommended
only as a starting hypothesis for the owner to confirm or overturn. **[OWNER SEAM]**

**Why the agent can't decide**: ruling shared-vs-distinct asserts a cross-layer
identity/scope decision (do the big-data and python aggregation routes share ONE
grain contract or TWO?). That is the exact class of judgment Principle V reserves
for a human; fabricating it would self-supply the contract the gate checks.

---

### C2 -- The manifest shape + who writes it **[OWNER SEAM]**

**Ambiguity**: does the agent create `docs/quality/shared-spine.yaml`?

**Recommended answer**: the agent supplies the manifest SHAPE (an example/empty
scaffold with the schema documented) ONLY if the owner asks; the owner authors the
actual `shared`/`distinct` declarations. Shape:
```yaml
# docs/quality/shared-spine.yaml -- human-authored cross-layer checklist contract
checklists:
  aggregation-grain-checklist.md: distinct   # or: shared   <- OWNER rules C1
```
The rule reads it; never writes it (FR-003). **[OWNER SEAM]**

---

### C3 -- Severity assignment

**Recommended answer**: ERROR for undeclared-collision (FR-004), shared-drift
(FR-005), missing/malformed manifest (FR-008); WARNING for moot-distinct (FR-006)
and stale-entry (FR-007). Consistent with fail-closed guards + surface-don't-block
for hygiene notes. Observed-not-declared (044): emitted per branch. Not an owner
seam -- house convention.

---

### C4 -- Rule id

**Recommended answer**: assigned by `retail scaffold` (candidate `SF1` /
shared-fork family); owner confirms at ratify. Deferred to build.

---

## Carried to the ratify ledger (owner confirms)

- **C1** -- rule the existing fork shared vs distinct (the BLOCKING judgment). Agent
  recommends `distinct` as a hypothesis; owner decides.
- **C2** -- owner authors `docs/quality/shared-spine.yaml`; agent may scaffold the
  shape on request only.
- **C4** -- concrete rule id at scaffold time.
