# Implementation Plan: Guided setup execution (derived plan -> approved provisioning)

**Branch**: `claude/spec-155-guided-setup-pzrctn` | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/155-guided-setup-execution/spec.md`

**Prerequisites: BOTH SATISFIED.** Spec 153 is implemented on `main` (PR #682) and
spec 154 / issue #671 is implemented (`b456577c`, PR #678). The authority this
feature consumes is the strong, committed, named-human one; the derived plan it
consumes is the shipped one.

## Summary

Connect three shipped things that do not currently touch: the derived capability
plan, the committed provisioning approval, and the installer. The delta is one new
module plus one additive selection path:

1. project a derived plan into the exact existing catalog component set;
2. present that as a capability-oriented change plan and an agent-readable status;
3. hand the scope to the existing approval gate, then to the existing installer,
   and let existing verification decide readiness.

Nothing about derivation, authorization, resolution, compatibility, installation,
discovery, or state recording is redefined. `DEFAULT_PROFILE` and every existing
`--profile` run are untouched.

## Technical Context

**Language/Version**: Python 3.13 (repo floor 3.11)

**Primary Dependencies**: none added. Reads `seshat.integrations.derivation`
(derived plan + projection), `seshat.integrations.approval` (`evaluate`),
`seshat.integrations.installer` (`plan`, `apply`), `seshat.integrations.catalog`
(`profiles_for`, `component`), `seshat.integrations.discovery`.

**Storage**: none new. The machine-local lock under `.seshat/integrations/` stays
the only provisioning state store, and no committed artifact is added.

**Testing**: pytest. Unit tests for projection, eligibility, scope determinism,
and status assembly; contract tests for the boundary invariants; the installer and
approval paths are exercised through their existing injected seams (`runner`,
`resolvers`, discovery runner) so no test spawns a real clone, venv, or network
call.

**Target Platform**: cross-platform CLI. CI is Linux -- no assertion may key on a
Windows literal (`.exe`, backslash paths).

**Project Type**: CLI within an existing library.

**Performance Goals**: N/A. Planning reads committed text and machine-local state.

**Constraints**: planning is network-free and write-free (FR-008); execution keeps
every existing gate (`--refresh` for exact coordinates, `--apply` for writes,
workspace validation, isolation); the base install stays usable with no optional
provider present.

**Scale/Scope**: 1 new module, 1 additive CLI selector, 1 optional keyword on two
existing installer entry points, ~25 tests. No new verb, no new dependency, no new
committed artifact.

## The seam

`installer.plan()` / `installer.apply()` take `profile: str` and call
`profile_components(profile)` -- the single selection input. Everything downstream
already consumes `tuple[Component, ...]`. So the change is to let a component set
be supplied directly, and to add a bridge upstream that produces one from the
derived plan.

Three facts from Phase 0 shape this and are easy to get wrong:

- **The bridge must NOT live in `derivation.py`.** Two shipped spec-153 tests read
  that file as source text and assert it contains no `apply_profile(`,
  `write_lock(`, `install(`, `approved`, `authorize`, `--yes` call site. Those
  assertions are the mechanical proof of spec 153 FR-017 and spec 153 FR-018.
  A bridge placed there turns them red; a separate module keeps both specs
  testable.
- **A derived scope installs into each component's OWN base profile environment**,
  not a new one. Every component in the shipped projection belongs to exactly one
  base profile (measured with `profiles_for`), and only PyPI components are
  environment-scoped at all. Reusing those environments is what makes "do not
  reinstall what is already satisfied" true instead of aspirational.
- **The approval gate needs no change.** The CLI already computes the requested
  scope from the plan's rows, never from argv, and passes it to
  `approval.evaluate`. Feeding it a derived scope is the whole integration.

## Constitution Check

*GATE: passes. Re-checked after Phase 1 design: still passes.*

| Principle | Assessment |
|---|---|
| I. Agent-First, Gate-Enforced | Honored. The agent may plan and request; the committed approval and the installer's own gates remain the authority. |
| II. Depend, Never Fork | Honored, and central: no installer, resolver, verifier, registry, or approval path is reimplemented. The feature is entirely composition. |
| V. Agent Stops at Judgment Calls | Honored. A blocked plan refuses; a declined `required` capability is never downgraded to clear the block; an unsupported capability is reported, not guessed at. |
| VI. Defaults Then Deviations | Honored. Derived selection is an opt-in deviation; the profile default is the untouched default. |
| VIII. Static-First, Live Deferred | Honored. Planning reads committed text and machine-local state only -- no DB, and no network without `--refresh`. |
| IX. Secrets and Reproducibility | Honored. FR-022 forbids any secret in any output; the derived scope is deterministic from committed evidence (FR-006). |

No principle weakened. No amendment required by this plan as designed -- see
Complexity Tracking for the one place an amendment could become necessary.

## Project Structure

### Documentation (this feature)

```text
specs/155-guided-setup-execution/
├── plan.md              # this file
├── spec.md              # ratifiable specification (22 FRs, 14 SCs)
├── research.md          # Phase 0 -- R1..R6, decisions and rejected alternatives
├── data-model.md        # Phase 1 -- DerivedScope, CapabilityStatus, GuidedSetupResult
├── quickstart.md        # Phase 1 -- the journey as the user sees it
├── contracts/
│   └── guided-setup-bridge.md   # 10 invariants + mutation cases
└── checklists/
    └── requirements.md  # specification quality checklist
```

### Source Code (repository root)

```text
src/seshat/integrations/
├── derivation.py        # spec 153 -- UNCHANGED by this feature
├── guided_setup.py      # NEW: projection -> scope -> status -> delegation
├── approval.py          # spec 154 -- unchanged; called
├── installer.py         # spec 144 -- optional component-set selection added
├── catalog.py           # unchanged; read
└── discovery.py         # unchanged; read

src/seshat/cli/
├── commands/integrations.py   # additive derived-selection path
└── parser_integrations.py     # additive opt-in selector

tests/
├── unit/        # projection, eligibility, determinism, status assembly
└── contract/    # the ten bridge invariants
```

**Structure Decision**: one new module beside the surfaces it composes, so the
import direction stays one-way (bridge -> derivation/approval/installer) and no
existing module gains a dependency on the bridge.

## Phase 0 -- Research

Complete. See [research.md](./research.md). Six questions, all resolved against
`main`: the installer seam (R1), the environment and lock question (R2), the CLI
shape (R3), whether the approval gate needs changing -- it does not (R4), what
decides satisfied and ready (R5), and where the bridge may live (R6).

Two findings changed the design rather than confirming it: the derivation purity
tests (R6) and the per-component base-profile environment (R2).

## Phase 1 -- Design

**data-model.md**: `DerivedScope` (ordered component ids + why each capability
contributed or did not + blockers + unsupported), `CapabilityStatus` (the eight
agent-facing facts), `GuidedSetupResult` (scope + statuses + the existing outcome).

**contracts/guided-setup-bridge.md**: ten invariants and their mutation cases --
what must change when the catalog, the projection, a decline, or an approval
changes, and what must not.

**quickstart.md**: the five-step journey, capability-oriented throughout, with the
refusal text and the not-ready-after-install case shown rather than described.

### Design invariants (each maps to a spec FR)

- The scope is projected through the EXISTING mapping and catalog; the bridge owns
  no component, coordinate, or version. (FR-002)
- `not-required`, declined, satisfied, `optional`, and `undetermined` capabilities
  contribute nothing. (FR-003, FR-004)
- A declined `required` capability blocks and keeps its strength. (FR-005)
- A needed capability with no catalog component is reported unsupported -- never
  dropped, never satisfied. (FR-023)
- An all-satisfied project reports "no change proposed" and demands no approval.
  (FR-024)
- Same evidence + catalog + declines + discovery state -> same ordered scope.
  (FR-006)
- No argv value widens the scope. (FR-007)
- Planning writes nothing and reaches no network. (FR-008)
- The normal presentation names no package, MCP server, npm package, runtime, or
  install command. (FR-009)
- Provider, component, resolved coordinate, and verification basis are available
  on request, read from the control plane. (FR-010)
- The status carries all eight agent-facing facts. (FR-011)
- Authority is the committed approval and nothing else; intent, prompts, stdin,
  JSON mode, and agent instructions confer none. (FR-012)
- A materially widened scope is not authorized by the earlier approval, and the
  refusal names both scopes. (FR-013)
- Refusal is fail-closed with a categorical reason and a next action. (FR-014)
- Execution delegates; no second installer, resolver, verifier, or state store, and
  no existing precondition removed. (FR-015)
- Readiness comes from verification, never from install success. (FR-016)
- Partial outcomes stay individually distinguishable. (FR-017)
- An unchanged approved scope reuses satisfied components and needs no new
  approval. (FR-018)
- A derived run preserves out-of-scope recorded state and never claims a curated
  profile. (FR-019)
- `DEFAULT_PROFILE` and existing profile behavior are untouched. (FR-020)
- No component is provisioned for sharing a profile with a needed one. (FR-021)
- No secret in any output. (FR-022)

## Verification Strategy

1. **The scope must actually be narrower.** Assert the derived scope for a
   Postgres + Power BI project is a strict subset of `PROFILES[DEFAULT_PROFILE]`,
   computed from the catalog at test time. A hardcoded expected list would stop
   being meaningful the moment the catalog changes.
2. **Exclusion must be attributable.** For each excluded capability, assert WHY
   (`not-required` / `declined` / `satisfied` / `optional` / `undetermined`) -- a
   test that only counts components cannot tell a correct exclusion from an
   accidental one.
3. **Scope-widening attempts need a real test each.** argv component id, package
   name, profile name, and a capability request outside derived need: each must
   leave `component_ids` byte-identical.
4. **Authority needs a negative test with every signal at once.** `--apply`,
   `--yes`, `--json`, piped stdin, and a simulated TTY together, with no committed
   approval: refuse, write nothing, call no network.
5. **"Not ready after install" must be reachable**, not argued: force a
   verification failure for one component while another succeeds, and assert the
   capability status and the run-level result separately.
6. **Reuse must be observed, not assumed.** Install a component under a
   profile-based run, then run the derived scope and assert the installer was asked
   to install nothing for it -- through the injected runner, so the assertion is on
   behavior rather than on a log line.
7. **Determinism must be asserted on order**, not just membership.
8. **Reachability is its own assertion.** FR-001 is the requirement this feature
   exists for, and it is satisfied only when the derived plan is obtainable through
   the normal CLI journey -- not when a library function exists. Assert the journey,
   and assert the derived path's exit codes distinguish "needs setup" from "nothing
   to do" (US1 AS7).
9. **The boundary invariants get contract tests**, including the one that keeps
   `derivation.py` free of execution call sites -- if this feature ever edits that
   file, spec 153's proof should fail loudly.

## Known Risks

1. **Reinstall-through-a-new-environment is the highest-value mistake to avoid.**
   Giving the derived scope its own isolation directory looks tidy and quietly
   breaks FR-018/SC-010: `_is_installed` would not see the previous profile run's
   venv. Phase 0 R2 settles this -- per-component base-profile environments -- and
   verification item 6 is what keeps it honest.
2. **The lock is whole-file today.** Derived-only merging is additive and stays
   inside FR-019; symmetric merging would change the profile path's observable
   behavior and needs an owner ruling first (owner decision 3). Getting this
   backwards would amend a ratified contract by accident.
3. **Provider names leak through reasons and errors.** Spec 153 already keeps
   reason text capability-first, but a refusal or a failure detail assembled here
   could paste a component id into the normal presentation. The advanced path
   exists precisely so the normal one does not need it.
4. **Optional capabilities invite an opt-in flag.** Adding one would create the
   authoring path the spec excludes; owner decision 2 records why they stay
   presented-only.
5. **`SetupOutcome.profile` is user-visible in both renderers.** A derived run must
   report its selection basis truthfully without breaking the JSON shape spec 144
   FR-010 protects -- a field's value may change; its presence may not.

## Complexity Tracking

No new dependency, module count beyond one, verb, flag family, registry, or
committed artifact. The single place this plan could require an amendment is
symmetric lock merging (risk 2) -- if a reviewer wants it, it is an owner decision
recorded as an amendment to spec 144 FR-011, not a quiet change made under this
feature's cover.
