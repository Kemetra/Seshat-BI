# KPI Pack Review Checklist

ID: KPI-CHK-02

Run this when assembling or reviewing a KPI pack (e.g., for an MVP dashboard).

## Required checks

- [ ] **Pack purpose is clear** — one sentence on the decision/audience it serves.
- [ ] **Every KPI has a contract or a planned/deferred marker** — no KPI listed without
      either a live contract link or an explicit Planned state.
- [ ] **No duplicate KPI meaning** — two entries do not silently compute the same thing
      under different names (e.g., net sales vs realised revenue).
- [ ] **No missing domain-critical KPI** — the pack's domain isn't missing an obviously
      required KPI (e.g., a margin pack without a margin %).
- [ ] **Unavailable fields are marked as dependencies** — the pack does not silently
      require fields/facts that aren't confirmed; each is flagged blocked-by.
- [ ] **Owner declared** for the pack.

## Gate

- [ ] The pack does **not** imply dashboard readiness — state this explicitly.
- [ ] Live vs planned split is honest: only KPIs with seeded contracts are "live".
- [ ] No DAX/SQL/dashboard design is embedded in the pack.

## Verdict

Record: **Pack scoped (N live / M planned)** with the blocked-by list, or **Needs work
(reason)**.
