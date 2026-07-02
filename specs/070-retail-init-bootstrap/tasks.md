# Tasks: `retail init` Bootstrap-to-First-Result (Compass-Driven Phase-1)

**Feature**: `070-retail-init-bootstrap` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Tests ARE included: the spec's acceptance scenarios and SC-002..SC-008 name concrete
mechanical guarantees (fence idempotency, no `current_stage`, projection drift,
deferred-live) that require unit coverage.

> **STATUS 2026-07-02: IMPLEMENTED.** All 25 tasks done on branch
> `070-retail-init-impl`. Modules `src/retail/{fence,compass_project,kit_init}.py` +
> the `init` CLI subcommand + `.claude/skills/retail-init/SKILL.md` + the canonical
> `.seshat/kit-source.yaml`. Dogfooded: `retail init` ran in this repo, generated
> `.seshat/` + the `SESHAT-KIT` fences (git diff = insertions only, outside-fence
> byte-identical); both drift checks pass. Gate: ruff format+lint clean, 842 unit
> tests pass (1 skipped, 94% cov), `retail check` exit 0, rule count unchanged at 47
> (no new `retail check` rule). The deferred-live profiling path is agent-performed
> (SKILL.md), not module logic, per BLOCKER-1.

Paths are relative to the repo root. `[P]` = parallelizable (different file, no
incomplete dependency).

---

## Phase 1: Setup

- [x] T001 Create the module skeletons `src/retail/kit_init.py`, `src/retail/compass_project.py`, `src/retail/fence.py`. Docstrings state the invariant: `kit_init`/`fence` do NO DB, NO network, NO profiling, NO prompt/menu; `compass_project` MAY import `pyyaml` lazily (like `semantic-check`) but does no DB/network — the `retail check` core stays stdlib-only
- [x] T002 [P] Create the canonical kit source `.seshat/kit-source.yaml` with the kit id, version, `verbs[]` (incl. `first-hour-compass` and `retail-onboard-table`), `hard_stops[]`, `integrations[]`, and `orient` block per `data-model.md` E1 (NO `current_stage`)
- [x] T003 [P] Create the agent-facing skill directory + `.claude/skills/retail-init/SKILL.md` frontmatter (name `retail-init`, Official Workflow Skill description: agent performs bootstrap + delegate + route; self-grants nothing; NOT a terminal wizard)

---

## Phase 2: Foundational (blocking prerequisites)

- [x] T004 Implement the fence reader/writer in `src/retail/fence.py`: locate `<!-- SESHAT-KIT START/END -->`, replace only the fenced body, insert a single fresh fence if absent, STOP+report if placement is unsafe (contract `fence.contract.md` F1–F6)
- [x] T005 Implement the projection generator in `src/retail/compass_project.py`: parse `.seshat/kit-source.yaml` (lazy `pyyaml`), emit `.seshat/compass.yaml` (verbatim `verbs`/`hard_stops`/`integrations`/`orient`, NO `current_stage`), render the fenced PROSE projection, and write `.seshat/manifest.yaml` + `.seshat/integrations/*.json` (contract `compass-yaml.contract.md` P1–P4)
- [x] T006 Implement TWO distinct drift checks in `src/retail/compass_project.py`, exposed as callables for later CI wiring (no new `retail check` rule this slice): (a) `compass.yaml == project_yaml(kit-source.yaml)` BYTE-EXACT; (b) `fenced_body == render_prose(kit-source.yaml)` (prose render-and-compare, NOT byte-vs-YAML) — per fence contract FC1 / compass contract P1

---

## Phase 3: User Story 1 — First run ends on a visible result from MY table (P1) 🎯 MVP

**Goal**: the AGENT (performing the skill) bootstraps, delegates the worked-example offer, routes into `retail-onboard-table`, and ends on grain candidates + column types (live DB) or the orientation structure + `[PENDING LIVE PROFILE]` (no DB) — substrate written but not shown. The `init` MODULE only writes substrate.

**Independent test**: the agent invokes the skill → delegates to `first-hour-compass` → routes into `retail-onboard-table` → ends on a profile result (live DB) or `[PENDING LIVE PROFILE]` structure (no DB); substrate present on disk but absent from the shown steps; no terminal menu.

