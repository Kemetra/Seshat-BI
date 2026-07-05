# themes/ -- the starter Power BI theme (surface 3)

Status note: Planning (docs/templates/skill only; no runtime code, no PBIP/PBIR
edit). Part of the Power BI Visual Foundation (F011A).

## What this folder is

The starter Power BI theme JSONs -- plus this README.
A theme is **surface 3** of the four Power BI design surfaces (see
`../docs/powerbi/visual-design-system.md`): the one JSON file imported into Power
BI that sets the report's styling DEFAULTS -- the color palette, fonts, and the
default formatting visuals inherit unless a visual overrides them.

### Inventory

- `tower-retail.theme.json` -- the hand-authored conservative default (see below).
- `executive-dark.theme.json` -- a generated dark starter (monochromatic teal
  ramp) produced by `retail theme-gen` (Slice 1). Its `theme-spec.md` sibling
  records CT1 contrast (computed, clean) and holds the CVD/render/saturation
  checks OPEN for a named reviewer; readiness = `warning`, never self-`pass`.
  Like every theme here it is a STARTER -- validate in Power BI Desktop first.

> `retail theme-gen` (a DEFINE-only kit verb) emits a token+theme+spec triplet
> from a caller-supplied palette, gated by DL1/DL3/CT1. It writes NO PBIR /
> report file and depends on no external tool -- surface-3 styling only.

`tower-retail.theme.json` is a conservative, generic, retail-executive STARTER.
It draws its palette, typography, and sentiment colors from the design tokens in
`../design/tokens/tower-retail-design-tokens.yaml`, and it carries only safe
defaults: `name`, `dataColors`, `background`, `foreground`, `tableAccent`, and a
minimal set of `visualStyles` defaults. It invents no business meaning, names no
subject area, and bakes in no connection host or secret.

## It is a STARTER -- validate in Power BI Desktop before use

This theme is a seed, not a finished, certified theme. **Validate it in Power BI
Desktop before relying on it:** import it (below), confirm Power BI accepts the
file without error, and check that the palette, fonts, and defaults render as
intended on a real page. Treat the committed file as a starting point to adjust
against your own pages, not as a guaranteed-correct drop-in.

## The exact theme schema is treated as UNCERTAIN

The precise Power BI report-theme JSON schema -- the full set of valid keys, their
nesting, and the per-visual style names -- changes across Power BI Desktop
versions and is not pinned here. This foundation deliberately does NOT claim
schema completeness. `tower-retail.theme.json` keeps to a small, widely supported
set of keys for that reason; anything beyond that minimal set should be added
only after Power BI Desktop accepts it in your version. If Desktop rejects a key,
remove or correct it -- the importing tool, not this README, is the authority on
what the schema currently allows.

## How to import it

1. Open your report in Power BI Desktop.
2. Go to the **View** ribbon -> **Themes** -> **Browse for themes**.
3. Select `themes/tower-retail.theme.json` from this repo.
4. Confirm the import succeeds with no error, then check a page: data colors,
   fonts, page/wallpaper default, and filter-pane styling should reflect the
   theme.
5. If Desktop reports an invalid theme, the schema is the authority -- fix or
   drop the offending key (see the schema-uncertainty note above) and re-import.

Editing the file outside Power BI: keep it ASCII, UTF-8 without BOM, and valid
JSON. Do not add a connection host, a secret, or any business logic (see below).

## It controls DEFAULTS, never business meaning

The governing rule for this surface (the full do/don't list is in
`../docs/powerbi/theme-json.md` and `../templates/theme-json-spec.md`):

Theme JSON controls DEFAULTS, never business meaning. It MAY set: color palette, fonts, visual
defaults, page/wallpaper defaults, filter-pane defaults, sentiment COLORS. It MUST NOT control:
DAX, metric definitions, semantic-model relationships, source mapping, visual storytelling, or
data validation. (A sentiment COLOR belongs in the theme; the sentiment THRESHOLD/RULE is a
metric contract, F009.)

In short: a sentiment COLOR belongs here; the sentiment THRESHOLD/RULE that
decides when a value is good, caution, or bad is business logic and belongs in a
metric contract (F009), never in this file.

## See also

- `../docs/powerbi/theme-json.md` -- what theme JSON controls and what it must
  NOT control (the prose reference for surface 3).
- `../templates/theme-json-spec.md` -- the copy-me theme spec (palette /
  typography / sentiment / defaults + the explicit must-NOT-control list).
- `../design/tokens/tower-retail-design-tokens.yaml` -- the design tokens the
  starter theme draws its palette, typography, and sentiment colors from.
- `../.claude/skills/powerbi-dashboard-design/workflows/theme-json-design.md` --
  the surface-3 authoring procedure (the agent workflow that produces a theme).
- `../docs/powerbi/visual-design-system.md` -- the four design surfaces and where
  theme JSON sits among them.
