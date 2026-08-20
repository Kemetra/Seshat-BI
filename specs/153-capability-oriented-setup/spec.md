# Feature Specification: Capability-oriented setup ("Seshat Setup")

**Feature Branch**: `153-capability-oriented-setup`

**Created**: 2026-08-20

**Status**: ratified -- Ahmed Shaaban, 2026-08-20

**Status history**: Draft -- 2026-08-20; ratified the same day, after its
prerequisite (issue #671, the provisioning-approval trust boundary) landed on
`main` as `b456577c`. Implementation is permitted from this point. FR-018 remains
a permanent boundary: the weak provisioning approval must never be inherited,
even though #671 removed it.

**Input**: Official-first roadmap, capability-experience delta: let a user or agent
describe the project and desired outcome, and have Seshat derive which
*capabilities* the project needs, at what strength, presented by capability name
and reason rather than by package, MCP server, or runtime name. Provisioning,
compatibility resolution, discovery, verification, and state recording are NOT
redefined here -- they are already owned by the ratified official-first program
(specs 143-150) and its integration control plane.

## Context: what already exists (this spec is a delta)

This feature is a thin layer over a ratified, built control plane. It MUST NOT
restate or duplicate the following, each of which is already specified and
shipped:

| Concern | Owning spec | Shipped surface |
|---|---|---|
| Official-first provider authority | 143 (ratified) | allowlisted catalog sources |
| Planner / installer / lock as sole authority | 144 (ratified) | `seshat integrations setup` |
| Power BI / dbt / Dagster intent routing | 145, 146, 147 (ratified) | workflow router skills |
| Obtained vs activated vs discoverable | 148 (ratified) | discovery facts |
| Upstream execution evidence | 150 (ratified) | evidence consumer |
| Capability manifest vocabulary | 118, 142 (implemented) | capability inventory |
| Compatibility / version resolution | 144 | version + policy resolution |

**The gap this spec closes.** The shipped setup journey selects work by *curated
profile*, and its default profile is the union of every profile -- a fixed bundle
for every user. Nothing inspects the project to decide what is actually needed,
and no field expresses how strongly a capability is needed. Catalog reason
strings are written provider-first ("Postgres adapter for the dbt engine"), not
capability-first. Those three things are this spec's entire scope.

**Deliberately excluded: the provisioning approval model.** The shipped approval
for provisioning is agent-self-grantable, tracked as its own security follow-up
(issue #671). Spec 144 FR-010 froze the current approval prompt as a
compatibility guarantee, so correcting it is an amendment of a ratified
requirement, not a defect patch. This spec does NOT own, restate, or inherit that
defect: it consumes whatever approval authority the control plane exposes once
#671 is dispositioned, and adds no approval path of its own.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Setup derived from the project, not a fixed bundle (Priority: P1)

A BI user who does not know the tooling ecosystem opens a project holding
PostgreSQL sources and intending a Power BI destination. Instead of being offered
every supported provider, they are shown a short list of the capabilities their
project actually needs, each with a plain-language reason, and each marked as
required, recommended, optional, or not required.

**Why this priority**: Without this, the normal journey offers a fixed bundle and
the user must decide package-by-package what they need -- the exact knowledge
burden this milestone removes. It is also the smallest slice that delivers
standalone value: derivation plus presentation is useful even before any
strength-aware provisioning behavior changes.

**Independent Test**: Point the derivation at two projects with different shapes
(one Postgres+Power BI, one Postgres-only with no BI destination) and prove the
derived capability sets and strengths differ, that each entry carries a reason,
and that no provider, package, MCP server, or runtime name appears in the normal
presentation.

**Acceptance Scenarios**:

1. **Given** a project with a reachable-by-declaration relational source and a
   declared Power BI destination, **when** setup is inspected, **then** Database
   Connectivity and Power BI Integration are `required`, Orchestration is
   `not-required`, and every entry states why in language naming no package.
2. **Given** the same project, **when** setup is inspected, **then** the result is
   not the union of all curated profiles, and capabilities the project does not
   need are present as `not-required` rather than silently absent.
3. **Given** a project declaring no BI destination, **when** setup is inspected,
   **then** Power BI Integration is not `required`.
4. **Given** a capability already present and verified by the existing control
   plane, **when** setup is inspected, **then** it is shown as already satisfied
   and appears in no proposed change set.
5. **Given** derivation cannot determine a capability's need from project
   evidence, **when** setup is inspected, **then** it is reported as undetermined
   with the missing evidence named, and never defaulted to `required`.

---

### User Story 2 - Requirement strength distinguishes must from might (Priority: P2)

A user reviewing the setup plan can tell, per capability, whether the project
cannot proceed without it, whether it is advised and why, whether it is merely
available, or whether it does not apply -- and can decline a recommendation
without being blocked.

**Why this priority**: Strength is what makes derivation actionable; without it a
derived list is just a shorter fixed bundle. It depends on Story 1 having derived
the set, so it follows.

**Independent Test**: Render a plan containing all four strengths, decline a
`recommended` capability and prove setup still proceeds, decline a `required` one
and prove setup reports a blocker instead of proceeding or silently downgrading.

**Acceptance Scenarios**:

1. **Given** a derived plan, **when** each entry is read, **then** its strength is
   exactly one of `required`, `recommended`, `optional`, `not-required`.
2. **Given** a `recommended` capability, **when** the user declines it, **then**
   the remaining approved work proceeds and the decline is recorded.
3. **Given** a `required` capability, **when** the user declines it, **then**
   setup reports an explicit blocker with a next action and does not represent
   the project as set up.
4. **Given** a `recommended` strength, **when** its reason is read, **then** the
   reason states the project evidence that justified the recommendation, not a
   generic statement.
5. **Given** a capability the project does not require, **when** an agent
   requests it anyway, **then** the request is reported as outside derived need
   and is not silently promoted to `required`.

---

### User Story 3 - Capability language for users, provider detail as evidence (Priority: P3)

An advanced user or auditor can ask for the technical detail behind any
capability -- which provider satisfies it, at which version, verified how -- while
the normal user never has to see or supply that detail.

**Why this priority**: The evidence path is required for auditability and for
advanced users, but the normal journey is already usable without it, so it ships
last.

**Independent Test**: Capture the normal presentation and assert it contains no
package, MCP server, or runtime identifier; then request technical detail for the
same capabilities and assert the provider identity, version state, and
verification basis are all reachable and attributed to the owning control-plane
surface.

**Acceptance Scenarios**:

1. **Given** the normal presentation, **when** it is rendered, **then** it names
   capabilities and reasons only, with no package, MCP server, npm, or runtime
   identifier and no installation command.
2. **Given** a capability, **when** technical detail is explicitly requested,
   **then** the satisfying provider, its compatibility/version state, and the
   verification basis are reported from the existing control plane rather than
   recomputed here.
3. **Given** a capability satisfiable by more than one provider, **when** detail
   is requested, **then** the selected provider and the basis for preferring it
   are both stated.
4. **Given** any presentation or machine-readable output, **when** it is
   inspected, **then** it contains no secret, credential, connection string, or
   token value.

---

### Edge Cases

- A required capability is already present and compatible: reported satisfied,
  proposed for no change, never reinstalled.
- A provider exists but is incompatible: surfaced as a compatibility failure from
  the existing resolution logic, with a next action; never presented as ready.
- A provider exists but cannot be verified: reported unverified with the failed
  check named; never inferred ready from a successful install.
- Multiple providers could satisfy one capability: the selection and its basis
  are both reported.
- A provider is unavailable on the user's operating system, or the network is
  unavailable: reported as a blocker with the constraint named; derivation and
  presentation still work offline from committed project evidence.
- Installation needs administrator rights, login, tenant configuration, or a
  licence: setup stops at a stated human-action boundary rather than attempting
  or claiming completion.
- A recommendation is declined: proceeds; the decline is recorded so a later run
  does not silently re-propose it as new.
- Partial success: capabilities that failed are individually reported as failed;
  the run is never represented as successful overall.
- Setup is re-run: derivation is repeatable on unchanged project evidence, and
  already-satisfied capabilities are proposed for no change.
- Project requirements change after setup: re-derivation reports the newly needed
  capabilities as a new proposal requiring its own authorization.
- A previously satisfied provider drifts or becomes incompatible: reported as no
  longer satisfied, using the existing verification and discovery surfaces.
- Project evidence is insufficient to derive a capability's need: reported
  undetermined with the missing evidence named; never defaulted to `required`.

## Requirements *(mandatory)*

### Functional Requirements

**Capability derivation**

- **FR-001**: Setup MUST derive the needed capability set from project evidence --
  declared data sources, declared BI destination, intended workflow, and
  capabilities already satisfied -- rather than from a fixed profile.
- **FR-002**: Derivation MUST be available as the selection basis for the normal
  setup journey. Existing selection flags MUST continue to exist and behave as
  they do today (spec 144 FR-010). Whether derivation becomes the *default* basis
  -- changing observable default selection behavior -- is owner decision 1 and is
  NOT settled by this spec.
- **FR-003**: Derivation MUST be repeatable: the same project evidence MUST yield
  the same derived set and strengths.
- **FR-004**: Derivation MUST require no network access and MUST write nothing.
- **FR-005**: When project evidence is insufficient to determine a capability's
  need, setup MUST report it as undetermined and name the missing evidence, and
  MUST NOT default it to `required` or silently omit it.
- **FR-006**: An agent-requested capability outside the derived need MUST be
  reported as outside derived need and MUST NOT be promoted to `required`.

**Requirement strength**

- **FR-007**: Every derived capability MUST carry exactly one strength:
  `required`, `recommended`, `optional`, or `not-required`.
- **FR-008**: Every derived capability MUST carry a reason stating the project
  evidence that produced its strength, expressed without naming a package, MCP
  server, npm package, or runtime.
- **FR-009**: Declining a `recommended` or `optional` capability MUST leave the
  remaining approved work able to proceed, and MUST record the decline so a later
  run does not re-propose it as newly discovered.
- **FR-010**: Declining a `required` capability MUST produce an explicit blocker
  with a next action, and MUST NOT allow setup to represent the project as set
  up, nor downgrade the strength to make the blocker disappear.
- **FR-011**: Strength MUST be represented as capability metadata and MUST NOT
  introduce a capability registry separate from the existing manifest and
  integration catalog.

**Capability-oriented presentation**

- **FR-012**: The normal presentation MUST identify capabilities by capability
  name and reason, and MUST NOT require the user to read or supply any package,
  MCP server, npm package, runtime name, or installation command.
- **FR-013**: Provider identity, compatibility/version state, and verification
  basis MUST be available on explicit request as technical evidence, sourced from
  the existing control plane rather than recomputed.
- **FR-014**: Where more than one provider could satisfy a capability, the
  selected provider and the basis for preferring it MUST both be reportable.
- **FR-015**: Setup MUST expose a machine-readable capability status carrying, per
  capability, its strength, whether it is satisfied, its reason, and any blocker
  or undetermined-evidence marker -- sufficient for an agent to answer what is
  needed, what is satisfied, what is missing, why a capability is recommended,
  and what the next safe action is, without inspecting provider internals.
- **FR-016**: No presentation, evidence, or machine-readable output MAY contain a
  secret, credential, connection string, or token value.

**Boundaries this spec MUST hold**

- **FR-017**: This feature MUST NOT install, resolve versions for, verify, or
  record provisioning state itself; it MUST delegate each to the existing
  control plane (spec 144) and existing discovery (spec 148), and MUST NOT
  introduce a second installer, resolver, verifier, or state store.
- **FR-018**: This feature MUST NOT define, weaken, or substitute for the
  authorization required before provisioning, and MUST NOT treat a caller-supplied
  flag as evidence of human approval. It consumes the control plane's
  authorization outcome; correcting that model is issue #671.
- **FR-019**: A capability MUST NOT be reported satisfied on the basis of a
  successful installation alone; satisfaction MUST rest on the existing
  verification and discovery surfaces.
- **FR-020**: Adding a future capability or provider MUST NOT require changing the
  user-facing setup journey.

### Key Entities

- **Capability**: A named, provider-independent ability a project needs (e.g.
  Database Connectivity, Power BI Integration). Carries a user-facing name and
  description. Extends the existing capability manifest vocabulary; introduces no
  new registry.
- **Requirement strength**: One of `required` / `recommended` / `optional` /
  `not-required`, attached to a capability *for a given project*, with the reason
  that produced it. New concept; the shipped catalog has no equivalent field.
- **Derivation evidence**: The project facts a strength was derived from --
  declared sources, declared destination, intended workflow, already-satisfied
  capabilities. Read-only.
- **Setup plan**: The derived capability set with strengths, reasons, satisfied
  state, and blockers, in both human and machine-readable form.
- **Provider (existing, referenced only)**: The concrete official component
  satisfying a capability. Owned by the integration catalog; not redefined here.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who cannot name any underlying package, MCP server, or
  runtime can complete the normal setup journey for a Postgres + Power BI project.
- **SC-002**: Two projects of different shape produce different derived capability
  sets, and a derived set is never the union of all curated profiles.
- **SC-003**: Every capability in a derived plan carries a strength and a reason
  that cites project evidence; zero entries lack either.
- **SC-004**: The normal presentation contains zero package, MCP server, npm,
  runtime identifiers and zero installation commands, while the same capabilities'
  provider detail is fully reachable on explicit request.
- **SC-005**: Declining a recommended capability leaves the remaining approved
  work able to proceed; declining a required one yields a blocker and never a
  set-up claim.
- **SC-006**: Re-running setup on unchanged project evidence proposes no change
  for already-satisfied capabilities and yields an identical derived set.
- **SC-007**: Every capability reported satisfied has a verification basis
  attributable to an existing verification or discovery surface; none rests on
  installation success alone.
- **SC-008**: An agent can answer what is needed, what is satisfied, what is
  missing, why a capability is recommended, and what the next safe action is, from
  the machine-readable status alone.
- **SC-009**: The base installation remains usable with no optional provider
  installed: derivation and presentation work offline and write nothing.
- **SC-010**: Adding a capability or provider to the existing catalog changes the
  derived plan with no change to the user-facing journey.
- **SC-011**: No setup output contains a secret, credential, connection string, or
  token value.

## Assumptions

- Specs 143-150 remain ratified and their shipped surfaces remain the sole
  authority for provisioning, compatibility resolution, discovery, verification,
  and lock/state recording. This spec adds a derivation and presentation layer
  above them.
- Project evidence is read from committed project declarations; derivation does
  not connect to a database or contact a network, consistent with the
  static-first governance posture.
- Per-project capability state belongs with the existing per-project integration
  state, not in the per-table readiness record. The four per-stage readiness
  status values remain untouched, so the capability strength vocabulary
  introduces no collision with them.
- Curated profiles and their existing flags remain available and unchanged in
  behavior. This spec adds derivation as a selection basis; whether it displaces
  the current default is owner decision 1, constrained by spec 144 FR-010.
- Reason and capability-name text is authored capability-first. The shipped
  catalog's provider-first role strings are evidence-layer text, not user-facing
  capability descriptions.
- Issue #671 (agent-self-grantable provisioning approval) lands BEFORE any spec
  153 implementation, by owner ruling. This spec neither depends on nor
  perpetuates the weaker model, and FR-018 keeps that boundary permanent even
  after #671 is fixed.

## Dependencies

- **Spec 144** (integration control plane) -- planner, installer, lock, sole
  operational integration authority. **Note**: its FR-010 freezes the current
  approval prompt; issue #671 proposes amending that requirement.
- **Spec 148** (official skill discovery) -- obtained / activated / discoverable
  facts used to decide whether a capability is satisfied.
- **Specs 143, 145, 146, 147, 150** -- official-first provider authority, intent
  routing, upstream evidence.
- **Specs 118, 142** -- capability manifest and ownership fields; the vocabulary
  this spec extends rather than replaces.
- **Issue #671** -- provisioning authorization correction. **HARD PREREQUISITE**:
  by owner ruling (2026-08-20) #671 MUST land before spec 153 implementation
  begins. Not merely sequenced before the provisioning path -- it blocks all
  implementation, including the read-only derivation and presentation stories.

## Out of Scope

- A second capability registry, installer, resolver, verifier, or state store.
- Replacing or redesigning the integration control plane or the readiness spine.
- Bundling all providers; a package marketplace; a graphical installer.
- Provider-specific implementation design, environment layout, or installation
  mechanism.
- Correcting the provisioning approval model (issue #671).
- Live database connection or network access as part of derivation.
- Implementation of any kind.

## Owner Decisions

All three questions raised in draft are settled. Decisions 1 and 2 were resolved
against repository and constitutional evidence; decision 3 was ruled by the owner.
Each records its basis so a later reader does not reopen it.

**Implementation is BLOCKED on issue #671** by owner ruling (decision 3). This spec
is ratifiable and reviewable now; no implementation may begin until #671 lands.

1. **RESOLVED BY EVIDENCE (no owner ruling needed).** The question was whether
   derivation may displace the current default selection. It may not, without an
   explicit amendment: `DEFAULT_PROFILE` is an **exported public constant**
   (listed in `seshat.integrations_setup.__all__`) and the default value of three
   public function signatures. Spec 144 **FR-006** requires that "the existing
   exported compatibility types, constants, prompt, and planner/apply/render
   aliases MUST remain importable unless exact repository evidence proves a symbol
   private" -- so the constant's *value* is part of the public contract, not merely
   the flag's existence. FR-002 therefore stands as written: derivation is
   *available* as a selection basis, existing flags and their behavior are
   untouched, and displacing the default would be a separate, explicitly-amended
   change. Corroborating evidence: shipped documentation passes
   `--profile analytics-full` explicitly rather than relying on the default
   (`docs/integrations/official-skill-discovery.md:17-18`).
2. **RESOLVED BY CONSTITUTION (no owner ruling needed).** The question was whether
   derivation must always commit to one of the four strengths. It must not: the
   Readiness System requires that a positive state "MUST carry evidence" and that
   readiness "MUST NOT be expressed as a fabricated confidence number"
   (`.specify/memory/constitution.md:523-527`). Committing to a strength on
   insufficient project evidence is exactly a fabricated confidence. FR-005 stands:
   an underivable capability is reported `undetermined` with the missing evidence
   named. Note `undetermined` is a *derivation-evidence* marker, NOT a fifth
   requirement strength -- the strength vocabulary remains exactly four values
   (FR-007).
3. **RULED BY OWNER (Ahmed Shaaban, 2026-08-20): SEQUENTIAL.** Issue #671 MUST
   land before spec 153 implementation begins. The provisioning-approval defect is
   corrected at the existing control-plane seam first, so that later setup work
   cannot accidentally couple to the weak approval path. Specification and review
   of spec 153 may proceed now; implementation may not.

   FR-018 remains the permanent boundary regardless of sequencing -- it is not
   satisfied or retired by #671 landing.
