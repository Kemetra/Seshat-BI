# Seshat BI — Claude Design System Design

**Status:** Draft for review
**Date:** 2026-06-26
**Author:** brainstorming session (advisor-assisted)
**Topic:** Author a self-contained, previewable component library that the
claude.ai `/design-sync` (DesignSync) tool can ingest, publishing the **Seshat
BI** visual identity as an org-visible design system.

---

## Goal

Produce a local bundle of self-contained **preview HTML cards** — one per
component/foundation — each tagged with a `<!-- @dsCard group="…" -->` marker,
that DesignSync uploads into a **new** `Seshat BI Design System` project on
claude.ai. The system renders the committed Seshat BI brand (not a from-scratch
invention) so it appears under "Design systems for everyone in your org."

This is **not** a React/Vite/Storybook app. The DesignSync contract renders
preview HTML files; the deliverable is ~12–15 static, inlined HTML files plus a
short README, not a build-tooled frontend package.

---

## Architecture

**One responsibility per file.** Each card is a single `.html` file that is
fully self-contained: all CSS inline, any raster/vector assets embedded as
`data:` URIs, no external fonts/scripts/stylesheets (claude.ai renders these
under a strict CSP that blocks external hosts — CDN fonts, remote images, and
fetch all fail).

```
design/claude-design-system/
  README.md                      # what this is, how to (re)sync, the don'ts
  foundations/
    01-color-palette.html        # brand palette + verified contrast table
    02-typography.html           # type scale + specimens (fallback stacks)
    03-spacing-grid.html         # spacing scale + 4px base + grid safe zones
  brand/
    04-seven-point-star.html     # the seven-point star (correct vs wrong)
    05-logo-system.html          # wordmark / stacked / CLI-icon layout slots
    06-brand-dos-donts.html      # the §3 non-negotiable rules, visualized
  components/
    07-kpi-card.html             # SIGNATURE: value+comparison+context+trend
    08-buttons.html              # primary / secondary / ghost, states
    09-sentiment-chips.html      # success / warning / danger / neutral chips
    10-data-table.html           # zebra rows, number formats, headers
    11-section-header.html       # page title + section header treatments
  patterns/
    12-exec-page-layout.html     # exec page: <=6 visuals, cards-over-tables
    13-number-formats.html       # the number-format reference (int/%/money)
  powerbi-surface/
    14-dashboard-tokens.html     # SEPARATE: the generic retail dashboard seed
```

**Card grouping** (the `@dsCard group="…"` value drives the Design System pane
sections): `Foundations`, `Brand`, `Components`, `Patterns`, `Power BI surface`.

---

## Foundation decision (the pivotal call — review this first)

The design system renders the **Seshat BI product brand** defined in
`docs/brand/visual-identity.md` — it is marked "Active — the committed brand for
the product." That is the identity an org-facing design system should show.

The **`design/tokens/tower-retail-design-tokens.yaml`** retail tokens are a
**different, intentionally generic seed** ("conservative executive retail",
"route to exactly one; never blend"). They are **NOT** the product brand and are
**NOT** blended into the core palette. They appear only in the isolated
`powerbi-surface/14-dashboard-tokens.html` card, clearly labeled as the generic
Power BI theme seed, so the two are never confused.

### Core brand palette (from visual-identity.md §5)

| Token | Hex | Role |
|-------|-----|------|
| `deep_navy` | `#001E35` | Main background, text base (60% + 25%) |
| `midnight_navy` | `#04172A` | Dark surfaces, app-icon background |
| `rich_gold` | `#C69214` | Star, rings, dividers, premium accents (10%) |
| `gold_light` | `#F2C14E` | Small highlights, metallic gradients |
| `teal` | `#0B9A9A` | Data network, `BI` accent, active states (5%) |
| `teal_light` | `#31C6C2` | Node/hover highlights |
| `ivory` | `#F7F1E7` | Brand-board / docs-cover background |
| `sand` | `#E8D8BD` | Subtle separators, soft panels |

Usage ratio (verbatim from §5): **60% ivory/navy base · 25% deep navy
text/structure · 10% rich gold accents · 5% teal data accents.**

---

## Accessibility — VERIFIED contrast (measured, not assumed)

WCAG 2.1 ratios computed for this spec (AA normal text ≥ 4.5:1, AA large/heading
≥ 3.0:1). These are **binding constraints** the cards must honor:

| Pair | Ratio | AA body | AA large | Rule it sets |
|------|------:|:-------:|:--------:|--------------|
| ivory on `deep_navy` | 15.11 | PASS | PASS | primary text treatment on dark |
| `deep_navy` on ivory | 15.11 | PASS | PASS | primary text treatment on light |
| `gold_light` on `deep_navy` | 10.12 | PASS | PASS | gold text OK on dark |
| `teal_light` on `deep_navy` | 8.07 | PASS | PASS | teal text OK on dark |
| `rich_gold` on `midnight_navy` | 6.48 | PASS | PASS | gold accents on app-icon bg |
| `rich_gold` on `deep_navy` | 6.08 | PASS | PASS | gold body text OK on dark |
| `teal` on `deep_navy` | 4.93 | PASS | PASS | teal body text OK on dark |
| **`teal` on ivory** | 3.06 | **fail** | PASS | teal = large/heading or non-text only on light |
| **`teal` on white** | 3.44 | **fail** | PASS | same |
| **`rich_gold` on ivory** | 2.48 | **fail** | **fail** | gold = non-text accent only on light (dividers/star), never text |

