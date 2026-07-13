# Contract: Project Metric-Contract Provenance (Additive Fields)

**Feature**: `124-generic-kpi-contract-authoring` -- US3/US4/US5, FR-011..FR-021, FR-034

This defines the ADDITIVE, backward-compatible provenance fields layered onto the shipped F009 metric-contract (`templates/metric-contract.yaml`, spec 010). All new fields are OPTIONAL so that existing project contracts remain valid (migration posture). Exact field names are finalized at plan-time decision D3; the behavior below is fixed.

## Additive fields (all optional)

```yaml
# Appended to a metric contract; every field optional -> legacy contracts stay valid
generic_kpi_ref: KPI-MC-01        # a registry entry id; present iff this realizes a known generic KPI
custom: false                     # true iff a custom KPI with no generic entry (US5)
decision_refs:                    # Decision Store record ids that authorize this contract
  - kpi_definition.<scope-slug>
  - policy_ruling.<scope-slug>    # where an applicable policy applies
source_evidence:                  # committed source/mapping evidence justifying the binding
  - mappings/<table>/source-map.yaml#<entry>
  - mappings/<table>/source-profile.md
```

## Rules

- **Exactly one of** `generic_kpi_ref` (resolving to a registry entry) **or** `custom: true` (FR-011, FR-021). A generic realization carries the ref even when the contract `name` differs from the canonical name (FR-012).
- `decision_refs` MUST reference at least one `approved` `kpi_definition` decision, plus every applicable approved `policy_ruling` (FR-013). The referenced decisions are validated by the EXISTING decision gate (approved, not superseded, evidence not stale) -- this feature adds no gate logic (FR-032).
- `source_evidence` MUST be repo-relative references; their freshness is checked by the existing `evidence_identity` sha256 mechanism (FR-014, FR-018).
- A `custom` contract MUST additionally satisfy: approved definition, grain, additivity, unit, applicable policies, required fields, and a NAMED ELIGIBLE owner; else authoring stops (FR-020, US5).
- No new readiness word: readiness stays `not_started | blocked | warning | pass`. No Gold binding -> `blocked` with `physical gold binding is not materialized` (FR-016). `pass` only with gold-only binding + valid decisions + fresh evidence + empty blockers + named-human approval (FR-017, FR-044).
- Forbidden content unchanged: no DAX/SQL/visual/connection string/raw PII/unbacked gold path (FR-015, SEC-001/002/003).

## End-to-end provenance chain (FR-034)

```
GenericKpiRegistryEntry (generic_kpi_ref)  OR  custom kpi_definition
        -> Decision Store decisions (decision_refs: kpi_definition + policy_ruling)
        -> source/mapping evidence (source_evidence)
        -> ProjectMetricContract (this file's fields)
        -> Gold-only binding (binds_to.gold_table/columns)   [Checkpoint B]
        -> downstream handoff (SQL / DAX / Python / Big-data) [out of scope here]
```

Every arrow is a structured, resolvable reference. A US7 consistency rule can verify the left three arrows resolve; the existing gate verifies decision validity and evidence freshness; the existing readiness model owns the binding->pass transition.

## Migration / backward-compatibility

- Additive-only: a contract with none of these fields is still valid; it is simply not yet provenance-linked.
- A legacy contract MAY be back-filled by adding the fields; no schema rewrite, no second contract format.
- Bundled worked-example contracts MAY be migrated as fixtures carrying these fields to demonstrate the pattern; their values still never enter the registry (SC-012).
- If a future slice makes any field mandatory, that is a separately-specified deprecation cycle with explicit warn-then-error timing (plan.md); this feature keeps them optional.
