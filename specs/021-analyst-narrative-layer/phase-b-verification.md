# Phase B verification record (spec 021, T017)

Phase B = the narrative GATE on the design skills + the three-way binding map
(US2, T009-T011). Phase A (knowledge pack) shipped in #460; Phase C (the
read-only `narrative-check` verb) + Phase D (propagation) shipped in #468. Phase
B was deliberately deferred there (owner-gated: it ARMS enforced behavior on two
already-shipped skills). This records the T017 Success-Criteria walk for Phase B.

## What shipped in Phase B

- **T009 -- the narrative gate.** `.claude/skills/dashboard-design/SKILL.md` now
  STOPs unless a committed `mappings/<table>/narrative-brief.md` (frozen
  `seshat.narrative-brief/v1`) exists before any layout/visual guidance
  (precondition 5 + the "no layout before narrative" section). Absence is the
  named blocker `narrative_brief_missing`, not a warning (FR-004). The
  blocking-reasons and "must NOT do" lists were updated to match.
- **T010 -- the three-way binding map, made checkable.** The skill's binding map
  is upgraded from two-way (visual -> contract) to THREE-way (visual -> contract
  -> decision-question), and the shipped `narrative-check` verb gains an opt-in
  `--binding-map` design-stage mode (`narrative_check.py::check_binding_map`):
  - `orphan_visual` (FR-005, orphan in EITHER direction): a visual whose
    `contract` is missing or not a declared approved contract, OR whose
    `decision_questions` is empty or names an id the brief does not declare. (An
    adversarial review caught that an early cut checked only the question leg and
    left `contract` decorative -- a visual with no/bogus contract passed; the
    contract leg is now grounded against the brief's declared contracts, reusing
    `_grounded_measure_ids`.)
  - `unanswered_question` (FR-005, the other direction): a brief decision-question
    that no visual answers -- a ranked owner decision the design does not inform.
  - `page_missing_question`: a declared page carrying no question-bearing visual.
  - `bare_total_headline_visual` (FR-006): a `headline: true` (KPI-card class)
    visual answering no `stage: overview` question. The brief already forces every
    overview question to name a `comparison` (never "none"), so this single
    structural link enforces "the headline carries a comparison" without the map
    restating the rule.
  - `decision_questions` is LIST-valued: one visual may answer more than one owner
    decision (the real worked example's basket-value card answers Q1 AND Q5 --
    the spec edge case "two questions answered by the same visual, both listed").
  - Fail-closed (FR-008) on a missing / unreadable / schema-invalid map or an
    absent referenced brief -- the SAME posture as the brief check. Opt-in via
    `--binding-map` so a US1 brief-stage caller (a brief exists, no map yet) is
    NOT broken by map-absence fail-close.
- **T011 -- the marketplace mirror.** The narrative gate + three-way route language
  was mirrored in the `powerbi-workflows` skill SOURCE
  (`distribution/bundle-templates/shared/skills/powerbi-workflows/SKILL.md`),
  `bi-analyst-knowledge` was added to its load-for-meaning routing list, and the
  `integrations/{claude-code,codex}` mirrors were regenerated via the exporter
  (parity clean).

## The circular-fixture guard (why Option B, and how it stays honest)

The map format (`seshat.binding-map/v1`) is NEW, so no committed artifact used it.
Per the circular-fixture lesson (a fixture that invents the shape the code expects
passes green while the code is broken on real data), Phase B:

- authors the three-way worked example as a TAUGHT instance in
  `bi-analyst-knowledge/example-specialty-retail.md` (exactly how Phase C treats
  that file as *the* worked example), and
- builds the library test `test_taught_binding_map_example_parses_and_passes` by
  reading that committed teaching file VERBATIM (the pack's own example must pass
  its own checker), and
- keeps `test_real_worked_example_map_still_needs_phase_b_migration`: the ONE real
  committed map (`mappings/retail_store_sales/design/visual-contract-binding-map.md`)
  is still the F011 two-way MARKDOWN pipe-table with no
  `seshat.binding-map/v1` front section, so the checker fails closed
  (`no_front_section`) on it. This makes "DOA on reality" VISIBLE instead of
  hidden behind fixture-only green.

**OWNER FLAG (Option A follow-up, owner-gated):** migrating the signed-off
`retail_store_sales` binding map into the new format + authoring its real
`narrative-brief.md` (and fixing the Phase-C revision-guard path coupling,
`contracts/` vs the real `metrics/`, which surfaces the moment a real brief is
authored) satisfies SC-002 literally against the real workspace. It edits a
human-approved (2026-06-25 sign-off) artifact + shipped Phase-C code, so it is a
deliberate owner-gated follow-up, not part of "build Phase B".

## Success Criteria

- **SC-002 (zero orphan visuals + zero bare-total headlines on the worked
  example)** -- VERIFIED against the TAUGHT worked example: the three-way binding
  map in `example-specialty-retail.md` parses under `seshat.binding-map/v1` and
  passes `check_binding_map` (no orphan, page served, headline on an overview
  question) via `test_taught_binding_map_example_parses_and_passes`, built from
  the committed file verbatim. NOT yet verified against the real
  `retail_store_sales` map -- that is the Option A follow-up (guard test pins the
  current DOA state).
- **SC-003 (three outcome classes, no silent-nothing)** -- VERIFIED for the map
  check: clean map -> `pass`/exit 0; each single mutation -> exactly its named
  finding (`orphan_visual`, `page_missing_question`, `bare_total_headline_visual`)
  /`blocked`/exit 1; missing/malformed map or absent brief -> fail-closed
  `blocked` naming the problem.
- **SC-004 (four #452 sub-gaps each have a named countermeasure)** -- the Phase B
  additions close the design-enforcement half:

  | #452 sub-gap | Phase-B enforcement |
  |---|---|
  | 1. No decision-questions | dashboard-design STOPs without a committed brief (FR-004); every visual must answer a brief question (`orphan_visual`) |
  | 2. No comparison framing | headline visual must answer an overview question that names a comparison (`bare_total_headline_visual`, FR-006) |
  | 3. No story order | the brief's story_order (Phase C) is the entry gate; a page serving no decision is a coverage defect |
  | 4. Not domain-specific | the three-way map ties every visual to a brief question grounded in the committed profile + contracts |

## Gate results (local, worktree)

- `ruff format --check` + `ruff check` on `src`/`tests`: clean (all checks pass).
- `seshat check` (static gate): exit 0 (pre-existing non-blocking RS1 warning on
  `retail_store_sales` readiness metadata dates only -- unrelated to this change).
- `seshat semantic-check`: exit 0, no drift (0 findings).
- Capability-inventory oracle: 45 pass (the updated `narrative-check`
  capabilities.yaml entry is valid and truthful).
- `narrative-check` + `_cli` tests: 46 pass (the two Phase-C skips are now real
  Phase-B tests; the CLI `--binding-map` mode covered).
- Full `pytest -m unit`: <recorded at commit time>.
- Exporter parity: `scripts/export_agent_bundles.py` -> "generated Claude and
  Codex bundles match reviewed inputs".
