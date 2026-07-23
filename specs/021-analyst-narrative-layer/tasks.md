# Tasks: analyst-narrative layer -- decision-driven design on top of the correctness gates

**Spec**: `specs/021-analyst-narrative-layer/spec.md` | **Plan**: `plan.md` | **Issue**: #452

**Created**: 2026-07-23

## Format: `[ID] [P?] [Story] Description`

- `[P]` = parallelizable with neighbors in the same phase.
- `[USn]` = which spec user story the task serves; `[SETUP]`/`[POLISH]` otherwise.

## Path Conventions

- Knowledge pack source of truth: `skills/bi-analyst-knowledge/`.
- Dev-repo skill: `.claude/skills/dashboard-design/SKILL.md`.
- Checker: `src/seshat/narrative_check.py`, CLI wiring per house pattern
  (`src/seshat/cli/`), tests in `tests/unit/`.
- Client-workspace artifact (documented, not created here):
  `mappings/<table>/narrative-brief.md`.

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 [SETUP] Create `skills/bi-analyst-knowledge/INDEX.md` skeleton:
      purpose line, route list (8 cards + derivation route + story order +
      2 examples), and the pack-level stop rules -- no metric meaning here
      (contracts + `retail-kpi-knowledge` own meaning), no invented numbers,
      unanswerable question -> [GAP] (FR-001). GENERALITY RULE: every card
      and route is domain-neutral; domain flavor enters ONLY via domain
      knowledge packs and the client's own contracts/profile at runtime --
      domain instances live in the worked examples, never in a card or
      route (Principle VII).
- [ ] T002 [SETUP] Freeze the narrative-brief schema in
      `skills/bi-analyst-knowledge/derivation-route.md`: machine-readable
      front section (table id, contract citations, ranked questions each
      carrying a framing-card id, story order, [GAP] list) + human-first body.
      This schema is the single contract Phases B and C both consume.

## Phase 2: Foundational (Blocking Prerequisites)

- [ ] T003 [US1] Author the derivation route body: inputs bounded to exactly
      two committed artifacts (approved metric contracts, source-profile);
      ranked-question procedure; the grounded-only rule (a question may cite
      only measures/dims/facts those artifacts contain); [GAP] entry format
      (question + missing source fact + unlocking feed) (FR-003).
- [ ] T004 [US1] Author `skills/bi-analyst-knowledge/story-order.md`:
      overview -> what changed -> why/where -> action, carrying the five
      decision-driven elements (priority, thresholds, signals, driver
      relationships, action cues); single-page zone variant.

## Phase 3: User Story 1 - Author a narrative brief from approved contracts (P1)

- [ ] T005 [P] [US1] Author framing cards 1-4 (trend-anomaly,
      period-variance, contribution-mix, concentration). Each card: question
      shape -> required inputs (contract kinds + dims) -> visual guidance ->
      statistical guardrail -> so-what template.
- [ ] T006 [P] [US1] Author framing cards 5-8 (rate-decomposition,
      segment-behavior, benchmark-threshold, signal-vs-noise). Card 8 is the
      guardrails home: control bands as labeled DISPLAY DERIVATIONS of
      approved measures, seasonality-aware comparison, minimum-sample caveat
      for rates, correlation-vs-causation caution; regression/forecasting/
      significance testing explicitly out of scope (FR-002a).
- [ ] T007 [P] [US1] Author `example-c086-retail.md`: sanitize the ex-2
      analyst redesign (generic divisions, no client numbers, no PII, no
      hosts) showing the full decision -> framing -> visual -> so-what chain
      including at least one [GAP] entry (Principles VII, IX).
- [ ] T008 [P] [US1] Author `example-weekly-business-review.md`: generic
      retail WBR example (variance vs prior-year, ABC concentration,
      threshold callouts) grounded in the research anchors cited in the spec.

## Phase 4: User Story 2 - Design guidance is narrative-gated and three-way bound (P1)

- [ ] T009 [US2] In `.claude/skills/dashboard-design/SKILL.md`, add the
      narrative precondition to the STOP-unless list: a committed
      `mappings/<table>/narrative-brief.md` conforming to the T002 schema
      MUST exist before any layout/visual guidance is authored; absence is a
      named blocker, not a warning (FR-004).
- [ ] T010 [US2] In the same skill, upgrade the binding map to three-way
      (visual -> contract -> decision-question): orphan in either direction is
      a defect; headline (KPI-card class) visuals MUST name a comparison
      framing from the catalog -- a bare total is a defect (FR-005, FR-006).
- [ ] T011 [US2] Mirror the same route language in the marketplace
      `powerbi-workflows` skill source (locate via the distribution pipeline;
      keep wording identical to avoid drift), and add `bi-analyst-knowledge`
      to the skill's load-for-meaning routing list.

## Phase 5: User Story 3 - Read-only narrative check (P2)

- [ ] T012 [US3] Write failing tests first in
      `tests/unit/test_narrative_check.py` with three fixture classes:
      (a) clean brief+guidance -> no findings, exit 0, output states
      "evidence, not approval"; (b) mutated fixtures -> exactly the named
      findings (orphan visual, bare-total headline, missing question on a
      page, undeclared story order, [GAP] rendered as a visual), non-zero
      exit; (c) malformed/missing brief -> fail-closed parse error naming the
      problem, never "classified nothing" with exit 0 (FR-007, FR-008,
      FR-009).
- [ ] T013 [US3] Implement `src/seshat/narrative_check.py`: parse the T002
      front section + design-guidance binding map; emit categorical findings
      with named blockers; no score, no approval verb, stdlib only.
- [ ] T014 [US3] Wire the CLI verb (`seshat narrative-check --table <table>
      [--report DIR] --format {text,json}`) following the house pattern in
      `src/seshat/cli/`; document exit meanings in the verb help; register in
      the command surface the same way the other helpers are.

## Phase 6: Polish & Cross-Cutting

- [ ] T015 [P] [POLISH] Propagate the pack through the existing pipeline:
      `distribution/bundle-templates/shared/skills/`, `integrations/
      claude-code/seshat-bi/knowledge/`, `integrations/codex/`, and the
      `distribution/public-knowledge-allowlist.yaml` entry; add the pack to
      whatever copy-parity check guards the other packs.
- [ ] T016 [P] [POLISH] Sanitization + secrets scan over every new file
      (no C086 client numbers outside the sanitized example, no PII, no DSN,
      no absolute paths) -- Principles VII and IX (FR-010).
- [ ] T017 [POLISH] Verify each spec Success Criterion: SC-001/SC-002 by
      walking the worked example end to end, SC-003 against the T012
      fixtures, SC-004 by tracing the #452 four sub-gaps to their shipped
      countermeasures. Record the walk in the PR/commit body.
- [ ] T018 [POLISH] CHANGELOG entry + close-the-loop comment on #452
      linking spec/plan/tasks and the shipped artifacts.

## Dependencies

- T002 blocks T009-T014 (schema is the shared contract).
- Phase A (T001-T008) is independently shippable (US1 alone = viable MVP).
- T012 precedes T013/T014 (tests first).
- #454's `pbir_validate_bindings` (in progress) composes with, and is NOT a
  dependency of, T012-T014.
