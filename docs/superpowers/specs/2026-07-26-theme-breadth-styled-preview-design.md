# Theme breadth + headless styled preview — design

**Date**: 2026-07-26
**Status**: Draft (awaiting owner review)
**Scope**: `theme_gen`, `theme_compile`, `blueprint_preview`, one new read-only verb
**Ordering**: Inside the ratified SLICE 1 (theme generator). Requires no reorder ruling.

## Problem

Seshat can govern a Power BI report but cannot make one look designed, and it
cannot show anyone what a theme will look like without opening Power BI Desktop.

Two verified gaps drive this:

1. **The shipped guidance already promises capability the code lacks.** The
   `powerbi-workflows` skill states themes cover "palette, fonts, visual defaults,
   page/wallpaper defaults, sentiment colors, and filter-pane/filter-card defaults"
   — present tense. `theme_gen.render_theme_json` emits 8 top-level keys plus a
   `visualStyles["*"]["*"]` wildcard carrying only `title`/`labels`/(optional)
   `background`. No filter-pane keys. No page/wallpaper keys. No per-visual-type
   defaults. `templates/theme-json-spec.md` §5 (visual defaults), §6 (filter-pane
   defaults), and §7 (page background) are specified tables with no emitter.
2. **Nothing renders a theme.** `blueprint_preview.render_blueprint_preview` takes
   four YAML paths and no theme input; it prints the theme *name* as a text label
   (`blueprint_preview.py:234`) and draws monochrome. `theme_gen` emits a
   `theme-spec.md` that no renderer consumes. The two subsystems never touch.

So a theme change today is unreviewable until a human opens Desktop, and the
theme itself cannot express most of what makes a report look considered —
gridlines, borders, number formats, page fill.

## Goals

- Emit spec §5/§6/§7 from the existing token pipeline.
- Render a styled, deterministic SVG preview from the same tokens.
- Keep every current guarantee: fail-before-write gates, determinism, no
  fabricated data, no self-granted approval.

## Non-goals (explicit)

- **No PBIR authoring.** `_VERIFIED_SAMPLES` stays `{page_shell, lineChart}`.
  Visual-type coverage is the later spec and needs its own owner ruling.
- **No filter behavior.** §6 styles the filter pane's LOOK only. Per the
  `powerbi-workflows` router: "the filter pane's LOOK, never what it filters."
  Nothing in this work reads or writes filter state, selections, or bound fields.
- **No background IMAGE generation.** §7 is the theme's default page/wallpaper
  FILL. An exported PNG/SVG background asset is surface 2 and stays out.
- **No live surface.** No pbi-cli, no MCP, no Power BI Service, no network, no DB.
  B1/B3 (AST guards forbidding module-scope network/DB imports in the static core)
  must keep passing unchanged.
- **No approval.** No verb here moves a readiness stage or grants anything.

## Architecture

One source of truth already exists — the committed design-tokens YAML. This work
gives it a second consumer.

```
design/tokens/<name>-design-tokens.yaml
    │
    ├──> theme_compile ──> themes/<name>.theme.json ──> pbir-apply-theme ──> PBIR
    │      (reuses theme_gen.render_theme_json as the single JSON-shape source)
    │
    └──> blueprint_preview ──> styled SVG          ← THE NEW SEAM
           (+ blueprint / visual-spec / composition / grid YAML for geometry)
```

Because both consumers read the same tokens, the preview cannot drift from the
artifact Power BI actually receives. That property is the point of the seam.

### Component 1 — theme breadth (`theme_gen`, inherited by `theme_compile`)

Extend `ThemeSeed` with optional token groups for the three spec sections, and
extend `render_theme_json` to emit them. `theme_compile` needs no new rendering
logic — it already delegates to `theme_gen.render_theme_json` as "the single
source of the theme's JSON shape" — but its `palette_from_tokens` reader must
learn the new token groups, and its DL3-deferred conflict list must be reviewed
so newly-generated keys are not treated as human-owned hand-tuning.

| Spec section | Emitted into | Fields |
|---|---|---|
| §5 visual defaults | `visualStyles["*"]["*"]` | background/fill, border (on/off + color), title (on/off + alignment), data labels (on/off), gridlines (on/off + color), default number format |
| §6 filter-pane defaults | `filterPane`, `filterCard` | pane background/border/text; card background/border/text (LOOK only) |
| §7 page background | page + wallpaper defaults | page color + transparency, wallpaper color + transparency |

