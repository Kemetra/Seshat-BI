# Feature Specification: Guided setup execution (derived plan -> approved provisioning)

**Feature Branch**: `claude/spec-155-guided-setup-pzrctn`

**Created**: 2026-08-20

**Status**: ratified -- Ahmed Shaaban, 2026-08-21

**Status history**: Draft -- 2026-08-20; implementation shipped 2026-08-21 on the
owner's instruction while the spec was still Draft; ratified 2026-08-21 by the owner
in session. Recorded in the order it actually happened: the build preceded the
ratification here, so this line is NOT evidence of the normal spec-then-build
sequence, and a reader should not cite spec 155 as a precedent for building ahead of
a ratification. The agent transcribed this decision and did not self-ratify. Both
prerequisites were already ratified -- specs 153 and 154, 2026-08-20. The spec-153
boundary remains permanent: `integrations/guided_setup.py` is the bridge, deliberately
NOT `derivation.py`, because two shipped spec-153 tests assert that file holds no
execution or approval call site.

**Input**: Connect the capability-oriented project plan produced by spec 153 to the
existing integration control plane, so a user provisions ONLY the capabilities the
project actually needs, under the committed named-human approval model delivered by
spec 154. A thin orchestration delta: no second installer, capability registry,
provider registry, approval mechanism, or control plane.

## Context: what already exists, and the exact gap

This feature is a **seam**, not a subsystem. Every stage below except one is
already built and ratified; this spec owns only the connection between them.

| # | Stage | Owner | Shipped surface |
|---|---|---|---|
| 1 | Project evidence | the project's committed artifacts | source-maps, Power BI project, transformation/orchestration manifests |
| 2 | Capability derivation | **spec 153** | derived plan: capability, strength, reason, satisfied, declined, blocker |
| 3 | Capability-to-component projection | **spec 153** | the catalog-verified capability -> component-id mapping |
| 4 | Proposed change set | **THIS SPEC** | -- does not exist -- |
| 5 | Human authorization | **spec 154** | committed named-human `governance` approval, read at HEAD, scope-bound |
| 6 | Installer execution | **spec 144** | planner, resolver, compatibility policy, installer, lock |
| 7 | Verification | **specs 144, 148** | discovery facts, installed-ref and payload checks |
| 8 | Resulting status | **specs 153, 144** | capability status; component plan rows |

**Verified on `main` at `88a194c`** (the four stated assumptions all hold, with two
material differences worth recording):

1. **Spec 153 is implemented** -- derivation from committed evidence, four
   requirement strengths, `undetermined` as a separate evidence marker, satisfied
   state routed through the discovery surface, committed declines, a human-readable
   plan, a machine-readable plan, and a request-only technical-evidence path.
   `DEFAULT_PROFILE` is untouched and nothing is installed.
   **Difference (narrows this spec):** a capability-to-component projection
   ALREADY EXISTS and is already verified against the catalog by test. This spec
   therefore does not define the projection -- it consumes it (stage 3 above).
   **Difference (widens this spec):** the derived plan is reachable only as a
   library surface. It has **no consumer anywhere outside its own unit tests** --
   no CLI verb, no flag, no skill, no documentation path. So "the derived plan is
   not the normal input to provisioning" is understated: today the derived plan is
   not reachable in the normal journey **at all**.
2. **Spec 154 / issue #671 is implemented** -- provisioning authority is a
   committed `governance` approval read at HEAD, shape-validated by the one
   canonical validator, bound to a component scope that ONE row must cover on its
   own, standing until material scope change, and never satisfied by `--apply`,
   `--yes`, a TTY answer, or stdin. The requested scope is already read from the
   plan's own rows rather than from argv.
3. **The existing control plane already owns** catalog/provider truth,
   compatibility and version resolution, installation into isolation, discovery,
   verification, lock/state recording, and rendering.
4. **Normal setup execution is still profile-only.** Component selection is
   `profile_components(profile)` and nothing else; there is no component-set entry
   point, the isolation environment is derived from the profile name, and the state
   record is one whole-file document carrying one profile label and only the
   components that landed in the last run.

