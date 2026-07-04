# Feature Specification: Anti-Pattern Parity Rule (visual-qa <-> dashboard-qa thirteen-in-lockstep)

**Feature Branch**: `085-antipattern-parity`

**Created**: 2026-07-04

**Status**: Ratified (Ahmed Shaaban, 2026-07-04) -- C1=align-first, id=AP1, same-PR landing

**Input**: User description: "Anti-Pattern Parity Rule (workflow <-> prose thirteen-in-lockstep)" -- idea B1 from docs/roadmap/idea-backlog.md (CONSIDER). Two committed docs each carry the SAME thirteen visual-QA anti-patterns but in DIFFERENT structural formats and with DIVERGENT wording; nothing enforces that they stay in lockstep, so an edit to one can silently drift from the other.

## Context (grounded facts, verified 2026-07-04)

- **The prose home**: `docs/powerbi/visual-qa.md` lists the thirteen anti-patterns
  as `### N. Title` headings (e.g. `### 1. Too many visuals on a page`).
- **The check catalog**: `.claude/skills/powerbi-dashboard-design/workflows/dashboard-qa.md`
  lists the same thirteen as a **pipe table** with columns `# | Anti-pattern |
  Rule / principle it violates | Severity` (e.g. `| 1 | Too many visuals on one
  page | ... | warning |`).
