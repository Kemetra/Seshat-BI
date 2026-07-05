# PBIR-authoring adapter contract -- <adapter_instance>

> GENERIC, copy-me contract. Specializes `templates/adapter-contract.md` for the
> Power BI report-AUTHORING adapter (F034 completion, ADR 0015). It declares the
> adapter's authority category and the exact boundary of what it may write. Fill the
> placeholders per instance. ASCII only, UTF-8 no BOM.

## Authority category (F024)

- **Category:** Execution / **Authoring** Adapter, `local-file`.
- **NOT** DB-connected, **NOT** publish-capable (that is F016). Stops at the
  committed on-disk PBIR.
- **Reads:** a generated theme (`retail theme-gen` output) + the committed PBIR.
- **Writes:** committed PBIR JSON, allow-list-only (below).
- **Creates NO truth:** no metric, mapping, semantic logic, or storytelling.

## The allow-list (what this adapter MAY write) -- per increment

Growing this list is a reviewed change, never silent. Anything not listed MUST NOT
be written.

| Increment | Allowed write targets |
|-----------|----------------------|
| A (theme) | `report.json` `themeCollection.baseTheme` + its `resourcePackages` item; the BaseTheme resource file under `StaticResources/SharedResources/BaseThemes/<name>.json` |
| B (visuals) | allow-listed FORMATTING keys inside an existing `visual.json` (fill, border, title font/alignment, data-label + gridline defaults, data colors) -- NEVER data bindings/measures |
| C (background) | a page's background reference to a committed surface-2 asset (per `background-spec.yaml`) -- honoring the surface-2 purity rule |

## What this adapter MUST NOT do

- Use pbi-cli, the Power BI MCP, a live Power BI / workspace connection, or any
  network call (ADR 0015 decision 4). stdlib-only.
- Write data bindings, measures, DAX, relationships, meaning-changing filters, or any
  semantic-model file (formatting/wiring only).
- Create a data-bound visual with no backing approved contract (surface-1 orphan).
- Move any readiness stage to `pass` or emit a numeric confidence/health/maturity
  score (hard rule #9). A successful write is EVIDENCE, never approval.
- Publish or refresh a live workspace (that is the parked F016 adapter).

## Safety + validation (every write)

- **In-repo path guard:** every read/write path resolves inside the repo/report dir.
- **No silent overwrite:** refuse to overwrite existing different content without an
  explicit force flag.
- **All-or-nothing:** stage in memory -> validate -> commit or roll back; never leave
  a partial/corrupt file.
- **Determinism:** byte-identical output on re-run (stable key order, no timestamps).
- **Validation:** written JSON is valid + keeps its `$schema`; round-trip stable;
  `retail check` R1 (model-ref) and R2 (report authoring-lint) stay green.

## The authorization gate

This adapter writes PBIR ONLY under the ratified ADR that lifts spec-001
FR-008/FR-009 for it: `docs/decisions/0015-pbir-authoring-adapter-lifts-fr008-fr009.md`
(owner-ratified 2026-07-05). Absent that record, the adapter refuses to write. The
agent never self-grants the lift (Principle V).

## Instance fields (fill per adapter instance)

- **Adapter instance:** `<name>`
- **Theme source consumed:** `<themes/<name>.theme.json>`
- **Target report:** `<...*.Report/>` (a CITED example; never inline a tenant here)
- **Increments enabled:** `<A | A,B | A,B,C>`
- **Authorization ADR:** `docs/decisions/0015-...md` (ratified by `<owner>` on `<date>`)
