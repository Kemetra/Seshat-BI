# Tasks: Review Pack Exporter (stable serialization formats)

**Feature**: `081-review-pack-exporter`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Data model**: [data-model.md](./data-model.md)

Dependency-ordered, TDD-first (tests before implementation, per this kit's Python testing rule
and the LVR/spec-057 precedent this feature follows). Organized by user story so each is an
independently testable slice (US1 Markdown, US2 JSON, US3 compact CI summary, US4
backwards-compatibility).

`[P]` = parallelizable with siblings in the same phase (different files, no ordering
dependency).

**Boundary (repeated from plan.md -- binding on every task below)**: this is the
IMPLEMENTATION-PHASE task list for a LATER, SEPARATE PR against `main`. Executing this
tasks.md is explicitly OUT OF SCOPE for the current spec-work run (no `src/` edits, no test
files created, no golden-file regen in this worktree). Do not run these tasks now.

**STOP CONDITION (binding on whoever executes this tasks.md later)**: STOP before any `git
commit`, `git push`, PR creation, merge, or self-approval. `git add -A` and `git add .` are
FORBIDDEN in every task below and in any task not listed here -- stage exact, named files only.

## Phase 0 - Setup

- [ ] **T001** Confirm the consumed seams are unchanged since research.md was written: re-read
  `src/retail/core.py` (`Finding`, `to_dict()` field names), `src/retail/runner.py::run_json`
  (the `{"findings": [...], "exit_code": ...}` envelope), and
  `src/retail/readiness_evidence.py` (`build_gold_ready_block` output shape and its
  `run_mode` values). Record any drift found against research.md section 1 in a short module
  docstring for the new file (do not silently proceed if a cited shape has changed). No
  functional code yet. (Grounds FR-009, SC-007.)
