# Implementation Plan: analyst-narrative layer -- decision-driven design on top of the correctness gates

**Branch**: `main` (session convention) | **Spec**: `specs/021-analyst-narrative-layer/spec.md` | **Issue**: #452

**Created**: 2026-07-23

## Summary

Add the judgment layer F011 lacks: a `bi-analyst-knowledge` pack (eight framing
cards with statistical guardrails, a decision-question derivation route, a
story-order rule, two worked examples), a mandatory narrative-brief step in the
`dashboard-design` skill (mirrored in the marketplace `powerbi-workflows`
skill) with a three-way binding map (visual -> contract -> decision-question),
and a read-only fail-closed narrative checker in the installed helper family.
Correctness gates from F009/F010/F011 are untouched; one new gate is added
(no layout before a committed narrative brief).

## Technical Context

- **Knowledge pack source of truth**: `skills/bi-analyst-knowledge/` at repo
  root (same layout as `skills/retail-kpi-knowledge/`: `INDEX.md` + routed
  cards). Propagation follows the existing pipeline: copies under
  `distribution/bundle-templates/shared/skills/`, integration mirrors under
  `integrations/claude-code/seshat-bi/knowledge/` and `integrations/codex/`,
  plus an entry in `distribution/public-knowledge-allowlist.yaml`. Reuse
  whatever sync script/check the repo already runs for the other packs -- do
  NOT hand-maintain divergent copies (Principle II).
- **Skill route**: `.claude/skills/dashboard-design/SKILL.md` (dev-repo skill,
  F011) gains the narrative-brief precondition and the three-way binding map;
  the marketplace-facing `powerbi-workflows` skill source gets the same route
  language. Pure agent-procedure text -- no codegen (same posture as 012).
- **Checker**: new module `src/seshat/narrative_check.py` + CLI wiring in
  `src/seshat/cli/` (house pattern: `dashboard_planner.py`,
  `cli/commands/gap_detector.py`). Verb name proposal:
  `seshat narrative-check --table <table> [--report DIR] --format {text,json}`
  reading `mappings/<table>/narrative-brief.md` + committed design guidance.
  Read-only, categorical output, named blockers, no score. Exit meanings
  follow the helper family: 0 = completed (findings are derived evidence),
  non-zero = findings / usage / refusal, and malformed input FAILS CLOSED with
  a parse error naming the problem (FR-008; the #453 lesson).
- **Composition**: the checker validates the NARRATIVE dimension only; binding
  resolution against the semantic model is #454's `pbir_validate_bindings`
  (in progress on `fix/454-pbir-validate-bindings`); page-intent parsing
  fixes are #453. No overlap, no dependency for v1.
- **Brief schema**: markdown with a small machine-readable front section
  (table id, contract citations, ranked questions each with framing-card id,
  story order, [GAP] list) so the checker parses structure without NLP.
  Exact front-matter keys are decided in T00x and documented in the pack.

## Constitution Check

- **I (agent-first, gate-enforced)**: new artifacts are gate inputs; the
  named-human design review remains the only approval. PASS.
- **II (depend, never fork)**: extends existing skill/helper/knowledge shapes;
  no new frameworks. PASS.
- **V (agent stops at judgment calls)**: unanswerable questions become [GAP]
  entries and stop; question ranking is owner-reviewable text. PASS.
- **VI (defaults then deviations)**: framing cards are defaults; deviations
  are recorded in the brief. PASS.
- **VII (C086 is an example, not the schema)**: worked examples sanitized;
  routes stay generic. PASS.
- **VIII (static-first)**: checker is static file analysis; no DB, no
  Desktop. PASS.
- **IX (secrets/reproducibility)**: briefs carry no DSN/PII/absolute paths;
  checker redacts nothing because nothing secret is ever input. PASS.

## Project Structure

### Documentation (this feature)

```
specs/021-analyst-narrative-layer/
  spec.md        # committed (ebab0a7)
  plan.md        # this file
  tasks.md       # phase-ordered tasks
```

### Source (repository root)

```
skills/bi-analyst-knowledge/
  INDEX.md                     # routes + stop rules
  framing-trend-anomaly.md     # card 1 (with guardrail: band basis, history floor)
  framing-period-variance.md   # card 2 (YoY/PoP/YTD-pace; seasonality-aware)
  framing-contribution-mix.md  # card 3
  framing-concentration.md     # card 4 (Pareto/ABC)
  framing-rate-decomposition.md# card 5 (total -> driver rates; domain-neutral)
  framing-segment-behavior.md  # card 6
  framing-benchmark-threshold.md # card 7
  framing-signal-vs-noise.md   # card 8 (statistical guardrails home card)
  derivation-route.md          # contracts + source-profile -> ranked questions
  story-order.md               # overview -> change -> why/where -> action
  example-c086-retail.md       # sanitized worked example (from #452 review)
  example-weekly-business-review.md  # generic retail WBR example
.claude/skills/dashboard-design/SKILL.md   # + narrative precondition, 3-way map
<powerbi-workflows skill source>           # mirrored route language
src/seshat/narrative_check.py              # checker module
src/seshat/cli/...                         # verb wiring (house pattern)
tests/unit/test_narrative_check.py         # fixtures: clean / findings / malformed
distribution/, integrations/               # pack propagation (existing pipeline)
```

## Phasing

- **Phase A (P1, docs-only, independently shippable)**: knowledge pack
  (INDEX + 8 cards + routes + 2 examples). Delivers User Story 1 by itself --
  an agent can author a correct brief with no code change.
- **Phase B (P1, docs-only)**: skill route changes (dashboard-design +
  powerbi-workflows mirror). Delivers User Story 2; depends on Phase A naming
  (card ids, brief schema).
- **Phase C (P2, code)**: narrative checker + tests + CLI wiring. Delivers
  User Story 3; depends on the brief schema frozen in Phase A.
- **Phase D (polish)**: propagation (distribution/integrations/allowlist),
  sanitization scan, SC verification, CHANGELOG.

## Complexity Tracking

- No new dependencies. Checker is stdlib file parsing (markdown front section),
  matching the static-first posture.
- The only cross-cutting risk is DRIFT between the three copies of the pack
  (skills/, distribution/, integrations/) -- mitigated by reusing the existing
  sync mechanism and adding the pack to whatever parity check guards the other
  packs today.
- Brief schema is deliberately minimal (front section only) to avoid inventing
  a new document format; the body stays human-first markdown.