- [x] T007 [US1] Implement `src/retail/kit_init.py` as SUBSTRATE-WRITING ONLY: call `compass_project` + `fence` to write the substrate and return a "next agent step" string. It MUST NOT profile, open a DB, prompt, or show a menu (assert-able: opens no DB connection). Delegation/routing/profiling is the agent's job in SKILL.md, not this module.
- [x] T008 [US1] Add the `init` subcommand to `src/retail/cli.py` (thin parser → `kit_init`; `--repo` default `.`; no DB args). It writes substrate and PRINTS the next agent step — no prompts, no menu, no profile (the `scaffold.py` write/print precedent)
- [x] T009 [US1] In `.claude/skills/retail-init/SKILL.md`, write the AGENT procedure: bootstrap (call `retail init` for substrate) → DELEGATE offer to `first-hour-compass` → ROUTE into `first-hour-compass` → `retail-onboard-table` for the Stage-1 profile → end on the visible result (live DB) or `[PENDING LIVE PROFILE]`. Explicitly forbid reimplementing the offer or the seam list (anti-fork, SC-008); explicitly state this is agent-performed, not a CLI wizard
- [x] T010 [P] [US1] In `.claude/skills/retail-init/SKILL.md` (and any `init` output), specify the deferred-live behavior the agent follows: when profiling reports no `db`/DSN, surface boundary + enable steps, mark `[PENDING LIVE PROFILE]`, stay useful, never traceback (FR-012) — delegated to the existing `retail-onboard-table`/`retail-validate` deferred mode, not reimplemented
- [x] T011 [P] [US1] Test `tests/unit/test_kit_init.py`: `kit_init` writes the substrate files and returns a next-step string; it opens NO DB connection and imports no profiler (assert the module boundary — profiling is the agent's, not the module's)
- [x] T012 [P] [US1] Test `tests/unit/test_kit_init.py`: the `retail init` CLI prints the next agent step and does NOT prompt / read stdin / print a profile (no-wizard guard)

**Checkpoint**: US1 is a demonstrable MVP — the agent performs `retail-init` and, over a live DB, reaches a first result on a real table (or `[PENDING LIVE PROFILE]` without one).

---

## Phase 4: User Story 2 — Bootstrap orients the agent (backstage substrate) (P2)

**Goal**: after `init`, an agent reads one harness-neutral router to learn verbs + hard-stops + "recompute stage from readiness-status.yaml"; fenced regions match source; hand-authored regions untouched.

**Independent test**: after `init`, `compass.yaml` declares verbs/hard-stops/orient with no `current_stage`; `AGENTS.md`/`CLAUDE.md` fenced regions match the canonical source; outside-fence bytes unchanged.

- [x] T013 [P] [US2] Test `tests/unit/test_compass_project.py`: `compass.yaml` is a byte-exact projection of `kit-source.yaml` and contains NO `current_stage` field (SC-004, P1/P2)
- [x] T014 [P] [US2] Test `tests/unit/test_fence.py`: run `init`-fence twice → exactly one fence; every byte OUTSIDE the fence identical before/after (SC-002, SC-003, F2/F3)
- [x] T015 [P] [US2] Test `tests/unit/test_fence.py`: no markers present → one fresh fence appended, rest unchanged; malformed/unsafe file → STOP + report, file unchanged (F4)
- [x] T016 [P] [US2] Test `tests/unit/test_compass_project.py`: an agent-style read of ONLY `compass.yaml` enumerates the verbs (incl. `retail-onboard-table`) + hard-stops (SC-007); the fenced prose projection agrees with the canonical PROSE render (FC1 render-and-compare, distinct from the byte-exact YAML check in T013)
- [x] T017 [US2] Dogfood: run `init` in THIS repo and commit the generated `.seshat/` + fenced regions of `AGENTS.md`/`CLAUDE.md`; confirm the drift check (T006) passes on the committed projections

**Checkpoint**: substrate is correct, harness-neutral, and constitution-safe; US1 still works on top of it.

