# Tasks: Severity-Posture Regression Lock (golden severity table)

**Input**: Design documents from `specs/046-severity-posture-lock/`

**Prerequisites**: plan.md (required), spec.md (required for user stories + the
Principle-V clarifications). The grain and L3-coverage rulings have been RESOLVED
by the planning advisor under explicit human authorization (spec `## Clarifications`
-> "Advisor-resolved Principle-V calls"): grain = `rule_id -> sorted SET of
severity classes`; L3 surface IN as a named `L3:verdict_to_finding` section. T004
and T010 are therefore UNBLOCKED. Ratification (Status -> Ratified, session date)
remains a human-only act and is NOT a prerequisite for implementation tasks.

**Tests**: This feature IS a test (a golden-equality snapshot test) plus an
observation generator. The snapshot test is authored TEST-FIRST (fails closed
before the record is committed, passes after). No DB/network/Power BI/agent.

**Organization**: Tasks are grouped by user story (US1 = drift guard, US2 =
deterministic regeneration, US3 = new-rule coverage). The over-scope guard is
load-bearing: NO new `@register`, NO new `EXPECTED_RULE_ID`; the snapshot test is
test-only, NOT a `retail check` rule, and NO `@register` is added to `semantic.py`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included.

## Path Conventions

Single project. New code under `src/retail/severity_posture.py` and a generator
subcommand in `src/retail/cli.py`; new test `tests/unit/test_severity_posture.py`;
synthetic fixtures under `tests/fixtures/severity/` if needed. The generated
artifact is `docs/rules/severity-posture.json`. One `.gitattributes` line.

---

## Phase 0: Principle-V rulings -- RESOLVED (advisor-authorized)

**Purpose**: The record's grain and L3 coverage were REFUSED judgment calls in
spec `## Clarifications`. They have been resolved by the planning advisor under
explicit human authorization, so the key is fixed and T004/T010 are unblocked.

- [x] T000 [RESOLVED] The two Principle-V judgment calls are ruled (spec
  `## Clarifications` -> "Advisor-resolved Principle-V calls"): (a) record GRAIN
  = `rule_id -> sorted SET of severity classes` (option (a)); (b) the non-registry
  L3 governance surface (drift -> ERROR / escalate -> WARNING) is IN scope,
  recorded as a named `L3:verdict_to_finding` second section. Resolved by the
  planning advisor under human authorization; this is NOT ratification (Status
  stays Draft, the session date stays pending -- both human-only).
  [Principle V; FR-009; FR-010]

---

## Phase 1: Setup (confirm seams; read-only)

**Purpose**: Confirm the source-of-truth seams and the observation mechanism
before authoring.

- [ ] T001 Confirm `registry.all_rules()` returns `tuple[RegisteredRule, ...]`
  carrying `id`/`title` and NO severity field, by reading `src/retail/registry.py`
  + `src/retail/core.py` -- confirming the record must be OBSERVED, not read.
  (read-only) [FR-002]
- [ ] T002 Confirm severity is per-finding-branch by reading the multi-class rule
  in `src/retail/rules/sql.py` (S4b emits ERROR + WARNING) and the L3 surface
  `src/retail/semantic.py` (`verdict_to_finding`: drift->ERROR / escalate->
  WARNING). Confirms the grain cannot be a flat id->class map. (read-only)
  [FR-009 evidence]
- [ ] T003 Confirm the test-path exemption (`core.is_test_path`) and how
  file-scanning rules consume `RuleContext.tracked_files`, so planted fixtures can
  be made NON-exempt and actually fire each rule. (read-only) [FR-008, Edge Cases]

---

## Phase 2: Foundational (blocking prerequisite)

**Purpose**: Fix the record's grain (post-gate) and the deterministic
serialization contract that BOTH the generator and the snapshot test depend on.

