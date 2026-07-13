# Implementation Plan: Generic KPI Knowledge Registry and Governed Project Metric-Contract Authoring

**Branch**: `124-generic-kpi-contract-authoring`

**Date**: 2026-07-13

**Spec**: [spec.md](./spec.md)

**Input**: Owner-directed product decisions D1-D10 (2026-07-13); research.md D1-D4.

> **Note**: This plan is spec-driven and STOPS after Phase 1 design + a `/speckit.analyze`-style
> cross-artifact pass. It writes NO runtime code, adds NO CLI command, and marks NOTHING ratified.
> It anticipates the source/artifact touch points but does not create them.

## Summary

Deliver the `kpi_contracts` flow stage as an agent-first, artifact-plus-static-check capability: (1) one authoritative generic KPI **registry** (single YAML under `skills/retail-kpi-knowledge/`) that indexes the 13 shipped knowledge contracts and reconciles their drift; (2) a per-source **answerability** artifact in the existing coverage-scorecard shape, bound to committed evidence + the Decision Store, failing closed; (3) **additive provenance fields** on the shipped F009 contract wiring generic-ref/custom, decision-refs, and source-evidence; (4) a **custom-KPI** path; (5) the **first expansion wave** (1 net-new, 1 from-planned, 2 reconcile-existing); (6) an **extension protocol** with at most two narrow static consistency rules. Everything reuses the existing Decision Store, decision gate, readiness model, and `retail-kpi-knowledge` routing -- no second store, no second engine, no new spine stage, no CLI family.

## Technical Context

- **Language/Version**: Python >= 3.13 (only if the two static rules are implemented in a later feature; this plan is spec-only). Authored artifacts are YAML / Markdown.
- **Primary Dependencies**: stdlib-only for any future rule (matches the SL1/PP1 pattern); `pyyaml` already a runtime dependency for rule YAML loads.
- **Storage**: committed text -- the registry YAML, per-source answerability artifacts, F009 contract YAML. No database writes.
- **Testing**: pytest fixtures (registry consistency, answerability decision-rules, provenance presence, no-leak) when the rules are built in a later slice; this feature ships the fixtures' specification, not the code.
- **Target Platform**: Windows-first repo; ASCII/UTF-8-no-BOM; short repo-relative paths.
- **Project Type**: agent-first BI readiness kit; the agent is the runtime, static checks are the gate.
- **Constraints**: no numeric confidence/score; gold-only bindings; no self-grant of approval; no worked-example leakage.
- **Scale/Scope**: 13 existing generic KPIs indexed; +2 new generic contracts (Discounted Transaction Rate, Average Basket Size (Units)); 2 reconciled; at most 2 new static rules.

## Constitution Check

| Principle | Gate | Status |
| --- | --- | --- |
| I. Agent-First, Gate-Enforced | Agent routes via `retail-kpi-knowledge`; the gate (static rule exit) is the contract | PASS -- no CLI family; at most two static rules; the gate disposes, the agent proposes. |
| II. Depend, Never Fork | No execution-adapter work | PASS -- adapter untouched; handoffs are prose intent only. |
| III. Medallion, Postgres-First, Gold-Only | Bindings are gold-only | PASS -- FR-044 forbids silver/bronze binding. |
| IV. Source Mapping Before Silver | No silver SQL | PASS -- feature stops before `silver_gold_model_planning`. |
| V. Agent Stops at Judgment Calls | Meaning/policy/PII/pass are named-human approvals | PASS -- FR-013/FR-017/FR-020/SEC-001 route to approvals; no self-grant. |
| VI. Defaults Then Deviations | Reuses RC/ambiguity defaults via spec 058 ledger | PASS -- no new defaults invented. |
| VII. C086 Is An Example | No worked-example leakage | PASS -- FR-040/SC-012 + a leakage consistency rule. |
| VIII. Static-First, Live Deferred | Static rules only; no live DB dependency | PASS -- registry/provenance rules are stdlib-static. |
| IX. Secrets and Reproducibility | No secrets/PII; ASCII/UTF-8-no-BOM; short paths | PASS -- SEC-001..003; ASCII authored throughout. |
| Readiness System (spine) | No new stage; reuses the engine | PASS -- FR-032/FR-033; maps to `semantic_model_ready` via existing `_FLOW_TO_SPINE`. |

