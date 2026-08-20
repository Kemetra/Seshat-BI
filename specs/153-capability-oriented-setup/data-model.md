# Data Model: Capability-oriented setup

**Feature**: `specs/153-capability-oriented-setup/` | **Date**: 2026-08-20

## Capability

A provider-independent ability a project needs. Four in this slice:

| id | Display name | Evidence that decides it |
|---|---|---|
| `database-connectivity` | Database Connectivity | a `mappings/*/source-map.yaml` declaring `meta.source_system` |
| `powerbi-integration` | Power BI Integration | a `powerbi/*.pbip` project |
| `transformation-engine` | Transformation Engine | a committed `dbt_project.yml` |
| `orchestration` | Orchestration | a committed `orchestration/dagster/` project |

**Why this list is not a second registry** (FR-011): these are the *setup*
capabilities a project can need. `docs/capabilities/capabilities.yaml` (spec 118)
is a different thing entirely -- it enumerates the KIT's own ~114 capabilities
(CLI verbs, skills, adapters) with `state`/`authority`/`surface`. Neither file
lists the other's contents, so there is nothing to duplicate. Which concrete
provider satisfies a capability remains the integration catalog's business.

## RequirementStrength

Exactly four values. Not extensible in this slice:

- `required` -- the project cannot proceed without it
- `recommended` -- advised, with the evidence that advises it
- `optional` -- available, not indicated
- `not-required` -- verified absent evidence; the project is not doing this work

`undetermined` is **NOT** a fifth strength. It is a separate evidence marker on the
row, used when evidence is contradictory or unreadable (FR-005). Keeping it off
the strength enum is what makes `not-required` reachable and US1 AS1 testable --
if "not using it" collapsed into `undetermined`, `not-required` would never fire.

## DerivationEvidence

The committed facts consulted, per capability: which artifact was looked for,
whether it was found, and its path when found. A reason is rendered from this, so
every reason -- positive **or negative** -- cites a real artifact:

- found: "a relational source is declared in `mappings/retail_store_sales/source-map.yaml`"
- not found: "no `dbt_project.yml` is committed"

Read-only. No network, no database, no writes (FR-004).

## SetupPlanRow

| Field | Meaning |
|---|---|
| `capability` | the `Capability` |
| `strength` | one of the four values |
| `reason` | capability-first prose citing evidence; names no package (FR-008, FR-012) |
| `satisfied` | whether it is already in place -- from the discovery surface, never from install success (FR-019) |
| `undetermined_evidence` | set only when evidence is contradictory/unreadable; names what is missing (FR-005) |
| `blocker` | set when a `required` capability is declined (FR-010) |

## SetupPlan

The ordered rows plus a count of what needs setup. Renders two ways:

- **normal**: capability names and reasons only. No package, MCP, npm, or runtime
  identifier; no install command (FR-012).
- **technical detail, on explicit request**: the satisfying provider, its
  compatibility/version state, and the verification basis -- sourced from the
  control plane, never recomputed here (FR-013).

Machine-readable form carries strength, satisfied, reason, and any
blocker/undetermined marker -- enough to answer what is needed, what is
satisfied, what is missing, why something is recommended, and the next safe
action, without exposing provider internals (FR-015).

## What this model deliberately does NOT contain

- No `Component` field. Strength is per-project derived state; putting it in the
  shared catalog would force one project's judgment onto every other (FR-011).
- No installer, resolver, verifier, or state store (FR-017).
- No approval decision and no caller-supplied authorization boolean. Authorization
  is the #671 gate's outcome, consumed not re-decided (FR-018, permanent).
- No persisted derivation. It is recomputed from committed evidence each time,
  which is what makes FR-003's repeatability free.
