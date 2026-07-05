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
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from .color import contrast_ratio, is_valid_hex

AA_FLOOR = 4.5
_TEXT_ROLES = ("primary", "secondary", "muted")

# A theme name is a filesystem-safe slug: it becomes a filename under themes/ and
# design/tokens/, so it must never contain a path separator or ``..`` (that would
# let --name escape the output dirs -- e.g. into powerbi/, a hard boundary). This
# mirrors the is_relative_to / path guards the sibling CLI verbs already enforce.
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Mode-sensible default sentiment colors (conservative, accessible tones) used
# when the caller does not override them. COLORS only -- the sentiment
# THRESHOLD/RULE is a metric contract (F009), never set here.
_DEFAULT_SENTIMENT = {"good": "#2E7D5B", "neutral": "#B5832A", "bad": "#B23A3A"}


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


def _hls_to_hex(h: float, lightness: float, s: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, min(1.0, lightness)), s)
    return "#{:02X}{:02X}{:02X}".format(round(r * 255), round(g * 255), round(b * 255))


def derive_ramp(accent: str, n: int = 6) -> tuple[str, ...]:
    """Monochromatic light->dark ramp from ``accent`` (monotonic lightness)."""
    if not is_valid_hex(accent):
        raise ThemeGenError(f"accent is not a #RRGGBB hex: {accent!r}")
    h, _lightness, s = _hex_to_hls(accent)
    s = max(s, 0.35)  # keep the hue readable, not washed to grey
    top, bottom = 0.78, 0.28  # lightness range: light -> dark
    if n == 1:
        return (accent,)
    steps = [top - (top - bottom) * i / (n - 1) for i in range(n)]
    return tuple(_hls_to_hex(h, lightness, s) for lightness in steps)


def _validate_name(name: str) -> None:
    """Reject a name that is not a filesystem-safe slug (no separators / ``..``).

    ``name`` becomes a filename under ``themes/`` and ``design/tokens/``; a value
    containing ``/``, ``\\`` or ``..`` would let the generator write outside its
    output directories (a path-traversal escape). Refuse it up front.
    """
    if not isinstance(name, str) or _NAME_RE.match(name) is None or ".." in name:
        raise ThemeGenError(
            f"name must be a filesystem-safe slug "
            f"(letters/digits/._- only, no path separators or '..'): {name!r}"
        )


def build_palette(seed: ThemeSeed) -> dict:
    """Resolve the seed into a full palette dict (fills ramp if none given)."""
    _validate_name(seed.name)
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
    if not ramp:
        raise ThemeGenError(
            "data_colors is empty -- supply at least one #RRGGBB, or omit "
            "--data-colors to derive a ramp from the accent"
        )
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
        "# Generated by `retail theme-gen` (Slice 1). Surface-3 tokens.\n"
        "# ASCII only, UTF-8 no BOM. Styling defaults only (no metric/DAX).\n"
        "meta:\n"
        f'  name: "{seed.name}-design-tokens"\n'
        f'  style: "generated ({seed.mode})"\n'
        '  version: "1"\n'
        f'  compiles_to: "themes/{seed.name}.theme.json"\n'
        "colors:\n"
        f'  primary: "{c["primary"]}"\n'
        f'  secondary: "{c["secondary"]}"\n'
        f'  background: "{c["background"]}"\n'
        "  text:\n"
        f'    primary: "{c["text"]["primary"]}"\n'
        f'    secondary: "{c["text"]["secondary"]}"\n'
        f'    muted: "{c["text"]["muted"]}"\n'
        "  sentiment:\n"
        f'    success: "{c["sentiment"]["success"]}"\n'
        f'    warning: "{c["sentiment"]["warning"]}"\n'
        f'    danger: "{c["sentiment"]["danger"]}"\n'
        "  data_colors:\n"
        f"{ramp}\n"
        "accessibility:\n"
        '  min_text_contrast_ratio: "4.5:1"\n'
        "  # monochromatic ramp: CVD is a named-reviewer call (Principle V)\n"
        "  colorblind_considerate_categoricals: false\n"
        "  do_not_rely_on_color_alone: true\n"
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
                    "title": [{"fontFamily": "Segoe UI Semibold", "fontSize": 12}],
                    "labels": [{"fontFamily": "Segoe UI", "fontSize": 9}],
                }
            }
        },
    }
    return json.dumps(doc, indent=2) + "\n"


