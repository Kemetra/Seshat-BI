---
description: "Task list for Friendly PR Reviewer (plain-language PR summary)"
---

# Tasks: Friendly PR Reviewer (Plain-Language PR Summary)

**Input**: Design documents from `specs/130-pr-reviewer/`

**Prerequisites**: plan.md (required), spec.md (required for user stories),
research.md, data-model.md, contracts/

**Tests**: REQUESTED. Every pure function (renderer, differ, masker, next-action
pick, sticky-comment-body composition) gets fixture-driven unit tests. The
networked GitHub post is documented, not unit-tested against a live API.

**Organization**: Grouped by user story so each ships and tests independently.
MVP = US1 (the renderer). US2 (temporal differ) and US3 (opt-in sticky comment)
build on US1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 / US2 / US3, or SETUP / FOUND / POLISH

## Path Conventions

Single project: `src/seshat/`, `tests/unit/` at repo root; the skill under
`.claude/skills/`; templates under `templates/`; tool doc under `docs/tools/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm reuse surfaces and pin design shapes before code.

- [ ] T001 [SETUP] Write `research.md`: confirm the six consumed seams
  (review envelope, `finding_fingerprint`, masking contracts, `readiness_classify`
  rank, base-identity source, `ci.yml` reuse) are stable + sufficient; record the
  masking decision (lift the `interview_review._mask` shape patterns into a
  self-contained stdlib masker with a citation, do NOT import the private symbol;
  `readiness_evidence._scrub` is NOT lifted -- it needs a literal DSN and is not a
  shape masker, so DSN-URL detection stays a documented v1 non-coverage per
  FR-009 -- mirrors how `readiness_evidence` re-implements `_redact_dsn`).
- [ ] T002 [SETUP] Write `data-model.md`: the `FriendlySummary`,
  `ChangeClassification`, and `StickyComment` shapes (frozen, additive-versioned,
  NO score field anywhere; an explicit `undetermined[]` for missing-input lines).
- [ ] T003 [P] [SETUP] Write `contracts/pr-summary-contract.md`: the pure-function
  signatures (`render_summary`, `classify_changes`, `mask`, `pick_next_action`,
  `compose_comment`) -- each deterministic, no clock, no network, no mutation.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The new pure module's skeleton + the reuse wiring every story needs.

**CRITICAL**: No user story work begins until this phase is complete.

- [ ] T004 [FOUND] Create `src/seshat/pr_summary.py` skeleton: module docstring
  naming the consumed seams (review_integration, sarif, readiness_classify,
  readiness_evidence, interview_review) and stating the read-only / no-network /
  no-clock / no-score / stdlib-only invariants (Principle VIII; B1/B3).
- [ ] T005 [FOUND] Define the frozen dataclasses from data-model.md in
  `pr_summary.py` (`FriendlySummary`, per-stage status record, blocker-group
  record, `ChangeClassification`, `StickyComment`); additive `schema_version`;
  no numeric field.
- [ ] T006 [P] [FOUND] Create `tests/unit/test_pr_summary.py` with the shared
  fixtures: a `blocked` review envelope, an `ok`-with-warnings envelope, an
  absent/unproducible-envelope case (bad commit range; NOT an `input_defect`
  outcome value -- `build_review_result` emits only `ok`/`blocked`), an
  empty/no-findings envelope, a readiness-status fixture, and adversarial finding
  messages carrying the `_mask`-detected shapes (email/SSN/long-digit/secret-
  assignment) PLUS one bare DSN-URL message used to assert the documented v1
  non-coverage (FR-009).

**Checkpoint**: module + shapes + fixtures ready; stories can proceed.

---

## Phase 3: User Story 1 - Plain-language summary over the review envelope (Priority: P1) MVP

**Goal**: Deterministically render a plain-language summary from ONE review
envelope + readiness state -- affected-artifact narrative, per-stage verbatim
status, required approval authority, exactly one next action, masked, no score.

**Independent Test**: Given a fixture envelope + readiness fixture, `render_summary`
returns a summary naming the affected stages, each stage status verbatim, the
required authority, and exactly one next action; byte-identical on repeat; no
score; no leaked `_mask`-detected secret/PII shape (DSN-URL a documented v1 gap,
FR-009).

### Tests for User Story 1 (write FIRST, ensure they FAIL)

- [ ] T007 [P] [US1] Test `mask()` redacts the reused `_mask` shapes -- email /
  SSN-like / long-digit / secret-assignment -- leaves clean text unchanged, is
  idempotent; and ASSERTS the v1 non-coverage: a bare DSN/connection-URL is NOT
  redacted by `mask()` (documented gap, FR-009), so the test pins the known
  behavior rather than a false guarantee -- in `tests/unit/test_pr_summary.py`.
- [ ] T008 [P] [US1] Test `pick_next_action()` selects EXACTLY ONE action from
  `next_actions[]` by the `readiness_classify` refutation-first rank, returns a
  sentinel/`None` on an empty list (never invents one), and never returns two.
- [ ] T009 [P] [US1] Test `render_summary()` on the `blocked` envelope: names
  affected stages, states each stage status verbatim, lists blockers in plain
  language, names the approval authority, states one next action, emits NO
  merge-ready boolean and NO numeric score.
- [ ] T010 [P] [US1] Test `render_summary()` on the `ok`-with-warnings envelope:
  states not-blocked, surfaces warnings as "worth a look" not blockers, one next
  action, no score.
- [ ] T011 [P] [US1] Test honesty-on-missing: an ABSENT/unproducible review
  envelope (e.g. a bad commit range failed the review step -- `build_review_result`
  emits only `ok`/`blocked`, never an `input_defect` outcome) -> states the review
  could not be produced and stops; empty next_actions -> states "no next action
  produced"; absent readiness file -> stage `unknown` (source named), never assumed
  `pass` (FR-017).
- [ ] T012 [P] [US1] Test determinism: `render_summary()` is byte-identical across
  repeated calls on the same inputs; no wall-clock read (timestamp is an explicit
  argument) (FR-012, SC-003).
- [ ] T013 [P] [US1] Test redaction end-to-end: an adversarial finding message
  carrying the shapes the reused `_mask` contract detects (email, SSN/national-ID
  number, long digit run, `key: value` secret assignment) is masked in the
  rendered summary and a redaction is noted, never verbatim. The test MUST also
  assert the documented v1 limitation: a bare DSN/connection-URL in a finding
  message is NOT claimed masked (records the known residual gap, does not assert
  its removal) (FR-009, SC-004).

### Implementation for User Story 1

- [ ] T014 [US1] Implement `mask(text)` in `pr_summary.py`: a self-contained
  stdlib masker reproducing the `interview_review._mask` PII shapes (email,
  SSN/national-ID, long digit run, `key: value` secret assignment), cited in the
  docstring, no import of the private helper. Does NOT add a DSN/connection-URL
  shape (v1 out-of-scope per FR-009); the docstring MUST state that a bare DSN URL
  in a finding message is not masked in v1.
- [ ] T015 [US1] Implement `pick_next_action(next_actions)` using
  `readiness_classify` rank; returns exactly one or an explicit "none" (T008).
- [ ] T016 [US1] Implement `render_summary(envelope, readiness, base_fingerprints=
  None, *, timestamp=None)`: build the affected-artifact narrative from
  `affected_stages` / `changed_files` / `changed_readiness_state`; per-stage
  verbatim status from readiness/envelope; required authority from `approvals[]`;
  masked blocker lines; one next action; explicit `undetermined[]` for missing
  inputs. No score. No clock. (base diff wiring lands in US2.)
- [ ] T017 [US1] Implement the honesty branches (absent/unproducible envelope,
  empty next_actions, absent readiness, non-file locator, source conflict surfaced
  not resolved) (FR-017/019).

**Checkpoint**: US1 fully functional and testable; MVP renders from one envelope.

---

## Phase 4: User Story 2 - NEW vs RESOLVED vs pre-existing blockers (Priority: P2)

**Goal**: Given a base finding-identity set + the head finding set, classify every
finding into three disjoint groups (new / resolved / carried-over) keyed on the
shipped `finding_fingerprint`, and label them in plain language in the summary.

**Independent Test**: Given base + head fingerprint sets, `classify_changes`
returns three disjoint groups covering the union; with no base set the summary
states the distinction is undeterminable (naming the missing input), never
defaulting all to "new".

### Tests for User Story 2 (write FIRST, ensure they FAIL)

- [ ] T018 [P] [US2] Test `classify_changes(base, head)`: a shared fingerprint ->
  carried_over; head-only -> new; base-only -> resolved; the three sets are
  disjoint and cover the union of base and head (SC-002).
- [ ] T019 [P] [US2] Test identity is keyed on `finding_fingerprint` (rule_id +
  severity + locator + message), so a message differing only in a masked position
  is classified honestly from the fingerprint (FR-006).
- [ ] T020 [P] [US2] Test `render_summary()` with a base set: NEW / RESOLVED /
  pre-existing groups are labeled distinctly in the plain-language output.
- [ ] T021 [P] [US2] Test no-base honesty: with `base_fingerprints=None` the
  new-vs-pre-existing section states it could not be determined (names the missing
  base input) and lists findings as "present", never all "new" (FR-018).

### Implementation for User Story 2

- [ ] T022 [US2] Implement `classify_changes(base_fingerprints, head_findings)`
  in `pr_summary.py`: compute head fingerprints via `sarif.finding_fingerprint`,
  return the three disjoint `ChangeClassification` sets.
- [ ] T023 [US2] Wire `classify_changes` into `render_summary` when
  `base_fingerprints` is supplied: render the NEW / RESOLVED / carried-over groups;
  when absent, render the FR-018 undeterminable statement.

**Checkpoint**: US1 + US2 both work; the summary now separates change classes.

---

## Phase 5: User Story 3 - Opt-in sticky PR comment via the existing Action (Priority: P3)

**Goal**: Compose the summary into ONE sticky comment (stable marker, update in
place) and post it via an OPT-IN, off-by-default step added to the EXISTING
`ci.yml` -- no new workflow, no spam, no behavior change when not opted in, no
secret/PII egress.

**Independent Test**: `compose_comment(summary)` returns a body carrying the
stable marker (pure, fixture-tested); update logic targets an existing
same-marker comment vs creating one; a non-opted-in repo posts nothing.

### Tests for User Story 3 (write FIRST, ensure they FAIL)

- [ ] T024 [P] [US3] Test `compose_comment(summary)`: the body carries the stable
  HTML-comment marker, is deterministic, and is masked (no secret/PII/local path
  in the body) (FR-014, FR-016, SC-004).
- [ ] T025 [P] [US3] Test the update-vs-create decision helper: given a prior body
  with the same marker -> "update" (target that comment); given none -> "create
  one"; never "create a second" when a marker match exists (FR-014, SC-005).

### Implementation for User Story 3

- [ ] T026 [US3] Implement `compose_comment(summary)` + the marker constant + the
  `find_existing(comment_bodies)` update-vs-create decision helper (pure) in
  `pr_summary.py`.
- [ ] T027 [US3] Add ONE additive, OPT-IN, off-by-default step to
  `.github/workflows/ci.yml` (gated on a repo-set flag / dispatch input): render
  `retail check --format review`, produce the summary, and post/update the sticky
  comment via the runner's `gh` + GITHUB_TOKEN. It is a thin wrapper -- no new
  workflow file, no new Python dependency, not part of the tested core; guarded so
  a non-opted-in repo runs nothing new (FR-015, SC-005). Verify the edited `ci.yml`
  keeps `retail check` green.

**Checkpoint**: all three stories independently functional; opt-in comment lands.

---

## Phase 6: Polish, Docs & the Module Contract

**Purpose**: Ship the docs-first surfaces and the governance declaration.

- [ ] T028 [P] [POLISH] Author `.claude/skills/friendly-pr-reviewer/SKILL.md`:
  when-to-run, the F025 boundary (narrative vs merge-verdict), the read-only /
  no-score / no-action guardrails, and an EMBEDDED F024 Module Contract (Product
  Module; `read-only`; forbidden: create truth, approve/merge/dismiss, publish,
  DB connect, emit a score); NO self-assigned F-number (cross-cutting companion,
  human assigns).
- [ ] T029 [P] [POLISH] Author `templates/friendly-pr-summary.md`: the
  plain-language summary / sticky-comment shape (marker, affected artifacts,
  per-stage status, NEW/RESOLVED/pre-existing groups, approval authority, ONE next
  action); generic placeholders only (Principle VII); ASCII / UTF-8-no-BOM.
- [ ] T030 [P] [POLISH] Author `docs/tools/friendly-pr-reviewer.md`: inputs (the
  review envelope + readiness + optional base fingerprints), the temporal
  fingerprint diff, the opt-in step, and the F025 boundary; cross-link the reused
  modules.
- [ ] T031 [POLISH] Run the full local gate: `ruff format --check src tests`,
  `ruff check src tests`, `pytest -m unit`, `retail check`, `retail semantic-check`,
  and confirm the rule-registry snapshot test is unchanged (SC-006: zero new
  rules) and the existing `test_sarif.py` / review tests stay green.
- [ ] T032 [POLISH] Run `quickstart.md` end-to-end against a fixture envelope and
  confirm the rendered summary matches the spec's acceptance scenarios.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately.
- **Foundational (Phase 2)**: depends on Setup -- BLOCKS all user stories.
- **US1 (Phase 3)**: depends on Foundational. The MVP.
- **US2 (Phase 4)**: depends on Foundational + US1's `render_summary`.
- **US3 (Phase 5)**: depends on Foundational + US1 (`render_summary`); independent
  of US2 (a summary without the base diff still posts).
- **Polish (Phase 6)**: depends on all desired stories complete.

### User Story Dependencies

- **US1 (P1)**: no dependency on other stories -- independently testable MVP.
- **US2 (P2)**: builds on US1's renderer; independently testable via
  `classify_changes` fixtures.
- **US3 (P3)**: builds on US1's renderer; independently testable via
  `compose_comment` + the update-vs-create helper fixtures.

### Within Each User Story

- Tests are written FIRST and must FAIL before implementation (TDD).
- Pure helpers (`mask`, `pick_next_action`, `classify_changes`, `compose_comment`)
  before `render_summary` wiring.
- Commit after each task or logical group.

### Parallel Opportunities

- T001-T003 (Setup docs) can run in parallel.
- T006 fixtures parallel with T004/T005 skeleton once the module exists.
- All `[P]` test tasks within a story run in parallel (same test file, distinct
  test functions -- coordinate to avoid edit collisions).
- T028-T030 (skill / template / tool doc) run in parallel.

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1 Setup -> 2. Phase 2 Foundational -> 3. Phase 3 US1 renderer.
4. STOP and VALIDATE: render a plain-language summary from a fixture envelope.
5. That alone is a shippable MVP (a human reads one PR without opening JSON).

### Incremental Delivery

1. Setup + Foundational -> foundation ready.
2. US1 -> the renderer (MVP).
3. US2 -> add the NEW/RESOLVED/pre-existing distinction.
4. US3 -> add the opt-in sticky comment.
5. Polish -> skill + template + tool doc + Module Contract + full gate.

---

## Notes

- `[P]` = different files / independent; coordinate same-file test edits.
- Every summary line traces to a consumed input; a line with no source is a defect.
- Verify tests fail before implementing.
- The networked `ci.yml` step is opt-in, off by default, outside the tested core.
- No `retail check` rule; no score; no PR-mutating action; ASCII / UTF-8-no-BOM.
- No self-assigned F-number -- a human assigns it.
