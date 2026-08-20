# Phase 0 Research: guided setup execution (spec 155)

Every question below was answered by reading `main` at `88a194c`, and several
answers changed the design. Where a finding contradicted the first design guess,
the guess is recorded too -- a reader who does not know what was rejected will
re-propose it.

## R1 -- Where does a derived component set enter the installer?

**Decision.** Add an OPTIONAL component-set selection to the existing planner and
installer entry points, and leave profile selection exactly as it is. The bridge
module resolves the derived scope and passes it in; the planner keeps owning
resolution, compatibility, install, and lock.

**Findings.** `installer.plan()` and `installer.apply()` both take
`profile: str = DEFAULT_PROFILE` and immediately call
`profile_components(profile)` -- that single call is the ONLY selection input.
Everything downstream (resolution, policy, install, lock, discovery) already
operates on a `tuple[Component, ...]`, so a component set is the shape the
pipeline natively consumes. Nothing else in either function reads `profile`
except the env/label/lock concerns covered by R2.

**Alternatives rejected.**
- *A synthetic "derived" profile registered into `PROFILES`.* Rejected: `PROFILES`
  is catalog truth and `PROFILE_NAMES` derives the CLI's `--profile` choices from
  it, so a per-project synthetic entry would leak a project-specific value into a
  global registry and into `--profile`'s help text -- a second registry by another
  name (FR-002).
- *A separate mini-installer in the bridge.* Rejected outright by FR-016.

## R2 -- Which isolation environment does a derived scope install into, and what happens to the lock?

**Decision.** Each component installs into the environment its OWN base profile
already defines; the derived scope invents no new isolation target. The lock is
MERGED for derived runs only -- previously recorded components outside the derived
scope are carried forward, entries in scope are overwritten by what landed. The
outcome's selection label reports the derived basis rather than naming a curated
profile.

**Findings, and why this matters more than it looks.**
- Only PyPI components are environment-scoped: `_is_installed` resolves a venv
  interpreter under `_profile_env(profile)` for PyPI, while GitHub skills
  (`SKILLS_DIR/<id>`), MCP registrations (`NODE_DIR/<id>/.seshat-installed`), and
  bundled skills use profile-INDEPENDENT paths. So the environment question
  applies to exactly the PyPI subset.
- Every component in the shipped capability projection belongs to exactly ONE base
  profile: `connectorx` -> `analytics-core`; `powerbi-modeling-mcp` and
  `fabric-skills` -> `powerbi-fabric`; `dbt-core`, `dbt-postgres` ->
  `transformation`; `dagster`, `seshat-dagster-adapter` -> `orchestration`
  (measured via `profiles_for`, not assumed). There is therefore no ambiguity to
  resolve and no need for a derived env.
- This is what makes FR-018/SC-010 achievable. A derived run that installed into
  its own env would find `_is_installed` false for a component a previous
  `analytics-full` run had already installed, and would reinstall it -- the exact
  "reuse existing valid setup state" failure the spec forbids. Reusing the base
  profile's env makes prior installs visible for free.
- `_profile_label(item)` already derives a row's label from `profiles_for(item.id)`
  rather than from the requested profile, so per-component labels stay truthful
  with no change.
- `write_lock` replaces the whole document, and `build_lock` records only what
  landed this run. Note this clobbering is PRE-EXISTING across profiles today (an
  `analytics-core` apply already drops an earlier `analytics-full` lock's other
  entries), so FR-019 is a new guarantee for the derived path, not a bug fix to
  the profile path.

**Alternatives rejected.**
- *A dedicated derived environment.* Rejected: breaks reuse (above), duplicates
  installs on disk, and would make the same component "installed" in one env and
  absent in another.
- *Merging the lock for every run, profile runs included.* Rejected here: it would
  change observable behavior of the profile path, which spec 144 FR-010's
  unamended clauses and FR-011 protect. Derived-only merging is additive. If a
  reviewer prefers symmetric merging, that is an amendment and needs the owner
  ruling that spec 155 owner decision 3 describes -- it is not a silent choice.

