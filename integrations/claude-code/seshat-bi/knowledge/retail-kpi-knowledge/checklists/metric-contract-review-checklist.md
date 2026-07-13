# Metric Contract Review Checklist

ID: KPI-CHK-01

Run this before a contract is handed off to the DAX/semantic layer. A contract that fails
any required item is **not** ready for handoff and is **not** dashboard-ready.

## Required checks

- [ ] **Business definition exists** — plain-language, agreed by the owner, states
      inclusions and exclusions.
- [ ] **Formula exists** in business terms (no DAX/SQL/Python code).
- [ ] **Grain declared** — the level it is computed from and the levels it aggregates to.
- [ ] **Additivity declared** — fully / semi / non-additive, with a one-line reason.
- [ ] **Required fields listed** — each marked confirmed / assumption / derived; no field
      asserted to exist that hasn't been confirmed.
- [ ] **Owner declared** — exactly one accountable business owner.
- [ ] **Ambiguity checked** — every relevant item from `knowledge/kpi-ambiguities.md`
      either resolved (with the deciding owner) or flagged Needs business definition.
- [ ] **Validation checks listed** — at least one reconciliation and one sanity/bound check.
- [ ] **Implementation handoff ready (SQL / DAX / Python / Big-data)** — handoff notes state the
      fact/dimension fields, grain, additivity, filters, and open ambiguities for the
      implementation layers (SQL: fields/grain/transform/reconciliation; DAX: the measure;
      Python: source-prep of the required fields).

## Gate

- [ ] If any required item above is incomplete → status is **not** Seeded; mark Planned or
      Needs business definition. **Not dashboard-ready.**
- [ ] Confirm no DAX/SQL/Python code was written into the contract.
- [ ] Confirm no readiness pass was granted (that is the Readiness layer's call).
- [ ] Confirm non-additive KPIs carry an explicit "do not sum" warning in Common mistakes.

## Verdict

Record one of: **Ready for implementation handoff (SQL / DAX / Python / Big-data)** · **Planned** ·
**Needs business definition (blocked on: …)**.