Number format values are constrained to the spec's stated vocabulary
(`#,##0`, `#,##0.00`, `0.0%`) — refuse anything else, consistent with how
`_VALID_SCALING` constrains page-background scaling today.

### Component 2 — styled preview (`blueprint_preview`)

Add one optional keyword parameter, `tokens_path`. When absent, behavior is
byte-identical to today (monochrome) — existing golden files must not change.
When present, the renderer derives fills, borders, gridlines, and text colors
from those tokens.

Deliberately unchanged: the geometry/sort/ordering logic, the absence of any
data-source parameter, and the `PLACEHOLDER` literal for every value.

### Not included: `theme-diff`

A `theme-diff` verb (report added/removed/changed keys between two theme JSONs
before `pbir-apply-theme` overwrites one, borrowed in concept from pbi-cli's
`diff-theme`) was considered and **cut**. It is a third CLI verb with its own
parser wiring, tests, and docs that the approved design did not ask for. YAGNI.
Recorded here so the idea is not lost; it belongs in a later spec if wanted.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Contrast gates | Extend to non-text 3:1 | §5 introduces gridlines/borders/fills — non-text elements under WCAG. The five existing gates only cover text-on-background (4.5:1), so without this §5 could emit an invisible gridline that passes everything. Same fail-before-write posture as the current gates. |
| Preview honesty | Stamp the limit on every render | Mirrors `tmdl-doc-comment-lint`, whose disclaimer fires on a PASS. Per the owner's #494 ruling, a partial checker "risks implying coverage it lacks" — so the SVG carries a visible caption and the CLI states on every run, including success, that this is an approximation that does not prove Desktop will render this way. |
| Preview data | `PLACEHOLDER` only | `render_blueprint_preview` has no data-source parameter *by design* — a structural guarantee that it cannot fabricate a number. Sample values would break it. |
| Playwright | Local rasterization only | Rasterizes our own SVG/HTML for side-by-side diffs. No auth, no tenant, no live surface. Power BI Service capture would be a new authenticated surface needing redaction parity and an ADR — explicitly out of scope. |

## Error handling — an in-scope fail-open repair

`blueprint_preview._load_yaml_mapping` (`:57-67`) currently returns `{}` on any
`OSError` / `UnicodeDecodeError` / `yaml.YAMLError`, and
`render_blueprint_preview` has no problems channel at all. A corrupt blueprint
therefore yields a near-empty SVG that is indistinguishable from a legitimately
sparse one — a silent degrade.

Since this work modifies the module, it gets a third state: **parsed / absent /
unparseable**, where unparseable is *reported*, not swallowed. Absent stays
non-fatal (a preview of a not-yet-authored page is a real use case); unparseable
is named. This follows the repo's own `degrade-without-reporting-is-fail-open`
rule and the fail-closed reference implementations in `never_execute.py:168-180`
and `rls_access.py:401-411`.

This is repair of code being modified, not unrelated refactoring. The four other
fail-open findings from the 2026-07-26 inventory stay out of scope and unfixed.

## Testing

- **Golden-file SVG** for the styled render. Determinism is already structurally
  guaranteed (no `hash`/`random`/`time`/`uuid` in the module; every iterable
  explicitly sorted), so goldens are stable.
- **No-tokens regression**: omitting `tokens_path` produces output byte-identical
  to the current goldens.
- **Contrast gate**: a low-contrast gridline color is REFUSED, not warned. The
  oracle computes the WCAG ratio independently rather than importing the
  threshold from the code under test — per the repo's
  `verifier-must-sit-on-the-risk` rule.
- **Number-format vocabulary**: an out-of-vocabulary format string is refused.
- **Filter-pane boundary**: a test asserts no emitted key touches filter state,
  selections, or bound fields — only appearance.
- **Third state**: an unparseable blueprint is REPORTED; an absent one is not.
- **B1/B3 still pass**: no module-scope network/DB import introduced.
- **Round-trip**: `theme-gen` → `theme-compile` on the new token groups is
  idempotent (compile re-renders byte-identically from committed tokens).

## Risks

