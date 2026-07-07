# Mapping review — user guide (roadmap M7)

> **Delivery under Option B (skill-driven).** A user-facing walkthrough of the
> *already-shipped* mapping-review skills — no new CLI verb, no new capability. The
> interface stays agent + skills (hard rule #1). Decision:
> `docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`.

## What mapping review is

After a table is onboarded (roadmap M6, `docs/user/source-onboarding.md`), the
`source-mapping` skill has produced the five mapping artifacts under `mappings/<table>/`,
including `source-map.yaml`. Mapping **review** is where **you** — the owner — inspect and
rule on the decisions those artifacts surface, before the mapping gate can clear. This is
the gate that stands between a raw source and any silver/gold work.

## The decisions you rule on (Principle V)

The mapping surfaces these for a named-human ruling; the agent proposes and records, it
never auto-approves:

- **Grain** — what one row means. The `grain-confidence-reviewer` skill (F008) surfaces
  grain *candidates* with the evidence for each; you pick the true grain.
- **Primary key** — which columns identify a row at that grain.
- **PII classification** — which columns are personal/sensitive and how they're handled.
- **Placement** — where each field lands in the medallion model (fact / dimension /
  degenerate dimension / dropped).
- **Business meaning / rollup / product identity** — any judgment call the source can't
  answer mechanically.

## The flow

You drive this by talking to the agent:

1. **Surface the candidates** — run `grain-confidence-reviewer` on the onboarded table.
   It presents grain candidates and their supporting evidence (never a fabricated
   confidence *score* — evidence and blocking reasons only).
2. **Review the `source-map.yaml`** — read the proposed grain / PK / PII / placement in
   `mappings/<table>/source-map.yaml`; confirm or correct each.
3. **Record your ruling** — the mapping gate clears only when the owner-owned decisions
   are recorded. This is a named-human act; the agent cannot self-grant it.

## Hard stops (the guide never suggests bypassing these)

- **`no_silver_before_mapping_cleared`** — silver/gold SQL is blocked until the mapping
  gate is cleared for the table.
- **Principle V / `never_self_grant_approval`** — grain, PK, PII, placement, and business
  meaning are owner rulings. The agent records the decision; it never makes it.

## Next

Once the mapping gate is cleared, build the medallion warehouse
(`docs/medallion-playbook.md`) and define the metric contracts before any dashboard work
(`no_dashboard_before_metric_contracts`). See the [readiness model](../readiness/readiness-model.md).
