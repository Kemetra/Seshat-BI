# `contracts/` — product-level knowledge contracts

Machine-readable **product data** that governs the agent-guided Database-to-PBIP
flow. Introduced by spec `specs/121-business-knowledge-interview`.

## contracts vs templates

- **`contracts/`** (this dir) holds *normative product data* the agent and the
  static checker read at runtime — the flow's stage routing, stop rules, blocking
  categories, and the decision-type → authority-class eligibility map. A user does
  not fill these in; they are the kit's opinion, versioned with the kit.
- **`templates/`** holds *blanks a user fills* for their own project (the decision
  store, the review artifact, the mapping-gate artifacts). See `templates/`.

## What lives here

| Path | Purpose | Spec anchor |
|---|---|---|
| `knowledge/database-to-pbip-flow.yaml` | One entry per flow stage: allowed knowledge routes, required inputs/outputs, stop rules, blocking decision categories, handoff, non-goals, evidence requirements. | FR-027..031 |
| `knowledge/approval-authority.yaml` | Each critical decision type → the authority class(es) eligible to approve it. The single source of truth for approval eligibility (DS2 reads it). | FR-021 |
| `interview/business-knowledge-interview.yaml` | The interview stage's behavior contract: question grouping, masking, pause/resume, recording obligations. | FR-006..012 |
| `report/dashboard-blueprint.yaml` | The blueprint-approval stage contract that gates the future PBIP prototype. | FR-036..038 |

## Reading rule (fail closed)

Every consumer of these contracts fails closed: a malformed, missing, or
unparseable contract is treated as *unsatisfied*, and any stage it governs reports
`blocked` — never `pass`. Contracts reference existing knowledge-map routes; they
never duplicate or restate the SQL / DAX / Python / Big-data / Retail-KPI knowledge
bases (FR-031).
