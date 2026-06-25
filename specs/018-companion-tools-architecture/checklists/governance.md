# Governance Checklist: Companion Tools Architecture

**Purpose**: Verify this feature respects Core Authority -- the architectural rule binding all
ten features -- and the constitution's honesty/scope guardrails. This is the "does it respect
Core Authority" gate for F024.
**Created**: 2026-06-25
**Roadmap feature**: F024 (on-disk spec 018)
**Feature**: [spec.md](../spec.md)

## Core-vs-Module authority (the matrix is the gate)

- [ ] CHK-G01 The authority matrix shows ONLY Core Authority with `yes` on CREATES truth
      (business meaning, metric, mapping). Every other category is `no`. (FR-002)
- [ ] CHK-G02 The authority matrix shows ONLY Core Authority with `yes` on GRANTS approval /
      moves a stage to `pass`. Every other category is `no`. (FR-002)
- [ ] CHK-G03 Every non-Core category (Workflow Skill, Module, Adapter, Maintenance) may READ
      evidence, SUMMARIZE/VISUALIZE, write DERIVED evidence, and EXECUTE an approved step --
      and nothing beyond what the matrix grants. (FR-008)
- [ ] CHK-G04 Modules and Adapters operate ONLY from committed evidence or named-human-approved
      runtime evidence -- never from self-generated truth. (FR-008)
- [ ] CHK-G05 No tool may self-classify into Core Authority; classifying a truth-creating
      proposal into a non-Core category is a defect. (FR-002, edge cases)

## Principle V -- stop-and-ask, no self-approval

- [ ] CHK-G06 A proposed tool that would create truth is a STOP-and-ask (Core Authority with a
      named human, or rejected), never auto-classified to gain that power. (Principle V; edge cases)
- [ ] CHK-G07 An Execution Adapter asked to DEFINE what it executes (e.g. invent a measure) is
      forbidden and surfaced as stop-and-ask -- the definition must pre-exist in Core Authority. (edge cases)
- [ ] CHK-G08 A Module asked to "approve" a stage so a pipeline can proceed is forbidden; it
      surfaces the missing approval as a blocker and the named human decides. (edge cases)
- [ ] CHK-G09 The human approval boundary names the architecture owner as the approver of the
      contract itself and any change to the categories / matrix / sub-axes -- no tool self-grants. (Human approval boundary)

## No self-granted capability (module/adapter seam)

- [ ] CHK-G10 Every Product Module declares exactly one capability from the CLOSED set
      { read-only, artifact-writing, execution-capable }; no other level is valid. (FR-003)
- [ ] CHK-G11 Every Execution Adapter declares exactly one connectivity from the CLOSED set
      { local-only, DB-connected, external-service-connected, publish-capable }; no other is valid. (FR-004)
- [ ] CHK-G12 The module-vs-adapter seam (external trust/connectivity boundary) makes the two
      categories disjoint: local-only execution -> Module; DB/external/publish -> Adapter. (FR-005)
- [ ] CHK-G13 Maintenance Automation runs without a per-invocation human trigger, emits ONLY
      derived evidence, and may NOT publish (publish is an Adapter capability) or create truth. (FR-006)

## No fake confidence (Principle IX / rule #9)

- [ ] CHK-G14 No numeric/maturity score is emitted for any tool; category is an explicit name. (FR-011)
- [ ] CHK-G15 Readiness vocabulary anywhere referenced is status + evidence[] + blocking_reasons[]
      only -- never a fabricated confidence number. (FR-011; readiness-model)
- [ ] CHK-G16 The maturity-level concept is explicitly DEFERRED to F033, not introduced here. (Deferred decisions)

## Generic (no worked-example bake-in -- Principle VII)

- [ ] CHK-G17 Zero C086 / retail_store_sales specifics (billing codes, segment rollups, PII
      columns, per-table grain keys) appear in any of the five files. (FR-013, SC-004)
- [ ] CHK-G18 The worked example is CITED as a filled reference only; its values are not inlined. (FR-013)

## Secrets / paths / encoding

- [ ] CHK-G19 No secrets, DSNs, tokens, Kaggle/Power BI credentials, or local machine paths
      appear in any file.
- [ ] CHK-G20 Every file is ASCII + UTF-8 no BOM: no Unicode arrows, em-dashes, or smart quotes
      (Principle IX; Windows charmap). `->` and `--` used throughout.

## Allowed-vs-forbidden operations (the scope wall)

- [ ] CHK-G21 Allowed operations are limited to: author the five spec-kit files; READ the
      roadmap/constitution/shipped specs; DEFINE the categories/matrix/sub-axes; ENUMERATE the
      five future deliverables; CITE the worked example. (Allowed operations)
- [ ] CHK-G22 No runtime code, UI, dbt, Dagster, or Power BI execution code is written. (FR-010; Forbidden operations)
- [ ] CHK-G23 None of the five future deliverables (product-modules.md,
      core-vs-modules-and-adapters.md, ADR 0008, module-contract.md, adapter-contract.md) is
      created this slice -- enumerated only. (FR-009; Forbidden operations)
- [ ] CHK-G24 No `retail check` rule, CLI verb, conformance checker, or readiness stage is
      added; `retail check` stays exit 0 and no new rule is added. (FR-010, FR-012, SC-005)
- [ ] CHK-G25 The Six product layers are CITED, not replaced, renumbered, or merged; the five
      categories are stated orthogonal to them (a tool carries two coordinates). (FR-007, SC-006)

## Evidence required (the feature must produce)

- [ ] CHK-G26 The five committed spec-kit files exist, ASCII + no BOM, each header stating both
      `018` and `F024` plus the numbering note. (Evidence required)
- [ ] CHK-G27 The authority matrix and the shipped-feature classification table are present in
      the spec (proof the taxonomy is real and Core Authority is the sole truth-holder). (FR-014; Evidence required)
- [ ] CHK-G28 A record that no new `retail check` rule was added (verified by the diff). (Evidence required)

## Notes

- This checklist maps each of the spec's Forbidden operations and the Human approval boundary
  to a concrete CHK item, and turns each row of the authority matrix into a checkable gate
  (CHK-G01..CHK-G04). It is the feature's Core-Authority conformance gate.
- The single highest-risk failure mode is a non-Core category silently gaining truth-creating
  or approval-granting power (CHK-G01/G02/G06) -- the matrix exists to make that impossible to
  miss in review.
- The second-highest risk is scope-bleed: shipping a checker, authoring a future deliverable,
  or renumbering the layers (CHK-G22..G25). These are checked explicitly because they are the
  ways this planning slice could over-reach into a build slice.
