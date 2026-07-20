# PBIR-authoring adapter -- integration + enumerated shape

The Power BI report-authoring adapter completes **F034** (Visual Implementation MVP):
it writes the committed PBIR report the kit previously left for a human to build in
Power BI Desktop. Authorized by **ADR 0015** (owner-ratified 2026-07-05), which lifts
spec-001 FR-008/FR-009 *for this bounded adapter only*.

## Why it exists

The owner's goal is a tool that authors report formatting -- the card/chart settings
a human sets by hand in the Power BI UI -- so the finished dashboard looks
professional, without depending on any external tool. Because a Power BI report in
PBIP format is plain-text JSON on disk, "change a setting in the UI" == "edit the
PBIR JSON." The adapter does that edit directly, in Python, with no pbi-cli and no
live Power BI.

## Architecture (the two homes)

ADR 0015 forbids the static DEFINE/CHECK core from writing PBIR, so the capability is
split:

- **The writer (companion adapter, MAY write PBIR):** `src/seshat/pbir_theme_apply.py`
  + the `retail pbir-apply-theme` verb + this skill/contract.
- **The lint (core, READ-ONLY, polices the write):** `src/seshat/rules/pbir.py` R2.

## Enumerated increments

| Increment | Status | What it writes |
|-----------|--------|----------------|
| **A -- apply a generated theme** | **SHIPPED** | a BaseTheme resource + `report.json` `themeCollection`/`resourcePackages` |
| **B -- per-visual formatting** | **SHIPPED** | allow-listed formatting under an existing `visual.json` `objects` / `visualContainerObjects` (data binding preserved byte-for-byte, FR-003) |
| **C -- page background** | **SHIPPED** | copies a surface-2 image asset into `RegisteredResources`, registers it in `report.json`, references it from `page.json` `objects.background` via a `ResourcePackageItem` (wire format taken verbatim from a real Desktop-authored sample -- the hold was correct) |
| **D -- visual geometry** | **SHIPPED (latent)** | an existing `visual.json`'s `position` rectangle (`x`/`y`/`width`/`height`/`z`/`tabOrder`), preserving the data binding (FR-003) and refusing off-canvas rectangles read from the real `page.json` canvas. Never `visualType`, never creates/deletes, never moves an unbound visual (ADR 0016). Authorized by ADR 0016 (ratified 2026-07-06) |

## Increment A -- how it works

`retail pbir-apply-theme --theme <theme.json> --report <*.Report/>`:

1. Validate both paths stay in-repo; the theme is a `theme-gen` theme (object with a
   safe-slug `name`).
2. Write the theme JSON to
   `<Report>/StaticResources/SharedResources/BaseThemes/<name>.json` (refuse to
   overwrite different existing content without `--force`).
3. Set `report.json` `themeCollection.baseTheme.name = <name>` and ensure the
   matching `resourcePackages` item (allow-list-only edit).
4. Validate the staged report (valid JSON + `$schema` preserved + round-trip stable),
   then write both files (all-or-nothing).

Deterministic: re-running produces a byte-identical result. Works on an empty report
page (no visuals required).

## The allow-list (increment A)

Exactly: `themeCollection.baseTheme`, its `resourcePackages` `SharedResources` item,
and the BaseTheme resource file. NOTHING else -- no `visual.json`, no `page.json`
geometry, no semantic-model file. The allow-list is enforced by the writer's
construction and policed by R2.

## Increment B -- per-visual formatting (how it works)

`retail pbir-format-visual --visual <visual.json> --formatting <json-or-path>` sets
allow-listed formatting on an EXISTING, already-data-bound visual:

- **Allow-list (increment B):** `objects` groups `{legend, labels, dataPoint,
  categoryAxis, valueAxis, title}` (chart-content) and `visualContainerObjects`
  groups `{border, title, subTitle, background, dropShadow}` (chrome). A container
  or group outside this map is refused.
