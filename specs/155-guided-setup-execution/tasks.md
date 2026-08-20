# Tasks: Guided setup execution (derived plan -> approved provisioning)

**Feature**: `specs/155-guided-setup-execution/` | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md) | **Contract**: [contracts/guided-setup-bridge.md](./contracts/guided-setup-bridge.md)

**Prerequisites SATISFIED**: spec 153 implemented (PR #682) and spec 154 / issue
#671 implemented (`b456577c`, PR #678). This feature consumes the strong committed
approval and the shipped derived plan; it re-implements neither.

**Spec status**: Draft. Phases 0 and 1 (research and design) are complete;
implementation phases below wait on ratification, per this repo's practice of not
building against an unratified spec.

**Progress**: Phase 0 and Phase 1 done (10 of 53). Implementation not started.

TDD order: the failing test comes before the code. A task is done only when its
test was seen RED, then GREEN. Nothing is marked done that was not observed.

## Phase 0 -- Research (DONE, recorded in research.md)

- [x] **T001** R1 -- the installer seam. Settled: `installer.plan`/`apply` select
  solely via `profile_components(profile)`, and everything downstream already
  consumes `tuple[Component, ...]`, so an optional component-set input is the
  additive shape. A synthetic profile in `PROFILES` was rejected -- it would leak
  a per-project value into catalog truth and into `--profile`'s choices.
- [x] **T002** R2 -- environment and lock. Settled: only PyPI components are
  env-scoped; every component in the shipped projection belongs to exactly ONE base
  profile (measured with `profiles_for`), so a derived scope installs into each
  component's own base-profile env and invents no isolation target. This is what
  makes reuse (FR-018) achievable rather than aspirational.
- [x] **T003** R2b -- lock merging is DERIVED-ONLY. Symmetric merging would change
  the profile path's observable behavior, which spec 144 FR-010/FR-011 protect; it
  is owner decision 3's escalation, not a silent choice.
- [x] **T004** R3 -- CLI shape. Settled: an additive opt-in selector on the
  existing `seshat integrations setup` verb. `--profile` keeps its choices and
  `DEFAULT_PROFILE` keeps its value; the three existing gates stay independent.
- [x] **T005** R4 -- the approval gate needs NO change. The CLI already derives the
  requested scope from the plan's rows, never argv, and `approval.evaluate` takes
  no boolean. Feeding it a derived scope is the whole integration.
- [x] **T006** R5/R6 -- readiness comes from `outcome.discovery` unioned with the
  installer's action set, and the bridge MUST be a new module: two shipped spec-153
  tests assert `derivation.py` contains no `apply_profile(`, `write_lock(`,
  `install(`, `approved`, `authorize`, `--yes` call site.

## Phase 1 -- Design (DONE)

- [x] **T007** `data-model.md`: `DerivedScope` (ordered ids, per-capability
  exclusion reason, blockers, unsupported), `CapabilityStatus` (the eight
  agent-facing facts), `GuidedSetupResult`. All computed; none persisted.
- [x] **T008** `contracts/guided-setup-bridge.md`: ten invariants plus the mutation
  cases that must change -- and must not change -- when the catalog, projection,
  declines, or approval move.
- [x] **T009** `quickstart.md`: the five-step journey with the refusal text and the
  installed-but-not-verified case shown, not described.
- [x] **T010** `plan.md`: design invariants mapped one-to-one to FR-002..FR-022,
  verification strategy, and the five known risks.

## Phase 2 -- Projection and the proposed change set (US1, P1)

- [ ] **T011** [RED] A Postgres + Power BI project -> the derived scope is exactly
  the projection of Database Connectivity and Power BI Integration, in
  `tests/unit/test_guided_setup_scope.py`. (FR-002, US1 AS1)
- [ ] **T012** [RED] The derived scope is a STRICT SUBSET of
  `PROFILES[DEFAULT_PROFILE]`, computed from the catalog at test time -- never a
  hardcoded id list that stops matching when the catalog changes. (SC-002)
- [ ] **T013** [RED] A `not-required` capability contributes zero components, and
  the exclusion reason is recorded as `not-required`. (FR-003, US1 AS1, B)
- [ ] **T014** [RED] A declined `recommended` capability contributes zero
  components and does not stop the remaining scope being proposed. (FR-003, US1
  AS4, D)
- [ ] **T015** [RED] A declined `required` capability leaves the plan blocked, keeps
  strength `required`, stays listed, and carries a next action. (FR-005, US1 AS5, E)
- [ ] **T016** [RED] A satisfied capability contributes zero install actions while
  still rendering as satisfied. (FR-004, US1 AS3, C)
- [ ] **T017** [RED] An `optional` capability is presented and contributes nothing.
  (FR-003, owner decision 2)
- [ ] **T018** [RED] A capability with `undetermined` evidence contributes nothing,
  and the missing evidence is named. (FR-003)
- [ ] **T019** [RED] A needed capability projecting to no catalog component is
  reported `unsupported` -- never dropped, never reported satisfied. (edge case)
- [ ] **T020** [RED] Every exclusion carries WHICH reason it was. A test that only
  counts components cannot tell a correct exclusion from an accidental one.
- [ ] **T021** [RED] Determinism, asserted on ORDER as well as membership: the same
  evidence, catalog, declines, and discovery state twice -> identical tuple.
  (FR-006, SC-007)
- [ ] **T022** [RED] Four scope-widening attempts, one assertion each -- an argv
  component id, a package name, a profile name, and a capability request outside
  derived need -- leave `component_ids` byte-identical. (FR-007, US1 AS6, SC-006)
- [ ] **T023** [RED] Planning writes nothing and makes no network call, asserted
  against a read-only fixture and the injected resolver seam. (FR-008, US1 AS7)
- [ ] **T024** [GREEN] Implement the projection and `DerivedScope` in
  `src/seshat/integrations/guided_setup.py`. `derivation.py` is NOT edited.
- [ ] **T025** [RED] The normal presentation shows capability name, strength,
  proposed action, and a proposed-change count, and contains no package, MCP, npm,
  or runtime identifier and no install command -- asserted against coordinates
  drawn FROM the catalog at test time. (FR-009, US1 AS2, SC-001)
- [ ] **T026** [RED] The advanced path reports provider, catalog component,
  resolved coordinate/version, and verification basis, each sourced from the
  control plane rather than recomputed. (FR-010, SC-001)
- [ ] **T027** [GREEN] Implement both presentations in `guided_setup.py`.
- [ ] **T028** [RED] The empty-but-unblocked scope renders "nothing to do" and
  demands no approval. (edge case)

**Independent test for US1**: plan two projects of different shape and prove the
proposed scopes differ, that every exclusion is attributable, that the rendering
names no package, and that the run wrote nothing and reached no network.

## Phase 3 -- Authorization and delegated execution (US2, P2)

- [ ] **T029** [RED] With no committed approval, provisioning refuses with EVERY
  caller-controlled signal supplied at once -- `--apply`, `--yes`, `--json`, piped
  stdin, a simulated TTY, and an agent instruction asserting approval -- installing
  nothing, writing nothing, calling no network, in
  `tests/unit/test_guided_setup_authorization.py`. (FR-012, US2 AS1, SC-005, F)
- [ ] **T030** [RED] An approval covering A+B does not authorize a derived scope of
  A+B+C, and the refusal names both scopes. (FR-013, US2 AS2, SC-006, G)
- [ ] **T031** [RED] A committed shape-valid `governance` approval covering the
  exact derived scope permits execution, still subject to `--refresh`, workspace
  validation, and compatibility policy. (FR-012, US2 AS3, H)
- [ ] **T032** [RED] A superset approval authorizes a subset derived scope; a
  subset approval refuses. (edge case)
- [ ] **T033** [RED] A blocked derived plan refuses BEFORE authorization is
  consulted, and no approval clears the blocker. (FR-005, US2 AS5)
- [ ] **T034** [RED] Every refusal carries a categorical reason and a next action in
  both the human-readable and machine-readable paths. (FR-014, US2 AS6, SC-008)
- [ ] **T035** [RED] A `not-required` capability's components are never installed,
  configured, registered, or resolved under a valid approval. (FR-021, US2 AS4, B)
- [ ] **T036** [GREEN] Wire the derived scope through `approval.evaluate` and into
  `installer.apply` in `guided_setup.py` and
  `src/seshat/cli/commands/integrations.py`.
- [ ] **T037** [GREEN] Add the optional component-set selection to
  `installer.plan`/`installer.apply`, defaulting to today's profile behavior.
- [ ] **T038** [GREEN] Add the additive opt-in selector in
  `src/seshat/cli/parser_integrations.py`.
- [ ] **T039** [RED] Each component installs into its OWN base-profile environment,
  asserted through the injected runner rather than a log line. (FR-015, R2)

**Independent test for US2**: with one derived scope, run with no approval, a
narrower approval, an exact approval, and a superset approval -- refuse, refuse,
execute, execute -- with every caller-controlled signal present each time.

## Phase 4 -- Honest results, retry, and the agent status (US3, P3)

- [ ] **T040** [RED] Installation that completes but fails verification leaves the
  capability NOT ready, names the failed check, and states a next action, in
  `tests/unit/test_guided_setup_results.py`. (FR-016, US3 AS1, SC-008, I)
- [ ] **T041** [RED] One component succeeding and another failing under one approved
  scope: both stay individually distinguishable, the affected capability is not
  ready, the run is not successful overall, and the unaffected capability's status
  is untouched. (FR-017, US3 AS2, SC-009, J)
- [ ] **T042** [RED] A retry of a materially unchanged approved scope reinstalls
  zero already-satisfied components -- asserted on the runner's calls -- and
  requires no new approval. (FR-018, US3 AS3, SC-010, K)
- [ ] **T043** [RED] A narrower derived apply after a broader profile-based run
  preserves the out-of-scope entries in the existing state record and does not
  label the derived scope as a curated profile. (FR-019, US3 AS4, SC-011)
- [ ] **T044** [RED] The machine-readable status carries all EIGHT facts --
  capability, strength, satisfied, needs-setup, proposed action, blocker, approval
  required and whether met, post-execution status -- with no package-specific
  reasoning required. (FR-011, US3 AS5, SC-012, L)
- [ ] **T045** [GREEN] Implement `CapabilityStatus`, `GuidedSetupResult`, and the
  status renderers in `guided_setup.py`, unioning the installer action set with the
  discovery vocabulary.

**Independent test for US3**: force one verification failure alongside one success
under a single approved scope, then re-run -- and assert the capability status, the
run-level result, and the reinstall count separately.

## Phase 5 -- Boundary and compatibility sweeps

- [ ] **T046** [RED] Contract test for the ten bridge invariants in
  `tests/contract/test_guided_setup_bridge.py`, including that `derivation.py`
  still contains no execution or approval call site -- if this feature ever edits
  that file, spec 153's proof must fail loudly. (contracts/)
- [ ] **T047** [RED] `DEFAULT_PROFILE` keeps its value; `--profile` keeps its
  `PROFILE_NAMES` choices; a profile-based run's selection, JSON shape, and exit
  codes are unchanged. (FR-020, SC-013)
- [ ] **T048** [RED] No output -- plan, refusal, evidence, or JSON -- contains a
  secret, credential, connection string, or token; and no assertion keys on a
  Windows literal. (FR-022, SC-014)

## Phase 6 -- Gates

- [ ] **T049** `ruff format --check src/ tests/` and `ruff check src/ tests/`.
- [ ] **T050** `pytest -m unit` green, with the feature's new tests counted against
  the session baseline. CI's unit job runs WITHOUT app extras.
- [ ] **T051** `seshat check` exit 0.
- [ ] **T052** Measure changed files with CodeScene if a working token or CLI is
  available. If not, state the limitation and what WAS measured instead -- never
  claim a health verdict that was not run (the spec-153 T046 precedent).
- [ ] **T053** Diff contains no unrelated file, and no committed provisioning
  approval or decline is added by this feature.

## Dependencies

- Phase 2 (US1) depends only on Phases 0-1. It is the MVP: a read-only,
  capability-oriented change plan that installs nothing.
- Phase 3 (US2) depends on Phase 2 producing the scope an approval binds to.
- Phase 4 (US3) depends on Phase 3 producing an execution to report on.
- Phase 5 can run alongside Phases 2-4; T046 is most useful written early, since it
  is what stops the bridge drifting into `derivation.py`.
- Phase 6 last.

## Parallel opportunities

- T011-T023 are independent assertions over the same fixture pair and can be
  written in parallel before T024.
- T025/T026 (presentation) are independent of T011-T023 (scope) once `DerivedScope`
  exists.
- T029-T035 are independent of one another; each builds its own approval fixture.
- T046-T048 touch different test files and are fully parallel.

## Implementation strategy

Ship US1 alone first: it delivers the visible value -- the user sees that the
project needs two capabilities, not the historical bundle -- while installing
nothing and needing no approval. US2 adds authorized execution. US3 makes failure
and repetition trustworthy. Each phase is independently demonstrable.

## Out of scope

- Editing `derivation.py`, the catalog, the resolver, the compatibility policy, the
  approval gate, or the discovery surface beyond the additive component-set input.
- Changing `DEFAULT_PROFILE`, or making derived selection the default.
- An opt-in path for provisioning `optional` capabilities.
- Symmetric (profile-path) lock merging, absent an owner ruling.
- A second installer, registry, verifier, approval mechanism, or authoring path.