**The gap, stated exactly.** Stage 4 does not exist, and stages 2-3 are not wired
to stages 5-8. Everything else is reuse. That is this spec's entire scope.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See exactly what this project needs, and exactly what would change (Priority: P1)

A BI user opens a PostgreSQL + Power BI project and asks what setup it needs. They
are shown their capabilities in capability language -- what is required, what is
already satisfied, what does not apply -- together with a count of the proposed
changes. The proposed change set contains only what those needed capabilities
require. Nothing is installed, written, or fetched.

**Why this priority**: This is the standalone value and the smallest safe slice:
the user can already see that they do not need the historical bundle, and can
review the exact scope a human would later be asked to approve. It is also the
only slice that must exist before any authorization question can be asked, because
the scope is what an approval binds to.

**Independent Test**: Plan two projects of different shape (Postgres + Power BI;
Postgres only) and prove the proposed component scopes differ, that each contains
only components projected from capabilities the derived plan reports as needing
action, that neither is the curated default profile's set, that an
already-satisfied capability contributes no action, and that the run wrote nothing
and contacted no network.

**Acceptance Scenarios**:

1. **Given** a project whose derived plan reports Database Connectivity and Power
   BI Integration as required and Transformation Engine and Orchestration as
   not-required, **when** guided setup is planned, **then** the proposed change set
   contains exactly the catalog components projected for the first two
   capabilities, and no component attributable only to the other two.
2. **Given** the same project, **when** the plan is rendered normally, **then** it
   names capabilities, strengths and a proposed-change count, and contains no
   package, MCP server, npm, or runtime identifier and no installation command.
3. **Given** a capability the existing discovery surface reports satisfied,
   **when** the plan is generated, **then** it appears as satisfied and produces no
   install action.
4. **Given** a `recommended` capability recorded as declined, **when** the plan is
   generated, **then** it produces no provisioning action and does not prevent the
   remaining proposed work from being proposed.
5. **Given** a `required` capability recorded as declined, **when** the plan is
   generated, **then** the plan is blocked, the capability is still reported
   `required` and still listed, and the blocker names the next action.
6. **Given** a caller that supplies a component id, package name, or profile name
   alongside the derived request, **when** the plan is generated, **then** the
   proposed scope is unchanged and the extra request is reported as outside derived
   need.
7. **Given** any plan in this story, **when** the run finishes, **then** no file
   was written, no network call was made, and the exit status distinguishes "needs
   setup" from "nothing to do".

---

### User Story 2 - Only a named human's committed approval provisions the derived scope (Priority: P2)

A named human reviews the proposed change set and records a committed approval for
exactly that scope. Provisioning then delegates to the existing installer. Without
that record -- or with a record for a different scope -- provisioning refuses and
changes nothing outside the repository.

**Why this priority**: Story 1 makes the need visible; this story makes it
actionable. It depends on Story 1 producing the scope an approval binds to.

**Independent Test**: With the same derived scope, run provisioning (a) with no
committed approval, (b) with an approval for a narrower scope, (c) with an approval
covering the scope exactly, (d) with an approval covering a superset -- and prove
refusal, refusal, execution, execution respectively, with every caller-controlled
signal supplied in every case.

**Acceptance Scenarios**:

1. **Given** a derived scope and no valid committed provisioning approval, **when**
   provisioning is requested with every caller-controlled signal available -- the
   execute-intent flag, the non-interactive flag, machine-readable mode, a piped
   stdin answer, a simulated terminal, and an agent instruction asserting approval
   -- **then** provisioning refuses, nothing is installed or written, no network
   call is made, and the refusal names what must be recorded and by whom.
2. **Given** a committed approval covering capabilities A and B, **when** the
   derived scope becomes A, B and C, **then** the earlier approval does not
   authorize C and the refusal names both the approved and the requested scopes.
