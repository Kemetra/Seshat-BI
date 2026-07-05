# ZoomCharts-inspired theme starters (surface 3) -- design

- **Date:** 2026-07-05
- **Author:** agent (brainstorming) + Ahmed Shaaban (decisions)
- **Surface:** 3 (theme JSON) -- routed by `.claude/skills/powerbi-dashboard-design/SKILL.md`
- **Workflow followed:** `workflows/theme-json-design.md`
- **Status:** design, pending user sign-off before writing-plans

## Goal

Add reusable Power BI **theme starters** to the kit whose palette and typography
evoke the ZoomCharts dashboard gallery, done **within the surface-3 boundary** the
kit already enforces. The user asked for "backgrounds and themes like ZoomCharts";
this design delivers the **theme** slice (the part theme JSON can actually express)
and states plainly what it cannot.

## The honest capability ceiling (why this is themes, not "the ZoomCharts look")

The ZoomCharts gallery was inspected first-hand (four real dashboards downloaded
and viewed: a dark-navy retail-Christmas report, a light HR report, a light
used-car report, a dark retail-supply-chain report). Their polish comes from:

| Ingredient | Surface | In scope here? |
|-----------|---------|----------------|
| Color palette + monochromatic data ramps | 3 (theme JSON) | **YES** -- this design |
| Typography (weights, sizes) | 3 (theme JSON) | **YES** -- this design |
| Page/canvas fill (navy vs white) | 3 (theme wallpaper default) | **YES** -- this design |
| Rounded white **card chrome**, pill nav buttons | 1/2 (custom visuals + background image) | NO -- not theme-expressible |
| Gradient bar fills, drill-down interactivity | 1 (ZoomCharts **paid** custom visuals) | NO -- not the kit's to render |
| Rendered/published report | 4 (F016 execution adapter) | NO -- deferred, hard rule #6 |

**Theme JSON cannot render gradients, glass, card frames, or custom visuals.**
So this design reproduces the ZoomCharts *palette and type layer* -- the biggest
single lever, and 100% theme-expressible -- and is explicit that the card chrome
and interactivity are out of reach without surface-1/2/4 work.

## What was observed in the gallery (the evidence the palettes are grounded in)

Two archetypes recur, both reproducible in theme JSON:

1. **Dark-navy executive** (retail-Christmas, supply-chain): deep navy canvas,
   white cards floating on it, a single saturated **teal-cyan** accent used as a
   light->dark ramp.
2. **Light executive** (HR, used-car): near-white canvas, white cards, a single
   bold accent color (HR = green, car = orange) used as a **monochromatic ramp**.

The signature is **monochromatic / single-hue data-color ramps**, not rainbow
categoricals. That is the decision below.

## Decisions (owner-ruled 2026-07-05)

- **D1 = build BOTH starters** (`executive-dark` + `vibrant-light`) -- the two
  archetypes observed.
- **D2 = monochromatic data-color ramps** -- single-hue light->dark, faithful to
  the gallery. Honest tradeoff recorded: a single-hue ramp is **less
  category-distinguishable** than multi-hue; this is flagged in each theme spec's
  section-8 as a CVD/legibility reviewer seam (Principle V), not silently shipped.
- **D3 = keep the existing default untouched** -- `tower-retail.theme.json` and its
  tokens are unchanged; the two new starters sit **alongside** it. Consistent with
  the seed's stated conservative-default intent and the immutability rule.

## Architecture -- three files per starter (mirrors the existing triplet exactly)

For each of `executive-dark` and `vibrant-light`:

1. `design/tokens/<name>-design-tokens.yaml` -- the full token set (colors,
   sentiment, neutrals, `data_colors`, typography, accessibility floor). **MUST
   carry `meta.compiles_to: themes/<name>.theme.json`** (see DL3 constraint below).
2. `themes/<name>.theme.json` -- the faithful compile: `dataColors` and
   `background` **exactly equal** the token values (DL3), styling-only keys (DL1).
3. A filled copy of `templates/theme-json-spec.md`, co-located next to its theme
   at `themes/<name>.theme-spec.md` -- the human-readable spec; section-8 cites
   CT1's computed verdict (not a bare tick) and leaves CVD/render checks as
   `warning` pending a named reviewer.
   **Convention note:** no filled theme-spec instance exists in the repo today
   (the template is the only one; `themes/README.md` points to it as the copy-me
   blank). These are the FIRST filled instances. Co-locating the filled spec beside
   its `.theme.json` mirrors how the kit co-locates mapping instances beside their
   tables (`mappings/<table>/`). This is a new, small convention introduced by this
   design, called out here so it is reviewed, not silently minted.

