---
description: "Task list for feature 008 -- business meaning registry + Arabic<->English retail term dictionary"
---

# Tasks: business meaning registry + Arabic<->English retail term dictionary

**Input**: Design documents from `specs/008-business-meaning-registry/`

**Prerequisites**: plan.md (required), spec.md (required for user stories). No
research.md / data-model.md / contracts/ for this docs/templates slice (see plan.md).

**Tests**: No automated test tasks -- this is docs/templates only (no code). Verification
is a leakage/ASCII/no-BOM scan + `retail check` exit 0 + the existing unit suite staying
green, captured in the Phase D tasks. Each user story's "Independent Test" (spec.md) is a
human review of a filled template, not an automated test.

**Organization**: Tasks grouped by user story so each story is independently authorable
and reviewable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 / US2 / US3, or SETUP / POLISH
- Exact file paths are absolute-from-repo-root.

## Path Conventions

- New templates: `templates/<name>.md`
- New Layer-2 doc: `docs/source-intelligence.md`
- Edited readiness doc: `docs/readiness/source-ready.md`
- Cited (NOT edited): `docs/data-dictionary.md`, `docs/worked-examples/c086-pharmacy.md`,
  `docs/roadmap/roadmap.md`, `.specify/memory/constitution.md`

---

## Phase 1: Setup (Shared Conventions)

**Purpose**: Establish the shared authoring conventions both templates must follow, so
Phase A and Phase B stay consistent and generic.

