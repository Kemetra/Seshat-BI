# Data Model: guided setup execution (spec 155)

Three new value types, all computed and none persisted. Nothing here introduces a
registry, a schema, or a committed artifact: the committed inputs
(`contracts/capability-declines.yaml`, `contracts/provisioning-approvals.yaml`) and
the machine-local state record all already exist and are owned elsewhere.

## DerivedScope

The ordered catalog component ids projected from the capabilities that need
action, plus what produced them.

| Field | Meaning |
|---|---|
| `component_ids` | `tuple[str, ...]` -- ordered, deduplicated, catalog-owned ids |
| `capabilities` | the plan rows that contributed, so every id traces to a capability |
| `excluded` | per capability, why it contributed nothing: `not-required`, `declined`, `satisfied`, `optional`, `undetermined` |
| `blockers` | `tuple[str, ...]` -- from the derived plan; non-empty means the scope MUST NOT execute |
| `unsupported` | capabilities that need action but project to no catalog component |

Rules:
- Order is deterministic (FR-006): capability order from the derived plan, then
  the projection's own order within each capability.
- `component_ids` is derived only from the derived plan, the existing projection,
  discovery state, and committed declines. No caller value contributes (FR-007).
- Empty `component_ids` with empty `blockers` is the legitimate "nothing to do"
  state, not a refusal.
- A row in `unsupported` is never reported satisfied and never silently dropped.

## CapabilityStatus

One row of the agent-facing status (FR-011). Assembled in the bridge, because it
must carry post-execution facts the derivation layer may not observe.

| Field | Source |
|---|---|
| `capability`, `strength`, `reason`, `satisfied`, `declined`, `blocker` | spec 153's derived plan, verbatim |
| `needs_setup` | the derived plan's needs-action definition |
| `proposed_action` | one of `set-up`, `already-satisfied`, `no-action`, `blocked` |
| `approval_required` | whether this capability contributes to a scope needing authorization |
| `approval_met` | the spec 154 verdict for the current scope -- never a caller assertion |
| `post_execution_status` | `ready`, `not-ready`, `failed`, `not-attempted`, decided by verification |
| `next_action` | the one safe next step, from the owning surface's own wording |

Rules:
- `post_execution_status` is `ready` only when the existing discovery/verification
  surfaces say so; an install row's success never sets it (FR-016).
- `approval_met` mirrors `ApprovalVerdict.authorized` for the exact derived scope;
  a scope change invalidates it rather than carrying it forward (FR-013).
- No field may hold a secret, credential, connection string, or token (FR-022).

## GuidedSetupResult

The outcome of one guided run: the `DerivedScope` it acted on, the per-capability
`CapabilityStatus` rows, the underlying component rows and discovery results from
the existing `SetupOutcome`, and one next action.

Rules:
- Succeeded and failed components stay individually addressable (FR-017); the
  result is never collapsed to a single boolean success.
- Reported "needs action" unions the installer's action set with the discovery
  vocabulary, matching what the compatibility facade already does -- reading only
  install rows would render an unverified component as done.

## Referenced, not redefined

- **Capability, requirement strength, derived plan, the capability-to-component
  projection, recorded declines** -- spec 153. Consumed verbatim.
- **Provisioning approval, approved scope, material scope change** -- spec 154.
  Read at HEAD by the existing gate.
- **Component, profile, resolution, compatibility policy, component plan row,
  discovery result, lock document** -- spec 144 / spec 148. The bridge passes
  component sets in and reads outcomes out; it adds no field to any of them.
