# Theme generator (Slice 1, DEFINE-only) -- design

- **Date:** 2026-07-05
- **Author:** agent (brainstorming) + Ahmed Shaaban (decisions + authorization)
- **Supersedes:** `2026-07-05-zoomcharts-theme-starters-design.md` (the 2-hand-authored-
  themes design; the review caught that the user wanted a *generator*, not artifacts).
- **Surface:** 3 (theme JSON) -- DEFINE layer. Routed by
  `.claude/skills/powerbi-dashboard-design/SKILL.md`, workflow `theme-json-design.md`.
- **Status:** design, owner pre-authorized ("Proceed now with Slice 1: theme generator only").

## The dream, and where this slice sits in it

The owner's goal is a tool that creates themes + backgrounds and edits Power BI
visuals to assemble professional dashboards. That decomposes by DEFINE vs EXECUTE:

1. **Theme generator (DEFINE) -- THIS SLICE.**
2. Backgrounds (surface-2 output) -- later, via the adapter.
3. Edit embedded Power BI visuals (EXECUTE = write PBIR JSON) -- the F034 completion.
4. Assemble professional dashboards (EXECUTE + design-intelligence) -- rides on 3.

Layers 3-4 are a SEPARATE authorized-but-not-yet-built companion **PBIR-authoring
adapter** (its own Spec Kit feature, own owner gate). **This slice builds ONLY layer 1**
and touches no PBIR/visual.json, lifts no FR-008/009, and claims no dashboard automation.

## Goal (Slice 1)

A self-contained kit verb that turns a **palette seed** into a complete, gated,
surface-3 theme artifact set: `retail theme-gen`. Deterministic, stdlib-only, no
external dependency (no pbi-cli, no color library -- Python `colorsys` + the WCAG
math already in `design_contrast.py`).

## Derivation model (owner-ruled: FULL MULTI-INPUT)

The generator ASSEMBLES + VALIDATES a palette the caller supplies, rather than
deriving everything from one accent. Inputs:

- `--name <slug>` (theme + token file basename; e.g. `executive-dark`)
- `--mode {light,dark}` (sets defaults + which contrast direction is expected)
- `--accent #RRGGBB` (primary brand / key series)
- `--background #RRGGBB` (page base fill)
- `--text-primary #RRGGBB` (+ optional `--text-secondary`, `--text-muted`)
- `--data-colors "#a,#b,#c,..."` (the ordered series ramp; if omitted, a
  monochromatic ramp is DERIVED from `--accent` via `colorsys` lightness steps)
- optional sentiment overrides `--good/--neutral/--bad` (else mode-sensible defaults)

The generator's job: assemble these into a valid token set + theme JSON + filled
spec, and **verify its own output against CT1 before writing** (see safety below).
Deriving the data-color ramp when omitted is the one computed convenience; everything
else is caller-supplied (full multi-input, per the ruling).

## Output artifacts (per run) -- mirrors the existing triplet exactly

1. `design/tokens/<name>-design-tokens.yaml` -- full token set, **with
   `meta.compiles_to: themes/<name>.theme.json`** (DL3 requires this once >1 theme
   exists), `accessibility.min_text_contrast_ratio: "4.5:1"`.
2. `themes/<name>.theme.json` -- faithful compile: `dataColors`/`background` **equal**
   the token values by construction (the generator writes both from one in-memory
   palette, so DL3 fidelity cannot drift). Styling-only keys (DL1-clean).
3. `themes/<name>.theme-spec.md` -- filled copy of `templates/theme-json-spec.md`;
   section-8 cites CT1's computed verdict (not a bare tick); CVD/small-size/saturation
   left as `warning` pending a named reviewer (Principle V). Co-located beside the
   theme (new convention, first filled instance -- called out for review).

The generator does NOT edit `themes/README.md` automatically (that is human inventory
prose); it prints a suggested README line for the human to add.

## Architecture

- New module `src/seshat/theme_gen.py` -- the palette assembly + derivation + the
  three artifact writers. Pure functions where possible; one `generate(args) ->
  written_paths` entry.
- New CLI verb in `src/seshat/cli.py`: `retail theme-gen ...` (an `add_parser`
  sibling of `gen`/`scaffold`), dispatching to `theme_gen.main`.
