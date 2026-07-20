---
name: dashboard-design
description: >-
  Design a Power BI dashboard FROM approved metric contracts in the
  Seshat BI repo. Use when someone asks to design a report/page,
  bind visuals to metrics, or produce a dashboard layout for a subject area whose
  semantic model is ready. This skill is HARD-GATED on semantic_model_ready: pass
  (no approved metric contracts -> no design); it authors reviewable design
  guidance only -- a layout plan, a visual list, and a visual->contract binding
  map where every visual binds to exactly one approved contract. It NEVER invents
  a metric, NEVER publishes, NEVER opens Power BI Desktop or a DB connection, and
  NEVER calls the Power BI execution adapter (official Power BI MCP / connection;
  `pbi-cli` no longer preferred) -- that is feature F016. It authors,
  runs static seshat check, records dashboard_ready at most as warning, and STOPS.
---

# dashboard-design

Stage 6 of the Tower BI Readiness System, **Dashboard Ready**
([`docs/readiness/dashboard-ready.md`](../../../docs/readiness/dashboard-ready.md)):
a report is designed AGAINST approved metric contracts -- never before them. This
skill is the agent VERB that runs that stage. It reads the approved metric
contracts (F009) and the governed PBIP model (F010), then authors a layout plan, a
visual list, and a visual->contract binding map so every visual traces to a
contract that already exists and is approved. It is the agent expression of roadmap
hard rule 5 ("no dashboard design before metric contracts") and hard rule 6 ("no
Power BI execution before semantic-model readiness").

This verb is the gated, contract-binding design step that the broader
`powerbi-dashboard-design` router (F011A, the visual-design FOUNDATION) hands the
"design a dashboard from approved contracts" intent to. The router carries the
design vocabulary (four surfaces, tokens, theme, blueprints, QA); this verb enforces
the gate and produces the binding map a human signs off.

## Scope boundary (read first)

This skill AUTHORS design guidance and STOPS. Authoring is in-scope: a layout plan,
a visual list, a visual->contract binding map, and (optionally) a blank PBIR
scaffold a human fills -- no side effects, no DB/Desktop connection, the same
category as `source-mapping` authoring `mappings/` and `retail-build-warehouse`
authoring `warehouse/migrations/*.sql`. EXECUTING the design -- generating the PBIR
report, publishing to a workspace, calling the Power BI execution adapter (official
Power BI MCP / connection; `pbi-cli` no longer preferred) -- is the deferred,
execution-only F016 adapter seam and is OUT of scope here. The skill authors, runs
static `seshat check` on any committed report text, and STOPS.

## Hard gate (rule 5) -- verify BEFORE authoring anything

Before authoring ANY design, read the subject area's readiness status and verify
`semantic_model_ready: pass`. "Pass" means BOTH:

- approved metric contracts exist (F009) -- each carries a recorded approval; and
- the governed PBIP model binds each measure to one (F010).

If `semantic_model_ready` is anything other than `pass` -- `not_started`,
`blocked`, or `warning` -- the gate FAILS. Author no design, record
`dashboard_ready: not_started` (the prior stage is not `pass`) with the concrete
blocking reason, and STOP. A `warning` prior stage does NOT authorize design (the
thing being awaited is exactly the contract approval). Never invent a metric to
fill a visual when the gate is not pass.

This skill reads the gate; it does NOT re-derive contract approval
([`readiness-pipeline.md`](../../../docs/readiness/readiness-pipeline.md): "pass"
of the prior stage is the entry condition).

## Author vs publish boundary (rule 6)

| In scope (author) | Out of scope (F016 owns) |
|-------------------|--------------------------|
| layout plan, visual list, visual->contract binding map | generating/publishing the PBIR report |
| optional blank PBIR scaffold a human fills | opening Power BI Desktop or a DB connection |
| running static `seshat check` on committed report text | calling the Power BI execution adapter (official Power BI MCP / connection) |
| recording `dashboard_ready: warning` + evidence | publishing to a workspace / refreshing a model |

The skill authors, checks, and STOPS. Name F016 (the Power BI execution adapter --
official Power BI MCP / connection; `pbi-cli` no longer preferred; the last and gated,
EXECUTION-ONLY feature) as the owner of any execution step. If the procedure ever needs
to publish or author the PBIR via automation, STOP and hand off to F016.

## Preconditions (STOP unless ALL hold)

1. `semantic_model_ready: pass` for the subject area (the hard gate above).
2. Approved metric contracts (F009) are readable and each carries a recorded
   approval (an unapproved-but-present contract is NOT a valid binding target).
3. The governed PBIP model (F010) is present and binds measures to those contracts.
4. The analyst has supplied the business questions the page must answer. This is a
   Principle V input -- if missing, ASK for it; do NOT invent a generic page.

If any precondition fails, record the matching `dashboard_ready` status + blocking
reason and STOP.

## Procedure (numbered; do not reorder)

### 1. Read inputs
Read the approved metric contracts (each: name, grain, formula intent, owner +
approval) and the business questions the page must answer. Confirm the governed
model is `semantic_model_ready: pass`.

### 2. Author the layout plan
Author the page/section structure as reviewable text: which business questions the
page answers, in what reading order, one question per region. (For the section
vocabulary -- header / KPI strip / main insight / diagnostic / exception-detail /
filter rail / footer-status -- and design principles, use the F011A foundation:
`docs/powerbi/visual-design-system.md` and
`../powerbi-dashboard-design/workflows/page-blueprint.md`.)

### 3. Author the visual list
For each proposed visual record: its type, the business question it answers, and
the ONE approved metric contract it binds to. Choose the visual type to fit the
contract's GRAIN (a single additive measure -> KPI card; a measure by a dimension
-> bar/column; a measure over time -> line; row-level detail -> table). A visual
with no backing approved contract MUST NOT be emitted (see Blocking reasons).

