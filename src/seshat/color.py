"""Shared, stdlib-only sRGB/WCAG color math.

The single source of truth for the WCAG 2.x relative-luminance contrast ratio.
Both the CT1 governance rule (seshat.rules.design_contrast) and the theme
generator (seshat.theme_gen) import from here, so the generator's pre-write
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


def format_pt(value: float) -> float | int:
    """Render a point size as ``int`` when integral, else keep the float.

    Prevents committed integral font sizes (``12``, ``9``) from churning to
    ``12.0``/``9.0`` on every regeneration -- a purely cosmetic JSON-shape
    change with no accessibility meaning.
    """
    return int(value) if value == int(value) else value