3. **Given** a committed, shape-valid, named-human `governance` approval covering
   the exact derived component scope, **when** provisioning is requested with
   intent to execute, **then** the existing installer may execute that scope,
   subject to every pre-existing gate (exact resolution before install, workspace
   validation, compatibility policy, isolation).
4. **Given** a capability the derived plan reports `not-required`, **when**
   provisioning executes under a valid approval, **then** no component of that
   capability is installed, configured, registered, or resolved.
5. **Given** a derived plan that is blocked by a declined `required` capability,
   **when** provisioning is requested, **then** it refuses on the blocker and no
   approval can substitute for removing it.
6. **Given** any refusal in this story, **when** the machine-readable output is
   read, **then** it carries a categorical reason and an explicit next action.

---

### User Story 3 - Honest results, safe retry, and an agent-usable status (Priority: P3)

After execution, the user is told which capabilities are actually ready -- decided
by verification, not by installation returning success -- and which failed, with
one next safe action. Re-running the same approved scope resumes rather than
restarts, and an agent can drive the whole journey from the machine-readable
status without reasoning about packages.

**Why this priority**: Stories 1 and 2 already deliver a safe, complete journey for
the happy path; this story is what makes failure and repetition trustworthy. It
ships last because it is only observable after execution exists.

**Independent Test**: Force a post-install verification failure for one component
and a success for another under one approved scope, and prove the capability of the
failed component is not reported ready, the run is not reported successful, both
outcomes are individually visible, and an immediate re-run reinstalls nothing that
is already satisfied and requires no new approval.

**Acceptance Scenarios**:

1. **Given** an install that completed but whose verification fails, **when** the
   status is read, **then** the capability is not reported ready, the failed check
   is named, and a next safe action is stated.
2. **Given** one component that succeeded and another that failed under the same
   approved scope, **when** the result is reported, **then** the succeeded and the
   failed components remain individually distinguishable, the affected capability
   is reported not ready, and the run is not reported successful overall.
3. **Given** a partial failure followed by a re-run of the same, materially
   unchanged, approved scope, **when** provisioning executes, **then** components
   already satisfied are reused rather than reinstalled, and no new approval is
   required.
4. **Given** a previous broader profile-based run recorded in the existing state
   record, **when** a narrower derived scope is provisioned, **then** the recorded
   state for components outside the derived scope is not discarded, and the record
   does not attribute the derived scope to a curated profile that was not
   installed.
5. **Given** the machine-readable output at any point in the journey, **when** an
   agent reads it, **then** it can obtain, per capability: the capability, its
   requirement strength, whether it is satisfied, whether it needs setup, the
   proposed action, any blocker, whether approval is required and whether that
   requirement is met, and the post-execution status -- with no package-specific
   reasoning.

---

### Edge Cases

- **Nothing to do**: every needed capability is already satisfied. The proposed
  change set is empty; no approval is demanded, and the run reports "nothing to
  do" rather than refusing for want of an approval.
- **A needed capability projects to no catalog component**: reported as an
  unsupported capability with the missing coverage named. Never silently dropped,
  and never treated as satisfied.
- **Undetermined evidence** (spec 153): the capability is excluded from the
  proposed scope with the missing evidence named. A guess is never installed.
- **The catalog gains a component for an already-approved capability**: the derived
  scope widens, which is a material scope change -- the standing approval no longer
  covers it and a new one is required.
- **The approval covers a superset** of the derived scope: authorized. **A subset**:
  refused with both scopes named.
- **A component in the derived scope is incompatible or unavailable** on this
  platform: surfaced by the existing compatibility/resolution logic with a next
  action; never reported ready, and the rest of the scope is reported honestly.
- **Installation needs administrator rights, a login, tenant configuration, or a
  licence**: the run stops at a stated human-action boundary rather than claiming
  completion.
- **Offline**: planning still works from committed evidence and the existing state
  record; execution refuses on the existing network affordance rather than
  installing from a floating reference.
