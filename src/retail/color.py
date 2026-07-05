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