**Complexity Tracking**: no principle requires a deviation; the only additive surfaces are one registry file, one artifact shape, four optional contract fields, and at most two static rules -- each the narrowest repo-consistent option (research D1-D4).

## Project Structure

### Documentation (this feature)

```
specs/124-generic-kpi-contract-authoring/
  spec.md
  research.md
  data-model.md
  plan.md
  tasks.md
  quickstart.md
  checklists/requirements.md
  contracts/
    generic-kpi-registry.schema.md
    kpi-answerability.schema.md
    project-contract-provenance.md
  analysis.md            # /speckit.analyze cross-artifact pass (this package)
```

### Source Code (repository root) -- anticipated touch points (NOT created by this plan)

```
skills/retail-kpi-knowledge/
  registry.yaml                       # NEW (US1) -- the one authoritative registry
  contracts/discounted-transaction-rate.md   # NEW (US6) -- net-new generic contract
  contracts/average-basket-size-units.md      # NEW (US6) -- promoted from Planned
  references/id-conventions.md         # EDIT (US1) -- extend MC range to 13+
  references/kpi-derivation-lineage.md # EDIT (US1) -- add MC-11/12/13 edges
  INDEX.md / README.md                 # EDIT (US1) -- reconcile seed count + lifecycle
  checklists/kpi-extension-checklist.md # NEW (US7)
templates/metric-contract.yaml         # EDIT (US3) -- add four optional provenance fields
src/seshat/rules/                       # NEW (US7) -- at most two static consistency rules
tests/                                  # NEW -- fixtures per SC matrix
```

**Structure Decision**: the registry lives beside the knowledge it indexes (research D1); provenance is additive on the shipped template (research D3); consistency rules follow the SL1/PP1 static-rule pattern (research D4). This plan creates none of these -- it specifies them.

## Phase 0 -- complete

Research (research.md) fixed: R1 no-duplicate matrix; R2 flow boundary; R3-R6 the four plan decisions (registry format/path; answerability shape; additive provenance fields; the two static rules); R7 faithful D10 status; R8 the Principle-V approval seams.

## Phase 1 -- complete

data-model.md defines GenericKpiRegistryEntry (NEW), KpiAnswerabilityRow (NEW), the additive ProjectMetricContract fields, and references the reused ProjectKpiDecision / KpiPack / WorkedExample / knowledge contract. contracts/ holds the registry schema, the answerability schema, and the provenance-fields contract. quickstart.md walks the MVP path.

**Post-design Constitution re-check**: no new violation introduced; the four-vocabulary distinction (answerability 5 / contract 4 / decision 9 / gate 3) is preserved with the `warning` vs `warn` spelling intact.

## Migration and backward-compatibility decision (Section 10)

- **Additive-only**: the four provenance fields are OPTIONAL. A contract with none remains valid; external user workspaces do not break silently.
- **No wholesale rewrite**: no second contract format; the base F009 schema is unchanged.
- **Worked examples as fixtures**: bundled examples MAY be back-filled with the fields to demonstrate the pattern; their values never enter the registry (SC-012).
- **Deprecation timing**: if a future slice makes any field mandatory, it is a separately-specified deprecation with explicit warn-then-error timing. This feature ships warn-never (optional); no error is emitted for a missing provenance field on a legacy contract.

## Explicit STOPs (human seams -- NOT cleared by this chain)

1. `kpi_definition` / `policy_ruling` approval -- `metric_owner`, named-human, no self-grant.
2. PII-handling ruling for a customer/identity KPI -- `data_owner` / `governance`.
3. Checkpoint-B `pass` -- named-human approval with recorded evidence.
4. Promotion of a custom KPI into the generic registry -- a separate contribution/review workflow, never automatic.
5. Editing the shipped scorecard template's em-dash strings -- an owner decision (documented drift), out of scope here.

## Delivery sequencing (feeds /speckit.tasks)

1. **US1** (registry) -- foundational; everything reads it. MVP.
2. **US2** (answerability) -- reads the registry + evidence + Decision Store. MVP.
3. **US3** (Checkpoint-A draft) -- reads answerability + approved decisions. MVP.
4. **US4** (Checkpoint-B binding + handoff) -- P2, depends on US3 + a materialized Gold (later stage).
5. **US5** (custom KPIs) -- P2, sits on US3's authoring path.
6. **US6** (expansion wave) -- P3, content on top of US1's registry.
7. **US7** (extension protocol + at most two static rules) -- P3, guards US1/US3 structure.