- **Power BI theme schema uncertainty.** `templates/theme-json-spec.md` §9 already
  treats the schema as UNCERTAIN. Filter-pane and wallpaper key names must be
  verified against Microsoft's published schema before implementation; a wrong
  key name is silently ignored by Desktop, which is a fail-open of its own.
  Mitigation: verify key names during implementation, and have the preview render
  from tokens rather than from the emitted JSON so a bad key name cannot make the
  preview lie.
- **DL3 fidelity rule interaction.** DL3 reconciles declared token↔theme
  correspondences and blocks on drift. New token groups must either be covered by
  DL3 or explicitly deferred like the existing DL3-deferred set — not left
  ambiguous.

### Two hard constraints found in the shipped rules (verified, not speculative)

These are blockers, not caveats. Both were confirmed by reading the code.

**C-1. `theme_compile` will refuse to overwrite its own §5 output unless the
generator-owned carve-out is extended.** `_DL3_DEFERRED_FIELDS`
(`theme_compile.py:56-73`) marks `visualStyles` as human-owned, with an explicit
exemption list `_GENERATOR_OWNED_VISUAL_STYLE_KEYS = ("title", "labels",
"background")`. Every §5 addition (border, gridlines, dataLabels, number format)
would land in the human-owned *remainder*, so `theme-compile` would treat the
generator's own output as hand-tuning and refuse to recompile it — even with
`--force`, since the conflict check runs regardless of force. The in-code comment
states the reason this list exists: otherwise "a legitimate token-declared
font/overlay change could never be recompiled over an existing theme."
**Required**: extend `_GENERATOR_OWNED_VISUAL_STYLE_KEYS` with every §5 sub-key,
and add a round-trip test that fails if a new generator-owned key is omitted.

**C-2. DL1 substring collision — CHECKED AND CLEAR (no owner ruling needed).**
DL1 (`rules/design_theme.py:100-109`) is confirmed a SUBSTRING match
(`if token in normalized`) on normalized theme-JSON key names, with an
`_ALLOWED_KEYS` carve-out, at `Severity.ERROR`. A collision would therefore be a
blocking `retail check` failure on a theme the generator itself produced. All 21
realistic §5/§6/§7 key names were tested empirically against `_is_forbidden`:
`gridline(s)`, `filterPane`, `filterCard`, `border`, `dataLabels`,
`labelDisplayUnits`, `valueAxis`, `categoryAxis`, `wallpaper`, `page`,
`outspace(Pane)`, `transparency`, `titleText`, `alignment`, `fontSize`,
`background`, `foreground`, `visualStyles`, `labels` — **all clear**.
**Required**: keep a test asserting every emitted key name passes
`_is_forbidden`, so a future key addition cannot silently reintroduce this.

**C-3. §7 page background lands INSIDE `visualStyles`, which widens C-1's fix.**
`templates/theme-json-spec.md` §7 names the fields (page color/transparency,
wallpaper color/transparency) but not a theme key. The shipped page-background
adapter writes to `page.json` → `objects.background` (`pbir_page_background.py:9,18`)
— a PAGE-LEVEL object, not a top-level report key. In a theme, the equivalent is
therefore `visualStyles["page"]["*"]` with `background` / `wallpaper` objects, not
a top-level `background`/`wallpaper` pair.
Consequence: C-1's fix is **not** a flat addition of sub-keys to
`visualStyles["*"]["*"]` — it must also treat a nested `page` visual-type entry as
generator-owned. That is a nested-key traversal in the DL3-deferred conflict
check, materially more than a one-line list extension.
**Required**: confirm the exact key path against Microsoft's published theme
schema during implementation (spec §9 already treats the schema as UNCERTAIN),
and make the preview render from TOKENS rather than from the emitted JSON so a
wrong key name cannot make the preview lie about what Desktop will show.
- **Preview fidelity is approximate, permanently.** SVG is not Power BI's
  renderer. The stamped disclaimer is the mitigation; it is not a fix, and the
  spec does not claim otherwise.

## Out of scope, tracked elsewhere

- Finding #0 from the 2026-07-26 inventory: a one-character TMDL header typo
  silences nine blocking D-rules in CI (`parse_tmdl` returns `None` for both
  "not a table file" and "corrupted"). Not a duplicate of issue #494 and not
  blocked by its ruling. Deserves its own issue.
- Visual-type coverage beyond `page_shell`/`lineChart` — later spec, needs a
  reorder ruling.
- Power BI Service screenshot automation — separate ADR-scale decision.
