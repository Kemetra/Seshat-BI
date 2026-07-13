# Contract: Generic KPI Registry Schema

**Feature**: `124-generic-kpi-contract-authoring` -- US1, FR-003..FR-006, FR-040

This is the SCHEMA and one ILLUSTRATIVE entry for the single authoritative generic KPI registry. The populated product artifact (under `skills/retail-kpi-knowledge/`) is authored by a US1 task, not by this spec package. Wire-format (YAML vs JSON) and exact path are plan-time decision D1.

## Top-level shape

```yaml
version: 1
entries:            # list of GenericKpiRegistryEntry; each KPI-MC-NN appears exactly once
  - <entry>
```

## Entry field contract

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `id` | string `^KPI-MC-\d{2,}$` | yes | stable, preserved, unique across entries |
| `slug` | string `^[a-z0-9]+(-[a-z0-9]+)*$` | yes | unique; machine slug, NOT the filename |
| `canonical_name` | string | yes | unique; the single display name |
| `aliases` | list[string] | yes (may be empty) | an alias never creates a second entry; an alias equal to any entry's `canonical_name` is a consistency error |
| `domain` | string | yes | one domain id from the domains catalog |
| `metric_kind` | enum | yes | `base_metric` \| `derived_metric` \| `ratio` \| `time_transform` \| `snapshot` \| `quality_metric` \| `analytical_slice` |
| `lifecycle` | enum | yes | `seeded` \| `planned` |
| `knowledge_contract_ref` | string path | yes | resolves to a committed tracked file |
| `derives_from` | list[string] | yes (may be empty) | each is a `KPI-MC-NN` that resolves to another entry; projected from spec 044 `derives_from`, never a second graph |
| `required_concepts` | list[string] | yes | LOGICAL concepts only; no physical column names |
| `required_decision_types` | list[enum] | yes | subset of Decision Store types; for KPIs at minimum `kpi_definition`, plus `policy_ruling` where a VAT/returns/discount/cost policy applies |
| `source_roles` | list[string] | yes | logical fact/source roles; a multi-fact KPI lists more than one |

## Client-free invariant (FR-040, SC-012)

No entry may contain: a physical schema/table/column name; a client or dataset name (C086, retail_store_sales, Kaggle, any customer/ERP); a policy value copied from a worked example; a specific number; or a named human. A US7 consistency rule detects a physical binding or client token in this file.

## Illustrative entries (NOT the product artifact)

```yaml
version: 1
entries:
  - id: KPI-MC-01
    slug: gross-sales
    canonical_name: "Gross Sales"
    aliases: []
    domain: sales-and-revenue
    metric_kind: base_metric
    lifecycle: seeded
    knowledge_contract_ref: skills/retail-kpi-knowledge/contracts/gross-sales.md
    derives_from: []
    required_concepts: [sales_amount]
    required_decision_types: [kpi_definition, policy_ruling]
    source_roles: [sales_fact]

  - id: KPI-MC-05
    slug: average-transaction-value
    canonical_name: "Average Transaction Value"
    aliases: ["average receipt value", "average basket value (currency)"]
    domain: basket-and-transactions
    metric_kind: ratio
    lifecycle: seeded
    knowledge_contract_ref: skills/retail-kpi-knowledge/contracts/average-transaction-value.md
    derives_from: [KPI-MC-02, KPI-MC-04]
    required_concepts: [net_sales_amount, transaction_identifier]
    required_decision_types: [kpi_definition]
    source_roles: [sales_fact]

  - id: KPI-MC-11
    slug: net-sales-growth
    canonical_name: "Net Sales Growth %"
    aliases: []
    domain: time-intelligence
    metric_kind: time_transform
    lifecycle: seeded            # reconciles the README/packs/candidates "planned" drift
    knowledge_contract_ref: skills/retail-kpi-knowledge/contracts/net-sales-growth.md
    derives_from: [KPI-MC-02]
    required_concepts: [net_sales_amount, comparison_period]  # comparison basis is an owner policy slot
    required_decision_types: [kpi_definition, policy_ruling]
    source_roles: [sales_fact, date_dimension]
```

## Notes for the maintainer

- `KPI-MC-12` (Same-Store Sales Growth %) has lifecycle `planned` (its contract is "structure only"); it stays Planned per FR-027.
- Planned-only KPIs with no knowledge contract (e.g. Inventory Turnover, GMROI, CLV) still get an entry with `lifecycle: planned` and a `knowledge_contract_ref` that MAY point to a planned placeholder; the consistency rule exempts `planned` entries from requiring a fully seeded contract, mirroring SL1's `Planned` exemption.