Plus one shared edit:

4. `themes/README.md` -- add the two new starters to the inventory with the
   STARTER / validate-in-Desktop / schema-uncertain caveat.

## The checks that gate this (verified against the rule source, not assumed)

All three surface-3 `retail check` rules **auto-discover** new files -- confirmed
by reading the rule source:

- **DL1 (purity, `design_theme.py`)** -- walks **all** `*.theme.json` in
  `tracked_files`. A new theme is covered automatically. Each new theme must use
  only styling keys (no key normalizing to a forbidden token: dax, measure,
  calculated*, expression, threshold, rule, relationship, sourcemapping,
  validation, metricdefinition).
- **DL3 (fidelity, `design_theme_fidelity.py`)** -- pairs each
  `*-design-tokens.yaml` to the theme named in its own `meta.compiles_to`, then
  asserts `background` identity and **positional `dataColors[i]` equality**.
  **Constraint:** DL3's no-`compiles_to` fallback only works when exactly ONE
  theme exists; with three themes, every tokens file **must** declare
  `meta.compiles_to` or it silently skips. Both new tokens files will declare it.
- **CT1 (contrast, `design_contrast.py`)** -- iterates **all**
  `*-design-tokens.yaml`; computes WCAG ratio of `text.{primary,secondary,muted}`
  vs `background` against the file's own `accessibility.min_text_contrast_ratio`.
  `_contrast_ratio` is symmetric, so **light-on-dark passes the same AA gate** as
  dark-on-light.

### Pre-verified palettes (CT1 math run ahead of build -- prove, don't assert)

Mirroring CT1's exact WCAG math, every proposed text/background pair clears the
4.5:1 AA floor:

- **executive-dark** (bg `#12263A`): primary `#F2F6FA` = 14.18:1, secondary
  `#C4D1DE` = 9.91:1, muted `#93A6B8` = 6.15:1. All pass.
- **vibrant-light** (bg `#FBFCFD`): primary `#14202B` = 16.08:1, secondary
  `#3A4855` = 9.13:1, muted `#63717E` = 4.87:1. All pass (muted is tight; final
  build will keep it at or above this).

Note (honest, recorded): the two darkest steps of the dark teal ramp
(`#0D7A8C` = 3.06:1, `#0A5E6B` = 2.07:1 vs the navy bg) are low-contrast. CT1 does
NOT check data-color-vs-bg (only text roles), so this is not a CT1 failure -- but
the dark ramp will be trimmed / its darkest steps reserved for large fills so the
sequence stays legible. This is a section-8 saturation/legibility note, not a
silent choice.

## Readiness (honest -- warning, not pass)

Each new theme lands at **`warning`**, never self-granted `pass`:

- CT1 contrast: clean and cited (computed above). Satisfied.
- CVD distinguishability / small-size legibility / no-pure-saturated-behind-dense:
  these need a **named human reviewer against a rendered page** (F016 surface,
  which does not exist yet). Left open at `warning` with a reason -- marking `pass`
  on author alone is exactly the self-asserted accessibility pass the kit forbids
  (theme-json-spec section 8, hard rule #9 spirit). The monochromatic-ramp CVD
  tradeoff (D2) is the specific thing that reviewer must judge.

## Scope discipline (what this design deliberately does NOT do)

- No PBIP/PBIR edit, no DAX, no SQL, no `pbi-cli` automation (surface 4 / F016).
- No background **image** assets (surface 2) -- that is a separate one-off design
  task if wanted later; this is themes only.
- No change to `tower-retail.theme.json` or its tokens (D3).
- No new `retail check` rule -- the existing three already cover the new files.
- No touching the HERA / ZEUS / other worktrees.

## Delivery

One PR to `main` on branch `feat/zoomcharts-theme-starters`. Gate before push:
`retail check` (DL1+DL3+CT1 green) + `ruff format --check src tests` +
`ruff check src tests` + `pytest -m unit`. PR title carries a `feat:` prefix
(squash-merge subject rule).

## See also

- Router: `.claude/skills/powerbi-dashboard-design/SKILL.md`
- Workflow: `.claude/skills/powerbi-dashboard-design/workflows/theme-json-design.md`
- Existing triplet: `themes/tower-retail.theme.json`,
  `design/tokens/tower-retail-design-tokens.yaml`, `templates/theme-json-spec.md`
- Rules: `src/retail/rules/design_theme.py` (DL1),
  `design_theme_fidelity.py` (DL3), `design_contrast.py` (CT1)