- **A malformed declines record** (spec 153): declines nothing, so a needed
  capability is never suppressed behind a clean-looking plan.
- **An uncommitted or dirty approval record**: no authority -- the existing gate
  reads HEAD only.
- **A profile-based run afterwards**: unchanged in selection, output shape, and
  exit codes.

## Requirements *(mandatory)*

### Functional Requirements

**Derived provisioning scope (stage 4: the proposed change set)**

- **FR-001**: Guided setup MUST be able to select the provisioning scope from the
  derived capability plan (spec 153) instead of from a curated profile, and that
  selection MUST be reachable in the normal user journey rather than only as a
  library call.
- **FR-002**: The proposed component scope MUST be obtained by projecting the
  derived capabilities through the EXISTING capability-to-component mapping and the
  existing catalog. This feature MUST NOT introduce a second capability registry, a
  second provider/package registry, or any component, coordinate, or version of its
  own.
- **FR-003**: Only capabilities the derived plan reports as needing action MUST
  enter the proposed change set. A `not-required` capability, a declined capability,
  a capability with undetermined evidence, and an `optional` capability MUST each
  contribute nothing to it.
- **FR-004**: A capability the existing discovery surface reports satisfied MUST
  remain VISIBLE in the plan, reported as satisfied with its verification basis
  available. (Its exclusion from the change set follows from FR-003; this
  requirement is the visibility obligation that exclusion alone would not give.)
- **FR-005**: A declined `required` capability MUST leave the plan blocked: the
  capability keeps its `required` strength, remains listed, is not silently omitted
  or downgraded, and the blocker MUST carry a next action. A blocked plan MUST NOT
  execute, and no approval may substitute for clearing the blocker.
- **FR-006**: The proposed scope MUST be deterministic: identical committed project
  evidence, catalog, recorded declines, and discovery/satisfaction state MUST yield
  an identical scope in an identical order.
- **FR-007**: No caller-supplied value -- a component id, package name, profile
  name, capability request, or any other argument -- may add anything to the
  proposed scope. A capability requested outside derived need MUST be reported as
  outside derived need and MUST NOT be promoted or provisioned.
- **FR-008**: Producing the plan MUST write nothing and MUST NOT contact the
  network; coordinate resolution and installation MUST remain behind the existing
  explicit network and write affordances.
- **FR-023**: A capability that needs action but projects to no catalog component
  MUST be reported as unsupported, naming the missing coverage. It MUST NOT be
  silently dropped from the plan, and MUST NOT be reported satisfied.
- **FR-024**: When every needed capability is already satisfied, the plan MUST
  report that no change is proposed, and MUST NOT demand an approval or refuse for
  want of one. An empty proposed scope is a valid outcome, not a refusal.

**Presentation and machine-readable status (stage 8)**

- **FR-009**: The normal presentation MUST remain capability-oriented -- capability
  name, requirement strength, satisfied / needs-setup state, and a count of proposed
  capability changes -- and MUST NOT require the user to read or supply a package,
  MCP server, npm package, runtime name, provider name, or installation command.
- **FR-010**: The provider, catalog component, resolved coordinate/version, and
  verification basis behind each capability MUST be available as technical evidence
  on explicit request, sourced from the existing catalog, resolver, and discovery
  surfaces rather than recomputed here.
- **FR-011**: A machine-readable status MUST carry, per capability: the capability,
  its requirement strength, whether it is satisfied, whether it needs setup, the
  proposed action, any blocker, whether provisioning approval is required and
  whether that requirement is currently met, and the post-execution status --
  sufficient to drive the journey without package-specific reasoning.

**Authorization (stage 5)**

- **FR-012**: Provisioning authority MUST come exclusively from the spec 154
  committed named-human approval model, evaluated against the exact derived
  component scope. This feature MUST NOT introduce a second approval mechanism, a
  new approval vocabulary, a new authority class, or a new approval-authoring path.
  Execute intent, a non-interactive affordance, an interactive confirmation, a
  stdin response, machine-readable mode, and an agent instruction asserting that
  approval exists MUST NOT constitute or imply authorization, individually or in
  combination.