- **The FR-003 guarantee:** the writer snapshots `visual.query` + `visual.visualType`
  before the edit and asserts they are byte-identical after -- refusing to write if
  the edit would touch the data binding. Formatting only, never binding.
- Property values are written in the PBIR `{"expr": {"Literal": {"Value": ...}}}`
  wrapper. Deterministic (`sort_keys`), all-or-nothing, `--force` gates overwriting a
  property already set to a different value.
- **Proven against a real fixture:** a Microsoft PBIP-sample data-bound `lineChart`
  (from `data-goblin/power-bi-visual-templates`), not a self-invented shape.
- **Latency (honest):** increment B has no live target yet -- the committed report
  page is empty, so it formats visuals a human authors later in Desktop. It is a
  capability, not a restyling of an existing live report.

## Increment D -- visual geometry (how it works)

`retail pbir-set-geometry --visual <visual.json> --position <json-or-path>` sets the
layout rectangle of an EXISTING, already-bound visual (authorized by ADR 0016):

- **Allow-list (increment D):** the `position` keys `{x, y, width, height, z,
  tabOrder}` only. Any other key is refused. Every value must be a number.
- **The FR-003 guarantee (unchanged):** the writer snapshots `visual.query` +
  `visual.visualType` before the edit and asserts they are byte-identical after --
  geometry is written BESIDE the binding, never through it. It never changes
  `visualType`, never creates/deletes a visual or page, never moves an unbound visual.
- **On-canvas guard:** the result rectangle (existing merged with requested keys) must
  fit the page's REAL canvas, read from the sibling `page.json` top-level
  `width`/`height` -- never a hardcoded size. Off-canvas / negative / non-numeric
  rectangles are refused; a missing/non-numeric `page.json` is a clean error, never a
  hardcode fallback. Overlap between visuals is ALLOWED (a design judgment, not a
  mechanical-validity one -- ADR 0016 Q3).
- **No `--force`:** position keys always pre-exist, so moving a visual is the operation;
  there is no differs-then-refuse gate (it would block every move). Overwrite safety is
  the reviewable git diff + human ratification.
- **Latency (honest):** the committed report page has zero visuals, so increment D is
  proven on a dedicated fixture and is LATENT until a real multi-visual report lands --
  a capability, not a re-layout of an existing live report.

## Validation (what keeps a write safe)

- Written JSON valid + keeps its `$schema` (PBIR is schema-versioned).
- Round-trip stable (read -> write -> read is identical).
- `seshat check` R1 (model reference relative) + R2 (report authoring-lint: valid /
  schema / referenced BaseTheme exists / no forbidden business-logic key) stay green.

## Boundaries (what it never does)

- No pbi-cli, no Power BI MCP, no live connection, no network -- stdlib only.
- No data bindings / measures / DAX / relationships / semantic-model edits.
- No readiness `pass` self-grant, no numeric score (hard rule #9).
- No live publish (that is the parked F016 adapter).

## Honesty note

The adapter is the *mechanism* -- it writes formatting deterministically. Producing
"great creative professional dashboards" is a separate design-intelligence layer that
would use this mechanism; the adapter does not claim it. Increment A restyles the
report theme; it does not populate an empty page or author visuals.

## See also

- ADR: `docs/decisions/0015-pbir-authoring-adapter-lifts-fr008-fr009.md`.
- Spec / plan / tasks: `specs/106-pbir-authoring-adapter/{spec,plan,tasks}.md`.
- Skill: `.claude/skills/pbir-authoring-adapter/SKILL.md`.
- Contract: `templates/pbir-adapter-contract.md`.
- Writer + verb: `src/seshat/pbir_theme_apply.py` (`retail pbir-apply-theme`).
- Core lint: `src/seshat/rules/pbir.py` (R2).
- Theme source: `src/seshat/theme_gen.py` (`retail theme-gen`, Slice 1, PR #204).
- Companion-adapter precedents: `docs/integrations/dbt-adapter.md` (F029), ADR 0009/0010.
