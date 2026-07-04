# Tasks: 085-antipattern-parity (B1)

Dependency-ordered. `[P]` = parallelizable with siblings. Each task cites the
FR/SC it satisfies. STOPS at ratify; no task here is "merge" or "ratify".

## Phase 0 -- Owner seam (BLOCKS a green landing; confirmed at ratify)

- [ ] **T000 [OWNER SEAM]** Owner confirms clarify C1 (align-first vs synonym map)
  and, if align-first, edits `docs/powerbi/visual-qa.md` so its thirteen
  anti-pattern names EXACTLY match `dashboard-qa.md`'s canonical names (the known
  deltas: #1 "a page"->"one page"; #5 "Slicers dominating the page"->"Slicers
  taking too much space"; sweep all 13). Agent MUST NOT make this edit
  unprompted -- it is human-authored prose (Principle V). _Satisfies: C1, FR-010._

## Phase 1 -- Wire the rule (scaffold WRITES 3 files; the rest is manual -- see adversarial review HIGH)

- [ ] **T101** Run `retail scaffold AP1` (or the id the owner confirms). This
  WRITES the stub module (`src/retail/rules/rule_ap1.py`), the test stub
  (`tests/unit/test_rule_ap1.py`), and the EXPECTED_RULE_IDS edit in
  `tests/unit/test_rules_wiring.py`. It PRINTS (does NOT write) the `__init__.py`
  import edit, the glossary rules-table row, and the two golden-record regen
  commands. Capture all printed output. _Satisfies: FR-001, FR-009(b)._
- [ ] **T101a** OPTIONAL rename: if keeping the plan's `antipattern_parity.py`
  name over scaffold's mechanical `rule_ap1.py`, rename module + test now (scaffold
  refuses to overwrite, so a rename is a deliberate step). Otherwise accept
  `rule_ap1.py`. _Reconciles plan Component 1/4 naming._
- [ ] **T101b [CRITICAL WIRING]** Apply the printed `import_all` edit: add the new
  module to the import tuple AND `__all__` in `src/retail/rules/__init__.py`. This
  is the ONLY step that makes `@register` fire (no autodiscovery). WITHOUT it the
  rule is a silent no-op and the gate is a false green. _Satisfies: FR-009(a)._
- [ ] **T101c** Assert the wiring actually fired: a test confirming the new id is
  in `all_rules()` (not merely in EXPECTED_RULE_IDS). _Satisfies: FR-009 (the
  "all_rules() MUST contain the new id" clause)._
- [ ] **T102** Apply the printed glossary rules-table row; regenerate the two golden
  records (manifest + severity-posture) via the printed commands; bump
  `docs/quality/rule-count-claims.yaml` + the "Currently N rules" anchor in
  `docs/glossary.md` (52 -> 53) in the same change. _Satisfies: FR-009(c,d,e),
  SC-005._

## Phase 2 -- The two extractors (TDD: tests first)

- [ ] **T201 [P]** Write `_extract_headings(text)` for the `### N. Title` format
  (visual-qa.md). _Satisfies: FR-002._
- [ ] **T202 [P]** Write `_extract_table(text)` for the `| N | Name | ... |` format
  (dashboard-qa.md); skip header + separator rows. _Satisfies: FR-003._
- [ ] **T203** Format-specificity tests: heading-extractor over the table doc -> [];
  table-extractor over the heading doc -> []; each over its own doc -> exactly 13.
  _Satisfies: FR-004, SC-003 (P2 acceptance 1-2)._

## Phase 3 -- The compare + Findings

- [ ] **T301** `_normalize(name)` = case-fold + whitespace-collapse ONLY (no map).
  _Satisfies: FR-007._
- [ ] **T302** `check(ctx)`: own-list count guard (each doc == 13 else ERROR before
  compare). _Satisfies: FR-005, edge "malformed own-list"._
- [ ] **T303** `check(ctx)`: count compare + number->name compare (reorder = ERROR)
  + normalized-name membership compare; one fail-closed ERROR per divergence naming
  number + both raw strings + both locators. _Satisfies: FR-006, FR-008, C3._
- [ ] **T304** `@register(RULE_ID, title)`; severity emitted per branch at the
  Finding site (ratified 044), never declared on the decorator. _Satisfies:
  FR-001, C2._
- [ ] **T305** Assert NO numeric score anywhere in the module/output.
  _Satisfies: FR-011, SC-004._

## Phase 4 -- Adversarial fixture corpus + fail-closed tests

- [ ] **T401 [P]** `tests/fixtures/antipattern_parity/{good,bad}/*`: aligned (pass);
  count-mismatch; dropped-entry; renamed-entry; reordered; malformed-own-list.
  _Satisfies: FR-012._
- [ ] **T402** `tests/unit/test_antipattern_parity.py`: run the rule over each
  fixture; assert exact locator + severity + count per Finding; mutation-verify
  each bad case is RED without the rule and each assert bites. _Satisfies: FR-012,
  SC-002._

## Phase 5 -- Local gate (mandatory before PR)

- [ ] **T501** `ruff format --check`, `ruff check`, `pytest -m unit`, then
  `retail check` + `retail kit-lint` green (accounting for the T000 owner seam:
  either the alignment edit is in, or the parity test is xfail/skip pending it --
  a ratify decision). _Satisfies: SC-001, SC-005._
- [ ] **T502** Confirm the wiring meta-gate (`tests/unit/test_wiring_meta_gate.py`)
  + the rule-count test (`tests/unit/test_rule_count_claims.py`) pass at 53, AND
  `all_rules()` contains the new id (T101c). _Satisfies: SC-005._

## STOP -- ratify ledger

The chain stops here. Ratification (owner confirms C1 + C4, authorizes T000, and
signs the spec) is a human edit the workflow is structurally forbidden to make
(Principle V). See `ratify-ledger.md`.
