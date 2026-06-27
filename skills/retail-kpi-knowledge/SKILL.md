---
name: retail-kpi-knowledge
description: >-
  Retail KPI / metric-contract reasoning layer for BI agents in the Seshat BI project.
  Use when an agent must reason about the BUSINESS MEANING of a retail KPI before any
  implementation — defining a KPI in business terms, classifying additivity
  (fully/semi/non-additive), identifying grain, listing required source fields, resolving
  ambiguity (gross vs net, VAT, returns, cost method, same-store), choosing an MVP KPI
  pack, reviewing a metric contract for completeness, or preparing a clean handoff to the
  DAX / semantic-model layer. This is a meaning/definition + review layer, not an executor:
  it does not write DAX/SQL/Python, grant readiness, or design dashboards. Initial seed —
  see INDEX.md for which routes are live (10 seeded contracts) and which are planned.
---

# Retail KPI Knowledge Skill

A Retail KPI and metric-contract reasoning layer for BI agents. It helps an agent
define, classify, review, and validate retail KPIs **before** any DAX measure, SQL
transformation, or dashboard page is built.

## Purpose

This layer owns the *business meaning* of retail KPIs and the *metric contract* that
must exist before implementation. It produces definitions, additivity and grain calls,
required-field lists, ambiguity flags, validation checks, and a clean handoff to the
DAX / semantic-model layer.

It does **not** produce runtime artifacts. It governs meaning; other layers govern code.

## Use when

The agent needs to:

- define a retail KPI in business terms
- review a metric contract for completeness
- classify a KPI's additivity (fully / semi / non-additive)
- identify a KPI's grain
- identify the required source fields for a KPI
- decide whether a KPI is safe for dashboard use
- choose an MVP KPI pack for a first dashboard
- detect ambiguous or dangerous KPI meaning (gross vs net, VAT, returns, cost method)
- prepare a handoff to an implementation layer (SQL for fields/grain/transform, DAX for
  the measure, Python for single-node source-prep, Big-data for distributed/at-scale
  aggregation & reconciliation)

## Do not use when

- writing DAX measures (→ DAX knowledge layer)
- building or transforming SQL tables (→ SQL knowledge layer)
- executing Python / dataframe prep (→ Python knowledge layer)
- approving readiness or granting pass/block (→ Readiness layer)
- designing dashboard visuals or page layout (→ Dashboard design layer)
- publishing Power BI

## Mandatory workflow

Always route, never scan. Open the fewest files needed.

```
SKILL.md  ->  INDEX.md  ->  relevant knowledge / contract / pack file(s)  ->  metric contract / checklist / verdict
```

1. Start here (`SKILL.md`) to confirm scope and boundaries.
2. Go to `INDEX.md` and pick the matching task / symptom / domain / pack route.
3. Open only the file(s) that route names.
4. End on a deliverable: a completed metric contract, a checklist result, a verdict,
   or an implementation handoff note (to SQL, DAX, or Python). Never end inside raw
   knowledge.

## Boundaries

- Readiness owns gates and pass/block status.
- SQL knowledge owns SQL transformation and reconciliation logic.
- DAX knowledge owns measures, filter context, and semantic-model implementation.
- Python knowledge owns dataframe / source-prep reasoning.
- Dashboard design owns visual and page design.
- Retail KPI knowledge (this layer) owns business KPI meaning and metric contracts.

## Stop rules

Stop and hand off (do not continue) when any of these is true:

- The task asks for DAX, SQL, or Python code → hand off to that layer; provide only a
  business-terms formula and a handoff note.
- The task asks whether a dataset/model is *ready* to ship → hand off to Readiness.
- The task asks for a dashboard page or visual design → hand off to Dashboard design.
- A KPI's policy is undefined (VAT, returns, cost method, same-store, snapshot date) →
  mark the contract **Needs business definition** and stop; do not invent the policy.
- A required source field cannot be confirmed to exist → mark it as an assumption or
  dependency; do not pretend the field exists.
