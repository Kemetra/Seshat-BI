# Feature Specification: Secure integration provisioning approval

**Feature Branch**: `154-secure-provisioning-approval`

**Created**: 2026-08-20

**Status**: Draft

**Input**: Issue #671 -- `seshat integrations setup --apply --yes` treats an
agent-supplied CLI flag as approval for installing external software. Converge the
provisioning trust boundary onto Seshat's existing committed, named-human approval
model, and define the deliberate amendment to spec 144 FR-010 that this requires.

## The defect (reproduced, not inferred)

`_approved()` in `src/seshat/cli/commands/integrations.py` returns True for a
namespace an agent constructs for itself:

```
[PROBE] agent-supplied --apply --yes  => True     # no human, no TTY, no record
[PROBE] --yes alone (no --apply)      => False
[PROBE] --apply --json (no --yes)     => False
[MODEL-A] bare flag-ish dict          => False
[MODEL-A] named human + ISO date      => True
```

The second and third results show the existing gate works as designed for its
original threat model -- accidental installs and unattended runs. The defect is
that the threat model never treated **the agent itself** as the actor. `--yes` is
read with `getattr(args, "yes", False)`: a precondition the caller supplies, which
is not a gate.

Origin is PR #578 (`728de126`), which predates spec 144.

## Two approval models exist; provisioning uses the weaker one