- **FR-013**: A materially changed derived scope MUST NOT be authorized by an
  earlier approval, and the refusal MUST name both the approved and the requested
  scopes. A materially unchanged scope MUST remain authorized by the standing
  approval (spec 154's lifetime semantics are consumed, not restated).
- **FR-014**: Every refusal MUST fail closed -- nothing installed, written,
  registered, or fetched -- and MUST expose a categorical reason plus an explicit
  next action in both human-readable and machine-readable form.

**Execution, verification, resulting state (stages 6-8)**

- **FR-015**: Execution MUST delegate to the existing installer and control plane.
  This feature MUST NOT introduce a second installer, resolver, compatibility
  policy, verifier, or state store, and MUST NOT remove or weaken any existing
  precondition (exact coordinate resolution before installing, workspace
  validation, isolation, non-clobbering registration).
- **FR-016**: A capability MUST NOT be reported ready on the basis of a successful
  installation. Readiness MUST come from the existing verification and discovery
  surfaces; when verification fails after installation the capability MUST remain
  not-ready, and the failed check and next safe action MUST be exposed.
- **FR-017**: A partial outcome MUST be reported honestly: succeeded components and
  failed or blocked components MUST remain individually distinguishable, the
  affected capabilities MUST NOT be reported ready, the run MUST NOT be reported
  successful overall, and one next safe action MUST be stated.
- **FR-018**: Re-running a materially unchanged approved scope MUST reuse existing
  valid setup state -- already-satisfied components MUST NOT be reinstalled -- and
  MUST NOT require a new approval.
- **FR-019**: Recording the resulting provisioning state MUST use the existing
  state record, MUST NOT discard previously recorded valid state for components
  outside the derived scope, and MUST NOT attribute a derived scope to a curated
  profile that was not installed.

**Compatibility boundaries**

- **FR-020**: Derived setup MUST be additive. Existing explicit profile-based
  workflows MUST remain available with unchanged selection, flag behavior, output
  shape, and exit codes; the value and public contract of `DEFAULT_PROFILE` MUST
  NOT change. Making derived selection the default MUST NOT happen implicitly --
  it would amend a ratified contract and is owner decision 1.
- **FR-021**: The derived journey MUST NOT provision a component merely because it
  belongs to the same curated or historical profile as a needed component.
- **FR-022**: No plan, refusal, evidence record, or machine-readable output may
  contain a secret, credential, connection string, or token value.

### Key Entities

- **Derived provisioning scope**: The ordered set of existing catalog component ids
  projected from the capabilities the derived plan reports as needing action. The
  one new concept in this spec, and the object an approval binds to. Carries no
  coordinate, version, or provider fact of its own.
- **Proposed change set**: The user-facing view of that scope -- per capability, the
  proposed action (set up / already satisfied / no action / blocked) and the count
  of capabilities that would change. Capability-oriented by construction.
- **Capability-to-component projection (existing, referenced only)**: Spec 153's
  catalog-verified mapping from capability to component ids. Consumed, never
  redefined.
- **Provisioning approval (existing, referenced only)**: Spec 154's committed
  named-human `governance` record, read at HEAD, covering a component scope on one
  row. Consumed, never redefined.
- **Material scope change (existing, referenced only)**: Spec 154's definition. This
  spec adds only that a widened PROJECTION -- from changed project evidence, changed
  declines, or a changed catalog -- is such a change.
- **Guided setup result**: Per capability, the post-execution readiness decided by
  verification, plus the per-component succeeded/failed detail and one next safe
  action.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who can name no package, MCP server, npm package, or runtime
  completes the review-and-approve journey for a Postgres + Power BI project; the
  normal presentation contains zero such identifiers and zero installation
  commands, while the same capabilities' provider detail is fully reachable on
  explicit request.
- **SC-002**: For that project the proposed component scope is exactly the
  projection of the needed capabilities, is strictly smaller than the curated
  default profile's component set, and contains zero components attributable only
  to `not-required` capabilities.
- **SC-003**: An already-satisfied capability produces zero install actions in the
  proposed change set while remaining visible as satisfied.
- **SC-004**: A declined `recommended` capability produces zero provisioning
  actions and leaves the remaining proposed work proposable; a declined `required`
  capability yields a blocked plan that executes nothing, in 100% of tested cases.
- **SC-005**: Zero code paths provision anything without a covering committed
  approval, measured across every caller-controlled signal -- execute intent,
  non-interactive flag, machine-readable mode, stdin, simulated terminal, and an
  agent instruction asserting approval.
- **SC-006**: Every scope-widening attempt is refused: a caller-supplied component,
  package, profile, or capability value changes the proposed scope in zero cases,
  and an approval for a narrower scope authorizes a widened scope in zero cases,
  with both scopes named in the refusal.
- **SC-007**: Re-planning on unchanged committed evidence yields an identical
  proposed scope, in identical order, across repeated runs.
- **SC-008**: Every capability reported ready has a verification basis attributable
  to an existing verification or discovery surface; zero rest on installation
  success alone, and a post-install verification failure yields not-ready plus the
  named failed check plus a next action in 100% of tested cases.
- **SC-009**: In a partial run, 100% of succeeded and 100% of failed components
  remain individually identifiable, and the run is reported successful in zero such
  cases.
- **SC-010**: A retry of a materially unchanged approved scope reinstalls zero
  already-satisfied components and requires zero additional approvals.
- **SC-011**: A narrower derived run discards zero previously recorded valid state
  entries for components outside its scope, and mislabels the derived scope as a
  curated profile in zero cases.
- **SC-012**: An agent obtains all eight facts named in FR-011 -- capability,
  strength, satisfied, needs-setup, proposed action, blocker, approval requirement,
  post-execution status -- from the machine-readable output alone, with zero
  package-specific reasoning.
- **SC-013**: `DEFAULT_PROFILE`'s value and every existing profile flag's behavior
  are unchanged, and existing profile-based runs produce identical selection,
  output shape, and exit codes.
- **SC-014**: Planning writes zero files and makes zero network calls; zero outputs
  contain a secret, credential, connection string, or token value.

## Assumptions

- Specs 143-150, 153, and 154 remain ratified, and their shipped surfaces remain
  the sole authority for provider truth, compatibility resolution, installation,
  discovery, verification, state recording, capability derivation, and provisioning
  authorization. This spec adds only the connection between them.
- Eligibility for the proposed change set is spec 153's existing needs-action
  definition (a `required` or `recommended` capability that is not satisfied and not
  declined). `optional` capabilities are therefore presented but never proposed --
  see owner decision 2.
- The projection consumed at stage 3 is spec 153's committed mapping, and its
  catalog agreement is already guarded by test. A capability whose projection is
  empty is an unsupported capability, not a satisfied one.
- Declines are read from the existing committed declines artifact with spec 153's
  fail-closed semantics; this spec adds no decline-authoring path.
- Approvals are read from the existing committed provisioning-approvals artifact
  with spec 154's semantics, including standing-until-scope-change lifetime and the
  one-row-must-cover-the-request rule; this spec adds no approval-authoring path and
  routes human authoring through the existing approval-console surfaces.
- Provisioning state remains machine-local and per-project, in the existing state
  record; this spec introduces no committed provisioning state and touches no
  per-table readiness record.
- The derived journey is expected to be usable offline for planning, consistent
  with the static-first governance posture.

## Dependencies

- **Spec 153** (capability-oriented setup) -- stages 1-3: derivation, requirement
  strength, declines, satisfied state, the capability-to-component projection, and
  the capability-oriented and machine-readable plan surfaces. Spec 153 FR-018
  (never define, weaken, or substitute for provisioning authorization) binds this
  spec too and is not retired by spec 154 having landed.
- **Spec 154** (secure provisioning approval) -- stage 5: the committed named-human
  `governance` approval read at HEAD, its scope binding, its material-scope-change
  rule, and its standing-until-scope-change lifetime.
- **Spec 144** (integration control plane) -- stages 6-8: catalog membership,
  resolver, compatibility policy, installer, isolation, lock/state recording, and
  rendering. Spec 144 FR-006 (exported symbols remain importable), the unamended
  clauses of spec 144 FR-010 (flags, exit codes, JSON shape, workspace validation,
  catalog-backed routing), and spec 144 FR-011 (existing lock and compatibility
  contracts stay green) all constrain this spec.
- **Spec 148** (official skill discovery) -- the obtained / activated /
  discoverable facts that decide satisfaction and post-execution readiness.
- **Specs 143, 145, 146, 147, 150** -- official-first provider authority, intent
  routing, upstream execution evidence. Referenced, unchanged.

## Out of Scope

- A second installer, resolver, compatibility policy, verifier, capability
  registry, provider/package registry, approval mechanism, approval vocabulary, or
  approval-authoring path.
- Changing `DEFAULT_PROFILE`, or making derived selection the default (owner
  decision 1).
- An opt-in path for provisioning `optional` capabilities (owner decision 2).
- A marketplace, a graphical installer, Studio work, a broad onboarding redesign,
  new readiness stages, or any change to the readiness spine.
- Automatic installation without human approval; bundling every supported
  integration.
- Rewriting the dbt, Dagster, Power BI MCP, or database-provider integrations, and
  any provider-specific implementation design.
- Live database access; network access during planning.
- Implementation of any kind.

## Owner Decisions

1. **RESOLVED BY EVIDENCE -- option A (additive mode), no owner ruling needed.**
   The question was whether the normal CLI journey should gain a derived/guided
   setup mode while preserving the current profile default (A), or eventually make
   derived setup the default (B). B is blocked by committed contracts: spec 153's
   owner decision 1 already ruled -- on the evidence that `DEFAULT_PROFILE` is an
   exported public constant and the default of three public signatures, protected
   as a value by spec 144 FR-006 -- that displacing the default requires an
   explicit amendment. Spec 144 FR-010's unamended clauses (flags, exit codes, JSON
   shape, catalog-backed routing) bind the same way. FR-020 therefore records A as
   the safe boundary: derived setup is an additional selection basis, existing
   flags and their behavior are untouched, and B stays available only as an
   explicit future amendment with a named owner ruling.