**Derived rule baked into every card:** gold and teal are *accent-on-dark*
colors. On light surfaces (ivory/sand) they are used only for large/heading text
or non-text accents (dividers, the star, rings) — **never gold body text on
ivory.** Brand rule §3.6 (do-not-rely-on-color-alone) and the
`do_not_rely_on_color_alone` token are honored: sentiment always pairs color +
icon/label.

---

## Open reconciliation item (flagged, NOT silently resolved)

`visual-identity.md` §7 says dashboards use **navy and ivory backgrounds**. The
retail seed `tower-retail-design-tokens.yaml` sets dashboard
`background: #FFFFFF` (white). These conflict. This spec does **not** pick a
winner — it records the conflict and presents both: the brand cards use
navy/ivory; the isolated Power BI surface card shows the white-background seed
as-is and notes the divergence. **Resolution is a question for the user** (likely:
brand governs covers/headers; the retail seed governs in-canvas Power BI default
theming — but that is theirs to confirm). Tracked as an open item, not a code
change to either source file.

---

## Component details

### Signature: KPI card (`07-kpi-card.html`)
The most important card. Renders the `kpi_card` contract from the design tokens
**and** brand rule §7 ("every KPI card must trace back to a metric contract"):
- value (headline number) + comparison (vs prior/target) + context label
  (what/when) + trend indicator — a bare number is the anti-pattern.
- sentiment color + icon (never color alone), max 1 decimal on headline.
- **All numbers are FABRICATED samples** — no real retail/C086/pharmacy values
  (the token file forbids inlining those; this keeps the system data-free).

### Other components
- **Buttons** — primary (gold-on-navy), secondary (teal accent), ghost; default
  / hover / active / disabled states.
- **Sentiment chips** — success/warning/danger/neutral, each color + icon + label.
- **Data table** — zebra striping (neutral ramp), aligned number formats, header
  treatment; fabricated rows.
- **Section header** — page-title (20pt) and section-header (14pt) treatments,
  wide letter-spacing on labels per §6.

### Foundations / Brand / Patterns
Color palette (with the verified contrast table rendered), type scale with
specimens using **fallback stacks only** (Georgia / Segoe UI / Consolas — the
declared fallbacks, since Cinzel/Inter won't load under CSP), spacing+grid, the
seven-point star (correct seven-point vs wrong eight-point, per §3.1–3.2),
logo-system layout, the §3 non-negotiable rules visualized, exec-page layout
(≤6 visuals, cards-over-tables), and the number-format reference.

---

## Sync workflow (the one outward-facing step — gated)

1. **Build locally** — author all cards in `design/claude-design-system/`.
   Fully local; zero outward effect.
2. **Self-check** — open each HTML locally, confirm it renders standalone, no
   external requests, `@dsCard` marker on line 1, contrast rules honored,
   no real data anywhere.
3. **Confirm with the user before any push.** A synced system becomes
   **org-visible**. The push is treated as publishing.
4. **DesignSync** (only after explicit go-ahead):
   `create_project` (name: `Seshat BI Design System`) →
   `finalize_plan` (exact path list, shown to the user as the review boundary) →
   `write_files`. Incremental, never wholesale replace.

No `projectId` is hardcoded; the sync resolves create→write at push time.

---

## Testing

This is static HTML, so "testing" = a deterministic local self-check (no test
runner needed):
- **Self-containment:** grep each file for `http://`, `https://`, `src=`,
  `@import`, `url(` pointing off-host → must be empty (or `data:` only).
- **Marker presence:** line 1 of each card matches `<!-- @dsCard group="…" -->`.
- **Contrast:** the palette card's rendered ratios match the verified table
  above (the numbers are computed, embedded, and visually confirmed).
- **Data-free:** grep for `C086`, `pharmacy`, and any real-looking value →
  empty; every number is an obvious sample.

---

## Scope discipline (YAGNI)

- ~14 static HTML files + one README. No React, no bundler, no npm, no new
  dependency. Nothing wired into `src/retail/` runtime.
- Does **not** modify `docs/brand/visual-identity.md` or the retail token file —
  it *renders* them.
- The background conflict is recorded, not fixed in source.
- Build is small enough to execute inline; does not need the full
  subagent-driven-development fleet.

---

## Decisions made

1. **Foundation = Seshat BI product brand** (visual-identity.md), not the retail
   seed and not a from-scratch invention.
2. **Retail tokens kept separate and labeled**, never blended.
3. **New `Seshat BI Design System` project** — additive, zero blast radius to
   the two existing POS Pulse projects.
4. **Contrast verified, not cited** — gold/teal are accent-on-dark; light-surface
   text rules derived from measured ratios.
5. **All sample data fabricated** — the system carries no real data or secrets.
6. **Push is gated** on explicit user go-ahead at sync time (org-visible).
7. **Navy-vs-white background conflict** surfaced as an open item for the user.

---

## Open questions for the user

1. **Background reconciliation:** brand says navy/ivory dashboards; retail seed
   says white. Confirm the split (brand for covers/headers; retail seed for
   in-canvas Power BI theme defaults) or state a single rule.
2. Any logo/star **SVG assets** you want embedded now, or should the brand cards
   use clean placeholder line-art slots until the final seven-point star asset
   is exported (per §10, the asset set is "approved conceptually" pending a final
   export)?
