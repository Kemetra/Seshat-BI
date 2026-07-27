"""Theme generator (Slice 1, DEFINE-only).

Turns a caller-supplied palette seed into a gated surface-3 theme artifact set:
a design-tokens YAML, a Power BI theme JSON, and a filled theme spec. Stdlib-only
(``colorsys`` + the shared ``seshat.color`` WCAG helper). Self-checks contrast
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
from dataclasses import dataclass, replace
from pathlib import Path

from .color import composite_over, contrast_ratio, delta_e76, format_pt, is_valid_hex
from .theme_style_cards import StyleCardError, build_page_cards, build_star_cards

AA_FLOOR = 4.5
# WCAG 2.x non-text contrast floor. Gridlines, borders, and visual fills are
# non-text elements: their floor is 3:1, not the 4.5:1 that applies to text. Kept
# separate from AA_FLOOR so neither can be loosened by editing the other.
AA_NON_TEXT_FLOOR = 3.0
MIN_TITLE_FONT_PT = 12.0
MIN_LABEL_FONT_PT = 9.0
MIN_CATEGORICAL_DELTAE = (
    2.0  # CIE76 JND-adjacent floor for whole-set data_colors distinctness
)
MIN_ADJACENT_DELTAE = (
    3.0  # OWNER-ratified 2026-07-08 (Task 14) -- adjacent-ramp near-collapse floor
)
TAP_TARGET_MIN_PX = 44  # doc-only floor (WCAG 2.5.8); never written to any artifact
_TEXT_ROLES = ("primary", "secondary", "muted")

# Which section 5/6/7 token keys hold a COLOR, and so must dark-derive (#521
# finding 2). Deliberately a closed set rather than a "looks like a hex" sniff:
# a value-shape guess would silently reclassify a key whose meaning changed.
# ``test_theme_gen_page_derivation`` pins these as subsets of the shipped
# CHROME_TOKEN_KEYS/PAGE_TOKEN_KEYS vocabularies AND pins that colour plus
# non-colour keys EXHAUST each vocabulary -- so adding a token key without
# classifying it here fails at test time instead of passing a light-mode colour
# into a dark theme, which is exactly how finding 2 arose.
_CHROME_COLOR_KEYS = ("gridline", "border")
_PAGE_COLOR_KEYS = (
    "background",
    "wallpaper",
    "filter_pane_background",
    "filter_pane_text",
    "filter_card_applied",
    "filter_card_available",
)

# OWNER-ratified 2026-07-08 (T18): the transparency-role schema. Choice 1 froze a
# SINGLE opt-in ``overlay`` role (background-overlay panels / card fills); choice 2
# froze an opaque default (a role only exists when a caller declares it). See
# docs/superpowers/specs/2026-07-08-transparency-role-schema-proposal.md.
_ALLOWED_TRANSPARENCY_ROLES = ("overlay",)

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
    title_font_pt: float = 12.0
    label_font_pt: float = 9.0
    # OWNER-ratified transparency roles (T18):
    # {role: {"fg": hex, "transparency_pct": float}}. None (default) means no
    # transparency declared -- every existing caller is unaffected and no
    # transparency block is emitted.
    transparency: dict | None = None
    # Section-5 visual chrome (gridline/border/title_align/data_labels/
    # number_format). None (default) means no chrome declared -- every existing
    # caller is unaffected and no section-5 card is emitted.
    chrome: dict | None = None
    # Sections 6+7 page cards (page/wallpaper fill, filter-pane LOOK). None
    # (default) emits no visualStyles["page"] entry at all.
    page: dict | None = None


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


def _invert_lightness(hex_color: str) -> str:
    """Flip the L channel (1.0 - L); hue and saturation unchanged."""
    h, lightness, s = _hex_to_hls(hex_color)
    return _hls_to_hex(h, 1.0 - lightness, s)


def _derive_group(group: dict | None, color_keys: tuple[str, ...]) -> dict | None:
    """A ``chrome``/``page`` token group with its COLOR values dark-derived.

    Only keys in ``color_keys`` invert; every other key (transparencies,
    ``title_align``, ``data_labels``, ``number_format``) passes through, since a
    50% transparency or a "left" alignment has no dark counterpart. Only keys
    the author actually DECLARED appear in the result -- an absent key stays
    absent rather than being fabricated at a derived default. An explicit
    ``None`` is an "off" declaration, not a faint color, so it survives as
    ``None`` instead of being fed to ``_invert_lightness``.

    A falsy group (``None`` or ``{}``) is returned as-is, so the overwhelmingly
    common seed declaring neither group derives byte-identically to before #521.
    A non-empty group with no color key returns a new dict that is value-equal
    to the input -- equal, not the same object.
    """
    if not group:
        return group
    return {
        key: (
            _invert_lightness(value)
            if key in color_keys and value is not None
            else value
        )
        for key, value in group.items()
    }


def derive_dark_seed(light: ThemeSeed) -> ThemeSeed:
    """Derive a dark-mode ThemeSeed from a light one by inverting bg/text
    lightness. Accent/data_colors/sentiment/fonts pass through unchanged; the
    surface (background), on-surface (text), and section 5/6/7 chrome/page
    COLOR roles invert.

    The ``chrome``/``page`` groups (theme-spec sections 5/6/7) derive too: every
    COLOR-valued key in them inverts, while transparencies and formatting keys
    pass through. Before #521 the whole group passed through, so a light seed's
    ``page.background: #FFFFFF`` reached the "dark" theme intact and the emitted
    page card painted a white page under inverted palette text.

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
        chrome=_derive_group(light.chrome, _CHROME_COLOR_KEYS),
        page=_derive_group(light.page, _PAGE_COLOR_KEYS),
    )


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


