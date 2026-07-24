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

- [x] T001 [SETUP] Create `skills/bi-analyst-knowledge/INDEX.md` skeleton:
      purpose line, route list (8 cards + derivation route + story order +
      2 examples), and the pack-level stop rules -- no metric meaning here
      (contracts + `retail-kpi-knowledge` own meaning), no invented numbers,
      unanswerable question -> [GAP] (FR-001). GENERALITY RULE: every card
      and route is domain-neutral; domain flavor enters ONLY via domain
      knowledge packs and the client's own contracts/profile at runtime --
      domain instances live in the worked examples, never in a card or
      route (Principle VII).
- [x] T002 [SETUP] Freeze the narrative-brief schema in
      `skills/bi-analyst-knowledge/derivation-route.md`: machine-readable
      front section (table id, contract citations, ranked questions each
      carrying a framing-card id, story order, [GAP] list) + human-first body.
      This schema is the single contract Phases B and C both consume.

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T003 [US1] Author the derivation route body: inputs bounded to exactly
      two committed artifacts (approved metric contracts, source-profile);
      ranked-question procedure; the grounded-only rule (a question may cite
      only measures/dims/facts those artifacts contain); [GAP] entry format
      (question + missing source fact + unlocking feed) (FR-003).
- [x] T004 [US1] Author `skills/bi-analyst-knowledge/story-order.md`:
      overview -> what changed -> why/where -> action, carrying the five
      decision-driven elements (priority, thresholds, signals, driver
      relationships, action cues); single-page zone variant.

## Phase 3: User Story 1 - Author a narrative brief from approved contracts (P1)

- [x] T005 [P] [US1] Author framing cards 1-4 (trend-anomaly,
      period-variance, contribution-mix, concentration). Each card: question
      shape -> required inputs (contract kinds + dims) -> visual guidance ->
      statistical guardrail -> so-what template.
- [x] T006 [P] [US1] Author framing cards 5-8 (rate-decomposition,
      segment-behavior, benchmark-threshold, signal-vs-noise). Card 8 is the
      guardrails home: control bands as labeled DISPLAY DERIVATIONS of
      approved measures, seasonality-aware comparison, minimum-sample caveat
      for rates, correlation-vs-causation caution; regression/forecasting/
      significance testing explicitly out of scope (FR-002a).
- [x] T007 [P] [US1] Author `example-specialty-retail.md` (shipped name; was
      drafted as `example-c086-retail.md`, renamed in the generality pass):
      sanitize the ex-2
      analyst redesign (generic divisions, no client numbers, no PII, no
      hosts) showing the full decision -> framing -> visual -> so-what chain
      including at least one [GAP] entry (Principles VII, IX).
- [x] T008 [P] [US1] Author `example-weekly-business-review.md`: generic
      retail WBR example (variance vs prior-year, ABC concentration,
      threshold callouts) grounded in the research anchors cited in the spec.

## Phase 4: User Story 2 - Design guidance is narrative-gated and three-way bound (P1)

