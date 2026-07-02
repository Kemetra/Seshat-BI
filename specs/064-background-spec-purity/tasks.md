# Tasks: Background-Spec Forbidden-Dynamic-Content Assertion Rule

**Input**: Design documents from `specs/064-background-spec-purity/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/rule-contract.md, quickstart.md

**Tests**: Included -- the spec's user stories are defined in test terms and the
project is a governance-rule codebase where TDD (RED->GREEN) is the norm.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 / US2 / US3, or SETUP / WIRING / POLISH

## GATING NOTE (Principle V -- read before Phase WIRING)

The filled-spec FILE-DISCOVERY CONVENTION (the suffix that marks a committed
filled background spec, recommended default `*.background.yaml`) is an OPEN
owner-convention ruling (spec ## Clarifications). Phases SETUP/US1/US2/US3 build
the generic seam against a single convention constant and can proceed on the
recommended default. Phase WIRING FREEZES the golden records (including the
convention encoded into the live discovery) and MUST NOT be committed until the
owner's convention ruling is recorded; wiring an owner-unratified convention would
encode a Principle-V judgment the workflow is forbidden to make. Until then the
rule is inert (C4) and the build stays green.

The boolean VOCABULARY (7 forbidden + 9 qa keys) is frozen verbatim from
`templates/background-spec.yaml` (Clarifications Q2) and is NOT gated -- it is the
template's own declared contract.

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 [SETUP] Confirm the live registry state on this branch: import
  `retail.rules`, call `registry.all_rules()`, and reconcile against
  `EXPECTED_RULE_IDS` in `tests/unit/test_rules_wiring.py`. Record the TRUE set and
  confirm the intended fresh, non-colliding, design-lint-namespaced rule id (the
  natural next in the DL family) is free. Do not trust a count claim; reconcile
  against the real set.
- [ ] T002 [SETUP] Create the fixture directory under the test-fixture exemption
  path (mirroring the DL1/design_theme fixtures convention) for the
  background-purity fixtures. ASCII, UTF-8 no BOM.

---

## Phase 2: Foundational (Blocking Prerequisites)

- [ ] T003 [SETUP] Author the frozen boolean vocabulary + the discovery-convention
  seam in a single place (named module-level constants): the 7
  `forbidden_dynamic_content` keys and 9 `qa_checklist` items DERIVED verbatim from
  `templates/background-spec.yaml`, and the discovery suffix constant (recommended
  `*.background.yaml`, marked pending the owner ruling). Include a code comment
  citing the template and marking the convention literal as pending. No
  tenant/example/brand literal (Principle VII).

---

## Phase 3: User Story 1 -- A filled spec that declares a defect fails (Priority: P1)

**Goal**: A true forbidden key (or an un-reasoned false qa item) in a committed
filled spec is an ERROR finding with a precise locator, and the check fails closed.

- [ ] T004 [P] [US1] Add fixture: a filled spec with exactly one
  `forbidden_dynamic_content` key set `true` (under the exemption path).
- [ ] T005 [P] [US1] Add fixture: a filled spec with two distinct forbidden keys
  set `true`.
- [ ] T006 [P] [US1] Add fixture: a filled spec with a `qa_checklist` item `false`
  and NO recorded reason.
- [ ] T007 [US1] Write failing unit tests in `tests/unit/test_design_background.py`
  for contract rows C5 (one ERROR + `file#/pointer` locator + fail closed), C6 (two
  findings, no masking), C10 (bare false qa -> one finding). RED.
- [ ] T008 [US1] Implement `src/retail/rules/design_background.py`: a
  `@register`-decorated function that discovers filled specs generically, LAZY
  `import yaml` inside the function (B1/B3), parses each spec, asserts the declared
  boolean contract, and emits one `Severity.ERROR` Finding per violation with a
  `file#/pointer` locator. Make C5, C6, C10 GREEN.

**Checkpoint**: US1 is an independently demonstrable MVP -- a defect-declaring
filled spec fails the rule with a precise finding.

---

## Phase 4: User Story 2 -- A clean, compliant filled spec passes (Priority: P1)

**Goal**: A compliant filled spec (all forbidden false, all qa true-or-reason)
produces zero findings; a reasoned warning is accepted.

- [ ] T009 [P] [US2] Add fixture: a fully compliant filled spec (all forbidden
  keys `false`, all qa items `true`).
- [ ] T010 [P] [US2] Add fixture: a filled spec with a `qa_checklist` item `false`
  WITH a recorded reason.
- [ ] T011 [US2] Write failing unit tests for contract rows C7 (all-false forbidden
  -> zero), C11 (false-with-reason qa -> zero), and SC-005 pairing (same item
  false+reason passes, false+no-reason fails). RED where behavior is missing.
