# Theme JSON Spec -- <theme_name> (surface 3, defaults only)

> GENERIC, copy-me template. Human-readable specification for ONE Power BI theme
> JSON. It is a SURFACE 3 artifact (theme JSON): the DEFAULTS layer -- palette,
> fonts, visual/page/filter-pane defaults, sentiment colors. Fill the placeholders;
> author the actual JSON separately (`themes/<name>.theme.json`) and validate it in
> Power BI Desktop before use. Status + evidence + blockers, never a fake number.
> See `docs/powerbi/theme-json.md` (the prose) and the
> `workflows/theme-json-design.md` workflow under the
> `.claude/skills/powerbi-dashboard-design/` router.

- **Theme name:** `<theme_name>`              (e.g. tower-retail; matches the JSON `name`)
- **Compiled JSON:** `<themes/<name>.theme.json>`   (the importable file this spec describes)
- **Authored by:** `<agent | person>`
- **Last reviewed:** `<YYYY-MM-DD>` by `<agent | person>`

## Which surface this belongs to (route to exactly one; never blend)

Surface 3 -- theme JSON. This spec carries DEFAULTS, not data and not structure.
It is NOT the same as:

- Surface 1 (report visuals) -- a visual's data binding lives in
  `templates/visual-spec.yaml`, never here.
- Surface 2 (external background/canvas) -- the static background IMAGE
  (the exported PNG/SVG, its safe zones and containers) is
  `templates/background-spec.yaml`. The `page_background` section below is the
  theme's wallpaper/page-fill DEFAULT only -- a flat default color, NOT the
  surface-2 image. Keep the two apart: a theme default fill is surface 3; an
  exported background asset is surface 2.
- Surface 4 (implementation handoff) -- importing/applying the theme to a report
  is routed by `powerbi-handoff` to Microsoft's official report-authoring skill
  when discoverable or to a human Desktop build. F016 owns only parked live
  semantic-model execution. This spec edits no PBIP/PBIR file.

## Surface-3 purity rule (the one boundary this spec enforces)

A theme is pure styling and is NOT gated on metric contracts: setting a palette,
fonts, or default formatting touches no metric, so a theme may be authored
before `semantic_model_ready` is `pass` (spec US2 scenario 4 -- surfaces 2 and 3
carry structure and defaults, not data). The theme's only business-logic boundary
is the MAY/MUST-NOT split stated VERBATIM below. (The data-bound gate -- no
visual before its contract exists -- lives one surface over, in
`templates/visual-spec.yaml`, and is owned by `docs/readiness/dashboard-ready.md`
+ the F011/012 dashboard-design verb. This spec does not restate that gate.)

The canonical rule, pasted unmodified -- it lists BOTH what the theme MAY set and
what it MUST NOT control:

Theme JSON controls DEFAULTS, never business meaning. It MAY set: color palette, fonts, visual
defaults, page/wallpaper defaults, filter-pane defaults, sentiment COLORS. It MUST NOT control:
DAX, metric definitions, semantic-model relationships, source mapping, visual storytelling, or
data validation. (A sentiment COLOR belongs in the theme; the sentiment THRESHOLD/RULE is a
metric contract, F009.)

Everything below is one of the MAY-set defaults. Nothing below carries a metric,
a formula, a relationship, a source mapping, a storytelling decision, or a
validation rule -- those are other features' jobs, not the theme's.

## 1. Palette

The brand/base colors the theme is built from. These are presentation defaults;
they carry no business meaning by themselves. Seed conservative, executive-retail
values from `design/tokens/tower-retail-design-tokens.yaml` -- not an
over-saturated SaaS palette.

| Role | Hex | Used for |
|------|-----|----------|
| Primary | `<#RRGGBB>` | primary brand accent (e.g. KPI emphasis, headers) |
| Secondary | `<#RRGGBB>` | secondary accent |
| Background | `<#RRGGBB>` | report/page base fill (a light neutral by default) |
| Surface | `<#RRGGBB>` | card/visual surface fill |
| Border / grid | `<#RRGGBB>` | gridlines, separators (low-contrast neutral) |

> Palette is the brand/base set. The chart SERIES colors are a separate sequence --
> see section 4 (data colors). Do not conflate the two.

## 2. Typography

Default fonts and sizes for titles, labels, and values. Use one font family for
the whole report (a mixed-font report is an anti-pattern). Seed from the tokens
file.

| Element | Font family | Size (pt) | Weight |
|---------|-------------|-----------|--------|
| Visual / card title | `<font_family>` | `<pt>` | `<regular | semibold | bold>` |
| KPI value | `<font_family>` | `<pt>` | `<weight>` |
| Axis / data labels | `<font_family>` | `<pt>` | `<weight>` |
| Body / table text | `<font_family>` | `<pt>` | `<weight>` |

