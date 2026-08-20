# Quickstart: capability-oriented setup

**Feature**: spec 153

## What it answers

"What does this project need, and why?" — in capability names, not package names.

## A Postgres + Power BI project

```
Project Setup

  o Database Connectivity  Required
  o Power BI Integration   Required
  o Transformation Engine  Required
  o Orchestration          Required

  Database Connectivity: a relational source is declared in
    mappings/demo_sample_orders/source-map.yaml
  Power BI Integration: a Power BI project is declared at
    powerbi/RetailStoreSales.pbip
  Transformation Engine: a transformation project is declared under dbt
  Orchestration: an orchestration project is declared under orchestration/

4 capabilities require setup.
```

Every line cites the artifact it read. No package, MCP server, npm name, or
install command appears — that is asserted by a test built from the catalog's own
coordinates, so it cannot quietly stop holding.

## The same repo without the BI and pipeline artifacts

```
Project Setup

  o Database Connectivity  Required
  - Power BI Integration   Not Required
  - Transformation Engine  Not Required
  - Orchestration          Not Required

  Database Connectivity: a relational source is declared in
    mappings/sales/source-map.yaml
  Power BI Integration: no Power BI project (*.pbip) is committed
  Transformation Engine: no transformation project manifest is committed, so no
    transformation work is declared
  Orchestration: no orchestration project is committed under orchestration/

1 capability requires setup.
```

Different shape, different plan — and the negative reasons name what was looked
for. **Absence is evidence**: "no `*.pbip` is committed" is a finding with a
citable basis, not silence, which is why these report `not-required` rather than
`undetermined`.

## When evidence cannot be read

```
  - Database Connectivity  Optional
  Database Connectivity: mappings/sales/source-map.yaml exists but could not be
    read as a source declaration
    undetermined -- needs a readable source-map at mappings/sales/source-map.yaml
```

`undetermined` is reserved for this: an artifact that exists but cannot be
parsed. It is **not** a fifth strength, and it never fires merely because a
capability is unused.

## Declining a capability

Record it in `contracts/capability-declines.yaml`:

```yaml
declines:
  - capability: transformation-engine
```

A declined `recommended` or `optional` capability stops being proposed; the rest
of the work proceeds.

**Declining a `required` capability does not make it un-required.** The strength
comes from project evidence, and a human declining something does not change the
evidence — so the row keeps `required`, gains a blocker, and the plan reports
`blocked`:

```
Power BI Integration is required by this project (a Power BI project is declared
at powerbi/Sales.pbip) but has been declined in
contracts/capability-declines.yaml; remove the decline or change the project so
the capability is no longer needed
```

A malformed or missing declines file declines **nothing** — failing open would
suppress every needed capability behind a clean-looking plan.

## For agents

`render_json(plan)` answers what is needed, what is satisfied, what is missing,
why, and whether anything blocks — without provider internals:

```json
{
  "blocked": false,
  "blockers": [],
  "capabilities": [
    {
      "id": "powerbi-integration",
      "name": "Power BI Integration",
      "strength": "required",
      "reason": "a Power BI project is declared at powerbi/Sales.pbip",
      "satisfied": false,
      "declined": false,
      "undetermined_evidence": null,
      "blocker": null
    }
  ],
  "needs_setup": 1
}
```

## For an auditor: which provider, and verified how

`technical_detail(plan)` is the advanced path. Provider identity, channel, role,
and verification basis all come from the integration catalog — nothing is
restated here, so a catalog change reaches this output with no change to the
normal journey.

## What this does NOT do

- **Install anything.** Provisioning belongs to `seshat integrations setup`,
  behind the committed named-human approval from issue #671.
- **Change the default.** `DEFAULT_PROFILE` is untouched; derivation is an
  additional selection basis, not a replacement.
- **Decide readiness.** A capability is satisfied only when the discovery surface
  says so — never because an install returned success.