- [ ] T012 [US2] Refine `design_background.py` so a real `false` forbidden key
  passes, a `true` qa item passes, and a `false` qa item WITH a present non-empty
  non-placeholder reason passes (reason PRESENCE only, never adequacy -- Principle
  V). Make C7, C11 GREEN.

**Checkpoint**: US1 + US2 together define the correctness boundary (no false
positives on a compliant/reasoned spec, no false negatives on a declared defect).

---

## Phase 5: User Story 3 -- Generic, inert-until-filled, self-registering (Priority: P2)

**Goal**: The rule scans any committed filled spec generically, exempts the
template + fixtures, is inert on an empty corpus, handles edge cases, and is
verifiably present in governance records.

- [ ] T013 [P] [US3] Add fixture: a discovered filled spec still carrying the
  `<true|false>` placeholder in a forbidden key (C8) and one with a non-boolean
  value (C9).
- [ ] T014 [P] [US3] Add fixture: a malformed (invalid YAML) filled spec (C12); and
  a second differently-named filled spec to prove generic discovery (C1).
- [ ] T015 [US3] Write failing unit tests for C1 (generic discovery, two files
  both scanned), C2 (template exempt), C3 (fixture-exemption path excluded from
  live scan), C4 (no filled spec -> zero, no error), C8 (placeholder -> finding),
  C9 (non-boolean -> finding), C12 (malformed -> finding, no crash), C13 (frozen
  vocabulary, no tenant literal). RED.
- [ ] T016 [US3] Implement generic discovery (suffix constant, template +
  `is_test_path` exemption), inert-on-empty behavior, placeholder/non-boolean
  detection, and malformed-YAML handling (emit a finding, do not raise; FR-009).
  Make C1-C4, C8, C9, C12, C13 GREEN.

**Checkpoint**: All contract rows C1-C13 GREEN; the rule is generic, inert-safe,
and robust.

---

## Phase 6: Wiring (Golden-Record Freeze -- GATED on owner convention ruling)

**BLOCKED until the Principle-V owner ruling on the filled-spec file-discovery
convention (the suffix) is recorded in spec ## Clarifications.**

- [ ] T017 [WIRING] Add `design_background` to the side-effecting import tuple AND
  `__all__` in `src/retail/rules/__init__.py`.
- [ ] T018 [WIRING] Add the fresh rule id to `EXPECTED_RULE_IDS` in
  `tests/unit/test_rules_wiring.py`.
- [ ] T019 [WIRING] Regenerate `docs/rules/rules-manifest.json` via the existing
  `retail manifest` command (adds the new id + title); update the manifest snapshot
  golden in `tests/unit/test_rules_manifest_snapshot.py`.
- [ ] T020 [WIRING] Regenerate `docs/rules/severity-posture.json` (the new id's
  OBSERVED severity; do not hand-declare a governed table -- ratified 044); update
  the severity-posture golden in `tests/unit/test_severity_posture.py`.

---

## Phase 7: Polish & Gate

- [ ] T021 [POLISH] Run `pytest -m unit` -- all C1-C13 tests plus the wiring,
  manifest-snapshot, and severity-posture tests pass.
- [ ] T022 [POLISH] Run `retail check` (full governance gate) -- green; the new
  rule produces zero findings on the live corpus (inert, no filled spec) and the
  wiring/golden-record tests pass.
- [ ] T023 [POLISH] Confirm all authored files are ASCII / UTF-8-no-BOM / short
  paths (Principle IX); confirm the module scope stays stdlib-only (yaml imported
  in-function, B1/B3); confirm no tenant/example literal appears in the rule
  (Principle VII).

---

## Dependencies & Ordering

- Setup (T001-T002) before everything.
- Foundational vocabulary + convention seam (T003) before US1 implementation
  (T008).
- Within each story: fixtures + failing tests before implementation (TDD).
- US1 (P1) and US2 (P1) are the MVP; US3 (P2) hardens.
- Phase 6 (WIRING) is GATED on the owner convention ruling and comes after all
  rule behavior is GREEN.
- Phase 7 (gate) is last.

## Parallel opportunities

- Fixture-authoring tasks marked [P] (T004-T006, T009-T010, T013-T014) touch
  distinct files and can be authored together.
- The two P1 stories can be built in sequence or interleaved; both must be GREEN
  before wiring.

## MVP scope

US1 + US2 (both P1) = the minimum viable rule: catches a declared defect, never
flags a compliant/reasoned filled spec. US3 + wiring make it generic, inert-safe,
and governed.
