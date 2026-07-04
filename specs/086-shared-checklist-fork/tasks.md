# Tasks: 086-shared-checklist-fork (I3)

Dependency-ordered. `[P]` = parallelizable. Each cites its FR/SC. STOPS at ratify.

## Phase 0 -- Owner seams (BLOCK a green landing; confirmed at ratify)

- [ ] **T000a [OWNER SEAM]** Owner rules the existing fork
  `aggregation-grain-checklist.md` (bi-bigdata vs bi-python) as `shared` or
  `distinct` (clarify C1). Agent recommends `distinct` as a hypothesis; agent MUST
  NOT set it. _Satisfies: C1._
- [ ] **T000b [OWNER SEAM]** Owner authors `docs/quality/shared-spine.yaml` with the
  C1 ruling (agent may commit the documented SHAPE/scaffold on request only; owner
  fills the `shared`/`distinct` values). _Satisfies: C2, FR-003._

## Phase 1 -- Wire the rule (scaffold WRITES 3 files; __init__ import is manual)

- [ ] **T101** Run `retail scaffold SF1` (or owner-confirmed id). WRITES stub
  module `src/retail/rules/rule_sf1.py`, test stub, EXPECTED_RULE_IDS edit; PRINTS
  the `__init__.py` import edit, glossary row, golden regen cmds. _FR-001, FR-011(b)._
- [ ] **T101b [CRITICAL WIRING]** Apply the printed import edit to
  `src/retail/rules/__init__.py` (import tuple + `__all__`) -- the ONLY step that
  makes `@register` fire (no autodiscovery). _FR-011(a)._
- [ ] **T101c** Test asserting the new id is in `all_rules()` (not just
  EXPECTED_RULE_IDS). _FR-011._
- [ ] **T102** Apply the glossary row; regen manifest + severity-posture; bump
  `docs/quality/rule-count-claims.yaml` + the "Currently N rules" glossary anchor
  (52 -> 53) in the same change. _FR-011(c,d,e), SC-005._

## Phase 2 -- Collect + spine load (TDD)

- [ ] **T201 [P]** `_collect(ctx)`: glob `skills/**/checklists/*.md` from
  tracked_files, exempt test paths, group by basename with per-copy sha256.
  _FR-002, FR-009._
- [ ] **T202 [P]** `_load_spine(ctx)`: read `docs/quality/shared-spine.yaml`; ERROR
  on missing/unparseable (FR-008); ERROR on a value not in {`shared`,`distinct`}
  naming the basename + bad value (FR-008b). _FR-003, FR-008, FR-008b._

## Phase 3 -- The reconcile + Findings

- [ ] **T301** Undeclared collision -> fail-closed ERROR naming basename + all
  paths. _FR-004 (US1)._
- [ ] **T302** `shared` + non-identical copies -> ERROR naming basename + divergent
  paths/hashes; `shared` + identical -> pass. _FR-005 (US2)._
- [ ] **T303** `distinct` + differing -> pass; `distinct` + identical -> WARNING
  (moot). _FR-006 (US3)._
- [ ] **T304** Stale spine entry (declared basename no longer collides / absent) ->
  WARNING. _FR-007._
- [ ] **T305** `@register(RULE_ID, title)`; severity per branch at emit site (044);
  no numeric score anywhere. _FR-001, FR-010, C3._

## Phase 4 -- Adversarial fixtures + fail-closed tests

- [ ] **T401 [P]** `tests/fixtures/shared_fork/*`: undeclared; shared-identical;
  shared-drift; distinct-differ; distinct-identical; stale-entry; missing-manifest;
  bad-enum-value (FR-008b); unique-basename; 3-copy shared. _FR-012._
- [ ] **T402** `tests/unit/test_rule_sf1.py`: run over each fixture; assert exact
  locator + severity + count; mutation-verify each case. Fixtures exempt from the
  real glob (FR-009) so they don't self-trip. Include a test asserting the module
  source contains no write against `SPINE_REL` (SC-004 measurable). _FR-012,
  SC-002/003/004._

## Phase 5 -- Local gate

- [ ] **T501** `ruff format --check`, `ruff check`, `pytest -m unit`, then
  `retail check` + `retail kit-lint` green -- REQUIRES the owner spine (T000b) to
  exist, else the missing-manifest ERROR fires by design. _SC-001._
- [ ] **T502** Confirm `test_wiring_meta_gate.py` + `test_rule_count_claims.py`
  pass at 53 and `all_rules()` contains the new id (T101c). _SC-005._

## STOP -- ratify ledger

Ratification (owner confirms C1/C2/C4, authors the spine, signs the spec) is a
human edit the workflow is forbidden to make (Principle V). See
`specs/086-shared-checklist-fork/ratify-ledger.md`.
Note: unlike B1, I3's owner seam is HEAVIER -- it needs an authored contract
(the spine + the fork ruling), not just a prose alignment edit.