## 3. Sentiment colors

The COLORS that signal good / caution / bad. These are colors only -- the
THRESHOLD/RULE that decides which sentiment a value gets is a metric contract
(F009), never set here (see the purity rule above).

| Sentiment | Hex | Meaning (color only) |
|-----------|-----|----------------------|
| Good / positive | `<#RRGGBB>` | favorable result |
| Caution / neutral | `<#RRGGBB>` | watch / on-track-but-not-met |
| Bad / negative | `<#RRGGBB>` | unfavorable result |

> Use a colorblind-safe combination (see section 8). Do NOT encode the
> good/caution/bad CUTOFFS here -- a cutoff is business logic (F009). The theme
> says "this is the bad-color"; the contract says "below X is bad".

## 4. Data colors

The ordered color sequence Power BI assigns to chart series/categories (the
theme's `dataColors`). Keep category/branch colors CONSISTENT across pages
(an inconsistent category-color scheme is an anti-pattern). This is a separate
list from the brand palette in section 1.

| # | Hex | Notes |
|---|-----|-------|
| 1 | `<#RRGGBB>` | first series / category |
| 2 | `<#RRGGBB>` | second series |
| 3 | `<#RRGGBB>` | third series |
| n | `<#RRGGBB>` | extend as needed; keep within a conservative, legible set |

## 5. Visual defaults

> **Emitted** by `seshat theme-gen` / `theme-compile` from committed design
> tokens. Key paths verified against `reportThemeSchema-2.156.json`.

Default formatting applied to all visuals unless a visual overrides it (an
override is a `warning`-class per-visual deviation recorded with a reason, in
`templates/visual-spec.yaml` -- defaults then deviations).

| Default | Value |
|---------|-------|
| Background / fill | `<color or 'none'>` |
| Border | `<on|off>`, color `<#RRGGBB>` |
| Title | `<on|off>`, alignment `<left|center>` |
| Data labels | `<on|off>` default |
| Gridlines | `<on|off>`, color `<#RRGGBB>` |
| Default number format | `<#,##0 | #,##0.00 | 0.0%>` (consistent formats; section depends on tokens) |

## 6. Filter-pane defaults

> **Emitted** by `seshat theme-gen` / `theme-compile` from committed design
> tokens. Key paths verified against `reportThemeSchema-2.156.json`.

The default look of the filter pane and its cards (a `filterPane` /
`filterCard` default in the theme). Presentation only.

| Default | Value |
|---------|-------|
| Filter-pane background | `<#RRGGBB>` |
| Filter-pane font / size | `<font_family>` / `<pt>` |
| Applied-filter card | background `<#RRGGBB>`, border `<#RRGGBB>` |
| Available-filter card | background `<#RRGGBB>`, border `<#RRGGBB>` |

## 7. Page background

> **Emitted** by `seshat theme-gen` / `theme-compile` from committed design
> tokens. Key paths verified against `reportThemeSchema-2.156.json`.

The theme's page/wallpaper DEFAULT fill -- a flat default color and transparency
for the page and wallpaper. This is the theme default ONLY.

| Default | Value |
|---------|-------|
| Page background color | `<#RRGGBB>` |
| Page background transparency | `<0-100 %>` |
| Wallpaper color | `<#RRGGBB>` |
| Wallpaper transparency | `<0-100 %>` |

> This is NOT the external background IMAGE. An exported PNG/SVG background
> (with safe zones and static containers) is surface 2 --
> `templates/background-spec.yaml`. The image sits as a page-image layer with the
> live visuals editable above it; the theme only sets the default fill behind it.

## 8. Accessibility checks

Each MUST be confirmed **with named evidence** before the theme is considered
done. A bare tick is NOT confirmation: a `[x]` with no cited evidence is an
UN-verified self-assertion and does not close the check (the same discipline
`DL4` applies to a design review, and hard rule #9's spirit -- do not assert a
pass nothing verified). A failed or unevidenced check is a `blocking_reasons[]`
entry or a recorded `warning` with a reason.

Evidence differs by check, because only ONE of these is computable from
committed text:

- [ ] **Contrast** -- text-to-background meets a readable ratio (aim WCAG AA;
      dark text on light surfaces by default).
      *Evidence: cite `CT1`'s verdict on the design-tokens the theme compiles
      from (the WCAG ratio is CT1's deterministic job, not a self-report). A
      theme cannot claim contrast on its own say-so.*
- [ ] **Color-vision-deficiency distinguishability** -- sentiment colors are
      distinguishable for common CVD (do not rely on red/green alone -- pair with
      position or icon downstream).
      *Evidence: a named reviewer + date (this is a human judgment call --
      Principle V; the kit does not rule on it). Cite the reviewer, not a tick.*
- [ ] **Small-size / adjacency legibility** -- the data-color sequence stays
      legible at small sizes and when adjacent.
      *Evidence: a named reviewer + date against a RENDERED page (F016 surface;
      not verifiable from committed text). Cite the reviewer, not a tick. If no
      render exists yet (the theme is authored before F016), leave this open and
      hold the theme at `warning` with a reason -- NOT `pass`, and not a silent
      tick.*
- [ ] **No pure-saturated background behind dense charts** -- a readability
      concern; record it as a `warning`-class design note, not a silent override.
      *Evidence: a named reviewer + date, or the recorded `warning` note. Cite
      it, not a tick.*

> Why evidence and not a checklist: a ticked box that nothing verified is exactly
> the self-asserted-but-unchecked accessibility pass this kit exists to prevent.
> Contrast is delegated to `CT1` (computed); the three judgment/render checks are
> owner/reviewer calls (Principle V) that carry a named human, never an
> unattributed confirmation. **A future evidence-gate rule (HELD) may enforce
> this shape on a FILLED theme spec; today no filled instance exists, so this
> template closes the hole at the DEFINE layer.**

## 9. JSON-validation reminder (schema treated as UNCERTAIN)

The exact Power BI theme JSON schema is treated as UNCERTAIN in this kit
(spec Assumptions). The compiled theme is a minimal, conservative STARTER.
Before relying on it:

- Confirm the file is VALID JSON (a single malformed key silently drops or
  rejects the theme on import).
- IMPORT it into Power BI Desktop and verify it loads and applies cleanly --
  Desktop is the source of truth for what the schema accepts. Do not assume an
  untested key is honored.
- Keep the theme to the safe, well-known keys; mark any uncertain key as such.
- The compiled artifact + its caveats live at `themes/<name>.theme.json` and
  `themes/README.md` (the STARTER + validate-in-Desktop + schema-uncertainty
  notes). This spec describes the intent; that JSON is what gets imported.

This spec edits no PBIP/PBIR file, generates no DAX, changes no SQL, and adds no
execution automation. Applying the validated theme is a surface-4 handoff step
for the official report-authoring owner or a human; F016 owns only parked live
semantic execution.

## Must NOT control (the explicit exclusion list)

Restated from the purity rule above so a reviewer sees it on its own: this theme
MUST NOT control DAX, metric definitions, semantic-model relationships, source
mapping, visual storytelling, or data validation. If a supplied theme tries to
encode any of these (for example a sentiment THRESHOLD by metric, or a measure
definition), separate it out: the COLOR stays in the theme; the RULE goes to its
owning feature (a sentiment threshold -> a metric contract, F009). The theme
carries no business meaning.

## Readiness

Record this theme's design readiness with the FOUR statuses only
(`docs/readiness/readiness-model.md`). NEVER a numeric confidence score
(roadmap rule 9). This is a styling artifact and does not -- and must not --
self-grant `dashboard_ready: pass`; that `pass` is the verb owner's recorded
design-review (F011/012), not this spec's.

- **Status:** `<not_started | blocked | warning | pass>`
- **Evidence:**
  - `<e.g. themes/<name>.theme.json validated in Power BI Desktop on <date>>`
  - `<e.g. section-8 contrast: CT1 clean on <tokens file> (cite CT1's verdict, not a tick)>`
  - `<e.g. section-8 CVD/legibility/saturation: reviewed by <named_human> on <date>>`
- **Blocking reasons (empty unless blocked):**
  - `<e.g. 'theme JSON failed to import in Desktop -- malformed key'>`
  - `<e.g. 'contrast check failed for sentiment colors'>`
  - `<e.g. 'section-8 CVD check has no named reviewer -- self-assertion, not confirmed'>`

(No `score:` / `confidence:` field exists here BY DESIGN -- rule 9.)

## See also

- Prose: `docs/powerbi/theme-json.md` (what theme JSON controls + must NOT control).
- Workflow: the `theme-json-design.md` workflow under
  `.claude/skills/powerbi-dashboard-design/` (the surface-3 procedure).
- Seed values: `design/tokens/tower-retail-design-tokens.yaml`.
- Compiled artifact: `themes/tower-retail.theme.json` + `themes/README.md`.
- Sister templates: `dashboard-page-blueprint.yaml` (the page), `visual-spec.yaml`
  (surface 1), `background-spec.yaml` (surface 2), `screenshot-review.md` (critique).
- The stage + gate (owned elsewhere, not restated here):
  `docs/readiness/dashboard-ready.md`.
- The readiness model (four statuses, no score): `docs/readiness/readiness-model.md`.