# Validate and return one spec's ``fg`` (T18 schema: #RRGGBB hex).
def _validated_transparency_fg(role: str, spec: dict) -> object:
    fg = spec.get("fg")
    if not is_valid_hex(fg):
        raise ThemeGenError(
            f"transparency role {role!r} fg is not a #RRGGBB hex: {fg!r}"
        )
    return fg


# Validate and return one spec's ``transparency_pct`` (T18: number in [0, 100]).
def _validated_transparency_pct(role: str, spec: dict) -> float:
    pct = spec.get("transparency_pct")
    if not isinstance(pct, (int, float)) or isinstance(pct, bool):
        raise ThemeGenError(
            f"transparency role {role!r} transparency_pct must be a number, got {pct!r}"
        )
    if not (0.0 <= float(pct) <= 100.0):
        raise ThemeGenError(
            f"transparency role {role!r} transparency_pct {pct!r} is out of "
            f"range -- must be in [0, 100]"
        )
    return float(pct)


# Validate one transparency ``role``/``spec`` pair; return its clean spec.
#
# Split out of ``_validate_transparency`` so the per-role guard clauses (the
# ratified T18 schema: allowed role, dict spec, #RRGGBB fg, numeric pct in
# [0, 100]) live in low-complexity helpers; fg is still checked before pct.
# Raises ThemeGenError (never a bare ValueError/KeyError) on any violation.
def _validate_transparency_role(role: str, spec: object) -> dict:
    if role not in _ALLOWED_TRANSPARENCY_ROLES:
        raise ThemeGenError(
            f"transparency role {role!r} is not allowed -- the ratified "
            f"schema permits only {list(_ALLOWED_TRANSPARENCY_ROLES)}"
        )
    if not isinstance(spec, dict):
        raise ThemeGenError(f"transparency role {role!r} spec must be a dict")
    return {
        "fg": _validated_transparency_fg(role, spec),
        "transparency_pct": _validated_transparency_pct(role, spec),
    }


def _validate_transparency(transparency: dict | None) -> dict | None:
    """Validate an opt-in transparency block; None passes through as None.

    Enforces the OWNER-ratified schema (T18): only the ``overlay`` role, each
    role a ``{"fg": #RRGGBB, "transparency_pct": float in [0, 100]}`` spec.
    Raises ThemeGenError (never a bare ValueError/KeyError) on any violation.
    """
    if transparency is None:
        return None
    if not isinstance(transparency, dict) or not transparency:
        raise ThemeGenError(
            f"transparency must be a non-empty dict of {{role: spec}}, got "
            f"{transparency!r}"
        )
    return {
        role: _validate_transparency_role(role, spec)
        for role, spec in transparency.items()
    }


def _validate_palette_colors(seed: ThemeSeed) -> None:
    """Raise on the first non-#RRGGBB single-color role in ``seed``.

    The eight scalar color roles (accent, background, the text triad, the
    sentiment triad) are checked in a fixed order so the surfaced ThemeGenError
    names the first offending role deterministically. data_colors are validated
    separately in ``_resolve_ramp`` (they may be absent and derived instead).
    """
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


