# Ratify Ledger — Spec 123: Governed Dashboard Intelligence and PBIR Authoring

**Feature**: 123-governed-dashboard-intelligence
**Ratified by**: Ahmed Shaaban (report_owner)
**Date**: 2026-07-12
**Status transition**: Draft → Ratified

## What was ratified

The owner explicitly ratified spec 123 and directed implementation of the full spec ("implement all spec 123"). This is a named, per-feature authorization (Constitution Principle V) — it applies to spec 123 only and does not blanket-authorize other specs.

## Authorizations granted with this ratification

1. **Spec ratification** — `spec.md` Status stamped `Ratified (Ahmed Shaaban, 2026-07-12)`.
2. **PBIR-creation ADR** — the owner authorized drafting and ratifying `docs/decisions/0017-pbir-creation-primitive.md`, which lifts the ADR-0015/0016 exclusion on *creating* PBIR pages/visuals, bounded to the allow-list in that ADR. Agent drafted; owner ratified by name.

## Explicitly NOT cleared by this ratification (data gaps, not authority gaps)

- **T039–T042** (US7 increments: KPI cards, column/bar charts, slicers+navigation, supported interactions) remain **BLOCKED**. They require real Power BI Desktop-authored reference sample JSON that does not exist in the repository. Ratification grants authority, not sample data. These stay unimplemented with a logged "awaiting owner Desktop sample" note; the repo forbids building against the `geometry.Report` placeholders (FR-029 + the shipped Increment-C hold precedent).

## Buildable scope this session

US1, US2 (MVP), US3, US4, US5, US6, US8, and US7 increments **1 (page shell, T037)** and **3-lineChart (T038)** only — the increments with an existing verified reference sample.

## Human seams that remain open after implementation

- Per-instance `report_intent_approval` / `dashboard_blueprint_approval` decisions (recorded by named humans at run time; the code provides the machinery, never the approval).
- Owner-supplied PBIR Desktop samples to unblock T039–T042.
- The final merge decision on the implementation PR (the build workflow stops PR-ready; it never merges).
