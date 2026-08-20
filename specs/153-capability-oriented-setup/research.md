# Phase 0 Research: Capability-oriented setup

**Feature**: `specs/153-capability-oriented-setup/` | **Date**: 2026-08-20

Verified against the repository, not inferred from naming.

## R1 -- What counts as project evidence? (SETTLED -- it already exists)

Three axes, each carried by an artifact that is ALREADY committed. No new
declaration file is needed, and authoring one would be a second registry by
another name (FR-011).

| Axis | Evidence | Status |
|---|---|---|
| Declared data source | `mappings/<table>/source-map.yaml` -> `meta.source_system` (e.g. `kaggle_retail_store_sales_dirty`), plus `meta.table_id` and the schema/DB named in the header | committed, per table |
| Declared BI destination | presence of a PBIP project -- `powerbi/*.pbip` (verified: `powerbi/RetailStoreSales.pbip`) | committed |
| Already satisfied | the existing discovery surface (spec 148: obtained / activated / discoverable) | shipped |
| Intended workflow | artifact presence/absence, enumerable from `git ls-files` | committed |

**What `.seshat/` does NOT carry.** `.seshat/manifest.yaml`, `compass.yaml`, and
`kit-source.yaml` are KIT metadata (kit name, version, verb list, hard-stops) --
not project declarations. `manifest.yaml` lists kit source paths. So the project
evidence is in `mappings/`, `powerbi/`, `dbt/`, and `orchestration/`, not in
`.seshat/`. Reaching for `.seshat/` would have been the natural wrong guess.

### Absence IS evidence, and it is deterministically checkable

My first pass assumed "intended workflow" had no committed declaration, and that
Transformation Engine / Orchestration would therefore have to report
`undetermined`. **That was wrong, and it mattered**: it would have contradicted
spec 153's own ratified US1 AS1 ("Orchestration is `not-required`"), because
`not-required` and `undetermined` are different values in the four-value
vocabulary. Writing tasks under that assumption would have encoded a spec/plan
mismatch into the build.

Verified by enumeration instead of argument:

| Capability | Evidence checked | This repo |
|---|---|---|
| Transformation Engine | `dbt_project.yml` in committed files | **present** (`dbt/dbt_project.yml`) |
| Orchestration | `orchestration/dagster/` in committed files | **present** (37 files) |
| Database Connectivity | `mappings/*/source-map.yaml` `meta.source_system` | present |
| Power BI Integration | `powerbi/*.pbip` | present (`RetailStoreSales.pbip`) |

Because each check is a deterministic query over committed state, a NEGATIVE
result is a finding with a citable basis, not a guess: "no `dbt_project.yml` is
committed" is evidence the project is not doing transformation work.

**Therefore `not-required` is derivable from verified absence**, and FR-005's
`undetermined` is reserved for its actual case: evidence that is contradictory or
unreadable (e.g. a `source-map.yaml` that exists but cannot be parsed, or a
declared destination contradicting the artifacts present). Every reason -- positive
or negative -- must name the artifact it consulted.

Spec 153's US1 AS1 and AS3 hold as ratified. No amendment required, and the MVP is
full-width across all four capabilities.

## R2 -- Capability vocabulary (SETTLED)

Two existing sources; use both for their respective halves, duplicate neither.

- **Capability NAME + description**: `docs/capabilities/capabilities.yaml` (spec
  118, ~114 entries). Read-only by design; its `requirements` field is a coarse
  categorical tag (`[]` / `database` / `optional-dependency` / `external-runtime`)
  -- NOT a resolvable dependency spec, so it cannot by itself say which component
  satisfies a capability.
- **Capability -> component mapping**: the integration catalog's `Component`
  entries. The catalog is the authority on what is installable
  (`catalog.py`, spec 144 FR-001).

The join between them is this feature's own derived state. Neither file is edited.

## R3 -- Where strength lives (SETTLED)

Strength is per-capability PER PROJECT, so it is **derived state, not catalog
state**. No `Component` field is added -- doing so would put a project-specific
fact in a shared registry and force one project's judgment on every other. Strength
is computed alongside its reason and returned in the plan row.

## R4 -- Satisfied-state source (SETTLED)

Reuse the spec 148 discovery surface, which already separates *obtained* from
*activated* from *discoverable*. FR-019 forbids inferring satisfaction from
installation success, and spec 148 exists precisely to make that distinction, so
this is reuse rather than a new check.

## R5 -- Reason text (SETTLED)

Catalog `role` strings are provider-first: "Postgres adapter for the dbt engine",
"dbt MCP server, launched through uvx at an exact version". Verified by reading
`catalog.py`. They are correct for the EVIDENCE layer (FR-013) and wrong for the
normal path (FR-012), which must name no package.

**Decision**: capability-first reason text is authored by this feature, keyed to
the capability and the evidence that triggered it (e.g. "a relational source is
declared in mappings/retail_store_sales/source-map.yaml"). Catalog `role` strings
stay where they are and surface only on explicit technical-detail request. Copying
them into the normal path would violate FR-012 while looking like reuse.

## Consequence for scope

Derivation is viable for **all four** illustrative capabilities, each from
committed evidence and each with a citable reason:

- Database Connectivity -- a source-map declares a source system
- Power BI Integration -- a PBIP project exists
- Transformation Engine -- a `dbt_project.yml` is (or is not) committed
- Orchestration -- an `orchestration/dagster/` project is (or is not) committed

Zero capabilities guessed. `undetermined` remains reachable and must be tested
(contradictory or unreadable evidence), but it is not the default outcome for a
capability the project simply is not using.
