# Implementation Plan: Capability-oriented setup ("Seshat Setup")

**Branch**: `153-capability-oriented-setup` | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/153-capability-oriented-setup/spec.md`

**Prerequisite: SATISFIED.** Issue #671 landed on `main` (`b456577c`, PR #678).
`seshat integrations setup --apply` now requires a committed named-human
`governance` approval read at HEAD, so the authorization outcome this feature
consumes is the STRONG one. FR-018 remains a permanent boundary regardless.

## Summary

Add a derivation and presentation layer ABOVE the shipped integration control
plane. Three things, and nothing else:

1. derive the needed capability set from project evidence rather than a profile;
2. attach a requirement strength (required / recommended / optional /
   not-required) plus the reason that produced it;
3. present capabilities by name and reason, with provider detail available only
   on explicit request.

Provisioning, compatibility resolution, discovery, verification, lock/state
recording, and authorization are NOT touched. They are owned by spec 144's
control plane, spec 148's discovery facts, and (now) the #671 approval gate.

## Technical Context

**Language/Version**: Python 3.13 (repo floor 3.11)

**Primary Dependencies**: none added. Reads `seshat.integrations.catalog`
(`Component`, `PROFILES`, `profile_components`) and, for satisfied-state,
the existing discovery surface.

**Storage**: none new. Derivation is computed, not persisted. Per-project
provisioning state remains the existing lockfile's business.

**Testing**: pytest. Unit tests for derivation, strength, and presentation.

**Target Platform**: cross-platform CLI. CI is Linux -- no assertion may key on
a Windows literal.

**Project Type**: CLI within an existing library.

**Performance Goals**: N/A -- derivation reads committed project declarations.

**Constraints**: derivation MUST be network-free and write-free (FR-004). It must
work with no optional provider installed (SC-009).

**Scale/Scope**: ~2 new modules, ~1 CLI presentation path, no new verb, no new
flag beyond an opt-in selector, ~20 tests.

## The seam

`src/seshat/integrations/installer.py:268` is `plan(root, *, profile=DEFAULT_PROFILE, ...)`.
Selection enters there as a profile name. This feature adds a step UPSTREAM that
produces a component set from project evidence; the planner is unchanged.

Critically, `DEFAULT_PROFILE` is an exported public constant whose value is part
of the contract (spec 144 FR-006), so **the default is not changed**. Derivation
is offered as an additional selection basis, per spec 153 FR-002 and owner
decision 1. Displacing the default would be a separate, explicitly-amended
change.

## Constitution Check

*GATE: passes.*

| Principle | Assessment |
|---|---|
| I. Agent-First, Gate-Enforced | Honored. Adds a read-only derivation; the gate's exit code stays the authority. |
| II. Depend, Never Fork | Honored. No provider is reimplemented; this only decides which official ones a project needs. |
| V. Agent Stops at Judgment Calls | Honored, and load-bearing: FR-005 forbids defaulting an underivable capability to `required`. Insufficient evidence is REPORTED, never guessed. |
| VIII. Static-First, Live Deferred | Honored. Derivation is pure committed-text reading -- no DB, no network (FR-004). |
| IX. Secrets and Reproducibility | Honored: FR-016 forbids any secret in presentation or machine-readable output. |

No principle weakened; no amendment required.

## Phase 0 -- Research

1. **R1 -- What counts as project evidence?** FR-001 names declared data sources,
   declared BI destination, intended workflow, and already-satisfied
   capabilities. Determine which committed artifacts actually carry these today
   (candidates: the readiness/source-map artifacts, PBIP presence, `contracts/`
   declarations, `.seshat/` project config). **Do not invent a new declaration
   file if one already carries the fact** -- that would be a second registry by
   another name.

2. **R2 -- Capability vocabulary.** FR-011 forbids a registry separate from the
   existing manifest and catalog. `docs/capabilities/capabilities.yaml` (spec 118)
   has ~114 entries with a `requirements` field; the integration catalog has
   `Component` with a provider-first `role` string. Decide which is the capability
   NAME source and how a capability maps to catalog components. Neither may be
   duplicated.

3. **R3 -- Where strength lives.** FR-007/FR-011 need a strength per capability
   PER PROJECT. It is therefore derived state, not catalog state -- confirm no
   `Component` field is added, and that strength is computed alongside the reason.

4. **R4 -- Satisfied-state source.** FR-019 forbids inferring satisfaction from
   installation success. Confirm the exact discovery/verification call that
   answers "is this capability already satisfied" and reuse it.

5. **R5 -- Reason text.** Catalog `role` strings are provider-first ("Postgres
   adapter for the dbt engine"). FR-008/FR-012 need capability-first reasons
   naming no package. Decide where that text lives so the evidence layer keeps
   the provider detail (FR-013) while the normal path never shows it.

## Phase 1 -- Design

**data-model.md**: `Capability` (name, description), `RequirementStrength` (the
four values plus the `undetermined` evidence marker -- NOT a fifth strength),
`DerivationEvidence` (the project facts read), `SetupPlanRow` (capability +
strength + reason + satisfied + blocker), `SetupPlan`.

**quickstart.md**: the two projects from spec 153 US1 -- Postgres + Power BI, and
Postgres-only -- shown producing different derived sets, with no package name in
either rendering.

### Design invariants (each maps to a spec FR)

- Derivation is read-only and network-free. (FR-004)
- Same evidence -> same derived set and strengths. (FR-003)
- Underivable -> `undetermined` naming the missing evidence, NEVER defaulted to
  `required`. (FR-005)
- `undetermined` is an evidence marker, not a fifth strength; the vocabulary
  stays at exactly four values. (FR-007)
- No provider/package/MCP/runtime name in the normal presentation. (FR-012)
- Provider detail is sourced from the control plane on request, never
  recomputed. (FR-013)
- No second registry, installer, resolver, verifier, or state store. (FR-011,
  FR-017)
- Never treat a caller-supplied flag as approval; consume the #671 gate's
  outcome. (FR-018 -- permanent)
- Satisfaction rests on existing verification/discovery, never on install
  success. (FR-019)

## Verification Strategy

1. **Derivation must actually differ per project.** Two fixture projects of
   different shape must yield different sets. A test that passes for both shapes
   proves nothing.
2. **Absence of package names must be non-vacuous.** Assert the rendering
   contains no catalog `coordinate` value drawn FROM the catalog at test time --
   not a hardcoded list that silently stops matching when the catalog changes.
3. **`undetermined` must be reachable.** Build a project whose evidence genuinely
   cannot decide a capability, and assert it is reported, not defaulted.
4. **FR-018 needs a real test**, not a comment: assert this feature's code
   contains no approval decision and consults the gate for authorization.

## Known Risks

1. **RESOLVED in Phase 0 -- absence is evidence.** The first pass assumed
   "intended workflow" had no committed declaration, which would have forced
   Transformation Engine and Orchestration to `undetermined` and CONTRADICTED
   spec 153's ratified US1 AS1 (`Orchestration is not-required`) -- two different
   values in a four-value vocabulary. Enumeration settled it: `dbt_project.yml`
   and `orchestration/dagster/` are deterministically checkable in committed
   state, so a negative result is a finding with a citable basis, not a guess.
   All four capabilities are derivable; `undetermined` is reserved for
   contradictory or unreadable evidence. **The risk now is the reverse**: letting
   `undetermined` become a dumping ground for "not using it", which would make
   `not-required` unreachable and US1 AS1 untestable.
2. **Reason text is where provider detail leaks.** The catalog's own strings name
   packages; copying them into the normal path would violate FR-012 while looking
   like reuse.
3. **The four-value vocabulary is easy to inflate.** `undetermined` must stay an
   evidence marker; adding it as a fifth strength would contradict FR-007.

## Complexity Tracking

No new dependency, no new registry, no new CLI verb. If R1 shows project evidence
is thin, prefer reporting `undetermined` honestly over widening scope to author
new declaration files -- that would turn a presentation delta into a data-model
change the spec's non-goals forbid.
