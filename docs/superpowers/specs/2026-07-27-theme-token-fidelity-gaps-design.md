# Theme-token and preview fidelity gaps (#521)

**Date:** 2026-07-27
**Issue:** #521 (successor findings to PR #518; three originals fixed in #523)
**Status:** design, approved for planning

## Summary

Issue #521 lists six findings against the section 5/6/7 token groups
(`chrome:` / `page:`) that PR #518 introduced. **One of the six is already
fixed**; five are live and reproduced. All five share one shape: a token group
is threaded into a consumer that only partially reads it, so a declared setting
is measured wrong, derived wrong, or not shown at all.

This spec covers the five live findings across two PRs.

## Correction to the issue as filed

**Finding 4 (preview line styling uses `colors.secondary` rather than
`chrome.border`/`chrome.gridline`) is FIXED** on `main` at
`blueprint_preview.py:117-138` (`_line_color_from_tokens`), landed in `9b8b76b`
and pinned by four tests in `tests/unit/test_blueprint_preview_styled.py:194-260`.
It resolves `chrome.border` -> `chrome.gridline` -> `colors.secondary` using key
*presence*, so an explicit `null` correctly means borders-off.

The issue must be corrected to five findings rather than closed as six. Closing
six when four were fixed would be the same silent-truncation shape the issue is
about.

## Reachability — latent, unchanged

No committed tokens file declares `chrome:` or `page:` (`seshat check` exits 0
on `2da8358`). None of these findings affects a committed artifact today; they
become reachable the first time a real tokens file adopts the groups. This is
hardening ahead of first use, which also means regression risk is low and
`seshat check` exit 0 before and after is a meaningful signal.

## Verified reproductions

Run against the source tree (`PYTHONPATH=src`) on `2da8358`. The issue recorded
findings 1 and 2 as "plausible from the code path but I did not run it"; both
are now reproduced, and finding 1 differs from how the issue described it.

### Finding 1 — uncomposited ground, fail-open CONFIRMED

```
page:   {background: '#101820', background_transparency: 100}
chrome: {border: '#E8E8E8'}
palette background: #FFFFFF
```

- Gate measures border `#E8E8E8` against the declared `#101820` -> **14.60:1**, passes the 3:1 floor.
- True render: the page background is 100% transparent, so the page shows `#FFFFFF`; border on white is **1.23:1** -> invisible.
- `check_non_text_contrast_or_raise` **passed**. Fail-open confirmed.

**The error runs both ways.** The inverse case (`page.background: #FFFFFF` at
100% transparency over a `#101820` palette, border `#D8D8D8`) is *falsely
refused*: the gate reports 1.43:1 and raises, while the border would truly
render at 12.55:1 — plainly visible. Measuring an uncomposited ground is wrong
in both directions, so the fix must correct the ground, not add a one-sided
tolerance.

`check_composite_contrast_or_raise` never participates: it iterates
`palette["transparency"]` roles only (`theme_gen.py:325-329`) and never reads
the `page` group.

### Finding 2 — dark derive passthrough, CONFIRMED (worse than filed)

```
light seed: page={'background': '#FFFFFF'}, chrome={'gridline': '#E0E0E0'}
derive_dark_seed(...) ->
  page   = {'background': '#FFFFFF'}   (unchanged)
  chrome = {'gridline': '#E0E0E0'}     (unchanged)
  palette background = #000000         (correctly inverted)
emitted visualStyles["page"]["*"]["background"] = #FFFFFF
```

The palette inverts to black while the emitted page card stays white, so the
"dark" theme paints a **white page**. `derive_dark_seed` (`theme_gen.py:136-144`)
names its inverted fields in `replace()` kwargs and `page`/`chrome` are not
among them.

### Finding 3 — documented degrade contract violated, CONFIRMED

`_load_yaml_mapping` correctly returns `{}` for an absent file
(`blueprint_preview.py:94-95`), but `_style_from_tokens` then raises because
`colors` is absent (`:161-168`). The committed contract at
`.claude/skills/powerbi-dashboard-design/workflows/blueprint-preview.md:84-86`
says `tokens_path` "follows the same degrade/raise split when given". The error
message is also misleading: it reports "has no 'colors' mapping" for a file that
does not exist.

### Findings 5 and 6 — preview fidelity, CONFIRMED

- **5:** only 3 of 14 `_text` call sites pass `fill` (page title `:447`, visual placeholder `:321`, disclaimer `:484`). The other 11 emit no `fill`, so on a dark canvas they fall to SVG-default black. Four block helpers — `_narrative_block` (`:333`), `_slicers_block` (`:350`), `_footer_block` (`:362`), `_navigation_block` (`:396`) — do not receive the style dict at all.
- **6:** `_style_from_tokens` sets `"ground"` from `colors.background` (`:171`). The file never reads the `page` group, while `theme_gen._non_text_ground:436-443` documents `page.background` as *overriding* the palette background as the page's real fill.

