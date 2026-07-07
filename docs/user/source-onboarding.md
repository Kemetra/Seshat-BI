# Source onboarding — user guide (roadmap M6)

> **Delivery under Option B (skill-driven).** This is a user-facing walkthrough of the
> *already-shipped* onboarding skills — it adds no new CLI verb and no new capability.
> The interface stays agent + skills (hard rule #1); this guide just makes the flow
> discoverable for a new user in a scaffolded workspace (`seshat init-project`, spec 107).
> Decision: `docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`.

## What onboarding does

Onboarding walks a new raw retail table across the first two readiness stages —
**Source Ready** (a profiled, understood source) → **Mapping Ready** (grain / PK / PII /
placement mapped and reviewed) — and stops at the mapping gate. It never writes silver
SQL, never self-grants the gate, and never answers a judgment call that is the owner's
(grain, PII, business rollup, product identity — Principle V).

## The flow

You drive this by talking to the agent; the agent runs the skills. In order:

1. **Onboard the table** — `retail-onboard-table` is the front door. Say something like
   *"onboard `<schema>.<table>`"* or *"take this new table from nothing to a reviewed
   map."* It sequences profile → map → gate, seeds the per-table `readiness-status`
   record, and **stops at Mapping Ready**. It delegates the actual mapping artifacts to
   the `source-mapping` skill (below) — it does not re-implement mapping.

2. **Map the source** — `source-mapping` is the mapping gate. It produces the five
   mapping artifacts (grain candidates, column classification, PII flags, placement,
   and the `source-map.yaml` that records them) under `mappings/<table>/` in your
   workspace. This is the gate: **no silver/gold work happens until it is cleared.**

3. **Review and approve** — the mapping surfaces grain / PK / PII / placement *decisions*
   for **you** to rule on (see the mapping-review guide, roadmap M7). The agent never
   auto-approves these — clearing the mapping gate is a named-human act (Principle V).

## Where the output lands

In a workspace scaffolded by `seshat init-project`, onboarding output lands in
`mappings/<table>/` — the layout the `source-mapping` skill writes to, already present
in the scaffold. Nothing extra to wire.

## Hard stops (the guide never suggests bypassing these)

- **`no_silver_before_mapping_cleared`** — you cannot build silver/gold SQL until the
  mapping gate is cleared for that table.
- **Principle V** — business meaning, grain, PII classification, and placement are owner
  decisions. The agent proposes and records; it never rules.

## Next

Once a table is Mapping Ready, continue with the **mapping-review** flow (roadmap M7,
`docs/user/mapping-review.md`) to approve the decisions, then the medallion warehouse
build. See the [medallion playbook](../medallion-playbook.md) and the
[readiness model](../readiness/readiness-model.md).
