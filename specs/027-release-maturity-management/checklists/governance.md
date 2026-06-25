# Governance Checklist: Release & Maturity Management

**Purpose**: Verify the feature respects Core Authority -- the architectural rule binding all
companion-tool features. A module may READ evidence, SUMMARIZE it, VISUALIZE it, write
DERIVED evidence, or EXECUTE approved steps; it MUST NOT create truth (no self-approval, no
defining business meaning, no approving a release/level, no publishing, no moving a state to
pass/approved without the required evidence + a named human).
**Created**: 2026-06-25
**Roadmap feature**: F033 (spec-dir 027; roadmap F-number authoritative)
**Feature**: [spec.md](../spec.md)

> Items are unchecked `[ ]`: this is the gate a reviewer runs against the spec before the
> feature is built. Each maps to a Forbidden operation, the Human approval boundary, or a
> constitutional principle.

## Core-vs-Module authority

- [ ] CHK-G01 The release-notes-generator is a MODULE: it READS evidence (F028 pack, F032
      matrix, roadmap ledger), SUMMARIZES it into a release note, and writes DERIVED artifacts
      under `docs/releases/` -- it does NOT create truth. (Core Authority)
- [ ] CHK-G02 The module never defines a capability's meaning or a release's significance on
      its own authority; "what became possible" is a derivation FROM cited evidence, never a
      claim the module originates. (Core Authority; FR-004/FR-011)
- [ ] CHK-G03 The module writes a release note / maturity snapshot as `draft`; the truth-making
      transition to `approved` belongs to a named human release owner, not the module. (FR-010)

## Principle V -- stop at judgment calls

- [ ] CHK-G04 Release approval (`draft -> approved`) is stop-and-ask: the module recommends +
      drafts, a named release owner decides. (Principle V; FR-010)
- [ ] CHK-G05 Level confirmation is stop-and-ask AND evidence-gated: a level the evidence does
      not support is refused by the binary rung test regardless of who asks; the human confirms
      only a level the evidence already supports. (Principle V; FR-005/FR-007)
- [ ] CHK-G06 Conflicting inputs (e.g. matrix asserts an adapter version but no adapter exists
      in-repo) are SURFACED as a finding, never silently resolved by the module. (Principle V;
      FR-012)

## No self-approval / no self-promotion

- [ ] CHK-G07 The module MUST NOT self-approve a release. (Forbidden op; FR-010)
- [ ] CHK-G08 The module MUST NOT self-confirm or self-bump a maturity level. (Forbidden op;
      FR-005/FR-010)
- [ ] CHK-G09 The module MUST NOT publish (no git tags, GitHub releases, registry publish, no
      Power BI publish). (Forbidden op; Non-goals)
- [ ] CHK-G10 The module MUST NOT move any per-table readiness stage to `pass`; release/maturity
      is orthogonal to the readiness spine and advances no stage. (Readiness stage affected =
      NONE)

## No fake confidence (hard rule #9) -- the crux gate

- [ ] CHK-G11 The maturity ladder is defined as EVIDENCE-GATED MILESTONES (a binary
      "evidence exists or not" test per rung; level = highest all-evidence-present rung),
      explicitly reconciled against hard rule #9 as analogous to the seven numbered readiness
      stages -- NOT a score. (FR-005/FR-006; the dedicated crux item.)
- [ ] CHK-G12 No artifact emits a percentage, a 0-100 number, an average, or any number that
      reads as confidence; a numeric-maturity-score request is DECLINED citing hard rule #9.
      (FR-006)
- [ ] CHK-G13 No capability / "production ready" / "GA" / "enterprise grade" claim is made
      without a backing evidence rung; with no backing rung the claim is refused. (FR-008)
- [ ] CHK-G14 The honest current state is pinned and verifiable: L1/L2 achieved (c086 +
      retail_store_sales), L3 caveated to those two tables, L4/L5/L6 NOT BUILT with the missing
      artifact named -- no rounding up. (FR-007; SC-003)

## Consume-never-re-measure

- [ ] CHK-G15 Evidence is CONSUMED from the F028 pack + F032 matrix + roadmap ledger; the
      module runs NO `retail check` / `retail validate`, profiles no source, opens NO DB
      connection, and reads NO `powerbi/`. (FR-009)
- [ ] CHK-G16 A missing input is recorded as "evidence not available", never fabricated; the
      note stays `draft`. (FR-009; edge cases)

## Generic (no per-table specifics)

- [ ] CHK-G17 `templates/release-notes.md` and `templates/maturity-report.md` carry NO
      per-table specifics (no billing codes, segments, PII columns, grain keys); they use
      placeholders only. (Principle VII; FR-002)
- [ ] CHK-G18 c086 and retail_store_sales appear ONLY as cited evidence FOR the ladder (the
      kit's real track record), never baked into generic template logic. (Principle VII;
      Assumptions)

## Secrets / paths / encoding

- [ ] CHK-G19 No secrets, DSNs, tokens, Kaggle/Power BI credentials, or local machine paths in
      any of the five files. (Principle IX)
- [ ] CHK-G20 All five files are ASCII + UTF-8 no BOM (no Unicode arrows/dashes/quotes; `->`
      for arrows, `--` for dashes), repo-relative paths short (<= 200 chars). (Principle IX)

## Allowed-vs-forbidden ops

- [ ] CHK-G21 Allowed ops are exactly: READ the cited inputs; DRAFT a release note + ASSESS a
      rung into DERIVED `draft` artifacts; SUMMARIZE/CITE evidence; SURFACE conflicts. (Allowed
      operations)
- [ ] CHK-G22 Forbidden ops are explicitly listed and each maps to a CHK above: numeric score
      (G12), unbacked claim (G13), level above evidence (G11/G14), self-approval (G07),
      self-level-bump (G08), publish (G09), re-measurement (G15), new rule/CLI/gate/validator
      (G23). (Forbidden operations)
- [ ] CHK-G23 The feature adds NO `retail check` rule, NO CLI verb, NO validator, NO new gate;
      no new `retail check` rule is added (checker stays exit 0). (Principle VIII; SC-001)

## Evidence-required

- [ ] CHK-G24 Every "what became possible" claim names a committed source (file/commit or the
      cited F028 entry); every rung verdict names the artifact whose presence/absence its
      binary test checks; `approved` status names a release owner + date. A claim or verdict
      with no traceable source is a defect. (FR-011; Evidence required)

## Enumerate-don't-create (planning slice integrity)

- [ ] CHK-G25 The four future deliverables (`templates/release-notes.md`,
      `templates/maturity-report.md`, `.claude/skills/release-notes-generator/SKILL.md`,
      `docs/releases/`) are ENUMERATED as planned outputs and CREATED by none of the five files
      written this slice. (SC-001)

## Notes

- The single highest-risk governance item is CHK-G11/CHK-G12: a numbered 0-6 ladder is exactly
  where the no-fake-confidence rule is most likely to be violated. It passes ONLY because the
  ladder is evidence-gated milestones with a binary test per rung -- the same structural device
  the seven numbered readiness stages use -- and never a percentage or score.
- F024 (companion-tools taxonomy) supplies the Core-Authority module rules this checklist
  enforces; F028 (evidence pack) and F032 (compatibility matrix) are the consumed inputs.
  These siblings are referenced by id + role; this gate does not depend on their internal
  structure.
