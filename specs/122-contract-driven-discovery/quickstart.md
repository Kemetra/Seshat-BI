# Quickstart: Contract-Driven Discovery-to-Decision Flow

**Feature**: `specs/122-contract-driven-discovery` | **Date**: 2026-07-12

A walkthrough of the agent-conducted bounded flow. The agent is the runtime
(Principle I); this is a procedure the agent performs via the new
`retail-discover-portfolio` skill, calling existing gates -- not a CLI command or an
engine. The flow is:

```text
portfolio discovery (Layer A)
  -> domain proposal
  -> scope proposal
  -> selected-table onboarding (Layer B, via retail-onboard-table)
  -> Business Knowledge Interview handoff
  -> stop
```

## Preconditions

- A reachable source of one of the supported kinds (R-7): a DB schema, or a standalone
  file source (CSV/Excel, or a folder of such files). Read-only metadata access is
  enough for Layer A; a live connection / optional reader being absent yields a truthful
  `[PENDING LIVE PROFILE]` boundary, not a stop.
- The existing Decision Store is loaded first (existing decisions are presented for
  confirmation/rejection/supersession, never overwritten).

## Step 1 -- Layer-A portfolio survey (the MVP)

The agent surveys **every reachable table's metadata** and writes one committed
portfolio survey (from `templates/portfolio-survey.md`): identity, inventory, declared
types, declared PK/FK metadata, candidate grain (from metadata), approximate row count,
date/PII **hints**, structural-role hints, coverage limits (only genuinely-unreachable
metadata), candidate domain/scope evidence. No value is sampled; no value-backed measure
is taken; no raw PII/credentials are written.

**Stop truthfully** if no reachable source metadata can be read: name the boundary and
the enabling step (e.g. `pip install 'retail[db]'` + set `ANALYTICS_DB_*` in a
git-ignored `.env`); record `warning`/`blocked`, never a fabricated inventory.

**Verify (SC-001)**: a new user locates every required survey element (metadata facts,
hints, coverage limits, candidate domain/scope evidence) from the single artifact
without reading the repo.

## Step 2 -- Domain proposal (P2)

From the survey evidence, the agent records a **non-critical `proposed`** domain
decision in the existing store (`confidence`, `proposed_by` = agent, citing survey
facts). If ambiguous, it records competing alternatives or an honest "undetermined" --
never a confident single guess. A named human confirms it via the existing low-risk
**batch** path, rejects it (`rejected`), or supersedes it. The agent never self-confirms.

**Stop truthfully** if no survey exists: the skill's own local precondition halts it
and names the missing survey. The inherited gate can pass here because this stage has
no blocking decision categories; the local stop is deliberately feature-owned.

## Step 3 -- Scope proposal (P2)

The agent records a **non-critical `proposed`** scope decision citing survey + domain
evidence: candidate tables, candidate questions, candidate KPI *names* (never defined),
explicit exclusions, unresolved dependencies, required owner decisions. Bounding is
deterministic (FR-018): honor an explicit user scope limit; else prefer one coherent
business process / one primary fact grain / KPIs sharing a coherent model boundary. If
the evidence crosses processes/grains/owner groups/model boundaries, record it
categorically as **cross-boundary** and present narrower coherent options or record
`needs_user_input`. No numeric score, table-count threshold, or fabricated rank.
Partial acceptance produces a bounded superseding proposal (original -> `superseded`).

**Stop truthfully** if no domain proposal exists: the skill's own local precondition
halts it and names the missing domain-guess decision; it does not rely on the inherited
gate to infer an absent input.

## Step 4 -- Selected-table onboarding (Layer B)

For each table in the proposed scope, the agent hands the table to the **existing**
`retail-onboard-table` / Source Ready profiler for value-backed profiling (measured
uniqueness/missingness/date-coverage, masked samples, returns population). This feature
authors no per-table profile and duplicates no `mappings/<table>/source-profile.md`.

## Step 5 -- Business Knowledge Interview handoff

The agent hands the interview its declared `required_inputs`: the committed Stage-1
per-table (Layer-B) profile of the in-scope tables (the interview's "a committed
discovery profile"), the proposed scope, and the existing Decision Store loaded first.
Control passes to the existing interview (spec 121); this feature does not re-implement
it, record interview outcomes, define KPI meaning, or grant approvals. KPI-meaning
questions route to the Retail KPI knowledge boundary.

## Step 6 -- Stop

The flow stops at the interview-handoff boundary. A request to cross into a downstream
capability (KPI contract authoring, Silver/Gold execution, DAX/PBIP, dashboards,
publishing) stops truthfully and states the crossing is out of scope for this feature.

## What this flow never does

- Never writes `silver.*`/`gold.*` SQL, DAX, metric contracts, PBIP, or dashboards.
- Never builds a second per-table profiler, a second Decision Store, or a second
  readiness engine.
- Never adds a new decision status, `decision_type`, or `approval-authority.yaml` row.
- Never self-grants or self-confirms any decision.
- Never repairs the global Decision Gate (that is the spec's deferred follow-up).
- Never commits a raw suspected-PII value, credential, DSN, or connection string.

## Acceptance anchors

SC-001 (single reviewable survey), SC-003 (proposals distinct from human confirmation),
SC-004 (no raw PII/credentials), SC-005 (bounded-flow local stops), SC-007 (exactly one
next action within the flow), SC-008 (stops before downstream), SC-009 (no duplicated
capability).

The synthetic end-to-end evidence lives under `tests/fixtures/portfolio-survey/`:
golden DB/file surveys, grounded domain and scope records, a Layer-B interview handoff,
and every bounded routing state. `tests/unit/test_discovery_flow_stops.py` verifies the
proposal lifecycle, supersession-only changes, exact interview inputs, local-stop
ownership, unchanged top-level contracts, and the one-next-action projection. Together
with the survey/enumerator tests, the interview begins from one survey plus a bounded
set of per-table profiles rather than asking one round per in-scope column.