## Decisions taken

Three forks were put to the owner; all three took the recommended option.

| # | Decision | Ruling |
|---|---|---|
| D1 | Dark-derive treatment of `page`/`chrome` | **Invert every declared color-valued key**; leave non-color keys untouched; gates re-validate the derived seed |
| D2 | Missing `tokens_path` | **Honor the committed doc**: absent degrades to monochrome, present-but-broken still raises |
| D3 | Preview fidelity scope | **Fix 5+6 as scoped**; no transparency/wallpaper compositing in the preview |

D3 keeps the shipped principle intact: preview fidelity is approximate,
permanently, and the preview renders from TOKENS, never from emitted JSON.
Reading `page.background` from the same tokens file is within that principle;
reimplementing Power BI's compositor in SVG is not.

## Architecture — two PRs on a real seam

**PR A — theme correctness** (`theme_gen.py`). Findings 1 + 2.
They interact: once dark-derive inverts `page.background`, the non-text gate
measures a different ground. Landing them separately means writing the same
test expectations twice.

**PR B — preview fidelity** (`blueprint_preview.py`). Findings 3 + 5 + 6.
Findings 3 and 6 edit the same ~10 lines of `_style_from_tokens`; splitting them
would mean two conflicting edits to one function.

PR A lands first so PR B's fidelity tests assert against settled semantics.

**Branching:** PR A (`fix/521-theme-token-fidelity-gaps`) carries this spec doc.
PR B branches off `main` **after** A merges, so the doc is not duplicated and B
needs no rebase. Merging sequentially also avoids the `capabilities.yaml` /
strict-mode collisions that concurrent branches in this repo have hit before.

## PR A — theme correctness

### Finding 2: closed color-key sets

Replace the hand-listed `replace()` kwargs with a derivation over two closed
sets of color-valued keys:

```
_PAGE_COLOR_KEYS   = background, wallpaper, filter_pane_background,
                     filter_pane_text, filter_card_applied, filter_card_available
_CHROME_COLOR_KEYS = gridline, border
```

Rules:

- Only keys **actually declared** in the seed are inverted; a key absent from the group stays absent (never fabricate a token).
- An explicitly `None` value is an "off" declaration and stays `None`.
- Non-color keys pass through untouched: `background_transparency`, `wallpaper_transparency`, `title_align`, `data_labels`, `number_format`.
- Inversion uses the existing `_invert_lightness`, the same function the palette roles already use.

**Vocabulary-drift guard.** Per the `gate-must-match-reader` invariant, a test
asserts `_PAGE_COLOR_KEYS` is a subset of `PAGE_TOKEN_KEYS` and
`_CHROME_COLOR_KEYS` a subset of `CHROME_TOKEN_KEYS`, and that the union of
color and known-non-color keys **exhausts** each vocabulary. Adding a token key
to a vocabulary without classifying it then fails loudly, instead of silently
passing a light color into a dark theme — which is exactly how finding 2 arose.

`derive_dark_seed`'s docstring currently says "Accent/data_colors/sentiment/fonts
pass through unchanged" without naming `page`/`chrome`. It must be corrected to
state what now derives and what still passes through.

**Attribute a derived-seed refusal to the derivation.** Inverting both halves of
a filter-pane pair does not preserve their contrast ratio, so a pair that cleared
AA in light mode can fail the pane gate (`theme_style_cards.py:250-261`) on the
derived dark seed. Per D1 that refusal is correct and stays. But a bare pane-AA
error would read as a fault in the authored tokens, so `generate_pair` must
surface that the failing pair came from the **derived dark seed**, not the
authored light one — otherwise the author debugs the wrong file.

### Finding 1: composite the ground before measuring

`_non_text_ground` returns the raw declared `page.background`. When
`page.background_transparency` is declared, the ground must be the page
background alpha-composited over the palette background before any contrast
measurement. `composite_over` is already imported at `theme_gen.py:24`.

Semantics, verified at `color.py:90-109`: `transparency_pct` is in `[0, 100]`,
where **0 is fully opaque `fg`** (result equals the declared page background) and
**100 is fully transparent** (result equals the palette background). It blends
per-channel in sRGB/gamma space, matching how a UI framework composites two
already-encoded colors, and raises `ValueError` for an out-of-range pct or
malformed hex. So the call is
`composite_over(page_background, palette_background, transparency_pct)`, and a
test pins both endpoints.

