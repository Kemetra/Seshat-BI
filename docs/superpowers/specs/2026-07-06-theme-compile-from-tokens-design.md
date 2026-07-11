# Theme-compile-from-tokens -- design

- **Date:** 2026-07-06
- **Author:** agent (brainstorming + advisor review) + Ahmed Shaaban (delegated "go as you recommend")
- **Surface:** the DEFINE side of surface-3 theming -- a deterministic verb that
  compiles a *committed* design-tokens YAML into its matching Power BI `theme.json`.
- **Status:** design, pending owner review before writing-plans.
- **Working title correction:** this slice was requested as "theme-generation-from-plan."
  Brainstorming found that framing is **circular** (see below); the honest slice is a
  tokens -> theme *compile*, upstream of any formatting plan. The name is fixed here.

## Why the requested framing ("generate a theme *from* a plan") does not exist

A `formatting-plan.md` row references the theme by citing a token path, e.g.
`design/tokens/<subject>-design-tokens.yaml#palette` (see `templates/formatting-plan.md`
row 96). That tokens file is **`theme-gen`'s own output.** So by the time a plan
exists that cites a theme, the theme has already been generated -- there is nothing left
to "generate from" the plan. Any seed/theme proposal must live **upstream** of the
formatting plan, not "from" it. The correct ordering is:

```
(seed) -> theme-gen -> tokens.yaml + theme.json  ->  formatting-plan cites them
```

This design takes the smallest, most constitutionally-clean step in that chain: the
`tokens.yaml -> theme.json` compile. (Proposing the *seed* -- picking a generic accent
+ mode -- is a separate, later, thinner slice; it proposes color and so carries a
Principle-V surface this slice deliberately avoids. It stays deferred.)

## What already exists (do not rebuild it)

Two facts, verified against the live tree, bound this slice tightly:

1. **`theme_gen.render_theme_json(palette, seed)`** already turns a resolved palette
   into the exact theme JSON we want. The compile verb REUSES it verbatim -- it invents
   no new rendering, no new color, no new key.
2. **DL3 (`src/seshat/rules/design_theme_fidelity.py`) already CHECKS this loop.** It
   reconciles `colors.background` and positional `colors.data_colors[i]` between a
   committed tokens YAML and its `meta.compiles_to` theme. So drift is *already caught*:
   a hand-edited `theme.json` out of sync with its tokens is a DL3 error today.

The value of this slice is therefore **not** "catch drift" (DL3 owns that). It is
**"remove the manual step that causes drift."** Today the only path to a `theme.json` is
`theme-gen` from a hand-typed 8-field seed; if tokens already exist and you want to
(re)produce or repair the matching theme deterministically, you must hand-edit -- exactly
the action that risks tripping DL3. `theme-compile` is the **generator whose output DL3
was written to verify.** Clean pairing: compile produces, DL3 checks.

### Narrowed thesis (verified against the live themes) -- write scope != check scope

The original framing above assumed compile's *write scope* equals DL3's *check scope*. It
does not, and the live tree proves it: `tower-retail.theme.json` is DL3-clean (its
`dataColors` + `background` match its tokens) yet was **hand-tuned by an owner ruling**
(commit `947e4fa`, 2026-07-03) in fields DL3 *deliberately defers* -- `name`,
`foreground`, `good`/`neutral`/`bad` (the 4->3 sentiment ambiguity DL3 was scoped to leave
to a human). A naive full-document compile would silently overwrite that ruling with
generic token defaults -- a Principle-V violation (overriding a human decision) and real
data loss.

So the honest thesis is narrower: `theme-compile` **repairs DL3-governed drift**
(`dataColors`, `background`) on a theme, and **refuses -- even with `--force` -- when any
DL3-deferred, human-owned field differs**, reporting those fields for manual
reconciliation. Refusing *surfaces* the discrepancy (the DEFINE/CHECK identity); merging
would *hide* it. Consequence: "byte-identical to what `theme-gen` wrote" holds only for a
theme that was generated and never hand-tuned (e.g. `executive-dark`); a hand-tuned theme
is protected, not reproduced.

## Architecture -- one deterministic verb, reusing the generator's renderer

| Role | Where | What | New? |
|------|-------|------|------|
| COMPILE | `retail theme-compile` -> `theme_compile.py` (thin) | read committed tokens YAML -> reconstruct the palette -> call `render_theme_json` -> write `theme.json` | new verb |
| RENDER | `theme_gen.render_theme_json` | unchanged; single source of the theme's JSON shape | reused unchanged |
| CHECK | DL3 (fidelity) + DL1 (purity) | verify the written theme matches its tokens + carries no business keys | reused unchanged |

