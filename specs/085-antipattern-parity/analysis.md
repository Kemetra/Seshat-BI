# Analysis: 085-antipattern-parity (B1) -- read-only cross-artifact consistency

Ran after spec + clarify + plan + tasks. Checks: requirement coverage, internal
contradiction, principle compliance, terminology drift, C086 leak.

## Coverage matrix (every FR -> a task)

| FR | Covered by | OK |
|----|-----------|----|
| FR-001 register/stdlib/read-only | T101, T304 | yes |
| FR-002 heading extractor | T201 | yes |
| FR-003 table extractor | T202 | yes |
| FR-004 format-specificity | T203 | yes |
| FR-005 own-list count guard | T302 | yes |
| FR-006 count+number+name compare | T303 | yes |
| FR-007 normalize, no map | T301 | yes |
| FR-008 fail-closed, no tolerance | T303 | yes |
| FR-009 five-place wiring + count | T101, T102 | yes |
| FR-010 never edits a doc | (design constraint; T000 is owner, not rule) | yes |
| FR-011 no numeric score | T305 | yes |
| FR-012 adversarial fixtures | T401, T402 | yes |

Every SC maps to a task: SC-001->T501, SC-002->T402, SC-003->T203, SC-004->T305,
SC-005->T502. No orphan requirement; no task without a requirement.

## Contradiction check

- **RESOLVED (was the main finding)**: the synonym-map vs align-first
  contradiction the draft carried is resolved in clarify C1 (align-first, no map)
  and propagated to FR-007/FR-008, User Story 3, SC-001, Assumptions, Key Entities.
  No residual reference to a synonym map remains.
- No other FR pair conflicts.

## Principle compliance

- Never-execute / static-first: PASS (stdlib re over tracked_files).
- No numeric score (#9): PASS (FR-011/T305).
- No self-grant / no doc rewrite (V): PASS (FR-010; the alignment is an owner edit
  T000, explicitly NOT a rule action).
- Observed-not-declared severity (044): PASS (C2/T304 emit per branch).
- Determinism (IX): PASS (set/tuple compare, UTF-8 no BOM).

## Terminology / drift

- "thirteen anti-patterns" used consistently; both doc paths cited identically in
  spec + plan + tasks (single-source path constants in plan).
- Rule id left as candidate AP1 pending scaffold + owner confirm (C4) --
  consistent across artifacts, not hardcoded.

## C086 / worked-example leak

- No client data, no c086 reference. The two QA docs are generic governance prose.
  PASS.

## Open items (all owner-facing, carried to ratify)

- C1 align-first confirmation + the visual-qa.md prose alignment edit (T000).
- C4 concrete rule id.
- Pre-alignment landing posture (alignment edit in the same PR vs rule xfail/skip
  pending it) -- a ratify decision, flagged in plan Risks + T501.

**Initial verdict: CONSISTENT** (0 critical, 0 high) -- but this was INCOMPLETE.

## Adversarial review corrections (2026-07-04, code-reviewer skeptic)

An independent adversarial pass caught two HIGH defects this analyze missed:

- **[HIGH -> FIXED] "Five-place wiring" was wrong.** `scaffold.py` WRITES only 3
  files and PRINTS the `__init__.py` import edit for manual application; per
  `src/retail/rules/__init__.py` that explicit import is the ONLY thing that makes
  `@register` fire (no autodiscovery). No task added it -> the rule would land as a
  silent no-op (the exact failure this feature prevents). FIXED: FR-009 rewritten
  to enumerate the real places incl. `__init__.py`; tasks T101b (apply import) +
  T101c (assert id in `all_rules()`) added.
- **[HIGH -> FIXED] "IL1" was a fabricated citation.** The wiring meta-gate is
  `tests/unit/test_wiring_meta_gate.py` (E1); IL1 is the unrelated shipped-ideas
  ledger seam. SC2's test is `test_rule_count_claims.py`. FIXED across spec/plan/
  tasks.
- **[MEDIUM -> FIXED] Scaffold filenames** (`rule_ap1.py` vs `antipattern_parity.py`):
  T101a rename step added.
- **[MEDIUM -> DOCUMENTED] Hardcoded 13**: FR-013 added -- a coordinated 14th entry
  requires updating the magic number; accepted + documented, not hidden.
- **[LOW] `ratify-ledger.md`**: created at ratify (this stage).

Adversarial grounding checks all PASSED: both docs' 13-in-claimed-format verified;
wording deltas real; count 52 confirmed; no existing duplicate rule (B1 genuinely
unshipped); RuleContext/Finding/register imports confirmed; two-extractor design
justified; hard-principle clean.

**Final verdict: CONSISTENT after fixes.** 0 remaining critical/high. The design
is sound, honestly scoped, hard-principle-clean, and now executes as written.
Remaining opens are legitimate owner seams (C1/C4 + pre-alignment posture).