- **Both docs already declare the lockstep intent in prose** ("carry the SAME
  anti-pattern list ... change both"; "Keep the two in sync -- same thirteen
  anti-patterns, same names") -- but that intent is enforced today only by agent
  judgment, so it can silently drift.
- **Verified divergence exists**: numbering aligns 1-13, but wording differs --
  e.g. #1 "Too many visuals on **a** page" (prose) vs "on **one** page" (table);
  #5 "Slicers **dominating the page**" vs "Slicers **taking too much space**".
- **Reviewer-flagged fragility**: a single text extractor is a no-op on one of
  the two formats (the prose uses `###` headings, the catalog uses a pipe table),
  so naive `rough_shape` matching fails. Two format-specific extractors are
  required. dashboard-qa.md is the FULLER doc (it carries the Severity column and
  rule references), so it is the recommended canonical side.
- B1 is git-verified OPEN as of 2026-07-04 (no shipping commit; `045-output-parity`
  is an unrelated feature).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detect count/name drift between the two anti-pattern lists (Priority: P1)

As the `retail check` governance gate (run by an agent or in CI), I extract the
thirteen anti-patterns from BOTH committed docs and fail loudly, naming the
offending entry, whenever the two lists disagree on count or on a normalized
name -- so an edit to one doc that forgets the other cannot merge silently.

**Why this priority**: This is the whole value of B1. The lockstep is asserted in
prose in both docs but enforced by nothing; the P1 rule turns that stated
invariant into a machine-checked one. It is the MVP -- shippable and valuable on
its own even without stories 2-3.

**Independent Test**: Add a fixture pair where one list has 12 entries and the
other 13 (or a renamed entry); assert the rule emits exactly one ERROR Finding
naming the missing/renamed anti-pattern and its doc, and exits non-zero.

**Acceptance Scenarios**:

1. **Given** both docs list the same thirteen normalized names, **When** the rule
   runs, **Then** it emits no Findings and the gate stays green.
2. **Given** `dashboard-qa.md` drops anti-pattern #7, **When** the rule runs,
   **Then** it emits one ERROR naming "#7 / No visual hierarchy" as present in
   `visual-qa.md` but absent from `dashboard-qa.md`.
3. **Given** `visual-qa.md` renames #6 to a name that does not normalize-equal the
   catalog's #6, **When** the rule runs, **Then** it emits one ERROR naming the
   two divergent strings and both doc locators.
4. **Given** the two docs disagree on total count, **When** the rule runs,
   **Then** it emits an ERROR stating both counts before any per-entry compare.

### User Story 2 - Parse each doc with its own format-specific extractor (Priority: P2)

As the rule author, I use TWO extractors -- one for the `### N. Title` heading
format (visual-qa.md) and one for the `| # | Anti-pattern | ... |` pipe-table
format (dashboard-qa.md) -- because a single extractor silently no-ops on the
format it was not written for, producing a false green.

**Why this priority**: This is the correctness spine that makes Story 1 sound.
The reviewer explicitly flagged that a single `rough_shape` extractor is fragile;
without two extractors the rule can pass while actually parsing zero entries from
one doc.

**Independent Test**: Point each extractor at the OTHER doc's format and assert it
returns zero entries (proving it is format-specific), then point each at its own
format and assert it returns exactly thirteen.

**Acceptance Scenarios**:

1. **Given** the heading extractor is run over the pipe-table doc, **When** it
   parses, **Then** it returns zero entries (does not silently half-match).
2. **Given** each extractor is run over its intended doc, **When** it parses,
   **Then** it returns exactly thirteen `(number, name)` entries in order.
3. **Given** an extractor returns a count != 13 from its own doc, **When** the
   rule runs, **Then** it emits an ERROR (a doc's own list is malformed) rather
   than proceeding to a false compare.

### User Story 3 - Owner aligns the names once; the rule then enforces exact equality (Priority: P3)

As the gate, after the owner has aligned `visual-qa.md`'s thirteen names to
`dashboard-qa.md`'s (the canonical side), I compare anti-pattern NAMES by exact
equality under a minimal deterministic normalization (case-fold +
whitespace-collapse ONLY -- NO synonym map), so the lockstep is true and there is
no unbounded "benign variant" list to rot.

**Why this priority**: See clarification C1. A parity rule that ships a committed
list of "these non-matching names are fine" is philosophically muddy and creates
the map-rot failure mode this spec's own Edge Cases flagged. The clean path is:
the owner makes the one prose edit to `visual-qa.md` (already the recommended B1
owner action), then the rule enforces exact normalized equality. This is an
[OWNER SEAM]: the doc edit precedes a green landing and is confirmed at ratify.

**Independent Test**: After the owner-aligned docs are in the tree, assert zero
Findings; then reintroduce ANY wording divergence and assert it fails.

**Acceptance Scenarios**:

1. **Given** the owner has aligned the names, **When** the rule runs over the
   current docs, **Then** zero Findings.
2. **Given** any wording divergence between the two docs, **When** the rule runs,
   **Then** it emits an ERROR naming the divergent pair and both locators.
3. **Given** the docs are NOT yet aligned, **When** the rule runs, **Then** it
   fails loudly (fail-closed) rather than being suppressed by a tolerance list.

### Edge Cases

- **A doc's own list is internally malformed** (e.g. 14 headings, or a table row
  with no number): emit an ERROR that the doc's own extraction failed, before any
  cross-doc compare -- never a silent skip.
- **Numbering reordered but names intact**: the rule compares by normalized name
  membership AND by number; a reordering that keeps the set is a WARNING-or-ERROR
  per the ratified severity posture (see Assumptions) -- decided at clarify.
- **A third doc later claims to carry the list**: out of scope; the rule is
  hard-scoped to exactly the two named docs (extending it is a future spec).
- **The synonym map rots** (a mapped entry is later removed from a doc): the map
  entry becomes dead; a mapped pair that no longer resolves must itself surface,
  not pass silently.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The rule MUST be a single `@register`ed static rule in
  `src/retail/rules/` (candidate id in the `AP`/`B`-family, assigned by
  `retail scaffold` at build time), stdlib-only, reading only committed files via
  `ctx.tracked_files` -- never the live filesystem, never a DB, never executing.
- **FR-002**: The rule MUST extract the thirteen anti-patterns from
  `docs/powerbi/visual-qa.md` using a HEADING extractor (`### N. Title`).
- **FR-003**: The rule MUST extract the thirteen anti-patterns from
  `.claude/skills/powerbi-dashboard-design/workflows/dashboard-qa.md` using a
  PIPE-TABLE extractor (`| # | Anti-pattern | ... |`).
- **FR-004**: Each extractor MUST be format-specific: run over the other doc's
  format it MUST return zero entries, never a partial/false match.
- **FR-005**: The rule MUST emit an ERROR Finding if EITHER doc's own extraction
  yields a count other than thirteen (a malformed own-list), before cross-compare.
- **FR-006**: The rule MUST compare the two lists by (a) count, (b) number->name
  mapping, and (c) normalized name membership, and emit one ERROR Finding per
  divergence, each naming the entry number, both raw strings, and both doc
  locators. A number->name mismatch (reorder) is an ERROR (clarification C3).
- **FR-007**: Name comparison MUST use a MINIMAL deterministic normalization --
  case-fold + whitespace-collapse ONLY. There is NO synonym map (clarification
  C1: align-first). The owner aligns `visual-qa.md`'s names to `dashboard-qa.md`'s
  BEFORE the rule lands green; thereafter exact normalized equality holds.
- **FR-008**: A divergence MUST be reported as a fail-closed ERROR, never
  suppressed by a tolerance/variant list (there is none).
- **FR-009**: The rule MUST be wired across ALL required places so `@register`
  actually fires. NOTE (per adversarial review): `retail scaffold` WRITES only the
  stub module, the test stub, and the EXPECTED_RULE_IDS edit; it PRINTS (for manual
  application) the `src/retail/rules/__init__.py` import edit, the glossary
  rules-table row, and the two golden-record regen commands (manifest +
  severity-posture). Per `src/retail/rules/__init__.py`, the explicit import is the
  ONLY thing that makes a new rule discoverable (no autodiscovery). Therefore the
  rule MUST: (a) add its module to the `__init__.py` import tuple + `__all__`,
  (b) be a member of EXPECTED_RULE_IDS, (c) have a glossary rules-table row,
  (d) be in `rules-manifest.json`, (e) be in the severity-posture record; and bump
  the rule-count claim (`docs/quality/rule-count-claims.yaml` + the glossary
  "Currently N rules" anchor) in the same commit. The wiring meta-gate
  (`tests/unit/test_wiring_meta_gate.py`) and the rule-count test
  (`tests/unit/test_rule_count_claims.py`) MUST stay green, AND `all_rules()` MUST
  actually contain the new id post-wiring (proving the import fired).
- **FR-010**: The rule MUST NOT edit, rewrite, or "fix" either doc. It reports
  drift; aligning the docs is a human edit (the canonical-side recommendation is
  advisory prose in the spec, applied by the owner, not by the rule).
- **FR-011**: The rule MUST NOT emit any numeric confidence/health score
  (roadmap hard rule #9); output is categorical Findings only.
- **FR-012**: The rule MUST ship with an adversarial good/bad fixture corpus and a
  fail-closed test asserting exact locator + severity + count, mirroring
  `tests/unit/test_design_*.py`.
- **FR-013**: The own-list count guard (FR-005) hardcodes 13. If a real 14th
  anti-pattern is ever added to BOTH docs in lockstep, the guard's magic number
  MUST be updated in the same change (the rule enforces "thirteen-in-lockstep" by
  name). This brittleness is accepted and documented, not hidden (adversarial
  review MEDIUM): the guard's purpose is to catch a doc's OWN list becoming
  malformed, distinct from the cross-doc parity check.

### Key Entities *(include if feature involves data)*

- **AntiPattern**: a `(number, normalized_name, raw_name, doc, line_locator)`
  tuple extracted from one doc. No implementation detail beyond these fields.
- **ParityFinding**: a `Finding(rule_id, severity, message, locator)` naming a
  count mismatch, a malformed own-list, a number->name reorder, or a per-entry
  name divergence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After the owner aligns `visual-qa.md`'s names to `dashboard-qa.md`'s
  (clarification C1, an [OWNER SEAM] confirmed at ratify), the rule produces ZERO
  Findings and `retail check` stays green. NOTE: on the CURRENT unaligned tree the
  rule correctly fails on the known "a page"/"one page"-class deltas -- that is the
  expected pre-alignment state, not a defect.
- **SC-002**: Deleting or renaming any one anti-pattern in EITHER doc causes the
  rule to fail with exactly one ERROR naming the offending entry and both docs
  (mutation-verified in tests).
- **SC-003**: Each extractor returns exactly thirteen entries from its own doc and
  zero from the other doc's format (proving format-specificity).
- **SC-004**: The rule adds no numeric score anywhere, and edits neither doc
  (verified by test + review).
- **SC-005**: The wiring + rule-count lockstep stays green after the rule lands
  (`tests/unit/test_wiring_meta_gate.py` and `tests/unit/test_rule_count_claims.py`
  pass at 53) AND `all_rules()` contains the new id (proving the `__init__.py`
  import fired -- not merely EXPECTED_RULE_IDS membership).

## Assumptions

- **Canonical side (align-first, clarification C1)**: `dashboard-qa.md` (the fuller
  doc, carrying Severity + rule references) is the canonical source of names;
  `visual-qa.md` aligns to it via a one-time OWNER prose edit BEFORE the rule lands
  green. There is NO synonym map. The rule never rewrites either doc (Principle V;
  FR-010). This ordering (owner edit -> rule green) is an [OWNER SEAM] on the
  ratify ledger.
- **Severity of a divergence**: assumed ERROR (fail-closed), consistent with the
  other wiring/lockstep guards; the observed-not-declared severity model (ratified
  spec 044) is honored -- severity is emitted per branch, not declared on
  `@register`. Final severity posture confirmed at clarify.
- **Exactly two docs**: the rule is hard-scoped to the two named files; a third
  carrier is a future spec (YAGNI).
- **Reused mechanism**: `retail scaffold <ID>` does the five-place wiring;
  `@register(RULE_ID, title)` on `check(ctx) -> Iterable[Finding]` with
  `RuleContext`/`Finding` from `src/retail/core.py`; fixture pattern from
  `tests/unit/test_design_*.py`. Nothing new is invented at the mechanism layer.
- **Ratification pending**: this spec STOPS at a ratify ledger; it is DEFINED and
  CHECKED, never approved or implemented here. Ratification is a human seam
  (Principle V) the author is structurally forbidden to self-clear.