- [ ] T004 Encode the resolved GRAIN (from T000: `rule_id -> sorted SET of
  severity classes`) as the record's key, and document the single deterministic
  ordering + serialization contract in a module docstring on
  `src/retail/severity_posture.py`: entries sorted by id; each entry's class set
  sorted by the severity string value; UTF-8 no-BOM, `\n` endings, single trailing
  newline, stable key order. (Principle IX) [FR-001, FR-005, FR-009] -- UNBLOCKED
  (T000 resolved).
- [ ] T005 Add `.gitattributes` entry: `docs/rules/severity-posture.json text
  eol=lf` so the committed bytes are stable across Windows
  (`core.autocrlf=true`) and Linux. [FR-005]

---

## Phase 3: User Story 1 -- Drift guard (Priority: P1)

**Goal**: A golden-equality snapshot test that fails closed when a rule's observed
severity posture diverges from the committed record. **Independent test**: change
a rule so a finding moves ERROR -> WARNING without regenerating -> test fails with
an actionable message naming the rule and the class delta; regenerate -> passes.

- [ ] T006 [US1] Implement the observation helper in
  `src/retail/severity_posture.py`: for each rule from a clean clear+reload of the
  registry, force it to fire over a minimal synthetic `RuleContext`/planted
  fixture and collect the `Severity` class(es) per the ruled grain. A rule that
  cannot be forced to fire gets an EXPLICIT no-finding marker entry. [FR-002,
  FR-008, FR-011]
- [ ] T007 [US1] Create synthetic, generic planted fixtures under
  `tests/fixtures/severity/` (only for rules that need a file/context to fire) --
  minimal, NON-exempt-path, and containing NO example-domain table/column/value.
  Because `is_test_path` exempts these from the live rules, add a fixture-
  genericity assertion in the lock test that scans the fixture FILES themselves
  for example-domain identifiers (the fixtures are not otherwise scanned).
  [FR-006, FR-008, SC-005, SC-007]
- [ ] T008 [US1] Author `tests/unit/test_severity_posture.py` (marked
  `@pytest.mark.unit`) TEST-FIRST, copying the proven clear+reload pattern from
  `test_rules_manifest_snapshot.py`: derive the live observed posture, read the
  committed `docs/rules/severity-posture.json` as UTF-8, parse, and assert the
  parsed data structures are equal (NOT raw text). The record does not exist yet
  -> fails closed (RED). [FR-003, FR-012]
- [ ] T009 [US1] Make the failure message actionable: on mismatch, report the
  affected rule + recorded-vs-observed class(es) (drifted/missing/stale) and
  instruct the developer to regenerate and commit the record in the same change.
  [FR-003, FR-004]
- [ ] T010 [US1] Observe the L3 surface (T000 ruled it IN): call
  `semantic.verdict_to_finding(name, locator, verdict)` over a `drift` verdict and
  an `escalate` verdict -- both constructed in-process as frozen
  `metric_drift.Verdict(status=..., detail=...)` values (NO YAML/DB/model/agent,
  so Principle VIII holds) -- and record the posture as a named section keyed
  `L3:verdict_to_finding -> [ERROR, WARNING]`. Add NO `@register` to `semantic.py`
  and NO new `EXPECTED_RULE_ID` (ADR-0007). [FR-010; ADR-0007] -- UNBLOCKED
  (T000 resolved).

---

## Phase 4: User Story 2 -- Deterministic regeneration (Priority: P2)

**Goal**: A one-action generator that writes the record deterministically from the
live observed posture. **Independent test**: run twice -> byte-identical; a
single-rule severity change -> diff confined to that rule's entry.

- [ ] T011 [US2] Add `build`/`serialize`/`render`/`write` functions to
  `src/retail/severity_posture.py` mirroring `manifest.py`: `build` returns the
  ordered observed-posture data, `serialize` writes UTF-8 no-BOM/`\n`/trailing
  newline, `write` targets `docs/rules/severity-posture.json`. Generated from live
  observation, never a hand-typed literal. [FR-001, FR-005]
