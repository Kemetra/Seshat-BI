# Implementation Plan: 085-antipattern-parity (B1)

**Branch**: `085-antipattern-parity` | **Spec**: `spec.md` | **Clarify**: `clarify.md`
**Status**: Draft (stops at ratify ledger; NOT approved, NOT implemented)

## Approach

A single static `@register`ed rule that reads the two committed QA docs, extracts
their thirteen anti-patterns with TWO format-specific extractors, and fails
fail-closed on any count / number->name / normalized-name divergence. No synonym
map (clarify C1: align-first). Stdlib-only, `ctx.tracked_files` only, never
executes, never writes, no numeric score.

## Constitution / hard-principle check

| Principle | How honored |
|---|---|
| Never-execute / static-first (VIII, B1/B3) | stdlib `re` over `ctx.tracked_files` text; no fs walk, no DB, no subprocess |
| No numeric score (hard rule #9) | categorical Findings only |
| No self-grant / no gate move (V) | rule REPORTS drift; never edits a doc, never writes approvals[] |
| No resolving a human judgment call (V) | the canonical-side alignment is an OWNER prose edit; rule only enforces equality after |
| Observed-not-declared severity (ratified 044) | severity emitted per branch at the Finding site, not declared on @register |
| ADD not REPLACE (VII) | new module + new fixtures; touches no existing rule |
| Determinism/portability (IX) | set/tuple compares; UTF-8 no BOM; MAX_PATH-safe package-relative paths |

## Components

1. **`src/retail/rules/antipattern_parity.py`** -- the rule module.
   - `_extract_headings(text) -> list[(int,str)]`: parse `### N. Title` lines from
     visual-qa.md. Returns [] on the table format (format-specific, FR-004).
   - `_extract_table(text) -> list[(int,str)]`: parse `| N | Name | ... |` rows
     (skip header/separator) from dashboard-qa.md. Returns [] on the heading
     format.
   - `_normalize(name) -> str`: case-fold + whitespace-collapse ONLY (FR-007).
   - `check(ctx) -> Iterable[Finding]`: read both docs from `ctx.tracked_files`;
     own-list count check (FR-005); count compare; number->name compare (C3);
     normalized-name membership compare (FR-006); emit fail-closed ERRORs (FR-008).
   - `@register(RULE_ID, "visual-qa <-> dashboard-qa anti-pattern parity")`.
     RULE_ID assigned by `retail scaffold` (candidate AP1; human confirms at
     ratify, clarify C4).
2. **Wiring** (per adversarial review HIGH): `retail scaffold <ID>` WRITES the stub
   module, the test stub, and the EXPECTED_RULE_IDS edit in
   `tests/unit/test_rules_wiring.py`. It PRINTS (apply by hand) the
   `src/retail/rules/__init__.py` import edit (the ONLY step that makes @register
   fire -- no autodiscovery), the `docs/glossary.md` rules-table row, and the two
   golden-record regen commands (manifest + severity-posture). A post-wiring test
   MUST confirm the id is in `all_rules()`, not just EXPECTED_RULE_IDS.
3. **Rule-count lockstep**: bump `docs/quality/rule-count-claims.yaml` + the
   "Currently N rules" anchor in `docs/glossary.md` in the SAME commit
   (registry 52 -> 53); `tests/unit/test_rule_count_claims.py` stays green.
4. **`tests/unit/test_antipattern_parity.py`** + `tests/fixtures/antipattern_parity/`
   good/bad corpus.

## Path targets (single source of truth)

- `VISUAL_QA_REL = "docs/powerbi/visual-qa.md"`
- `DASHBOARD_QA_REL = ".claude/skills/powerbi-dashboard-design/workflows/dashboard-qa.md"`

## Test strategy (fail-closed, mirrors test_design_*.py)

- Fixtures: aligned pair (pass); count-mismatch (ERROR); dropped-entry (ERROR);
  renamed-entry (ERROR); reordered number->name (ERROR); malformed own-list
  (ERROR before compare); heading-extractor-over-table -> [] and
  table-extractor-over-heading -> [] (format-specificity, FR-004/SC-003).
- Mutation-verified: each ERROR case is RED before the rule, GREEN after; deleting
  an assert makes a bad fixture pass (proves the assert bites).
- Exact locator + severity + count asserted per Finding.

## Sequencing (single PR, no parallelism -- one new rule = one registry-count serialization point)

Waves are trivial here (one rule): scaffold -> write check() -> fixtures/tests ->
count lockstep -> local gate -> PR. See tasks.md.

## Risks

- **Extractor half-match** -> the format-specificity tests (returns [] on the
  other format) are the guard; they are P2 acceptance scenarios.
- **Pre-alignment RED** -> SC-001 notes the rule correctly fails on the current
  unaligned docs; the owner alignment edit (C1 owner seam) precedes a green land.
  The PR must either (a) include the owner-approved visual-qa.md alignment edit or
  (b) land the rule as xfail/skip pending the edit -- a ratify-ledger decision,
  NOT made here.
- **Rule-count merge clash** -> only this one rule in flight; no other rule PR may
  land between scaffold and merge without re-syncing the count.

## Out of scope

A third carrier doc; auto-fixing either doc; any Power BI execution; a numeric
score; moving any readiness stage.
