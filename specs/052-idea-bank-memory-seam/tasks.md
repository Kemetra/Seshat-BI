---
description: "Task list for 052-idea-bank-memory-seam"
---

# Tasks: Idea-Bank Memory Seam (IL1)

**Input**: Design documents from `specs/052-idea-bank-memory-seam/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/shipped-ideas.schema.md, quickstart.md

**Tests**: Included -- the spec defines a generic-only / fail-loud guard invariant (FR-006,
FR-007) that requires a test; TDD applies to that guard.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency)
- Scope is the CORE seam only; the optional IL1 static rule is OUT OF SCOPE (spec FR-010) and
  has NO task here.

## Phase 1: Setup

- [ ] T001 Confirm the spec dir + design artifacts are present (spec.md, plan.md,
  data-model.md, contracts/shipped-ideas.schema.md, quickstart.md) and the branch is
  `052-idea-bank-memory-seam`. No tooling/dependency setup is required (no new library).

---

## Phase 2: Foundational (the seam artifact)

**Purpose**: the ledger file must exist before the engine read step can consume it.

- [ ] T002 [US2] Author `docs/roadmap/shipped-ideas.yaml` per data-model.md and the contract:
  a YAML mapping keyed by idea-id, each entry having `status` (`shipped`|`settled`),
  `pr_sha` (non-empty evidence), `f_row` (F-row label or `none`). Seed from the existing
  prose "## SHIPPED / SETTLED" appendix in `docs/roadmap/idea-backlog.md`: A1/B1/B2/F7/F8 as
  `shipped` (each with its cited PR/SHA; `f_row: none` where a human placed no row -- e.g. the
  idea-engine planning workflows), F5/F6 as `settled` (citing the rejection rationale). ASCII +
  UTF-8 no BOM; generic identifiers only (no sample data / C086 specifics).

---

## Phase 3: User Story 1 -- Engine remembers what already shipped (P1)

**Goal**: the Memory stage reads the ledger as authoritative-on-conflict known-history.

**Independent test**: seed one id that the engine would otherwise generate; confirm it is
labeled known-history (with cited evidence) not presented as new.

- [ ] T003 [US1] Write a FAILING guard test for the ledger (TDD red) that asserts: (a) the
  committed `shipped-ideas.yaml` is valid YAML with every entry carrying the required keys and
  an in-domain `status`; (b) the generic-identifiers-only invariant (FR-007) -- no disallowed
  sample/domain values; (c) a malformed fixture fails loud (FR-006) and an absent/empty fixture
  degrades gracefully (FR-005). Place it alongside the existing repo manifest/wiring tests
  (mirror how `status-claims.yaml`/`parked-on.yaml` are guarded); use a lazy `import yaml` if
  Python, per the repo invariant.
- [ ] T004 [US1] Make T003 pass (green): ensure the seeded ledger satisfies the guard; adjust
  the seed rows if the test surfaces a missing key or a disallowed value. Do NOT weaken the
  test to fit a bad row.
- [ ] T005 [US1] Edit the Memory stage in `.claude/workflows/idea-engine.js` (`phase('Memory')`,
  the `agent(...)` reader prompt around the existing step 2/2b): add a step that resolves the
  repo root via `git rev-parse --show-toplevel` (no hard-coded machine path) and reads
  `docs/roadmap/shipped-ideas.yaml`. Fold each entry into the existing `prior_ideas[]` shape:
  `status: shipped -> current_state: shipped`, `status: settled -> rejected-settled`,
  `state_citation` built from `pr_sha` (+ `f_row` when not `none`). Keep `git_corroborated:
  false` (Ground still owns git). Respect the Workflow loader's stricter-than-node JS parser
  limits (CRLF, nested templates, quotes-in-template-text -- see repo memory note).
- [ ] T006 [US1] In the same Memory reader, encode the conflict precedence (FR-009): on a
  ledger-vs-prose disagreement for an id, use the ledger value and record the disagreement in
  `notes`; never rewrite either source. Encode the fail-loud branch (malformed/ missing-key
  yaml -> clear error) and the graceful branch (absent/empty -> continue on prose +
  ship-status) per the contract.
- [ ] T007 [US1] Assert the non-promotion invariant in the edit (FR-003/SC-002): the read step
  only LABELS; it adds nothing to `roadmap.md` and assigns no `f_row`. Leave a short code
  comment stating evidence-of-shipped-only, mirroring the existing "never writes the roadmap"
  comment in the stage.

---

## Phase 4: Polish / cross-cutting

- [ ] T008 [P] Validate the JS workflow still loads under the Workflow loader (the stricter
  parser, not just `node --check`) -- confirm the Memory-stage edit introduced none of the 5
  known incompatibility classes (CRLF, nested templates, quotes-in-template-text,
  quotes-in-interpolations, multi-line `(...).method()` wrappers).
- [ ] T009 [P] Run the quickstart.md checks: inspect the seeded ledger, run the guard test,
  read the Memory-stage wiring to confirm labeling + precedence + no-promotion. Confirm no new
  `EXPECTED_RULE_IDS` entry and no `src/retail/rules/` file were added (optional rule deferred).

## Dependencies

- T002 (ledger exists) blocks T003-T007 (the engine read + guard need the artifact).
- T003 (red) precedes T004 (green) -- TDD.
- T005 precedes T006-T007 (same file, sequential edits to one workflow function).
- T008-T009 run after the engine edit.

## Out of scope (no task)

- The optional IL1 static reconciler rule (spec FR-010) -- deferred to a separate rule-budget
  decision; if built later it must register its id and appear in `EXPECTED_RULE_IDS` (38 -> 39
  against the live frozenset, not prose) in that same change.
- Any "replace the prose appendix" edit to `idea-backlog.md` -- left for the human scope call
  (spec ## Clarifications); the yaml sits alongside the prose under this feature.
