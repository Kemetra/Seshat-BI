# Theme Generator (Slice 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a self-contained `retail theme-gen` verb that turns a caller-supplied palette into a gated Power BI theme artifact set (tokens + theme JSON + filled spec), stdlib-only, self-checking CT1 before writing.

**Architecture:** Extract the WCAG contrast math from `design_contrast.py` into a shared `src/seshat/color.py` (CT1 re-exports it so its test is unchanged). New `src/seshat/theme_gen.py` assembles the palette, derives a monochromatic `dataColors` ramp with stdlib `colorsys` when none is given, self-checks contrast via the shared helper, and writes three artifacts by construction-fidelity (DL1-clean, DL3-faithful). New `retail theme-gen` CLI verb dispatches to it.

**Tech Stack:** Python 3.13, stdlib only (`json`, `colorsys`, `pathlib`, `argparse`), `pyyaml` (already a dep) for tokens/spec YAML/text output, `pytest` (`@pytest.mark.unit`).

## Global Constraints

- **stdlib-only core; no new dependency.** No color library; use `colorsys` + the shared WCAG helper. (pyproject runtime deps stay `["pyyaml>=6"]`.)
- **No pbi-cli, no live Power BI, no network, no execution.** Local-file writes only.
- **DEFINE-only. Writes NO PBIR / `visual.json` / `powerbi/*.Report/`. Does NOT lift FR-008/FR-009.** No dashboard-automation claim anywhere in output.
- **ASCII only, UTF-8 without BOM, `\n` line endings** for every written artifact.
- **Never self-grant `pass`.** Generated spec readiness = `warning` (rule #9 / Principle V). CT1 cited as satisfied; CVD/render checks open pending a named reviewer.
- **Generated theme keys are styling-only** (DL1) and `dataColors`/`background` equal the tokens by construction (DL3). New tokens file carries `meta.compiles_to`.
- **No silent overwrite:** refuse to write an existing file without `--force`.
- Commit type prefix `<type>:`; end commits with the `Co-Authored-By` trailer.

---

### Task 1: Extract shared WCAG color helper (`color.py`)

**Files:**
- Create: `src/seshat/color.py`
- Modify: `src/seshat/rules/design_contrast.py:51-75` (replace defs with a re-export)
- Test: `tests/unit/test_color.py` (new); `tests/unit/test_design_contrast.py` (must still pass unchanged)

**Interfaces:**
- Produces: `retail.color.channel_luminance(c: int) -> float`, `relative_luminance(hex_color: str) -> float`, `contrast_ratio(a: str, b: str) -> float`, `is_valid_hex(s: str) -> bool`. All raise `ValueError` on a non-`#RRGGBB` hex (same as today).
- Consumes: nothing.

- [ ] **Step 1: Write the failing test** — `tests/unit/test_color.py`

```python
"""Unit tests for the shared WCAG color helper (retail.color)."""
from __future__ import annotations

import pytest

from retail.color import contrast_ratio, is_valid_hex, relative_luminance

pytestmark = pytest.mark.unit


def test_black_on_white_is_21_to_1() -> None:
    assert round(contrast_ratio("#000000", "#FFFFFF"), 1) == 21.0


def test_ratio_is_symmetric() -> None:
    assert round(contrast_ratio("#1A1D21", "#FFFFFF"), 4) == round(
        contrast_ratio("#FFFFFF", "#1A1D21"), 4
    )


def test_relative_luminance_bounds() -> None:
    assert relative_luminance("#000000") == 0.0
    assert round(relative_luminance("#FFFFFF"), 4) == 1.0


def test_is_valid_hex() -> None:
    assert is_valid_hex("#2FB6C4")
    assert not is_valid_hex("2FB6C4")
    assert not is_valid_hex("#2FB")
    assert not is_valid_hex("#GGGGGG")


def test_bad_hex_raises() -> None:
    with pytest.raises(ValueError):
        contrast_ratio("nothex", "#FFFFFF")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_color.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'retail.color'`

- [ ] **Step 3: Write `src/seshat/color.py`**

```python
"""Shared, stdlib-only sRGB/WCAG color math.

The single source of truth for the WCAG 2.x relative-luminance contrast ratio.
Both the CT1 governance rule (retail.rules.design_contrast) and the theme
generator (retail.theme_gen) import from here, so the generator's pre-write
self-check uses the exact arithmetic the gate later applies. No dependency
beyond the stdlib.
"""

from __future__ import annotations

import re

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def is_valid_hex(s: str) -> bool:
    """True iff ``s`` is a ``#RRGGBB`` hex color."""
    return isinstance(s, str) and _HEX_RE.match(s) is not None


def channel_luminance(c: int) -> float:
    """Linearize one 0-255 sRGB channel to its WCAG luminance component."""
    s = c / 255.0
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """WCAG 2.x relative luminance of an ``#RRGGBB`` color."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"not a 6-digit hex color: {hex_color!r}")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return (
        0.2126 * channel_luminance(r)
        + 0.7152 * channel_luminance(g)
        + 0.0722 * channel_luminance(b)
    )


def contrast_ratio(a: str, b: str) -> float:
    """WCAG contrast ratio (>= 1.0) between two ``#RRGGBB`` colors."""
    la = relative_luminance(a)
    lb = relative_luminance(b)
    lighter, darker = (la, lb) if la >= lb else (lb, la)
    return (lighter + 0.05) / (darker + 0.05)
```

- [ ] **Step 4: Re-export from `design_contrast.py` so CT1 + its test are unchanged**

Replace the three private defs at `src/seshat/rules/design_contrast.py:51-75` with:

```python
# WCAG math now lives in the shared helper so the CT1 rule and the theme
# generator apply identical arithmetic. Re-exported under the original private
# names to preserve every existing import (tests/unit/test_design_contrast.py).
from ..color import (  # noqa: F401
    channel_luminance as _channel_luminance,
    contrast_ratio as _contrast_ratio,
    relative_luminance as _relative_luminance,
)
```

(Leave `_parse_floor`, `_iter_tokens_files`, `_check_tokens`, `check_contrast` exactly as they are — they call `_contrast_ratio`, which now resolves to the re-export.)

- [ ] **Step 5: Run both test files to verify green**

Run: `pytest tests/unit/test_color.py tests/unit/test_design_contrast.py -q`
Expected: PASS (new helper tests pass; every existing CT1 test still passes unchanged).

- [ ] **Step 6: Commit**

```bash
git add src/seshat/color.py src/seshat/rules/design_contrast.py tests/unit/test_color.py
git commit -m "$(printf 'refactor: extract shared WCAG color helper (retail.color)\n\nCT1 re-exports it so its behavior + tests are unchanged; the theme\ngenerator will import the same arithmetic for its pre-write self-check.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 2: Theme generator core (`theme_gen.py`)

**Files:**
- Create: `src/seshat/theme_gen.py`
- Test: `tests/unit/test_theme_gen.py`

**Interfaces:**
- Consumes: `retail.color.{contrast_ratio, is_valid_hex}`.
- Produces:
  - `@dataclass(frozen=True) ThemeSeed(name, mode, accent, background, text_primary, text_secondary, text_muted, data_colors: tuple[str,...] | None, good, neutral, bad)`
  - `derive_ramp(accent: str, n: int = 6) -> tuple[str, ...]` — monochromatic light→dark ramp via `colorsys`, monotonic decreasing lightness.
  - `build_palette(seed: ThemeSeed) -> dict` — the resolved palette (fills defaults, derives ramp if `data_colors is None`).
  - `check_contrast_or_raise(palette: dict, floor: float = 4.5) -> None` — raises `ThemeGenError` naming the failing role + ratio.
  - `render_tokens_yaml(palette, seed) -> str`, `render_theme_json(palette, seed) -> str`, `render_spec_md(palette, seed) -> str`.
  - `generate(seed: ThemeSeed, repo_root: Path, force: bool = False) -> list[Path]` — writes the three artifacts, returns their paths. Raises `ThemeGenError` on bad hex, failed contrast, or existing file without `force`.
  - `class ThemeGenError(Exception)`.

- [ ] **Step 1: Write the failing tests** — `tests/unit/test_theme_gen.py`

```python
"""Unit tests for the theme generator (retail.theme_gen), Slice 1."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from retail.theme_gen import (
    ThemeGenError,
    ThemeSeed,
    build_palette,
    derive_ramp,
    generate,
)

pytestmark = pytest.mark.unit

DARK = dict(
    name="executive-dark",
    mode="dark",
    accent="#2FB6C4",
    background="#12263A",
    text_primary="#F2F6FA",
    text_secondary="#C4D1DE",
    text_muted="#93A6B8",
    data_colors=None,
    good="#3DDC97",
    neutral="#E5C13B",
    bad="#F2705B",
)


def _seed(**over) -> ThemeSeed:
    d = {**DARK, **over}
    return ThemeSeed(**d)


def test_derive_ramp_is_monotonic_lightness() -> None:
    from retail.color import relative_luminance

    ramp = derive_ramp("#2FB6C4", n=6)
    assert len(ramp) == 6
    lums = [relative_luminance(c) for c in ramp]
    assert lums == sorted(lums, reverse=True)  # light -> dark


def test_build_palette_derives_ramp_when_none() -> None:
    pal = build_palette(_seed(data_colors=None))
    assert len(pal["colors"]["data_colors"]) >= 4
    assert pal["colors"]["background"] == "#12263A"


def test_build_palette_uses_given_ramp() -> None:
    pal = build_palette(_seed(data_colors=("#111111", "#222222")))
    assert pal["colors"]["data_colors"] == ["#111111", "#222222"]


def test_generate_writes_three_artifacts(tmp_path: Path) -> None:
    paths = generate(_seed(), repo_root=tmp_path)
    rels = sorted(str(p.relative_to(tmp_path)).replace("\\", "/") for p in paths)
    assert rels == [
        "design/tokens/executive-dark-design-tokens.yaml",
        "themes/executive-dark.theme-spec.md",
        "themes/executive-dark.theme.json",
    ]


def test_generated_theme_is_dl3_faithful(tmp_path: Path) -> None:
    generate(_seed(), repo_root=tmp_path)
    theme = json.loads((tmp_path / "themes/executive-dark.theme.json").read_text())
    tokens = yaml.safe_load(
        (tmp_path / "design/tokens/executive-dark-design-tokens.yaml").read_text()
    )
    assert theme["background"] == tokens["colors"]["background"]
    assert theme["dataColors"] == tokens["colors"]["data_colors"]
    assert tokens["meta"]["compiles_to"] == "themes/executive-dark.theme.json"


def test_generated_theme_is_dl1_clean(tmp_path: Path) -> None:
    generate(_seed(), repo_root=tmp_path)
    theme = json.loads((tmp_path / "themes/executive-dark.theme.json").read_text())
    forbidden = ("dax", "measure", "calculated", "expression", "threshold",
                 "rule", "relationship", "sourcemapping", "validation",
                 "metricdefinition")
    allowed = {"good", "neutral", "bad", "datacolors", "foreground",
               "background", "tableaccent"}

    def norm(k: str) -> str:
        return k.lower().replace("-", "").replace("_", "").replace(" ", "")

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                nk = norm(k)
                if nk not in allowed:
                    assert not any(t in nk for t in forbidden), f"forbidden key {k}"
                walk(v)
        elif isinstance(node, list):
            for it in node:
                walk(it)

    walk(theme)


def test_spec_readiness_is_warning_not_pass(tmp_path: Path) -> None:
    generate(_seed(), repo_root=tmp_path)
    spec = (tmp_path / "themes/executive-dark.theme-spec.md").read_text()
    assert "**Status:** `warning`" in spec
    assert "pass" not in spec.split("## Readiness")[1].split("Status")[1][:40]


def test_contrast_failure_refuses_to_write(tmp_path: Path) -> None:
    # text_muted too dark on a dark bg -> below 4.5:1
    with pytest.raises(ThemeGenError, match="contrast"):
        generate(_seed(text_muted="#1A2A38"), repo_root=tmp_path)
    assert not (tmp_path / "themes/executive-dark.theme.json").exists()


def test_bad_hex_is_clean_error(tmp_path: Path) -> None:
    with pytest.raises(ThemeGenError, match="hex"):
        generate(_seed(accent="not-a-hex"), repo_root=tmp_path)


def test_refuses_overwrite_without_force(tmp_path: Path) -> None:
    generate(_seed(), repo_root=tmp_path)
    with pytest.raises(ThemeGenError, match="exists"):
        generate(_seed(), repo_root=tmp_path)
    generate(_seed(), repo_root=tmp_path, force=True)  # ok with force
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/unit/test_theme_gen.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'retail.theme_gen'`

- [ ] **Step 3: Write `src/seshat/theme_gen.py`**

```python
"""Theme generator (Slice 1, DEFINE-only).

Turns a caller-supplied palette seed into a gated surface-3 theme artifact set:
a design-tokens YAML, a Power BI theme JSON, and a filled theme spec. Stdlib-only
(``colorsys`` + the shared ``retail.color`` WCAG helper). Self-checks contrast
before writing and refuses to emit a theme the CT1 gate would reject.

DEFINE-only: writes NO PBIR / visual.json / powerbi report file, lifts no
FR-008/009, uses no pbi-cli / live Power BI / network. Never self-grants a
readiness ``pass`` (rule #9 / Principle V): the generated spec is ``warning``,
with CT1 cited as satisfied and the human-judgment checks (CVD / render /
saturation) left open for a named reviewer.
"""

from __future__ import annotations

import colorsys
import json
from dataclasses import dataclass
from pathlib import Path

from .color import contrast_ratio, is_valid_hex

AA_FLOOR = 4.5
_TEXT_ROLES = ("primary", "secondary", "muted")


class ThemeGenError(Exception):
    """A generation input/output problem surfaced cleanly (never a traceback)."""


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


def _hex_to_hls(h: str) -> tuple[float, float, float]:
    r, g, b = (int(h.lstrip("#")[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b)


def _hls_to_hex(h: float, l: float, s: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, min(1.0, l)), s)
    return "#{:02X}{:02X}{:02X}".format(
        round(r * 255), round(g * 255), round(b * 255)
    )


def derive_ramp(accent: str, n: int = 6) -> tuple[str, ...]:
    """Monochromatic light->dark ramp from ``accent`` (monotonic lightness)."""
    if not is_valid_hex(accent):
        raise ThemeGenError(f"accent is not a #RRGGBB hex: {accent!r}")
    h, _l, s = _hex_to_hls(accent)
    s = max(s, 0.35)  # keep the hue readable, not washed to grey
    # lightness steps from light (0.78) down to dark (0.28)
    top, bottom = 0.78, 0.28
    if n == 1:
        return (accent,)
    steps = [top - (top - bottom) * i / (n - 1) for i in range(n)]
    return tuple(_hls_to_hex(h, l, s) for l in steps)


def build_palette(seed: ThemeSeed) -> dict:
    """Resolve the seed into a full palette dict (fills ramp if none given)."""
    for label, val in (
        ("accent", seed.accent),
        ("background", seed.background),
        ("text_primary", seed.text_primary),
        ("text_secondary", seed.text_secondary),
        ("text_muted", seed.text_muted),
        ("good", seed.good),
        ("neutral", seed.neutral),
        ("bad", seed.bad),
    ):
        if not is_valid_hex(val):
            raise ThemeGenError(f"{label} is not a #RRGGBB hex: {val!r}")
    if seed.data_colors is None:
        ramp = list(derive_ramp(seed.accent))
    else:
        for c in seed.data_colors:
            if not is_valid_hex(c):
                raise ThemeGenError(f"data color is not a #RRGGBB hex: {c!r}")
        ramp = list(seed.data_colors)
    return {
        "colors": {
            "primary": seed.accent,
            "secondary": ramp[min(1, len(ramp) - 1)],
            "background": seed.background,
            "text": {
                "primary": seed.text_primary,
                "secondary": seed.text_secondary,
                "muted": seed.text_muted,
            },
            "sentiment": {
                "success": seed.good,
                "warning": seed.neutral,
                "danger": seed.bad,
            },
            "data_colors": ramp,
        }
    }


def check_contrast_or_raise(palette: dict, floor: float = AA_FLOOR) -> None:
    """Refuse to proceed if any text role fails the AA floor vs background."""
    bg = palette["colors"]["background"]
    text = palette["colors"]["text"]
    for role in _TEXT_ROLES:
        ratio = contrast_ratio(text[role], bg)
        if ratio < floor:
            raise ThemeGenError(
                f"contrast: text.{role} {text[role]} on {bg} is "
                f"{ratio:.2f}:1, below the {floor:g}:1 AA floor -- refusing "
                f"to write (would fail CT1)"
            )


def render_tokens_yaml(palette: dict, seed: ThemeSeed) -> str:
    c = palette["colors"]
    ramp = "\n".join(f'    - "{h}"' for h in c["data_colors"])
    return (
        f"# Generated by `retail theme-gen` (Slice 1). Surface-3 tokens.\n"
        f"# ASCII only, UTF-8 no BOM. Styling defaults only (no metric/DAX).\n"
        f"meta:\n"
        f'  name: "{seed.name}-design-tokens"\n'
        f'  style: "generated ({seed.mode})"\n'
        f'  version: "1"\n'
        f'  compiles_to: "themes/{seed.name}.theme.json"\n'
        f"colors:\n"
        f'  primary: "{c["primary"]}"\n'
        f'  secondary: "{c["secondary"]}"\n'
        f'  background: "{c["background"]}"\n'
        f"  text:\n"
        f'    primary: "{c["text"]["primary"]}"\n'
        f'    secondary: "{c["text"]["secondary"]}"\n'
        f'    muted: "{c["text"]["muted"]}"\n'
        f"  sentiment:\n"
        f'    success: "{c["sentiment"]["success"]}"\n'
        f'    warning: "{c["sentiment"]["warning"]}"\n'
        f'    danger: "{c["sentiment"]["danger"]}"\n'
        f"  data_colors:\n"
        f"{ramp}\n"
        f"accessibility:\n"
        f'  min_text_contrast_ratio: "4.5:1"\n'
        f"  colorblind_considerate_categoricals: false"
        f"   # monochromatic ramp: CVD is a named-reviewer call (Principle V)\n"
        f"  do_not_rely_on_color_alone: true\n"
    )


def render_theme_json(palette: dict, seed: ThemeSeed) -> str:
    c = palette["colors"]
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
                        {"fontFamily": "Segoe UI Semibold", "fontSize": 12}
                    ],
                    "labels": [{"fontFamily": "Segoe UI", "fontSize": 9}],
                }
            }
        },
    }
    return json.dumps(doc, indent=2) + "\n"


def render_spec_md(palette: dict, seed: ThemeSeed) -> str:
    c = palette["colors"]
    ratios = {
        r: contrast_ratio(c["text"][r], c["background"]) for r in _TEXT_ROLES
    }
    return (
        f"# Theme JSON Spec -- {seed.name} (surface 3, defaults only)\n\n"
        f"> GENERATED by `retail theme-gen` (Slice 1). Styling DEFAULTS only.\n"
        f"> Validate in Power BI Desktop before use (schema treated as UNCERTAIN).\n\n"
        f"- **Theme name:** `{seed.name}`\n"
        f"- **Compiled JSON:** `themes/{seed.name}.theme.json`\n"
        f"- **Mode:** `{seed.mode}`\n"
        f"- **Authored by:** `retail theme-gen`\n\n"
        f"## 8. Accessibility checks\n\n"
        f"- [x] **Contrast** -- CT1 (computed): "
        f"text.primary {ratios['primary']:.2f}:1, "
        f"text.secondary {ratios['secondary']:.2f}:1, "
        f"text.muted {ratios['muted']:.2f}:1 vs background "
        f"(all >= 4.5:1 AA). *Evidence: CT1 arithmetic on the committed tokens.*\n"
        f"- [ ] **CVD distinguishability** -- OPEN: the monochromatic ramp is "
        f"less category-distinguishable; needs a named reviewer (Principle V).\n"
        f"- [ ] **Small-size / adjacency legibility** -- OPEN: needs a named "
        f"reviewer against a rendered page (F016 surface; not yet built).\n"
        f"- [ ] **No pure-saturated background behind dense charts** -- OPEN: "
        f"named-reviewer design note.\n\n"
        f"## Readiness\n\n"
        f"- **Status:** `warning`\n"
        f"- **Evidence:**\n"
        f"  - `themes/{seed.name}.theme.json` generated; CT1 contrast clean "
        f"(computed above)\n"
        f"- **Blocking reasons (open, not blocking a `pass` that was never "
        f"claimed):**\n"
        f"  - CVD / legibility / saturation have no named reviewer yet "
        f"(cannot be `pass` on author alone -- rule #9 / Principle V)\n\n"
        f"(No `score:` / `confidence:` field exists here BY DESIGN -- rule 9.)\n"
    )


def generate(seed: ThemeSeed, repo_root: Path, force: bool = False) -> list[Path]:
    palette = build_palette(seed)
    check_contrast_or_raise(palette)
    targets = {
        repo_root / "design" / "tokens" / f"{seed.name}-design-tokens.yaml":
            render_tokens_yaml(palette, seed),
        repo_root / "themes" / f"{seed.name}.theme.json":
            render_theme_json(palette, seed),
        repo_root / "themes" / f"{seed.name}.theme-spec.md":
            render_spec_md(palette, seed),
    }
    if not force:
        for p in targets:
            if p.exists():
                raise ThemeGenError(
                    f"{p} exists -- refusing to overwrite (use --force)"
                )
    written: list[Path] = []
    for p, content in targets.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
        written.append(p)
    return written
```

- [ ] **Step 4: Run to verify green**

Run: `pytest tests/unit/test_theme_gen.py -q`
Expected: PASS (all 11 tests).

- [ ] **Step 5: Commit**

```bash
git add src/seshat/theme_gen.py tests/unit/test_theme_gen.py
git commit -m "$(printf 'feat: theme generator core (retail.theme_gen, Slice 1)\n\nFull-multi-input palette -> tokens+theme+spec, stdlib-only; derives a\nmonochromatic dataColors ramp via colorsys when none given; self-checks\nCT1 before writing and refuses a below-floor theme; DL1-clean + DL3-\nfaithful by construction; readiness = warning (never self-pass).\n\nDEFINE-only: no PBIR, no FR-008/009 lift, no pbi-cli.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 3: CLI verb `retail theme-gen`

**Files:**
- Modify: `src/seshat/cli.py` (add `theme-gen` subparser near the `generate` verb ~line 166; add dispatch in the command switch)
- Test: `tests/unit/test_theme_gen_cli.py`

**Interfaces:**
- Consumes: `retail.theme_gen.{ThemeSeed, generate, ThemeGenError}`.
- Produces: exit code 0 on success (prints written paths + a suggested `themes/README.md` line), exit code 2 on `ThemeGenError` (prints the error to stderr). Adds a `theme_gen_main(args) -> int` in `theme_gen.py` for the CLI to call.

- [ ] **Step 1: Add `theme_gen_main` to `theme_gen.py`**

```python
def theme_gen_main(args) -> int:
    """CLI entry: assemble a ThemeSeed from argparse args, generate, report."""
    import sys

    dcs = (
        tuple(s.strip() for s in args.data_colors.split(",") if s.strip())
        if args.data_colors
        else None
    )
    defaults = (
        {"good": "#2E7D5B", "neutral": "#B5832A", "bad": "#B23A3A"}
    )
    seed = ThemeSeed(
        name=args.name,
        mode=args.mode,
        accent=args.accent,
        background=args.background,
        text_primary=args.text_primary,
        text_secondary=args.text_secondary or args.text_primary,
        text_muted=args.text_muted or args.text_secondary or args.text_primary,
        data_colors=dcs,
        good=args.good or defaults["good"],
        neutral=args.neutral or defaults["neutral"],
        bad=args.bad or defaults["bad"],
    )
    try:
        written = generate(seed, Path(args.repo), force=args.force)
    except ThemeGenError as exc:
        print(f"theme-gen: {exc}", file=sys.stderr)
        return 2
    for p in written:
        print(f"wrote {p}")
    print(
        f"suggested themes/README.md line: "
        f"- `{args.name}.theme.json` -- generated starter ({args.mode}); "
        f"validate in Power BI Desktop; readiness = warning."
    )
    return 0
```

- [ ] **Step 2: Write the failing CLI test** — `tests/unit/test_theme_gen_cli.py`

```python
"""CLI-level test for `retail theme-gen` (Slice 1)."""
from __future__ import annotations

from pathlib import Path

import pytest

from retail.cli import main

pytestmark = pytest.mark.unit


def _args(tmp: Path) -> list[str]:
    return [
        "theme-gen", "--name", "gen-dark", "--mode", "dark",
        "--accent", "#2FB6C4", "--background", "#12263A",
        "--text-primary", "#F2F6FA", "--text-secondary", "#C4D1DE",
        "--text-muted", "#93A6B8", "--repo", str(tmp),
    ]


def test_cli_generates_and_exits_zero(tmp_path: Path) -> None:
    rc = main(_args(tmp_path))
    assert rc == 0
    assert (tmp_path / "themes/gen-dark.theme.json").exists()
    assert (tmp_path / "design/tokens/gen-dark-design-tokens.yaml").exists()
    assert (tmp_path / "themes/gen-dark.theme-spec.md").exists()


def test_cli_bad_hex_exits_two(tmp_path: Path) -> None:
    bad = _args(tmp_path)
    bad[bad.index("#2FB6C4")] = "not-hex"
    assert main(bad) == 2
```

- [ ] **Step 3: Run to verify it fails**

Run: `pytest tests/unit/test_theme_gen_cli.py -q`
Expected: FAIL — `argument command: invalid choice: 'theme-gen'`

- [ ] **Step 4: Wire the subparser + dispatch in `cli.py`**

Add after the `generate` parser block (~line 166):

```python
    themegen = sub.add_parser(
        "theme-gen",
        help="generate a gated Power BI theme (tokens + theme JSON + spec)",
    )
    themegen.add_argument("--name", required=True, help="theme/file basename slug")
    themegen.add_argument(
        "--mode", choices=("light", "dark"), required=True, help="light or dark"
    )
    themegen.add_argument("--accent", required=True, metavar="#RRGGBB")
    themegen.add_argument("--background", required=True, metavar="#RRGGBB")
    themegen.add_argument("--text-primary", dest="text_primary", required=True,
                          metavar="#RRGGBB")
    themegen.add_argument("--text-secondary", dest="text_secondary",
                          default=None, metavar="#RRGGBB")
    themegen.add_argument("--text-muted", dest="text_muted", default=None,
                          metavar="#RRGGBB")
    themegen.add_argument("--data-colors", dest="data_colors", default=None,
                          metavar="#a,#b,...",
                          help="comma-separated ramp; derived from accent if omitted")
    themegen.add_argument("--good", default=None, metavar="#RRGGBB")
    themegen.add_argument("--neutral", default=None, metavar="#RRGGBB")
    themegen.add_argument("--bad", default=None, metavar="#RRGGBB")
    themegen.add_argument("--repo", default=".", help="repo root to write into")
    themegen.add_argument("--force", action="store_true",
                          help="overwrite existing files")
```

In the command-dispatch switch (where `generate`/`scaffold`/etc. dispatch), add:

```python
    if args.command == "theme-gen":
        from .theme_gen import theme_gen_main

        return theme_gen_main(args)
```

(Match the surrounding dispatch style — if the switch returns `int`, return; if it calls a function and returns its code, mirror that. Confirm by reading the existing `generate`/`scaffold` dispatch lines.)

- [ ] **Step 5: Run to verify green**

Run: `pytest tests/unit/test_theme_gen_cli.py -q`
Expected: PASS (both tests).

- [ ] **Step 6: Commit**

```bash
git add src/seshat/cli.py src/seshat/theme_gen.py tests/unit/test_theme_gen_cli.py
git commit -m "$(printf 'feat: retail theme-gen CLI verb (Slice 1)\n\nWires the theme generator as a stdlib-only kit verb: assembles a\nThemeSeed from args, generates the gated triplet, prints written paths +\na suggested README line; exit 2 on a clean ThemeGenError.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 4: Full-gate verification + generate one committed example

**Files:**
- Create (via the verb, then commit): `design/tokens/executive-dark-design-tokens.yaml`, `themes/executive-dark.theme.json`, `themes/executive-dark.theme-spec.md`
- Modify: `themes/README.md` (add the generated-starter inventory line, by hand)

**Interfaces:** none (verification + dogfood).

- [ ] **Step 1: Run the full CI gate locally**

Run:
```bash
ruff format --check src tests
ruff check src tests
pytest -m unit -q
python -m retail check
```
Expected: all pass; `retail check` exit 0.

- [ ] **Step 2: Generate one real example into the repo (dogfood the verb)**

Run:
```bash
python -m retail theme-gen --name executive-dark --mode dark \
  --accent "#2FB6C4" --background "#12263A" \
  --text-primary "#F2F6FA" --text-secondary "#C4D1DE" --text-muted "#93A6B8"
```
Expected: writes the three files; prints the suggested README line.

- [ ] **Step 3: Confirm the generated example passes the gate**

Run: `python -m retail check`
Expected: exit 0 — DL1 (purity), DL3 (fidelity), CT1 (contrast) all clean on the generated `executive-dark` triplet. (This proves the generator's output survives the real gate, not just its self-check.)

- [ ] **Step 4: Add the README inventory line (by hand, ASCII)**

Add under the themes inventory in `themes/README.md`:

```markdown
- `executive-dark.theme.json` -- generated starter (dark) via `retail theme-gen`;
  validate in Power BI Desktop; readiness = warning (CVD/render checks open).
```

- [ ] **Step 5: Commit the example + README line**

```bash
git add design/tokens/executive-dark-design-tokens.yaml themes/executive-dark.theme.json themes/executive-dark.theme-spec.md themes/README.md
git commit -m "$(printf 'feat: generate executive-dark example theme (dogfood theme-gen)\n\nThe first generator output committed; proves the emitted triplet passes\nthe real retail check gate (DL1+DL3+CT1), not just the self-check.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Self-Review

- **Spec coverage:** verb (T3) ✓; full-multi-input palette + derived ramp fallback (T2 `build_palette`/`derive_ramp`) ✓; three artifacts w/ `compiles_to` (T2) ✓; CT1 self-check refuses below-floor (T2 `check_contrast_or_raise`, tested) ✓; DL1-clean + DL3-faithful by construction (T2, tested) ✓; readiness=warning (T2 `render_spec_md`, tested) ✓; no-overwrite-without-force (T2, tested) ✓; shared color helper w/ CT1 unchanged (T1) ✓; stdlib-only (no import beyond `colorsys`/`json`/`pathlib`/`yaml`) ✓; DEFINE-only boundary (no PBIR anywhere) ✓; gate + dogfood (T4) ✓.
- **Placeholder scan:** none — every code step has complete code.
- **Type consistency:** `ThemeSeed`, `generate(seed, repo_root, force)`, `ThemeGenError`, `derive_ramp`, `build_palette`, `check_contrast_or_raise`, `theme_gen_main` used consistently across T2/T3.
- **Boundary check:** no task writes `powerbi/*.Report/`, `visual.json`, or touches FR-008/009. No pbi-cli. Confirmed.