def render_spec_md(palette: dict, seed: ThemeSeed) -> str:
    c = palette["colors"]
    ratios = {r: contrast_ratio(c["text"][r], c["background"]) for r in _TEXT_ROLES}
    return (
        f"# Theme JSON Spec -- {seed.name} (surface 3, defaults only)\n\n"
        "> GENERATED by `retail theme-gen` (Slice 1). Styling DEFAULTS only.\n"
        "> Validate in Power BI Desktop before use (schema treated as "
        "UNCERTAIN).\n\n"
        f"- **Theme name:** `{seed.name}`\n"
        f"- **Compiled JSON:** `themes/{seed.name}.theme.json`\n"
        f"- **Mode:** `{seed.mode}`\n"
        "- **Authored by:** `retail theme-gen`\n\n"
        "## 8. Accessibility checks\n\n"
        "- [x] **Contrast** -- CT1 (computed): "
        f"text.primary {ratios['primary']:.2f}:1, "
        f"text.secondary {ratios['secondary']:.2f}:1, "
        f"text.muted {ratios['muted']:.2f}:1 vs background "
        "(all >= 4.5:1 AA). *Evidence: CT1 arithmetic on the committed "
        "tokens.*\n"
        "- [ ] **CVD distinguishability** -- OPEN: the monochromatic ramp is "
        "less category-distinguishable; needs a named reviewer (Principle V).\n"
        "- [ ] **Small-size / adjacency legibility** -- OPEN: needs a named "
        "reviewer against a rendered page (F016 surface; not yet built).\n"
        "- [ ] **No pure-saturated background behind dense charts** -- OPEN: "
        "named-reviewer design note.\n\n"
        "## Readiness\n\n"
        "- **Status:** `warning`\n"
        "- **Evidence:**\n"
        f"  - `themes/{seed.name}.theme.json` generated; CT1 contrast clean "
        "(computed above)\n"
        "- **Blocking reasons (open; no `pass` was ever claimed):**\n"
        "  - CVD / legibility / saturation have no named reviewer yet "
        "(cannot be `pass` on author alone -- rule #9 / Principle V)\n\n"
        "(No `score:` / `confidence:` field exists here BY DESIGN -- rule 9.)\n"
    )


def generate(seed: ThemeSeed, repo_root: Path, force: bool = False) -> list[Path]:
    palette = build_palette(seed)
    check_contrast_or_raise(palette)
    targets = {
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


def theme_gen_main(args) -> int:
    """CLI entry: assemble a ThemeSeed from argparse args, generate, report."""
    dcs: tuple[str, ...] | None = (
        tuple(s.strip() for s in args.data_colors.split(",") if s.strip())
        if args.data_colors
        else None
    )
    if dcs == ():  # an all-blank --data-colors -> derive from accent, not empty
        dcs = None
    seed = ThemeSeed(
        name=args.name,
        mode=args.mode,
        accent=args.accent,
        background=args.background,
        text_primary=args.text_primary,
        text_secondary=args.text_secondary or args.text_primary,
        text_muted=args.text_muted or args.text_secondary or args.text_primary,
        data_colors=dcs,
        good=args.good or _DEFAULT_SENTIMENT["good"],
        neutral=args.neutral or _DEFAULT_SENTIMENT["neutral"],
        bad=args.bad or _DEFAULT_SENTIMENT["bad"],
    )
    try:
        written = generate(seed, Path(args.repo), force=args.force)
    except ThemeGenError as exc:
        print(f"theme-gen: {exc}", file=sys.stderr)
        return 2
    for p in written:
        print(f"wrote {p}")
    print(
        f"suggested themes/README.md line: - `{args.name}.theme.json` -- "
        f"generated starter ({args.mode}); validate in Power BI Desktop; "
        f"readiness = warning."
    )
    return 0
