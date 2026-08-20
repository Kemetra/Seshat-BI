# Quickstart: guided setup execution

**Feature**: spec 155. Reviewable now; the outputs below are what the
implementation must produce, not a recording of a run.

## The journey

```
project evidence -> derived capabilities -> exact catalog components
  -> capability-oriented change plan -> committed human approval
  -> existing installer -> existing verification -> capability status
```

## 1. What does this project need?

A Postgres + Power BI project, planned with no network and no writes:

```
Project Setup

  o Database Connectivity  Required -- needs setup
  o Power BI Integration   Required -- needs setup
  - Transformation Engine  Not Required
  - Orchestration          Not Required

  Database Connectivity: a relational source is declared in
    mappings/demo_sample_orders/source-map.yaml
  Power BI Integration: a Power BI project is declared at
    powerbi/RetailStoreSales.pbip
  Transformation Engine: no transformation project manifest is committed
  Orchestration: no orchestration project is committed under orchestration/

Proposed changes: 2 capabilities
```

No package, MCP server, npm, or runtime name appears, and no install command.
The user never selects `analytics-full` to obtain these two capabilities.

## 2. What exactly would change?

The proposed scope is the projection of those two capabilities and nothing else --
`connectorx`, `powerbi-modeling-mcp`, `fabric-skills`. The four components behind
Transformation Engine and Orchestration are absent because those capabilities are
`not-required`, not because they were filtered out late.

That detail is the ADVANCED view. Asked for it, setup reports the provider, the
catalog component, the resolved coordinate, and the verification basis -- each read
from the control plane, none recomputed.

## 3. Approval

The proposed component scope is what a named human approves, in
`contracts/provisioning-approvals.yaml`, read at HEAD:

```yaml
approvals:
  - stage: provisioning
    owner: "Person Name (governance)"
    at: "2026-08-21"
    components: [connectorx, powerbi-modeling-mcp, fabric-skills]
```

Without a covering row, `--apply` refuses and changes nothing:

```
error: provisioning needs a committed named-human approval -- record a
provisioning approval in contracts/provisioning-approvals.yaml
```

`--apply` is intent. `--yes` suppresses the prompt. Neither authorizes, and
neither does `--json`, a piped answer, a simulated terminal, or an agent asserting
that approval exists.

If the project later also needs Transformation Engine, the derived scope widens and
the earlier approval stops covering it -- the refusal names both scopes.

## 4. Execution, then verification

Execution delegates to the existing installer, still behind `--refresh` for exact
coordinates. Each component installs into the environment its own base profile
already defines, so a component a previous profile-based run installed is reused
rather than reinstalled.

Installation success is not readiness. A component that installed but failed
verification leaves its capability **not ready**, with the failed check named:

```
  x Power BI Integration   Not ready -- installed, verification failed
    next: <the failing check's own next action>
```

## 5. Partial failure and retry

One component succeeding and another failing is reported as exactly that -- both
remain visible, the affected capability is not ready, and the run is not called
successful. Re-running the same approved scope reuses what is already satisfied
and needs no new approval.

## For agents

The machine-readable status answers, per capability: capability, strength,
satisfied, needs-setup, proposed action, blocker, whether approval is required and
whether it is met, and post-execution status -- with no package-specific reasoning.

## What this does NOT do

- **Install without a committed human approval.** Ever.
- **Change the default.** `DEFAULT_PROFILE` and every existing `--profile` run are
  untouched; derived selection is additive.
- **Decide readiness itself.** Verification and discovery do.
- **Own the projection.** Spec 153 does. This connects it to provisioning.
