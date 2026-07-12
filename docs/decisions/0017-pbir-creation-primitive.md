# 0017 -- The PBIR compiler may CREATE pages and visual containers from an approved blueprint, bounded

- **Date:** 2026-07-12
- **Status:** **Accepted -- RATIFIED by Ahmed Shaaban (owner) on 2026-07-12.** The owner
  ratified spec 123 and directed implementation of the full spec ("implement all spec 123"),
  which requires the blueprint->PBIR compiler (US7). This ADR authorizes the *creation*
  primitive that ADRs 0015 and 0016 deliberately excluded. The compiler/allow-list/tests are
  enumerated future work in `specs/123-governed-dashboard-intelligence/tasks.md`; this decision
  ships no PBIR by itself.
- **Roadmap feature:** spec 123, US7 (blueprint->PBIR compiler). Extends the formatting-only
  (ADR 0015, RATIFIED 2026-07-05) + geometry (ADR 0016, RATIFIED 2026-07-06) adapters to a
  *bounded* creation capability. A/B/C/D restyle/reposition visuals a human already authored;
  creation is the genuinely new surface both prior ADRs explicitly refuse.
- **Authority category (F024):** Execution / **Authoring** Adapter, `local-file` (same category
  as ADR 0015/0016 -- NOT DB-connected, NOT publish-capable, stops at committed on-disk PBIR).
- **Context:** ADR 0016 §2 states the adapter "MUST NOT ... **create** a visual, delete a
  visual, or add/remove a page -- creation is authoring truth, not laying out existing truth."
  US7 needs exactly that: compiling an *approved* blueprint into new PBIR page shells and
  visual containers. Reading 0015/0016 as already covering creation would be the agent
  self-granting an expansion of its own authority (Principle V). This ADR is the owner's named
  grant that closes the question: **may the compiler create a page/visual, and under what
  boundary?**

## Decision (RATIFIED)

### 1. What is lifted: creation of pages + visual containers declared by an APPROVED blueprint

The compiler (`src/seshat/pbir_compile.py` + per-increment submodules) may create:

> - a new **page** (`page.json` + `pages.json` registration) declared by an approved
>   `report-composition.yaml` / `dashboard-page-blueprint.yaml`;
> - a new **visual container** (`visual.json`) declared by an approved `visual-spec.yaml`,
>   bound ONLY to a metric contract + semantic field that appear on the approved
>   `visual-contract-binding-map.md`.

Everything downstream of creation (theme, per-visual formatting, page background, geometry)
is delegated to the four shipped adapters (ADR 0015/0016) -- the compiler adds no second
formatting engine.

### 2. The hard exclusions (the load-bearing part -- creation is bounded)

The compiler MUST NOT, even under this lift:

> - create a visual **not declared** in an approved visual-spec, or bound to a field
>   **absent from the approved binding-map** (`blocked-orphan` -- route upstream);
> - create any element without a **verified Desktop-authored reference sample** for that
>   element type (FR-029; the Increment-C "hold until real sample" precedent). No JSON
>   guessing. Increments with no verified sample stay BLOCKED (tasks T039-T042);
> - redefine a metric, write DAX, or touch the semantic model (that is the metric-contract /
>   model layer, guarded byte-identical by FR-003 wherever an existing visual is touched);
> - mint a **non-deterministic** id -- page/visual `name` values are derived deterministically
>   from the blueprint element's stable id (e.g. a truncated hash of `report_id` + element
>   slug), never random/time-based (FR-027 / US7 determinism);
> - leave a **partial write** after failure -- the compiler stages the complete file tree,
>   validates the batch, then commits; on failure it writes nothing (recovery net:
>   `git checkout -- <report-dir>`);
> - **publish** to the Power BI Service, refresh, export, or schedule (F016 remains the
>   deferred, unbuilt owner of live publish).

### 3. Per-increment creation allow-list (docs-first; each ships only with its verified sample)

| Increment | Creates | Verified sample status | Buildable |
|---|---|---|---|
| 1 page shells | `page.json` + `pages.json` entry | live `RetailStoreSales.Report` empty page (real Desktop save) | **YES** |
| 3 lineChart | `visual.json` (lineChart) | data-goblin `visual_fmt.Report` fixture | **YES** |
| 2 KPI cards | `visual.json` (card) | none (placeholder only) | **BLOCKED** -- owner sample |
| 3 column/bar | `visual.json` (columnChart/barChart) | none (placeholder only) | **BLOCKED** -- owner sample |
| 4 slicers + nav | slicer `visual.json` + bookmark/nav | none | **BLOCKED** -- owner sample |
| 5 interactions | interaction wiring | none | **BLOCKED** -- owner sample |

### 4. Determinism, reversibility, validation

Inherited verbatim from the shipped adapters: `json.dumps(sort_keys=True, indent=2) + "\n"`
serialization; stage->validate->commit; refuse-overwrite-without-force; path-traversal guard;
FR-003 query/visualType snapshot wherever an existing visual is touched. Reversibility is the
reviewable git diff (ADR 0016 §5), extended by the multi-file staged-tree-then-commit rule in
clause 2.

## Alternatives considered

- **Read ADR 0015/0016 as already covering creation.** Rejected -- both explicitly exclude it
  ("creation is authoring truth"); acting on that reading would be the agent self-granting
  authority (Principle V).
- **Treat the per-blueprint `dashboard_blueprint_approval` as sufficient.** Rejected -- that
  authorizes a specific blueprint's *content*, not the kit's *standing authority* to write PBIR
  structure. The kit-wide question belongs at the ADR layer, ratified once, reused per compile.
- **Allow creation of any visual type immediately.** Rejected -- FR-029 + the Increment-C
  precedent require a verified Desktop sample per type; guessing wire formats was proven wrong
  before.

## Ratification

The owner (Ahmed Shaaban) directed ratification of this ADR by name on 2026-07-12, as part of
authorizing implementation of the full spec 123. The agent drafted this ADR and never
self-granted the creation authority; the grant is the owner's named action recorded here and in
`specs/123-governed-dashboard-intelligence/ratify-ledger.md`.