- [ ] **T002** [P] Create the new module skeleton `src/retail/review_pack_export.py` with only
  the `Pack`, `Section` dataclasses (per data-model.md sections 2-3; `frozen=True` per this
  kit's Python style rule) and module-level docstring citing this feature's spec path and the
  research.md-confirmed seams. No render functions yet (tests come first).

## Phase 1 - Tests first (RED), by user story

### US1 - Markdown (P1)

- [ ] **T003** [P] [US1] Write `tests/unit/test_review_pack_export_markdown.py` case: the
  `contracts/markdown.md` worked example (two sections, one `pass` one `blocked`, one embedded
  finding) renders to the exact expected Markdown string. (SC-002, SC-003.)
- [ ] **T004** [P] [US1] Add case: a section with empty `evidence`/`blocking_reasons` renders
  "none recorded" text, never an omitted section or blank ambiguous line. (spec.md Edge Cases.)
- [ ] **T005** [P] [US1] Add case: a `not_applicable` status section renders that token's own
  wording, never coerced to `pass` or `blocked`. (Acceptance Scenario US1.2.)
- [ ] **T006** [P] [US1] Add case: rendering the same `Pack` object twice (no `generated_at`)
  produces byte-identical output. (SC-005, FR-013.)
- [ ] **T007** [P] [US1] Add case: an unrecognized status token (not in data-model.md section 1)
  is visibly flagged in the Markdown output, never silently rendered as a known token.
  (FR-017.)

### US2 - JSON (P1)

- [ ] **T008** [P] [US2] Write `tests/unit/test_review_pack_export_json.py` case: the
  `contracts/json-schema.md` worked example round-trips through `to_json(pack)` ->
  `json.dumps` -> `json.loads` with every field matching exactly (including `schema_version`
  at the top level). (SC-002, FR-007.)
- [ ] **T009** [P] [US2] Add case: an embedded `FindingRecord` (four B2 fields) round-trips
  with field names and value shapes unchanged -- assert equality against
  `core.Finding(...).to_dict()` output for a synthetic Finding. (SC-007, FR-009.)
- [ ] **T010** [P] [US2] Add case: a section with no `findings` omits the `findings` key
  entirely from the JSON output (not an empty list) -- per the documented convention in
  `contracts/json-schema.md`.
- [ ] **T011** [P] [US2] Add case: no field in any rendered JSON document is a float/percentage
  or a bare completeness-count field name (grep the rendered dict's keys/values against a
  documented forbidden-pattern list: no key matching `*_score`, `*_health`, `*_confidence`,
  `*_of_*`, `*_percent`, `*_pct`). (SC-003, hard rule #9.)
- [ ] **T012** [P] [US2] Add case: an unrecognized status token in JSON output carries
  `"recognized": false"` alongside the verbatim token string. (FR-017.)

### US3 - Compact CI/PR summary (P2) -- highest fake-confidence risk

- [ ] **T013** [P] [US3] Write `tests/unit/test_review_pack_export_compact.py` case: the
  `contracts/compact-ci-summary.md` first worked example (worst status `blocked`, one
  `pass` + one `blocked` section) renders exactly the required shape (leading bracketed status
  token + every blocking reason from the worst-ranked section(s)). (FR-006, Acceptance
  Scenario US3.1.)
- [ ] **T014** [P] [US3] Add case: an all-`pass`/`not_applicable` pack renders `[PASS]` with at
  least one cited evidence line, never a bare "all good" with no citation. (Acceptance Scenario
  US3.2.)
- [ ] **T015** [P] [US3] Add case: a zero-section pack renders `[NO SECTIONS]`, never `[PASS]`.
  (spec.md Edge Cases; Acceptance Scenario US3.3.)
- [ ] **T016** [P] [US3] Add the FAKE-CONFIDENCE NEGATIVE test: assert the compact summary
  output for a representative set of fixture packs NEVER matches ANY of these forbidden
  patterns, anywhere in the output (not merely "as the primary verdict"): (a) any `\d+\s+of\s+
  \d+` count (e.g. "1 of 2"); (b) any `%` character or a `\d+\s*percent`/`pct` token; (c) any
  bare numeric fraction/ratio like `\d+/\d+`; (d) a maturity adjective like "mostly ready" /
  "partially ready" with no basis in an explicit status token. This is the single most
  important test in the whole suite (spec.md Safety Constraints; FR-005/FR-006/hard rule #9) --
  do not skip, narrow, or weaken it. It must also run against the compact output for EVERY
  fixture the other US3 tests use, not just a dedicated one.
- [ ] **T017** [P] [US3] Add case: two or more sections tied at the worst rank each contribute
  their `blocking_reasons` to the summary (not just the first one found). (data-model.md
  section 5.)

### US4 - Backwards compatibility (P2)

- [ ] **T018** [P] [US4] Write `tests/unit/test_review_pack_export_compat.py` case: encode the
  `contracts/backwards-compat-example.md` compliant `"1.0"` -> `"1.1"` pair as fixtures; assert
  every field the `"1.0"` consumer contract names is present and unchanged in the `"1.1"`
  fixture's rendered JSON. (SC-004, FR-007.)
- [ ] **T019** [P] [US4] Add a documentation-level (not runtime-enforced) test asserting the
  module's own docstring/comments state the additive-only rule from data-model.md section 4,
  so a future contributor changing the dataclasses sees the rule adjacent to the code they are
  editing. (Guards against the "schema-version discipline erosion" risk in plan.md.)
- [ ] **T020** Run the full suite; confirm every test from T003-T019 FAILS (module/functions not
  yet implemented beyond the T002 skeleton). RED gate.

## Phase 2 - Implement (GREEN)

- [ ] **T021** [US1] Implement `to_markdown(pack: Pack) -> str` in
  `src/retail/review_pack_export.py` per data-model.md + `contracts/markdown.md`. Deterministic;
  no wall-clock read; renders the status-severity fallback for unrecognized tokens per FR-017.
- [ ] **T022** [US2] Implement `to_json(pack: Pack) -> dict` per data-model.md +
  `contracts/json-schema.md`, including the `schema_version` top-level field, the
  findings-key-omission convention, and the `"recognized": false` companion field for
  unrecognized tokens.
- [ ] **T023** [US3] Implement the `STATUS_SEVERITY_ORDER` table (data-model.md section 5) and
  `to_compact_ci_summary(pack: Pack) -> str` per `contracts/compact-ci-summary.md`, including
  the all-clear and zero-section branches.
- [ ] **T024** Run the full suite; confirm T003-T019 all PASS. GREEN gate.

## Phase 3 - Guardrails (IMPROVE / verify invariants)

- [ ] **T025** Run the existing import-boundary guard test (B3,
  `tests/unit/test_live_surface_boundary.py`) and `retail check` to confirm the new module
  introduces no heavy import into the shared stdlib-only path and that the rule count is
  UNCHANGED (this feature adds no `retail check` rule). (Constitution Principle VIII.)
- [ ] **T026** [P] Grep the new module, its tests, and `contracts/` for any C086/pharmacy table,
  column, or measure literal; confirm none are hardcoded (Principle VII, FR-014, SC-006).
- [ ] **T027** [P] Confirm the new module has no import of `readiness-status.yaml`, any
  `mappings/**` path, `docs/quality/parked-on.yaml`, a DB driver, or a network call anywhere in
  `src/retail/review_pack_export.py` (FR-001, FR-011) -- a static grep for `open(`, `psycopg2`,
  `requests`, `urllib.request`, and any `mappings/` string literal should find nothing in this
  file.
- [ ] **T028** [P] Confirm the module never mutates its input `Pack`/`Section` objects (the
  dataclasses are `frozen=True`; add an explicit test if not already covered by T003-T019).
- [ ] **T029** Run `ruff format --check src/ tests/`, `ruff check src/ tests/`, and
  `pytest -m unit -x -q` clean. Final local-verification gate per this kit's standard workflow.
- [ ] **T030** Manually walk every acceptance scenario in spec.md (all four user stories)
  against the `contracts/` worked examples one final time, confirming the shipped module's
  actual output matches each contract file byte-for-byte (or updating the contract file, never
  silently diverging code from its own documented contract).

## Documentation tasks

- [ ] **T031** [P] Add a short "Review Pack Exporter" entry to whatever index this repo uses for
  new `src/retail/` modules (check `docs/architecture/` for an existing module inventory before
  adding a new one; if none exists, skip rather than inventing a new doc surface).
- [ ] **T032** [P] Cross-link this feature from `research.md`'s cited neighbours' own docs ONLY
  if those neighbours' maintainers choose to (e.g. J1's SKILL.md "See also" section) -- this
  is an OPTIONAL, separate, later edit to J1's shipped skill and is explicitly NOT required to
  ship this feature; do not perform it as part of this feature's own PR.

## Validation tasks

- [ ] **T033** Confirm `retail check` exit code and rule count are unchanged before/after this
  feature's implementation PR (Constitution Principle I: the gate exit code is the authority).
- [ ] **T034** Confirm `git status --short` after implementation shows only the new module, new
  test files, and (if T031 applied) one doc-index line -- no unrelated file touched, no `src/`
  file outside `review_pack_export.py` modified, no `templates/` or `docs/readiness/` change.

## STOP (binding)

- [ ] **T035** STOP here. Do not `git commit`, `git push`, open a PR, merge, or self-approve.
  Present the diff for human review per this repo's standard PR workflow. `git add -A` / `git
  add .` remain forbidden even at this final step -- stage only the exact files listed in T034.

## Out of scope (explicit -- do NOT do in this feature)

- Reading `readiness-status.yaml`, `metrics/*.yaml`, or `docs/quality/parked-on.yaml` from the
  exporter module (that is J1's composer role -- FR-001).
- Adding a new `retail check` rule or a new readiness stage.
- Adding a YAML writer/dependency (FR-016; deferred).
- Adding a `retail export-pack` CLI subcommand or any CLI wiring (plan.md Forbidden scope).
- Any numeric confidence/health/maturity score or "N of M" completeness tally in any output
  format, under any circumstance (hard rule #9).
- Editing J1's shipped skill/template, B2's `runner.py`, or LVR's `readiness_evidence.py` --
  this feature reuses their field-name conventions by documentation only, never by editing
  their source.
- Any live DB, PBIP, or execution-adapter (F016) read.
- Building K1 (gate-observability-rollup) or treating this feature as K1's "third emission
  format" -- this feature is a formatter over one pack, not an aggregator over many gates
  (research.md section 1.4).