---

## Phase 5: User Story 3 — Honest expectation-setting on the human seams (P3)

**Goal**: before profiling, the `init` skill states agent-handles-plumbing / user-owns-judgment and surfaces the seams from `first-hour-compass`'s single-source list as STOP points (no divergent copy).

**Independent test**: the skill surfaces the plumbing-vs-judgment statement and the seams AS STATED BY `first-hour-compass` before the profile step; there is no re-typed, divergent seam list inside `init`.

- [x] T018 [US3] In `.claude/skills/retail-init/SKILL.md`, have the agent emit the expectation statement (agent owns sequence/plumbing; user owns the judgment seams as STOP points) BEFORE routing to profiling, surfacing the seam wording from `first-hour-compass` (its single source), NOT a re-typed list (FR-009)
- [x] T019 [US3] In `.claude/skills/retail-init/SKILL.md`, state that the worked example is a narrative pattern to steer by, never a file template copied into the table dir (FR-013); delegate the actual wording to `first-hour-compass`
- [x] T020 [P] [US3] Test/review `tests/unit/test_kit_init.py` (or a docs check): the expectation statement precedes the profile step and `init` carries no divergent seam list — the seams shown trace to `first-hour-compass` (SC-006, anti-fork)

---

## Phase 6: Polish & Cross-Cutting

- [x] T021 [P] Wire the three new modules into `src/retail/rules/__init__.py`-style discovery only if applicable — NOTE: `init` adds NO `retail check` rule this slice; confirm the gate ID set is unchanged (guard against accidental rule wiring)
- [x] T021b [P] Guard test `tests/unit/test_kit_init.py`: assert `kit_init` / `compass_project` / `fence` import no network module (no `socket`/`urllib`/`http`/`requests`) and perform no fetch — the negative for FR-011 (no remote fetch / no auto-exec of pulled content)
- [x] T022 [P] Run `ruff format --check src tests` + `ruff check src tests` + `pytest -m unit` + `retail check` in the worktree; fix any finding at its locator
- [x] T023 [P] Add a glossary/docs note pointing at `docs/roadmap/distribution-ideas.md` and this feature (the `init` verb + `compass.yaml`), and update `COMPASS.md`'s routing table if a route entry for `init` is warranted (human-reviewed; no forked source of truth)
- [x] T024 Verify all authored files are UTF-8 no BOM, `\n`, ASCII, ≤260-char paths (FR-014, Principle IX); confirm no secret/host/DSN is written into any tracked file

---

## Dependencies & execution order

- **Setup (T001–T003)** → **Foundational (T004–T006)** → user stories.
- **US1 (P1, T007–T012)** depends on Foundational; it is the MVP and can ship first.
- **US2 (P2, T013–T017)** depends on Foundational; mostly tests of the substrate US1 already exercises — can run alongside US1 once T004–T006 land.
- **US3 (P3, T018–T020)** depends on US1's `kit_init` + SKILL.md existing.
- **Polish (T021–T024)** last.

## Parallel opportunities

- T002, T003 (Setup) in parallel — different files.
- Within US1: T010, T011, T012 in parallel (distinct concerns/files) after T007–T009.
- US2 tests T013–T016 all `[P]` — independent test files/assertions.
- Polish T021–T023 `[P]`.

## Implementation strategy

**MVP = Phase 1 + Phase 2 + Phase 3 (US1).** That alone delivers the analyst-visible
"aha": the agent performs `retail-init` → delegate example offer → route into
`retail-onboard-table` → profile (live DB) or `[PENDING LIVE PROFILE]` (no DB) →
first result. (The `retail init` CLI writes substrate + prints the next step; the
pick/profile are agent-performed, not a CLI wizard.) US2 hardens the substrate
(mostly test coverage of guarantees US1 already relies on); US3 adds the honest seam
framing. Ship US1 first; US2/US3 are incremental.

**Anti-fork guard is a first-class acceptance gate**, not polish: T009 forbids
restating the `first-hour-compass` offer, and SC-008 (T-none needed beyond review)
checks there is no second source for the first-arrival pattern.
