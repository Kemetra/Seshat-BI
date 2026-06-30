# Tasks: Publish-pack completeness gate (PP1)

**Feature**: `049-publish-pack-completeness-gate`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Contract**: [contracts/rule-contract.md](./contracts/rule-contract.md)

TDD is the repo default (RED -> GREEN -> refactor). Test tasks precede the
implementation they cover. All paths are repo-relative.

Scope guard (YAGNI / first step): add ONE registered static rule that reuses G6's
placeholder mechanism (no second parser), an explicit required-section-set constant,
the wiring-id update, the regenerated manifest, and a firing test. Scan only
`mappings/<table>/handoff/bi-handoff-pack.md` instances. Modify NO committed handoff
pack, template, or readiness file. Add NO new dependency, executor, or severity
tier. The registry id (`PP1`), the final required-section-set membership, and the
severity posture are recommendations pending human ratification (spec ##
Clarifications) -- use the working id `PP1` and leave a note; do NOT invent a
readiness stage; do NOT decompose the four MANDATORY caveats individually.

## Phase 1: Setup

- [ ] T001 Confirm the reusable placeholder mechanism in `src/retail/rules/g6.py`
  (`_PLACEHOLDER_RE = re.compile(r"<[^>]+>")`) and decide the reuse seam per
  research.md (recommended: lift the one-line pattern into a tiny shared helper both
  `g6.py` and `publish_pack.py` import; acceptable fallback: import the pattern
  directly). Implement the chosen seam with G6's behavior unchanged, and record the
  working rule id `PP1` (pending ratification per spec ## Clarifications) in a
  top-of-module comment.

## Phase 2: Foundational (blocking prerequisites)

- [ ] T002 Read `tests/unit/test_rules_wiring.py` to confirm `EXPECTED_RULE_IDS` is
  a frozenset whose length drives the snapshot count (no literal baseline), and read
  `docs/rules/rules-manifest.json` + the `manifest` subcommand in `src/retail/cli.py`
  (`_run_manifest`) to confirm the `retail manifest --repo .` regeneration path
  before adding an id. Confirm the generic template structure in
  `templates/handoff/bi-handoff-pack.md` (the six required-section-index rows a-f and
  the structured "Resolved?" cell) that the required-section-set constant keys off.

## Phase 3: User Story 1 -- An incomplete publish pack fails the gate (P1)

**Goal**: A required section left as `<placeholder>` or recorded as `GAP` produces a
Finding; a fully filled pack does not.

**Independent test**: Invoke the rule against synthetic generic pack source strings
(filled vs placeholder/GAP) and assert Findings / no Findings per contract C1/C2/C4.

- [ ] T003 [US1] Add `tests/unit/test_publish_pack.py` with RED tests asserting
  contract C1 (a required section whose resolution value is still a `<placeholder>`
  -> one Finding naming the pack + section) and C4 (a fully filled generic pack -> no
  Finding). Use synthetic generic pack strings + a fake `RuleContext` (generic
  labels only; no domain artifact).
- [ ] T004 [US1] Extend `tests/unit/test_publish_pack.py` with RED tests for C2 (a
  required section's structured "Resolved?" cell = `GAP` -> one Finding), C2b (the
  word "gap" in narrative prose, not the resolution cell -> no Finding), and C7 (an
  unreadable selected pack -> a fail-loud Finding).
- [ ] T005 [US1] Create `src/retail/rules/publish_pack.py`: reuse the placeholder
  mechanism from T001 (no fork), define the explicit required-section-set constant
  (the six generic index rows a-f -- recommended membership, comment that final
  membership is confirmed at ratify), implement the `@register("PP1", ...)`ed checker
  that selects only tracked `mappings/*/handoff/bi-handoff-pack.md` (excluding the
  template and `is_test_path()` fixtures), reads each pack's text, flags each missing
  or unfilled (placeholder / GAP-in-resolution-cell) required section as a
  `Severity.ERROR` Finding, and converts a read error into a fail-loud Finding. Make
  T003/T004 GREEN.
- [ ] T006 [US1] Run `pytest -m unit tests/unit/test_publish_pack.py` and
  `retail check`; confirm tests pass and `retail check` reports zero new Findings on
  the current tree (the one existing pack
  `mappings/retail_store_sales/handoff/bi-handoff-pack.md` is filled -> the rule is
  green today, fires only on an incomplete pack -- contract C14).

## Phase 4: User Story 2 -- A pack missing a required section is flagged (P1)

**Goal**: A pack omitting a required-section heading is flagged.

**Independent test**: A generic pack source omitting one required section -> a
missing-section Finding; a pack with all sections -> none.

- [ ] T007 [US2] Add a RED test to `tests/unit/test_publish_pack.py` for C3 (a
  generic pack omitting one required-section heading/index row -> one Finding naming
  the missing section; a pack with all required sections -> no missing-section
  Finding). Make it GREEN by extending the T005 checker if presence-detection is not
  already covered.

## Phase 5: User Story 3 -- Genuinely wired, not just listed (P1)

**Goal**: The id is in the registry, the regenerated manifest, and the wiring
expected set, AND the rule is exercised firing (close the wiring-latent-gap).

**Independent test**: The snapshot/wiring test passes with the new id; a direct test
observes the rule fire on a known-bad fixture.

- [ ] T008 [US3] Add the working id `PP1` to `EXPECTED_RULE_IDS` in
  `tests/unit/test_rules_wiring.py` (with a one-line comment), keeping the set the
  single source of truth; do NOT introduce any literal baseline count.
- [ ] T009 [US3] Regenerate `docs/rules/rules-manifest.json` via
  `retail manifest --repo .` so it contains the new id; verify it is the only
  intended diff.
- [ ] T010 [US3] Run `pytest -m unit tests/unit/test_rules_wiring.py`; confirm the
  live registry id set equals `EXPECTED_RULE_IDS`, `len(all_rules()) ==
  len(EXPECTED_RULE_IDS)`, and the rule submodule is auto-discovered by `pkgutil`.
- [ ] T011 [US3] Confirm `tests/unit/test_publish_pack.py` includes at least one
  test that invokes the rule directly on a known-bad fixture and asserts a non-empty
  Finding set (the rule FIRES, not merely registers -- FR-011 / SC-005, contract C9);
  add it if not already covered by T003.

## Phase 6: User Story 4 -- Approval slot checked present, never granted (P1)

**Goal**: The publish-approval check is presence-and-non-placeholder only; never
inspect/validate/populate the sign-off (Principle V).

**Independent test**: A filled approval slot -> no approval-slot Finding without the
rule reading its contents; an unfilled approval slot -> flagged like any other
required section.

- [ ] T012 [US4] Add tests to `tests/unit/test_publish_pack.py` for C8: an unfilled
  approval section (`<placeholder>` / GAP) -> a Finding (flagged as a required
  section), AND a filled approval section -> no approval-slot Finding. Assert (test
  or inspection note) that the rule code path for the approval section reads only
  presence-and-non-placeholder and never the owner/date/legitimacy, and writes no
  approval (FR-006 / SC-008).

## Phase 7: Polish & Cross-Cutting

- [ ] T013 [P] Add a test/inspection note for C10/C6: the rule, its
  required-section-set constant, and every fixture contain only generic labels and
  the placeholder/GAP convention -- no table / column / KPI / PII; and an empty
  tracked-file set (no packs) -> no Finding (silent pass, FR-009).
- [ ] T014 [P] Run `ruff` and the full `pytest -m unit` suite; confirm ASCII /
  UTF-8 no BOM in all new files and that no new third-party dependency, network
  call, or DB access was introduced (SC-007, contract C12).
- [ ] T015 [P] Confirm the spec's Open-for-human items (the readiness-stage +
  roadmap-provenance assignment, and the publish-safety boundary confirmation) and
  the two reversible advisor recommendations (required-section set, severity = ERROR)
  remain recorded and unanswered/unconfirmed; do NOT self-assign a readiness stage,
  a ratified id, or self-grant any approval.

## Dependencies

- T001, T002 (Setup/Foundational) before all story phases.
- US1 (T003-T006) is the MVP; US2 (T007) and US4 (T012) depend on the rule existing
  (T005). US3 (T008-T011) depends on the rule existing (T005).
- T003/T004 (RED) before T005 (GREEN). T008/T009 before T010.
- Polish (T013-T015) last.

## Parallel opportunities

- T013, T014, T015 are independent ([P]).
- Within US1, T003 and T004 edit the same test file -> run sequentially.

## MVP scope

User Story 1 (T001-T006) alone delivers the protective value: an incomplete
committed handoff pack fails the gate. US2 (missing section), US3 (wiring integrity),
and US4 (the Principle-V approval boundary) harden completeness, wiring, and safety.