- [ ] T012 [US2] Wire the generator behind a CLI subcommand in
  `src/retail/cli.py` (mirroring the `manifest` subcommand placement; clarify Q1).
  No `--check` mode (YAGNI). [FR-001]
- [ ] T013 [US2] Run the generator to PRODUCE the committed
  `docs/rules/severity-posture.json`; the snapshot test from Phase 3 now passes
  (GREEN). [US1 + US2 join here]
- [ ] T014 [US2] Add a determinism/idempotency unit assertion: generating twice
  yields byte-identical output (render == render). [SC-002, SC-003]

---

## Phase 5: User Story 3 -- New-rule coverage (Priority: P3)

**Goal**: A newly added registered rule cannot enter with an unrecorded severity.

- [ ] T015 [US3] Add a unit assertion that every registered rule has exactly one
  entry (or explicit no-finding marker) in the record's REGISTERED-RULES section --
  i.e. that section's covered-rule-id set equals the live registered-rule-id set,
  failing closed on a missing or stale rule. The named L3 section
  (`L3:verdict_to_finding`) is asserted SEPARATELY (it is not a registered rule),
  so it neither satisfies nor breaks the registered-set equality. [SC-006, FR-003]
- [ ] T016 [US3] Add a "no new gating rule" assertion mirroring the manifest
  sibling: the registered rule count is unchanged and no new `EXPECTED_RULE_ID`
  was introduced by this feature (test-only). [FR-007, SC-004]

---

## Phase 6: Verification

**Purpose**: Confirm the gate is unchanged and the feature is cross-platform
stable.

- [ ] T017 Run `retail check` -> exit code logic UNCHANGED and the registered rule
  count UNCHANGED (no new rule, no new `EXPECTED_RULE_ID`, no `@register` added to
  `semantic.py`). [SC-004, FR-007]
- [ ] T018 Run `pytest -m unit` -> the snapshot test passes on a clean checkout;
  confirm the multi-class rule (S4b) records BOTH ERROR and WARNING (not collapsed),
  the L3 section records `L3:verdict_to_finding -> [ERROR, WARNING]`, the fixture-
  genericity assertion passes (no example-domain identifier in any planted fixture
  file, SC-007), and there is no line-ending flakiness (data-comparison, not raw
  text). [SC-001, SC-007, FR-009, FR-010, FR-012]

---

## Dependencies

- **T000 is RESOLVED (advisor-authorized), so T004 and T010 are UNBLOCKED** -- the
  grain (`rule_id -> sorted SET of classes`) and L3-coverage (IN, named section)
  rulings are fixed. No human gate remains before implementation; only
  ratification (Status/date) is still human-only and is not an implementation
  dependency.
- Phase 2 (T004 grain + serialization contract) blocks Phases 3 and 4.
- Phase 3 (T008 snapshot test) is authored RED before Phase 4 produces the record
  (T013 turns it GREEN) -- the test-first ordering.
- T007 (fixtures) supports T006 (observation) and must land before T013.
- T015/T016 (US3) follow once the record exists.

## Out of Scope (YAGNI)

- No new `@register` rule; no new `EXPECTED_RULE_ID`; no change to `retail check`
  behavior or exit-code logic; no `@register` added to `semantic.py`.
- No numeric severity/health/readiness/confidence score.
- No `--check` CI-verify subcommand mode for the first step.
- No reordering/refactor of existing rules to ease observation.
- No DB/network/Power BI/agent integration; no dependency on F016 or F031-F033.
- No `@register` for L3 and no new `EXPECTED_RULE_ID` for the L3 entry (ADR-0007),
  even though L3 is now in scope as a record section.
- No setting of Status to Ratified and no filling of the session date -- those
  stay human-only even though the grain/L3-coverage judgment calls are
  advisor-resolved.
