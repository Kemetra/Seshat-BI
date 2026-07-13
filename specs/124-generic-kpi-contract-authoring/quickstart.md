# Quickstart: Generic KPI Registry and Governed Project Metric-Contract Authoring

**Feature**: `124-generic-kpi-contract-authoring`

This walks the MVP path (US1 -> US2 -> US3) the way the agent runs it. The agent is the runtime; every durable output is a committed artifact plus a static check. Nothing here executes DAX/SQL or grants readiness.

## Preconditions

- The Business Knowledge Interview (spec 121) has produced `kpi_definition` / `policy_ruling` decisions in the Decision Store (`.seshat/kpi-contracts.yaml`). This feature CONSUMES them.
- Committed source evidence exists (`mappings/<table>/source-profile.md`, `source-map.yaml`).
- You are at the `kpi_contracts` flow stage (downstream of `business_knowledge_interview`, upstream of `silver_gold_model_planning`).

## Step 1 -- Read the generic KPI registry (US1)

The registry (`skills/retail-kpi-knowledge/registry.yaml`) is the ONE authoritative inventory. For each candidate KPI it tells you: canonical name + aliases, metric kind, lifecycle (`seeded`/`planned`), the knowledge-contract reference, `derives_from`, `required_concepts`, `required_decision_types`, and `source_roles`.

Route via `retail-kpi-knowledge` (SKILL -> INDEX -> registry/contract). Do not scan; open the fewest files.

## Step 2 -- Produce answerability for your source (US2)

For your table/subject area, generate the answerability artifact (coverage-scorecard shape). Each KPI gets exactly one of:

```
Covered
Blocked -- missing field
Blocked -- needs business definition
Planned
Out of scope
```

Rules that keep it honest:
- A lookalike column name is NOT a mapping -> `Blocked -- needs business definition`.
- A present field with an unresolved policy is insufficient -> `Blocked -- needs business definition`.
- Missing/stale evidence fails closed -> never `Covered`.
- A multi-fact KPI names every required role and blocks on any absent one.
- No score, no percentage, no ranking. `Covered` means "eligible to draft," nothing more.

SL1 (spec 056) lints this artifact's structure; it does not decide its truth.

## Step 3 -- Draft the project contract from approved decisions (US3)

Only for a `Covered` KPI with an approved `kpi_definition` (and every applicable approved `policy_ruling`):

1. Copy `templates/metric-contract.yaml`.
2. Fill business intent, grain, additivity, unit (where applicable), filters/exclusions, ambiguities (spec 058 ledger), handoff intent.
3. Set provenance:
   - `generic_kpi_ref: KPI-MC-NN` (or `custom: true` for a custom KPI), exactly one.
   - `decision_refs:` the approved decision ids.
   - `source_evidence:` the source-map/profile refs.
4. If Gold does not exist yet, leave `readiness.status: blocked`, reason `physical gold binding is not materialized`, with a concrete next action.

The draft contains NO DAX, SQL, visual spec, connection string, raw PII, or invented Gold path.

If there is no approved `kpi_definition`, STOP: name the missing decision and route back to the interview.

## Step 4 (later, US4) -- Bind to Gold and hand off

After Gold is materialized and validated (a later stage), complete `binds_to` (gold-only). The contract may reach `pass` only with: valid binding + valid (non-superseded) decisions + fresh evidence + empty blockers + a named-human approval. Then emit clean SQL/DAX/Python/Big-data handoff intent -- this feature implements none of it.

## Custom KPI (US5)

No registry entry? Author a custom contract: approved definition + grain + additivity + unit + policies + required fields + a NAMED ELIGIBLE owner; mark `custom: true`; the generic registry stays untouched. To make it generic later, follow the separate contribution workflow (not automatic).

## What this never does

No second Decision Store, no second readiness engine, no new spine stage, no CLI family, no numeric score, no worked-example value as a product default, no DAX/SQL/dashboard/publish.
