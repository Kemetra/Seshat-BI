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


_RGB_TO_LMS = (
    (17.8824, 43.5161, 4.11935),
    (3.45565, 27.1554, 3.86714),
    (0.0299566, 0.184309, 1.46709),
)

_LMS_TO_RGB = (
    (0.0809444479, -0.130504409, 0.116721066),
    (-0.0102485335, 0.0540193266, -0.113614708),
    (-0.000365296938, -0.00412161469, 0.693511405),
)


def _encode_srgb_channel(linear: float) -> int:
    """Inverse of ``channel_luminance``: linear light -> a 0-255 sRGB channel."""
    c = 0.0 if linear < 0.0 else (1.0 if linear > 1.0 else linear)
    s = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1.0 / 2.4) - 0.055
    return round(max(0.0, min(1.0, s)) * 255.0)


def _hex_to_linear_rgb(hex_color: str) -> tuple[float, float, float]:
    """``#RRGGBB`` -> linear-light RGB, reusing the shared sRGB linearization."""
    h = hex_color.lstrip("#")
    r, g, b = (channel_luminance(int(h[i : i + 2], 16)) for i in (0, 2, 4))
    return (r, g, b)


def _apply_matrix(
    matrix: tuple[tuple[float, float, float], ...],
    vector: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Multiply a 3x3 matrix by a 3-vector."""
    x, y, z = vector
    return tuple(row[0] * x + row[1] * y + row[2] * z for row in matrix)  # type: ignore[return-value]


def _project_lms(
    lms: tuple[float, float, float], deficiency: str
) -> tuple[float, float, float]:
    """Project an LMS triple onto the dichromat plane for ``deficiency``."""
    long_, medium, short = lms
    if deficiency == "protanope":
        return (2.02344 * medium - 2.52581 * short, medium, short)
    if deficiency == "deuteranope":
        return (long_, 0.494207 * long_ + 1.24827 * short, short)
    if deficiency == "tritanope":
        return (long_, medium, -0.395913 * long_ + 0.801109 * medium)
    raise ValueError(f"unknown deficiency: {deficiency!r}")


def simulate_cvd(hex_color: str, deficiency: str) -> str:
    """``#RRGGBB`` as it appears under one colour-vision deficiency.

    Deterministic, closed-form, stdlib-only: linearize sRGB (reusing
    ``channel_luminance``), convert to LMS cone space, project onto the
    dichromat plane for ``deficiency``, convert back, and re-encode. Same input
    always yields byte-identical output -- no randomness, no data, no model.

    The LMS matrices and the three plane projections are the Vienot, Brettel &
    Mollon (1999) set, applied to LINEAR-light RGB (some published
    implementations apply them to gamma-encoded values instead; this module
    commits to the linear convention and is internally consistent).

    Being a projection, it is idempotent to within rounding: simulating an
    already-simulated colour returns essentially the same colour. The unit
    tests pin that property, which is what makes the matrix pair verifiable
    without trusting a transcribed reference table.

    This is a MEASUREMENT aid only. It produces no verdict, no score, and no
    statement that a palette is or is not colorblind-safe -- those stay a named
    reviewer's call (hard rule #9, Principle V).
    """
    if not is_valid_hex(hex_color):
        raise ValueError(f"not a #RRGGBB hex color: {hex_color!r}")

    linear = _hex_to_linear_rgb(hex_color)
    lms = _apply_matrix(_RGB_TO_LMS, linear)
    projected = _project_lms(lms, deficiency)
    out = _apply_matrix(_LMS_TO_RGB, projected)
    return "#" + "".join(f"{_encode_srgb_channel(v):02X}" for v in out)


def simulate_protanope(hex_color: str) -> str:
    """``#RRGGBB`` under protanopia (absent long-wave/red cones)."""
    return simulate_cvd(hex_color, "protanope")


def simulate_deuteranope(hex_color: str) -> str:
    """``#RRGGBB`` under deuteranopia (absent medium-wave/green cones)."""
    return simulate_cvd(hex_color, "deuteranope")


def simulate_tritanope(hex_color: str) -> str:
    """``#RRGGBB`` under tritanopia (absent short-wave/blue cones)."""
    return simulate_cvd(hex_color, "tritanope")


CVD_DEFICIENCIES: tuple[str, ...] = ("protanope", "deuteranope", "tritanope")


def format_pt(value: float) -> float | int:
    """Render a point size as ``int`` when integral, else keep the float.

    Prevents committed integral font sizes (``12``, ``9``) from churning to
    ``12.0``/``9.0`` on every regeneration -- a purely cosmetic JSON-shape
    change with no accessibility meaning.
    """
    return int(value) if value == int(value) else value