- [x] T009 [US2] In `.claude/skills/dashboard-design/SKILL.md`, added the
      narrative precondition to the STOP-unless list (precondition 5 + the "no
      layout before narrative" gate section): a committed
      `mappings/<table>/narrative-brief.md` conforming to the T002 schema MUST
      exist before any layout/visual guidance; absence is the named blocker
      `narrative_brief_missing`, not a warning (FR-004). Blocking-reasons and
      "must NOT do" lists updated to match.
- [x] T010 [US2] Upgraded the binding map to three-way (visual -> contract ->
      decision-question) in the skill AND made it CHECKABLE: the shipped
      `narrative-check` verb gains an opt-in `--binding-map` design-stage mode
      (`src/seshat/narrative_check.py::check_binding_map`) reading a
      `seshat.binding-map/v1` front section -- orphan in either direction
      (`orphan_visual`, FR-005), page-serves-no-decision, and a headline visual
      answering no overview question (`bare_total_headline_visual`, FR-006, via
      the brief's already-enforced overview-comparison rule). `decision_questions`
      is LIST-valued (a visual may answer >1 decision -- the real worked
      example's basket-value card answers Q1+Q5). Fail-closed on missing/
      malformed map or absent referenced brief (opt-in so US1 brief-stage callers
      are not broken). Template + `example-specialty-retail.md` teach the shape;
      capabilities.yaml entry updated (oracle 45 pass).
- [x] T011 [US2] Mirrored the narrative gate + three-way route in the marketplace
      `powerbi-workflows` skill SOURCE
      (`distribution/bundle-templates/shared/skills/powerbi-workflows/SKILL.md`),
      added `bi-analyst-knowledge` to its load-for-meaning routing list, and
      regenerated the `integrations/{claude-code,codex}` mirrors via
      `scripts/export_agent_bundles.py` (parity: "generated bundles match
      reviewed inputs").

## Phase 5: User Story 3 - Read-only narrative check (P2)

- [x] T012 [US3] Write failing tests first in
      `tests/unit/test_narrative_check.py` (+ `_cli.py`) with three fixture
      classes: (a) clean brief -> no findings, exit 0, output states
      "evidence, not approval"; (b) mutated fixtures -> exactly the named
      findings (bare-total headline, undeclared/mismatched story order, [GAP]
      framed as a question, ungrounded cite, stale contract revision, invalid
      stage, empty callout, missing guardrail basis), non-zero exit; (c)
      malformed/missing brief -> fail-closed parse error naming the problem,
      never "classified nothing" with exit 0 (FR-007, FR-008, FR-009).
      SCOPE (Phase C): the two BINDING-MAP fixtures (orphan visual, missing
      question on a page) shipped as visible `@pytest.mark.skip` -- they needed
      the Phase-B three-way map (T010). Phase B replaced both skips with real
      tests (orphan visual, page-missing-question, headline-visual, multi-question
      visual, fail-closed cases) built from the committed teaching file, plus a
      guard test asserting the real retail_store_sales map still needs migration.
- [x] T013 [US3] Implement `src/seshat/narrative_check.py`: parse the T002
      front section; enforce the derivation-route.md checker rules (grounded
      cites, fresh contract revisions, story-order coverage/stage-match/
      non-empty overview, headline comparison, guardrail basis, GAP-not-framed);
      emit categorical findings with named blockers; no score, no approval verb,
      stdlib + PyYAML + the shared hardened read-only git probe. The
      design-guidance BINDING-MAP check is a Phase-B addition (T010), documented
      as out of scope here (see phase-c-verification.md).
- [x] T014 [US3] Wire the CLI verb (`seshat narrative-check --table <table>
      [--report DIR] --format {text,json}`) following the house pattern in
      `src/seshat/cli/`; document exit meanings in the verb help; register in
      the command surface the same way the other helpers are (parser fn + call
      + lazy dispatch + capability-manifest entry -- the manifest oracle caught
      the missing entry).

## Phase 6: Polish & Cross-Cutting

- [x] T015 [P] [POLISH] Propagate the pack through the existing pipeline via
      `scripts/export_agent_bundles.py` (full pack ->
      `integrations/{claude-code,codex}/seshat-bi/knowledge/bi-analyst-knowledge/`,
      thin redirect stub at `skills/<pack>/SKILL.md`, matching the peer packs),
      plus the `distribution/public-knowledge-allowlist.yaml` entries
      (kb-156..169 + wrapper), `public-command-surface.yaml`, and the shared
      router. Guarded by the existing copy-parity + bundle contract tests
      (43 pass; exporter idempotent; 14/14 knowledge copies byte-identical).
- [x] T016 [P] [POLISH] Sanitization + secrets scan over every new file
      (no client numbers outside the sanitized example, no PII, no DSN,
      no absolute paths) -- Principles VII and IX (FR-010). CLEAN across all
      five categories; the only c086 hit is a deviation note documenting the
      T007 rename.
- [x] T017 [POLISH] Verify each spec Success Criterion: SC-001/SC-002 by
      walking the worked example end to end, SC-003 against the T012
      fixtures, SC-004 by tracing the #452 four sub-gaps to their shipped
      countermeasures. Recorded in `phase-c-verification.md`. (SC-002 walk
      confirmed the full worked-example brief passes the checker;
      flow-style YAML verified.)
- [x] T018 [POLISH] CHANGELOG entry (under [Unreleased] Added) done. The
      close-the-loop comment on #452 is a GitHub action deferred to PR time
      (this branch is not yet pushed; owner drives the push/PR).

## Dependencies

- T002 blocks T009-T014 (schema is the shared contract).
- Phase A (T001-T008) is independently shippable (US1 alone = viable MVP).
- T012 precedes T013/T014 (tests first).
- #454's `pbir_validate_bindings` (in progress) composes with, and is NOT a
  dependency of, T012-T014.