No new rule. No new template. No new reasoning skill (this is deterministic, so it lives
in the core, not a skill). No ADR (writes a `themes/*.theme.json`, which `theme-gen`
already does -- this is the same DEFINE-side surface-3 artifact, not PBIR).

## Data flow

```
themes/<name>.theme.json  <--- render_theme_json(palette, seed)
        ^                              ^
        |                     palette rebuilt from the tokens' own committed values
        |                              |
  write (refuse overwrite w/o --force) |
        |                    read design/tokens/<name>-design-tokens.yaml
        +------------------------------+
                (meta.compiles_to names the target path)
```

The tokens file already declares its own target via `meta.compiles_to`
(`themes/<name>.theme.json`) -- the compile verb writes exactly there, so DL3's existing
pairing resolves the same pair with zero new wiring.

### Rebuilding the palette from tokens (no re-derivation, no new color)

`render_theme_json` needs a `palette` dict and a `seed` (it reads `seed.name` only). The
compile verb reconstructs both **purely from values already committed in the tokens YAML**
-- it derives nothing and chooses nothing:

- `palette["colors"]` <- the tokens' `colors` block, field for field
  (`primary`, `secondary`, `background`, `text.*`, `sentiment.*`, `data_colors`).
- `seed.name` <- the tokens' `meta.name` with the `-design-tokens` suffix stripped
  (or `--name` override), validated by the SAME `_validate_name` slug guard.

Because every value is copied from committed tokens, the compiled `theme.json` is
byte-identical to what `theme-gen` wrote (or what it *would* write for those tokens) --
which is precisely the invariant DL3 asserts. That equivalence is the core test.

## Error handling (all clean `ThemeCompileError`, never a traceback)

- tokens file missing / unreadable / not valid YAML -> clean error, exit 2.
- tokens missing a required `colors.*` field -> clean error naming the field.
- any color value not `#RRGGBB` -> reuse `is_valid_hex`; clean error (same guard as gen).
- `meta.compiles_to` absent AND no `--out` given -> clean error (we do not guess a path).
- target exists and `--force` not given -> refuse to overwrite (matches `theme-gen`).
- contrast below AA -> reuse `check_contrast_or_raise`: refuse to compile a theme the CT1
  gate would reject (do not emit a knowingly-failing theme just because tokens hold it).

## Scope discipline

- **DEFINE-only.** Writes one `themes/*.theme.json`. No PBIR, no visual.json, no model,
  no live Power BI, no network, no pbi-cli. Stdlib + existing `retail.color` only.
- **No color decision.** Every value is copied from committed tokens; the verb chooses
  nothing. Zero Principle-V color surface (unlike the deferred seed-proposal slice).
- **No self-granted pass.** The verb prints where it wrote and reminds that DL3/DL1 and
  Desktop validation still gate the theme; it never claims the theme is "good."
- **Latent-until-real-report? No -- this one is live now.** Unlike the smart-formatting
  workflow (which needs a filled report page), `theme-compile` operates on committed
  tokens that already exist (`executive-dark`, `tower-retail`). It is exercisable on day
  one against the two committed token files. State that honestly -- it is the first piece
  of this stack that is NOT latent.

## Testing

- **Round-trip invariant (the core test):** `theme-gen` a seed -> tokens+theme; delete
  the theme; `theme-compile` the tokens -> a theme byte-identical to the deleted one.
- DL3 passes on the compiled pair (the generator-checker pairing holds end to end).
- Overwrite refused without `--force`; allowed with it.
- Each error path (missing field, bad hex, no target, sub-AA contrast) yields a clean
  `ThemeCompileError` and exit 2, never a traceback.
- CLI wiring test: `theme-compile` subcommand parses and dispatches.

## The single sharpest risk that remains

Value overlap perception: a reviewer may ask "if DL3 already catches drift, why a compile
verb?" The answer, stated in the plan and the module docstring, is that DL3 is the
*check* and this is the *generator DL3 checks* -- removing the hand-edit that is the only
current way to desync them. If that framing does not convince on review, the slice is
cheap to drop (one thin module + wiring); it changes no existing behavior. The design
carries no irreversible surface.

## See also

- The renderer it reuses: `src/seshat/theme_gen.py` (`render_theme_json`, `build_palette`).
- The checker it feeds: `src/seshat/rules/design_theme_fidelity.py` (DL3) + `design_theme.py` (DL1).
- The circular framing it replaces: `docs/superpowers/specs/2026-07-06-smart-formatting-layer-design.md`
  (deferred list: "theme *generation* from the plan").
- Tokens format: `design/tokens/executive-dark-design-tokens.yaml`.
