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

- **The writer (companion adapter, MAY write PBIR):** `src/retail/pbir_theme_apply.py`
  + the `retail pbir-apply-theme` verb + this skill/contract.
- **The lint (core, READ-ONLY, polices the write):** `src/retail/rules/pbir.py` R2.

## Enumerated increments

| Increment | Status | What it writes |
|-----------|--------|----------------|
| **A -- apply a generated theme** | **SHIPPED** | a BaseTheme resource + `report.json` `themeCollection`/`resourcePackages` |
| B -- per-visual formatting | planned (separate plan) | allow-listed formatting keys in an existing `visual.json` |
| C -- backgrounds | planned (separate plan) | a page background reference to a committed surface-2 asset |

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

## Validation (what keeps a write safe)

- Written JSON valid + keeps its `$schema` (PBIR is schema-versioned).
- Round-trip stable (read -> write -> read is identical).
- `retail check` R1 (model reference relative) + R2 (report authoring-lint: valid /
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
- Writer + verb: `src/retail/pbir_theme_apply.py` (`retail pbir-apply-theme`).
- Core lint: `src/retail/rules/pbir.py` (R2).
- Theme source: `src/retail/theme_gen.py` (`retail theme-gen`, Slice 1, PR #204).
- Companion-adapter precedents: `docs/integrations/dbt-adapter.md` (F029), ADR 0009/0010.