| | Model A (canonical) | Model B (provisioning, today) |
|---|---|---|
| Site | `src/seshat/pbi_mcp_adapter/gate.py` | `src/seshat/cli/commands/integrations.py` |
| Signal | `approvals[]` read HEAD-only via `is_tracked_and_clean` + `committed_text` | `--apply` + (`--yes` OR TTY `confirm()`) |
| Shape | `approval_is_shape_valid()` -- named decider + authority class + ISO `at:` | none |
| Agent can self-grant | No (worktree reads rejected; bug #334) | **Yes** |

`never_self_grant_approval` is enforced mechanically across the dashboard
coordinator, mapping mirror, readiness classifier, and as static-check finding
`hs-self-grant-approval`. Provisioning is the outlier. This feature moves
provisioning onto Model A and introduces no third model.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An agent cannot authorize provisioning (Priority: P1)

An agent running in an unattended session requests provisioning with every
caller-controlled signal it can supply -- `--apply`, `--yes`, a piped stdin
answer, a simulated TTY. Provisioning is refused because no committed approval
authorizes it, and the refusal names the exact next action a human must take.

**Why this priority**: This is the security defect. It is also the smallest slice
that closes it: refusing without a committed record is valuable even before the
approval-authoring path is convenient.

**Independent Test**: Construct the agent-supplied namespace directly (as the
reproduction above does) with no committed approval present, and assert
provisioning is refused, nothing is written, no network call is made, and the
refusal carries a next action. Repeat with a piped stdin answer and with a
simulated attended terminal.

**Acceptance Scenarios**:

1. **Given** no committed approval, **when** an agent runs with `--apply --yes`,
   **then** provisioning is refused, no filesystem or network mutation occurs, and
   the refusal states what must be recorded and by whom.
2. **Given** no committed approval, **when** a TTY confirmation is answered yes,
   **then** provisioning is still refused -- an interactive answer is not authority.
3. **Given** no committed approval, **when** an answer is supplied on stdin,
   **then** provisioning is refused.
4. **Given** an approval recorded ONLY in the working tree (uncommitted, or
   committed-but-dirty), **when** provisioning is requested, **then** it is
   refused: authority is read at HEAD only.
5. **Given** any refusal in this story, **when** the machine-readable output is
   read, **then** it carries a categorical refusal reason and a next action.

---

### User Story 2 - A named human's committed approval authorizes a bounded scope (Priority: P2)

A named human records an approval into committed repository state, scoped to the
capability set actually being provisioned. Provisioning then proceeds -- still
subject to every existing integration gate -- and an approval for a different
scope does not authorize this run.

**Why this priority**: Story 1 makes the system safe; this story makes it usable.
It depends on Story 1's refusal path existing.

**Independent Test**: Commit a shape-valid approval for capability set X; prove
provisioning of X proceeds and provisioning of Y is refused with a scope-mismatch
reason.

**Acceptance Scenarios**:

1. **Given** a committed, shape-valid approval naming a human decider with an
   authority class and an ISO date, scoped to the requested capability set,
   **when** provisioning is requested with intent to execute, **then** it may
   proceed subject to all existing catalog, resolver, compatibility, installer,
   and verification gates.
2. **Given** a committed approval whose scope names a different capability set,
   **when** provisioning is requested, **then** it is refused with a
   scope-mismatch reason naming both the approved and requested scopes.
3. **Given** a committed approval that is malformed -- missing the decider, the
   authority class, or a parseable date; or carrying a bare role token as the name
   -- **when** provisioning is requested, **then** it is refused as invalid shape,
   using the same validation semantics that govern readiness approvals.
4. **Given** a valid committed approval, **when** the run is non-interactive,
   **then** the non-interactivity affordance suppresses prompting only and
   supplies no authority.
5. **Given** a valid committed approval and provisioning that executes, **when**
   provider verification subsequently fails, **then** the capability is NOT
   reported ready and the run is not reported successful.
6. **Given** a committed approval recorded under a per-table
   `mappings/<table>/readiness-status.yaml` path, **when** provisioning is
   requested, **then** it is refused: a table-readiness approval never confers
   provisioning authority.
7. **Given** a committed provisioning approval whose authority class is anything
   other than `governance`, **when** provisioning is requested, **then** it is
   refused as insufficient authority.
8. **Given** a partial failure under a valid approval, **when** the same approved
   scope is retried, **then** it proceeds under the original approval with no new
   approval required.
9. **Given** a successful provisioning run under a valid approval, **when** the
   same approved scope is requested again, **then** it proceeds -- the approval is
   standing, not single-use.
10. **Given** a valid approval, **when** the request materially changes scope
    (a capability added, the provider changed, the component set expanded, or the
    installation target changed in a security-relevant way), **then** provisioning
    is refused pending a new approval.
11. **Given** a previously valid approval that has been revoked, removed, or
    replaced in committed state, **when** provisioning is requested, **then** it is
    refused from that point forward.
12. **Given** a valid approval whose ISO date is old, **when** provisioning is
    requested with an unchanged scope, **then** age alone does not refuse it --
    there is no time-based expiry.

---

### User Story 3 - Authoring approval reuses the existing human path (Priority: P3)

A human asked to authorize provisioning is given the same packaged-decision
experience that already exists for readiness gates, and records the decision
through the existing approval-writing surface rather than a new one.

**Why this priority**: Stories 1-2 are the security boundary and can ship with a
hand-authored committed record. This story removes the friction and prevents a
third write path from emerging later.

**Independent Test**: Drive an approval request and its recording through the
existing approval surfaces and prove the resulting committed record is accepted by
the Story 2 gate, with no new approval-writing code path introduced.

**Acceptance Scenarios**:

1. **Given** a provisioning request needing authorization, **when** a decision
   package is assembled, **then** it is produced by the existing evidence/console
   surfaces and states the capability set, the providers implied, and the risk.
2. **Given** a named human's answer, **when** it is recorded, **then** it is
   written through the existing approval-recording surface and no second
   approval-writing path is created.
3. **Given** the recorded approval, **when** the provisioning gate reads it,
   **then** it is accepted without translation into a different vocabulary.

---

### Edge Cases

- Approval absent, malformed, undated, or naming a bare role: refused as invalid.
- Approval present in the worktree but uncommitted, or committed on a dirty path:
  refused -- HEAD-only read.
- Approval file unparseable or unreadable: refused, and not distinguished in a way
  that could be mistaken for a pass.
- Approval scope narrower than the request: refused with both scopes named.
- Approval scope broader than the request: a superset scope authorizes a subset
  request, since the subset is materially within what the human approved.
- Re-run after a successful provisioning with the same committed approval:
  permitted -- the approval is standing until scope changes (FR-012a).
- Retry after a partial failure, same scope: permitted under the original approval
  (FR-012b); execution failure alone never invalidates authority.
- Approval revoked, removed, or replaced in committed state: ceases to authorize
  from that point (FR-012d).
- Approval old but scope unchanged: still valid -- no time-based expiry (FR-012e).
- Approval recorded under a per-table readiness path: refused (FR-001a).
- Approval carrying an authority class other than `governance`: refused (FR-004a).
- Approval valid, provisioning partially fails: failed capabilities individually
  reported failed; the run is never reported successful overall.
- Approval valid, verification fails afterwards: not reported ready.
- The capability set changes after approval: the prior approval does not extend to
  newly added capabilities.
- A human is unavailable: the run stops at a stated human-action boundary and
  claims nothing.
- No secret, credential, or token appears in any refusal, evidence, or
  machine-readable output.

## Requirements *(mandatory)*

### Functional Requirements

**Authority source**

- **FR-001**: Provisioning authorization MUST come from an approval recorded in a
  **dedicated per-project committed approval artifact**. No caller-supplied runtime
  signal may constitute authorization.
- **FR-001a**: A provisioning approval MUST NOT be read from, or recorded into, a
  per-table `mappings/<table>/readiness-status.yaml` path. Provisioning authority
  is project-scoped (environment and tool changes), not table-readiness-scoped, and
  the two MUST NOT be conflated in either direction.
- **FR-002**: The approval MUST be read from HEAD only. An uncommitted working-tree
  edit, or a record on a path that is not tracked-and-clean, MUST NOT grant
  authority.
- **FR-003**: Approval shape MUST be validated by the existing canonical
  definition (`approval_is_shape_valid()` semantics: a named decider WITH an
  authority class, plus a parseable ISO date). This feature MUST NOT define a
  second approval vocabulary or a second shape validator.
- **FR-004**: The approval MUST identify a named human decider and that decider's
  authority class. A bare role token, an unclassed name, or a role masquerading as
  a name MUST be refused.
- **FR-004a**: The authority class for a provisioning approval MUST be the existing
  `governance` class, denoting the named human project-governance authority
  approving external environment/tool changes. This feature MUST NOT introduce a
  sixth authority class or otherwise widen the existing closed authority-class set.
- **FR-004b**: The `governance` authority MUST NEVER be inferred, synthesized, or
  self-granted by an agent; it is satisfied only by a committed record naming a
  human.
- **FR-005**: An agent-controlled CLI flag MUST NEVER constitute approval, in this
  or any future provisioning surface.
- **FR-006**: A TTY confirmation, a stdin response, or any other interactive or
  pipeable answer MUST NOT substitute for a committed approval.

**Intent vs authority vs execution**

- **FR-007**: The existing execute-intent flag (`--apply`) MAY continue to express
  intent to provision. Intent MUST NOT be treated as authority.
- **FR-008**: The existing non-interactivity flag (`--yes`) MAY remain solely as a
  do-not-prompt affordance. It MUST NOT create, imply, or substitute for
  authorization.
- **FR-009**: The network-access flag and the write-access flag MUST retain their
  current independent behavior; this feature adds an authorization requirement and
  removes none of the existing preconditions.

**Scope binding**

- **FR-010**: An approval MUST be bound to the capability/component set it
  authorizes. A blanket approval that authorizes any future provisioning MUST NOT
  be introduced.
- **FR-011**: A request whose capability set is not covered by the approved scope
  MUST be refused with a scope-mismatch reason naming the approved scope and the
  requested scope.
- **FR-012**: Capabilities added to a request after an approval was recorded MUST
  NOT be authorized by that approval.

**Approval lifetime (standing-until-scope-change)**

- **FR-012a**: A valid committed provisioning approval MUST remain sufficient for
  retries and repeated execution while the approved provisioning scope remains
  materially identical. Provisioning MUST NOT demand a fresh approval merely
  because a prior execution failed.
- **FR-012b**: A partial failure followed by a retry of the same approved scope
  MUST proceed under the original approval.
- **FR-012c**: The approval MUST become insufficient, requiring new human
  approval, when the requested scope changes materially -- including adding a
  capability, changing the provider, expanding the approved component set,
  changing an installation target or environment in a security-relevant way, or
  otherwise materially changing the provisioning plan.
- **FR-012d**: An approval that is explicitly revoked, removed, or replaced in
  committed state MUST cease to authorize provisioning from that point forward.
- **FR-012e**: Approval lifetime MUST NOT be governed by a time-based expiry. The
  canonical ISO date remains required for shape validity and audit, but MUST NOT be
  interpreted as an expiry clock.

**Fail-closed and reporting**

- **FR-013**: A missing, malformed, undated, stale, scope-mismatched, unparseable,
  or uncommitted approval MUST fail closed: refuse, mutate nothing, contact no
  network.
- **FR-014**: Every refusal MUST expose both a human-readable and a
  machine-readable categorical reason plus an explicit next action.
- **FR-015**: A refusal, evidence record, or machine-readable output MUST NOT
  contain a secret, credential, connection string, or token value.
- **FR-016**: Provisioning that executes under a valid approval MUST still not
  report a capability ready unless the existing verification and discovery surfaces
  confirm it. Authorization is not verification.

**Reuse and non-duplication**

- **FR-017**: Human approval authoring and pre-approval evidence MUST route
  through the existing approval-console / approval-evidence-pack surfaces. No
  third approval-writing path may be created.
- **FR-018**: The existing integration catalog, resolver, compatibility policy,
  installer, lockfile, and discovery behavior MUST remain intact except where this
  trust-boundary change directly requires otherwise.
- **FR-019**: CLI compatibility MUST be preserved wherever it does not conflict
  with the security requirement: flags, exit codes, and JSON shape remain, and only
  the authorization semantics of the approval signal change.

**Amendment**

- **FR-020**: This feature MUST explicitly amend spec 144 FR-010 (see the
  Amendment section) rather than silently violating it, and the amendment MUST be
  recorded in spec 144's own artifact when this feature is ratified.

### Key Entities

- **Provisioning approval**: A record in a dedicated **per-project** committed
  approval artifact authorizing a bounded capability set to be provisioned,
  carrying a named human decider, the `governance` authority class, and an ISO
  date. Reuses the canonical approval shape and validator; introduces no new
  vocabulary and no sixth authority class. Distinct from, and never satisfied by, a
  per-table readiness approval.
- **Approved scope**: The capability/component set an approval authorizes, against
  which a request is matched. Governs approval lifetime: the approval stands while
  the requested scope remains materially identical, and a superset scope authorizes
  a subset request.
- **Material scope change**: A change that invalidates a standing approval --
  adding a capability, changing the provider, expanding the component set, changing
  an installation target/environment in a security-relevant way, or otherwise
  materially changing the provisioning plan.
- **Provision intent**: The caller's request to execute (today `--apply`).
  Deliberately distinct from authority.
- **Non-interactivity affordance**: The caller's declaration not to be prompted
  (today `--yes`). Carries no authority.
- **Refusal**: A categorical, machine-readable fail-closed outcome with a next
  action.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An agent supplying every caller-controlled signal available to it --
  execute intent, non-interactivity, stdin, simulated TTY -- cannot provision
  anything without a committed approval; zero paths succeed.
- **SC-002**: An approval present only in the working tree grants no authority in
  any case tested.
- **SC-003**: Every malformed approval variant (no decider, no authority class, no
  parseable date, bare role token) is refused, judged by the same validator that
  governs readiness approvals.
- **SC-004**: A scope-mismatched approval is refused, and the refusal names both
  scopes.
- **SC-005**: A correct committed approval permits provisioning to proceed, and it
  remains subject to every pre-existing integration gate -- none is bypassed or
  weakened.
- **SC-006**: A non-interactive run with a valid committed approval completes
  without prompting and without deriving authority from the non-interactivity flag.
- **SC-007**: When verification fails after an authorized install, no capability is
  reported ready and the run is not reported successful.
- **SC-008**: Every refusal path emits a categorical machine-readable reason and a
  next action; zero silent or uncategorized refusals.
- **SC-009**: No approval-writing path exists outside the existing approval
  surfaces; the count of approval-write paths does not increase.
- **SC-010**: No output on any path contains a secret, credential, connection
  string, or token value.
- **SC-011**: The amendment to spec 144 FR-010 is recorded in spec 144's artifact,
  and no other FR-010-protected behavior (flags, exit codes, JSON shape, workspace
  validation, catalog routing) changes.
- **SC-012**: A per-table readiness approval never authorizes provisioning, and a
  provisioning approval is never written into a per-table readiness record; both
  directions are refused.
- **SC-013**: The authority-class set is unchanged in size by this feature: exactly
  the five existing classes remain, and only `governance` satisfies a provisioning
  approval.
- **SC-014**: A retry of an unchanged approved scope after either a partial failure
  or a prior success proceeds without a new approval, while every material scope
  change is refused pending new approval.
- **SC-015**: A revoked, removed, or replaced approval stops authorizing
  provisioning, and approval age alone never refuses an otherwise-valid unchanged
  scope.

## Amendment to Spec 144 FR-010

**The exact statement amended.** Spec 144, Functional Requirements, FR-010:

> "The current CLI flags, approval prompt, exit-code behavior, JSON shape,
> workspace validation, and catalog-backed routing MUST survive."

**What spec 144 intended.** Phase 2 was a control-plane *convergence*: it made the
catalog-backed planner/installer/lock the sole integration authority while
guaranteeing no observable regression for existing callers. FR-010 is that
no-regression guarantee. It preserved the approval prompt as an artifact of
compatibility; it did not design or endorse the prompt's trust model, and its own
FR-009 states that compatibility apply must "never infer approval" -- the intent
was clearly against inferred authority.

**What this feature changes.** Exactly one clause of FR-010: the **approval
prompt** ceases to be an authorization mechanism. The prompt (and the
non-interactivity flag that suppresses it) may remain as user-experience
affordances, but neither confers authority; authority moves to a committed
named-human record.

**What this feature deliberately does NOT change.** The other five clauses of
FR-010 stand unamended: CLI flags continue to exist, exit-code behavior, JSON
shape, workspace validation, and catalog-backed routing all survive. Spec 144's
FR-001..FR-009 and FR-011..FR-013 are untouched.

**Why an amendment rather than a defect fix.** Because FR-010 is a ratified
compatibility guarantee, changing the prompt's authority is a deliberate narrowing
of a ratified requirement, not the correction of an implementation slip. Treating
it as a bug fix would silently contradict a ratified spec -- the pattern this
repository has been bitten by before. On ratification of this spec, spec 144's
FR-010 MUST be annotated to record the narrowing and point here.

## Dependencies and Sequencing

- **Blocks spec 153** (capability-oriented setup). By owner ruling (2026-08-20)
  spec 153 implementation MUST NOT begin until this feature lands, so that later
  setup work cannot couple to the weak approval path. Spec 153's FR-018 remains a
  permanent boundary and is NOT retired by this feature landing.
- **Amends spec 144** FR-010, one clause (see above). Depends on spec 144's
  catalog, resolver, installer, lock, and compatibility surfaces remaining the sole
  provisioning authority.
- **Depends on spec 148** discovery facts and the existing verification surfaces for
  FR-016 (authorization is not verification).
- **Reuses** the canonical readiness approval shape validator and the HEAD-only
  committed-read helpers already used by the Power BI MCP write gate.
- **Reuses** the approval-console (F027) and approval-evidence-pack (F035) surfaces
  for authoring and evidence (FR-017). Because owner decision 1 places the record in
  a dedicated per-project artifact, this reuse entails extending those surfaces to
  a project-scoped write target -- it does NOT entail a new approval-writing path,
  and it does NOT overload the per-table readiness record.
- **Constitution**: Principle V (a stage's approval is a named human action the
  agent cannot self-grant) and the Readiness System's same prohibition are the
  governing authority. Principle II is unaffected -- providers remain
  depended-upon, not forked.

## Out of Scope

- Any implementation. This is a specification-only artifact.
- Redesigning the integration control plane, catalog, resolver, installer, lock, or
  discovery.
- A second capability registry, approval vocabulary, shape validator, or
  approval-writing path.
- Spec 153's project-derived capability inference, requirement strength, and
  capability-oriented presentation.
- A package marketplace, a graphical installer, or a broad CLI redesign.
- Unrelated Power BI, dbt, Dagster, Studio, or memory work.

## Assumptions

- The canonical approval shape (named decider + authority class + ISO date) is
  sufficient for provisioning. Its location (a dedicated per-project artifact), its
  authority class (`governance`), and its lifetime (standing-until-scope-change)
  are all settled by the owner rulings recorded below.
- Existing integration gates (`--refresh` for network, `--apply` for write) remain
  necessary; this feature adds authorization as an additional requirement and
  relaxes nothing.
- Provisioning is a per-project action, whereas the existing approval-authoring
  surfaces write per-table `mappings/<table>/readiness-status.yaml`. Per owner
  decision 1 the record lives in a dedicated per-project artifact, so FR-017's
  reuse of those surfaces implies extending them to a project-scoped target rather
  than overloading a table readiness record.
- CLI flags remain present; only the authorization semantics of the approval
  signal change.

## Owner Decisions

Both decisions are RULED. Zero remain unresolved.

### 1. RULED (Ahmed Shaaban, 2026-08-20) -- dedicated per-project artifact, `governance` class

A provisioning approval is recorded in a **dedicated per-project committed
approval artifact**. It MUST NOT be placed under a per-table
`mappings/<table>/readiness-status.yaml` path, because provisioning authority
applies to project-level environment and tool changes rather than to table
readiness.

The existing canonical approval **shape and validator are reused** unchanged
(FR-003): a named human decider WITH an authority class, plus a parseable ISO
date.

The authority class is the existing **`governance`** class. **No sixth authority
class is introduced by this feature** -- the ruling is deliberately narrow so a
security fix does not expand the global approval vocabulary.

For provisioning, `governance` denotes the **named human project-governance
authority approving external environment/tool changes**. It MUST NEVER be
inferred, synthesized, or self-granted by an agent.

*Context that made this a decision rather than a default*: both existing
approval-authoring surfaces (approval-console F027, approval-evidence-pack F035)
write into per-table `mappings/<table>/readiness-status.yaml` `approvals[]`, so the
canonical shape was reusable but the canonical *location* was not a fit; and the
closed authority-class set
`{analyst, governance, data_owner, metric_owner, report_owner}` contains no class
that plainly reads as "may install software". The ruling resolves both without
widening the vocabulary.

### 2. RULED (Ahmed Shaaban, 2026-08-20) -- `standing-until-scope-change`

A valid committed provisioning approval MAY be reused for retries and repeated
execution **only while the approved provisioning scope remains materially
identical**.

The approval becomes insufficient and requires new human approval when the
requested scope changes materially, including: adding a capability; changing the
provider; expanding the approved component set; changing an installation
target/environment in a security-relevant way; or otherwise materially changing
the provisioning plan.

A **partial failure followed by a retry of the same approved scope MUST NOT
require a new approval** merely because execution previously failed.

An approval also ceases to authorize provisioning if it is explicitly **revoked,
removed, or replaced** in committed state.

**No time-based expiry** is introduced: no existing repository authority requires
one for provisioning, and inventing one here would add a failure mode this
security fix does not need. (The canonical ISO `at:` date remains required for
shape validity and audit, but it is not an expiry clock.)
