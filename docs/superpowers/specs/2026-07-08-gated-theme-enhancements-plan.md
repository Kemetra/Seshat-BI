# Provably-Accessible Gated Theme Layer -- Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Harden the DEFINE-only `theme_gen` pipeline into a provably-accessible gated theme layer that either PROVES a narrow computable accessibility fact (contrast, color separation, font floor) and fails closed, or FLAGS a declared-correspondence drift, while leaving every human-judgment seam explicitly OPEN.

**Architecture:** A shared stdlib-only `color.py` grows CIE76 deltaE, alpha-composite, and pt-formatting primitives that both the generator self-checks and the static rules consume, so the pre-write guard applies the exact arithmetic the governance gate later re-applies. `theme_gen.py` gains fail-closed self-checks (ramp deltaE, categorical distinctness, font floor, composite contrast) plus a light/dark pair generator; `theme_compile.py` mirrors the font-floor gate on the compile leg. Three new registry rules (CT2, CT3, DL8) govern committed artifacts, each silent-on-main until a token file opts in.

**Tech Stack:** Python 3.13, stdlib-only color math (colorsys/math), pytest (-m unit), ruff, the retail-check rule registry.

## Global Constraints

- DEFINE-only: pure stdlib arithmetic on the palette; no render, no network, no live Power BI, never write `visual.json`/PBIR.
- Non-pass-granting (Principle V / rule #9): may ADD a proven check or FLAG a failure; never self-grant readiness `pass`; no `score:` / `confidence:` field anywhere; human seams stay `[ ]` in every `spec_md`.
- ASCII-only in ALL generated strings and identifiers: use `deltaE76` / `dE76`, NEVER the Greek glyph (charmap codec risk on Windows write).
- Type hints on every function signature.
- Functions under 50 lines.
- `ThemeSeed` stays a `@dataclass(frozen=True)`; new fields carry defaults so existing call sites keep working.
- TDD: write the failing test FIRST, confirm the expected failure, then the minimal implementation.
- Before every commit: `ruff format --check` + `ruff check` + `pytest -m unit` on the touched paths.
- New rules MUST be `<no-finding>` on `main` at merge (a missing declared key is a silent skip, never an ERROR).
- Rule IDs (verified free against `EXPECTED_RULE_IDS`): `CT2` (idea 1), `CT3` (idea 3), `DL8` (idea 6).
- Three OWNER STOPS halt the build: the idea-1 deltaE floor value, the idea-2 transparency-role schema, and the idea-6 sentiment-map ruling.

## File Structure

**Source (modified):**
- `src/seshat/color.py` -- shared stdlib color math; gains `hex_to_lab`, `delta_e76`, `_lab_f`, `composite_over`, `format_pt`.
- `src/seshat/theme_gen.py` -- generator; gains font fields + floor constants on `ThemeSeed`, `check_font_floor_or_raise`, `check_categorical_distinctness_or_raise` + `min_categorical_delta_e`, `check_ramp_deltae_or_raise` + `MIN_ADJACENT_DELTAE`, `check_composite_contrast_or_raise`, `_targets_for`/`_validate_and_collect`/`_write_targets` split, `derive_dark_seed` + `_invert_lightness`, `generate_pair`; renders seed fonts + typography block.
- `src/seshat/theme_compile.py` -- compile leg; `seed_from_tokens` reads typography per-key, `compile_theme` calls the font-floor gate.
- `src/seshat/cli/parser.py` -- theme-gen subparser; gains `--pair`, `--title-font-pt`, `--label-font-pt`.
- `src/seshat/severity_posture.py` -- posture fixtures for CT2, CT3, DL8.
- `src/seshat/rules/__init__.py` -- import tuple + `__all__` gain `design_categorical_distinctness` and `design_ramp_deltae` (DL8 skips: `design_theme_fidelity` already imported).

**Source (created):**
- `src/seshat/rules/design_ramp_deltae.py` -- rule **CT2**: adjacent `data_colors` deltaE76 near-collapse guard.
- `src/seshat/rules/design_categorical_distinctness.py` -- rule **CT3**: whole-set `data_colors` deltaE76 distinctness guard.
- `src/seshat/rules/design_theme_fidelity.py` -- gains a second `@register` fn for **DL8** (sentiment 4->3 fidelity); existing `RULE_ID = "DL3"` untouched.

**Tests (modified/created):**
- `tests/unit/test_color.py` -- deltaE76, composite_over, format_pt cases.
- `tests/unit/test_theme_gen.py` -- font floor, categorical, ramp deltaE, composite, derive_dark_seed, generate_pair cases.
- `tests/unit/test_theme_compile.py` -- typography per-key fallback + font-floor compile gate + round-trip.
- `tests/unit/test_cli_parser.py` -- font-pt flag parsing.
- `tests/unit/test_rules_wiring.py` -- `EXPECTED_RULE_IDS` gains CT2, CT3, DL8.
- `tests/unit/test_design_ramp_deltae.py` (created) -- CT2 rule tests.
- `tests/unit/test_design_categorical_distinctness.py` (created) -- CT3 rule tests.
- `tests/unit/test_design_theme_fidelity.py` -- DL8 rule tests.
- `tests/fixtures/theme_fidelity/sentiment_map_*/` (created) -- DL8 fixtures.

**Docs (regenerated, never hand-edited content):**
- `docs/rules/rules-manifest.json` -- via `retail manifest`.
- `docs/rules/severity-posture.json` -- via `retail severity-posture`.

**Docs (hand-edited):**
- `docs/glossary.md` -- CT and DL family rows + rule-count line.
- `docs/quality/rule-count-claims.yaml` -- `anchor` + `claimed-count`, computed not hardcoded.

## Build Order & Dependencies

The build is mostly serial because ideas 1/3/4/5 all edit the same `generate()` call site (line ~253) and the same `ThemeSeed` dataclass. Phase 0 (Tasks 1-3) lays the shared `color.py` primitives that ideas 1/2/3/4 all consume and MUST land first. Phase 1 (Tasks 4-9, idea 5 refactor then idea 4 font floor) restructures `generate()` into validate/collect/write phases so every later self-check slots into one choke point, then wires the font floor through both `theme_gen` and `theme_compile`. Phase 2 (Tasks 10-16, ideas 3 and 1) adds the categorical and ramp-deltaE self-checks and their CT3/CT2 governance rules. Phase 3 (Tasks 17-19, ideas 5-pair, 2, 6) adds `generate_pair` + `--pair`, the standalone-unwired composite proof, and the DL8 sentiment rule. Static-rule tasks (CT2, CT3, DL8) are parallelizable relative to each other once their generator counterparts exist, but each shares the rule-count docs surface, so land them one at a time and recompute the manifest length each time rather than hardcoding it. **Three OWNER STOPS halt the build:** (1) the idea-1 deltaE floor value (Task 14), before any code hardcodes `MIN_ADJACENT_DELTAE`; (2) the idea-2 transparency-role schema (Task 18), before the composite check is ever wired; (3) the idea-6 sentiment-map ruling (Task 19), before any tokens file's `meta.sentiment_map` is authored.

---

### Task 1: color.py -- add `hex_to_lab` + `delta_e76` (CIE76 shared deltaE primitive)

**Files:**
- Modify: `src/seshat/color.py` -- add two module-level functions directly below `contrast_ratio` (after line 46).
- Modify: `tests/unit/test_color.py` -- extend the `from retail.color import ...` line (line 7) and append new test functions.

**Interfaces:**
- Consumes: `retail.color.channel_luminance(c: int) -> float` (existing, reused for the sRGB->linear step -- do not reimplement the EOTF).
- Produces:
  - `hex_to_lab(hex_color: str) -> tuple[float, float, float]` -- CIE L\*a\*b\* (D65) of a `#RRGGBB` color. Raises `ValueError` on a malformed hex (same guard as `relative_luminance`).
  - `delta_e76(a: str, b: str) -> float` -- Euclidean distance between two colors' Lab values (CIE76). Raises `ValueError` if either hex is malformed (propagates from `hex_to_lab`).
  - Private helper `_lab_f(t: float) -> float` -- Lab nonlinearity, keeps `hex_to_lab` under 50 lines.

Steps:

- [ ] 1. Write the failing tests first in `tests/unit/test_color.py`:

```python
from retail.color import (
    contrast_ratio,
    delta_e76,
    hex_to_lab,
    is_valid_hex,
    relative_luminance,
)
```

```python
def test_hex_to_lab_black_is_origin() -> None:
    L, a, b = hex_to_lab("#000000")
    assert (round(L, 1), round(a, 1), round(b, 1)) == (0.0, 0.0, 0.0)


def test_hex_to_lab_white_is_l100() -> None:
    L, _a, _b = hex_to_lab("#FFFFFF")
    assert round(L, 1) == 100.0


def test_hex_to_lab_bad_hex_raises() -> None:
    with pytest.raises(ValueError):
        hex_to_lab("nothex")


def test_delta_e76_black_white_is_about_100() -> None:
    assert round(delta_e76("#000000", "#FFFFFF"), 1) == 100.0


def test_delta_e76_identical_colors_is_zero() -> None:
    assert delta_e76("#2E7D5B", "#2E7D5B") == 0.0


def test_delta_e76_bad_hex_raises() -> None:
    with pytest.raises(ValueError):
        delta_e76("nothex", "#FFFFFF")
```

- [ ] 2. Run the new tests and confirm they fail on import (functions do not exist yet):

```
pytest tests/unit/test_color.py::test_hex_to_lab_black_is_origin -v
```

Expected FAIL reason: `ImportError: cannot import name 'hex_to_lab' from 'retail.color'` (collection error -- the whole module fails to import since `delta_e76`/`hex_to_lab` are missing from the import line).

- [ ] 3. Minimal implementation -- add to `src/seshat/color.py` directly after `contrast_ratio` (after line 46):

```python
def _lab_f(t: float) -> float:
    """CIE Lab nonlinearity: cube root above the linear-segment threshold."""
    epsilon = (6.0 / 29.0) ** 3
    kappa = (1.0 / 3.0) * (29.0 / 6.0) ** 2
    return t ** (1.0 / 3.0) if t > epsilon else kappa * t + 4.0 / 29.0


def hex_to_lab(hex_color: str) -> tuple[float, float, float]:
    """CIE L*a*b* (D65 white point) of an ``#RRGGBB`` color.

    Reuses ``channel_luminance`` for the sRGB->linear step, then applies the
    standard linRGB->XYZ (D65) matrix before the Lab nonlinearity. The XYZ Y
    row (0.2126, 0.7152, 0.0722) matches ``relative_luminance``'s WCAG
    coefficients -- same underlying linear-light Y, different downstream use.
    """
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"not a 6-digit hex color: {hex_color!r}")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    rl, gl, bl = channel_luminance(r), channel_luminance(g), channel_luminance(b)

    x = 0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl
    y = 0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl
    z = 0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl

    x_n, y_n, z_n = 0.95047, 1.0, 1.08883
    fx, fy, fz = _lab_f(x / x_n), _lab_f(y / y_n), _lab_f(z / z_n)

    lightness = 116.0 * fy - 16.0
    a_axis = 500.0 * (fx - fy)
    b_axis = 200.0 * (fy - fz)
    return (lightness, a_axis, b_axis)


def delta_e76(a: str, b: str) -> float:
    """CIE76 color difference: Euclidean distance between two Lab colors."""
    l1, a1, b1 = hex_to_lab(a)
    l2, a2, b2 = hex_to_lab(b)
    return ((l1 - l2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2) ** 0.5
```

- [ ] 4. Run tests -- confirm PASS:

```
pytest tests/unit/test_color.py -v
```

Expected: all tests in the file PASS, including the 6 new ones (`test_hex_to_lab_black_is_origin`, `test_hex_to_lab_white_is_l100`, `test_hex_to_lab_bad_hex_raises`, `test_delta_e76_black_white_is_about_100`, `test_delta_e76_identical_colors_is_zero`, `test_delta_e76_bad_hex_raises`) plus the pre-existing ones.

- [ ] 5. Format, lint, commit:

```
ruff format src/seshat/color.py tests/unit/test_color.py
ruff check src/seshat/color.py tests/unit/test_color.py
git add src/seshat/color.py tests/unit/test_color.py
git commit -m "feat: color.py -- add hex_to_lab + delta_e76 (CIE76) shared primitive"
```

---

### Task 2: color.py -- add `composite_over` (alpha-compositing primitive)

**Files:**
- Modify: `src/seshat/color.py` -- add one function directly below `delta_e76` (added in the prior task).
- Modify: `tests/unit/test_color.py` -- extend the import line and append new test functions.

**Interfaces:**
- Consumes: `retail.color.is_valid_hex(s: str) -> bool` (existing, reused for both hex guards).
- Produces: `composite_over(fg: str, bg: str, transparency_pct: float) -> str` -- returns the `#RRGGBB` result of compositing `fg` over `bg` at the given transparency. `transparency_pct=0` means fully opaque `fg` (returns `fg`'s color); `transparency_pct=100` means fully transparent `fg` (returns `bg`'s color). Raises `ValueError` if `transparency_pct` is outside `[0, 100]` or either hex is malformed.

Steps:

- [ ] 1. Write the failing tests first, append to `tests/unit/test_color.py`:

```python
def test_composite_over_50pct_black_over_white_is_gray() -> None:
    assert composite_over("#000000", "#FFFFFF", 50.0) == "#808080"


def test_composite_over_0pct_returns_fg() -> None:
    assert composite_over("#000000", "#FFFFFF", 0.0) == "#000000"


def test_composite_over_100pct_returns_bg() -> None:
    assert composite_over("#000000", "#FFFFFF", 100.0) == "#FFFFFF"


def test_composite_over_below_zero_raises() -> None:
    with pytest.raises(ValueError):
        composite_over("#000000", "#FFFFFF", -1.0)


def test_composite_over_above_100_raises() -> None:
    with pytest.raises(ValueError):
        composite_over("#000000", "#FFFFFF", 101.0)


def test_composite_over_bad_hex_raises() -> None:
    with pytest.raises(ValueError):
        composite_over("nothex", "#FFFFFF", 50.0)
```

Also update the import line to include `composite_over`:

```python
from retail.color import (
    composite_over,
    contrast_ratio,
    delta_e76,
    hex_to_lab,
    is_valid_hex,
    relative_luminance,
)
```

- [ ] 2. Run the new tests and confirm they fail:

```
pytest tests/unit/test_color.py::test_composite_over_50pct_black_over_white_is_gray -v
```

Expected FAIL reason: `ImportError: cannot import name 'composite_over' from 'retail.color'` (collection error, same failure mode as Task 1).

- [ ] 3. Minimal implementation -- add to `src/seshat/color.py` directly after `delta_e76`:

```python
def composite_over(fg: str, bg: str, transparency_pct: float) -> str:
    """``#RRGGBB`` of ``fg`` alpha-composited over ``bg``.

    ``transparency_pct`` is in [0, 100]; 0 means fully opaque ``fg`` (result
    equals ``fg``), 100 means fully transparent ``fg`` (result equals ``bg``).
    Blends per-channel in sRGB (gamma) space, matching how a UI framework
    composites two already-encoded colors -- not a linear-light blend. Raises
    ValueError for an out-of-range pct or a malformed hex so a bad caller
    value never leaks a bare stdlib traceback downstream.
    """
    if not (0.0 <= transparency_pct <= 100.0):
        raise ValueError(
            f"transparency_pct must be in [0, 100], got {transparency_pct!r}"
        )
    if not is_valid_hex(fg):
        raise ValueError(f"not a #RRGGBB hex color: {fg!r}")
    if not is_valid_hex(bg):
        raise ValueError(f"not a #RRGGBB hex color: {bg!r}")

    alpha = 1.0 - transparency_pct / 100.0
    h_fg = fg.lstrip("#")
    h_bg = bg.lstrip("#")
    out_channels = []
    for i in (0, 2, 4):
        fg_c = int(h_fg[i : i + 2], 16)
        bg_c = int(h_bg[i : i + 2], 16)
        out_channels.append(round(alpha * fg_c + (1.0 - alpha) * bg_c))
    return "#" + "".join(f"{v:02X}" for v in out_channels)
```

- [ ] 4. Run tests -- confirm PASS:

```
pytest tests/unit/test_color.py -v
```

Expected: all tests in the file PASS (pre-existing + Task 1's 6 + these 6 composite_over tests).

- [ ] 5. Format, lint, run the full unit suite as a regression check, and commit:

```
ruff format src/seshat/color.py tests/unit/test_color.py
ruff check src/seshat/color.py tests/unit/test_color.py
pytest -m unit -x -q
git add src/seshat/color.py tests/unit/test_color.py
git commit -m "feat: color.py -- add composite_over alpha-compositing primitive"
```

**OWNER STOP:** none in this section -- Phase 0 is pure stdlib arithmetic with no gate surface (no rule, no CLI, no `spec_md` line). The idea-1 floor re-derivation (Task 14) is where the first OWNER ratification stop is required, per the design doc's Build Order.

---

### Task 3: color.py -- add `format_pt` (int-safe pt formatting helper)

**Files:**
- Modify: `src/seshat/color.py` -- add helper after `composite_over` (end of file).
- Modify: `tests/unit/test_color.py` -- extend the import line and append new test functions.

**Interfaces:**
- Consumes: `float`.
- Produces: `format_pt(value: float) -> float | int` -- returns `int(value)` when `value` is integral (e.g. `12.0 -> 12`), else returns `value` unchanged (e.g. `11.5 -> 11.5`). Pure formatting helper so `json.dumps` never churns committed integral fontSize values (`12`, `9`) into `12.0`/`9.0`.

Steps:

- [ ] 1. Write the failing test. Append to `tests/unit/test_color.py`:

```python
def test_format_pt_collapses_integral_float_to_int() -> None:
    assert format_pt(12.0) == 12
    assert isinstance(format_pt(12.0), int)
    assert format_pt(9.0) == 9


def test_format_pt_preserves_fractional_value() -> None:
    assert format_pt(11.5) == 11.5
    assert isinstance(format_pt(11.5), float)
```

Add `format_pt` to the import block:

```python
from retail.color import (
    composite_over,
    contrast_ratio,
    delta_e76,
    format_pt,
    hex_to_lab,
    is_valid_hex,
    relative_luminance,
)
```

- [ ] 2. Run it and confirm the FAIL reason:

```
pytest tests/unit/test_color.py::test_format_pt_collapses_integral_float_to_int -v
```
Expected: `ImportError: cannot import name 'format_pt' from 'retail.color'`.

- [ ] 3. Minimal implementation. Append to `src/seshat/color.py`:

```python
def format_pt(value: float) -> float | int:
    """Render a point size as ``int`` when integral, else keep the float.

    Prevents committed integral font sizes (``12``, ``9``) from churning to
    ``12.0``/``9.0`` on every regeneration -- a purely cosmetic JSON-shape
    change with no accessibility meaning.
    """
    return int(value) if value == int(value) else value
```

- [ ] 4. Run both new tests plus the full color module suite:

```
pytest tests/unit/test_color.py -v
```
Expected: all PASS, including the two new tests.

- [ ] 5. Format, lint, commit:

```
ruff format src/seshat/color.py tests/unit/test_color.py
ruff check src/seshat/color.py tests/unit/test_color.py
git add src/seshat/color.py tests/unit/test_color.py
git commit -m "feat: color.py format_pt helper -- integral pt sizes render as int, not float"
```

---

### Task 4: Extract `_targets_for` and split `generate()` into validate/write phases (no behavior change)

**Files:**
- Modify: `src/seshat/theme_gen.py` (lines 251-277 -- `generate()`; this task restructures it into three helpers and a thin composing `generate()`)
- Modify: `tests/unit/test_theme_gen.py` (add one new test near the bottom; do NOT rewrite `test_generate_writes_three_artifacts` -- it is the regression pin)

**Interfaces:**
- Consumes: `ThemeSeed` (existing), `build_palette(seed) -> dict` (existing), `check_contrast_or_raise(palette, floor=AA_FLOOR) -> None` (existing), `render_tokens_yaml`/`render_theme_json`/`render_spec_md` (existing, unchanged signatures)
- Produces:
  - `_targets_for(seed: ThemeSeed, repo_root: Path, palette: dict) -> dict[Path, str]` -- pure, no I/O; returns the same 3-entry dict literal currently inlined in `generate()`.
  - `_validate_and_collect(seed: ThemeSeed, repo_root: Path, force: bool) -> dict[Path, str]` -- calls `build_palette`, `check_contrast_or_raise`, `_targets_for`, then the `force`/`p.exists()` collision check; raises `ThemeGenError` on any failure; performs NO writes.
  - `_write_targets(targets: dict[Path, str]) -> list[Path]` -- the write loop only (`mkdir` + `write_text`); no validation.
  - `generate(seed: ThemeSeed, repo_root: Path, force: bool = False) -> list[Path]` -- unchanged public signature; body becomes `return _write_targets(_validate_and_collect(seed, repo_root, force))`.

Steps:

- [ ] 1. Write the failing test first -- it targets the new `_targets_for` seam directly (the regression proof for "no behavior change" is the full existing suite, exercised in step 4, not this new test).

```python
def test_targets_for_returns_expected_three_paths(tmp_path: Path) -> None:
    from retail.theme_gen import _targets_for, build_palette

    seed = _seed()
    palette = build_palette(seed)
    targets = _targets_for(seed, tmp_path, palette)
    rels = sorted(str(p.relative_to(tmp_path)).replace("\\", "/") for p in targets)
    assert rels == [
        "design/tokens/executive-dark-design-tokens.yaml",
        "themes/executive-dark.theme-spec.md",
        "themes/executive-dark.theme.json",
    ]
    assert all(isinstance(v, str) and v for v in targets.values())
```

- [ ] 2. Run it and confirm the expected failure:
```
pytest tests/unit/test_theme_gen.py::test_targets_for_returns_expected_three_paths -v
```
Expected FAIL reason: `ImportError: cannot import name '_targets_for' from 'retail.theme_gen'` (the function does not exist yet -- it is still an inline dict literal inside `generate()`).

- [ ] 3. Minimal implementation -- replace `generate()` (current lines 251-277) with four functions:

```python
def _targets_for(seed: ThemeSeed, repo_root: Path, palette: dict) -> dict[Path, str]:
    """Pure: theme output path -> rendered file content. No I/O, no validation."""
    return {
        repo_root
        / "design"
        / "tokens"
        / f"{seed.name}-design-tokens.yaml": render_tokens_yaml(palette, seed),
        repo_root / "themes" / f"{seed.name}.theme.json": render_theme_json(
            palette, seed
        ),
        repo_root / "themes" / f"{seed.name}.theme-spec.md": render_spec_md(
            palette, seed
        ),
    }


def _validate_and_collect(
    seed: ThemeSeed, repo_root: Path, force: bool
) -> dict[Path, str]:
    """Run every self-check + build the target set; raise before any write.

    This is the single choke point for pre-write gates: contrast today, and
    the future font-floor / categorical-distinctness / ramp-deltaE self-checks
    slot in here too, so a caller validating multiple seeds (e.g. a light/dark
    pair) can validate all of them before writing any of them.
    """
    palette = build_palette(seed)
    check_contrast_or_raise(palette)
    targets = _targets_for(seed, repo_root, palette)
    if not force:
        for p in targets:
            if p.exists():
                raise ThemeGenError(
                    f"{p} exists -- refusing to overwrite (use --force)"
                )
    return targets


def _write_targets(targets: dict[Path, str]) -> list[Path]:
    """Write-only phase: no validation, assumes targets already cleared."""
    written: list[Path] = []
    for p, content in targets.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
        written.append(p)
    return written


def generate(seed: ThemeSeed, repo_root: Path, force: bool = False) -> list[Path]:
    return _write_targets(_validate_and_collect(seed, repo_root, force))
```

- [ ] 4. Run the whole file plus lint/format to prove no behavior change (this, not the new test, is the regression proof -- `test_generate_writes_three_artifacts` is the pin that must stay green untouched):
```
pytest tests/unit/test_theme_gen.py -q
ruff format --check src/seshat/theme_gen.py tests/unit/test_theme_gen.py
ruff check src/seshat/theme_gen.py tests/unit/test_theme_gen.py
```
Expected PASS: all tests green (including the new `test_targets_for_returns_expected_three_paths` and the untouched `test_generate_writes_three_artifacts`), ruff clean.

- [ ] 5. Commit:
```
git add src/seshat/theme_gen.py tests/unit/test_theme_gen.py && git commit -m "refactor: split theme_gen.generate() into validate/collect/write phases"
```

---

### Task 5: `ThemeSeed` font fields + module font-floor constants + `check_font_floor_or_raise`

**Files:**
- Modify: `src/seshat/theme_gen.py` -- `ThemeSeed` dataclass (append fields after `bad`); add constants near `AA_FLOOR` (line 26); add `check_font_floor_or_raise` after `check_contrast_or_raise` (after line 155)
- Modify: `tests/unit/test_theme_gen.py` -- add new test functions (the `DARK` seed dict needs no new keys; fields have defaults)

**Interfaces:**
- Consumes: `ThemeSeed` (now with `title_font_pt: float = 12.0`, `label_font_pt: float = 9.0`)
- Produces: `check_font_floor_or_raise(seed: ThemeSeed) -> None` -- raises `ThemeGenError` if `seed.title_font_pt < MIN_TITLE_FONT_PT` or `seed.label_font_pt < MIN_LABEL_FONT_PT`; returns `None` (no finding) otherwise.
- New module constants (fixed, NOT CLI-settable, NOT read from any file): `MIN_TITLE_FONT_PT = 12.0`, `MIN_LABEL_FONT_PT = 9.0`, `TAP_TARGET_MIN_PX = 44`.

Steps:

- [ ] 1. Write the failing tests. Append to `tests/unit/test_theme_gen.py`:

```python
def test_check_font_floor_raises_below_title_floor() -> None:
    from retail.theme_gen import ThemeGenError, check_font_floor_or_raise

    seed = _seed(title_font_pt=11.9)
    with pytest.raises(ThemeGenError, match="title_font_pt"):
        check_font_floor_or_raise(seed)


def test_check_font_floor_raises_below_label_floor() -> None:
    from retail.theme_gen import ThemeGenError, check_font_floor_or_raise

    seed = _seed(label_font_pt=8.9)
    with pytest.raises(ThemeGenError, match="label_font_pt"):
        check_font_floor_or_raise(seed)


def test_check_font_floor_passes_at_exact_floor() -> None:
    from retail.theme_gen import check_font_floor_or_raise

    seed = _seed(title_font_pt=12.0, label_font_pt=9.0)
    check_font_floor_or_raise(seed)  # no raise


def test_font_floor_constants_are_fixed_values() -> None:
    from retail.theme_gen import MIN_LABEL_FONT_PT, MIN_TITLE_FONT_PT, TAP_TARGET_MIN_PX

    assert MIN_TITLE_FONT_PT == 12.0
    assert MIN_LABEL_FONT_PT == 9.0
    assert TAP_TARGET_MIN_PX == 44
```

- [ ] 2. Run and confirm FAIL:

```
pytest tests/unit/test_theme_gen.py::test_check_font_floor_raises_below_title_floor -v
```
Expected: `TypeError: ThemeSeed.__init__() got an unexpected keyword argument 'title_font_pt'` (the field does not exist yet).

- [ ] 3. Minimal implementation. In `src/seshat/theme_gen.py`:

Edit the constants block (after line 26 `AA_FLOOR = 4.5`):

```python
AA_FLOOR = 4.5
MIN_TITLE_FONT_PT = 12.0
MIN_LABEL_FONT_PT = 9.0
TAP_TARGET_MIN_PX = 44  # doc-only floor (WCAG 2.5.8); never written to any artifact
_TEXT_ROLES = ("primary", "secondary", "muted")
```

Edit `ThemeSeed` (append fields after `bad: str`, so existing positional/keyword call sites with no font args still work):

```python
@dataclass(frozen=True)
class ThemeSeed:
    name: str
    mode: str  # "light" | "dark"
    accent: str
    background: str
    text_primary: str
    text_secondary: str
    text_muted: str
    data_colors: tuple[str, ...] | None
    good: str
    neutral: str
    bad: str
    title_font_pt: float = 12.0
    label_font_pt: float = 9.0
```

Add `check_font_floor_or_raise` right after `check_contrast_or_raise` (after line 155, before `render_tokens_yaml`):

```python
def check_font_floor_or_raise(seed: ThemeSeed) -> None:
    """Refuse a title/label font size below the fixed accessibility floor.

    The floors (MIN_TITLE_FONT_PT, MIN_LABEL_FONT_PT) are fixed module
    constants -- never CLI-settable, never read from tokens -- so this check
    cannot be tuned away by a caller (a settable floor of 0 would make the
    refusal decorative).
    """
    if seed.title_font_pt < MIN_TITLE_FONT_PT:
        raise ThemeGenError(
            f"title_font_pt {seed.title_font_pt:g} is below the "
            f"{MIN_TITLE_FONT_PT:g}pt accessibility floor -- refusing to write"
        )
    if seed.label_font_pt < MIN_LABEL_FONT_PT:
        raise ThemeGenError(
            f"label_font_pt {seed.label_font_pt:g} is below the "
            f"{MIN_LABEL_FONT_PT:g}pt accessibility floor -- refusing to write"
        )
```

- [ ] 4. Run tests:

```
pytest tests/unit/test_theme_gen.py -v
```
Expected: all PASS (new font-floor tests + all pre-existing `test_theme_gen.py` tests still green, since the two new fields carry defaults).

- [ ] 5. Commit:

```
git add src/seshat/theme_gen.py tests/unit/test_theme_gen.py
git commit -m "feat: ThemeSeed title/label font-pt fields + fixed accessibility floor check"
```

---

### Task 6: wire `check_font_floor_or_raise` into `generate()`, render fonts from the seed, emit typography block in tokens YAML

**Files:**
- Modify: `src/seshat/theme_gen.py` -- `render_theme_json` (font literals at 205-206); `render_tokens_yaml` (add typography block before `accessibility:`); `_validate_and_collect()` (add the call right after `check_contrast_or_raise`); `render_spec_md` (add the `[x]` Font floor line + tap-target `[ ]` doc note); import `format_pt`
- Modify: `tests/unit/test_theme_gen.py`

**Interfaces:**
- Consumes: `ThemeSeed.title_font_pt`, `ThemeSeed.label_font_pt`, `color.format_pt`
- Produces: no new function; `render_theme_json`, `render_tokens_yaml`, `render_spec_md`, `_validate_and_collect` change their output/behavior only.

Note: the font-floor call goes in `_validate_and_collect` (the Task-4 choke point), NOT the old inline `generate()` body -- `generate()` is now `return _write_targets(_validate_and_collect(...))`.

Steps:

- [ ] 1. Write the failing tests. Append to `tests/unit/test_theme_gen.py`:

```python
def test_render_theme_json_uses_seed_font_sizes() -> None:
    theme = json.loads(render_theme_json(build_palette(_seed()), _seed()))
    title = theme["visualStyles"]["*"]["*"]["title"][0]
    labels = theme["visualStyles"]["*"]["*"]["labels"][0]
    assert title["fontSize"] == 12
    assert labels["fontSize"] == 9


def test_render_theme_json_custom_font_sizes_round_trip() -> None:
    seed = _seed(title_font_pt=14.0, label_font_pt=10.0)
    theme = json.loads(render_theme_json(build_palette(seed), seed))
    assert theme["visualStyles"]["*"]["*"]["title"][0]["fontSize"] == 14
    assert theme["visualStyles"]["*"]["*"]["labels"][0]["fontSize"] == 10


def test_tokens_yaml_emits_typography_block() -> None:
    tokens = yaml.safe_load(render_tokens_yaml(build_palette(_seed()), _seed()))
    assert tokens["typography"]["title_font_pt"] == 12
    assert tokens["typography"]["label_font_pt"] == 9


def test_generate_refuses_sub_floor_title_font(tmp_path: Path) -> None:
    with pytest.raises(ThemeGenError, match="title_font_pt"):
        generate(_seed(title_font_pt=11.9), repo_root=tmp_path)
    assert not (tmp_path / "themes").exists()  # refused before any write


def test_spec_md_has_font_floor_line_and_tap_target_is_doc_only() -> None:
    spec = render_spec_md(build_palette(_seed()), _seed())
    assert "[x]" in spec and "Font floor" in spec
    assert "tap" in spec.lower() or "Tap" in spec
    assert '"tapTarget"' not in spec
```

- [ ] 2. Run and confirm FAIL (use the custom-size test to get a real FAIL, not the default case which passes trivially):

```
pytest tests/unit/test_theme_gen.py::test_render_theme_json_custom_font_sizes_round_trip -v
```
Expected FAIL: `AssertionError: assert 12 == 14` (render_theme_json still hardcodes `12`/`9`, ignores the seed).

- [ ] 3. Minimal implementation.

Edit the color import line (currently `from .color import contrast_ratio, is_valid_hex`):

```python
from .color import contrast_ratio, format_pt, is_valid_hex
```

Edit `render_theme_json` (lines 191-211) to read the seed:

```python
def render_theme_json(palette: dict, seed: ThemeSeed) -> str:
    c = palette["colors"]
    title_pt = format_pt(seed.title_font_pt)
    label_pt = format_pt(seed.label_font_pt)
    doc = {
        "name": seed.name,
        "dataColors": c["data_colors"],
        "background": c["background"],
        "foreground": c["text"]["primary"],
        "tableAccent": c["primary"],
        "good": c["sentiment"]["success"],
        "neutral": c["sentiment"]["warning"],
        "bad": c["sentiment"]["danger"],
        "visualStyles": {
            "*": {
                "*": {
                    "title": [
                        {"fontFamily": "Segoe UI Semibold", "fontSize": title_pt}
                    ],
                    "labels": [{"fontFamily": "Segoe UI", "fontSize": label_pt}],
                }
            }
        },
    }
    return json.dumps(doc, indent=2) + "\n"
```

Edit `render_tokens_yaml` -- replace the existing `"  data_colors:\n" f"{ramp}\n" "accessibility:\n"` three-line tail with the typography block inserted between `data_colors` and `accessibility`:

```python
        "  data_colors:\n"
        f"{ramp}\n"
        "typography:\n"
        f"  title_font_pt: {format_pt(seed.title_font_pt)}\n"
        f"  label_font_pt: {format_pt(seed.label_font_pt)}\n"
        "accessibility:\n"
```

Edit `_validate_and_collect()` to call the new check right after contrast:

```python
    palette = build_palette(seed)
    check_contrast_or_raise(palette)
    check_font_floor_or_raise(seed)
    targets = _targets_for(seed, repo_root, palette)
```

Edit `render_spec_md` -- add the `[x]` Font floor line right after the Contrast `[x]` block, and a tap-target doc-only `[ ]` note after the saturation line:

```python
        "(all >= 4.5:1 AA). *Evidence: CT1 arithmetic on the committed "
        "tokens.*\n"
        "- [x] **Font floor** (computed): title "
        f"{seed.title_font_pt:g}pt >= {MIN_TITLE_FONT_PT:g}pt, label "
        f"{seed.label_font_pt:g}pt >= {MIN_LABEL_FONT_PT:g}pt. *Evidence: "
        "check_font_floor_or_raise on the committed tokens (a number proves "
        "the number, not on-screen legibility).*\n"
        "- [ ] **CVD distinguishability** -- OPEN: the monochromatic ramp is "
        "less category-distinguishable; needs a named reviewer (Principle V).\n"
        "- [ ] **Small-size / adjacency legibility** -- OPEN: needs a named "
        "reviewer against a rendered page (F016 surface; not yet built).\n"
        "- [ ] **No pure-saturated background behind dense charts** -- OPEN: "
        "named-reviewer design note.\n"
        "- [ ] **Tap-target sizing** -- OPEN, doc-only: interactive elements "
        f"should target >= {TAP_TARGET_MIN_PX}px; not computable from a "
        "DEFINE-only palette, no `tapTarget` key is ever written; needs a "
        "named reviewer against a rendered page.\n\n"
```

- [ ] 4. Run tests:

```
pytest tests/unit/test_theme_gen.py -v
```
Expected: all PASS, including the 5 new tests. Also confirm the DL1-clean walk still passes (fontSize/fontFamily keys unchanged in shape):

```
pytest tests/unit/test_theme_gen.py::test_generated_theme_is_dl1_clean -v
```
Expected: PASS.

- [ ] 5. Commit:

```
git add src/seshat/theme_gen.py tests/unit/test_theme_gen.py
git commit -m "feat: theme-gen renders seed font sizes + refuses sub-floor fonts before write"
```

---

### Task 7: `--title-font-pt` / `--label-font-pt` CLI flags

**Files:**
- Modify: `src/seshat/cli/parser.py` -- theme-gen subparser, add two `add_argument` calls after `--bad` and before `--repo`/`--force`
- Modify: `src/seshat/theme_gen.py` -- `theme_gen_main` (lines 289-301), read the two new args into the `ThemeSeed` call
- Modify: `tests/unit/test_cli_parser.py` (check the parser factory name first)

**Interfaces:**
- Consumes: `args.title_font_pt: str | None`, `args.label_font_pt: str | None` (argparse strings, converted to `float`)
- Produces: no new function; `theme_gen_main` passes `title_font_pt=float(args.title_font_pt) if args.title_font_pt else 12.0` (and label equivalent) into `ThemeSeed`.

Steps:

- [ ] 1. Locate the existing CLI parser test pattern.

```
Grep -n "theme-gen\|theme_gen\|build_parser" tests/unit/test_cli_parser.py
```

- [ ] 2. Write the failing test. Append to `tests/unit/test_cli_parser.py` (mirroring the existing theme-gen parse assertions; use the exact parser factory name found in step 1):

```python
def test_theme_gen_parser_accepts_font_pt_flags() -> None:
    from retail.cli.parser import build_parser

    parser = build_parser()
    args = parser.parse_args(
        [
            "theme-gen",
            "--name",
            "t1",
            "--mode",
            "light",
            "--accent",
            "#2E7D5B",
            "--background",
            "#FFFFFF",
            "--text-primary",
            "#111111",
            "--title-font-pt",
            "14",
            "--label-font-pt",
            "10",
        ]
    )
    assert args.title_font_pt == "14"
    assert args.label_font_pt == "10"


def test_theme_gen_parser_font_pt_flags_default_none() -> None:
    from retail.cli.parser import build_parser

    parser = build_parser()
    args = parser.parse_args(
        [
            "theme-gen",
            "--name",
            "t1",
            "--mode",
            "light",
            "--accent",
            "#2E7D5B",
            "--background",
            "#FFFFFF",
            "--text-primary",
            "#111111",
        ]
    )
    assert args.title_font_pt is None
    assert args.label_font_pt is None
```

- [ ] 3. Run and confirm FAIL:

```
pytest tests/unit/test_cli_parser.py::test_theme_gen_parser_accepts_font_pt_flags -v
```
Expected: `AttributeError: 'Namespace' object has no attribute 'title_font_pt'`.

- [ ] 4. Minimal implementation.

Edit `src/seshat/cli/parser.py` -- insert after the `--bad` line and before `--repo`:

```python
    themegen.add_argument(
        "--title-font-pt",
        dest="title_font_pt",
        default=None,
        metavar="PT",
        help="title font size in points (default 12.0; floor enforced, not settable)",
    )
    themegen.add_argument(
        "--label-font-pt",
        dest="label_font_pt",
        default=None,
        metavar="PT",
        help="label font size in points (default 9.0; floor enforced, not settable)",
    )
```

Edit `theme_gen_main` in `src/seshat/theme_gen.py` (lines 289-301) to thread the two new args through the `ThemeSeed` call, appending after `bad=...`:

```python
        bad=args.bad or _DEFAULT_SENTIMENT["bad"],
        title_font_pt=float(args.title_font_pt) if args.title_font_pt else 12.0,
        label_font_pt=float(args.label_font_pt) if args.label_font_pt else 9.0,
    )
```

- [ ] 5. Run tests:

```
pytest tests/unit/test_cli_parser.py -v
pytest tests/unit/test_theme_gen.py -v
```
Expected: all PASS.

- [ ] 6. Commit:

```
git add src/seshat/cli/parser.py src/seshat/theme_gen.py tests/unit/test_cli_parser.py
git commit -m "feat: theme-gen CLI gains --title-font-pt / --label-font-pt (floor is fixed, not CLI-settable)"
```

---

### Task 8: `seed_from_tokens` per-key typography fallback + `check_font_floor_or_raise` wired into `compile_theme`

**Files:**
- Modify: `src/seshat/theme_compile.py` -- `seed_from_tokens` (lines 150-171); `compile_theme` (add the call right after `check_contrast_or_raise`); import list (lines 29-35)
- Modify: `tests/unit/test_theme_compile.py`

**Interfaces:**
- Consumes: `tokens_doc: dict` with an OPTIONAL `typography.title_font_pt` / `typography.label_font_pt`
- Produces: `seed_from_tokens` now populates `ThemeSeed.title_font_pt` / `label_font_pt` by per-KEY fallback (not per-block): `typo = tokens_doc.get("typography") or {}` then `float(typo.get("title_font_pt", MIN_TITLE_FONT_PT))`. `compile_theme` calls `check_font_floor_or_raise(seed)` after `check_contrast_or_raise(palette)`.

Steps:

- [ ] 1. Write the failing tests. Append to `tests/unit/test_theme_compile.py`:

```python
def test_seed_from_tokens_reads_typography_block() -> None:
    tokens = {**TOKENS, "typography": {"title_font_pt": 14, "label_font_pt": 10}}
    seed = seed_from_tokens(tokens, name_override=None)
    assert seed.title_font_pt == 14.0
    assert seed.label_font_pt == 10.0


def test_seed_from_tokens_falls_back_to_constants_when_typography_absent() -> None:
    # executive-dark shape: no typography block at all.
    seed = seed_from_tokens(TOKENS, name_override=None)
    assert seed.title_font_pt == 12.0
    assert seed.label_font_pt == 9.0


def test_seed_from_tokens_falls_back_per_key_when_typography_block_partial() -> None:
    # tower-retail shape: a typography block exists but lacks font-pt keys.
    tokens = {
        **TOKENS,
        "typography": {"font_family": "Segoe UI", "base_size_pt": 10},
    }
    seed = seed_from_tokens(tokens, name_override=None)
    assert seed.title_font_pt == 12.0
    assert seed.label_font_pt == 9.0


def test_compile_refuses_sub_floor_title_font(tmp_path: Path) -> None:
    tokens = {**TOKENS, "typography": {"title_font_pt": 11.9, "label_font_pt": 9}}
    p = _write_tokens(tmp_path, tokens)
    with pytest.raises(ThemeCompileError, match="title_font_pt"):
        compile_theme(p, out_path=None, force=False)


def test_custom_font_pt_round_trips_through_generate_then_compile(tmp_path: Path):
    """Idea 4 round-trip: gen a 14pt title, compile from its own tokens, no
    phantom DL3-deferred conflict, fontSize:14 survives byte-identical."""
    from retail.theme_gen import ThemeSeed, generate

    seed = ThemeSeed(
        name="roundtrip",
        mode="light",
        accent="#2E7D5B",
        background="#FFFFFF",
        text_primary="#111111",
        text_secondary="#333333",
        text_muted="#555555",
        data_colors=None,
        good="#2E7D5B",
        neutral="#B5832A",
        bad="#B23A3A",
        title_font_pt=14.0,
        label_font_pt=9.0,
    )
    generate(seed, tmp_path, force=True)
    theme_path = tmp_path / "themes/roundtrip.theme.json"
    assert json.loads(theme_path.read_text())["visualStyles"]["*"]["*"]["title"][0][
        "fontSize"
    ] == 14

    # recompile from the committed tokens over the existing theme -- must NOT
    # raise a DL3-deferred conflict, and must keep fontSize:14.
    tokens_path = tmp_path / "design/tokens/roundtrip-design-tokens.yaml"
    out = compile_theme(tokens_path, out_path=None, force=True)
    recompiled = json.loads(out.read_text())
    assert recompiled["visualStyles"]["*"]["*"]["title"][0]["fontSize"] == 14
```

- [ ] 2. Run and confirm FAIL:

```
pytest tests/unit/test_theme_compile.py::test_seed_from_tokens_reads_typography_block -v
```
Expected FAIL: `AssertionError: assert 12.0 == 14.0` (seed_from_tokens ignores the tokens' typography block and always uses the ThemeSeed default).

- [ ] 3. Minimal implementation.

Edit imports in `src/seshat/theme_compile.py` (lines 29-35) to add `MIN_LABEL_FONT_PT`, `MIN_TITLE_FONT_PT`, `check_font_floor_or_raise`:

```python
from .theme_gen import (
    MIN_LABEL_FONT_PT,
    MIN_TITLE_FONT_PT,
    ThemeGenError,
    ThemeSeed,
    _validate_name,
    check_contrast_or_raise,
    check_font_floor_or_raise,
    render_theme_json,
)
```

Edit `seed_from_tokens` (lines 150-171) to add the per-key fallback read and thread the two new fields into the `ThemeSeed(...)` call:

```python
    # Per-KEY fallback, not per-block: a pre-feature tokens file may have no
    # typography block at all (executive-dark), or a typography block that
    # predates these two keys (tower-retail's base_size_pt/scale_pt block).
    # Either way, a missing KEY falls back to the fixed constant -- never to
    # a guessed/inherited value -- so a byte-identical recompile of an
    # unmodified tokens file never trips a phantom font-field conflict.
    typo = tokens_doc.get("typography") or {}
    title_font_pt = float(typo.get("title_font_pt", MIN_TITLE_FONT_PT))
    label_font_pt = float(typo.get("label_font_pt", MIN_LABEL_FONT_PT))
    return ThemeSeed(
        name=name,
        mode=_mode_from_style(tokens_doc),
        accent=c["primary"],
        background=c["background"],
        text_primary=c["text"]["primary"],
        text_secondary=c["text"]["secondary"],
        text_muted=c["text"]["muted"],
        data_colors=tuple(c["data_colors"]),
        good=c["sentiment"]["success"],
        neutral=c["sentiment"]["warning"],
        bad=c["sentiment"]["danger"],
        title_font_pt=title_font_pt,
        label_font_pt=label_font_pt,
    )
```

Edit `compile_theme` to add the font-floor check right after the contrast check:

```python
    check_contrast_or_raise(palette)  # refuse a theme CT1 would reject
    check_font_floor_or_raise(seed)  # refuse a committed sub-floor font
```

- [ ] 4. Run tests:

```
pytest tests/unit/test_theme_compile.py -v
```
Expected: all PASS, including the 5 new tests -- `test_custom_font_pt_round_trips_through_generate_then_compile` must show `fontSize == 14` survives the compile leg with no `ThemeCompileError` raised (`visualStyles` is a `_DL3_DEFERRED_FIELDS` entry, so compile re-renders it fresh from the seed each time; the freshly rendered `visualStyles` equals the on-disk 14pt version byte-for-byte and no conflict fires).

- [ ] 5. Run the full existing regression pass for both modules together (they share `ThemeSeed`):

```
pytest tests/unit/test_theme_gen.py tests/unit/test_theme_compile.py -v
```
Expected: all PASS.

- [ ] 6. Commit:

```
git add src/seshat/theme_compile.py tests/unit/test_theme_compile.py
git commit -m "fix: theme-compile reads typography per-key (not per-block) + refuses sub-floor fonts"
```

---

### Task 9: full-suite regression + lint gate for Idea 4

**Files:** none (verification-only task)

**Interfaces:** none (runs the existing test/lint commands)

Steps:

- [ ] 1. Run the mandatory local verification gate:

```
ruff format --check src/seshat/color.py src/seshat/theme_gen.py src/seshat/theme_compile.py src/seshat/cli/parser.py tests/unit/test_color.py tests/unit/test_theme_gen.py tests/unit/test_theme_compile.py tests/unit/test_cli_parser.py
ruff check src/seshat/color.py src/seshat/theme_gen.py src/seshat/theme_compile.py src/seshat/cli/parser.py tests/unit/test_color.py tests/unit/test_theme_gen.py tests/unit/test_theme_compile.py tests/unit/test_cli_parser.py
```
Expected: both commands print nothing / exit 0. If `ruff format --check` fails, run `ruff format <same paths>` and re-diff before committing.

- [ ] 2. Run the full unit suite (Idea 4 touches shared `theme_gen.py`/`theme_compile.py`):

```
pytest -m unit -x -q
```
Expected: all tests PASS, no regressions in `test_design_theme_fidelity.py`, `test_design_contrast.py`, or the rule wiring tests (Idea 4 adds no rule, so `EXPECTED_RULE_IDS` is untouched by this task).

- [ ] 3. Confirm no rule/manifest/glossary drift was introduced (Idea 4 is generation-side only, no `retail check` rule):

```
pytest tests/unit/test_rules_manifest_snapshot.py tests/unit/test_rules_wiring.py tests/unit/test_glossary_rule_table.py -v
```
Expected: all PASS unchanged (these files are not touched by Idea 4's edits).

**OWNER STOP:** present the diff for `src/seshat/theme_gen.py`, `src/seshat/theme_compile.py`, `src/seshat/cli/parser.py`, `src/seshat/color.py`, the new typography-block shape in `render_tokens_yaml`'s output, and the two new CLI flags. The build halts here because: (a) this is the first PR-sized slice and the owner has not yet ratified that `render_tokens_yaml`'s new `typography:` block placement (between `data_colors` and `accessibility`) is the desired committed-tokens shape going forward -- every future `retail theme-gen` run will now always emit this block, a permanent format change; (b) run the CodeScene new-code health gate (10.0) on the touched functions (`render_theme_json`, `render_tokens_yaml`, `seed_from_tokens`, `compile_theme`) per the `codescene-new-code-health-gate` memory before opening a PR -- do not self-grant a clean bill.

---

### Task 10: Categorical distinctness self-check in theme_gen (min pairwise deltaE76)

**Files:**
- Modify: `src/seshat/theme_gen.py` -- add `MIN_CATEGORICAL_DELTAE = 2.0` constant near `AA_FLOOR`; add `min_categorical_delta_e(data_colors: tuple[str, ...]) -> float` and `check_categorical_distinctness_or_raise(palette: dict, floor: float = MIN_CATEGORICAL_DELTAE) -> None` after `check_contrast_or_raise`; call the new check in `_validate_and_collect()` right after `check_contrast_or_raise(palette)`; add an `[x]` evidence line to `render_spec_md` directly under the existing CT1 contrast `[x]` block; update the color import to add `delta_e76`.
- Modify: `tests/unit/test_theme_gen.py` -- add tests using the existing `DARK`/`_seed()` fixtures.

**Interfaces:**
- Consumes: `from .color import delta_e76` (Phase 0 shared helper -- add it to the existing `from .color import contrast_ratio, format_pt, is_valid_hex` line, do NOT re-add a separate import).
- Produces:
  - `MIN_CATEGORICAL_DELTAE: float = 2.0` (module constant).
  - `min_categorical_delta_e(data_colors: tuple[str, ...]) -> float` -- returns the minimum `delta_e76(a, b)` over all unordered pairs `i < j`; returns `float("inf")` for 0 or 1 colors.
  - `check_categorical_distinctness_or_raise(palette: dict, floor: float = MIN_CATEGORICAL_DELTAE) -> None` -- reads `palette["colors"]["data_colors"]`; raises `ThemeGenError` naming the two closest hexes and the computed deltaE if the minimum is below `floor`; no-ops if fewer than 2 colors.

Steps:

- [ ] 1. Write the failing test in `tests/unit/test_theme_gen.py`:

```python
def test_min_categorical_delta_e_default_ramp_passes_floor() -> None:
    from retail.theme_gen import MIN_CATEGORICAL_DELTAE, min_categorical_delta_e

    palette = build_palette(_seed())
    got = min_categorical_delta_e(tuple(palette["colors"]["data_colors"]))
    assert got >= MIN_CATEGORICAL_DELTAE


def test_check_categorical_distinctness_or_raise_flags_near_identical_pair() -> None:
    from retail.theme_gen import check_categorical_distinctness_or_raise

    palette = build_palette(_seed())
    palette["colors"]["data_colors"] = ["#2FB6C4", "#2FB6C5", "#12263A"]
    with pytest.raises(ThemeGenError) as exc:
        check_categorical_distinctness_or_raise(palette)
    msg = str(exc.value)
    assert "#2FB6C4" in msg
    assert "#2FB6C5" in msg


def test_check_categorical_distinctness_or_raise_honors_floor_param() -> None:
    from retail.theme_gen import check_categorical_distinctness_or_raise

    palette = build_palette(_seed())
    palette["colors"]["data_colors"] = ["#2FB6C4", "#2FB6C5"]
    check_categorical_distinctness_or_raise(palette, floor=0.0)  # does not raise


def test_min_categorical_delta_e_single_color_is_noop() -> None:
    from retail.theme_gen import (
        check_categorical_distinctness_or_raise,
        min_categorical_delta_e,
    )

    assert min_categorical_delta_e(("#2FB6C4",)) == float("inf")
    palette = build_palette(_seed())
    palette["colors"]["data_colors"] = ["#2FB6C4"]
    check_categorical_distinctness_or_raise(palette)  # does not raise
```

- [ ] 2. Run it and confirm the expected failure:
```
pytest tests/unit/test_theme_gen.py::test_min_categorical_delta_e_default_ramp_passes_floor -v
```
Expected FAIL: `ImportError: cannot import name 'MIN_CATEGORICAL_DELTAE' from 'retail.theme_gen'`.

- [ ] 3. Minimal implementation. Add the constant next to `AA_FLOOR`:

```python
MIN_CATEGORICAL_DELTAE = 2.0  # CIE76 JND-adjacent floor for whole-set data_colors distinctness
```

Update the color import line to add `delta_e76`:

```python
from .color import contrast_ratio, delta_e76, format_pt, is_valid_hex
```

Add the two functions immediately after `check_contrast_or_raise`:

```python
def min_categorical_delta_e(data_colors: tuple[str, ...]) -> float:
    """Minimum CIE76 deltaE76 over all i<j pairs in data_colors.

    Returns float("inf") when fewer than 2 colors are present (no pair to
    compare, so nothing can violate a distinctness floor).
    """
    n = len(data_colors)
    if n < 2:
        return float("inf")
    best = float("inf")
    for i in range(n):
        for j in range(i + 1, n):
            d = delta_e76(data_colors[i], data_colors[j])
            if d < best:
                best = d
    return best


def check_categorical_distinctness_or_raise(
    palette: dict, floor: float = MIN_CATEGORICAL_DELTAE
) -> None:
    """Refuse to proceed if any two data_colors entries collapse under floor.

    Whole-set (all i<j pairs), not just adjacent -- catches a normal-vision
    near-duplicate anywhere in the categorical palette. Does not auto-widen
    hue: a caught collision is refused, never silently corrected (auto-
    correction can't be justified CVD-safe without a named reviewer).
    """
    data_colors = tuple(palette["colors"].get("data_colors") or ())
    n = len(data_colors)
    if n < 2:
        return
    worst_pair: tuple[str, str] | None = None
    worst = float("inf")
    for i in range(n):
        for j in range(i + 1, n):
            d = delta_e76(data_colors[i], data_colors[j])
            if d < worst:
                worst = d
                worst_pair = (data_colors[i], data_colors[j])
    if worst < floor and worst_pair is not None:
        raise ThemeGenError(
            f"categorical distinctness: data_colors {worst_pair[0]} and "
            f"{worst_pair[1]} are {worst:.2f} dE76 apart, below the "
            f"{floor:g} dE76 floor -- refusing to write (would fail CT3)"
        )
```

Wire the call into `_validate_and_collect()` right after `check_contrast_or_raise(palette)` (and after `check_font_floor_or_raise(seed)` from Task 6):

```python
    check_contrast_or_raise(palette)
    check_font_floor_or_raise(seed)
    check_categorical_distinctness_or_raise(palette)
    targets = _targets_for(seed, repo_root, palette)
```

Add the spec_md evidence line in `render_spec_md`, directly after the existing CT1 `[x]` contrast block, before the CVD `[ ]` line (there must remain exactly one CVD line):

```python
        "(all >= 4.5:1 AA). *Evidence: CT1 arithmetic on the committed "
        "tokens.*\n"
        "- [x] **Categorical distinctness (whole-set)** -- CT3 (computed): "
        f"min pairwise dE76 across data_colors = "
        f"{min_categorical_delta_e(tuple(c['data_colors'])):.2f}, "
        f">= {MIN_CATEGORICAL_DELTAE:g} dE76 floor. *Evidence: CIE76 "
        "arithmetic on the committed ramp (normal-vision near-collapse "
        "guard only -- NOT a colorblind-safe claim).*\n"
```

Note: this task and Task 6 both insert `[x]` lines after the contrast block. When both have landed, the order is: Contrast `[x]`, Font floor `[x]` (Task 6), Categorical `[x]` (this task), then the `[ ]` CVD/legibility/saturation/tap-target lines. Verify no duplicate CVD line remains.

- [ ] 4. Run the tests:
```
pytest tests/unit/test_theme_gen.py -v
pytest tests/unit/test_theme_gen.py -k spec_md -v
```
Expected PASS: all `test_theme_gen.py` tests green, including the four new ones.

- [ ] 5. Commit:
```
git add src/seshat/theme_gen.py tests/unit/test_theme_gen.py
git commit -m "feat: theme_gen categorical distinctness self-check (whole-set dE76 floor)"
```

---

### Task 11: CT3 static rule -- categorical distinctness governance + full wiring

**Files:**
- Create: `src/seshat/rules/design_categorical_distinctness.py` (mirrors `src/seshat/rules/design_contrast.py`).
- Create: `tests/unit/test_design_categorical_distinctness.py` (mirrors `tests/unit/test_design_contrast.py`).
- Modify: `src/seshat/rules/__init__.py` -- add `design_categorical_distinctness` to the import tuple (alphabetically between `design_background` and `design_contrast`) and to `__all__` in the same slot.
- Modify: `tests/unit/test_rules_wiring.py` -- add `"CT3"` to `EXPECTED_RULE_IDS` (near the existing `"CT1"`).
- Modify: `src/seshat/severity_posture.py` -- add a `_YAML_CT3` fixture (near `_YAML_CT1`) and a `"CT3": _Fixture(...)` entry in `_RULE_FIXTURES`.
- Modify: `docs/glossary.md` -- add `CT3` to the `**CT**` family row and update the rule-count line.
- Modify: `docs/quality/rule-count-claims.yaml` -- update `anchor` + `claimed-count` to match.
- Regenerate: `docs/rules/rules-manifest.json` (via `retail manifest`, never hand-edited).
- Regenerate: `docs/rules/severity-posture.json` (via `retail severity-posture`, never hand-edited).

**Interfaces:**
- Consumes: `from ..color import delta_e76`; `from ..core import Finding, RuleContext, Severity, is_test_path`; `from ..registry import register`.
- Produces:
  - `RULE_ID = "CT3"` (module constant).
  - `check_categorical_distinctness(ctx: RuleContext) -> Iterable[Finding]` -- `@register(RULE_ID, "...")`-decorated entry point.
  - Reads `accessibility.min_categorical_deltae` from each committed `*-design-tokens.yaml`; missing key -> silent skip (`return`, no `Finding`), matching CT1's declared-pairs-only pattern -- the floor key itself IS the opt-in signal for CT3.

Steps:

- [ ] 1. Write the failing test. Create `tests/unit/test_design_categorical_distinctness.py`:

```python
"""Unit tests for CT3 (categorical distinctness whole-set pre-check).

CT3 is a deterministic, read-only accessibility check: it computes the CIE76
deltaE76 Euclidean Lab distance between every i<j pair of committed
`colors.data_colors` entries and compares the minimum against a token-declared
`accessibility.min_categorical_deltae` floor. A collapse below the floor is an
ERROR naming both hexes and the computed distance.

Missing declared floor -> SILENT SKIP, not ERROR (Principle V / emits-on-main):
this is a normal-vision near-collapse guard, not a colorblind-safe claim, and
a tokens file that never opted in must stay clean on main.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.design_categorical_distinctness import (
    RULE_ID,
    check_categorical_distinctness,
)

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "categorical_distinctness"
REPO_ROOT = Path(__file__).parent.parent.parent


def _ctx(*tracked: str, repo_root: Path = FIXTURES) -> RuleContext:
    return RuleContext(repo_root=repo_root, tracked_files=tracked)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_ct3_id_is_registered() -> None:
    assert RULE_ID == "CT3"


def test_missing_floor_key_is_silent_skip(tmp_path: Path) -> None:
    _write(
        tmp_path / "design" / "tokens" / "demo-design-tokens.yaml",
        "colors:\n  data_colors:\n    - '#2FB6C4'\n    - '#2FB6C5'\n",
    )
    ctx = _ctx("design/tokens/demo-design-tokens.yaml", repo_root=tmp_path)
    findings = list(check_categorical_distinctness(ctx))
    assert findings == []


def test_near_identical_pair_below_floor_errors(tmp_path: Path) -> None:
    _write(
        tmp_path / "design" / "tokens" / "demo-design-tokens.yaml",
        (
            "colors:\n  data_colors:\n    - '#2FB6C4'\n    - '#2FB6C5'\n"
            "    - '#12263A'\n"
            "accessibility:\n  min_categorical_deltae: 2.0\n"
        ),
    )
    ctx = _ctx("design/tokens/demo-design-tokens.yaml", repo_root=tmp_path)
    findings = list(check_categorical_distinctness(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == RULE_ID
    assert findings[0].severity == Severity.ERROR
    assert "#2FB6C4" in findings[0].message
    assert "#2FB6C5" in findings[0].message


def test_distinct_palette_at_or_above_floor_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path / "design" / "tokens" / "demo-design-tokens.yaml",
        (
            "colors:\n  data_colors:\n    - '#2FB6C4'\n    - '#12263A'\n"
            "accessibility:\n  min_categorical_deltae: 2.0\n"
        ),
    )
    ctx = _ctx("design/tokens/demo-design-tokens.yaml", repo_root=tmp_path)
    assert list(check_categorical_distinctness(ctx)) == []


def test_committed_executive_dark_tokens_are_clean_on_main() -> None:
    rel = "design/tokens/executive-dark-design-tokens.yaml"
    ctx = _ctx(rel, repo_root=REPO_ROOT)
    findings = list(check_categorical_distinctness(ctx))
    assert findings == []  # no min_categorical_deltae declared yet -> skip


def test_committed_tower_retail_tokens_are_clean_on_main() -> None:
    rel = "design/tokens/tower-retail-design-tokens.yaml"
    ctx = _ctx(rel, repo_root=REPO_ROOT)
    findings = list(check_categorical_distinctness(ctx))
    assert findings == []  # no min_categorical_deltae declared yet -> skip
```

- [ ] 2. Run it and confirm the expected failure:
```
pytest tests/unit/test_design_categorical_distinctness.py::test_ct3_id_is_registered -v
```
Expected FAIL: `ModuleNotFoundError: No module named 'retail.rules.design_categorical_distinctness'`.

- [ ] 3. Minimal implementation. Create `src/seshat/rules/design_categorical_distinctness.py`:

```python
"""Design-lint rule CT3: categorical distinctness whole-set pre-check.

A deterministic, read-only accessibility check. CT3 computes the CIE76
deltaE76 Euclidean Lab distance between every i<j pair of committed
``colors.data_colors`` entries and compares the MINIMUM against the
token-declared ``accessibility.min_categorical_deltae`` floor. A collapse
below the floor is an ERROR naming both hexes and the computed distance; at
or above the floor is clean.

This is a normal-vision near-collapse guard (two swatches so close a sighted
viewer cannot tell them apart), NOT a colorblind-safe claim -- CVD
distinguishability stays an OPEN human seam (Principle V).

DECLARED-floor-only (Principle V -- the floor key IS the opt-in signal): a
tokens file with `colors.data_colors` but no `accessibility.min_categorical_
deltae` has not opted in, and CT3 silently skips it (NOT an error) so it
stays clean on main until an owner declares a floor.

NOT a fabricated confidence score (hard rule #9): the distance is
deterministic arithmetic on committed hexes, a pass/fail categorical test
against a declared threshold. Read-only: parses committed YAML, renders no
pixel, opens no DB, writes nothing. Generic: field names only, no tenant/
brand literal (Principle VII).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..color import delta_e76
from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "CT3"

_TOKENS_SUFFIX = "-design-tokens.yaml"
_TOKENS_BASENAMES = ("tokens.yaml",)


def _iter_tokens_files(ctx: RuleContext) -> list[str]:
    out = []
    for p in ctx.tracked_files:
        if is_test_path(p):
            continue
        base = p.rsplit("/", 1)[-1]
        if p.endswith(_TOKENS_SUFFIX) or base in _TOKENS_BASENAMES:
            out.append(p)
    return out


def _load_yaml(path: Path) -> tuple[Any, str | None]:
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope (B1/B3)

    try:
        with path.open(encoding="utf-8-sig") as fh:
            return yaml.safe_load(fh), None
    except (OSError, yaml.YAMLError) as exc:
        return None, exc.__class__.__name__


def _min_pair(data_colors: list[str]) -> tuple[float, str, str] | None:
    n = len(data_colors)
    if n < 2:
        return None
    best = float("inf")
    best_pair = ("", "")
    for i in range(n):
        for j in range(i + 1, n):
            try:
                d = delta_e76(data_colors[i], data_colors[j])
            except ValueError:
                continue
            if d < best:
                best = d
                best_pair = (data_colors[i], data_colors[j])
    if best == float("inf"):
        return None
    return best, best_pair[0], best_pair[1]


def _check_tokens(rel: str, doc: Any) -> Iterable[Finding]:
    colors = doc.get("colors", {}) if isinstance(doc, dict) else {}
    data_colors = colors.get("data_colors")
    access = doc.get("accessibility", {}) if isinstance(doc, dict) else {}
    floor = access.get("min_categorical_deltae")
    if not isinstance(data_colors, list) or floor is None:
        return  # not opted in -- nothing declared to check (Principle V)
    try:
        floor_f = float(floor)
    except (TypeError, ValueError):
        yield Finding(
            RULE_ID,
            Severity.ERROR,
            "accessibility.min_categorical_deltae is declared but not a "
            "parseable number; categorical distinctness cannot be verified",
            f"{rel}#/accessibility/min_categorical_deltae",
        )
        return
    result = _min_pair(data_colors)
    if result is None:
        return
    dist, a, b = result
    if dist < floor_f:
        yield Finding(
            RULE_ID,
            Severity.ERROR,
            f"data_colors {a!r} and {b!r} are {dist:.2f} dE76 apart, below "
            f"the declared floor {floor_f:g} dE76 -- normal-vision "
            f"near-collapse",
            f"{rel}#/colors/data_colors",
        )


@register(
    RULE_ID,
    "Categorical data_colors entries meet the declared whole-set deltaE76 distinctness floor",
)
def check_categorical_distinctness(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in _iter_tokens_files(ctx):
        doc, err = _load_yaml(ctx.repo_root / rel)
        if err is not None:
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"design-tokens file could not be parsed ({err}); "
                    f"categorical distinctness cannot be verified",
                    f"{rel}#/",
                )
            )
            continue
        findings.extend(_check_tokens(rel, doc))
    return findings
```

Wire the import in `src/seshat/rules/__init__.py` (insert alphabetically between `design_background` and `design_contrast`):

```python
    design_background,
    design_categorical_distinctness,
    design_contrast,
```

and in `__all__` (same alphabetical slot):

```python
    "design_background",
    "design_categorical_distinctness",
    "design_contrast",
```

- [ ] 4. Run the new rule tests:
```
pytest tests/unit/test_design_categorical_distinctness.py -v
```
Expected PASS: all 6 tests green.

- [ ] 5. Add `"CT3"` to `EXPECTED_RULE_IDS` in `tests/unit/test_rules_wiring.py`, right after the existing `"CT1"` entry:

```python
        "CT1",  # contrast: token text/background pairs meet the declared WCAG floor
        "CT3",  # categorical distinctness: whole-set data_colors dE76 floor (missing key -> skip)
```

Run:
```
pytest tests/unit/test_rules_wiring.py::test_registered_rule_ids_match_expected_set -v
```
Expected PASS: registered ids now include `CT3` and match `EXPECTED_RULE_IDS` exactly.

- [ ] 6. Add the severity-posture fixture. In `src/seshat/severity_posture.py`, add near `_YAML_CT1`:

```python
# data_colors declared without a min_categorical_deltae floor -> CT3 opt-in
# absent -> silent skip, <no-finding> (Principle V: floor key IS the opt-in).
_YAML_CT3 = "colors:\n  data_colors:\n    - '#2FB6C4'\n    - '#12263A'\n"
```

Add the fixture entry in `_RULE_FIXTURES`, right after the `"CT1"` entry:

```python
    "CT1": _Fixture(files=(("design/tokens/demo-design-tokens.yaml", _YAML_CT1),)),
    "CT3": _Fixture(files=(("design/tokens/demo-design-tokens.yaml", _YAML_CT3),)),
```

Regenerate and inspect the CT3 entry:
```
retail severity-posture --repo .
python -c "import json; d=json.load(open('docs/rules/severity-posture.json')); print(d['CT3'])"
```
Expected output: `['<no-finding>']` (the fixture has `data_colors` but no `min_categorical_deltae`, so CT3 silently skips it -- confirming the emits-on-main gate before landing).

- [ ] 7. Regenerate the rules manifest and read the new authoritative count:
```
retail manifest --repo .
python -c "import json; d=json.load(open('docs/rules/rules-manifest.json')); print(len(d))"
```
Read the integer that prints (call it `N`). Do NOT hardcode a value -- CT2/DL8 may land before or after this task, so use whatever `len()` actually prints.

- [ ] 8. Update `docs/glossary.md`. Edit the rule-count line and the CT family row to reflect the real `N` from step 7 and to list CT3.

Rule-count line (replace `67` with the real printed `N`; family list unchanged -- CT already exists):
```
> **Currently N rules in 23 families** (S, D, C, R, RS, G, P, A, B, PP, SC, DF, SL, AL, AD, AQ, CB, DL, CT, DR, AP, SF, HR).
```

CT row -- append the CT3 clause after the CT1 clause:
```
| **CT** | contrast / accessibility | `CT1` token text/background color pairs meet the token-declared WCAG contrast floor (deterministic sRGB luminance ratio, pass/fail against `accessibility.min_text_contrast_ratio`, never a score) - `CT3` categorical `data_colors` entries meet the token-declared whole-set deltaE76 (CIE76) distinctness floor (`accessibility.min_categorical_deltae`); a normal-vision near-collapse guard only, NOT a colorblind-safe claim; a tokens file with `data_colors` but no declared floor silently skips (opt-in, never inferred) |
```

- [ ] 9. Update `docs/quality/rule-count-claims.yaml` `anchor` + `claimed-count` to the same `N` (both must read identically to the glossary sentence, byte-for-byte, or SC2 ERRORs):

```yaml
    anchor: "Currently N rules in 23 families"
    claimed-count: N
```

- [ ] 10. Run the glossary/count/manifest snapshot tests together:
```
pytest tests/unit/test_glossary_rule_table.py tests/unit/test_rules_manifest_snapshot.py -v
```
Expected PASS: `test_glossary_rule_table.py` finds `CT3` listed; the manifest snapshot passes against the regenerated file.

- [ ] 11. Run `retail check` locally to confirm CT3, SC2, and SC1 are all clean (no self-inflicted findings from the doc edits):
```
retail check
```
Expected: no ERROR findings for `CT3`, `SC1`, `SC2`, `DL3` introduced by this change.

- [ ] 12. Run the full unit suite and formatting/lint gates:
```
ruff format --check src/seshat/rules/design_categorical_distinctness.py src/seshat/severity_posture.py tests/unit/test_design_categorical_distinctness.py tests/unit/test_rules_wiring.py
ruff check src/seshat/rules/design_categorical_distinctness.py src/seshat/rules/__init__.py src/seshat/severity_posture.py tests/unit/test_design_categorical_distinctness.py tests/unit/test_rules_wiring.py
pytest -m unit -x -q
```
Expected PASS: clean format/lint, full unit suite green.

**OWNER STOP:** Before committing, present the regenerated `N` (rule count), the new CT3 glossary row wording, and the `<no-finding>` severity-posture confirmation for both committed token files. This is the point where a wrong `N` would silently corrupt SC2 forever if committed. Halt only if `N` looks inconsistent with the other in-flight CT2/DL8 sections' expected counts; otherwise proceed to commit.

- [ ] 13. Commit:
```
git add src/seshat/rules/design_categorical_distinctness.py src/seshat/rules/__init__.py tests/unit/test_design_categorical_distinctness.py tests/unit/test_rules_wiring.py src/seshat/severity_posture.py docs/rules/rules-manifest.json docs/rules/severity-posture.json docs/glossary.md docs/quality/rule-count-claims.yaml
git commit -m "feat: CT3 -- categorical distinctness whole-set governance rule (dE76 floor, opt-in silent-skip)"
```

---

### Task 12: Idea 1 -- adjacent ramp deltaE floor, standalone self-check (CT2 part A)

**Files:**
- Modify: `src/seshat/theme_gen.py` -- add `check_ramp_deltae_or_raise(palette, floor) -> None` near `check_contrast_or_raise`; NOT called from `_validate_and_collect()` yet (that wait is Tasks 14-15).
- Modify: `tests/unit/test_theme_gen.py` -- new test functions using the existing `DARK` dict / `_seed()` helper.

**Interfaces:**
- Consumes: `retail.color.delta_e76(a: str, b: str) -> float` (Phase 0; already imported into `theme_gen` by Task 10 -- do NOT re-add the import). Consumes `palette["colors"]["data_colors"]` (a `list[str]` of `#RRGGBB`, produced by `build_palette`).
- Produces: `check_ramp_deltae_or_raise(palette: dict, floor: float) -> None` -- iterates `zip(dc, dc[1:])` over `palette["colors"]["data_colors"]`; raises `ThemeGenError` naming both offending hexes and the computed deltaE if any adjacent pair's `delta_e76` is below `floor`; returns `None` silently otherwise. `floor` is a required positional/keyword param -- no module-level default yet (the default is the OWNER-ratified constant, added in Task 15).

Note: this corrects a design-doc drafting slip -- the palette key is `palette["colors"]["data_colors"]`, not `palette["data_colors"]`. Idea 3's self-check (Task 10) already uses the correct nested path; this task matches it.

Steps:

- [ ] 1. Write the failing test. Add to `tests/unit/test_theme_gen.py`:
```python
def test_check_ramp_deltae_raises_below_floor() -> None:
    from retail.theme_gen import (
        ThemeGenError,
        build_palette,
        check_ramp_deltae_or_raise,
    )

    palette = build_palette(
        _seed(data_colors=("#336699", "#346699"))
    )  # near-identical adjacent pair
    with pytest.raises(ThemeGenError, match="deltaE76"):
        check_ramp_deltae_or_raise(palette, floor=10.0)


def test_check_ramp_deltae_names_both_hexes() -> None:
    from retail.theme_gen import (
        ThemeGenError,
        build_palette,
        check_ramp_deltae_or_raise,
    )

    palette = build_palette(_seed(data_colors=("#336699", "#346699")))
    with pytest.raises(ThemeGenError) as exc_info:
        check_ramp_deltae_or_raise(palette, floor=10.0)
    assert "#336699" in str(exc_info.value)
    assert "#346699" in str(exc_info.value)


def test_check_ramp_deltae_passes_at_or_above_floor() -> None:
    from retail.theme_gen import build_palette, check_ramp_deltae_or_raise

    palette = build_palette(_seed(data_colors=("#000000", "#FFFFFF", "#000000")))
    check_ramp_deltae_or_raise(palette, floor=10.0)  # no raise -- deltaE ~= 100 each hop


def test_check_ramp_deltae_floor_is_a_real_param() -> None:
    from retail.theme_gen import build_palette, check_ramp_deltae_or_raise

    palette = build_palette(_seed(data_colors=("#336699", "#346699")))
    check_ramp_deltae_or_raise(palette, floor=0.5)  # low floor -- same pair now passes
```

- [ ] 2. Run it and confirm the expected failure:
```
pytest tests/unit/test_theme_gen.py::test_check_ramp_deltae_raises_below_floor -v
```
Expected FAIL reason: `ImportError: cannot import name 'check_ramp_deltae_or_raise' from 'retail.theme_gen'`.

- [ ] 3. Minimal implementation. `delta_e76` is already imported (Task 10). Add the function immediately after `check_contrast_or_raise`:
```python
def check_ramp_deltae_or_raise(palette: dict, floor: float) -> None:
    """Raise if any two ADJACENT data_colors entries are near-collapsed.

    Deterministic CIE76 (delta_e76) distance on adjacent ramp/data_colors
    pairs only -- NOT a colorblind-safe / whole-set claim (that is CT3's
    idea). ``floor`` is caller-supplied; there is no built-in default here.
    """
    dc = palette["colors"]["data_colors"]
    for a, b in zip(dc, dc[1:]):
        d = delta_e76(a, b)
        if d < floor:
            raise ThemeGenError(
                f"adjacent data_colors {a!r} and {b!r} are too close "
                f"(deltaE76 {d:.2f} < floor {floor:g}) -- near-collapse risk"
            )
```

- [ ] 4. Run tests to confirm PASS:
```
pytest tests/unit/test_theme_gen.py -k check_ramp_deltae -v
```
Expected: all 4 new tests PASS.

- [ ] 5. Commit:
```
git add src/seshat/theme_gen.py tests/unit/test_theme_gen.py
git commit -m "feat: standalone check_ramp_deltae_or_raise self-check (CT2 prep, unwired)"
```

---

### Task 13: Idea 1 -- CT2 static rule, full wiring

**Files:**
- Create: `src/seshat/rules/design_ramp_deltae.py` (mirrors `src/seshat/rules/design_contrast.py` shape).
- Create: `tests/unit/test_design_ramp_deltae.py`.
- Modify: `src/seshat/rules/__init__.py` -- add `design_ramp_deltae` to the `from . import (...)` tuple (alphabetically between `design_grid_closure` and `design_review_evidence`) AND to `__all__` (same slot).
- Modify: `tests/unit/test_rules_wiring.py` -- add `"CT2"` to `EXPECTED_RULE_IDS` (near the existing `"CT1"`/`"CT3"`).
- Modify: `src/seshat/severity_posture.py` -- add `"CT2": _Fixture()` to `_RULE_FIXTURES` (near `"CT1"`); no committed tokens file declares `min_adjacent_delta_e`, so CT2 is `<no-finding>` everywhere.
- Regenerate: `docs/rules/rules-manifest.json` via `retail manifest`; `docs/rules/severity-posture.json` via `retail severity-posture`.
- Modify: `docs/glossary.md` -- CT row gets a new clause for `CT2`; rule-count line.
- Modify: `docs/quality/rule-count-claims.yaml` -- `anchor` + `claimed-count`, synced to the regenerated manifest length.

**Interfaces:**
- Consumes: `Finding`, `RuleContext`, `Severity`, `is_test_path` from `..core`; `register` from `..registry`; `delta_e76` from `..color`. Reuses the `_iter_tokens_files` / `_parse_floor` / `_load_yaml` pattern from `design_contrast.py` (copy, do not import private helpers cross-module).
- Produces: `RULE_ID = "CT2"`; `@register(RULE_ID, "Adjacent data_colors/ramp entries clear the declared deltaE76 floor")` decorating `check_ramp_deltae(ctx: RuleContext) -> Iterable[Finding]`.

Steps:

- [ ] 1. Write the failing test. Create `tests/unit/test_design_ramp_deltae.py`:
```python
"""Unit tests for CT2 (adjacent ramp deltaE76 floor)."""

from __future__ import annotations

import pytest

from retail.core import RuleContext, Severity
from retail.rules.design_ramp_deltae import RULE_ID, check_ramp_deltae

pytestmark = pytest.mark.unit

_TOKENS_DECLARED = """
meta:
  name: "t"
colors:
  data_colors:
    - "#336699"
    - "#346699"
accessibility:
  min_adjacent_delta_e: 10.0
"""

_TOKENS_MISSING_KEY = """
meta:
  name: "t"
colors:
  data_colors:
    - "#336699"
    - "#346699"
accessibility:
  min_text_contrast_ratio: "4.5:1"
"""


def test_ct2_flags_near_collapsed_pair_when_floor_declared(tmp_path) -> None:
    p = tmp_path / "x-design-tokens.yaml"
    p.write_text(_TOKENS_DECLARED, encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("x-design-tokens.yaml",))
    findings = list(check_ramp_deltae(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == RULE_ID
    assert findings[0].severity == Severity.ERROR
    assert "#336699" in findings[0].message
    assert "#346699" in findings[0].message


def test_ct2_missing_declared_floor_is_silent_skip(tmp_path) -> None:
    p = tmp_path / "x-design-tokens.yaml"
    p.write_text(_TOKENS_MISSING_KEY, encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("x-design-tokens.yaml",))
    findings = list(check_ramp_deltae(ctx))
    assert findings == []
```
(Match `RuleContext`'s real constructor -- if it differs, read `src/seshat/core.py`'s `RuleContext` definition first and adjust the `RuleContext(...)` calls; keep the two test bodies' intent unchanged.)

- [ ] 2. Run it and confirm the expected failure:
```
pytest tests/unit/test_design_ramp_deltae.py -v
```
Expected FAIL reason: `ModuleNotFoundError: No module named 'retail.rules.design_ramp_deltae'`.

- [ ] 3. Minimal implementation. Create `src/seshat/rules/design_ramp_deltae.py`:
```python
"""Design-lint rule CT2: adjacent data_colors/ramp deltaE76 near-collapse guard.

A deterministic, read-only accessibility check. CT2 computes the CIE76 Lab
distance (delta_e76) between each ADJACENT pair in a token file's declared
``colors.data_colors`` ramp and compares it against the token-declared floor
``accessibility.min_adjacent_delta_e``. A pair below the floor is an ERROR
naming both hexes and the computed distance.

This is a near-collapse guard, NOT a colorblind-safe / whole-set claim (that
is CT3's job) -- adjacent pairs only, mirroring the ordering theme dataColors
compiles from.

DECLARED floor only (Principle V): a tokens file with no
``accessibility.min_adjacent_delta_e`` key has nothing to check -- silent
skip, never ERROR (mirrors CT1's missing-declaration branch).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..color import delta_e76
from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "CT2"

_TOKENS_SUFFIX = "-design-tokens.yaml"
_TOKENS_BASENAMES = ("tokens.yaml",)


def _iter_tokens_files(ctx: RuleContext) -> list[str]:
    out = []
    for p in ctx.tracked_files:
        if is_test_path(p):
            continue
        base = p.rsplit("/", 1)[-1]
        if p.endswith(_TOKENS_SUFFIX) or base in _TOKENS_BASENAMES:
            out.append(p)
    return out


def _parse_floor(raw: Any) -> float | None:
    if isinstance(raw, (int, float)):
        return float(raw)
    return None


def _load_yaml(path: Path) -> tuple[Any, str | None]:
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope (B1/B3)

    try:
        with path.open(encoding="utf-8-sig") as fh:
            return yaml.safe_load(fh), None
    except (OSError, yaml.YAMLError) as exc:
        return None, exc.__class__.__name__


def _check_tokens(rel: str, doc: Any) -> Iterable[Finding]:
    colors = doc.get("colors", {}) if isinstance(doc, dict) else {}
    data_colors = colors.get("data_colors")
    if not isinstance(data_colors, list) or len(data_colors) < 2:
        return  # nothing declared to check
    access = doc.get("accessibility", {}) if isinstance(doc, dict) else {}
    floor = _parse_floor(access.get("min_adjacent_delta_e"))
    if floor is None:
        return  # no declared floor -- silent skip, not an ERROR (Principle V)
    for a, b in zip(data_colors, data_colors[1:]):
        try:
            d = delta_e76(a, b)
        except ValueError:
            yield Finding(
                RULE_ID,
                Severity.ERROR,
                f"data_colors entry {a!r} or {b!r} is not a valid #RRGGBB "
                f"hex; adjacent deltaE76 could not be computed",
                f"{rel}#/colors/data_colors",
            )
            continue
        if d < floor:
            yield Finding(
                RULE_ID,
                Severity.ERROR,
                f"adjacent data_colors {a!r} and {b!r} have deltaE76 "
                f"{d:.2f}, below the declared floor {floor:g}",
                f"{rel}#/colors/data_colors",
            )


@register(
    RULE_ID,
    "Adjacent data_colors/ramp entries clear the declared deltaE76 floor",
)
def check_ramp_deltae(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in _iter_tokens_files(ctx):
        doc, err = _load_yaml(ctx.repo_root / rel)
        if err is not None:
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"could not parse {rel} as YAML ({err})",
                    rel,
                )
            )
            continue
        findings.extend(_check_tokens(rel, doc))
    return findings
```
Add the import wiring in `src/seshat/rules/__init__.py`:
```python
    design_grid_closure,
    design_ramp_deltae,
    design_review_evidence,
```
```python
    "design_grid_closure",
    "design_ramp_deltae",
    "design_review_evidence",
```

- [ ] 4. Run tests to confirm PASS:
```
pytest tests/unit/test_design_ramp_deltae.py -v
```
Expected: both tests PASS.

- [ ] 5. Add `"CT2"` to `tests/unit/test_rules_wiring.py`'s `EXPECTED_RULE_IDS`, next to `"CT1"`:
```python
        "CT1",  # contrast: token text/background pairs meet the declared WCAG floor
        "CT2",  # contrast: adjacent data_colors/ramp entries clear the declared deltaE76 floor
        "CT3",  # categorical distinctness: whole-set data_colors dE76 floor (missing key -> skip)
```
Run:
```
pytest tests/unit/test_rules_wiring.py -v
```
Expected PASS.

- [ ] 6. Verify emits-on-main is clean (neither committed tokens file declares `min_adjacent_delta_e`, so this must show zero findings):
```
python -m seshat.cli check --rules CT2
```
Expected: exit 0, zero CT2 findings on both `design/tokens/executive-dark-design-tokens.yaml` and `design/tokens/tower-retail-design-tokens.yaml`.

- [ ] 7. Regenerate the manifest and severity posture (never hand-edit their JSON):
```
retail manifest --repo .
```
Add a `"CT2": _Fixture()` entry to `_RULE_FIXTURES` in `src/seshat/severity_posture.py` (near `"CT1"`) -- an empty/default `_Fixture()` falls through to the no-finding marker:
```python
    "CT1": _Fixture(...),
    "CT2": _Fixture(),
```
```
retail severity-posture --repo .
```
Confirm the generated `docs/rules/severity-posture.json` has `"CT2": ["<no-finding>"]`.

- [ ] 8. Update the glossary and rule-count claim together. Read the regenerated count:
```
python -c "import json; print(len(json.load(open('docs/rules/rules-manifest.json'))))"
```
Use that printed integer `N` for both edits (do not hardcode). In `docs/glossary.md`, edit the rule-count line to `Currently N rules in 23 families` (family list unchanged -- `CT` already exists). Edit the `CT` row to append the CT2 clause:
```
- `CT2` adjacent `data_colors`/ramp entries meet the token-declared deltaE76 near-collapse floor (deterministic CIE76 Lab distance, pass/fail against `accessibility.min_adjacent_delta_e`, missing key -> silent skip, never a score)
```
In `docs/quality/rule-count-claims.yaml`, edit `anchor` + `claimed-count` so both read the same `N`.

- [ ] 9. Run the full cross-cutting verification:
```
pytest tests/unit/test_rules_manifest_snapshot.py tests/unit/test_glossary_rule_table.py -v
ruff format --check src/seshat/rules/design_ramp_deltae.py tests/unit/test_design_ramp_deltae.py
ruff check src/seshat/rules/design_ramp_deltae.py tests/unit/test_design_ramp_deltae.py
pytest -m unit -x -q
```
Expected: all PASS, no formatting/lint diffs, full unit suite green.

- [ ] 10. Commit:
```
git add src/seshat/rules/design_ramp_deltae.py tests/unit/test_design_ramp_deltae.py \
        src/seshat/rules/__init__.py tests/unit/test_rules_wiring.py \
        src/seshat/severity_posture.py docs/rules/rules-manifest.json \
        docs/rules/severity-posture.json docs/glossary.md \
        docs/quality/rule-count-claims.yaml
git commit -m "feat: CT2 static rule -- adjacent data_colors deltaE76 near-collapse guard"
```

---

### Task 14: Idea 1 -- re-derive and ratify the deltaE floor constant (OWNER STOP)

**Files:**
- No repo file changes. This task produces a number for the owner, not code (use `python -c`, no committed scratch file).

**Interfaces:**
- Consumes: `retail.theme_gen.derive_ramp(accent: str, n: int = 6) -> tuple[str, ...]` (existing) and `retail.color.delta_e76(a: str, b: str) -> float` (Phase 0).
- Produces: a printed report handed to the OWNER (nothing importable).

Steps:

- [ ] 1. Compute `delta_e76` on real `derive_ramp` output across the shipping accents used in committed tokens/tests, including `#2E7D5B` and the `executive-dark` accent `#2FB6C4`:
```
python -c "
from retail.theme_gen import derive_ramp
from retail.color import delta_e76

accents = ['#2E7D5B', '#2FB6C4', '#1F4E79', '#B5832A']
for accent in accents:
    ramp = derive_ramp(accent, n=6)
    pairs = list(zip(ramp, ramp[1:]))
    deltas = [delta_e76(a, b) for a, b in pairs]
    print(accent, 'ramp=', ramp)
    print(accent, 'adjacent deltaE76=', [round(d, 2) for d in deltas], 'min=', round(min(deltas), 2))
"
```

- [ ] 2. Also compute `delta_e76` across the two COMMITTED `data_colors` lists directly, since `--data-colors` lets a caller supply a hand-picked list that bypasses `derive_ramp`:
```
python -c "
from retail.color import delta_e76
import yaml

for path in ['design/tokens/executive-dark-design-tokens.yaml', 'design/tokens/tower-retail-design-tokens.yaml']:
    doc = yaml.safe_load(open(path, encoding='utf-8-sig'))
    dc = doc['colors']['data_colors']
    pairs = list(zip(dc, dc[1:]))
    deltas = [round(delta_e76(a, b), 2) for a, b in pairs]
    print(path, deltas, 'min=', min(deltas))
"
```

**OWNER STOP:** present both tables verbatim to the owner (accent-derived ramps AND the two committed `data_colors` lists, each adjacent-pair deltaE76 and the min). State explicitly: "proposed floor `10.0` is empirically wrong -- `#2E7D5B`'s 6-step `derive_ramp` output has min adjacent deltaE76 = 9.13, which is below 10.0 and would make `generate()` hard-fail a shipping default. Candidates that clear all computed minimums while still catching a genuinely near-identical pair (e.g. `#336699`/`#346699`, deltaE76 ~= 0.6) are in the ~7-8 range." Ask the owner to ratify one exact float value as `MIN_ADJACENT_DELTAE`. Do NOT proceed to Task 15 until the owner responds with a number. Record the owner's ratified value and the date in the PR description verbatim (do not silently pick a value yourself).

---

### Task 15: Idea 1 -- wire the ratified floor into `generate()` (post-OWNER-STOP)

**Files:**
- Modify: `src/seshat/theme_gen.py` -- add `MIN_ADJACENT_DELTAE = <OWNER_RATIFIED_VALUE>` module constant near `AA_FLOOR`; call `check_ramp_deltae_or_raise(palette, MIN_ADJACENT_DELTAE)` inside `_validate_and_collect()` immediately after `check_categorical_distinctness_or_raise(palette)`.
- Modify: `tests/unit/test_theme_gen.py` -- add a `generate()`-level regression test proving the shipping default still passes end-to-end.

**Interfaces:**
- Consumes: `check_ramp_deltae_or_raise(palette, floor)` from Task 12; the OWNER-ratified float from Task 14.
- Produces: `generate()`'s signature is unchanged; its behavior now also refuses near-collapsed adjacent `data_colors` (including via `--data-colors`).

Steps:

- [ ] 1. Write the failing test (substitute the real ratified number before running; example assumes `7.5`):
```python
def test_generate_refuses_near_collapsed_data_colors(tmp_path: Path) -> None:
    from retail.theme_gen import ThemeGenError, generate

    seed = _seed(
        data_colors=(
            "#336699",
            "#346699",
            "#1F4E79",
            "#B5832A",
            "#2E7D5B",
            "#7A5C8E",
        )
    )
    with pytest.raises(ThemeGenError, match="deltaE76"):
        generate(seed, repo_root=tmp_path)


def test_generate_shipping_default_ramp_still_passes(tmp_path: Path) -> None:
    from retail.theme_gen import generate

    # data_colors=None -> build_palette derives via derive_ramp(accent); must
    # clear the ratified floor for every accent shipped in committed tokens.
    seed = _seed(accent="#2E7D5B", data_colors=None)
    written = generate(seed, repo_root=tmp_path)
    assert len(written) == 3
```

- [ ] 2. Run it and confirm the expected failure:
```
pytest tests/unit/test_theme_gen.py::test_generate_refuses_near_collapsed_data_colors -v
```
Expected FAIL reason: `Failed: DID NOT RAISE <class 'retail.theme_gen.ThemeGenError'>`.

- [ ] 3. Minimal implementation. Add the constant near `AA_FLOOR` (replace `7.5` with the real ratified value):
```python
MIN_ADJACENT_DELTAE = 7.5  # OWNER-ratified <DATE> -- replace with the real ratified value
```
Edit `_validate_and_collect()`:
```python
    check_contrast_or_raise(palette)
    check_font_floor_or_raise(seed)
    check_categorical_distinctness_or_raise(palette)
    check_ramp_deltae_or_raise(palette, MIN_ADJACENT_DELTAE)
    targets = _targets_for(seed, repo_root, palette)
```

- [ ] 4. Run tests to confirm PASS:
```
pytest tests/unit/test_theme_gen.py -v
```
Expected: full file passes, including both new tests and every pre-existing `test_generated_theme_is_dl1_clean`-style test (no regression on the default fixture).

- [ ] 5. Commit:
```
git add src/seshat/theme_gen.py tests/unit/test_theme_gen.py
git commit -m "feat: wire OWNER-ratified adjacent-ramp deltaE floor into generate()"
```

---

### Task 16: `derive_dark_seed` -- derive a dark `ThemeSeed` from a light one

**Files:**
- Modify: `src/seshat/theme_gen.py` (add near `_hex_to_hls`/`_hls_to_hex`, and after `derive_ramp`; update the `dataclasses` import at line 21)
- Modify: `tests/unit/test_theme_gen.py` (add a `LIGHT` fixture dict alongside `DARK`, and new tests)

**Interfaces:**
- Consumes: `ThemeSeed` (existing frozen dataclass), `_hex_to_hls(h: str) -> tuple[float, float, float]` (existing), `_hls_to_hex(h: float, lightness: float, s: float) -> str` (existing), `dataclasses.replace` (new import)
- Produces:
  - `_invert_lightness(hex_color: str) -> str` -- flips the L channel (`1.0 - L`), hue/saturation preserved.
  - `derive_dark_seed(light: ThemeSeed) -> ThemeSeed` -- raises `ThemeGenError` if `light.mode != "light"`; otherwise returns a new frozen `ThemeSeed` with `mode="dark"`, `name=f"{light.name}-dark"`, `background`/`text_primary`/`text_secondary`/`text_muted` lightness-inverted, `accent`/`data_colors`/`good`/`neutral`/`bad`/`title_font_pt`/`label_font_pt` passed through unchanged (via `dataclasses.replace`, so the two new font fields are preserved automatically).

Steps:

- [ ] 1. Write the failing test first. Add a `LIGHT` fixture (light background, dark text -- chosen so both the light seed and its derived dark seed clear the 4.5:1 AA floor) next to the existing `DARK` dict:

```python
LIGHT = dict(
    name="executive-light",
    mode="light",
    accent="#1B6E4F",
    background="#F5F7FA",
    text_primary="#1A2430",
    text_secondary="#3D4A59",
    text_muted="#5B6B7C",
    data_colors=None,
    good="#1F7A4D",
    neutral="#8A6D1D",
    bad="#A23A3A",
)


def _light_seed(**over) -> ThemeSeed:
    d = {**LIGHT, **over}
    return ThemeSeed(**d)


def test_derive_dark_seed_inverts_background_and_text_only() -> None:
    from retail.theme_gen import derive_dark_seed

    light = _light_seed()
    dark = derive_dark_seed(light)
    assert dark.mode == "dark"
    assert dark.name == "executive-light-dark"
    assert dark.background != light.background
    assert dark.text_primary != light.text_primary
    # everything else passes through unchanged
    assert dark.accent == light.accent
    assert dark.data_colors == light.data_colors
    assert dark.good == light.good
    assert dark.neutral == light.neutral
    assert dark.bad == light.bad


def test_derive_dark_seed_clears_contrast_floor(tmp_path: Path) -> None:
    from retail.theme_gen import build_palette, check_contrast_or_raise, derive_dark_seed

    dark = derive_dark_seed(_light_seed())
    palette = build_palette(dark)
    check_contrast_or_raise(palette)  # must not raise


def test_derive_dark_seed_rejects_non_light_input() -> None:
    from retail.theme_gen import derive_dark_seed

    with pytest.raises(ThemeGenError, match="mode"):
        derive_dark_seed(_seed())  # DARK fixture: mode="dark"
```

- [ ] 2. Run and confirm the expected failure:
```
pytest tests/unit/test_theme_gen.py::test_derive_dark_seed_inverts_background_and_text_only -v
```
Expected FAIL reason: `ImportError: cannot import name 'derive_dark_seed' from 'retail.theme_gen'`.

- [ ] 3. Minimal implementation. First widen the import at line 21:

```python
from dataclasses import dataclass, replace
```

Then add, after `derive_ramp`:

```python
def _invert_lightness(hex_color: str) -> str:
    """Flip the L channel (1.0 - L); hue and saturation unchanged."""
    h, lightness, s = _hex_to_hls(hex_color)
    return _hls_to_hex(h, 1.0 - lightness, s)


def derive_dark_seed(light: ThemeSeed) -> ThemeSeed:
    """Derive a dark-mode ThemeSeed from a light one by inverting bg/text
    lightness. Accent/data_colors/sentiment/fonts pass through unchanged --
    only the surface (background) and on-surface (text) roles invert.

    Refuses a non-light input up front: --pair on an already-dark seed would
    otherwise double-invert (light -> dark -> "dark" that is really light).
    """
    if light.mode != "light":
        raise ThemeGenError(
            f"derive_dark_seed requires mode='light', got {light.mode!r} -- "
            "refusing to double-invert an already-dark seed"
        )
    return replace(
        light,
        mode="dark",
        name=f"{light.name}-dark",
        background=_invert_lightness(light.background),
        text_primary=_invert_lightness(light.text_primary),
        text_secondary=_invert_lightness(light.text_secondary),
        text_muted=_invert_lightness(light.text_muted),
    )
```

- [ ] 4. Run tests:
```
pytest tests/unit/test_theme_gen.py -q
ruff format --check src/seshat/theme_gen.py tests/unit/test_theme_gen.py
ruff check src/seshat/theme_gen.py tests/unit/test_theme_gen.py
```
Expected PASS: all green, including the new derive-dark tests and the full pre-existing suite.

Note: if `test_derive_dark_seed_clears_contrast_floor` fails because the inverted dark palette does not clear 4.5:1, adjust the `LIGHT` fixture's `text_primary`/`background` hex values (keep them plausible light-mode colors) until both directions clear AA -- do not weaken `check_contrast_or_raise`.

- [ ] 5. Commit:
```
git add src/seshat/theme_gen.py tests/unit/test_theme_gen.py && git commit -m "feat: derive_dark_seed -- invert bg/text lightness for a light seed"
```

---

### Task 17: `generate_pair` + `--pair` CLI flag (all-or-nothing light/dark write)

**Files:**
- Modify: `src/seshat/theme_gen.py` (add after `generate()`; modify `theme_gen_main`)
- Modify: `src/seshat/cli/parser.py` (theme-gen subparser -- add `--pair` after `--force`)
- Modify: `tests/unit/test_theme_gen.py` (new tests using the `LIGHT`/`_light_seed` fixtures from Task 16)

**Interfaces:**
- Consumes: `_validate_and_collect(seed, repo_root, force) -> dict[Path, str]`, `_write_targets(targets) -> list[Path]`, `derive_dark_seed(light: ThemeSeed) -> ThemeSeed` (all from prior tasks)
- Produces:
  - `generate_pair(light: ThemeSeed, repo_root: Path, force: bool = False) -> tuple[list[Path], list[Path]]` -- validates the light seed, derives + validates the dark seed, and ONLY THEN writes both; returns `(light_written, dark_written)`. Raises `ThemeGenError` and writes NOTHING if either seed fails validation (AA contrast, font floor, distinctness, ramp deltaE, or file-collision) or if `light.mode != "light"` or `light.name` already ends with `"-dark"`.
  - CLI: `--pair` (`store_true`) on the `theme-gen` subparser; `theme_gen_main` branches on `args.pair` to call `generate_pair` instead of `generate`.

Steps:

- [ ] 1. Write the failing tests first:

```python
def test_generate_pair_writes_six_files(tmp_path: Path) -> None:
    from retail.theme_gen import generate_pair

    light_written, dark_written = generate_pair(_light_seed(), repo_root=tmp_path)
    assert len(light_written) == 3
    assert len(dark_written) == 3
    dark_rels = sorted(
        str(p.relative_to(tmp_path)).replace("\\", "/") for p in dark_written
    )
    assert dark_rels == [
        "design/tokens/executive-light-dark-design-tokens.yaml",
        "themes/executive-light-dark.theme-spec.md",
        "themes/executive-light-dark.theme.json",
    ]


def test_generate_pair_rejects_dark_mode_input(tmp_path: Path) -> None:
    from retail.theme_gen import generate_pair

    with pytest.raises(ThemeGenError, match="mode"):
        generate_pair(_seed(), repo_root=tmp_path)  # DARK fixture: mode="dark"
    assert list(tmp_path.rglob("*.theme.json")) == []


def test_generate_pair_rejects_name_already_ending_in_dark(tmp_path: Path) -> None:
    from retail.theme_gen import generate_pair

    with pytest.raises(ThemeGenError, match="dark"):
        generate_pair(_light_seed(name="foo-dark"), repo_root=tmp_path)
    assert list(tmp_path.rglob("*.theme.json")) == []


def test_generate_pair_writes_nothing_if_dark_side_fails_aa(tmp_path: Path) -> None:
    from retail.theme_gen import generate_pair

    # text_muted picked so the LIGHT side clears AA but the lightness-inverted
    # DARK side (1.0 - L) collapses contrast against the inverted background.
    light = _light_seed(text_muted="#EDEFF2")
    with pytest.raises(ThemeGenError, match="contrast"):
        generate_pair(light, repo_root=tmp_path)
    assert list(tmp_path.rglob("*.theme.json")) == []
    assert list(tmp_path.rglob("*.theme-spec.md")) == []
```

- [ ] 2. Run and confirm the expected failure:
```
pytest tests/unit/test_theme_gen.py::test_generate_pair_writes_six_files -v
```
Expected FAIL reason: `ImportError: cannot import name 'generate_pair' from 'retail.theme_gen'`.

- [ ] 3. Minimal implementation. Add after `generate()` in `theme_gen.py`:

```python
def generate_pair(
    light: ThemeSeed, repo_root: Path, force: bool = False
) -> tuple[list[Path], list[Path]]:
    """Derive a dark seed from ``light`` and write both, all-or-nothing.

    Both seeds are fully validated (contrast + font floor + distinctness +
    ramp deltaE + collision) BEFORE either is written, so a dark-side failure
    or a file collision on either seed leaves the working tree untouched --
    never a half-written pair.
    """
    if light.mode != "light":
        raise ThemeGenError(
            f"--pair requires a light-mode seed, got mode={light.mode!r} -- "
            "refusing to double-invert an already-dark seed"
        )
    if light.name.endswith("-dark"):
        raise ThemeGenError(
            f"--pair derives '{light.name}-dark' from --name -- a name "
            f"already ending in '-dark' ({light.name!r}) would collide"
        )
    light_targets = _validate_and_collect(light, repo_root, force)
    dark = derive_dark_seed(light)
    dark_targets = _validate_and_collect(dark, repo_root, force)
    light_written = _write_targets(light_targets)
    dark_written = _write_targets(dark_targets)
    return light_written, dark_written
```

Then update `theme_gen_main` to branch on `args.pair`. Replace the single call site inside the `try:` block:

```python
    try:
        if args.pair:
            light_written, dark_written = generate_pair(
                seed, Path(args.repo), force=args.force
            )
            written = light_written + dark_written
        else:
            written = generate(seed, Path(args.repo), force=args.force)
    except ThemeGenError as exc:
        print(f"theme-gen: {exc}", file=sys.stderr)
        return 2
```

Add the CLI flag in `cli/parser.py` right after `--force`:

```python
    themegen.add_argument(
        "--pair",
        action="store_true",
        help="also derive and write a dark-mode pair from a light --mode seed",
    )
```

- [ ] 4. Run tests:
```
pytest tests/unit/test_theme_gen.py -q
pytest tests/unit -k theme -q
ruff format --check src/seshat/theme_gen.py src/seshat/cli/parser.py tests/unit/test_theme_gen.py
ruff check src/seshat/theme_gen.py src/seshat/cli/parser.py tests/unit/test_theme_gen.py
```
Expected PASS: all green, including the four new `generate_pair` tests, all prior theme_gen tests unaffected, and existing CLI parser tests still passing since `--pair` is additive/optional.

**OWNER STOP:** none required for this task's code (a pure structural/CLI addition with no ratified constants). Present the finished `--pair` behavior to the OWNER before wider rollout: confirm the `-dark`-suffix guard (a name-based heuristic, not in the design doc's line-250 test list) is an acceptable interpretation of "reject conflicting derived names" versus leaving it unguarded. This is a UX judgment call, not a gated fact -- flag it in the PR description rather than blocking the commit.

- [ ] 5. Commit:
```
git add src/seshat/theme_gen.py src/seshat/cli/parser.py tests/unit/test_theme_gen.py && git commit -m "feat: generate_pair + --pair -- all-or-nothing light/dark theme write"
```

---

### Task 18: Idea 2 -- gated composite-transparency contrast check (standalone, unwired)

**Files:**
- Modify: `src/seshat/theme_gen.py` -- add `check_composite_contrast_or_raise(palette: dict, floor: float = AA_FLOOR) -> None` near `check_contrast_or_raise`, importing `composite_over` alongside the existing color imports. **Do NOT call it from `_validate_and_collect()` / `generate()`** -- no alpha fields exist on `ThemeSeed`, so wiring would be dead code per the design doc's OWNER STOP.
- Modify: `tests/unit/test_theme_gen.py` -- add `check_composite_contrast_or_raise` tests.

**Interfaces:**
- Consumes: `retail.color.contrast_ratio(a: str, b: str) -> float` (existing); `retail.color.composite_over(fg: str, bg: str, transparency_pct: float) -> str` (Phase 0, Task 2).
- Produces: `retail.theme_gen.check_composite_contrast_or_raise(palette: dict, floor: float = AA_FLOOR) -> None`. Raises `ThemeGenError` (never a bare `ValueError`/traceback) if the composited foreground-over-background fails the floor. Returns `None` silently if `palette` carries no `transparency` role (today: always, since no alpha fields exist).

Steps:

- [ ] 1. Write the failing test for `check_composite_contrast_or_raise`:

```python
from retail.theme_gen import check_composite_contrast_or_raise  # extend the import block


def test_composite_contrast_raises_below_floor() -> None:
    palette = build_palette(_seed())
    bg = palette["colors"]["background"]
    palette_with_weak_fg = {
        **palette,
        "transparency": {"overlay": {"fg": bg, "transparency_pct": 0.0}},
    }
    with pytest.raises(ThemeGenError, match="composite"):
        check_composite_contrast_or_raise(palette_with_weak_fg, floor=4.5)


def test_composite_contrast_passes_at_or_above_floor() -> None:
    palette = build_palette(_seed())
    bg = palette["colors"]["background"]
    fg = palette["colors"]["text"]["primary"]
    palette_with_strong_fg = {
        **palette,
        "transparency": {"overlay": {"fg": fg, "transparency_pct": 0.0}},
    }
    check_composite_contrast_or_raise(palette_with_strong_fg, floor=4.5)  # no raise


def test_composite_contrast_no_transparency_role_is_noop() -> None:
    # No alpha/transparency fields exist on ThemeSeed/build_palette today,
    # so the check has nothing declared to composite against and must be a
    # silent no-op -- never a fabricated pass, never an error on absence.
    palette = build_palette(_seed())
    assert check_composite_contrast_or_raise(palette) is None
```

- [ ] 2. Run it, expect FAIL:
```
pytest tests/unit/test_theme_gen.py -v -k composite_contrast
```
Expected failure reason: `ImportError: cannot import name 'check_composite_contrast_or_raise' from 'retail.theme_gen'`.

- [ ] 3. Minimal implementation. Update the color import to add `composite_over`:

```python
from .color import composite_over, contrast_ratio, delta_e76, format_pt, is_valid_hex
```

Add after `check_contrast_or_raise`:

```python
def check_composite_contrast_or_raise(palette: dict, floor: float = AA_FLOOR) -> None:
    """Refuse to proceed if a declared transparency role fails AA once composited.

    STANDALONE and UNWIRED: no `generate()` call site invokes this today.
    ``ThemeSeed``/``build_palette`` carry zero alpha/transparency fields, so
    there is nothing declared to composite against -- this is a silent no-op
    until an OWNER-approved transparency-role schema lands on ``ThemeSeed``.
    Never fabricates a role or infers a transparency_pct from color proximity.
    """
    transparency = palette.get("transparency")
    if not isinstance(transparency, dict):
        return  # nothing declared to check
    bg = palette["colors"]["background"]
    for role, spec in transparency.items():
        fg = spec.get("fg")
        pct = spec.get("transparency_pct")
        if fg is None or pct is None:
            continue
        composited = composite_over(fg, bg, pct)
        ratio = contrast_ratio(composited, bg)
        if ratio < floor:
            raise ThemeGenError(
                f"composite contrast: transparency role {role!r} "
                f"({fg} at {pct:g}% over {bg}) composites to {composited}, "
                f"{ratio:.2f}:1 vs background, below the {floor:g}:1 AA "
                f"floor -- refusing (would fail CT1 once rendered)"
            )
```

- [ ] 4. Run tests, expect PASS:
```
pytest tests/unit/test_theme_gen.py -v -k composite_contrast
pytest tests/unit/test_color.py tests/unit/test_theme_gen.py -q
```
Expected: all listed tests pass; no regression in the full files.

- [ ] 5. Verify non-wiring and gate compliance:
```
grep -n "check_composite_contrast_or_raise" src/seshat/theme_gen.py
```
Expected: exactly one match (the `def` line) -- zero call sites inside `_validate_and_collect` / `generate` / `generate_pair`. If a second match appears, remove it; wiring is explicitly out of scope.
```
grep -rn "check_composite_contrast_or_raise" src/seshat/theme_compile.py src/seshat/cli/
```
Expected: no matches (not exposed via CLI, not called from `theme_compile.py`).

- [ ] 6. Run full quality gates:
```
ruff format --check src/seshat/theme_gen.py tests/unit/test_theme_gen.py
ruff check src/seshat/theme_gen.py tests/unit/test_theme_gen.py
pytest -m unit -x -q
```
Expected: clean format, no lint errors, full unit suite green.

**OWNER STOP:** Present to the OWNER: `check_composite_contrast_or_raise` and `composite_over` are built, unit-tested, and importable, but **not called from any generation or compile path** -- `ThemeSeed`/`build_palette` have zero alpha/transparency fields, so there is no schema yet describing what a "transparency role" is (which color field, what default `transparency_pct`, per-role or global) or how it round-trips through `design/tokens/*.yaml` and `themes/*.theme.json` (the `visualStyles` transparency key shape + sRGB-vs-linear blend space are also open). The build halts because wiring without that schema would either be dead code (current state, acceptable) or a self-invented schema decision the OWNER did not ratify (rule #9 / Principle V violation). Any composite-contrast evidence surfaced to a human stays **stdout-only** or, if ever added to `render_spec_md`, must be a `[ ]` OPEN checklist line -- **never `[x]`** -- until wiring is explicitly approved as its own follow-up.

- [ ] 7. Commit:
```
git add src/seshat/theme_gen.py tests/unit/test_theme_gen.py
git commit -m "feat: composite-transparency AA proof (idea 2) -- standalone, unwired"
```

---

### Task 19: Idea 6 -- DL8 sentiment 4->3 fidelity rule (inert shell, owner-gated map)

**Files:**
- Modify: `src/seshat/rules/design_theme_fidelity.py` (add second `@register` fn; existing `RULE_ID = "DL3"` / `check_theme_fidelity` untouched)
- Modify: `tests/unit/test_design_theme_fidelity.py` (add DL8 test cases; existing DL3 tests untouched)
- Create: `tests/fixtures/theme_fidelity/sentiment_map_faithful/tokens.yaml`, `.../theme.json`
- Create: `tests/fixtures/theme_fidelity/sentiment_map_drift/tokens.yaml`, `.../theme.json`
- Create: `tests/fixtures/theme_fidelity/sentiment_map_missing_key/tokens.yaml`, `.../theme.json`
- Create: `tests/fixtures/theme_fidelity/sentiment_map_malformed/tokens.yaml` (unparseable YAML), `.../theme.json`
- Reuse fixture: `tests/fixtures/theme_fidelity/sentiment_only_drift/tokens.yaml` (has `colors.sentiment`, no `meta.sentiment_map` -- the map-absent trip-wire)
- Modify: `tests/unit/test_rules_wiring.py` (`EXPECTED_RULE_IDS` += `"DL8"`, next to the `DL7` entry)
- Modify: `src/seshat/severity_posture.py` (`_RULE_FIXTURES` dict, alongside the `"DL3"` entry; new `_YAML_DL8_TOKENS` / `_JSON_DL8_THEME` constants near `_YAML_DL3_TOKENS`)
- Regenerate (never hand-edit): `docs/rules/rules-manifest.json`, `docs/rules/severity-posture.json`
- Modify: `docs/glossary.md` (DL row -- append ` - DL8 sentiment fidelity ...`; rule-count line)
- Modify: `docs/quality/rule-count-claims.yaml` (`anchor` + `claimed-count`, computed not hardcoded)
- NOT modified: `src/seshat/rules/__init__.py` (module already imported for DL3)

**Interfaces:**
- Consumes: `RuleContext`, `Finding`, `Severity` from `..core`; `register` from `..registry`; module-private `_iter_tokens_files(ctx) -> list[str]`, `_theme_rel_for(tokens_rel, tokens_doc, ctx) -> str | None`, `_load_yaml(path) -> tuple[Any, str | None]`, `_load_json(path) -> tuple[Any, str | None]` (all already defined in this module for DL3, reused as-is).
- Produces: `SENTIMENT_RULE_ID: str = "DL8"` (module-scope constant, separate from `RULE_ID = "DL3"`); `_sentiment_map_for(tokens_doc: Any) -> dict[str, str] | None`; `_reconcile_sentiment(tokens_rel: str, theme_rel: str, ctx: RuleContext) -> Iterable[Finding]`; `check_sentiment_fidelity(ctx: RuleContext) -> Iterable[Finding]` (the `@register("DL8", ...)` entry point).

Steps:

- [ ] 1. Write the failing tests. Add to `tests/unit/test_design_theme_fidelity.py`, after the existing DL3 tests:

```python
# --- DL8: sentiment 4->3 fidelity (opt-in, inert until owner declares the map) --

from retail.rules.design_theme_fidelity import (  # noqa: E402
    SENTIMENT_RULE_ID,
    check_sentiment_fidelity,
)


def test_sentiment_map_absent_is_zero_findings_refuse_to_invent() -> None:
    """No meta.sentiment_map -- DL8 must never guess a correspondence
    (Principle V). Reuses the DL3 sentiment-drift fixture, which has
    colors.sentiment but no map."""
    findings = list(
        check_sentiment_fidelity(
            _ctx("sentiment_only_drift/tokens.yaml", "sentiment_only_drift/theme.json")
        )
    )
    assert findings == []


def test_sentiment_map_faithful_is_zero_findings() -> None:
    findings = list(
        check_sentiment_fidelity(
            _ctx(
                "sentiment_map_faithful/tokens.yaml",
                "sentiment_map_faithful/theme.json",
            )
        )
    )
    assert findings == []


def test_sentiment_map_drift_is_error_with_locator() -> None:
    findings = list(
        check_sentiment_fidelity(
            _ctx("sentiment_map_drift/tokens.yaml", "sentiment_map_drift/theme.json")
        )
    )
    assert len(findings) >= 1
    assert all(f.severity is Severity.ERROR for f in findings)
    assert all(f.rule_id == SENTIMENT_RULE_ID for f in findings)
    assert any("sentiment" in f.locator for f in findings)


def test_sentiment_map_missing_key_is_error() -> None:
    """A declared map key with no counterpart on either side ERRORs (never
    silently drops the mapping)."""
    findings = list(
        check_sentiment_fidelity(
            _ctx(
                "sentiment_map_missing_key/tokens.yaml",
                "sentiment_map_missing_key/theme.json",
            )
        )
    )
    assert len(findings) >= 1
    assert all(f.severity is Severity.ERROR for f in findings)


def test_sentiment_map_malformed_tokens_is_error_not_crash() -> None:
    findings = list(
        check_sentiment_fidelity(
            _ctx(
                "sentiment_map_malformed/tokens.yaml",
                "sentiment_map_malformed/theme.json",
            )
        )
    )
    assert len(findings) >= 1
    assert any("could not be parsed" in f.message.lower() for f in findings)


def test_sentiment_rule_id_is_dl8_not_dl3() -> None:
    assert SENTIMENT_RULE_ID == "DL8"


def test_dl3_still_ignores_sentiment_after_dl8_lands() -> None:
    """Regression guard: adding DL8 must not change check_theme_fidelity's
    behavior -- DL3 stays sentiment-blind."""
    from retail.rules.design_theme_fidelity import check_theme_fidelity

    findings = list(
        check_theme_fidelity(
            _ctx("sentiment_only_drift/tokens.yaml", "sentiment_only_drift/theme.json")
        )
    )
    assert findings == []


def test_sentiment_live_pair_inert_on_main() -> None:
    """emits-on-main guard: neither committed tokens file declares
    meta.sentiment_map today, so DL8 is silent on both -- including
    tower-retail, whose sentiment colors actually drift (proving DL8 is
    inert-by-absence, not accidentally-passing)."""
    exec_dark = _ctx(
        "design/tokens/executive-dark-design-tokens.yaml",
        "themes/executive-dark.theme.json",
        repo_root=REPO_ROOT,
    )
    tower = _ctx(
        "design/tokens/tower-retail-design-tokens.yaml",
        "themes/tower-retail.theme.json",
        repo_root=REPO_ROOT,
    )
    assert list(check_sentiment_fidelity(exec_dark)) == []
    assert list(check_sentiment_fidelity(tower)) == []
```

(If `_ctx` / `REPO_ROOT` helpers in this file have different names or signatures, read the file's existing DL3 test helpers first and match them; keep each test body's intent unchanged.)

Create the fixture files:

`tests/fixtures/theme_fidelity/sentiment_map_faithful/tokens.yaml`:
```yaml
meta:
  compiles_to: "theme.json"
  sentiment_map:
    success: "good"
    warning: "neutral"
    danger: "bad"
colors:
  background: "#FFFFFF"
  data_colors:
    - "#111111"
  sentiment:
    success: "#2E7D5B"
    warning: "#B5832A"
    danger: "#B23A3A"
```

`tests/fixtures/theme_fidelity/sentiment_map_faithful/theme.json`:
```json
{
  "background": "#FFFFFF",
  "dataColors": ["#111111"],
  "good": "#2E7D5B",
  "neutral": "#B5832A",
  "bad": "#B23A3A"
}
```

`tests/fixtures/theme_fidelity/sentiment_map_drift/tokens.yaml`:
```yaml
meta:
  compiles_to: "theme.json"
  sentiment_map:
    success: "good"
    warning: "neutral"
    danger: "bad"
colors:
  background: "#FFFFFF"
  data_colors:
    - "#111111"
  sentiment:
    success: "#2E7D5B"
    warning: "#B5832A"
    danger: "#B23A3A"
```

`tests/fixtures/theme_fidelity/sentiment_map_drift/theme.json`:
```json
{
  "background": "#FFFFFF",
  "dataColors": ["#111111"],
  "good": "#2E7D32",
  "neutral": "#B8860B",
  "bad": "#B23A2E"
}
```

`tests/fixtures/theme_fidelity/sentiment_map_missing_key/tokens.yaml`:
```yaml
meta:
  compiles_to: "theme.json"
  sentiment_map:
    success: "good"
    warning: "neutral"
    danger: "bad"
colors:
  background: "#FFFFFF"
  data_colors:
    - "#111111"
  sentiment:
    success: "#2E7D5B"
    warning: "#B5832A"
    # danger deliberately absent -- the map cites a tokens key that does not exist
```

`tests/fixtures/theme_fidelity/sentiment_map_missing_key/theme.json`:
```json
{
  "background": "#FFFFFF",
  "dataColors": ["#111111"],
  "good": "#2E7D5B",
  "neutral": "#B5832A"
}
```

`tests/fixtures/theme_fidelity/sentiment_map_malformed/tokens.yaml`:
```yaml
meta: {compiles_to: "theme.json", sentiment_map: {success: "good"}
colors: [this is not closed yaml
```

`tests/fixtures/theme_fidelity/sentiment_map_malformed/theme.json`:
```json
{"background": "#FFFFFF"}
```

- [ ] 2. Run and confirm the expected failure:
```
pytest tests/unit/test_design_theme_fidelity.py::test_sentiment_map_absent_is_zero_findings_refuse_to_invent -v
```
Expected FAIL: `ImportError: cannot import name 'check_sentiment_fidelity' from 'retail.rules.design_theme_fidelity'`.

- [ ] 3. Minimal implementation. In `src/seshat/rules/design_theme_fidelity.py`, first update the module docstring's "DELIBERATELY OUT OF SCOPE" section so it names DL8 as the follow-on rule (replace the sentiment-fidelity paragraph that currently claims it is permanently unowned with a paragraph pointing to DL8 reading an opt-in `meta.sentiment_map`).

Then append at the end of the file (after `check_theme_fidelity`):

```python
# --- DL8: sentiment 4->3 fidelity (opt-in, human-declared correspondence) -----
#
# DL3 above deliberately never reconciles sentiment (a 4->3 naming ambiguity a
# human must resolve). DL8 is the follow-on rule that ruling unlocks: it reads
# an opt-in ``meta.sentiment_map`` -- a human-frozen ``{tokens_key: theme_key}``
# correspondence -- and FLAGS any mismatch. Absent the map, DL8 is provably
# inert (no finding, ever): it never guesses which tokens sentiment key
# corresponds to which theme key. Own rule id (Principle V hard rule #9: two
# rules must never share one id) -- DL8, not DL3.

SENTIMENT_RULE_ID = "DL8"


def _sentiment_map_for(tokens_doc: Any) -> dict[str, str] | None:
    """The human-declared ``{tokens_sentiment_key: theme_key}`` map, or None.

    None means "no map declared" -- the caller must skip with zero findings.
    DL8 never infers this map from color proximity or key names; it only
    reads what a human has already written to ``meta.sentiment_map``.
    """
    if not isinstance(tokens_doc, dict):
        return None
    meta = tokens_doc.get("meta")
    if not isinstance(meta, dict):
        return None
    raw = meta.get("sentiment_map")
    if not isinstance(raw, dict) or not raw:
        return None
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in raw.items()):
        return None
    return raw


def _reconcile_sentiment(
    tokens_rel: str, theme_rel: str, ctx: RuleContext
) -> Iterable[Finding]:
    tokens_doc, terr = _load_yaml(ctx.repo_root / tokens_rel)
    if terr is not None:
        yield Finding(
            SENTIMENT_RULE_ID,
            Severity.ERROR,
            f"design-tokens file could not be parsed ({terr}); sentiment "
            f"fidelity cannot be verified",
            f"{tokens_rel}#/",
        )
        return
    sentiment_map = _sentiment_map_for(tokens_doc)
    if sentiment_map is None:
        return  # no declared correspondence -- refuse to invent one

    theme_doc, herr = _load_json(ctx.repo_root / theme_rel)
    if herr is not None:
        yield Finding(
            SENTIMENT_RULE_ID,
            Severity.ERROR,
            f"theme file could not be parsed ({herr}); sentiment fidelity "
            f"cannot be verified",
            f"{theme_rel}#/",
        )
        return

    colors = tokens_doc.get("colors", {}) if isinstance(tokens_doc, dict) else {}
    tok_sentiment = colors.get("sentiment", {})
    tok_sentiment = tok_sentiment if isinstance(tok_sentiment, dict) else {}
    theme = theme_doc if isinstance(theme_doc, dict) else {}

    for tok_key, thm_key in sentiment_map.items():
        tok_val = tok_sentiment.get(tok_key)
        thm_val = theme.get(thm_key)
        if tok_val is None or thm_val is None:
            yield Finding(
                SENTIMENT_RULE_ID,
                Severity.ERROR,
                f"declared sentiment_map entry {tok_key!r} -> {thm_key!r} "
                f"cannot be reconciled: "
                f"colors.sentiment.{tok_key} is "
                f"{'absent' if tok_val is None else tok_val!r}, "
                f"theme.{thm_key} is "
                f"{'absent' if thm_val is None else thm_val!r}",
                f"{theme_rel}#/{thm_key}",
            )
            continue
        if tok_val != thm_val:
            yield Finding(
                SENTIMENT_RULE_ID,
                Severity.ERROR,
                f"theme {thm_key} {thm_val!r} does not match the token "
                f"declared sentiment.{tok_key} value {tok_val!r} "
                f"(declared correspondence {tok_key!r} -> {thm_key!r})",
                f"{theme_rel}#/{thm_key}",
            )


@register(
    SENTIMENT_RULE_ID,
    "Theme sentiment colors are faithful to a human-declared sentiment_map",
)
def check_sentiment_fidelity(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for tokens_rel in _iter_tokens_files(ctx):
        tokens_doc, terr = _load_yaml(ctx.repo_root / tokens_rel)
        if terr is not None:
            findings.append(
                Finding(
                    SENTIMENT_RULE_ID,
                    Severity.ERROR,
                    f"design-tokens file could not be parsed ({terr}); "
                    f"sentiment fidelity cannot be verified",
                    f"{tokens_rel}#/",
                )
            )
            continue
        theme_rel = _theme_rel_for(tokens_rel, tokens_doc, ctx)
        if theme_rel is None:
            continue
        findings.extend(_reconcile_sentiment(tokens_rel, theme_rel, ctx))
    return findings
```

Note: `_reconcile_sentiment` re-parses `tokens_doc` internally for the malformed-file path (mirrors DL3's existing `_reconcile` shape exactly), while `check_sentiment_fidelity`'s outer loop also parses once per tokens file to resolve `theme_rel` -- this double-parse-on-error-path is the same shape DL3 already has; do not "optimize" it away in this task.

- [ ] 4. Run tests, confirm GREEN (DL8 not yet in `EXPECTED_RULE_IDS`, so `test_registered_rule_ids_match_expected_set` will FAIL at this step -- that is expected; step 5 fixes it):
```
pytest tests/unit/test_design_theme_fidelity.py -v
pytest tests/unit/test_rules_wiring.py::test_registered_rule_ids_match_expected_set -v
```
Expected: DL8 tests green; the wiring test FAILs with `rule-id drift: missing={'DL8'}, unexpected=set()`.

- [ ] 5. Wire `EXPECTED_RULE_IDS`. Edit `tests/unit/test_rules_wiring.py`, immediately after the `"DL7",` line:
```python
        "DL7",  # design-lint: formatting-plan ledger well-formedness
        "DL8",  # design-lint: sentiment 4->3 fidelity, inert until owner declares meta.sentiment_map
```
Run:
```
pytest tests/unit/test_rules_wiring.py -v
```
Expected PASS.

- [ ] 6. Regenerate the manifest snapshot:
```
retail manifest --repo .
pytest tests/unit/test_rules_manifest_snapshot.py -v
```
Expected PASS: `docs/rules/rules-manifest.json` now contains a DL8 entry and the snapshot test is green.

- [ ] 7. Add the severity-posture fixture (use a drifting fixture so the generator observes DL8's real active posture, mirroring DL3). In `src/seshat/severity_posture.py`, add constants near `_YAML_DL3_TOKENS`/`_JSON_DL3_THEME`:
```python
_YAML_DL8_TOKENS = (
    "meta: { compiles_to: demo.theme.json, sentiment_map: { success: good } }\n"
    "colors:\n  sentiment:\n    success: '#2E7D5B'\n"
)
_JSON_DL8_THEME = '{"good": "#000000"}\n'
```
Add to `_RULE_FIXTURES`, right after the `"DL3"` entry:
```python
    "DL8": _Fixture(
        files=(
            ("design/tokens/demo-design-tokens.yaml", _YAML_DL8_TOKENS),
            ("demo.theme.json", _JSON_DL8_THEME),
        )
    ),
```
Run:
```
retail severity-posture --repo .
pytest tests/unit/test_severity_posture_snapshot.py -v
```
Expected PASS: `docs/rules/severity-posture.json` now carries a `"DL8"` entry with the generator-observed posture (commit the generator's output verbatim; the drift fixture makes DL8 fire, proving it is not a permanently-dead rule).

- [ ] 8. Reconcile the rule count (computed, not hardcoded):
```
python -c "import json; print(len(json.load(open('docs/rules/rules-manifest.json', encoding='utf-8'))))"
```
Read the printed integer `N` (do not assume a literal -- CT2/CT3 may land before or after). Edit `docs/glossary.md`'s rule-count line to `Currently N rules in 23 families` (family list unchanged -- DL8 joins the existing DL family). Edit `docs/quality/rule-count-claims.yaml`'s `anchor` + `claimed-count` to the same `N`, keeping both equal to `len(rules-manifest.json)`.

- [ ] 9. Glossary DL row. Append to the end of the existing `**DL**` row cell:
```
- `DL8` sentiment 4->3 fidelity -- reads an opt-in, human-declared `meta.sentiment_map` ({tokens sentiment key -> theme key}) and FLAGS any `colors.sentiment[k] != theme[v]` or a mapped key missing from either side as ERROR; absent the map, DL8 emits nothing (refuse to invent the correspondence, Principle V) -- inert on every tokens file until an owner freezes its map
```
Run:
```
pytest tests/unit/test_glossary_rule_table.py -v
```
Expected PASS: every live registered rule id (including `DL8`) appears in the glossary table.

- [ ] 10. Full verification sweep:
```
ruff format --check src/seshat/rules/design_theme_fidelity.py src/seshat/severity_posture.py tests/unit/test_design_theme_fidelity.py tests/unit/test_rules_wiring.py
ruff check src/seshat/rules/design_theme_fidelity.py src/seshat/severity_posture.py tests/unit/test_design_theme_fidelity.py tests/unit/test_rules_wiring.py
pytest -m unit -x -q
```
Expected: all green, including `test_rules_manifest_snapshot.py`, `test_severity_posture_snapshot.py`, `test_glossary_rule_table.py`, `test_rules_wiring.py`, `test_design_theme_fidelity.py`, and `test_sentiment_live_pair_inert_on_main` (the emits-on-main guard).

- [ ] 11. Commit:
```
git add src/seshat/rules/design_theme_fidelity.py tests/unit/test_design_theme_fidelity.py tests/fixtures/theme_fidelity/sentiment_map_faithful tests/fixtures/theme_fidelity/sentiment_map_drift tests/fixtures/theme_fidelity/sentiment_map_missing_key tests/fixtures/theme_fidelity/sentiment_map_malformed tests/unit/test_rules_wiring.py src/seshat/severity_posture.py docs/rules/rules-manifest.json docs/rules/severity-posture.json docs/glossary.md docs/quality/rule-count-claims.yaml
git commit -m "feat: DL8 sentiment 4->3 fidelity rule -- inert shell until owner declares meta.sentiment_map"
```

**OWNER STOP:** Present to the owner:
1. The proposed `meta.sentiment_map` for `design/tokens/executive-dark-design-tokens.yaml` (verified byte-exact faithful against `themes/executive-dark.theme.json` during recon):
   ```yaml
   meta:
     sentiment_map:
       success: "good"
       warning: "neutral"
       danger: "bad"
   ```
2. A dated Clarifications entry for the theme's `theme-spec.md` recording the frozen 4->3 correspondence ruling: `success->good`, `warning->neutral`, `danger->bad`; `neutral` (tokens) has no theme counterpart and is excluded from the map by the owner's own naming choice, not the rule's inference.
3. Why the build halts here: writing `meta.sentiment_map` into a committed tokens file is a Principle-V human seam -- DL8 reads a correspondence, it does not choose one. The owner adding this block to `executive-dark-design-tokens.yaml` is expected to land DL8 green there. `design/tokens/tower-retail-design-tokens.yaml` has real 3-value color drift (`success #2E7D5B` vs theme `good #2E7D32`, `warning #B5832A` vs `neutral #B8860B`, `danger #B23A3A` vs `bad #B23A2E`) plus an unmapped 4th `neutral` tokens key -- its `sentiment_map` stays **unwritten (rule inert)** until the owner reconciles the hexes or explicitly rules the drift acceptable. This task does not write either tokens file's map; that authorship belongs to the owner alone.

---

## Self-Review

### (a) Spec coverage -- each idea + shared phase to its task number(s)

| Design element | Task(s) |
| --- | --- |
| Shared foundation: `hex_to_lab` + `delta_e76` | Task 1 |
| Shared foundation: `composite_over` | Task 2 |
| Shared foundation: `format_pt` (Idea 4 support) | Task 3 |
| Idea 5 refactor (`_targets_for`/validate/write split) | Task 4 |
| Idea 4 -- font floor: `ThemeSeed` fields + constants + check | Tasks 5, 6 |
| Idea 4 -- CLI font flags | Task 7 |
| Idea 4 -- compile-leg round-trip | Task 8 |
| Idea 4 -- regression/lint gate | Task 9 |
| Idea 3 -- categorical self-check | Task 10 |
| Idea 3 -- CT3 static rule | Task 11 |
| Idea 1 -- ramp deltaE self-check (unwired) | Task 12 |
| Idea 1 -- CT2 static rule | Task 13 |
| Idea 1 -- floor re-derivation (OWNER STOP) | Task 14 |
| Idea 1 -- wire ratified floor | Task 15 |
| Idea 5 -- `derive_dark_seed` | Task 16 |
| Idea 5 -- `generate_pair` + `--pair` | Task 17 |
| Idea 2 -- composite-contrast check (standalone/unwired, OWNER STOP) | Task 18 |
| Idea 6 -- DL8 sentiment fidelity (OWNER STOP) | Task 19 |

All 6 ideas plus the shared Phase 0 are covered. The three OWNER STOPS the design doc mandates land at Tasks 14 (idea-1 floor), 18 (idea-2 schema), and 19 (idea-6 sentiment map).

### (b) Placeholder scan result

No `<TODO>` / `TBD` / bare-`...` placeholders remain in any implementation body. The only intentional literal placeholders are: `<OWNER_RATIFIED_VALUE>` / `MIN_ADJACENT_DELTAE = 7.5 # ... replace` in Task 15, and the `N` (rule-count) tokens in Tasks 11/13/19 -- both are correctly gated (the floor behind Task 14's OWNER STOP; `N` behind an explicit `python -c "print(len(...))"` read, never hardcoded). Every code block is real, runnable code.

### (c) Type-consistency check across tasks -- issues found and fixed inline

1. **Palette key path (fixed).** The Idea-1 draft used `palette["data_colors"]`; the real `build_palette` returns `palette["colors"]["data_colors"]` (verified against `src/seshat/theme_gen.py` line 139), and Idea 3's self-check already used the correct nested path. I corrected `check_ramp_deltae_or_raise` in Task 12 to read `palette["colors"]["data_colors"]`, with an inline note flagging the drafting slip.
2. **`generate()` call-site drift (fixed).** Several idea drafts said "call the check in `generate()` at line 253." After Task 4 refactors `generate()` into `_write_targets(_validate_and_collect(...))`, that inline body no longer exists. I retargeted every later self-check wiring (Tasks 6, 10, 15) to `_validate_and_collect()` -- the single choke point -- and stated so explicitly in each task, so the checks compose in one place: contrast, font floor, categorical distinctness, ramp deltaE.
3. **`delta_e76` import duplication (fixed).** Idea 1 and Idea 3 both add `delta_e76` to `theme_gen`'s color import. Task 10 (Idea 3) lands first and adds it to the single `from .color import contrast_ratio, delta_e76, format_pt, is_valid_hex` line; Task 12 (Idea 1) explicitly does NOT re-import. Task 18 extends the same line with `composite_over`. One import line, evolved additively.
4. **`derive_dark_seed` and the new font fields (fixed).** Task 16 uses `dataclasses.replace`, which preserves `title_font_pt`/`label_font_pt` automatically; I updated the interface note and docstring to say fonts pass through, avoiding a stale "accent/data_colors/sentiment only" claim now that `ThemeSeed` has two more fields.
5. **`composite_over` hex validation (reconciled).** The design doc's Idea-2 BLOCKER requires `ValueError` for out-of-range pct AND malformed hex. Task 2's implementation guards both (via `is_valid_hex`) and Task 18 consumes it; the two are consistent, and Task 18's check returns `ThemeGenError` (never a bare traceback) as the contract requires.
6. **Function-name consistency (verified).** `check_ramp_deltae_or_raise` (self-check) vs `check_ramp_deltae` (CT2 rule entry point) are deliberately distinct names in distinct modules; `check_categorical_distinctness_or_raise` (self-check) vs `check_categorical_distinctness` (CT3 rule) follow the same established `*_or_raise` (generator) / bare (rule) convention already used by `check_contrast_or_raise` / `check_contrast`. No collision.
7. **Rule-count `N` never hardcoded (verified).** Tasks 11, 13, and 19 all read `len(rules-manifest.json)` at run time and reuse the same integer in glossary + rule-count-claims, because they may land in any order and each adds one rule. No task assumes a fixed final count.

All fixes are applied inline in the task bodies above; nothing is left for the implementer to reconcile.
