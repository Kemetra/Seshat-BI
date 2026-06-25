# Governance Checklist: Evidence Pack Generator

**Purpose**: Verify the feature respects Core Authority -- the module composes and
surfaces evidence, never creates truth. This is the feature's "does it respect Core
Authority" gate, mapping the spec's Forbidden operations + Human approval boundary to
the architectural rules binding all features.
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md)  **Roadmap feature**: F028 (dir 022)

## Core-vs-Module authority

- [ ] CHK-G01 The module is classified as a PRODUCT MODULE (artifact-writing, derived
      evidence only) -- it READS, SUMMARIZES, LINKS, and WRITES a DERIVED pack; it does
      NOT create truth. (spec "Architecture"; Core Authority rule)
- [ ] CHK-G02 The module defines NO business meaning, approves NO metric or mapping, and
      authors NO source artifact -- it only summarizes/links what upstream features already
      produced. (spec Forbidden operations; FR-002)
- [ ] CHK-G03 The Core Authority artifacts remain the single source of truth:
      `readiness-status.yaml`, `source-map.yaml`, `mappings/<table>/`, metric contracts,
      approvals[] -- the pack reads them, never overwrites them. (FR-005, FR-010)
- [ ] CHK-G04 The F013 relationship is one-directional: F028 CONSUMES and EMBEDS F013 as
      section 08 and NEVER re-authors, edits, or redefines the handoff template, and NEVER
      records the publish approval (F013 / Core Authority owns it). (FR-004; scope delta)

## Principle V -- stop at judgment calls

- [ ] CHK-G05 Publish authorization is a HUMAN decision the pack surfaces, never makes;
      the module recommends nothing about whether to publish beyond showing the recorded
      state. (spec Human approval boundary; FR-005, FR-006)
- [ ] CHK-G06 Disagreeing upstream sources are SURFACED with both source links + a `warning`
      for human resolution; the module never silently reconciles or picks a winner. (FR-009)
- [ ] CHK-G07 Grain ambiguity, PII publish-safety, business rollup/segment mappings, and
      sentinel-vs-null questions appearing in any section are recorded as stop-and-ask
      `warning`/`blocked` items, never auto-resolved by the module. (spec edge cases; FR-009)

## No self-approval / no stage promotion

- [ ] CHK-G08 The module writes NO approval into `readiness-status.yaml` `approvals[]`.
      (FR-005; spec Forbidden operations)
- [ ] CHK-G09 The module moves NO readiness stage to `pass` -- it composes evidence and
      surfaces the state the Core Authority artifacts already record. (FR-005; Principle I)
- [ ] CHK-G10 The pack prints a publish-ready CLAIM only when `publish_ready: pass` with a
      named recorded approval exists; otherwise it shows the upstream blocking reasons.
      (FR-006; SC-004)

## No fake confidence

- [ ] CHK-G11 Readiness is expressed ONLY as the four explicit statuses
      (`not_started` / `blocked` / `warning` / `pass`) + `evidence[]` + `blocking_reasons[]`.
      (FR-007)
- [ ] CHK-G12 NO numeric confidence/health score is emitted anywhere; an optional factual
      "N of 10 sections present" tally (deferred) must read as a tally, never as confidence.
      (FR-007; hard rule #9; spec Deferred decisions)
- [ ] CHK-G13 A `warning` NEVER auto-promotes to `pass`; a missing source is `blocked`, never
      softened to an adjective or a number. (FR-003, FR-007)

## Compose, never invent

- [ ] CHK-G14 Every section is composed from + links back to an EXISTING committed source;
      no section originates content from nothing. (FR-002; SC-001, SC-002)
- [ ] CHK-G15 A missing / unfilled / blank-template source is recorded as a `blocked` section
      with a blocking reason naming the source -- the module synthesizes NO substitute
      content (no invented profile rows, contracts, totals, summaries, or handoff). (FR-003)

## Generic (no worked-example baked in)

- [ ] CHK-G16 The spec, plan, future skill, doc, and templates stay generic -- no C086 /
      retail_store_sales values (billing codes, segment rollups, PII columns, grain keys);
      the worked example is cited by reference only. (FR-011; Principle VII)
- [ ] CHK-G17 The 10-section contract uses generic placeholders (`<schema>.<table>`,
      `<source>`); worked-example specifics live only in that example's own filled artifacts.

## Secrets / paths / reproducibility

- [ ] CHK-G18 No secrets, DSNs, tokens, Kaggle / Power BI credentials, or local machine paths
      anywhere in any delivered artifact. (Principle IX; repo hard rule)
- [ ] CHK-G19 All artifacts are ASCII, UTF-8 without BOM, and use short repo-relative paths
      within the Windows `MAX_PATH` budget. (FR-012; Principle IX)

## Allowed-vs-forbidden operations

- [ ] CHK-G20 The spec lists ALLOWED ops (read committed sources + readiness-status.yaml;
      summarize/link; write derived pack; record status; embed F013 as section 08; surface
      publish state read-only) and they match the architectural "may read/summarize/visualize/
      write-derived/execute-approved" envelope. (spec Allowed operations)
- [ ] CHK-G21 The spec lists FORBIDDEN ops (invent content; write/imply approval; move a stage;
      edit/redefine a source incl. F013; emit a score; read live DB/PBIP; call F016; publish;
      add a rule / new stage; silently reconcile; inline C086) and none is contradicted by any
      FR or user story. (spec Forbidden operations)
- [ ] CHK-G22 No live database read, no PBIP read, no Power BI execution adapter (F016) call,
      and no publish/deploy is introduced -- the module reads only committed artifacts.
      (FR-010; Principle VIII)
- [ ] CHK-G23 This planning slice creates ONLY the 5 spec-kit files; the four future
      deliverables are enumerated as PLANNED outputs, not built. (plan.md "PLANS (not created)")

## Evidence required

- [ ] CHK-G24 Each section carries: source artifact path(s), status (one of four),
      `evidence[]`, and `blocking_reasons[]` for any gap. (spec Evidence required; FR-007)
- [ ] CHK-G25 The pack summary's surfaced state (current stage, `publish_ready`, recorded
      approval owner + date, rolled-up blockers) is each traceable to `readiness-status.yaml`
      or a section source -- nothing asserted without a source link. (spec Evidence required)

## Notes

- The two governance flashpoints for this feature are (1) the F013 boundary -- the module must
  never become a competing or re-authored handoff (CHK-G04), and (2) publish authority -- the
  module must surface, never assert, publish-readiness (CHK-G05, CHK-G08..G10).
- Every forbidden operation in the spec maps to at least one CHK item above; this checklist is
  the gate that the spec's allowed/forbidden split actually respects Core Authority.
