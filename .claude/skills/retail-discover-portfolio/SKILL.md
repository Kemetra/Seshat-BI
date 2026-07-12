---
name: retail-discover-portfolio
description: >-
  Discover an unfamiliar retail data portfolio before per-table onboarding.
  Produces one metadata-only Layer-A survey across every reachable table, proposes
  non-critical domain and first-delivery scope decisions, delegates selected
  tables to retail-onboard-table for Layer-B profiling, and hands off to the
  existing business-knowledge-interview. Never samples source values, self-confirms
  a decision, or advances beyond the interview handoff.
---

# retail-discover-portfolio

Use this skill when the owner has an unfamiliar database schema or file folder and
needs a governed route from portfolio discovery to the business interview.

## Boundary

This is an agent-conducted flow, not a new state engine or CLI workflow:

portfolio discovery -> domain -> scope -> selected-table onboarding -> interview handoff -> STOP

- Layer A is the metadata-only portfolio survey in
  templates/portfolio-survey.md.
- Layer B is the existing value-backed, per-table Source Ready profile owned by
  retail-onboard-table.
- Never create a second profiler or author mappings/<table>/source-profile.md here.
- Never select a scale-out route. Record scale evidence for the existing
  silver_gold_model_planning boundary to decide later.
- Read the existing stage contracts and committed artifacts to derive exactly one
  next action. Create no run-state, projection, or routing file.

The golden reference shapes are:

- tests/fixtures/portfolio-survey/db-schema/survey.md
- tests/fixtures/portfolio-survey/file-folder/survey.md

## 1. Produce the Layer-A survey

For a database schema:

1. Call seshat.portfolio_enumerate.enumerate_tables(schema). This helper is the
   only DB table-enumeration path. Do not issue a raw information_schema.tables
   query, and do not catch raw config, driver, or connection exceptions.
2. If it returns an error, show only that redacted error. If no metadata is
   readable, STOP and name the unblock: configure the gitignored .env, install
   the matching retail DB extra, or grant metadata permission.
3. For every returned table, read information_schema.columns plus declared PK/FK
   and catalog-estimate metadata through the same read-only boundary.

For a file folder, list every reachable CSV and Excel file and inspect only
format/schema metadata. Do not read source values.

Fill one committed survey from templates/portfolio-survey.md:

- include every reachable table; never choose a table-count or time cap;
- include declared types, declared PK/FK metadata, catalog row estimates, and
  name/type-based date, PII-suspicion, grain, and structural-role hints;
- label every inference candidate/hint, never a ruling;
- for unavailable metadata, record [PENDING LIVE PROFILE] or needs_sample, the
  exact reason, and the enabling step;
- never measure uniqueness, missingness, date spans, or returns population;
- never include raw or masked samples, suspected-PII values, credentials, DSNs,
  or connection strings.

## 2. Propose a domain

Precondition: a committed, non-empty portfolio survey exists. The inherited
domain_guess gate can pass with an absent store because its
blocking_decision_categories is empty; therefore enforce this local precondition
here. If missing, STOP: "portfolio survey missing; complete Layer-A discovery."

Load .seshat/semantic-decisions.yaml first and append a non-critical proposal:

- decision_type: domain_classification (free-form, not a critical type)
- status: proposed
- confidence: low | medium | high (proposal confidence only)
- proposed_by: agent
- proposed_at: ISO-8601 timestamp
- evidence: non-empty citations to survey facts

When evidence is ambiguous, record alternatives or "undetermined". Never approve,
confirm, or add an approval-authority.yaml row. A named human may confirm through
the existing low-risk batch path; follow spec 121's current status convention.

## 3. Propose a bounded first-delivery scope

Precondition: the domain proposal exists. If missing, STOP:
"domain proposal missing; record a grounded domain guess."

Append a non-critical proposed scope decision with proposed_by, proposed_at,
confidence, and non-empty survey + domain evidence. Record candidate tables,
business questions, KPI names (not definitions), exclusions, and dependencies.

Bounding is deterministic:

- honor an explicit owner-supplied scope limit;
- otherwise prefer one coherent business process, one primary fact grain, and
  KPI names sharing one model boundary;
- when metadata crosses processes/grains, present narrower coherent alternatives
  or record needs_user_input.

Describe the result categorically as coherent, cross-boundary, unresolved, or
needs-user-input. Never store a numeric score, threshold, or rank. Partial
acceptance creates a bounded new proposed record and marks the original
superseded; never edit history in place.

For each selected table invoke retail-onboard-table. That existing skill alone
produces Layer-B source-profile.md. Do not deep-profile inside the survey.

## 4. Hand off to the existing interview

Before handoff, require exactly the existing interview inputs:

1. committed Layer-B per-table profiles for every selected table;
2. the proposed scope;
3. the existing Decision Store, loaded first and presented for confirmation or
   supersession without overwriting any record.

If a selected table lacks its Layer-B profile, STOP and name that table plus the
retail-onboard-table unblock. Then invoke business-knowledge-interview; do not
re-implement it and do not record an interview outcome here. Route KPI-meaning
questions to the Retail KPI knowledge boundary.

At the interview handoff, STOP. This skill grants no approval and advances no
readiness stage.

## Resume and local-stop table

| Committed state | One next action |
|-----------------|-----------------|
| No survey | Produce the Layer-A portfolio survey. |
| Survey, no domain proposal | Record the grounded domain proposal. |
| Survey + domain, no scope | Record the bounded scope proposal. |
| Scope, selected table lacks Layer-B profile | Invoke retail-onboard-table for that table. |
| All Layer-B profiles + scope + loaded store | Hand off to business-knowledge-interview, then STOP. |
| Request beyond interview handoff | STOP; continue under the downstream stage contract, not this skill. |

Every stop names the concrete missing artifact/decision and the action that
unblocks it. Existing Decision Store records are never overwritten; reruns present
them and changes use supersession.
