# Specification Quality Checklist: dbt Transformation Adapter

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md)  **Roadmap feature**: F029 (spec-dir 023)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) leak as REQUIREMENTS -- dbt is
      named as the engine being adapted, which is the feature's subject, not an implementation
      leak; no dbt SQL/Jinja is authored in the spec
- [x] Focused on user value and business needs (a gated optional build engine that keeps
      Tower BI the authority)
- [x] Written for a reviewer evaluating the gate, not for an implementer
- [x] All mandatory sections completed (Why / scope wall / scope delta / architecture / user
      scenarios / requirements / success criteria / approval boundary / allowed + forbidden
      ops / evidence / readiness stage / dependencies / non-goals / assumptions / deferred)

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (parity tolerance + dimension-row assertion
      recorded as Deferred decisions with stated defaults, not blockers)
- [x] Requirements are testable and unambiguous (FR-001..FR-012)
- [x] Success criteria are measurable (SC-001..SC-007: gate, parity assertions, no-auto-pass
      path, zero leak, zero dbt files, no secrets, explicit auto-update policy)
- [x] Success criteria are technology-agnostic where they should be (the gate/evidence/parity
      rules); dbt-specific success criteria name dbt because dbt is the feature's subject
- [x] All acceptance scenarios are defined (US1 gate / US2 citation / US3 evidence-not-approval
      / US4 parity, each Given/When/Then)
- [x] Edge cases identified (models without an approved map, sentinel divergence, grain
      change, secret in profiles.yml, major-version PR, green-test-without-readiness)
- [x] Scope clearly bounded (the scope wall + Non-goals; planning-only; DB-connected not
      publish-capable)
- [x] Dependencies and assumptions identified (F024 category, F005 spine, the approved map,
      `warehouse/migrations` as default + parity target)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (each FR maps to a US
      scenario or a Success Criterion)
- [x] User scenarios cover the primary flows (build-behind-gate, cite-the-map,
      evidence-not-approval, reconcile-to-gold)
- [x] Feature meets the measurable outcomes defined in Success Criteria
- [x] No implementation details leak into the specification beyond naming dbt as the engine

## Reconciliation-specific completeness (feature-specific)

- [x] The parity target is named concretely: `gold.fct_sales_rss` and its dims from
      `warehouse/migrations/0004_*` (the migration output dbt must reproduce)
- [x] The three parity assertions are stated: equal row count, preserved `transaction_id`
      distinct count, additive-measure (`total_spent`) sum within a stated tolerance
- [x] The optional-alternative posture is explicit: migrations stay the DEFAULT until parity
      passes AND a named human approves the switch; the two paths never silently feed the same
      gold tables
- [x] The first MVP to PLAN is bounded: one `retail_store_sales` staging model + one mart
      model + basic tests (`unique`/`not_null`/`relationships` + reconciliation)

## Planning-only completeness (feature-specific)

- [x] This slice writes ONLY the five spec-kit files; the dbt project + contracts + ADR +
      integration doc + skill are ENUMERATED as planned future outputs, not created
- [x] `profiles.example.yml` (no secrets) is the only profile planned for commit;
      `profiles.yml` is enumerated as git-ignored
- [x] The auto-update policy is stated (pin dbt-core + dbt-postgres; patch/minor -> PR;
      major -> human review; no automerge for minor/major until compatibility tests exist)

## Notes

- This is a PLANNING-ONLY slice for a DB-connected EXECUTION adapter. "No implementation
  details" is interpreted relative to that: the spec may name dbt (the engine being adapted)
  and the parity target (the existing migration gold tables) because those are the feature's
  subject; it authors no dbt SQL/Jinja and no runtime code.
- The single highest-risk drift -- treating a green `dbt test` as an approval -- is closed by
  FR-004, US3, SC-003, and the Human approval boundary + Forbidden operations sections, and is
  re-checked in `governance.md`.
- `retail_store_sales` is cited as the filled first-MVP example only; the generic contract
  templates, ADR, integration doc, and skill carry none of its specifics (FR-012, SC-004).
- Parity tolerance and whether dimension row counts are asserted (beyond the fact) are
  recorded as Deferred decisions with stated defaults, not [NEEDS CLARIFICATION] blockers.
