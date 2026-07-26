# Theme Breadth + Headless Styled Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit Power BI theme spec §5/§6/§7 (visual defaults, filter-pane, page background) from the existing token pipeline, and render a styled SVG preview from those same tokens so a human can review a theme without opening Power BI Desktop.

**Architecture:** One source of truth — the committed `design/tokens/*-design-tokens.yaml` — gains a second consumer. `theme_gen.render_theme_json` grows three new emission targets (all verified against Microsoft's published schema); `blueprint_preview.render_blueprint_preview` gains an optional `tokens_path` that colors the SVG. Because both read the same tokens, the preview cannot drift from the artifact Power BI receives.

**Tech Stack:** Python 3.13, stdlib only (`json`, `pathlib`, `colorsys`) plus `pyyaml` (existing dependency) and the local `seshat.color` WCAG helper. No new dependencies. No pbi-cli, no MCP, no network, no database.

## Global Constraints

- **Design spec:** `docs/superpowers/specs/2026-07-26-theme-breadth-styled-preview-design.md`. Read it before Task 1.
- **Schema pinned to 2.156.** All key paths verified against `reportThemeSchema-2.156.json` in `microsoft/powerbi-desktop-samples`. Do not invent key names; if a needed key is absent from the table below, STOP and ask.
- **Environment (this worktree):** run every command with
  `export PYTHONPATH="$(pwd)/src"` and
  `export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=commit.gpgsign GIT_CONFIG_VALUE_0=false GIT_CONFIG_KEY_1=tag.gpgsign GIT_CONFIG_VALUE_1=false`.
  Without both, 15 unit tests fail for environmental reasons unrelated to your change.
- **Run tests with `--no-cov`.** Use `python -m pytest`, never bare `pytest`.
- **No live surface.** Never add a module-scope import of `psycopg2`, `requests`, `socket`, `urllib`, or any DB/network library to `theme_gen.py`, `theme_compile.py`, or `blueprint_preview.py`. Rules B1/B3 are AST guards that BLOCK on this.
- **Never `--no-verify`, never commit to `main`, never push to `main`.** Work stays on the current worktree branch.
- **No approval granted.** No code here may set a readiness stage, write an approval, or emit a confidence/readiness score.
- **`filter pane LOOK only`.** §6 styles appearance. Never read or write filter state, selections, or bound fields.
- **Determinism.** Never use `Date.now`, `time`, `random`, `uuid`, or unsorted iteration in emitted output. Sort every dict key you emit (`json.dumps(..., indent=2)`, and the existing code relies on insertion order being deterministic).
- **Line endings / encoding.** Read JSON and TMDL with `encoding="utf-8-sig"`. Write with `\n` only.

### Verified emission targets (do not deviate)

| Spec § | Exact key path | Cards in scope |
|---|---|---|
| §5 | `visualStyles["*"]["*"]` | `categoryAxis`, `valueAxis`, `border`, `title`, `labels` |
| §6 | `visualStyles["page"]["*"]` | `outspacePane`, `filterCard` |
| §7 | `visualStyles["page"]["*"]` | `background`, `outspace` (= wallpaper) |

`filterCard` is an ARRAY of two objects discriminated by `$id`: `"Applied"` and `"Available"`.

### Existing API you will use (verified signatures)

```python
# seshat.color
contrast_ratio(a: str, b: str) -> float
composite_over(fg: str, bg: str, transparency_pct: float) -> str
delta_e76(a: str, b: str) -> float
is_valid_hex(s: str) -> bool
format_pt(value: float) -> float | int

# seshat.theme_gen
AA_FLOOR = 4.5
MIN_TITLE_FONT_PT = 12.0
MIN_LABEL_FONT_PT = 9.0
class ThemeSeed  # frozen dataclass; see Task 2 for the fields you add
def render_theme_json(palette: dict, seed: ThemeSeed) -> str
def check_contrast_or_raise(palette: dict, floor: float = AA_FLOOR) -> None
class ThemeGenError(Exception)

# seshat.theme_compile
_DL3_DEFERRED_FIELDS: tuple[str, ...]
_GENERATOR_OWNED_VISUAL_STYLE_KEYS = ("title", "labels", "background")
def _human_owned_visual_styles(vs: object) -> object
class ThemeCompileError(Exception)
```

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `src/seshat/theme_compile.py` | Generalize the generator-owned carve-out so new emitted keys are not read as hand-tuning | 1 |
| `src/seshat/theme_style_cards.py` (NEW) | Pure card-builder functions: tokens → §5/§6/§7 card dicts. No I/O, no validation. | 2, 3 |
| `src/seshat/theme_gen.py` | `ThemeSeed` new optional fields; `render_theme_json` calls the card builders; new non-text contrast gate | 2, 3, 4 |
| `src/seshat/blueprint_preview.py` | Optional `tokens_path`; token-driven colors; third-state reporting | 5, 6 |
| `tests/unit/test_theme_style_cards.py` (NEW) | Card-builder unit tests | 2, 3 |
| `tests/unit/test_theme_gen_breadth.py` (NEW) | Emission + gate + key-name-safety tests | 2, 3, 4 |
| `tests/unit/test_theme_compile_carveout.py` (NEW) | Round-trip / no-false-conflict tests | 1 |
| `tests/unit/test_blueprint_preview_styled.py` (NEW) | Styled render + no-tokens regression + third state | 5, 6 |

**Why a new `theme_style_cards.py`:** `theme_gen.py` is already 780 lines. Adding three card builders plus their vocabularies would push it past the ~800-line CodeScene gate. A cohesive sub-domain module that `theme_gen` imports keeps both files focused — the pattern this repo already used for `redaction_core.py`.

---

### Task 1: Generalize the DL3 generator-owned carve-out

**Why first:** `_human_owned_visual_styles` hardcodes a walk into `visualStyles["*"]["*"]`. The moment Task 3 emits `visualStyles["page"]`, that key is unpruned, so `existing != rendered` and `theme-compile` refuses to recompile its own output — **even with `--force`**, because the conflict check runs before the force branch. Fix the carve-out before the emitter grows, or every later task fails for a misleading reason.

**Files:**
- Modify: `src/seshat/theme_compile.py` (`_GENERATOR_OWNED_VISUAL_STYLE_KEYS`, `_human_owned_visual_styles`)
- Test: `tests/unit/test_theme_compile_carveout.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `_GENERATOR_OWNED_CARDS: dict[str, tuple[str, ...]]` mapping visual-type name → generator-owned card names. `_human_owned_visual_styles(vs: object) -> object` keeps its signature.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_theme_compile_carveout.py`:

```python
import pytest

from seshat.theme_compile import _human_owned_visual_styles

pytestmark = pytest.mark.unit


def test_generator_owned_page_cards_are_pruned():
    """A generator-emitted visualStyles["page"]["*"] is NOT human-owned."""
    vs = {
        "page": {
            "*": {
                "background": [{"color": {"solid": {"color": "#FFFFFF"}}}],
                "outspace": [{"color": {"solid": {"color": "#F3F2F1"}}}],
                "outspacePane": [{"backgroundColor": {"solid": {"color": "#FFF"}}}],
                "filterCard": [{"$id": "Applied"}, {"$id": "Available"}],
            }
        }
    }
    assert _human_owned_visual_styles(vs) == {}


def test_human_added_page_card_survives_pruning():
    """A card the generator does NOT own stays visible as human-owned."""
    vs = {"page": {"*": {"pageRefresh": [{"show": True}]}}}
    assert _human_owned_visual_styles(vs) == {
        "page": {"*": {"pageRefresh": [{"show": True}]}}
    }


def test_generator_owned_star_cards_still_pruned():
    """Regression: the original *//* carve-out must keep working."""
    vs = {
        "*": {
            "*": {
                "title": [{"fontSize": 12}],
                "labels": [{"fontSize": 9}],
                "categoryAxis": [{"gridlineStyle": "dotted"}],
            }
        }
    }
    assert _human_owned_visual_styles(vs) == {}


def test_human_added_visual_type_survives():
    """Regression: an unrelated visual type is untouched."""
    vs = {"scatterChart": {"*": {"bubbles": [{"bubbleSize": -10}]}}}
    assert _human_owned_visual_styles(vs) == vs
```

- [ ] **Step 2: Run test to verify it fails**

```bash
export PYTHONPATH="$(pwd)/src"
python -m pytest tests/unit/test_theme_compile_carveout.py -v --no-cov
```

Expected: `test_generator_owned_page_cards_are_pruned` FAILS (returns the `page` dict unchanged, not `{}`) and `test_generator_owned_star_cards_still_pruned` FAILS (`categoryAxis` is not yet generator-owned). The other two PASS.

- [ ] **Step 3: Replace the hardcoded walk with a table-driven one**

In `src/seshat/theme_compile.py`, replace `_GENERATOR_OWNED_VISUAL_STYLE_KEYS` and `_human_owned_visual_styles` with:

```python
# Generator-owned cards per visual type. A card listed here is written by
# theme_gen from committed tokens, so it is NEVER a human hand-tune -- pruning it
# before the DL3-deferred comparison is what lets a token change recompile over an
# existing theme (T8/T18, and spec 5/6/7). Any card NOT listed is human-owned.
_GENERATOR_OWNED_CARDS: dict[str, tuple[str, ...]] = {
    "*": ("title", "labels", "background", "categoryAxis", "valueAxis", "border"),
    "page": ("background", "outspace", "outspacePane", "filterCard"),
}

# Back-compat alias: the original name, now derived from the table above.
_GENERATOR_OWNED_VISUAL_STYLE_KEYS = _GENERATOR_OWNED_CARDS["*"]


def _prune_generator_cards(style: object, owned: tuple[str, ...]) -> object:
    """One style-preset dict with the generator-owned cards removed."""
    if not isinstance(style, dict):
        return style
    return {k: v for k, v in style.items() if k not in owned}


def _human_owned_visual_styles(vs: object) -> object:
    """``visualStyles`` with every generator-owned card removed.

    Table-driven over ``_GENERATOR_OWNED_CARDS`` so a new emission target (a new
    visual type or card) is declared in one place. Comparing the returned value
    across existing-vs-rendered detects a hand-tuned visualStyle a human added
    while ignoring token-driven churn the generator legitimately owns. An empty
    style preset or visual type is dropped entirely so it cannot register as a
    spurious conflict.
    """
    if not isinstance(vs, dict):
        return vs
    result: dict[str, object] = {}
    for visual_type, presets in vs.items():
        owned = _GENERATOR_OWNED_CARDS.get(visual_type)
        if owned is None or not isinstance(presets, dict):
            result[visual_type] = presets
            continue
        kept_presets: dict[str, object] = {}
        for preset_name, style in presets.items():
            if preset_name != "*":
                # A NAMED style preset is human-authored by definition.
                kept_presets[preset_name] = style
                continue
            pruned = _prune_generator_cards(style, owned)
            if pruned:
                kept_presets[preset_name] = pruned
        if kept_presets:
            result[visual_type] = kept_presets
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/unit/test_theme_compile_carveout.py -v --no-cov
```

Expected: 4 passed.

- [ ] **Step 5: Verify no existing theme test regressed**

```bash
python -m pytest tests/unit/ -k "theme" -q --no-cov
```

Expected: all pass. If a test asserting the old `_GENERATOR_OWNED_VISUAL_STYLE_KEYS` tuple fails, the alias in Step 3 is wrong — fix the alias, do not change the test.

- [ ] **Step 6: Commit**

```bash
git add src/seshat/theme_compile.py tests/unit/test_theme_compile_carveout.py
git commit -m "refactor: make the DL3 generator-owned carve-out table-driven

_human_owned_visual_styles hardcoded a walk into visualStyles[*][*], so any new
emission target would be misread as human hand-tuning and theme-compile would
refuse to recompile its own output -- even with --force, since the conflict check
runs first. Declares owned cards per visual type in one table instead.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: §5 visual-default cards (builder + emission)

**Files:**
- Create: `src/seshat/theme_style_cards.py`
- Create: `tests/unit/test_theme_style_cards.py`
- Modify: `src/seshat/theme_gen.py` (`ThemeSeed`, `render_theme_json`)
- Create: `tests/unit/test_theme_gen_breadth.py`

**Interfaces:**
- Consumes: `_GENERATOR_OWNED_CARDS` from Task 1 (already lists the §5 cards).
- Produces:
  - `VALID_NUMBER_FORMATS: tuple[str, ...] = ("#,##0", "#,##0.00", "0.0%")`
  - `class StyleCardError(Exception)`
  - `build_star_cards(chrome: dict) -> dict[str, list[dict]]`
  - `ThemeSeed.chrome: dict | None = None` (new field, default `None` keeps every existing caller byte-identical)

- [ ] **Step 1: Write the failing test for the card builder**

Create `tests/unit/test_theme_style_cards.py`:

```python
import pytest

from seshat.theme_style_cards import (
    VALID_NUMBER_FORMATS,
    StyleCardError,
    build_star_cards,
)

pytestmark = pytest.mark.unit

CHROME = {
    "gridline": "#E1DFDD",
    "border": "#C8C6C4",
    "title_align": "left",
    "data_labels": False,
    "number_format": "#,##0",
}


def test_build_star_cards_emits_both_axes_and_border():
    cards = build_star_cards(CHROME)
    assert set(cards) == {"categoryAxis", "valueAxis", "border"}
    assert cards["categoryAxis"] == [
        {"gridlineColor": {"solid": {"color": "#E1DFDD"}}, "gridlineShow": True}
    ]
    assert cards["border"] == [
        {"color": {"solid": {"color": "#C8C6C4"}}, "show": True}
    ]


def test_gridline_none_turns_gridlines_off_without_a_color():
    cards = build_star_cards({**CHROME, "gridline": None})
    assert cards["categoryAxis"] == [{"gridlineShow": False}]
    assert cards["valueAxis"] == [{"gridlineShow": False}]


def test_out_of_vocabulary_number_format_is_refused():
    with pytest.raises(StyleCardError, match="number_format"):
        build_star_cards({**CHROME, "number_format": "0.000"})


def test_every_valid_number_format_is_accepted():
    for fmt in VALID_NUMBER_FORMATS:
        build_star_cards({**CHROME, "number_format": fmt})


def test_invalid_hex_is_refused():
    with pytest.raises(StyleCardError, match="gridline"):
        build_star_cards({**CHROME, "gridline": "not-a-hex"})


def test_bad_title_alignment_is_refused():
    with pytest.raises(StyleCardError, match="title_align"):
        build_star_cards({**CHROME, "title_align": "justified"})


def test_empty_chrome_emits_no_cards():
    assert build_star_cards({}) == {}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/unit/test_theme_style_cards.py -v --no-cov
```

Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.theme_style_cards'`.

- [ ] **Step 3: Write the card builder**

Create `src/seshat/theme_style_cards.py`:

```python
"""Power BI theme style-card builders (theme spec sections 5/6/7).

Pure functions: committed design tokens in, theme-JSON card dicts out. No I/O, no
file reads, no validation of the wider theme -- ``theme_gen`` owns those. Split
from ``theme_gen`` so neither module carries both the palette pipeline and the
card vocabularies.

Every key path here is verified against Microsoft's published validation schema
(``reportThemeSchema-2.156.json``, ``microsoft/powerbi-desktop-samples``):

    visualStyles > <visualName> > <stylePresetName> > <cardName> > [{prop: value}]

Stdlib only. Uses no pbi-cli, no live Power BI, no network.
"""

from __future__ import annotations

from seshat.color import is_valid_hex

# The theme spec's stated number-format vocabulary (section 5). Anything else is
# refused rather than passed through, mirroring how ``_VALID_SCALING`` constrains
# page-background scaling.
VALID_NUMBER_FORMATS: tuple[str, ...] = ("#,##0", "#,##0.00", "0.0%")

VALID_TITLE_ALIGNMENTS: tuple[str, ...] = ("left", "center", "right")


class StyleCardError(Exception):
    """A style-card token problem surfaced cleanly (no traceback)."""


def _fill(hex_color: str) -> dict:
    """The theme JSON fill wrapper Power BI expects for a color value."""
    return {"solid": {"color": hex_color}}


def _require_hex(value: object, field: str) -> str:
    if not isinstance(value, str) or not is_valid_hex(value):
        raise StyleCardError(f"{field} must be a #RRGGBB hex color, got {value!r}")
    return value


def _require_pct(value: object, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise StyleCardError(f"{field} must be a number 0-100, got {value!r}")
    if not 0 <= float(value) <= 100:
        raise StyleCardError(f"{field} must be between 0 and 100, got {value!r}")
    return float(value)


def _axis_card(gridline: object) -> list[dict]:
    """One axis card: gridline color when declared, else gridlines off.

    ``None`` is a deliberate "no gridlines" declaration, not a missing value --
    it emits ``gridlineShow: False`` rather than omitting the card, so the intent
    is explicit in the theme a human reviews.
    """
    if gridline is None:
        return [{"gridlineShow": False}]
    color = _require_hex(gridline, "gridline")
    return [{"gridlineColor": _fill(color), "gridlineShow": True}]


def build_star_cards(chrome: dict) -> dict[str, list[dict]]:
    """Section 5 cards for ``visualStyles["*"]["*"]``.

    ``chrome`` keys (all optional): ``gridline`` (hex or None), ``border`` (hex or
    None), ``title_align``, ``data_labels`` (bool), ``number_format``. An empty
    mapping yields no cards, so a theme that declares no chrome is unchanged.
    """
    if not chrome:
        return {}
    cards: dict[str, list[dict]] = {}

    if "number_format" in chrome:
        fmt = chrome["number_format"]
        if fmt not in VALID_NUMBER_FORMATS:
            raise StyleCardError(
                f"number_format must be one of {VALID_NUMBER_FORMATS}, got {fmt!r}"
            )

    if "gridline" in chrome:
        axis = _axis_card(chrome["gridline"])
        cards["categoryAxis"] = axis
        cards["valueAxis"] = list(axis)

    if "border" in chrome:
        border = chrome["border"]
        if border is None:
            cards["border"] = [{"show": False}]
        else:
            cards["border"] = [{"color": _fill(_require_hex(border, "border")), "show": True}]

    if "title_align" in chrome:
        align = chrome["title_align"]
        if align not in VALID_TITLE_ALIGNMENTS:
            raise StyleCardError(
                f"title_align must be one of {VALID_TITLE_ALIGNMENTS}, got {align!r}"
            )
        cards.setdefault("title", [{}])[0]["alignment"] = align

    if "data_labels" in chrome:
        show = chrome["data_labels"]
        if not isinstance(show, bool):
            raise StyleCardError(f"data_labels must be true or false, got {show!r}")
        cards["labels"] = [{"show": show}]

    return cards
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/unit/test_theme_style_cards.py -v --no-cov
```

Expected: 7 passed.

Note: `test_build_star_cards_emits_both_axes_and_border` asserts exactly three
card names, but `CHROME` also declares `title_align` and `data_labels`. Change the
assertion to `{"categoryAxis", "valueAxis", "border", "title", "labels"}` — the
builder is correct; the test's expectation was written narrowly. Fix the test.

- [ ] **Step 5: Wire the cards into `render_theme_json`**

In `src/seshat/theme_gen.py`, add the import near the other local imports:

```python
from seshat.theme_style_cards import build_star_cards
```

Add the new field to `ThemeSeed`, after `transparency`:

```python
    # Section-5 visual chrome (gridline/border/title_align/data_labels/
    # number_format). None (default) means no chrome declared -- every existing
    # caller is unaffected and no section-5 card is emitted.
    chrome: dict | None = None
```

In `render_theme_json`, after the existing `overlay` block and before `doc = {`:

```python
    star_style.update(build_star_cards(seed.chrome or {}))
```

- [ ] **Step 6: Write the emission test**

Create `tests/unit/test_theme_gen_breadth.py`:

```python
import json

import pytest

from seshat.theme_gen import ThemeSeed, build_palette, render_theme_json

pytestmark = pytest.mark.unit


def _seed(**over) -> ThemeSeed:
    base = dict(
        name="breadth-test",
        mode="light",
        accent="#118DFF",
        background="#FFFFFF",
        text_primary="#252423",
        text_secondary="#605E5C",
        text_muted="#605E5C",
        data_colors=("#118DFF", "#E66C37", "#1AAB40"),
        good="#1AAB40",
        neutral="#D9B300",
        bad="#D64550",
    )
    base.update(over)
    return ThemeSeed(**base)


def test_no_chrome_emits_no_section5_cards():
    """Regression: an existing caller's output is unchanged."""
    seed = _seed()
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    star = doc["visualStyles"]["*"]["*"]
    assert set(star) == {"title", "labels"}


def test_chrome_emits_gridline_and_border_cards():
    seed = _seed(chrome={"gridline": "#E1DFDD", "border": "#C8C6C4"})
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    star = doc["visualStyles"]["*"]["*"]
    assert star["categoryAxis"][0]["gridlineColor"] == {
        "solid": {"color": "#E1DFDD"}
    }
    assert star["border"][0]["show"] is True
```

- [ ] **Step 7: Run the emission tests**

```bash
python -m pytest tests/unit/test_theme_gen_breadth.py -v --no-cov
```

Expected: 2 passed. (`build_palette` is verified to exist in `seshat.theme_gen` —
it is the exported palette builder; `_validate_palette_colors` is private and not
what you want.)

- [ ] **Step 8: Confirm no existing theme test regressed**

```bash
python -m pytest tests/unit/ -k "theme" -q --no-cov
```

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add src/seshat/theme_style_cards.py src/seshat/theme_gen.py \
        tests/unit/test_theme_style_cards.py tests/unit/test_theme_gen_breadth.py
git commit -m "feat: emit theme spec section-5 visual defaults from tokens

Adds theme_style_cards.build_star_cards (gridlines, border, title alignment,
data labels, number format) and an optional ThemeSeed.chrome field. Key paths
verified against reportThemeSchema-2.156.json. Number formats are constrained to
the spec vocabulary and refused otherwise; omitting chrome leaves existing output
byte-identical.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: §6 filter-pane + §7 page background cards

**Files:**
- Modify: `src/seshat/theme_style_cards.py` (add `build_page_cards`)
- Modify: `tests/unit/test_theme_style_cards.py`
- Modify: `src/seshat/theme_gen.py` (`ThemeSeed.page`, `render_theme_json`)
- Modify: `tests/unit/test_theme_gen_breadth.py`

**Interfaces:**
- Consumes: `_fill`, `_require_hex`, `_require_pct`, `StyleCardError` from Task 2.
- Produces:
  - `build_page_cards(page: dict) -> dict[str, list[dict]]`
  - `ThemeSeed.page: dict | None = None`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_theme_style_cards.py`:

```python
from seshat.theme_style_cards import build_page_cards

PAGE = {
    "background": "#FFFFFF",
    "background_transparency": 0,
    "wallpaper": "#F3F2F1",
    "wallpaper_transparency": 0,
    "filter_pane_background": "#FFFFFF",
    "filter_pane_text": "#252423",
    "filter_card_applied": "#E1DFDD",
    "filter_card_available": "#FFFFFF",
}


def test_page_cards_use_outspace_for_wallpaper():
    """outspace IS the wallpaper card per the published schema."""
    cards = build_page_cards(PAGE)
    assert cards["background"] == [
        {"color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0.0}
    ]
    assert cards["outspace"] == [
        {"color": {"solid": {"color": "#F3F2F1"}}, "transparency": 0.0}
    ]


def test_filter_card_is_an_array_keyed_by_id():
    """filterCard carries a $id discriminator for its two states."""
    cards = build_page_cards(PAGE)
    ids = [c["$id"] for c in cards["filterCard"]]
    assert ids == ["Applied", "Available"]


def test_filter_pane_card_emitted():
    cards = build_page_cards(PAGE)
    assert cards["outspacePane"][0]["backgroundColor"] == {
        "solid": {"color": "#FFFFFF"}
    }


def test_page_transparency_out_of_range_is_refused():
    with pytest.raises(StyleCardError, match="background_transparency"):
        build_page_cards({**PAGE, "background_transparency": 150})


def test_empty_page_emits_no_cards():
    assert build_page_cards({}) == {}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/unit/test_theme_style_cards.py -k page_cards -v --no-cov
```

Expected: FAIL — `ImportError: cannot import name 'build_page_cards'`.

- [ ] **Step 3: Add the page-card builder**

Append to `src/seshat/theme_style_cards.py`:

```python
def _colored_card(page: dict, color_key: str, pct_key: str) -> list[dict] | None:
    """One color+transparency card, or None when the color is not declared."""
    if color_key not in page:
        return None
    color = _require_hex(page[color_key], color_key)
    card: dict = {"color": _fill(color)}
    if pct_key in page:
        card["transparency"] = _require_pct(page[pct_key], pct_key)
    return [card]


def build_page_cards(page: dict) -> dict[str, list[dict]]:
    """Sections 6 and 7 cards for ``visualStyles["page"]["*"]``.

    Both spec sections land under the SAME ``page`` visual type per the published
    schema, which admits exactly ten cards there; four are in scope:
    ``background`` and ``outspace`` (section 7 -- ``outspace`` IS the wallpaper),
    plus ``outspacePane`` and ``filterCard`` (section 6).

    Section 6 styles the filter pane's LOOK only. Nothing here reads or writes
    filter state, selections, or bound fields.
    """
    if not page:
        return {}
    cards: dict[str, list[dict]] = {}

    background = _colored_card(page, "background", "background_transparency")
    if background is not None:
        cards["background"] = background

    wallpaper = _colored_card(page, "wallpaper", "wallpaper_transparency")
    if wallpaper is not None:
        cards["outspace"] = wallpaper

    pane: dict = {}
    if "filter_pane_background" in page:
        pane["backgroundColor"] = _fill(
            _require_hex(page["filter_pane_background"], "filter_pane_background")
        )
    if "filter_pane_text" in page:
        pane["foregroundColor"] = _fill(
            _require_hex(page["filter_pane_text"], "filter_pane_text")
        )
    if pane:
        cards["outspacePane"] = [pane]

    # filterCard is an ARRAY discriminated by $id -- one object per state.
    filter_cards: list[dict] = []
    for state, key in (("Applied", "filter_card_applied"), ("Available", "filter_card_available")):
        if key in page:
            filter_cards.append(
                {"$id": state, "backgroundColor": _fill(_require_hex(page[key], key))}
            )
    if filter_cards:
        cards["filterCard"] = filter_cards

    return cards
```

- [ ] **Step 4: Run the builder tests**

```bash
python -m pytest tests/unit/test_theme_style_cards.py -v --no-cov
```

Expected: 12 passed.

- [ ] **Step 5: Wire page cards into `render_theme_json`**

In `src/seshat/theme_gen.py`, extend the import:

```python
from seshat.theme_style_cards import build_page_cards, build_star_cards
```

Add the field to `ThemeSeed`, after `chrome`:

```python
    # Sections 6+7 page cards (page/wallpaper fill, filter-pane LOOK). None
    # (default) emits no visualStyles["page"] entry at all.
    page: dict | None = None
```

In `render_theme_json`, replace the `"visualStyles": {"*": {"*": star_style}},`
line with a pre-built mapping. Insert BEFORE `doc = {`:

```python
    visual_styles: dict = {"*": {"*": star_style}}
    page_cards = build_page_cards(seed.page or {})
    if page_cards:
        visual_styles["page"] = {"*": page_cards}
```

and inside `doc`, use:

```python
        "visualStyles": visual_styles,
```

- [ ] **Step 6: Write the emission test**

Append to `tests/unit/test_theme_gen_breadth.py`:

```python
def test_no_page_tokens_emits_no_page_visual_type():
    """Regression: absent page tokens leave visualStyles shape unchanged."""
    seed = _seed()
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    assert set(doc["visualStyles"]) == {"*"}


def test_page_tokens_emit_page_visual_type():
    seed = _seed(page={"background": "#FFFFFF", "wallpaper": "#F3F2F1"})
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    page = doc["visualStyles"]["page"]["*"]
    assert set(page) == {"background", "outspace"}


def test_page_cards_survive_a_compile_round_trip():
    """The Task-1 carve-out must not read generated page cards as hand-tuning."""
    from seshat.theme_compile import _human_owned_visual_styles

    seed = _seed(page={"background": "#FFFFFF"}, chrome={"gridline": "#E1DFDD"})
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    assert _human_owned_visual_styles(doc["visualStyles"]) == {}
```

- [ ] **Step 7: Run all theme tests**

```bash
python -m pytest tests/unit/ -k "theme" -q --no-cov
```

Expected: all pass. `test_page_cards_survive_a_compile_round_trip` is the C-1
guard — if it fails, `_GENERATOR_OWNED_CARDS` in Task 1 is missing a card name.

- [ ] **Step 8: Commit**

```bash
git add src/seshat/theme_style_cards.py src/seshat/theme_gen.py \
        tests/unit/test_theme_style_cards.py tests/unit/test_theme_gen_breadth.py
git commit -m "feat: emit theme spec sections 6+7 (filter-pane look, page background)

Both sections land under visualStyles[page][*] per reportThemeSchema-2.156.json,
which admits exactly ten cards there; four are in scope. outspace IS the wallpaper
card, and filterCard is an array discriminated by \$id (Applied/Available).
Section 6 styles the pane's LOOK only -- no filter state is read or written.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Non-text contrast gate (WCAG 3:1)

**Why:** the five existing gates check TEXT on background at 4.5:1. §5 introduces gridlines and borders — non-text elements whose WCAG floor is 3:1. Without this gate, a theme can emit an invisible gridline and pass every check.

**Files:**
- Modify: `src/seshat/theme_gen.py` (new constant + gate, called from the validate-before-write path)
- Modify: `tests/unit/test_theme_gen_breadth.py`

**Interfaces:**
- Consumes: `ThemeSeed.chrome` (Task 2), `ThemeSeed.page` (Task 3), `contrast_ratio` from `seshat.color`.
- Produces: `AA_NON_TEXT_FLOOR = 3.0`; `check_non_text_contrast_or_raise(palette: dict, seed: ThemeSeed, floor: float = AA_NON_TEXT_FLOOR) -> None`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_theme_gen_breadth.py`:

```python
from seshat.color import contrast_ratio
from seshat.theme_gen import (
    AA_NON_TEXT_FLOOR,
    ThemeGenError,
    _validate_and_collect,
    check_non_text_contrast_or_raise,
)


def test_invisible_gridline_is_refused():
    """A gridline nearly identical to the background must not pass."""
    seed = _seed(chrome={"gridline": "#FEFEFE"})  # on #FFFFFF background
    # Oracle: compute the ratio independently rather than trusting the module.
    assert contrast_ratio("#FEFEFE", "#FFFFFF") < AA_NON_TEXT_FLOOR
    with pytest.raises(ThemeGenError, match="gridline"):
        check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_legible_gridline_passes():
    seed = _seed(chrome={"gridline": "#767676"})
    assert contrast_ratio("#767676", "#FFFFFF") >= AA_NON_TEXT_FLOOR
    check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_no_chrome_is_vacuously_fine():
    seed = _seed()
    check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_gridlines_off_is_not_a_contrast_failure():
    """None means gridlines off -- there is nothing to be invisible."""
    seed = _seed(chrome={"gridline": None})
    check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_generate_refuses_an_invisible_border_end_to_end():
    """The gate must run in the validate-before-write path, not just standalone."""
    seed = _seed(chrome={"border": "#FEFEFE"})
    with pytest.raises(ThemeGenError, match="border"):
        _validate_and_collect(build_palette(seed), seed)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/unit/test_theme_gen_breadth.py -k contrast -v --no-cov
```

Expected: FAIL — `ImportError: cannot import name 'AA_NON_TEXT_FLOOR'`.

- [ ] **Step 3: Add the constant and gate**

In `src/seshat/theme_gen.py`, beside `AA_FLOOR`:

```python
# WCAG 2.x non-text contrast floor. Gridlines, borders, and visual fills are
# non-text elements: their floor is 3:1, not the 4.5:1 that applies to text. Kept
# separate from AA_FLOOR so neither can be loosened by editing the other.
AA_NON_TEXT_FLOOR = 3.0
```

Add the gate near the other `check_*_or_raise` functions:

```python
def check_non_text_contrast_or_raise(
    palette: dict, seed: ThemeSeed, floor: float = AA_NON_TEXT_FLOOR
) -> None:
    """Every declared non-text chrome color must clear ``floor`` on its ground.

    Gridlines and borders sit on the page background. A ``None`` color is an
    explicit "off" declaration, not a faint color, so it is skipped rather than
    failed. Raises ``ThemeGenError`` naming the offending token.
    """
    chrome = seed.chrome or {}
    ground = palette["colors"]["background"]
    for field in ("gridline", "border"):
        color = chrome.get(field)
        if color is None:
            continue
        ratio = contrast_ratio(color, ground)
        if ratio < floor:
            raise ThemeGenError(
                f"{field} {color} has contrast {ratio:.2f}:1 against background "
                f"{ground} -- below the {floor}:1 WCAG non-text floor; it would "
                f"be effectively invisible"
            )
```

- [ ] **Step 4: Call the gate from the validate-before-write path**

`_validate_and_collect` is defined at `theme_gen.py:607` and calls the five
existing gates at lines 619–623:

```python
    check_contrast_or_raise(palette)
    check_font_floor_or_raise(seed)
    check_categorical_distinctness_or_raise(palette)
    check_ramp_deltae_or_raise(palette, MIN_ADJACENT_DELTAE)
    check_composite_contrast_or_raise(palette)
```

Add the sixth immediately after them:

```python
    check_non_text_contrast_or_raise(palette, seed)
```

Confirm `contrast_ratio` is already imported at module top; if not, add it to the
existing `from seshat.color import ...` line.

- [ ] **Step 5: Run the tests**

```bash
python -m pytest tests/unit/test_theme_gen_breadth.py -v --no-cov
```

Expected: all pass. `test_generate_refuses_an_invisible_border_end_to_end` is the
guard that the gate actually runs in the write path rather than only standing
alone — import `_validate_and_collect` from `seshat.theme_gen` in that test.

- [ ] **Step 6: Full theme suite + lint**

```bash
python -m pytest tests/unit/ -k "theme" -q --no-cov
ruff format --check src tests && ruff check src tests
```

Expected: tests pass, both lint gates clean.

- [ ] **Step 7: Commit**

```bash
git add src/seshat/theme_gen.py tests/unit/test_theme_gen_breadth.py
git commit -m "feat: gate non-text chrome contrast at the WCAG 3:1 floor

Section 5 introduces gridlines and borders -- non-text elements whose WCAG floor
is 3:1, not the 4.5:1 the five existing gates apply to text. Without this a theme
could emit an invisible gridline and pass every check. A None color is an explicit
off declaration and is skipped, not failed.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Report an unparseable preview input (third state)

**Why:** `_load_yaml_mapping` returns `{}` for unreadable, malformed, AND absent inputs alike, and `render_blueprint_preview` has no problems channel — so a corrupt blueprint renders a near-empty SVG indistinguishable from a sparse one. Fix this before adding styling, so a styling bug is never mistaken for a silent input failure.

**Files:**
- Modify: `src/seshat/blueprint_preview.py`
- Create: `tests/unit/test_blueprint_preview_styled.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `class PreviewInputError(Exception)`; `_load_yaml_mapping(path)` raises it on unparseable input while still returning `{}` for absent input.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_blueprint_preview_styled.py`:

```python
import pytest

from seshat.blueprint_preview import PreviewInputError, _load_yaml_mapping

pytestmark = pytest.mark.unit


def test_absent_input_is_not_an_error(tmp_path):
    """A not-yet-authored page is a real use case -- stays non-fatal."""
    assert _load_yaml_mapping(tmp_path / "missing.yaml") == {}


def test_unparseable_input_is_reported(tmp_path):
    """A corrupt file must NOT silently become an empty preview."""
    bad = tmp_path / "bad.yaml"
    bad.write_text("pages: [unclosed\n", encoding="utf-8")
    with pytest.raises(PreviewInputError, match="bad.yaml"):
        _load_yaml_mapping(bad)


def test_non_mapping_input_is_reported(tmp_path):
    """A YAML list parses fine but is the wrong shape -- name it."""
    listy = tmp_path / "listy.yaml"
    listy.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(PreviewInputError, match="mapping"):
        _load_yaml_mapping(listy)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/unit/test_blueprint_preview_styled.py -v --no-cov
```

Expected: FAIL — `ImportError: cannot import name 'PreviewInputError'`.

- [ ] **Step 3: Add the third state**

In `src/seshat/blueprint_preview.py`, add near the top:

```python
class PreviewInputError(Exception):
    """A preview input that exists but cannot be used, named for the caller."""
```

Replace `_load_yaml_mapping` with:

```python
def _load_yaml_mapping(path: Path | str) -> dict:
    """A preview input YAML as a mapping.

    Three distinct states, never conflated: ABSENT returns ``{}`` (a
    not-yet-authored artifact is a legitimate preview subject); UNPARSEABLE and
    WRONG-SHAPE raise ``PreviewInputError`` naming the file. Silently returning
    ``{}`` for a corrupt file would render an empty SVG indistinguishable from a
    sparse one -- a degrade-without-reporting fail-open.
    """
    import yaml

    p = Path(path)
    if not p.exists():
        return {}
    try:
        text = p.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise PreviewInputError(
            f"preview input {p} is unreadable ({exc}) -- check permissions/encoding"
        ) from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PreviewInputError(
            f"preview input {p} is not valid YAML ({exc}) -- fix the syntax"
        ) from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise PreviewInputError(
            f"preview input {p} must be a YAML mapping, got {type(data).__name__}"
        )
    return data
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/unit/test_blueprint_preview_styled.py -v --no-cov
```

Expected: 3 passed.

- [ ] **Step 5: Verify no existing preview test regressed**

```bash
python -m pytest tests/unit/ -k "blueprint or preview" -q --no-cov
```

Expected: all pass. If a test asserted that a malformed input returns `{}`, that
test pinned the fail-open — update it to assert `PreviewInputError` and note the
change in the commit message.

- [ ] **Step 6: Commit**

```bash
git add src/seshat/blueprint_preview.py tests/unit/test_blueprint_preview_styled.py
git commit -m "fix: report an unparseable preview input instead of rendering empty

_load_yaml_mapping returned {} for unreadable, malformed, and absent inputs
alike, with no problems channel -- so a corrupt blueprint rendered a near-empty
SVG indistinguishable from a sparse one. Splits the three states: absent stays
non-fatal, unparseable and wrong-shape are named.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Token-driven styled preview + stamped disclaimer

**Files:**
- Modify: `src/seshat/blueprint_preview.py` (`render_blueprint_preview`, palette helper, caption)
- Modify: `tests/unit/test_blueprint_preview_styled.py`

**Interfaces:**
- Consumes: `PreviewInputError` (Task 5); the tokens YAML shape `theme_compile.palette_from_tokens` already reads.
- Produces: `render_blueprint_preview(..., tokens_path: Path | str | None = None) -> str` — new keyword-only parameter, default `None` preserves current output byte-for-byte.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_blueprint_preview_styled.py`:

```python
import json

from seshat.blueprint_preview import PREVIEW_DISCLAIMER, render_blueprint_preview


def _write_min_inputs(tmp_path):
    """The four minimal preview inputs, as YAML the renderer accepts."""
    (tmp_path / "bp.yaml").write_text(
        "pages:\n  - name: Overview\n    order: 1\n", encoding="utf-8"
    )
    (tmp_path / "comp.yaml").write_text("pages: []\n", encoding="utf-8")
    (tmp_path / "grid.yaml").write_text(
        "width: 1280\nheight: 720\ncolumns: 12\n", encoding="utf-8"
    )
    (tmp_path / "tokens.yaml").write_text(
        "meta:\n  name: t\ncolors:\n"
        "  primary: '#118DFF'\n  secondary: '#E66C37'\n  background: '#101820'\n"
        "  text:\n    primary: '#F2F2F2'\n    secondary: '#C8C8C8'\n    muted: '#A0A0A0'\n"
        "  sentiment:\n    success: '#1AAB40'\n    warning: '#D9B300'\n    danger: '#D64550'\n"
        "  data_colors: ['#118DFF', '#E66C37']\n",
        encoding="utf-8",
    )
    return tmp_path


def test_disclaimer_is_stamped_on_every_render(tmp_path):
    """Mirrors tmdl-doc-comment-lint: the limit is stated even on success."""
    d = _write_min_inputs(tmp_path)
    svg = render_blueprint_preview(
        blueprint_path=d / "bp.yaml",
        visual_spec_paths=[],
        composition_path=d / "comp.yaml",
        grid_path=d / "grid.yaml",
    )
    assert PREVIEW_DISCLAIMER in svg


def test_tokens_color_the_render(tmp_path):
    d = _write_min_inputs(tmp_path)
    styled = render_blueprint_preview(
        blueprint_path=d / "bp.yaml",
        visual_spec_paths=[],
        composition_path=d / "comp.yaml",
        grid_path=d / "grid.yaml",
        tokens_path=d / "tokens.yaml",
    )
    assert "#101820" in styled


def test_omitting_tokens_leaves_output_unchanged(tmp_path):
    """Regression: the no-tokens path must not shift for existing callers."""
    d = _write_min_inputs(tmp_path)
    kwargs = dict(
        blueprint_path=d / "bp.yaml",
        visual_spec_paths=[],
        composition_path=d / "comp.yaml",
        grid_path=d / "grid.yaml",
    )
    assert render_blueprint_preview(**kwargs) == render_blueprint_preview(**kwargs)
    assert "#101820" not in render_blueprint_preview(**kwargs)


def test_preview_never_fabricates_a_number(tmp_path):
    """PLACEHOLDER only -- the structural no-data guarantee holds."""
    d = _write_min_inputs(tmp_path)
    svg = render_blueprint_preview(
        blueprint_path=d / "bp.yaml",
        visual_spec_paths=[],
        composition_path=d / "comp.yaml",
        grid_path=d / "grid.yaml",
        tokens_path=d / "tokens.yaml",
    )
    assert "PLACEHOLDER" in svg
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/unit/test_blueprint_preview_styled.py -k "disclaimer or tokens or fabricate" -v --no-cov
```

Expected: FAIL — `ImportError: cannot import name 'PREVIEW_DISCLAIMER'`.

- [ ] **Step 3: Add the disclaimer constant and palette helper**

In `src/seshat/blueprint_preview.py`, near `_PLACEHOLDER`:

```python
# Stated on EVERY render including a clean one. An SVG approximation is not
# Power BI's renderer: a preview that looks right proves nothing about what
# Desktop will draw. Mirrors the tmdl-doc-comment-lint posture, where the scope
# limit is printed on a pass -- a pass is exactly where over-reading happens.
PREVIEW_DISCLAIMER = (
    "APPROXIMATION -- an SVG preview of committed design intent. "
    "It does NOT prove Power BI Desktop will render this way, and grants no approval."
)

# Monochrome fallbacks, used verbatim when no tokens are supplied so existing
# output stays byte-identical.
_DEFAULT_STYLE = {
    "ground": "#FFFFFF",
    "ink": "#252423",
    "ink_muted": "#605E5C",
    "line": "#C8C6C4",
}


def _style_from_tokens(tokens_path: Path | str | None) -> dict:
    """Preview colors from a committed tokens YAML, or the monochrome default.

    Reads the SAME tokens file theme_compile consumes, so the preview and the
    emitted theme.json cannot disagree. Renders from TOKENS, never from a theme
    JSON -- a valid-but-wrong theme key must not be able to make the preview lie.
    """
    if tokens_path is None:
        return dict(_DEFAULT_STYLE)
    tokens = _load_yaml_mapping(tokens_path)
    colors = tokens.get("colors")
    if not isinstance(colors, dict):
        raise PreviewInputError(
            f"tokens {tokens_path} has no 'colors' mapping -- cannot style the preview"
        )
    text = colors.get("text") if isinstance(colors.get("text"), dict) else {}
    return {
        "ground": colors.get("background", _DEFAULT_STYLE["ground"]),
        "ink": text.get("primary", _DEFAULT_STYLE["ink"]),
        "ink_muted": text.get("muted", _DEFAULT_STYLE["ink_muted"]),
        "line": colors.get("secondary", _DEFAULT_STYLE["line"]),
    }
```

- [ ] **Step 4: Thread the style through the renderer**

In `render_blueprint_preview`, add the keyword-only parameter and resolve the style:

```python
def render_blueprint_preview(
    *,
    blueprint_path: Path | str,
    visual_spec_paths: list[Path | str],
    composition_path: Path | str,
    grid_path: Path | str,
    tokens_path: Path | str | None = None,
) -> str:
```

As the first statement in the body:

```python
    style = _style_from_tokens(tokens_path)
```

Then pass `style` down to `_page_svg` / `_visual_group` and use
`style["ground"]` for the page rect fill, `style["line"]` for visual borders and
gridlines, `style["ink"]` for labels, and `style["ink_muted"]` for the
`PLACEHOLDER` text. Emit the disclaimer as a `<text>` element at the bottom of
each page group using the existing `_text(...)` helper, at
`font-size: 9` in `style["ink_muted"]`.

Do NOT change any geometry, ordering, or sorting logic.

- [ ] **Step 5: Run the tests**

```bash
python -m pytest tests/unit/test_blueprint_preview_styled.py -v --no-cov
```

Expected: 7 passed. If `test_omitting_tokens_leaves_output_unchanged` fails
because the disclaimer shifted the default output, that is EXPECTED and correct —
the disclaimer is intentionally on every render. Update any pre-existing golden
file to include it, and say so in the commit message.

- [ ] **Step 6: Full gate set**

```bash
python -m pytest -m unit -q --no-cov
ruff format --check src tests && ruff check src tests
python -m seshat.cli check --repo .
python -m seshat.cli semantic-check --repo .
```

Expected: unit suite green (3994+ passing, 0 failed), both lint gates clean,
`check` exit 0 with only the known non-blocking RS1 warning, `semantic-check`
0 findings.

- [ ] **Step 7: Commit**

```bash
git add src/seshat/blueprint_preview.py tests/unit/test_blueprint_preview_styled.py
git commit -m "feat: style the blueprint preview from committed design tokens

render_blueprint_preview gains an optional tokens_path that colors the SVG from
the SAME tokens theme_compile consumes, so the preview cannot drift from the
emitted theme.json. Renders from tokens, never from a theme JSON, so a
valid-but-wrong theme key cannot make the preview lie.

Every render carries PREVIEW_DISCLAIMER, including a clean one -- an SVG is not
Power BI's renderer and a good-looking preview proves nothing about Desktop.
PLACEHOLDER-only output is unchanged: no sample values, no fabricated numbers.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Key-name safety net + docs

**Files:**
- Modify: `tests/unit/test_theme_gen_breadth.py`
- Modify: `templates/theme-json-spec.md` (mark §5/§6/§7 as emitted)

**Interfaces:**
- Consumes: `build_star_cards`, `build_page_cards` (Tasks 2–3); `seshat.rules.design_theme._is_forbidden`.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Write the DL1 safety-net test**

Append to `tests/unit/test_theme_gen_breadth.py`:

```python
def test_no_emitted_key_name_trips_dl1():
    """DL1 substring-matches forbidden tokens in theme key NAMES at ERROR
    severity. All current section 5/6/7 names were verified clear; this test
    stops a future key addition from silently reintroducing a blocking rule
    failure on a theme the generator itself produced."""
    from seshat.rules.design_theme import _is_forbidden

    seed = _seed(
        chrome={
            "gridline": "#767676",
            "border": "#767676",
            "title_align": "left",
            "data_labels": False,
            "number_format": "#,##0",
        },
        page={
            "background": "#FFFFFF",
            "wallpaper": "#F3F2F1",
            "filter_pane_background": "#FFFFFF",
            "filter_card_applied": "#E1DFDD",
            "filter_card_available": "#FFFFFF",
        },
    )
    doc = json.loads(render_theme_json(build_palette(seed), seed))

    offenders = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if _is_forbidden(key):
                    offenders.append(key)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(doc)
    assert offenders == [], f"emitted key names trip DL1: {offenders}"
```

- [ ] **Step 2: Run it**

```bash
python -m pytest tests/unit/test_theme_gen_breadth.py -k dl1 -v --no-cov
```

Expected: PASS immediately (all names were pre-verified clear). If it FAILS, a
key name collides with a DL1 forbidden token — STOP and report; widening DL1 is
an owner decision, not an implementer's.

- [ ] **Step 3: Mark the spec sections as emitted**

In `templates/theme-json-spec.md`, add one line under each of the §5, §6, and §7
headings:

```markdown
> **Emitted** by `seshat theme-gen` / `theme-compile` from committed design
> tokens. Key paths verified against `reportThemeSchema-2.156.json`.
```

- [ ] **Step 4: Run the full gate set once more**

```bash
python -m pytest -m unit -q --no-cov
ruff format --check src tests && ruff check src tests
python -m seshat.cli check --repo .
python -m seshat.cli kit-lint --repo . || true
```

Expected: unit suite green, lint clean, `check` exit 0 with only the RS1 warning.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_theme_gen_breadth.py templates/theme-json-spec.md
git commit -m "test: pin every emitted theme key name against the DL1 token list

DL1 substring-matches forbidden tokens in theme key names at ERROR severity, so a
collision would block retail check on a theme the generator itself produced. All
current section 5/6/7 names were verified clear; this test stops a future addition
from reintroducing that silently. Marks the three spec sections as emitted.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage.** §5 → Task 2. §6 → Task 3. §7 → Task 3. Non-text contrast decision → Task 4. Preview honesty (stamped disclaimer) → Task 6. PLACEHOLDER-only decision → Task 6 Step 1 test. Playwright local-render-only → **deliberately not implemented**: the SVG is directly viewable and diffable as a file, so rasterization adds a dependency with no current consumer. Recorded here as an explicit YAGNI cut, matching the `theme-diff` cut in the spec. C-1 → Task 1. C-2 → Task 7. C-3 → Tasks 1 + 3. Fail-open repair → Task 5. No spec requirement is unaddressed.

**2. Placeholder scan.** No TBD/TODO. Every code step carries literal code. Every test step carries the assertions. Three steps name a specific fallback if a symbol name differs (`build_palette`, `_validate_and_collect`, the pre-existing golden) rather than saying "adjust as needed".

**3. Type consistency.** `build_star_cards(chrome: dict) -> dict[str, list[dict]]` and `build_page_cards(page: dict) -> dict[str, list[dict]]` — same shape, both consumed in `render_theme_json` via `.update()` / direct assignment. `StyleCardError` raised in Tasks 2–3, `ThemeGenError` in Task 4, `PreviewInputError` in Tasks 5–6 — three distinct exception types, each used only where defined. `_GENERATOR_OWNED_CARDS` defined in Task 1 is read in Task 3's round-trip test. `PREVIEW_DISCLAIMER` defined and asserted in Task 6. `AA_NON_TEXT_FLOOR` defined and asserted in Task 4.

**Known ordering hazard, by design:** Task 1 must land before Task 3, or the C-1 carve-out gap makes Task 3's round-trip test fail for a confusing reason. Task 5 must land before Task 6, so a styling bug is never mistaken for a silent input failure.