### 4. Author the visual->contract binding map
Author the committed note proving each visual maps to exactly one approved contract
(no orphan visual). This is the artifact the design review signs off. Cite each
contract by name. If more approved contracts exist than visuals on the page, record
each DROPPED contract with a reason (e.g. "covered by the Stage 7 handoff pack, not
the dashboard") -- never a silent omission.

### 5. Record readiness (warning, never pass)
Record `dashboard_ready: warning` with `evidence[]` (the committed layout plan +
visual list + binding map) and `next_action: "get the design review
(visual->contract binding) signed off by the BI report owner"`. Use the four
statuses only (`not_started` / `blocked` / `warning` / `pass`) -- NEVER a numeric
confidence score.

### 6. STOP
Stop at the design-review boundary. The skill never writes `dashboard_ready: pass`
itself (see No self-granted pass). Hand the design to the BI report owner for the
visual->contract binding review.

## R1 / relative-reference note

When a committed PBIR report exists for the subject area, confirm `seshat check`
(rule R1) stays exit 0 -- the report references the governed model by a RELATIVE
path, not an absolute/remote ref. On failure, record `dashboard_ready: blocked`
with the reason ("PBIR references the model by absolute/remote path -- R1 fails")
and STOP; the relative-reference fix is the human's. This skill reuses the existing
R1 rule; it adds no new `seshat check` rule.

## Blocking reasons (each maps to a STOP)

- `semantic_model_ready` is not `pass` (the hard gate -- contracts must exist first).
- A visual has no backing approved metric contract (orphan visual).
- A metric is invented at design time instead of reusing an approved contract.
- The PBIR references the model by an absolute/remote path (R1 fails).

## No invented metrics

The skill binds ONLY to existing approved contracts. It NEVER defines, alters, or
invents a metric -- metric definition is F009's job, not this skill's. An
unapproved-but-present contract is not a valid binding target; a visual that would
need it is an orphan -> STOP. If a needed metric does not exist as an approved
contract, the gap is recorded ("orphan visual: no approved contract for
<question>") and the skill STOPS rather than inventing one.

## No self-granted pass

The skill NEVER writes `dashboard_ready: pass`. The highest status it records is
`warning`, with `next_action: "get the design review (visual->contract binding)
signed off by the BI report owner"`. A `pass` requires an `approvals[]` entry --
`{stage: dashboard_ready, owner: <bi-report-owner>, at: <date>}` -- written by the
REVIEWER, not by this skill. When that approval is recorded by the reviewer,
`dashboard_ready` may become `pass` and `next_action` points to Stage 7
([`publish-ready.md`](../../../docs/readiness/publish-ready.md)).

## Edge cases

- **More approved contracts than visuals**: not every contract must appear on the
  page, but each dropped contract MUST be recorded with a reason -- no silent
  omission.
- **Grain mismatch** (e.g. a row-level contract asked to be a single KPI card):
  record a `warning`-class design note, propose the grain-appropriate visual, and
  never silently mis-bind.
- **A contract exists but is not approved**: treat only APPROVED contracts as
  bindable -> the visual is an orphan -> STOP.
- **Subject area spans multiple tables/models**: bind visuals only to contracts
  within the governed model(s) that are `semantic_model_ready: pass`; a visual
  needing an out-of-model metric is an orphan -> STOP.
- **No business questions supplied**: design is question-driven -- ASK for the
  questions (a Principle V input); do not invent a generic page.

## What the agent must NOT do

- Do NOT invent, define, or alter a metric at design time -- only bind to approved
  contracts (metric definition is F009).
- Do NOT design any visual before its metric contract exists / before
  `semantic_model_ready: pass` (rule 5).
- Do NOT call the Power BI execution adapter (official Power BI MCP / connection;
  `pbi-cli` no longer preferred), generate or publish the PBIR, or refresh a model --
  that is feature F016 (rule 6), execution-only and gated.
- Do NOT open a DB or Power BI Desktop connection.
- Do NOT self-grant `dashboard_ready: pass` -- the highest this skill records is
  `warning`; `pass` needs the reviewer's `approvals[]` entry.
- Do NOT fabricate a confidence score -- use the four statuses + evidence + blockers.
- Do NOT bake any real connection host or secret into any output (G6).

## Generic, not C086

This skill and any template scaffold it uses are GENERIC (roadmap rule 7). No
C086/pharmacy specifics (billing codes, segment rollups, insurance/PII columns,
pharmacy grain keys, real metric names) appear in the skill text or any committed
template. Worked values belong only to a per-subject-area instance; C086 is the
first worked example, not the schema (Principle VII).

## See also

- The stage contract: [`docs/readiness/dashboard-ready.md`](../../../docs/readiness/dashboard-ready.md).
- The prior stage / gate: [`docs/readiness/semantic-model-ready.md`](../../../docs/readiness/semantic-model-ready.md).
- Status + evidence + blockers: [`docs/readiness/readiness-model.md`](../../../docs/readiness/readiness-model.md).
- Hard rules 5/6/7/8: [`docs/roadmap/roadmap.md`](../../../docs/roadmap/roadmap.md).
- The visual-design FOUNDATION this verb reasons with: the `powerbi-dashboard-design`
  router skill + `docs/powerbi/` + `templates/` + `design/` + `themes/` +
  `reports/blueprints/` (F011A).
- Generic scaffolds: `templates/dashboard-layout.md`,
  `templates/visual-contract-binding-map.md`.

## Orchestration

When a table is driven end-to-end, the `retail-orchestrate` conductor sequences
this verb after `semantic_model_ready` is `pass` and runs the self-heal loop
against the gate exit code. This skill stays single-purpose: it authors the design,
records `dashboard_ready: warning`, and STOPS at the human design-review boundary.
The loop lives only in `retail-orchestrate`, never here.