def _resolve_ramp(seed: ThemeSeed) -> list[str]:
    """The data_colors ramp: caller-supplied (validated) or derived from accent.

    A ``None`` data_colors derives a monochromatic ramp from the accent; an
    explicit list is validated hex-by-hex. An empty result is refused *after*
    resolution so an all-blank ``--data-colors`` gets the actionable message
    rather than silently deriving.
    """
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
    return ramp


def build_palette(seed: ThemeSeed) -> dict:
    """Resolve the seed into a full palette dict (fills ramp if none given)."""
    _validate_name(seed.name)
    _validate_palette_colors(seed)
    ramp = _resolve_ramp(seed)
    palette: dict = {
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
    transparency = _validate_transparency(seed.transparency)
    if transparency is not None:
        palette["transparency"] = transparency
    return palette


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


def check_composite_contrast_or_raise(palette: dict, floor: float = AA_FLOOR) -> None:
    """Refuse to proceed if a declared transparency role fails AA once composited.

    WIRED (T18, OWNER-ratified 2026-07-08): ``_validate_and_collect`` invokes
    this in the same choke point as the other gates. It stays a silent no-op
    for every seed that declares no ``transparency`` block (the default), so
    existing callers are unaffected. When a caller DOES declare an ``overlay``
    role, the role's fg is alpha-composited over the background and the result
    must clear the AA floor or the write is refused. Never fabricates a role or
    infers a transparency_pct from color proximity.
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


def _worst_categorical_pair(
    data_colors: tuple[str, ...],
) -> tuple[float, tuple[str, str] | None]:
    """The closest (min CIE76 dE76) i<j pair in ``data_colors``.

    Returns ``(distance, pair)``; ``(float("inf"), None)`` when fewer than 2
    colors are present (no pair to compare). Single source of truth for the
    whole-set pairwise scan shared by ``min_categorical_delta_e`` (distance
    only) and ``check_categorical_distinctness_or_raise`` (distance + pair).
    """
    n = len(data_colors)
    worst = float("inf")
    worst_pair: tuple[str, str] | None = None
    for i in range(n):
        for j in range(i + 1, n):
            d = delta_e76(data_colors[i], data_colors[j])
            if d < worst:
                worst = d
                worst_pair = (data_colors[i], data_colors[j])
    return worst, worst_pair


def min_categorical_delta_e(data_colors: tuple[str, ...]) -> float:
    """Minimum CIE76 deltaE76 over all i<j pairs in data_colors.

    Returns float("inf") when fewer than 2 colors are present (no pair to
    compare, so nothing can violate a distinctness floor).
    """
    return _worst_categorical_pair(data_colors)[0]


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
    worst, worst_pair = _worst_categorical_pair(data_colors)
    if worst < floor and worst_pair is not None:
        raise ThemeGenError(
            f"categorical distinctness: data_colors {worst_pair[0]} and "
            f"{worst_pair[1]} are {worst:.2f} dE76 apart, below the "
            f"{floor:g} dE76 floor -- refusing to write (would fail CT3)"
        )


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


def _non_text_ground(palette: dict, seed: ThemeSeed) -> str:
    """The color gridlines/borders actually render against.

    ``seed.page["background"]`` (theme-spec sections 6/7), when declared,
    OVERRIDES the palette background as the page's real fill -- that is what
    ``render_theme_json`` writes into ``visualStyles["page"]["*"]["background"]``.
    Preferring it here keeps the gate measuring the same ground the compiled
    theme actually paints, instead of a palette color the page may no longer
    show. Falls back to the palette background when no ``page`` group is
    declared, or when it is declared without a ``background`` key -- both keep
    today's behavior unchanged.

    A declared ``background_transparency`` is composited in before the color is
    returned (#521 finding 1): a page background is only the real ground to the
    extent it is opaque. Measuring the raw declared color was wrong in BOTH
    directions -- it let a near-white border pass at 14.60:1 against a
    fully-transparent dark page while truly rendering at 1.23:1, and it refused
    a dark border at 1.43:1 against a fully-transparent white page that truly
    rendered at 12.55:1. So this composites rather than applying a one-sided
    tolerance. Per ``composite_over``, 0 is fully opaque (ground is the declared
    color) and 100 fully transparent (ground is the palette background).
    """
    page = seed.page or {}
    declared = page.get("background")
    palette_bg = palette["colors"]["background"]
    if declared is None:
        return palette_bg
    pct = page.get("background_transparency")
    if pct is None:
        return declared
    # Validate BEFORE compositing. ``composite_over`` raises a bare ValueError
    # for an out-of-range pct and a bare TypeError for a string, and treats
    # ``True`` as 1% -- so passing the raw token through would replace the clean
    # field-named StyleCardError the render path already gives with a traceback
    # naming neither the token nor the file, breaking ThemeGenError's
    # "surfaced cleanly" contract for library callers of this gate.
    # ``bool`` is excluded explicitly: it is an int subclass, so ``True`` would
    # otherwise pass the range check and silently composite at 1% opacity.
    if isinstance(pct, bool) or not isinstance(pct, (int, float)):
        raise ThemeGenError(
            f"page.background_transparency must be a number in [0, 100], got "
            f"{pct!r} ({type(pct).__name__})"
        )
    if not 0 <= pct <= 100:
        raise ThemeGenError(
            f"page.background_transparency must be in [0, 100], got {pct!r}"
        )
    return composite_over(declared, palette_bg, pct)


def check_non_text_contrast_or_raise(
    palette: dict, seed: ThemeSeed, floor: float = AA_NON_TEXT_FLOOR
) -> None:
    """Every declared non-text chrome color must clear ``floor`` on its ground.

    Gridlines and borders sit on the page background -- the EMITTED one (see
    ``_non_text_ground``), not necessarily the palette's, since a declared
    ``page.background`` overrides what the page actually renders. A ``None``
    color is an explicit "off" declaration, not a faint color, so it is
    skipped rather than failed. Raises ``ThemeGenError`` naming the offending
    token.
    """
    chrome = seed.chrome or {}
    ground = _non_text_ground(palette, seed)
    for field in ("gridline", "border"):
        color = chrome.get(field)
        if color is None:
            continue
        if not is_valid_hex(color):
            raise ThemeGenError(f"{field} is not a #RRGGBB hex: {color!r}")
        ratio = contrast_ratio(color, ground)
        if ratio < floor:
            raise ThemeGenError(
                f"{field} {color} has contrast {ratio:.2f}:1 against background "
                f"{ground} -- below the {floor:g}:1 WCAG non-text floor; it would "
                f"be effectively invisible"
            )


def _render_transparency_yaml(palette: dict) -> str:
    """A top-level ``transparency:`` block (sibling of ``colors:``), or "".

    Empty string when no transparency role is declared, so a default theme's
    tokens file is byte-for-byte what it was before T18.
    """
    transparency = palette.get("transparency")
    if not transparency:
        return ""
    lines = ["transparency:\n"]
    for role, spec in transparency.items():
        lines.append(f"  {role}:\n")
        lines.append(f'    fg: "{spec["fg"]}"\n')
        lines.append(f"    transparency_pct: {format_pt(spec['transparency_pct'])}\n")
    return "".join(lines)


def _yaml_scalar(value: object) -> str:
    """One token value as a YAML scalar, in the shape ``theme_compile`` reads
    back: a hex/string is double-quoted, ``None`` is the bare YAML null
    (``null``, never the Python-repr string ``"None"``), a bool is lowercase
    (``true``/``false``, never Python's ``True``/``False``), and a number
    passes through ``format_pt`` (matching ``_render_transparency_yaml``'s
    existing numeric convention).

    A single choke point for every chrome/page scalar so
    ``_render_chrome_yaml``/``_render_page_yaml`` stay a plain per-key loop
    with no per-type branching of their own (keeps cyclomatic complexity low).
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return format_pt(value)
    return f'"{value}"'


def _render_token_group_yaml(header: str, group: dict | None, keys: tuple) -> str:
    """A ``header:`` YAML block over ``keys`` present in ``group``, or "".

    Shared by chrome/page: both are "a header line, then one ``  key: scalar``
    line per declared key, in the fixed ``keys`` order" -- identical shape,
    different vocabulary. Returns "" when ``group`` is None/empty so an
    unset seed field emits nothing (byte-identical to a pre-chrome/page
    tokens file).
    """
    if not group:
        return ""
    lines = [f"{header}:\n"]
    for key in keys:
        if key in group:
            lines.append(f"  {key}: {_yaml_scalar(group[key])}\n")
    return "".join(lines)


def _render_chrome_yaml(chrome: dict | None) -> str:
    """The optional ``chrome:`` block (theme-spec section 5), or "".

    Key order and vocabulary match ``CHROME_TOKEN_KEYS`` -- the same list
    ``theme_compile.chrome_from_tokens`` reads -- so the writer and reader
    agree key-for-key (finding 2).
    """
    from .theme_style_cards import CHROME_TOKEN_KEYS

    return _render_token_group_yaml("chrome", chrome, CHROME_TOKEN_KEYS)


def _render_page_yaml(page: dict | None) -> str:
    """The optional ``page:`` block (theme-spec sections 6+7), or "".

    Key order and vocabulary match ``PAGE_TOKEN_KEYS`` -- the same list
    ``theme_compile.page_from_tokens`` reads -- so the writer and reader agree
    key-for-key (finding 2).
    """
    from .theme_style_cards import PAGE_TOKEN_KEYS

    return _render_token_group_yaml("page", page, PAGE_TOKEN_KEYS)


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
        f"{_render_transparency_yaml(palette)}"
        "typography:\n"
        f"  title_font_pt: {format_pt(seed.title_font_pt)}\n"
        f"  label_font_pt: {format_pt(seed.label_font_pt)}\n"
        "accessibility:\n"
        '  min_text_contrast_ratio: "4.5:1"\n'
        "  # monochromatic ramp: CVD is a named-reviewer call (Principle V)\n"
        "  colorblind_considerate_categoricals: false\n"
        "  do_not_rely_on_color_alone: true\n"
        f"{_render_chrome_yaml(seed.chrome)}"
        f"{_render_page_yaml(seed.page)}"
    )


def render_theme_json(palette: dict, seed: ThemeSeed) -> str:
    c = palette["colors"]
    title_pt = format_pt(seed.title_font_pt)
    label_pt = format_pt(seed.label_font_pt)
    star_style = {
        "title": [{"fontFamily": "Segoe UI Semibold", "fontSize": title_pt}],
        "labels": [{"fontFamily": "Segoe UI", "fontSize": label_pt}],
    }
    # OWNER-ratified T18: the opt-in ``overlay`` role compiles to a Power BI
    # visualStyles background (fg color at its transparency percent). Emitted
    # only when declared; sRGB blend matches how the renderer composites, so the
    # AA proof (check_composite_contrast_or_raise) is faithful to what ships.
    overlay = (palette.get("transparency") or {}).get("overlay")
    if overlay is not None:
        star_style["background"] = [
            {
                "color": {"solid": {"color": overlay["fg"]}},
                "transparency": format_pt(overlay["transparency_pct"]),
            }
        ]
    # Merge, not replace: title/labels already carry font cards above, and
    # build_star_cards can return "title": [{"alignment": ...}] / "labels":
    # [{"show": ...}] -- a plain dict.update would drop fontFamily/fontSize.
    for card, value in build_star_cards(seed.chrome or {}).items():
        if card in star_style:
            star_style[card][0].update(value[0])
        else:
            star_style[card] = value
    visual_styles: dict = {"*": {"*": star_style}}
    page_cards = build_page_cards(seed.page or {})
    if page_cards:
        visual_styles["page"] = {"*": page_cards}
    doc = {
        "name": seed.name,
        "dataColors": c["data_colors"],
        "background": c["background"],
        "foreground": c["text"]["primary"],
        "tableAccent": c["primary"],
        "good": c["sentiment"]["success"],
        "neutral": c["sentiment"]["warning"],
        "bad": c["sentiment"]["danger"],
        "visualStyles": visual_styles,
    }
    return json.dumps(doc, indent=2) + "\n"


def _composite_contrast_line(palette: dict) -> str:
    """A computed `[x]` composite-contrast line, or "" when none is declared.

    Only emitted when a transparency role exists, so a default theme's spec is
    unchanged. A `[x]` here is a proven arithmetic fact (the role already passed
    check_composite_contrast_or_raise before any write), never a human-judgment
    claim.
    """
    transparency = palette.get("transparency")
    if not transparency:
        return ""
    bg = palette["colors"]["background"]
    parts = []
    for role, spec in transparency.items():
        composited = composite_over(spec["fg"], bg, spec["transparency_pct"])
        ratio = contrast_ratio(composited, bg)
        parts.append(
            f"{role} {spec['fg']} at {spec['transparency_pct']:g}% -> "
            f"{composited} = {ratio:.2f}:1"
        )
    return (
        "- [x] **Composite transparency contrast** -- (computed): "
        f"{'; '.join(parts)} vs background (all >= {AA_FLOOR:g}:1 AA). "
        "*Evidence: sRGB alpha-composite arithmetic on the committed "
        "transparency roles (proves the composited number, not on-screen "
        "legibility).*\n"
    )


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
        "- [x] **Font floor** (computed): title "
        f"{seed.title_font_pt:g}pt >= {MIN_TITLE_FONT_PT:g}pt, label "
        f"{seed.label_font_pt:g}pt >= {MIN_LABEL_FONT_PT:g}pt. *Evidence: "
        "check_font_floor_or_raise on the committed tokens (a number proves "
        "the number, not on-screen legibility).*\n"
        "- [x] **Categorical distinctness (whole-set)** -- CT3 (computed): "
        f"min pairwise dE76 across data_colors = "
        f"{min_categorical_delta_e(tuple(c['data_colors'])):.2f}, "
        f">= {MIN_CATEGORICAL_DELTAE:g} dE76 floor. *Evidence: CIE76 "
        "arithmetic on the committed ramp (normal-vision near-collapse "
        "guard only -- NOT a colorblind-safe claim).*\n"
        f"{_composite_contrast_line(palette)}"
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


def _gate_and_render(seed: ThemeSeed, repo_root: Path) -> dict[Path, str]:
    """Every value-level self-check on ``seed``, plus the rendered target set.

    Split out from ``_validate_and_collect`` so a caller can distinguish a
    VALUE failure (a token the seed cannot legally carry) from a target-collision
    failure (a file already on disk). ``generate_pair`` needs that distinction: a
    value failure on a derived seed is attributable to the derivation, while a
    collision is about the filesystem and is fixed with ``--force`` -- advice
    about "the light values it derives from" would be actively wrong there.

    Rendering is INSIDE this boundary, not after it, because several token gates
    fire lazily while cards are built rather than in an explicit ``check_*``
    call -- ``_outspace_pane_card``'s filter-pane AA floor is one, reached only
    via ``render_theme_json``. Excluding rendering would leave those failures
    unattributed, which is the very defect this split exists to fix.
    """
    palette = build_palette(seed)
    check_contrast_or_raise(palette)
    check_font_floor_or_raise(seed)
    check_categorical_distinctness_or_raise(palette)
    check_ramp_deltae_or_raise(palette, MIN_ADJACENT_DELTAE)
    check_composite_contrast_or_raise(palette)
    check_non_text_contrast_or_raise(palette, seed)
    return _targets_for(seed, repo_root, palette)


def _validate_and_collect(
    seed: ThemeSeed, repo_root: Path, force: bool
) -> dict[Path, str]:
    """Run every self-check + build the target set; raise before any write.

    This is the single choke point for pre-write gates: contrast, font floor,
    categorical distinctness (whole-set), adjacent-ramp deltaE (near-collapse),
    and composite-transparency AA (opt-in overlay role) today, with room for
    future self-checks to slot in here too, so a caller validating multiple
    seeds (e.g. a light/dark pair) can validate all of them before writing any.
    """
    targets = _gate_and_render(seed, repo_root)
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
    # Only the GATE phase is wrapped. The dark seed is DERIVED, not authored, so
    # an unattributed gate error reads as a fault in the author's tokens and
    # sends them to debug the wrong file: inverting both halves of a pair
    # preserves neither their contrast ratio nor its sign, so a filter-pane pair
    # that cleared AA in light mode can legitimately fail once derived (#521 D1
    # -- that refusal is correct; only its attribution was missing).
    # A target COLLISION is deliberately left outside this try: it is about the
    # filesystem, not the derivation, and is fixed with --force. Wrapping it too
    # would append "adjust the light values it derives from", which is actively
    # wrong advice -- reproducing the very misattribution this block exists to
    # prevent.
    try:
        dark_targets = _gate_and_render(dark, repo_root)
    except (ThemeGenError, StyleCardError) as exc:
        raise ThemeGenError(
            f"--pair: the DERIVED dark seed {dark.name!r} failed validation: "
            f"{exc} -- this is the dark seed derived from your light tokens, "
            f"not the light tokens themselves; adjust the light values it "
            f"derives from, or author the dark theme explicitly instead of "
            f"using --pair"
        ) from exc
    # OUTSIDE the wrapper: a collision is a filesystem fact, not a derivation
    # fault, and its "use --force" guidance must reach the caller verbatim.
    if not force:
        for p in dark_targets:
            if p.exists():
                raise ThemeGenError(
                    f"{p} exists -- refusing to overwrite (use --force)"
                )
    light_written = _write_targets(light_targets)
    dark_written = _write_targets(dark_targets)
    return light_written, dark_written


def _parse_data_colors(raw: str | None) -> tuple[str, ...] | None:
    """Split a ``--data-colors`` CSV into a tuple, or None to derive a ramp.

    An absent flag or an all-blank value (``""``, ``" , "``) both mean "derive
    the ramp from the accent" -- neither is a real caller-supplied palette.
    """
    if not raw:
        return None
    dcs = tuple(s.strip() for s in raw.split(",") if s.strip())
    return dcs or None


def _text_roles_from_args(args) -> tuple[str, str, str]:
    """Resolve (primary, secondary, muted) text colors with cascading fallback.

    Each unset role falls back to the next-more-prominent one, so a caller
    only has to supply --text-primary and still gets a coherent triad.
    """
    primary = args.text_primary
    secondary = args.text_secondary or primary
    muted = args.text_muted or secondary
    return primary, secondary, muted


def _sentiment_from_args(args) -> tuple[str, str, str]:
    """Resolve (good, neutral, bad) sentiment colors, defaulting per-role."""
    return (
        args.good or _DEFAULT_SENTIMENT["good"],
        args.neutral or _DEFAULT_SENTIMENT["neutral"],
        args.bad or _DEFAULT_SENTIMENT["bad"],
    )


def _font_pt_from_args(args) -> tuple[float, float]:
    """Resolve (title, label) font sizes, defaulting to the MIN_* floors.

    References MIN_TITLE_FONT_PT / MIN_LABEL_FONT_PT rather than
    re-hardcoding 12.0/9.0: those constants equal ThemeSeed's own field
    defaults, so this is a single source of truth, not a coincidence.
    """
    title = args.title_font_pt if args.title_font_pt is not None else MIN_TITLE_FONT_PT
    label = args.label_font_pt if args.label_font_pt is not None else MIN_LABEL_FONT_PT
    return title, label


def _transparency_from_args(args) -> dict | None:
    """Build the opt-in overlay transparency block from CLI args, or None.

    Returns None when neither overlay flag is given (the default -- no
    transparency). A partial spec (one flag without the other) is passed
    through as-is so ``build_palette``'s ``_validate_transparency`` raises the
    single clean ThemeGenError, rather than duplicating that guard here.
    """
    fg = getattr(args, "overlay_fg", None)
    pct = getattr(args, "overlay_transparency_pct", None)
    if fg is None and pct is None:
        return None
    return {"overlay": {"fg": fg, "transparency_pct": pct}}


def _seed_from_args(args) -> ThemeSeed:
    """Assemble a ThemeSeed from argparse ``theme-gen`` args (pure, no I/O)."""
    text_primary, text_secondary, text_muted = _text_roles_from_args(args)
    good, neutral, bad = _sentiment_from_args(args)
    title_font_pt, label_font_pt = _font_pt_from_args(args)
    return ThemeSeed(
        name=args.name,
        mode=args.mode,
        accent=args.accent,
        background=args.background,
        text_primary=text_primary,
        text_secondary=text_secondary,
        text_muted=text_muted,
        data_colors=_parse_data_colors(args.data_colors),
        good=good,
        neutral=neutral,
        bad=bad,
        title_font_pt=title_font_pt,
        label_font_pt=label_font_pt,
        transparency=_transparency_from_args(args),
    )


def theme_gen_main(args) -> int:
    """CLI entry: assemble a ThemeSeed from argparse args, generate, report."""
    seed = _seed_from_args(args)
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
    for p in written:
        print(f"wrote {p}")
    print(
        f"suggested themes/README.md line: - `{args.name}.theme.json` -- "
        f"generated starter ({args.mode}); validate in Power BI Desktop; "
        f"readiness = warning."
    )
    return 0