- [ ] T001 [SETUP] Re-read the convention sources and record the shared header recipe to
      reuse verbatim in both new templates: the `>`-blockquote header ("copy this file to
      ...", "ASCII only. Use `->` for arrows ...", "cite numbers, not adjectives"), and
      the "See also" block shape. Sources: `templates/source-profile.md`,
      `templates/assumptions.md`, `templates/unresolved-questions.md`.
- [ ] T002 [SETUP] Confirm the generic/instance boundary checklist for the leakage scan:
      the forbidden-token list (real Arabic source terms, `Z`-style billing codes,
      `PHARMA`/segment values, real product/store/staff names, El Ezaby, C086 as a VALUE
      vs C086 as a CITATION). Derived from Principle VII + hard rule #7;
      filled instance to CITE is `docs/data-dictionary.md` reference mappings. (FR-005)

**Checkpoint**: Convention recipe + forbidden-token list ready; authoring can begin.

---

## Phase 2: Foundational

**Purpose**: None blocking. This slice has no shared code/schema foundation; the two
templates are independent files. (Phase kept for template parity; intentionally empty.)

**Checkpoint**: N/A -- proceed directly to user stories.

---

## Phase 3: User Story 1 - Register a business term with a PROPOSED meaning (Priority: P1) MVP

**Goal**: Deliver the generic Business Meaning Registry template -- the reusable shape for
"PROPOSED for human confirmation, never invented" semantic registration.

**Independent Test**: a reviewer fills the empty template with PLACEHOLDER (non-C086)
terms and confirms every entry has a meaning + `proposed`/`confirmed` status, there is NO
numeric confidence field, and the filled file is citable as Source Ready `evidence[]` --
no code written.

### Implementation for User Story 1

- [ ] T003 [US1] Author `templates/business-meaning-registry.md` -- the `>`-blockquote
      header (T001 recipe): "copy this file to `mappings/<table>/business-meaning-registry.md`",
      ASCII-only note, generic-not-C086 warning, cite-the-worked-example instruction. (FR-001)
- [ ] T004 [US1] In the same file, define the per-entry schema table with columns: term /
      coded value (as in source) | canonical meaning | observed surface forms | source
      column(s) seen in | status (`proposed` | `confirmed`) | confirming owner (when
      `confirmed`) | evidence cited. Placeholder rows only. NO numeric confidence/score
      column. (FR-002; hard rule #9)
- [ ] T005 [US1] Encode the PROPOSED-not-invented discipline in the file: every meaning
      defaults to `proposed`; promotion to `confirmed` is a NAMED human action; a
      business-rollup / PII / grain meaning MUST route to
      `mappings/<table>/unresolved-questions.md` and MUST NOT be self-confirmed by the
      agent. Add the Socratic conflict-surfacing reminder (an entry that contradicts the
      profile must STOP, not be buried). (FR-006; Principle V)
- [ ] T006 [P] [US1] Add the "See also" block to the registry template: Principles V & VII,
      RC defaults it relies on, `docs/readiness/source-ready.md`, and the filled instance
      it CITES (`docs/data-dictionary.md`, `docs/worked-examples/c086-pharmacy.md`). (FR-010)
- [ ] T007 [US1] Leakage + ASCII + no-BOM self-check on `templates/business-meaning-registry.md`
      against the T002 forbidden-token list (zero C086/ezaby/pharmacy VALUES; cite-not-inline;
      UTF-8 no BOM; ASCII content). (FR-005, SC-001, SC-002)

**Checkpoint**: Business Meaning Registry template complete and passes its leakage/ASCII
self-check -- MVP is usable on its own.

---

## Phase 4: User Story 2 - Look up / record an Arabic<->English retail term (Priority: P1)

**Goal**: Deliver the generic Arabic<->English retail term Dictionary template with the
RC8 returns discipline and synonym/encoding-variant handling baked in.

**Independent Test**: fill the dictionary with PLACEHOLDER bilingual rows
(`<arabic-term>` -> `<english-meaning>`, no real values), confirm it captures term +
meaning + synonyms + evidence + status and states returns identity comes from the
authoritative billing column (RC8), not a measure sign.

### Implementation for User Story 2

- [ ] T008 [US2] Author `templates/retail-term-dictionary.md` -- the `>`-blockquote header
      (T001 recipe), "copy this file to `mappings/<table>/retail-term-dictionary.md`",
      ASCII-only note, generic-not-C086 warning, cite-the-worked-example instruction. (FR-003)
- [ ] T009 [US2] Define the per-entry bilingual schema table: term (source language, e.g.
      Arabic) | canonical English meaning | synonyms / surface variants (incl.
      encoding-corruption variants under one canonical term) | source column seen in |
      status (`proposed` | `confirmed`) | evidence contributed. Placeholder rows only; NO
      numeric score column. (FR-004; hard rule #9)
- [ ] T010 [US2] Bake in the RC8 returns discipline: a returns-related term's note MUST
      state returns identity comes from the AUTHORITATIVE billing column, NOT the sign of a
      measure; and an encoding-variant note (one canonical meaning absorbs mojibake/
      alternate spellings as synonyms, not new terms). (FR-004; Principle VI / RC8)
- [ ] T011 [P] [US2] Add the "See also" block to the dictionary template: Principles V & VII,
      RC8 + RC-encoding, `docs/readiness/source-ready.md`, and the CITED filled instance
      (`docs/data-dictionary.md` billing_type/business_segment tables;
      `docs/worked-examples/c086-pharmacy.md`). (FR-010)
- [ ] T012 [US2] Leakage + ASCII + no-BOM self-check on `templates/retail-term-dictionary.md`
      (zero real Arabic source terms / `Z`-codes / segment values; cite-not-inline; UTF-8 no
      BOM; ASCII -- including the placeholder Arabic must be the literal token `<arabic-term>`,
      NOT a real Arabic string). (FR-005, SC-001, SC-002)

**Checkpoint**: Both P1 templates exist, are generic, and pass their self-checks.

---

## Phase 5: User Story 3 - Feed Source Ready evidence without inventing readiness (Priority: P2)

**Goal**: Document how the two artifacts contribute Source Ready `evidence[]` and map them
onto the EXISTING Source Ready statuses, and wire the spine -- without adding any new
stage, status, blocking reason, or confidence number.

**Independent Test**: trace a generic example -- empty registry -> Source Ready
`blocked`/`warning`; filled+PROPOSED -> contributes to `pass` evidence; INVENTED meaning ->
`blocked` with the EXISTING "Semantic meaning INVENTED" blocking reason -- using only the
vocabulary already in `docs/readiness/source-ready.md`.

### Implementation for User Story 3

- [ ] T013 [US3] Author `docs/source-intelligence.md` -- the Layer-2 (Source Intelligence)
      reference: what the registry + dictionary are, how a filled copy becomes Source Ready
      `evidence[]`, the generic example trace (empty -> blocked/warning; filled+proposed ->
      pass evidence after analyst confirms; invented -> blocked), and an explicit statement
      that NO new stage / status / blocking reason / confidence number is introduced.
      ASCII, UTF-8 no BOM, "See also" block. (FR-007; SC-004; hard rule #9)
- [ ] T014 [US3] Edit `docs/readiness/source-ready.md` ADDITIVELY: in "Required artifacts"
      add a note (or a sibling "Optional strengthening artifacts" line) that the registry +
      dictionary are OPTIONAL semantic-proposal artifacts that strengthen evidence, while
      the profile remains the ONE required artifact and the gate stays a review; add both to
      "See also". MUST NOT change the required-artifact set, the statuses, the blocking
      reasons, or the review-gate posture. (FR-008)
- [ ] T015 [US3] Verify the spine linkage reads consistently: `docs/source-intelligence.md`
      and the `source-ready.md` note agree, both point to `readiness-model.md` /
      `readiness-pipeline.md`, and neither introduces a numeric score or a new status.
      (SC-004, SC-005)

**Checkpoint**: The artifacts are wired into Source Ready as optional evidence; the spine
vocabulary is unchanged.

---

## Phase 6: Polish & Verification (Cross-Cutting)

**Purpose**: Repo-wide verification that the slice is generic, ASCII-clean, and
gate-green.

- [ ] T016 [POLISH] Repo-wide leakage scan over all NEW/EDITED files
      (`templates/business-meaning-registry.md`, `templates/retail-term-dictionary.md`,
      `docs/source-intelligence.md`, `docs/readiness/source-ready.md`): assert ZERO
      C086/ezaby/pharmacy VALUES; every such reference is a CITATION to the worked example.
      (FR-005; SC-002; Principle VII; hard rule #7)
- [ ] T017 [P] [POLISH] ASCII + UTF-8-no-BOM scan over all four files (no BOM; no byte > 127;
      placeholder Arabic is the token `<arabic-term>`, not a real string). (SC-001)
- [ ] T018 [POLISH] Run `retail check` -- assert exit 0 (current rule count) with the new/edited files;
      run the existing unit suite -- assert green; confirm no new Python and `dependencies = []`
      unchanged. (SC-003; FR-009)
- [ ] T019 [P] [POLISH] No-score / discipline review: grep both templates for any
      confidence/score field and confirm NONE exists; confirm each template carries the
      proposed-default + human-confirmation + `unresolved-questions.md` pointer. (SC-005;
      hard rule #9; Principle V)
- [ ] T020 [POLISH] Trace-the-example review (SC-004): a reviewer walks the generic example
      in `docs/source-intelligence.md` end-to-end and confirms it uses only existing Source
      Ready vocabulary (no invented stage/status/blocking-reason/score).

**Checkpoint**: All success criteria SC-001..SC-005 demonstrably met.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately.
- **Foundational (Phase 2)**: intentionally empty -- no blocker.
- **US1 (Phase 3)** and **US2 (Phase 4)**: both depend only on Setup; they touch DIFFERENT
  files (`business-meaning-registry.md` vs `retail-term-dictionary.md`) and can run in
  parallel.
- **US3 (Phase 5)**: depends on US1 + US2 existing (the explainer and the `source-ready.md`
  note reference both templates).
- **Polish (Phase 6)**: depends on Phases 3-5 complete (it scans/verifies all new files).

### User Story Dependencies

- **US1 (P1)**: independent -- the registry stands alone (MVP).
- **US2 (P1)**: independent of US1 -- the dictionary stands alone; parallelizable with US1.
- **US3 (P2)**: integrates US1 + US2 into the spine; not required for either to be usable.

### Within Each User Story

- Header (T003/T008) before the schema table (T004/T009) before discipline (T005/T010).
- "See also" (T006/T011) is [P] -- independent once the file exists.
- The per-story leakage self-check (T007/T012) is last within the story.

### Parallel Opportunities

- Phase 1: T001 and T002 are independent -- run together.
- US1 and US2 entire phases run in parallel (different files).
- T006 [P] / T011 [P] within their stories; T017 [P] / T019 [P] in Polish.

---

## Parallel Example: US1 and US2 together

```text
# Two authors (or two passes) in parallel, different files:
Author A: T003 -> T004 -> T005 -> T006 -> T007   (templates/business-meaning-registry.md)
Author B: T008 -> T009 -> T010 -> T011 -> T012   (templates/retail-term-dictionary.md)
# Then converge:
Both done -> T013/T014/T015 (US3) -> T016..T020 (Polish)
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1 Setup (T001, T002).
2. Phase 3 US1 -- the Business Meaning Registry template.
3. STOP and VALIDATE: fill it with placeholders; confirm generic + no-score + citable.
4. The registry is a usable Source Ready evidence artifact on its own.

### Incremental Delivery

1. Setup -> US1 (registry, MVP) -> US2 (dictionary) -> US3 (spine linkage) -> Polish.
2. Each P1 template adds standalone value; US3 ties them to the spine; Polish proves the
   generic/ASCII/gate-green guarantees.

---

## Notes

- [P] = different files, no dependencies.
- This slice writes TEXT only -- no code, no CLI, no checker rule, no dependency
  (FR-009). `retail check` exit 0 + green suite is necessary; the generic/no-invention
  discipline is the substantive bar (SC-002, SC-005).
- The single biggest risk is C086 LEAKAGE -- T002/T007/T012/T016 exist to catch it.
- Commit after each story or logical group; keep `source-ready.md` edits additive.
