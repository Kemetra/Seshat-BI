# Feature Specification: Agent-driven bundle completion

**Feature Branch**: `138-agent-driven-bundle`

**Created**: 2026-07-31

**Status**: draft

<!-- One of: draft | ratified | implemented | superseded (ADR 0019).
     draft       -- authored, not yet ratified by a named human
     ratified    -- a named human approved THE SPEC; record their name and the date
     implemented -- the capability exists on `main`; MUST name its artifact, e.g.
                    `**Status**: implemented -- artifact `src/seshat/foo.py``, and gets a
                    `spec-<NNN>-implemented` claim in docs/quality/status-claims.yaml
     superseded  -- replaced; name the superseding spec id
     When changing this value, move the previous text verbatim into a
     `**Status history**:` line rather than deleting it. -->

**Input**: User description: "Enhance the integration with AI agents (Claude Code and Codex) now that marketplaces and skills exist, and sharpen it toward the goal of an agent-driven tool. Deliver all identified gaps as a safe sequence, parallel where safe and sequential where required."

---

## Context and boundary

On 2026-07-07 the owner ratified **Option B — skill-driven packaging**
(`docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`): *"The interface stays
agent+skills (hard rule #1); the CLI stays a narrow gate. M4/M6/M7/M9/M10 are
delivered as an install/discovery/**packaging** story over the already-shipped
skills — NOT a broad verb surface."*

That decision was delivered by specs 109–113, each of which records
`**Status**: **BUILT** (docs-only)` with a `docs/user/*.md` deliverable. None of
the five mentions a bundle, a plugin, an export, or a marketplace. The
marketplace distribution (spec 125) was built afterward, on 2026-07-13, and
carried the six reviewed knowledge skills plus generated router skills and
slash-command wrappers over CLI verbs.

The two efforts never met. The result is an artifact that contradicts itself:

- `.seshat/compass.yaml` — and the fenced router prose it projects into
  `CLAUDE.md` / `AGENTS.md` — names **ten verbs the agent drives**.
- The generated bundles ship **none of those ten**. An installed agent reads the
  router, learns ten verb names, and cannot load one of them.
- The shipped router skill documents a governed MCP loop
  (`seshat_get_next_action` → act → `seshat_run_static_check` → repeat) built on
  a read-only governor that exists (`src/seshat/governor/mcp_server.py`, six
  tools) but that the plugin does not declare. Wiring it is a manual
  `claude mcp add` step documented at `docs/install/agent-install.md:172`.

This feature closes that gap. It is **packaging and truthfulness work under the
already-ratified Option B**, not a new product direction and not a re-litigation
of the A-vs-B fork.

### What this feature is NOT

- **Not a new CLI verb.** Option B keeps the CLI a narrow gate. No verb is added,
  renamed, or promoted; `_DISPATCH` is untouched.
- **Not readiness logic.** No stage moves, no gate is granted, no approval is
  self-granted, no `seshat check` rule is added or changed.
- **Not a scoring surface.** No confidence, health, maturity, or completeness
  number is emitted anywhere in this feature (hard rule #9).
- **Not a catalog submission.** Public catalog listing remains a named-owner
  action under spec 125 lanes 3–4 and is out of scope here.
- **Not a second source of truth.** Every shipped skill remains generated from
  its canonical source; no skill is forked, duplicated, or hand-maintained in a
  bundle.

### Measured starting state (verified 2026-07-31)

| Fact | Value |
|---|---|
| Skill directories under `.claude/skills/` | 50 (14 speckit, 36 other) |
| Reviewed knowledge skills under `skills/` | 6 |
| Skills carried by each generated bundle | 11 (6 knowledge + 5 generated routers) |
| Compass verbs named in `.seshat/kit-source.yaml` | 10 — all 10 have a matching skill directory, 0 ship |
| Claude slash commands in the bundle | 24 (20 canonical + 4 deprecated aliases) |
| Codex slash commands | 0 — the Codex plugin format has no prompt/command surface; skills, MCP servers and app integrations are its only component types |
| `surface: skill` entries in `docs/capabilities/capabilities.yaml` | 29 of 93 capabilities |
| Knowledge roots present in that inventory | **0 of 6** |
| `surface: skill` ids with no matching directory | **4** (`retail-govern-skill`, `run-next-readiness-skill`, `pbir-authoring-adapter-skill`, `speckit-workflow-skills`) |
| Export transforms allowed | 2 (`copy-normalized-v1`, `template-substitute-version-v1`) |
| Dev-only path references inside the 10 compass verb skills | 23 distinct |

---

## Clarifications

### Session 2026-07-31

- Q: Where should the "does this skill ship" decision be authored, given the
  public knowledge allowlist already exists as the export's input? → A: The
  inventory authors it and the allowlist is generated from it — the allowlist
  remains a committed, reviewable intermediate, with a contract test asserting
  the two agree.
- Q: Growing each bundle from 11 to roughly 43 skills adds a per-session routing
  cost. Should the specification constrain it? → A: Yes — measure the routing
  cost of the skill listing before and after, record a stated ceiling, and
  enforce it. Splitting the distribution into separate core and extended plugins
  is deferred until a measurement justifies it.
- Q: Plugin versions are single-sourced from the Python package, but four phases
  change plugin contents without changing the CLI. How should versioning work? →
  A: Stay single-sourced. No phase touches a version; publishing a phase requires
  a named-owner version approval under spec 125 lane 5, and no agent selects a
  version number.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The governed loop works the moment the plugin is installed (Priority: P1)

A user installs the Seshat BI plugin in Claude Code or Codex and asks the agent
to drive their project. The agent immediately holds the read-only governor tools
— it can ask for the current status, the one truthful next action, the named
blockers, and it can package an approval request and stop. No manual MCP
registration step is required, and no separate instruction tells the user to run
a command before the documented loop works.

**Why this priority**: This is the smallest change that converts *documented*
agent-driven behaviour into *actual* agent-driven behaviour, and it is the only
story with no dependency on any other. It is the MVP: shipped alone it delivers
standalone value. It also moves the `never_self_grant_approval` hard stop from
prose the model may drift past onto a tool surface, because packaging an approval
request becomes a callable tool with no counterpart that grants one.

**Independent Test**: Install the plugin into a clean workspace on each harness,
start a session, and confirm the governor's tools are present and answer without
any manual registration step. Then uninstall the optional runtime and confirm the
absence is reported as a named, actionable blocker rather than a silent failure
or a simulated answer.

**Acceptance Scenarios**:

1. **Given** a workspace with the plugin installed and the optional governor
   runtime present, **When** a session starts, **Then** the six read-only
   governor tools are available without the user running any registration
   command.
2. **Given** the same workspace, **When** the agent follows the documented loop,
   **Then** it can obtain a next action, re-run the static check, and reach a
   named-human gate at which it packages an approval request and stops.
3. **Given** a workspace where the optional governor runtime is **not**
   installed, **When** a session starts, **Then** the user is told exactly what
   to install, and the agent neither simulates a governor answer nor reports the
   loop as available.
4. **Given** a governed gate is blocked, **When** the agent runs the loop,
   **Then** no available tool advances a stage, grants an approval, or emits a
   score, and the loop stops at the gate rather than routing around it.

---

### User Story 2 - The capability inventory and the export gate tell one truth (Priority: P2)

A maintainer asks what Seshat BI can do and which of those capabilities the
public bundles carry. Today the inventory that claims to list everything omits
the only skills that actually ship, four of its skill ids match no directory on
disk, and the export gate is a hand-written list of six names. After this story
there is one reconciled answer: the inventory names every skill, each skill
resolves to a real directory, and what ships is derived from that inventory by
rule rather than transcribed by hand.

**Why this priority**: It is the enabling refactor for User Stories 3 and 4, and
it repairs a live truthfulness defect in the inventory independent of anything
that ships afterwards. It is sequenced second because it delivers no new agent
capability on its own — its value is that it makes the later payload changes
mechanical, reviewable, and permanently drift-proof.

**Independent Test**: Repair the inventory and replace the hand-written gate with
the derivation, then regenerate both bundles from a clean tree and confirm the
committed bundle bytes are unchanged. A byte-identical regeneration is the proof
that a fail-closed governance gate was refactored without altering behaviour.

**Acceptance Scenarios**:

1. **Given** the repaired inventory, **When** it is read, **Then** every reviewed
   knowledge skill and every skill directory that is not excluded appears exactly
   once, and every `surface: skill` entry resolves to an existing directory.
2. **Given** the derived allowlist with only the currently-shipped skills marked
   as shipping, **When** both bundles are regenerated from a clean checkout,
   **Then** the regenerated output is byte-identical to what is committed.
3. **Given** an inventory entry marked as shipping, **When** the export runs and
   no corresponding bundle file would be produced, **Then** the export fails with
   a named reason rather than silently omitting it.
4. **Given** a skill directory that appears in neither the inventory nor the
   exclusion list, **When** the export runs, **Then** it fails with that
   directory named, so a new skill cannot be added without a deliberate
   ship-or-exclude decision.

---

### User Story 3 - The ten compass verbs the agent is told to drive are loadable (Priority: P3)

A user installs the plugin into a fresh workspace that does not contain the
Seshat development repository. The agent reads the compass, learns the ten verbs
it drives, and can load every one of them. The onboarding, mapping-gate,
contract, warehouse, validation and governance procedure the agent needs is
present in the workspace, and nothing it loads instructs it to read a file that
exists only in the development repository.

**Why this priority**: This is the story that makes a fresh install behave like
this repository, and it removes the bundle's self-contradiction. It is sequenced
after User Story 2 because it is a flag change plus a portability pass on top of
that story's mechanism.

**Independent Test**: In a workspace containing no Seshat development checkout,
install the plugin, and for each of the ten compass verbs confirm the agent loads
the skill and that every file path the skill instructs the agent to read either
exists in a scaffolded workspace or is produced by a named scaffold step.

**Acceptance Scenarios**:

1. **Given** a fresh workspace with the plugin installed, **When** the agent is
   asked to drive any verb the compass names, **Then** the corresponding skill
   loads.
2. **Given** a skill marked as shipping, **When** the export runs and that skill
   instructs the agent to read a path absent from a scaffolded workspace,
   **Then** the export fails and names the skill and the offending path.
3. **Given** a shipped skill that mentions a template, **When** the portability
   check runs, **Then** the mention passes if it names an output a scaffold step
   produces and fails if it instructs the agent to read a development-repository
   file.
4. **Given** the ten verbs ship, **When** a shipped skill reaches a judgment call
   reserved for a named human, **Then** it still stops at that gate and does not
   self-grant.

---

### User Story 4 - The remaining consumer capabilities ship (Priority: P4)

A user in a fresh workspace can reach the analysis, dashboard, evidence,
dictionary and lineage capabilities the same way they reach the core readiness
verbs, without cloning the development repository. Capabilities that exist only
to develop Seshat BI itself are absent, so the installed surface is exactly the
customer-facing product.

**Why this priority**: It completes "a fresh install equals this repository" for
the capabilities off the critical readiness path. It is sequenced last among the
payload stories because each shipped skill adds provenance and portability work,
and none of them blocks the core journey.

**Independent Test**: In a workspace containing no Seshat development checkout,
confirm every consumer capability loads and that no development-only skill is
present.

**Acceptance Scenarios**:

1. **Given** a fresh workspace with the plugin installed, **When** the installed
   skills are enumerated, **Then** every consumer-facing skill is present and no
   development-only or specification-workflow skill is.
2. **Given** a newly authored development-only skill, **When** the export runs,
   **Then** it is excluded by its recorded classification and not by a name
   pattern.

---

### User Story 5 - The published claims match the shipped artifact (Priority: P5)

A prospective adopter reads the support matrix and the install guide and sees an
accurate description of what each plugin carries, on which runtime it was
exercised, and how far its validation goes. Nothing claims a behaviour that the
new bundles have not been exercised for.

**Why this priority**: Every prior story changes what the artifact contains;
publishing unchanged claims over changed contents would make the distribution
surface untrustworthy. It is last because it can only be truthfully written once
the contents are final.

**Independent Test**: Run the shipped agent-compatibility verification for each
target and the external acceptance capture against the new bundles, then confirm
every row of the support matrix and every list in the install guide is
reproducible from that evidence.

**Acceptance Scenarios**:

1. **Given** the regenerated bundles, **When** agent-compatibility verification
   runs for each target, **Then** it reports categorical evidence with no
   unresolved structural blocker.
2. **Given** a surface changed by this feature, **When** the support matrix is
   read, **Then** its validation column states what was actually exercised and
   does not carry forward an older acceptance claim as if it covered the new
   contents.
3. **Given** the install guide, **When** it describes wiring the governor,
   **Then** the automatic path is primary and the manual registration form is
   retained only for use outside the plugin.

---

### Edge Cases

- **The optional governor runtime is missing.** The declared server cannot start.
  The user must receive a named, actionable instruction; the agent must not
  silently lose the tools, must not report the loop as working, and must not
  simulate a governor response.
- **A shipped skill names a path that a scaffolded workspace does not create.**
  The export must fail closed and name the skill and the path. Shipping a skill
  that instructs an agent to read a non-existent file is the specific failure
  this feature exists to prevent.
- **A capability entry is marked as shipping but its directory was deleted or
  renamed.** The export must fail with the entry named, rather than producing a
  bundle missing an advertised skill.
- **A new skill directory is added with no classification.** The export must fail
  rather than defaulting to ship or to exclude; the classification is a
  deliberate decision.
- **The bundle-symmetry reconciliation encounters the new artifact class.** That
  class has no wrapper template and no knowledge-allowlist entry by design; the
  reconciliation must exempt it explicitly rather than treating the absence as a
  violation or, worse, being loosened for every class.
- **A skill ships to one harness but not the other.** Both harnesses must carry
  the same skill set; a per-harness divergence must be an explicit recorded
  decision, not an artefact of two code paths.
- **Two phases are merged out of order.** Each phase must be independently
  releasable and safe to merge alone; a phase that depends on an earlier one must
  fail closed if that dependency is absent rather than degrading quietly.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Truthful inventory (User Story 2)

- **FR-001**: The capability inventory MUST contain an entry for every reviewed
  knowledge skill currently carried by the bundles; today six such skills ship
  and none is listed.
- **FR-002**: Every capability entry whose surface is a skill MUST resolve to an
  existing skill directory; where the entry id and the directory name differ, the
  entry MUST record the directory explicitly rather than relying on the id.
- **FR-003**: Every capability entry whose surface is a skill MUST record whether
  it ships in the public bundles, and MUST record which authority classified it
  (a compass verb, a reviewed knowledge root, or a consumer capability).
- **FR-004**: Skill directories that exist to develop Seshat BI itself MUST be
  recorded as excluded by that recorded classification, never by a filename
  pattern or a hard-coded name list.
- **FR-005**: The inventory MUST remain read-only, gate-free and score-free; this
  feature adds no rule, no readiness effect, and no numeric value to it.

#### Derived export gate (User Story 2)

- **FR-006**: The export MUST derive the set of skills it carries from the
  capability inventory. The hand-written six-name assertion in the export script
  MUST be replaced, not supplemented.
- **FR-006a**: The capability inventory is the single **authored** source of the
  ship decision. The public knowledge allowlist MUST be **generated** from it and
  MUST remain committed, so that a reviewer reads a compact per-root diff of what
  became shippable rather than inferring it from the full inventory. A contract
  test MUST assert the generated allowlist and the inventory agree, and a
  hand-edit of the generated allowlist MUST fail that test rather than silently
  taking effect.
- **FR-007**: The derived gate MUST remain fail-closed: an entry marked as
  shipping with no producible bundle file, a shipping entry whose directory is
  missing, and a skill directory absent from both the inventory and the exclusion
  set MUST each fail the export with the offending name reported.
- **FR-008**: The change that introduces the derivation MUST leave the bundle
  contents unchanged. Regeneration from a clean checkout MUST be byte-identical
  to the committed bundles, and the existing clean-regeneration contract test is
  the acceptance evidence for this requirement.
- **FR-009**: Both generated bundles MUST carry the same skill set unless a
  divergence is explicitly recorded in the inventory with a reason.

#### Governor bundling (User Story 1)

- **FR-010**: Each generated plugin MUST declare the read-only governor as a
  bundled component, so that enabling the plugin makes the governor's tools
  available without a manual registration step on either harness.
- **FR-011**: The declaration MUST expose only the existing six read-only tools.
  This feature adds no tool, and no declared tool may advance a stage, grant an
  approval, write a readiness artifact, or emit a score.
- **FR-012**: When the optional governor runtime is absent, the failure MUST be
  reported to the user as a named, actionable instruction naming what to install;
  it MUST NOT be silent, and the agent MUST NOT simulate governor output.
- **FR-013**: The public command surface MUST gain an artifact class for bundled
  servers, and its symmetry reconciliation MUST exempt that class explicitly on
  the stated ground that such a component has no wrapper template and no
  knowledge-allowlist entry. The exemption MUST be scoped to that class alone.
- **FR-014**: The install guide MUST present automatic wiring as the primary path
  and retain the manual registration form only for use outside the plugin.

#### Shipping the compass verbs (User Story 3)

- **FR-015**: Every verb named in the canonical kit source MUST ship in both
  bundles. The compass MUST NOT name a verb whose skill the bundle omits, and
  this correspondence MUST be asserted by a contract test so the two cannot drift
  apart again.
- **FR-016**: A new fail-closed export transform MUST reject any shipping skill
  that instructs the agent to read a path absent from a scaffolded workspace,
  naming both the skill and the path.
- **FR-017**: A reference to a template MUST pass the portability check when it
  names an output that a scaffold step produces, and MUST fail when it instructs
  the agent to read a development-repository file. Resolution is per reference,
  not per path prefix.
- **FR-018**: Each of the 23 known dev-only references MUST be resolved by
  rewriting the canonical skill source. Automatic removal of content at export
  time is prohibited, because it would let a generated skill diverge silently
  from its source.
- **FR-019**: Shipping a skill MUST NOT change its governed behaviour: every hard
  stop, human-approval gate and refusal it carries in this repository MUST be
  carried unchanged into the bundle.

#### Shipping the remaining consumer capabilities (User Story 4)

- **FR-020**: Every consumer-facing skill not covered by FR-015 MUST ship, marked
  by the same recorded classification and subject to the same portability check.
- **FR-021**: Specification-workflow skills and development-only skills MUST NOT
  ship.
- **FR-021a**: The per-session routing cost a bundle imposes — the material an
  agent must hold merely to know which skills exist, before invoking any of them
  — MUST be measured for the bundle as it ships today and for the bundle after
  each payload story. A ceiling MUST be recorded as a reviewed number, and
  exceeding it MUST fail rather than pass with a note. Splitting the
  distribution into separate core and extended plugins is explicitly deferred:
  it MUST NOT be undertaken unless a recorded measurement shows the ceiling
  cannot otherwise be met.
- **FR-021b**: Skill bodies MUST remain loaded on demand. No story in this
  feature may make a skill's full text part of what an agent holds before it
  invokes that skill.

#### Published claims (User Story 5)

- **FR-022**: Agent-compatibility verification MUST be run for each target
  against the regenerated bundles, and external acceptance evidence MUST be
  captured for both harnesses.
- **FR-023**: The support matrix and install guide MUST be updated to describe
  the new contents, and MUST NOT carry an older acceptance claim forward as
  though it covered them.
- **FR-024**: Public catalog submission MUST remain a named-owner action and MUST
  NOT be performed, prepared for submission, or implied as complete by this
  feature.
- **FR-024a**: Plugin and marketplace versions MUST remain single-sourced from
  the Python package version, and no story in this feature may introduce an
  independent version line for the plugins. No story may change a version value.
- **FR-024b**: Publishing any story's contents MUST require a named-owner version
  approval under the existing release lane discipline. No agent may select,
  propose as final, or ratify a version number, create a tag, or publish a
  release.

#### Sequencing

- **FR-025**: Each of the five stories MUST be independently releasable and safe
  to merge alone. User Story 1 has no dependency on the others and may proceed in
  parallel with them; User Stories 3 and 4 depend on User Story 2 and MUST fail
  closed rather than degrade if merged without it.
- **FR-026**: No implementation may begin until this specification is ratified by
  a named human. While `specs/137-finance-gl-genericity-proof` is also awaiting
  ratification, at most one of the two may be in implementation at a time.

### Key Entities

- **Capability entry**: one reviewed record of a thing Seshat BI can do. For a
  skill it names the capability, its surface, its authority, its skill directory,
  the classification authority that placed it, and whether it ships publicly.
- **Ship classification**: the recorded reason a skill does or does not reach the
  public bundles — compass verb, reviewed knowledge root, consumer capability, or
  development-only. It is the single input the export consults.
- **Bundle artifact class**: a kind of file a generated bundle may contain.
  Today: commands and skills. This feature adds bundled servers, which carry a
  different symmetry contract from the other two.
- **Portability finding**: one instance of a shipping skill instructing the agent
  to read a path a scaffolded workspace does not have. Each is resolved by
  rewriting the canonical source; each is reported by name when it blocks.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a workspace containing no Seshat development checkout, an agent
  with the plugin installed can load **every** verb the compass names — from ten
  of ten unloadable today to ten of ten loadable.
- **SC-002**: A user reaches the governed loop with **zero** manual wiring steps,
  down from one documented registration command.
- **SC-003**: The number of shipped skills that instruct an agent to read a path
  absent from a scaffolded workspace is **zero**, and this is enforced by a
  failing export rather than by review.
- **SC-004**: Regenerating both bundles at the gate-refactor step produces output
  **byte-identical** to what is committed, demonstrating the governance gate was
  changed without changing behaviour.
- **SC-005**: Every skill directory in the repository is either shipped or
  excluded by a recorded classification — **no** directory is unclassified, and
  adding one without a decision fails the export.
- **SC-006**: The capability inventory accounts for **every** skill the bundles
  carry, up from none of the six shipped today.
- **SC-007**: Both harnesses carry the **same** skill set, with any divergence
  explicitly recorded and justified.
- **SC-008**: Every governed hard stop and human-approval gate observable in this
  repository is observable in a fresh installed workspace, with **no** refusal
  weakened by shipping.
- **SC-009**: Each published claim about bundle contents is reproducible from
  captured acceptance evidence for the bundles as shipped, with **no** claim
  carried forward from an earlier bundle.
- **SC-010**: The per-session routing cost of each bundle is a recorded number
  both before and after every payload story, and stays at or under the reviewed
  ceiling. This is a measurement of size, not a score of quality, and no
  confidence, health or maturity value is derived from it.

---

## Assumptions

- **Both harnesses support bundled servers.** Confirmed from primary sources: one
  platform's official plugins reference states that servers may be declared in a
  root configuration file or inline in the manifest and start automatically when
  the plugin is enabled; on the other, an upstream issue records a plugin's server
  registering automatically in the runtime, observable through that runtime's own
  list and get commands, with the entrypoint returning a valid initialize
  response. Two constraints follow and are carried into the contract: the
  declaration's wrapper key MUST be the camelCase form (the snake_case form in one
  published example is unparsed and yields a server that silently never loads),
  and acceptance MUST be verified at the runtime rather than in a settings pane
  (a known open defect hides the server from one platform's settings UI while it
  works). A live, version-specific confirmation is still required before
  implementation; a negative result there re-scopes User Story 1 rather than
  prompting a workaround.
- **Codex has no prompt or slash-command surface, and this is a platform
  property, not a gap.** Grounded in this repository's own evidence: the v0.3.1
  public acceptance record describes installing "the skills-only plugin" on
  codex-cli 0.144.5, and the generated Codex bundle has no commands directory
  while the Claude bundle does. The shipped router's statement that there are no
  Codex slash commands is therefore correct and is retained. Harness parity in
  this feature means the same skills and the same bundled server, not the same
  commands.
- **A scaffolded workspace creates `mappings`, `warehouse/migrations`, `powerbi`,
  `reports` and `evidence`, and does not create a templates directory.** Template
  material reaches a workspace through an explicit scaffold step, which is why
  FR-017 resolves template references by intent rather than by prefix.
- **The capability inventory is the right derivation source once repaired.** It
  is not usable as-is: it omits all six shipped knowledge skills and four of its
  skill ids match no directory. FR-001 and FR-002 repair exactly those defects,
  which is why the repair is sequenced before the derivation.
- **Agent-compatibility verification already exists** (spec 129, implemented) and
  is reused rather than rebuilt. It inspects the installed bundle and its static
  governance contract; it does not drive a live model.
- **The A-versus-B fork is settled.** Serving skill content through a governor
  tool instead of shipping skills was considered and rejected: it re-centralises
  the product on the CLI that Option B ratified away from, and it forfeits the
  agent's own skill-index routing.
- **This is packaging, not capability.** Every skill this feature ships already
  exists, is already reviewed, and already carries its gates. Nothing here
  authors a new capability, and the number of capabilities Seshat BI has is
  unchanged by it.
