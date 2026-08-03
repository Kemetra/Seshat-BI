---
description: "Task list for spec 138 — agent-driven bundle completion"
---

# Tasks: Agent-driven bundle completion

**Input**: Design documents from `/specs/138-agent-driven-bundle/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

> **RATIFIED** by Ahmed Shaaban (owner) 2026-07-31 — implementation permitted.
> FR-026 still caps concurrent implementation at **one story at a time** across
> specs 137 and 138. Both blocking owner decisions are now RULED (2026-07-31):
> the routing-cost ceiling is **6,000 `tokens_approx` per bundle** (T006), and
> shipped skills **name the scaffold verb** rather than instructing a read of
> `templates/`. Payload work is unblocked.

**Tests**: REQUIRED. The specification makes contract tests the acceptance
evidence (FR-008 names `test_committed_bundles_match_clean_regeneration`), and
each file in `contracts/` names its enforcing test.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable — different files, no dependency on an incomplete task
- **[Story]**: US1–US5, matching the user stories in spec.md

## Path Conventions

Existing repository layout. No new package, no new top-level directory
(plan.md, Structure Decision).

---

## Phase 1: Setup (baseline capture)

**Purpose**: record the "before" state everything is measured against. No
behaviour changes.

- [x] T001 Capture the pre-change gate baseline into `specs/138-agent-driven-bundle/evidence/baseline-gates.txt` by running `seshat check`, `seshat kit-lint` and `seshat doctor`, recording the pre-existing `RS1` warning on `mappings/retail_store_sales/readiness-status.yaml` as expected-and-unrelated — **done**
- [x] T002 [P] Record the committed bundle digests for both harnesses into `specs/138-agent-driven-bundle/evidence/baseline-bundles.txt` from `integrations/claude-code/seshat-bi/bundle-manifest.json` and `integrations/codex/seshat-bi/bundle-manifest.json` — **done: 11 skills each, 255/231 files, zero compass verbs**
- [x] T003 [P] Enumerate the dev-only references into `specs/138-agent-driven-bundle/evidence/portability-findings.md`, one row per reference with skill, path, line and the FR-017 verdict — **done: 33 pairs, not the 23 cited while authoring (that counted path classes); 1 PASS-dev-scoped, 3 REVIEW, 17 FAIL-read, 12 FAIL-provenance**

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the only genuinely cross-story prerequisite — the routing-cost
measurement US3 and US4 are both gated on. **Not** a prerequisite for US1.

- [x] T004 Implement the routing-cost measurement per research R5 in `scripts/measure_bundle_routing_cost.py`, measuring only the shipped skill set's name and description metadata per bundle, never skill bodies
- [x] T005 Record the current routing cost for both bundles into `specs/138-agent-driven-bundle/evidence/routing-cost.md` and propose the ceiling required by FR-021a as a reviewed number
- [x] T006 Obtain the owner's reviewed ceiling for FR-021a and record it in `specs/138-agent-driven-bundle/evidence/routing-cost.md` — the agent proposes, a named human sets it

**Checkpoint**: PASSED -- ceiling ruled at 6,000 tokens_approx per bundle (Ahmed Shaaban, 2026-07-31); see evidence/routing-cost.md.

---

## Phase 3: User Story 1 — the governed loop works on install (Priority: P1) 🎯 MVP

**Goal**: enabling the plugin makes the six read-only governor tools available
with no manual registration step, on both harnesses.

**Independent test**: install into a clean workspace on each harness; tools
present without registration; with the optional extra removed, a named
actionable instruction and no simulated answer.

**No dependency on any other story. Merge-safe alone and in any order.**

### Blocking research (must close before any US1 edit)

- [x] T007 [US1] **CONFIRMED both harnesses** (see evidence/harness-server-support.md) Confirm research R1 at the harness versions the acceptance run will name — feasibility is already established from primary sources, so this confirms *this build*. Verify at the runtime, not a settings pane: `codex mcp list` / `codex mcp get` on Codex (an absent settings-UI row is expected per the open upstream defect) and the equivalent on Claude. Record versions and output in `specs/138-agent-driven-bundle/evidence/harness-server-support.md`; note the local CLI is `codex-cli 0.146.0` against `0.144.5` in `docs/install/support-matrix.md`
- [x] T008 [US1] **CLOSED BY DESIGN per owner ruling 2026-07-31** -- the cwd dependency is removed (`src/seshat/workspace_root.py`); discovery fails by name rather than reporting on the wrong tree, so R2's answer cannot break the loop. Original: Confirm research R2 — the working directory a plugin-launched server starts in — and record whether `seshat mcp`'s `--repo` default of `.` resolves to the user's workspace or the plugin directory
- [x] T009 [US1] **CONFIRMED on Claude, PARTIAL on Codex** Confirm research R3 — whether each harness surfaces a failed plugin server's diagnostic to the user — and record the result in `specs/138-agent-driven-bundle/evidence/harness-server-support.md`
- [x] T010 [US1] **STOP GATE CLEARED 2026-07-31 by owner ruling** -- T007 positive, T009 positive/partial, T008 closed by design (cwd dependency removed). No workaround was implemented and no re-scope occurred.: if T007 or T008 is negative, halt US1, report to the owner, and re-scope. Do not implement a workaround. A missing settings-UI row is **not** a negative result — only a runtime that does not register the server, or one that resolves the wrong repository root, is.

### Tests

- [x] T011 [P] [US1] (in `tests/contract/test_bundled_server_declaration.py`; the exemption is enumerated in `reconciliation_exemptions` so WIDENING it fails) Add the bundled-server class exemption assertions to `tests/contract/test_public_command_surface.py` per `contracts/bundled-server-declaration.md` obligation 6 — the exemption must be scoped to that class alone and must fail if widened
- [x] T012 [P] [US1] Add assertions to `tests/contract/test_claude_plugin_bundle.py` that the Claude bundle carries the server declaration and its manifest pointer
- [x] T013 [P] [US1] Add the equivalent assertions to `tests/contract/test_codex_plugin_bundle.py`
- [x] T014 [P] [US1] (camelCase `mcpServers` asserted; snake_case explicitly rejected) Add assertions to `tests/contract/test_generated_agent_bundles.py` that the declaration carries no repository path argument, no credential and no environment secret, **and that its wrapper key is the camelCase `mcpServers`** — the snake_case `mcp_servers` form in one platform's published example is unparsed and yields a server that silently never loads (`contracts/bundled-server-declaration.md` obligation 7)

### Implementation

- [x] T015 [US1] `distribution/bundle-templates/shared/mcp-servers.json`: Author the single shared server declaration in `distribution/bundle-templates/shared/` naming only the six existing read-only tools' server
- [x] T016 [US1] Add the manifest pointer to `distribution/bundle-templates/claude/.claude-plugin/plugin.json`
- [x] T017 [US1] Add the manifest pointer to `distribution/bundle-templates/codex/.codex-plugin/plugin.json`
- [x] T018 [US1] Add the bundled-server artifact class to `distribution/public-command-surface.yaml`, with the reconciliation exemption documented inline as required by FR-013
- [x] T019 [US1] Project the declaration into both bundles by running `python scripts/export_agent_bundles.py --repo .`; never hand-edit `integrations/`
- [x] T020 [US1] Update `docs/install/agent-install.md` so automatic wiring is the primary path and the manual `claude mcp add` form is retained only for non-plugin use (FR-014) — do not delete it

### Verification

- [ ] T021 [US1] Verify on both harnesses in a scratch workspace created by `seshat init-project`: tools present with no registration, and the governor reporting on the scratch workspace rather than the plugin directory. Confirm via the runtime's own list/get commands plus a successful tool call — never via a settings pane
- [x] T022 [US1] Verify degradation with the optional extra removed — a named two-lane install hint from `src/seshat/cli/__init__.py::_run_mcp`, no simulated governor output, no claim the loop is available — recording the session evidence in `specs/138-agent-driven-bundle/evidence/us1-acceptance.md`
- [x] T023 [US1] Verify against `src/seshat/governor/mcp_server.py` that no enabled tool advances a stage, grants an approval, writes a readiness artifact, or emits any score, and record it in `specs/138-agent-driven-bundle/evidence/us1-acceptance.md`

**Checkpoint**: US1 is independently shippable.

---

## Phase 4: User Story 2 — inventory and gate tell one truth (Priority: P2)

**Goal**: one authored source for what ships; the allowlist generated from it;
the hand-written six-name gate gone.

**Independent test**: regenerate both bundles from a clean checkout and get
byte-identical output.

**Blocks US3 and US4.**

### Tests

- [x] T024 [P] [US2] Create `tests/contract/test_capability_inventory.py` asserting every skill-surface entry resolves to an existing directory via `references.skill` (scalar or list) — this already holds today, so it lands as a regression guard
- [x] T025 [P] [US2] Assert in the same file that every skill directory in the repository is covered by exactly one inventory entry
- [x] T026 [P] [US2] Assert `ships` has no default — an entry lacking it is an error, so a new skill cannot slip in unclassified (`contracts/ship-classification.md` obligation 2)
- [x] T027 [P] [US2] Assert the classification invariants: `development-only` implies `ships: false`; `compass-verb` implies `ships: true` and appears in `.seshat/kit-source.yaml`
- [x] T028 [P] [US2] Assert in `tests/contract/test_capability_ship_classification.py` that the committed `distribution/public-knowledge-allowlist.yaml` matches a fresh derivation, so a hand-edit fails rather than taking effect (obligation 13) -- written; **RED until T039 regenerates the allowlist**, which is blocked on the portability audit per the correction-4 ruling
- [x] T029 [P] [US2] Assert in `tests/contract/test_capability_ship_classification.py` that the fail-closed export conditions (obligations 10–12) each fail with the offender named -- all three GREEN. Obligation 11 needed splitting: the derivation check uses a synthetic root (no skill directory in this repo lacks a `SKILL.md`), and a separate `test_committed_bundle_carries_every_shipping_entry` asserts the tree-state property, which is RED with 32 offenders until regeneration

### Inventory repair

- [x] T030 [US2] Widen the O2 coverage-scope statement in the header of `docs/capabilities/capabilities.yaml` from `.claude/skills/*/SKILL.md` to any committed kit-authored SKILL.md, then add the six knowledge-root entries to `docs/capabilities/capabilities.yaml` (`bi-sql-`, `bi-dax-`, `bi-python-`, `bi-bigdata-`, `retail-kpi-`, `bi-analyst-knowledge`) with `ship_classification: knowledge-root` and `ships: true`
- [x] T031 [US2] ~~Add `skill_dir` to the four entries whose id matches no directory~~ **DROPPED 2026-07-31** -- the existing `references.skill` already resolves all four (scalar and list form); measured 50/50 coverage, 0 dangling. See `evidence/us2-design-corrections.md`
- [x] T032 [US2] Add `ships` and `ship_classification` to every skill-surface entry, with `ships: true` for the six knowledge roots only and `ships: false` for everything else at this story
- [x] T033 [US2] Classify the four development-only skills as `development-only`: `friendly-pr-reviewer`, `pr-readiness-reviewer`, `release-notes-generator`, `showcase-build`
- [x] T034 [US2] Classify the fourteen specification-workflow skill directories as `development-only`
- [x] T035 [US2] Verify the repaired inventory renders by running `python -m seshat.capability_inventory --format json`

### Derivation

- [x] T036 [US2] Implement the allowlist derivation from the inventory, producing deterministic ordering and stable `entry_id` assignment (`contracts/ship-classification.md` obligation 6) -- `src/seshat/allowlist_derivation.py`. Scope discovered during implementation: the allowlist has TWO sections with different authorities. `entries` are derived here; `template_entries` describe bundle-native scaffolding authored under `distribution/bundle-templates/` and are carried through verbatim, because their `template_id` values (`router`, `sql-skill`, …) are authored names a derivation must not invent
- [x] T037 [US2] Replace the hand-written six-name assertion in `scripts/export_agent_bundles.py` with the derivation — replacement, not supplementation (FR-006). Wiring it before the audit passes would make the export emit 43-skill bundles carrying read-instructions that cannot resolve in a consumer workspace
- [x] T038 [US2] Preserve every existing allowlist entry field and `policy.absence_means_excluded: true` in the generated output (obligations 7–8) -- the full nine-field entry shape is emitted and `policy` is carried verbatim
- [x] T039 [US2] Regenerate `distribution/public-knowledge-allowlist.yaml` from the inventory and commit it as generated-but-reviewed

### Verification

- [x] T040 [US2] ~~Run `python scripts/export_agent_bundles.py --repo .` then `git diff --stat integrations/` and confirm the diff is **empty**~~ **WAIVED 2026-07-31 by owner ruling** (correction 4, option 2): US2 now carries the US3+US4 payload, so the `integrations/` diff is large by design and must be reviewed as a payload change rather than compared to zero. The empty-diff acceptance no longer applies; the replacement check is T059/T064 against the 6,000 ceiling plus the portability audit. See `evidence/us2-design-corrections.md`
- [x] T041 [US2] Confirm `tests/contract/test_generated_agent_bundles.py::test_committed_bundles_match_clean_regeneration` passes unchanged

**Checkpoint**: the gate is derived and fail-closed, with zero payload change.

---

## Phase 5: User Story 3 — the ten compass verbs are loadable (Priority: P3)

**Goal**: every verb `.seshat/kit-source.yaml` names ships, and no shipped skill
points at a file a customer workspace lacks.

**Independent test**: in a workspace with no Seshat development checkout, all ten
load and every instructed path resolves.

**Depends on US2.**

### Tests

- [x] T042 [P] [US3] Create `tests/unit/test_portability_audit.py` asserting the transform fails on a read-instruction to an unscaffolded path and reports skill, path, line and reason
- [x] T043 [P] [US3] Assert in `tests/unit/test_portability_audit.py` that it permits a reference naming a scaffold output, and permits a reference scoped by an explicit development-repository condition (obligations 3–4)
- [x] T044 [P] [US3] Assert it derives "present in a workspace" from `src/seshat/workspace_init.py::_EMPTY_DIRS` rather than carrying a duplicate list (obligation 5)
- [x] T045 [P] [US3] Assert in `tests/unit/test_portability_audit.py` that it never modifies content, never classifies by path prefix, and offers no suppression mechanism (the three prohibitions)
- [x] T046 [P] [US3] Add a contract assertion that every verb id in `.seshat/kit-source.yaml` has a corresponding bundle file in both bundles (FR-015), so the compass and the bundle cannot drift again

### Transform

- [x] T047 [US3] Implement `portability-audit-v1` in `scripts/export_agent_bundles.py` as a gate that permits or fails, never rewrites
- [x] T048 [US3] Add `portability-audit-v1` to the allowed-transform set and to `policy.transforms` in the generated allowlist
- [x] T049 [US3] Run the export and confirm it **fails**, naming the outstanding findings — the transform must reject before it permits

### Canonical rewrites

- [x] T050 [US3] Rewrite the `templates/` references across `first-hour-compass`, `retail-onboard-table`, `retail-discover-portfolio`, `source-mapping` and `retail-validate`, applying FR-017 per reference by intent
- [x] T051 [US3] Rewrite the `docs/worked-examples` references in `retail-orchestrate`, `first-hour-compass`, `retail-onboard-table` and `source-mapping`
- [x] T052 [US3] Rewrite the `specs/` references in `retail-orchestrate`, `business-knowledge-interview`, `retail-build-warehouse` and `retail-govern`
- [x] T053 [US3] Rewrite the `.claude/skills/` references in `retail-orchestrate`, `retail-onboard-table` and `retail-build-warehouse`
- [x] T054 [US3] Rewrite the remaining `docs/roadmap`, `docs/quality/`, `scripts/`, `src/seshat/` and `tests/` references in `retail-onboard-table`, `retail-discover-portfolio`, `kpi-contract-builder`, `retail-validate` and `retail-govern`
- [x] T055 [US3] For every rewrite, verify both contexts — unchanged behaviour in this repository, and every instructed path resolvable in a `seshat init-project` workspace — recording each in `specs/138-agent-driven-bundle/evidence/portability-findings.md`
- [x] T056 [US3] Diff each rewritten `.claude/skills/<verb>/SKILL.md` against its pre-rewrite text and confirm no hard stop, gate or refusal was weakened, reworded or dropped (FR-019)

### Ship

- [x] T057 [US3] Flip `ships: true` and `ship_classification: compass-verb` for the ten verbs in `docs/capabilities/capabilities.yaml`
- [x] T058 [US3] Regenerate the allowlist and both bundles, and commit the generated output
- [x] T059 [US3] Record the post-story routing cost in `specs/138-agent-driven-bundle/evidence/routing-cost.md` and confirm it is at or under the ceiling from T006
- [ ] T060 [US3] **OPERATOR-RUN, still open** -- Verify in a workspace with no Seshat development checkout that all ten `.seshat/kit-source.yaml` verbs load and every hard stop still stops, recording the session evidence in `specs/138-agent-driven-bundle/evidence/us3-acceptance.md`

**Checkpoint**: the bundle no longer contradicts its own compass.

---

## Phase 6: User Story 4 — remaining consumer capabilities ship (Priority: P4)

**Goal**: a fresh install carries every consumer-facing skill and no
development-only or specification-workflow skill.

**Independent test**: enumerate installed skills in a fresh workspace; the set is
exactly the consumer product.

**Depends on US2; sequenced after US3.**

- [ ] T061 [US4] Flip `ships: true` and `ship_classification: consumer-capability` for the remaining consumer skills in `docs/capabilities/capabilities.yaml`
- [ ] T062 [US4] Run the export and resolve any portability findings the new skills raise, by canonical rewrite only
- [ ] T063 [US4] Regenerate the allowlist and both bundles and commit the generated output
- [ ] T064 [US4] Record the post-story routing cost; if it exceeds the ceiling, **fail** — do not pass with a note, and do not split the distribution without a recorded measurement justifying it (FR-021a)
- [x] T065 [US4] Verify in a fresh workspace that no development-only or specification-workflow skill is present
- [x] T066 [US4] Prove exclusion is caused by the recorded classification, not a name pattern: temporarily reclassify one development-only skill as consumer-facing, confirm it *would* ship, then revert
- [x] T067 [US4] Confirm skill bodies still load on demand and no story made a body resident (FR-021b)

**Checkpoint**: a fresh install equals this repository for the consumer product.

---

## Phase 7: User Story 5 — published claims match the artifact (Priority: P5)

**Goal**: every published claim is reproducible from evidence captured against
the bundles as shipped.

**Depends on US1–US4.**

- [x] T068 [US5] Run `seshat agent verify --target claude` against the regenerated bundle and capture the evidence
- [x] T069 [US5] Run `seshat agent verify --target codex` against the regenerated bundle and capture the evidence
- [ ] T070 [US5] Capture external acceptance evidence for both harnesses per `scripts/external_agent_acceptance.py`
- [x] T071 [US5] Update `docs/install/support-matrix.md` so every changed row states what was actually exercised against the new contents, carrying no earlier acceptance claim forward
- [x] T072 [US5] Update `docs/install/agent-install.md` to list the skills the bundles now carry and the wiring that is now automatic
- [x] T073 [US5] Confirm no version value was changed by any story (FR-024a) and that no tag, release or catalog submission was performed (FR-024, FR-024b)

---

## Phase 8: Polish & cross-cutting

- [x] T074 [P] Add a `spec-138-implemented` claim to `docs/quality/status-claims.yaml` naming the delivered artifacts, per the spec status convention
- [x] T075 [P] **DEVIATED (see spec.md):** Status set to `partially implemented`, not `implemented` -- US1, US4 and the external half of US5 are outstanding, so the stronger value would be a false claim. Original text: Update `specs/138-agent-driven-bundle/spec.md` Status to `implemented`, moving the previous text verbatim into a `**Status history**:` line
- [ ] T076 [P] **DELIBERATELY NOT DONE -- the fence stays on spec 138, which is not finished.** Move the SPECKIT fence in **both** `CLAUDE.md` and `AGENTS.md` to the next active plan, keeping the two bodies identical
- [x] T077 Run the whole-feature regression from `quickstart.md`: export, `git status --porcelain`, `seshat check`, `kit-lint`, `doctor`, `pytest tests/contract`
- [x] T078 Run `analyze_change_set` before pushing — a required delta code-health check fails PRs on newly-introduced smells even when every GitHub job is green

---

## Dependencies

```text
Setup (T001-T003)
   │
   ├────────────────────────────────┐
   ▼                                ▼
Foundational (T004-T006)        US1 (T007-T023)   ← no dependency, MVP
   │                                │
   ▼                                │
US2 (T024-T041)                     │
   │                                │
   ▼                                │
US3 (T042-T060)                     │
   │                                │
   ▼                                │
US4 (T061-T067)                     │
   └────────────┬───────────────────┘
                ▼
         US5 (T068-T073)
                ▼
         Polish (T074-T078)
```

- **US1 is independent** of the entire US2→US3→US4 chain and may be delivered
  first, last, or alone.
- **US3 and US4 must fail closed without US2**, not degrade.
- **US5 is a merge point** — it can only make truthful claims once contents are
  final.
- **Only one story may be in implementation at a time** across specs 137 and 138
  (FR-026). The graph shows merge safety, not concurrent work.

## Parallel opportunities

- **Setup**: T002, T003 in parallel after T001.
- **US1 tests**: T011–T014 all touch different test files.
- **US2 tests**: T024–T029 are assertions in one new file — parallel to author,
  serial to commit.
- **US3 tests**: T042–T046 in parallel.
- **US3 rewrites**: T050–T054 touch different skill files and can proceed in
  parallel, but T055–T056 verify all of them and must follow.
- **Polish**: T074–T076 in parallel; T077–T078 must run last.

## Implementation strategy

**MVP = User Story 1 alone.** It has no dependencies, is merge-safe in any order,
and delivers the feature's headline value on its own: the documented governed
loop starts actually working on install. If nothing else ships, that ships.

**Then the chain.** US2 is a zero-payload refactor whose acceptance is that
nothing changed — the safest possible way to widen a fail-closed governance gate.
US3 is where the bundle stops contradicting its compass. US4 completes the
consumer surface. US5 makes the published claims true again.

**Stop conditions.** T010 halts US1 on a negative research result rather than
working around it. T064 halts US4 if the routing-cost ceiling is exceeded. Both
are reported to the owner, not resolved by the agent.

## Task counts

| Phase | Tasks |
|---|---|
| Setup | 3 |
| Foundational | 3 |
| US1 (P1, MVP) | 17 |
| US2 (P2) | 18 |
| US3 (P3) | 19 |
| US4 (P4) | 7 |
| US5 (P5) | 6 |
| Polish | 5 |
| **Total** | **78** |
