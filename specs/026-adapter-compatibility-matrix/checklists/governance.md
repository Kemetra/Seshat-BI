# Governance Checklist: Adapter Compatibility Matrix

**Purpose**: Verify this feature respects Core Authority -- it RECORDS verified versions and never CREATES truth, enforcement, or adapter behavior it does not own
**Created**: 2026-06-25
**Roadmap feature**: F032 (on-disk spec-dir 026)
**Feature**: [spec.md](../spec.md)

> These `[ ]` items are gate items. They map 1:1 to spec.md's **Forbidden operations**
> and **Human approval boundary**. An unchecked item is a governance defect that must be
> resolved before the future authoring slice proceeds.

## Core-vs-Module authority (the matrix is a RECORD, not truth-maker)

- [ ] **G-01** The matrix RECORDS verified versions; it does not CREATE the truth of
      compatibility. A row becomes supported only via a named owner attesting a passed
      smoke test -- the record summarizes/visualizes that evidence, it does not self-grant
      it. [Forbidden: self-attesting / self-promoting a cell]
- [ ] **G-02** F032 does not define the Maintenance Automation category or the
      companion-vs-core authority rule (that is F024); it is one entry inside that category.
- [ ] **G-03** F032 does not create enforcement: no PR gate, no CI fail condition, no merge
      block, no enforcement logic in the matrix. Enforcement is the F031 policy.
      [Forbidden: adding enforcement logic to the matrix]
- [ ] **G-04** F032 does not create adapter behavior: it does not author, modify, or execute
      the F029 dbt adapter, the F030 Dagster adapter, or the F016 Power BI execution adapter.
      [Forbidden: building/running an adapter]

## Principle V -- stop at judgment calls (recommend, do not decide)

- [ ] **G-05** When a version/range/adapter is untested, the agent marks it `unknown` and
      STOPS -- it surfaces the uncertainty and does not infer "compatible". [Human approval
      boundary: stop-and-ask = mark UNKNOWN, never infer]
- [ ] **G-06** The agent recommends and records; the named owner decides and attests. The
      only path to a supported status is a named owner attesting a passed smoke test
      (evidence = result + run date + owner). [Human approval boundary]
- [ ] **G-07** The classic data judgment calls (grain, PII publish-safety, business rollup)
      are explicitly stated N/A for a version record -- not fake-fitted, not auto-answered.
      The one judgment call ("is this version verified?") is surfaced as G-05.

## No self-approval / no self-promotion

- [ ] **G-08** The agent never self-attests as the owner of a row. [Forbidden: self-attesting]
- [ ] **G-09** The agent never self-promotes a cell from `unknown` to supported. A promotion
      requires the named owner's attestation as evidence. [Forbidden: self-promoting a cell]
- [ ] **G-10** A row with no named attesting owner reads `UNASSIGNED` and is flagged; it does
      not silently become supported. [Edge case: missing owner]

## No fake confidence (hard rule #9 / Principle IX)

- [ ] **G-11** An UNKNOWN version/range/adapter is recorded `unknown` -- never supported,
      never `pass`, never inferred from "probably works". [Forbidden: marking untested as
      supported by inference]
- [ ] **G-12** No numeric compatibility/confidence score appears anywhere; the matrix carries
      explicit status (`pass`/`warning`/`blocked`/`not_started`/`unknown`) + evidence only.
      [Forbidden: emitting a numeric score]
- [ ] **G-13** A named-but-unrun smoke test yields `unknown` ("named, not yet run"), not
      supported. [Edge case: smoke test exists in name but never run]
- [ ] **G-14** Every supported row is backed by evidence: the named smoke test, its passed
      result, its last-verified date, and the attesting owner. A supported status with no
      evidence is a defect. [Evidence required]

## Generic (no C086 / retail_store_sales)

- [ ] **G-15** No worked-example specifics (billing codes, segments, PII column names, grain
      keys) appear in any field shape or example; C086 / retail_store_sales is cited as an
      example, never inlined. [Forbidden: inlining C086 specifics; Principle VII]
- [ ] **G-16** Concrete version strings in a future filled matrix are treated as environment
      facts, not pharmacy specifics; this planning slice carries placeholders only.

## Secrets / paths (Principle IX)

- [ ] **G-17** No secrets, DSNs, connection strings, tokens, or credentials appear in any
      artifact. [Forbidden: inlining secrets]
- [ ] **G-18** No local machine paths; repo-relative paths only, kept short (Windows budget).
      All files ASCII + UTF-8 no BOM; `->`/`--` used, no Unicode symbols. [Forbidden: local paths]

## Allowed-vs-forbidden operations (the scope wall)

- [ ] **G-19** This slice creates ONLY the five Spec-Kit planning files; the matrix doc and
      record template are enumerated as FUTURE outputs, not created now. [Forbidden: creating
      any file other than the five planning files]
- [ ] **G-20** No runtime code, no CLI subcommand, no `retail check` rule, no new gate, no CI
      job, no dbt/Dagster/Power BI artifact is added this slice; `retail check` stays exit 0 and
      no new rule is added. [Forbidden: adding runtime code / CLI / rule / gate]
- [ ] **G-21** No smoke test is authored, run, or wired into CI; the matrix names the required
      smoke test and records its last result only. [Forbidden: authoring/running smoke tests]

## Evidence required (the record's own honesty)

- [ ] **G-22** Every matrix cell is traceable: a supported status names its smoke test + run
      date + owner; an `unknown` names its missing-evidence blocker in `blocking_reasons[]`. A
      cell with no traceable evidence is a defect. [Evidence required]
- [ ] **G-23** The record/policy boundary is traceable in the artifact: a reader can point to
      where the matrix states "F032 records; F031 enforces" and confirm no enforcement logic is
      present. [SC-005]

## Readiness stage authority

- [ ] **G-24** F032 advances NO readiness stage and moves no stage to `pass`. It states
      "readiness stage affected: none directly" and is positioned as a Maintenance Automation
      record, not a spine gate. [Readiness stage affected; Forbidden: moving a stage to pass]

## Notes

- This governance gate is the feature's "does it respect Core Authority" check. The dominant
  risks are scope-bleed from the RECORD into the POLICY (G-03, G-23 -- enforcement is F031) and
  from the RECORD into the ADAPTERS (G-04, G-21 -- build/run is F029/F030/F016), plus the
  no-fake-confidence guardrail (G-11..G-14 -- UNKNOWN is never compatible).
- Items map 1:1 to spec.md Forbidden operations (G-01/G-03/G-04/G-08/G-09/G-11/G-12/G-15/G-17/
  G-18/G-19/G-20/G-21/G-24) and Human approval boundary (G-05/G-06/G-09/G-10).
- The agent's authority here is to AUTHOR the planning files, ENUMERATE the future deliverables,
  READ to cite boundaries, and (in a later slice) RECORD an `unknown` for any untested cell. It
  has NO authority to attest a version, enforce a PR, build an adapter, or invent a score.
