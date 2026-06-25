# Specification Quality Checklist: Release & Maturity Management

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-25
**Roadmap feature**: F033 (spec-dir 027; roadmap F-number authoritative)
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) -- this is a docs/planning
      slice; the "fields" described are template/skill shapes, the artifacts this feature
      will later deliver, not application code.
- [x] Focused on user value and business needs (a maintainer/release-owner/BI-consumer needs
      an honest "what became possible + how mature" record).
- [x] Written for non-technical stakeholders (the release owner reads it to approve).
- [x] All mandatory sections completed (Why / scope wall / scope delta / architecture / user
      scenarios / requirements / success criteria / approval boundary / allowed / forbidden /
      evidence / readiness stage / dependencies / non-goals / assumptions / deferred / see also).

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain.
- [x] Requirements are testable and unambiguous (FR-001..FR-013).
- [x] Success criteria are measurable (SC-001..SC-005).
- [x] Success criteria are technology-agnostic (no implementation details leak).
- [x] All acceptance scenarios are defined (US1 notes, US2 ladder, US3 honesty guard).
- [x] Edge cases are identified (no evidence pack, partial rung evidence, F028/F032 not yet
      authored, conflicting evidence, an over-claiming release owner).
- [x] Scope is clearly bounded (the scope wall + scope-delta vs F012/F013/F015/F028/F032/F024;
      readiness stage affected = NONE).
- [x] Dependencies and assumptions identified (F024 taxonomy, F028 evidence pack, F032 matrix;
      sibling specs referenced by id + role, not internal structure).

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (each FR maps to a US or SC).
- [x] User scenarios cover primary flows (generate notes / assess maturity / refuse overclaim).
- [x] Feature meets measurable outcomes defined in Success Criteria.
- [x] No implementation details leak into specification.

## Feature-specific acceptance (Release & Maturity)

- [x] **Seven release-note blocks** are all required (FR-004): what became possible / what
      changed / readiness stages affected / new modules+adapters / known limitations /
      migration notes / next best slice -- each "became possible" claim cites evidence.
- [x] **Two distinct templates** are planned (FR-002): `release-notes.md` (per-release) and
      `maturity-report.md` (point-in-time ladder) -- not merged.
- [x] **Maturity ladder is evidence-gated milestones**, not a score (FR-005/FR-006): seven
      rungs L0..L6, a binary evidence test per rung, level = highest all-evidence-present rung.
- [x] **No numeric maturity score** anywhere (FR-006): a "score out of 100" request is
      DECLINED citing hard rule #9.
- [x] **Honest current state pinned** (FR-007): L1/L2 achieved (c086 + retail_store_sales),
      L3 caveated to those two tables, L4 (dbt) / L5 (Dagster) / L6 (Power BI execution) NOT
      BUILT with the missing artifact named -- matches the repo today.
- [x] **No capability without evidence** (FR-008): "production ready"/"GA"/"enterprise grade"
      refused with no backing rung; today the kit makes no production claim.
- [x] **Consume-never-re-measure** (FR-009): inputs are the F028 pack + F032 matrix + roadmap
      ledger; no `retail check`/`validate`, no DB, no `powerbi/` read; missing input ->
      "evidence not available", never fabricated.
- [x] **Human approval boundary** present (FR-010): release owner approves `draft -> approved`
      + confirms level; the skill drafts/assesses only.
- [x] **Evidence traceability** (FR-011): every capability claim + rung verdict names a
      committed source.
- [x] **Readiness stage affected = NONE**: stated explicitly (product-level process).
- [x] **Future deliverables enumerated, not created** (SC-001): `templates/release-notes.md`,
      `templates/maturity-report.md`, `.claude/skills/release-notes-generator/SKILL.md`,
      `docs/releases/` are planned outputs only; this slice writes only the five spec-kit files.

## Notes

- This is a docs/planning slice (Principle VIII, roadmap rule #8): no runtime code, so
  "implementation details" here means template/skill field shapes -- the artifacts this
  feature will later deliver, not application code.
- Citing c086 and retail_store_sales as the kit's track record is allowed evidence-citation
  (the evidence FOR the ladder), distinct from baking per-table logic into a generic template
  (Principle VII forbids the latter, not the former).
- The crux acceptance item is the maturity-ladder-vs-score reconciliation: the numbered 0-6
  ladder is legitimate ONLY because it is evidence-gated milestones (like the seven numbered
  readiness stages), with a binary test per rung -- not a percentage. This is cross-checked
  in governance.md as a dedicated CHK.
- F028 and F032 are sibling specs in this batch; this spec references them by id + role and
  does not depend on their internal structure being finalized.
