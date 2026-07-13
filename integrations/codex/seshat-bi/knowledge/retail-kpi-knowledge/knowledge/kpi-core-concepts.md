# KPI Core Concepts

Foundational vocabulary for this layer. IDs use the `KPI-CN-*` convention
(see `references/id-conventions.md`).

## KPI-CN-01 — KPI vs metric vs measure

These three words are often used interchangeably and that is where confusion starts.
This layer keeps them distinct:

- **KPI** — a business performance indicator tied to a decision or goal (e.g.,
  "Net Sales vs Target %"). A KPI has an owner and a reason to exist.
- **Metric** — the quantified concept behind a KPI, expressed as a business-terms
  definition and formula (e.g., net sales = gross sales − discounts, pre-tax).
- **Measure** — the *implemented* calculation in the semantic model (DAX). Measures
  belong to the DAX layer, **not** here.

This layer owns KPIs and metrics. It hands measures off.

## KPI-CN-02 — Business definition before formula

A KPI is not safe until a plain-language definition exists that a non-technical
stakeholder would agree with. The definition states what is counted, what is excluded,
and which policies apply. Only after the definition is agreed do we write the
business-terms formula. A formula without an agreed definition encodes a guess.

## KPI-CN-03 — Contract before DAX

No DAX measure should be written until a metric contract exists and passes the
metric-contract-review-checklist. The contract is the single source of truth that the
DAX, dashboard, and readiness layers all reference. Writing DAX first is an anti-pattern
(`KPI-AP-03`).

## KPI-CN-04 — KPI owner

Every KPI has exactly one accountable business owner (e.g., Finance for revenue,
Commercial for discounts, Supply Chain for inventory). The owner resolves policy
ambiguities and signs off the definition. A KPI with no owner cannot be validated and
must not reach a dashboard (`KPI-AP-01`).

## KPI-CN-05 — Required fields

The concrete source fields a KPI depends on, drawn from fact and dimension tables.
Each field is marked **confirmed**, **assumption** (likely exists, needs source-owner
confirmation), or **derived**. This layer never asserts that a field exists; unconfirmed
fields stay flagged so downstream layers know what to verify. See
`references/source-field-requirements.md`.

## KPI-CN-06 — Dimensions

The attributes a KPI can be sliced by (date, branch, region, channel, product,
category, brand, supplier, customer segment). Recommended dimensions are part of the
contract because they shape both the model and the dashboard, and because some KPIs are
only meaningful at certain grains.

## KPI-CN-07 — Filters / exclusions

The rules that decide which rows qualify: exclude cancelled/void/test transactions,
decide returns handling, decide VAT inclusion, exclude internal transfers or staff
sales by policy. Filters belong in the contract because two reports applying different
filters will disagree even with identical data.

## KPI-CN-08 — Validation checks

The reconciliation and sanity steps that confirm a KPI is trustworthy: reconcile to a
source-of-truth report, spot-check sample records, bound-check ratios (0–100%), and
confirm empty periods show zero rather than blanks. Validation checks are listed in the
contract and run before dashboard use — but **passing them is not a readiness grant**;
readiness is owned by the Readiness layer.