- **Reuse, don't duplicate, the WCAG math.** `design_contrast.py` already has
  `_channel_luminance`/`_relative_luminance`/`_contrast_ratio`. Extract these into a
  small shared helper (e.g. `src/seshat/color.py`) and have BOTH the CT1 rule and the
  generator import it -- so the generator's self-check uses the *exact* arithmetic the
  gate will later apply. This is a targeted, in-scope improvement (removes a
  copy-paste risk), not unrelated refactoring.
- `colorsys` (stdlib) for the optional monochromatic-ramp derivation only.

## Safety checks (the generator polices its own output)

- **Pre-write CT1 self-check:** compute contrast of each text role vs background with
  the shared helper; if any pair is below `4.5:1`, the generator **refuses to write**
  and prints which pair failed + the computed ratio. (It never silently ships a theme
  that CT1 would then fail -- fail fast, fail loud.)
- **DL1 key hygiene:** the generator only ever writes known styling keys (`name`,
  `dataColors`, `background`, `foreground`, `tableAccent`, `good`, `neutral`, `bad`,
  `visualStyles.title/labels`), so DL1 purity holds by construction.
- **Hex validation:** every input hex is validated (`#RRGGBB`) before use; a bad hex
  is a clean error, not a traceback.
- **No overwrite without `--force`:** if `themes/<name>.theme.json` exists, refuse
  unless `--force` (immutability-friendly; no silent clobber).
- **Readiness = `warning`, never `pass`:** the spec is written at `warning` with CT1
  cited as satisfied and the human-judgment checks open. The generator cannot
  self-grant `pass` (rule #9 / Principle V).

## What Slice 1 explicitly does NOT do (owner boundary, verbatim intent)

- Does NOT implement PBIR visual editing. Writes NO `visual.json` / report file.
- Does NOT lift FR-008/FR-009. Does NOT touch `powerbi/*.Report/`.
- Does NOT depend on pbi-cli or any external tool / live Power BI.
- Does NOT claim "professional dashboard automation" -- it emits a theme artifact set.
- Does NOT auto-edit `themes/README.md` or grant any readiness `pass`.

## Testing

- `tests/unit/test_theme_gen.py` (`@pytest.mark.unit`): generate into a tmp repo;
  assert (a) all three files written, (b) theme JSON is valid + DL1-clean, (c)
  `dataColors`/`background` match the tokens (DL3 by construction), (d) the CT1
  self-check rejects a below-floor text/bg pair, (e) bad hex -> clean error, (f)
  existing file -> refuse without `--force`, (g) the derived monochromatic ramp is
  monotonic in lightness when `--data-colors` omitted.
- The shared `color.py` gets its own tests; the existing `test_design_contrast.py`
  must still pass unchanged (proves the extraction preserved CT1 behavior).
- Gate before push: `retail check` (DL1+DL3+CT1 green on a generated example) +
  `ruff format --check src tests` + `ruff check src tests` + `pytest -m unit`.

## Delivery

One PR to `main`, branch `feat/theme-generator-slice1` (the current
`feat/zoomcharts-theme-starters` branch is renamed/repurposed; the superseded design
doc is retained in history). PR title `feat:`-prefixed. No worktree; no HERA/ZEUS
changes.

## After Slice 1 (not built here)

Prepare a separate Spec Kit feature: the self-contained **PBIR-authoring adapter**
(F034 completion) -- adapter boundary, allowed PBIR JSON edits, forbidden
live-PB/pbi-cli/external deps, safety checks, validation strategy, dependence on the
generated theme, backgrounds as surface-2 output, and an explicit owner approval gate
before implementation. See memory `pbir-authoring-adapter-authorized`.

## See also

- Router/workflow: `.claude/skills/powerbi-dashboard-design/SKILL.md` +
  `workflows/theme-json-design.md`
- Rules the generator satisfies: `design_theme.py` (DL1), `design_theme_fidelity.py`
  (DL3), `design_contrast.py` (CT1)
- Seed reference: `design/tokens/tower-retail-design-tokens.yaml`,
  `themes/tower-retail.theme.json`, `templates/theme-json-spec.md`
- CLI/verb precedent: `src/seshat/cli.py`, `src/seshat/dax_gen.py`,
  `src/seshat/scaffold.py`
