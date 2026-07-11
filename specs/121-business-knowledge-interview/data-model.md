# Data Model: Business Knowledge Interview, Decision Store, and Knowledge Contracts

**Feature**: `specs/121-business-knowledge-interview` | **Date**: 2026-07-11

Machine-readable shapes are normatively defined in
[contracts/decision-record.schema.json](./contracts/decision-record.schema.json) and
[contracts/knowledge-contract.schema.json](./contracts/knowledge-contract.schema.json);
this file is the narrative model.

## Store File Layout

Each of the three store files (`.seshat/semantic-decisions.yaml`,
`.seshat/kpi-contracts.yaml`, `.seshat/cleaning-rules.yaml`) is a top-level object:

```yaml
decisions: []   # Decision Records (required key)
batches: []     # Batch Approval Sets (optional key)
```

A file missing the `decisions` key, or containing unknown top-level keys, fails
closed (DS1).

## Decision Record

One recorded business decision. Lives in one of the three store files by concern
(R-3). Immutable once approved (FR-017): the only change path is supersession.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | slug string | yes | `<decision_type>.<scope-slug>[.<n>]`, unique per project (R-2) |
| `decision_type` | enum | yes | see Decision Types below |
| `statement` | string | yes | the decision in one or two business-readable sentences |
| `scope` | object | yes | `tables[]`, `columns[]`, `kpis[]`, `artifacts[]` -- at least one non-empty (FR-019) |
| `status` | enum | yes | see Status Lifecycle below (FR-014) |
| `confidence` | `low\|medium\|high` | yes on proposals | agent proposal confidence only; never approval, never surfaced as readiness (FR-015/016) |
| `evidence` | list of refs | yes | profile summaries, masked samples, checklist runs; repo-relative paths or artifact ids |
| `proposed_by` / `proposed_at` | string / ISO date | yes | who raised it (agent or human) and when |
| `approval` | Approval Record | when `approved` | see below (FR-020) |
| `supersedes` / `superseded_by` | id refs | when applicable | both directions recorded; referenced ids must resolve (DS4) |
| `batch_id` | id ref | when batch-approved | links to the Batch Approval Set |
| `notes` | string | no | free text; never a substitute for `statement` or `evidence` |

### Decision Types (critical set, FR-018)

`kpi_definition`, `pii_handling`, `table_grain`, `primary_key`,
`relationship_cardinality`, `missing_value_rule`, `data_exclusion`, `policy_ruling`
(VAT/returns/discount/cost), `dashboard_blueprint_approval`, `publish_export`.
Non-critical types are allowed (e.g. `naming`, `display_format`) and are the only
types eligible for batches (DS3). An unknown type inside a blocking category fails
closed (FR-035). Note: `missing_value_rule` is treated as critical for ALL fields --
a deliberate conservative superset of FR-018's KPI/financial/quantity/date scoping
(fail-closed direction).

### Status Lifecycle (FR-014, FR-017)

```text
                 +--> approved --------(only exit)--> superseded
                 |
proposed --------+--> rejected
   |             +--> deferred
   |             +--> blocked
   +--> pending --+--> needs_user_input --> (answered) --> proposed/approved path
                  +--> needs_sample -----> (sample provided) --> proposed path
```

- `proposed` -- agent-raised, awaiting a human ruling.
- `pending` / `needs_user_input` / `needs_sample` -- open; each blocks per FR-032 when
  its type is in a blocking category.
- `approved` -- carries a valid Approval Record; **immutable**; only transition is to
  `superseded` via a replacement record.
- `rejected` -- the assumption is ruled false; recorded, not deleted.
- `deferred` -- owner explicitly postponed; still blocking if in a blocking category.
- `blocked` -- cannot be decided yet (upstream dependency); names its blocker.
- `superseded` -- replaced; retains `superseded_by`.

## Approval Record (FR-020 to FR-023)

