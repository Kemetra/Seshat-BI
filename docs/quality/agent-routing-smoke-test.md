# Agent Routing Smoke Test

## Purpose

This document is a lightweight **manual** smoke test for the Seshat BI agent
navigation layer. It checks that an agent entering through `COMPASS.md` and
`docs/knowledge-map.md` can route common Retail BI requests to the correct
readiness stage, skill, checklist, or blocked verdict.

What this is and is not:

- It is **not** a runtime test.
- It is **not** a database test.
- It is **not** a SQL/DAX correctness test.
- It **is** a routing and governance smoke test.
- It should be run **mentally** (or by an agent) before expanding the navigation
  docs — a cheap check that the compass, router, and knowledge layer still point
  agents to the right place and that the gates still block unsafe progression.

## Entry contract

The agent must start from:

```text
AGENTS.md
  -> COMPASS.md
    -> docs/readiness/readiness-model.md
    -> docs/knowledge-map.md
      -> relevant skill/router
        -> required artifact/checklist/verdict
```

The agent must **not** jump directly into a knowledge file unless the router
(`docs/knowledge-map.md`, or a skill's own `INDEX.md`) tells it to.

## Pass criteria

The smoke test passes only if every scenario:

- identifies the readiness stage being served;
- routes to the correct first document or skill;
- avoids reading the whole knowledge base (open only what the route names);
- ends on an artifact, checklist, verdict, or explicit blocker;
- does not bypass source mapping, validation, metric contracts, semantic
  readiness, or F016 gating;
- does not invent source meaning, metric meaning, approval, or readiness `pass`
  status.

## Scenario matrix

`Result` is the manual outcome cell. It is **`Not run`** by default — this PR
defines the test; it does not execute it (see "Expected result for this PR").

| ID | User request / symptom | Expected stage | Expected route | Expected end artifact/verdict | Must not do | Result |
|---|---|---|---|---|---|---|
| RT-001 | "Onboard a new retail sales source." | Source Ready | `AGENTS.md` → `COMPASS.md` → `docs/knowledge-map.md` → `docs/readiness/readiness-model.md` (onboarding; then `source-ready.md` for the profile step) | readiness status + source profile, or blocked verdict listing the missing source facts | Do not create silver/gold SQL directly. | Not run |
| RT-002 | "The source grain is unclear." | Mapping Ready | `COMPASS.md` → `docs/knowledge-map.md` → `docs/readiness/mapping-ready.md` | declared grain + uniqueness evidence, unresolved questions, or blocked verdict | Do not guess grain or approve mapping automatically. | Not run |
| RT-003 | "Gold totals do not reconcile to source." | Gold Ready / Validation | `COMPASS.md` → `docs/knowledge-map.md` → `skills/bi-sql-knowledge/SKILL.md` → `skills/bi-sql-knowledge/INDEX.md` → "Route by symptom" | PB-SQL verdict (PB-SQL-08) or SQL reconciliation checklist | Do not diagnose from `COMPASS.md` or read the whole SQL knowledge base. | Not run |
| RT-004 | "Review this silver/gold SQL transformation." | Silver Ready or Gold Ready | `COMPASS.md` → `docs/knowledge-map.md` → `skills/bi-sql-knowledge/SKILL.md` → `skills/bi-sql-knowledge/INDEX.md` | SQL review checklist, a VP-* validation gate shape, or a blocked metadata request | Do not execute the SQL or claim validation passed without evidence. | Not run |
| RT-005 | "Measure ignores slicers." | Semantic Model Ready / DAX review | `COMPASS.md` → `docs/knowledge-map.md` → `skills/bi-dax-knowledge/SKILL.md` → `skills/bi-dax-knowledge/INDEX.md` → "Route by symptom" → fix context/filter problems | context diagnosis + corrected DAX shape, or blocked model-metadata request (audit with `checklists/dax-measure-review-checklist.md`) | Do not write arbitrary DAX before mapping model roles and filter behavior. | Not run |
| RT-006 | "Define Net Sales." | Metric contract (business meaning) | `COMPASS.md` → `docs/knowledge-map.md` (route 12) → `skills/retail-kpi-knowledge/SKILL.md` → `skills/retail-kpi-knowledge/INDEX.md` → `contracts/net-sales.md` | `metric-contract-review-checklist` verdict (+ implementation handoff note to SQL / DAX / Python), or blocked business-definition question | Do not open a DAX file during the definition step; do not create a dashboard KPI or DAX measure before metric intent, grain, additivity, required fields, and filter behavior are known. | Not run |
| RT-007 | "Design the executive dashboard." | Dashboard Ready | `COMPASS.md` → `docs/knowledge-map.md` → `.claude/skills/powerbi-dashboard-design/` (router) → gated verb `.claude/skills/dashboard-design/` **only if** metric contracts + `semantic_model_ready: pass` exist | dashboard blueprint, or blocked verdict (no approved contracts / model not ready) | Do not design visuals before metric contracts and `semantic_model_ready` evidence. | Not run |
| RT-008 | "Publish this Power BI report." | Publish Ready / F016 boundary | `COMPASS.md` → `docs/knowledge-map.md` → `docs/roadmap/roadmap.md` (F016, gated / execution-only / later) | blocked verdict unless `semantic_model_ready` and the publish gates have passed | Do not run or advance the Power BI execution adapter (F016). | Not run |
| RT-009 | "SQL total doubled after a join." | SQL diagnostics / Silver–Gold validation | `COMPASS.md` → `docs/knowledge-map.md` → `skills/bi-sql-knowledge/INDEX.md` → "Route by symptom" | PB-SQL join fan-out diagnostic verdict (PB-SQL-01/02) | Do not apply a random `DISTINCT` or aggregate the issue away without grain evidence. | Not run |
| RT-010 | "YTD is wrong." | Semantic Model Ready / DAX time intelligence | `COMPASS.md` → `docs/knowledge-map.md` → `skills/bi-dax-knowledge/INDEX.md` → "Route by symptom" / time-intelligence route | date-table prerequisite checklist (`checklists/dax-model-review-checklist.md`), DAX shape, or blocked verdict | Do not fake a date table, "Mark as Date Table", a relationship, or calendar assumptions. | Not run |
| RT-011 | "Define the business meaning of Net Sales." | Metric contract (business meaning) | `COMPASS.md` → `docs/knowledge-map.md` (route 12) → `skills/retail-kpi-knowledge/SKILL.md` → `skills/retail-kpi-knowledge/INDEX.md` (task: Define Net Sales) → `contracts/net-sales.md` | `metric-contract-review-checklist` verdict (Seeded / Needs business definition) | Do not write DAX; do not approve readiness; do not skip the VAT / returns / date-policy ambiguity. | Not run |
| RT-012 | "Is Average Transaction Value additive?" | Metric contract (additivity) | `COMPASS.md` → `docs/knowledge-map.md` (route 12a) → `skills/retail-kpi-knowledge/INDEX.md` (additivity route) → `knowledge/kpi-additivity-and-grain.md` | `metric-contract-review-checklist` (additivity verdict + aggregation rule) | Do not answer "just sum it" without the additivity file; do not write a DAX measure. | Not run |
| RT-013 | "Gross and net sales are mixed in our report." | Metric ambiguity | `COMPASS.md` → `docs/knowledge-map.md` (symptom: Retail KPI) → `skills/retail-kpi-knowledge/INDEX.md` (symptom route) → `knowledge/kpi-ambiguities.md` | `metric-ambiguity-checklist` (ambiguity resolved with owner, or Needs business definition) | Do not invent a reconciliation rule; do not skip the owner ruling. | Not run |
| RT-014 | "Choose the KPIs for the first dashboard." | KPI-pack selection | `COMPASS.md` → `docs/knowledge-map.md` (route 12b) → `skills/retail-kpi-knowledge/INDEX.md` (pack selection) → `packs/mvp-retail-kpi-pack.md` | `kpi-pack-review-checklist` (live count / planned count / blockers) | Do not treat pack selection as readiness approval; do not put planned (uncontracted) KPIs on the first dashboard. | Not run |
| RT-015 | "Write the DAX measure for Net Sales." | DAX implementation (boundary case — routes AWAY from Retail KPI) | `COMPASS.md` → `docs/knowledge-map.md` (route 12c) → `skills/bi-dax-knowledge/SKILL.md` → `skills/bi-dax-knowledge/INDEX.md` | generated measure + contract assumptions, or a blocked verdict that routes back to `retail-kpi-knowledge` if no business contract exists | Do not redefine the KPI's business meaning or additivity inside DAX; do not generate code with no upstream business contract. | Not run |

## Manual run instructions

1. Pick one scenario from the matrix.
2. Start at `COMPASS.md`.
3. Identify the readiness stage being served.
4. Use `docs/knowledge-map.md` to select the route.
5. Open **only** the named skill/router (then its `INDEX.md` if it is a knowledge skill).
6. Stop on the expected artifact / checklist / verdict.
7. Mark `Result` as **PASS** or **BLOCKED**.
8. If blocked, record the missing route, the missing file, or the unsafe ambiguity.

## Failure examples

A scenario has **failed routing** (not merely blocked-by-design) if the agent:

- reads the whole SQL or DAX knowledge base instead of the one file the route names;
- writes silver SQL before Mapping Ready is `pass`;
- writes DAX before a metric contract / required model metadata exists;
- defines a KPI's business meaning inside the DAX (or SQL/Python) layer instead of routing
  to `skills/retail-kpi-knowledge/` first;
- generates a DAX measure for a KPI that has no upstream business contract, instead of
  routing back to `retail-kpi-knowledge`;
- fabricates a metric contract for a `[planned]`/uncontracted KPI instead of returning a
  planned/deferred note;
- designs a dashboard before metric contracts and `semantic_model_ready`;
- routes a Power BI publish request to execution instead of the F016 blocked boundary;
- invents a readiness `pass` without citing evidence;
- treats C086 as the generic schema.

## Expected result for this PR

This PR **defines** the smoke test. It should leave every scenario `Result` cell as
**`Not run`** by default. A future PR may add an execution record once an agent has
actually walked the scenarios.

Do **not** fabricate a `PASS` run unless the manual checks were actually performed
and exact file evidence is cited.

## See also

- `COMPASS.md` — the compass (entry point + fast routing).
- `docs/knowledge-map.md` — the router (route by task and by symptom).
- `AGENTS.md` — the short operating contract.
- `docs/readiness/readiness-model.md` — the readiness spine and gate ordering.