2. **RESOLVED BY EVIDENCE -- `optional` capabilities are presented, never
   proposed.** The question was whether a non-declined `optional` capability may be
   provisioned through the guided path. Any such path needs a recorded signal
   saying the user wants it, and no such signal exists in committed state: the only
   committed capability-scope artifacts are the declines record and the provisioning
   approval, and spec 154's approval authorizes a scope rather than choosing one.
   Inventing a third committed signal would be a new authoring path, excluded above.
   So `optional` capabilities are shown with their reason and contribute nothing to
   the proposed scope (FR-003); a request for one is reported as outside derived
   need (FR-007). A future opt-in is its own spec.
3. **DEFERRED TO PLANNING, with a guardrail -- not an owner decision unless the
   mechanism amends a ratified contract.** The existing state record is one
   whole-file document carrying a single profile label and only the components that
   landed in the last run, and the isolation environment is derived from the profile
   name. A narrower derived run must therefore not discard out-of-scope recorded
   state (FR-019), and must not misattribute the derived scope to a curated profile
   it did not install. FR-019 fixes the required BEHAVIOR; the mechanism (merging
   into the existing record versus recording the selection basis distinctly, and
   which isolation target a derived scope installs into) is a `/speckit.plan`
   research item. **Escalate to an explicit owner ruling if, and only if, the chosen
   mechanism changes the documented meaning or schema of the existing state record
   or isolation layout** -- that would amend spec 144 FR-011 and must be recorded as
   an amendment rather than done implicitly.