| Field | Type | Notes |
|---|---|---|
| `approved_by` | string | `"<Name> (<authority_class>)"` -- the existing RS1 shape; class must be eligible for the decision_type per `contracts/knowledge/approval-authority.yaml` (clarify Q2) |
| `approved_at` | ISO date | |
| `source` | enum | `interview`, `review`, `batch`, `owner_ruling` |
| `evidence` | list of refs | what the approver saw; must resolve (FR-022) |
| `evidence_identity` | map ref -> identity | content identity (hash or revision) of each cited evidence artifact, captured at approval time; the staleness comparator (FR-020) |
| `reviewed_scope` | scope selector | the scope the approver actually reviewed (same whitelist shape as `scope`); must cover the record's scope |

Validity is conjunctive: any missing field (including `evidence_identity`),
unresolvable evidence, ineligible authority class, or agent identity invalidates the
approval and the decision is treated as unresolved (fail closed).

**Staleness** (clarify Q1): detected by comparing each cited artifact's current
identity against the approval's recorded `evidence_identity`. If cited evidence
changed after approval, the approval is stale -- critical types => dependent verdicts blocked until re-confirmed/superseded;
non-critical => listed under warn.

## Batch Approval Set (FR-007, FR-023, clarify Q4)

| Field | Type | Notes |
|---|---|---|
| `batch_id` | slug | |
| `presented_at` | ISO date | |
| `members` | id refs | decisions approved by this batch; critical types forbidden (DS3) |
| `excluded` | id refs | items the owner pulled out; each becomes an individual `pending` question |
| `confirmed_by` / `confirmed_at` | RS1 string / ISO date | one named-human confirmation covers the remaining members |
| `evidence` | list of refs | what the batch presented |

## Knowledge Contract (FR-027 to FR-031)

One entry per flow stage in `contracts/knowledge/database-to-pbip-flow.yaml`.

| Field | Type | Notes |
|---|---|---|
| `stage` | slug | one of the 11 flow stages |
| `allowed_routes` | list | existing knowledge-map routes only (FR-031) |
| `required_inputs` | list | artifacts/decision categories that must exist (approved where critical) |
| `required_outputs` | list | what the stage must produce |
| `stop_rules` | list | conditions that halt entry/progress, each naming what unblocks it (FR-030) |
| `blocking_decision_categories` | list of decision_types | unresolved => blocked |
| `handoff` | slug | the next stage / owning layer |
| `non_goals` | list | what this stage must not do (e.g. DAX stage: define meaning) |
| `evidence_requirements` | list | what a pass must cite |

Boundary invariants encoded across entries: KPI-meaning questions route to Retail KPI
from any stage (FR-028); Big-data requires recorded scale evidence, else Python
(FR-029); execution adapters never gain meaning/mapping/metric/semantic/approval
authority (FR-004).

## Gate Verdict (FR-033 to FR-035)

Computed, never stored as authority (R-6).

| Field | Type | Notes |
|---|---|---|
| `stage` | slug | requested stage |
| `verdict` | `pass\|warn\|blocked` | pass needs valid approvals + resolvable evidence + no blocking condition; warn = non-fatal issues listed; blocked names each unresolved decision |
| `blocking` | list of {decision id, reason} | required when blocked |
| `warnings` | list | required when warn |
| `evidence` | list of refs | required when pass (a pass with no evidence is a defect) |

Projection into the spine: contributes to the affected stage's `blocking_reasons[]` /
`warning` in `readiness-status.yaml`; the spine remains the stage-state authority.

## Validation Rules -> Static Rule Family (R-1)

| Rule | Validates | Spec anchor |
|---|---|---|
| DS1 | store parses with the `{decisions, batches}` layout; ids unique + well-formed; statuses/types/confidence in vocab; scope non-empty; no raw suspected-PII value shapes | FR-013/014/015/019, FR-005 |
| DS2 | approval completeness incl. evidence_identity; RS1 name+class shape; authority-class eligibility; evidence resolvable; reviewed_scope covers scope | FR-020/021/022 |
| DS3 | no critical type in a batch; exclusions recorded; batch confirmation valid | FR-023 |
| DS4 | approved records immutable across history (supersession-only); supersedes/superseded_by resolve both ways; no two active records conflict on the same scope | FR-017, edge cases |
| DS5 | verdict consistency: no pass without evidence; blocked lists concrete decisions; recomputation matches recorded blocking reasons | FR-033/034/035 |