This **tightens** a gate: a border that previously passed may now be refused,
and one previously refused may now pass. Both are corrections, and both
directions get a test.

## PR B — preview fidelity

### Finding 3: absent vs present-but-broken

`_style_from_tokens` distinguishes the two states before consulting `colors`:

| `tokens_path` | Behavior |
|---|---|
| `None` | `{}` — monochrome (unchanged) |
| names a nonexistent file | `{}` — monochrome (**changed**) |
| exists, empty / all-null | `{}` — monochrome |
| exists, not a mapping | raise `PreviewInputError` |
| exists, mapping without `colors` | raise `PreviewInputError` |

The nonexistent-file case must not reuse the "has no 'colors' mapping" message.

### Finding 6: ground from the page group

`"ground"` resolves `page.background`, falling back to `colors.background`, then
`_DEFAULT_STYLE["ground"]`. Uses the same key-**presence** discipline as
`_line_color_from_tokens`, so an explicit `page.background: null` is a real
declaration rather than a fall-through.

### Finding 5: fill at every text site

Thread the style dict into `_narrative_block`, `_slicers_block`,
`_footer_block`, and `_navigation_block`, and pass `fill` at all 14 `_text`
sites — `ink` for primary content, `ink_muted` for secondary/reference lines,
matching the three sites that already do this.

No test calls any of those four helpers directly (verified: no match for them
under `tests/`), so adding a `style` parameter is safe and does not need a
keyword-with-default to protect unrelated tests.

**Constraint:** the no-tokens path must stay attribute-free.
`_style_from_tokens(None)` returns `{}`, `.get()` yields `None`, and
`_style_attr` suppresses falsy values — so the fix flows through only if it
threads the real style dict. Substituting `_DEFAULT_STYLE` on the no-tokens path
would break `test_omitting_tokens_leaves_output_unchanged`, correctly.

## Testing

The oracle matters more than the count. Three specific traps:

1. **Findings 1, 2, 3 assert the observable change, not an absence.** For 1 and 3 that means asserting the error **is raised** (and, for the newly-passing direction, that it is *not*); for 2, that the derived value actually inverted. The issue names this explicitly: a test asserting the bad value is merely absent from output passes for the wrong reason, since it is absent either way.
2. **Write finding 2's RED test first.** No existing test passes a seed carrying a `page` group through `generate_pair`, so that path is entirely untested. The reproduction above is the oracle; the test must fail before the fix.
3. **`test_tokens_color_the_canvas_ground_specifically`** (`test_blueprint_preview_styled.py:163-175`) asserts `fill="#101820"` from `colors.background` with no `page` group in its fixture — so it passes finding 6's fix without exercising it. It needs a sibling case where `page.background` differs from `colors.background` and the canvas follows the former.

New coverage: both transparency endpoints for finding 1; both fail-open and
false-refusal directions; the vocabulary-exhaustion guard; each row of the
finding-3 table; a dark-canvas render asserting no text element lacks a `fill`.

**Derived-dark tokens round-trip.** `render_tokens_yaml` persists `chrome`/`page`
(#523), so `generate_pair` now writes *inverted* page/chrome into the dark tokens
YAML. A test must assert that file carries the inverted `page.background` and
that re-reading it through the readers does not raise. Without it the inversion
could be right in the emitted theme and wrong in the artifact a human edits next.

Existing suites that must stay green: `test_theme_gen.py`,
`test_theme_gen_breadth.py`, `test_theme_compile*.py`,
`test_blueprint_preview*.py`, plus `seshat check` exit 0.

## Out of scope

- Wallpaper / transparency compositing inside the preview SVG (D3).
- Filter-pane and filter-card *rendering* in the preview; only the canvas ground and text fills are in scope.
- `#520`'s card/property/entry pruning logic — untouched.
- Visual-type coverage beyond `page_shell`/`lineChart`, per the #518 spec's own out-of-scope list.

## Risks

- **Tightening a gate can refuse a previously-accepted seed.** Latent today (no committed tokens file declares these groups), so no committed artifact changes. Both directions are tested so the new behavior is deliberate rather than emergent.
- **`composite_over`'s transparency direction.** Resolved during design (`color.py:93-94`: 0 opaque, 100 transparent), so this is no longer an open unknown. It stays listed because getting it backwards would produce a gate that *looks* fixed while measuring the wrong ground — a silent failure mode. Pinned by endpoint tests.
- **Dark inversion of filter-pane pairs** could in principle produce a pane that fails its own AA gate at `theme_style_cards.py:250-261`. That gate is the backstop and its refusal is correct behavior; the test suite covers a declared filter-pane pair through `generate_pair`.

## Data safety

- [x] This spec contains no secrets, real connection strings, client data, or PII.