**Consequence for owner decision 3.** The environment half is settled by evidence
(reuse the base profile's env; no schema or layout change). Only the lock-merge
half remains a judgment call, and it stays inside FR-019's stated behavior.

## R3 -- What CLI shape keeps the profile default untouched?

**Decision.** An additive opt-in selector on the existing `seshat integrations
setup` verb. `--profile` keeps its `PROFILE_NAMES` choices and its
`DEFAULT_PROFILE` default; passing the derived selector instead selects the
derived scope. No new verb, and no change to any existing flag's behavior.

**Findings.** `DEFAULT_PROFILE` is exported in `integrations_setup.__all__` and is
the default of three public signatures; spec 144 FR-006 protects it as a value,
and spec 153 owner decision 1 already ruled that displacing the default needs an
explicit amendment. The three existing gates are independent and must stay so:
`--refresh` is the network gate, `--apply` the write gate, `--yes` suppresses the
prompt only. The derived selector is a fourth, orthogonal concern: it changes WHAT
is selected, never whether anything is resolved, written, or authorized.

**Alternatives rejected.**
- *A new top-level verb.* Rejected: the journey, the workspace validation, the
  three gates, and the renderers already exist on this verb; a second verb would
  duplicate all four.
- *Making derived selection the default now.* Rejected by owner decision 1.

## R4 -- Does the approval gate need any change?

**Decision.** None. The bridge feeds it the derived component ids and consumes its
verdict.

**Findings.** `cli/commands/integrations.py` already computes the requested scope
as `_requested_components(outcome)` -- read from the plan's own rows, explicitly
"derived from the plan, never from argv" -- and passes it to
`approval.evaluate(root, components)`. `evaluate` takes no boolean, reads
`contracts/provisioning-approvals.yaml` at HEAD through
`is_tracked_and_clean` + `committed_text`, requires the `governance` class, and
returns a categorical `ApprovalVerdict` with `next_action`. A derived plan
produces rows exactly as a profile plan does, so scope binding, the
superset-authorizes-subset rule, the standing-approval lifetime, and every
refusal reason apply unchanged.

**Consequence.** FR-012 through FR-015 are satisfied by REUSE. The only work is
ensuring the derived scope is what reaches `_requested_components`, and that a
blocked plan (FR-005) refuses before authorization is even consulted.

## R5 -- What decides "satisfied" before, and "ready" after, execution?

**Decision.** Before execution, reuse spec 153's satisfied-state path
(`discovery.installed_ref`, already routed through a small seam). After execution,
readiness comes from the discovery results the outcome already carries, never from
an install row's success.

**Findings.** `apply()` already appends `inspect_official_skills(...)` results to
`outcome.discovery`, and `SetupOutcome.needs_action` is true when EITHER a
component row or a discovery result needs action -- so "installed but unverified"
is already distinguishable from "ready" without inventing anything.
`inspect_locked_component` exists for a single component when its exact locked
checkout is present. `installer.NEEDS_ACTION` and the discovery status vocabulary
are two different sets, which the compatibility facade already unions
deliberately; the bridge must union them the same way rather than reading only the
install rows.

**Alternative rejected.** Treating a `ComponentPlan` status of installed as
capability readiness. Rejected by FR-017 and by spec 153 FR-019 before it.

## R6 -- Where does the bridge live, and what may it not touch?

**Decision.** A NEW module. `derivation.py` is not modified.

**Finding, and it is a hard constraint.** Two shipped spec-153 tests read
`derivation.__file__` as source text and assert it contains none of
`apply_profile(`, `live_resolvers(`, `write_lock(`, `install(`, `pip `, `npm `,
`approved`, `authorize`, `--yes`, `args.yes`. The bridge legitimately calls the
installer and consults the approval gate, so putting it in `derivation.py` would
turn those assertions red -- and they are the mechanical proof of spec 153's
FR-017/FR-018 boundaries, not incidental lint. A separate module keeps both specs'
boundaries testable: derivation stays pure, the bridge stays the only place that
touches execution.

**Consequence.** The capability-oriented status assembly (FR-011) also belongs in
the bridge, not in `derivation.render_json`, because it must carry
post-execution state that derivation may not observe.
