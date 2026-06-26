# Seshat BI — Claude Design System (preview bundle)

Self-contained preview cards for the claude.ai DesignSync tool. Renders the
committed **Seshat BI** brand (`docs/brand/visual-identity.md`).

## Layout
- `colors_and_type.css` — brand tokens as CSS custom properties (source of truth).
- `preview/_card.css` — shared card stylesheet (imports the tokens).
- `preview/*.html` — one `@dsCard`-marked card per component/foundation.
- `validate_cards.py` — render-check validator (run before any sync).

## Validate
`python validate_cards.py preview`  → `[OK] 15 cards, 2 css clean`.

## Sync (org-visible — get explicit go-ahead first)
1. Validate (above) must pass.
2. DesignSync: `create_project` (name "Seshat BI Design System") → `finalize_plan`
   (exact path list) → `write_files`. Incremental; never wholesale replace.

## Don'ts
- No external hosts (CSP): no CDN fonts / `@import url(https://...)` / remote assets.
- No real data: no C086, no pharmacy, no tenant values — fabricated samples only.
- Do not blend the Power BI retail seed into the brand palette.
- The Seshat star is always seven-pointed.
