"""Design-lint rule CT1: WCAG contrast pre-check (surface 3, accessibility / A3).

A deterministic, read-only accessibility check. CT1 computes the WCAG 2.x sRGB
relative-luminance contrast ratio between committed static token colors and
compares each DECLARED text/background pair against the token-declared floor.
A pair below the floor is an ERROR carrying the computed ratio; a pair at or
above the floor is clean.

DECLARED pairs only (Principle V -- CT1 checks the correspondences the tokens
themselves annotate ("a legible hierarchy on light surfaces (WCAG AA target)",
each text color "AA on bg"), and never invents which pairs matter):
  * ``colors.text.{primary,secondary,muted}`` vs ``colors.background`` at the
    ``accessibility.min_text_contrast_ratio`` floor.

NOT a fabricated confidence score (hard rule #9): the ratio is deterministic
arithmetic on committed hexes, surfaced as a pass/fail categorical test against
a declared threshold. Read-only: parses committed YAML, renders no pixel, opens
no DB, writes nothing. Generic: field names only, no tenant/brand literal
(Principle VII).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..color import (
    channel_luminance as _channel_luminance,  # noqa: F401  (kept for import stability)
)
from ..color import (
    contrast_ratio as _contrast_ratio,
)
from ..color import (
    relative_luminance as _relative_luminance,  # noqa: F401  (kept for import stability)
)
from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

# WCAG math lives in the shared helper (seshat.color) so the CT1 rule and the
# theme generator apply identical arithmetic. The three names above are
# re-exported under their original private names to preserve every existing
# import (e.g. tests/unit/test_design_contrast.py imports _contrast_ratio).

RULE_ID = "CT1"

_TOKENS_SUFFIX = "-design-tokens.yaml"
_TOKENS_BASENAMES = ("tokens.yaml",)

# The declared text roles checked against the background (tokens annotate these
# as "AA on bg"). Generic role names, not a tenant literal.
_TEXT_ROLES = ("primary", "secondary", "muted")


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
    """Parse a ``"4.5:1"`` (or ``4.5``) floor into a float ratio, else None."""
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        head = raw.split(":", 1)[0].strip()
        try:
            return float(head)
        except ValueError:
            return None
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
    background = colors.get("background")
    text = colors.get("text", {})
    if not isinstance(text, dict) or background is None:
        return  # nothing declared to check
    access = doc.get("accessibility", {}) if isinstance(doc, dict) else {}
    floor = _parse_floor(access.get("min_text_contrast_ratio"))
    if floor is None:
        yield Finding(
            RULE_ID,
            Severity.ERROR,
            "tokens declare text colors on a background but no parseable "
            "accessibility.min_text_contrast_ratio floor; contrast cannot be "
            "verified",
            f"{rel}#/accessibility/min_text_contrast_ratio",
        )
        return
    for role in _TEXT_ROLES:
        color = text.get(role)
        if color is None:
            continue
        try:
            ratio = _contrast_ratio(color, background)
        except ValueError:
            yield Finding(
                RULE_ID,
                Severity.ERROR,
                f"text.{role} {color!r} is not a valid #RRGGBB hex; its "
                f"contrast against the background could not be computed",
                f"{rel}#/colors/text/{role}",
            )
            continue
        if ratio < floor:
            yield Finding(
                RULE_ID,
                Severity.ERROR,
                f"text.{role} {color!r} on background {background!r} has "
                f"contrast {ratio:.2f}:1, below the declared floor {floor:g}:1",
                f"{rel}#/colors/text/{role}",
            )


@register(
    RULE_ID, "Token text/background color pairs meet the declared WCAG contrast floor"
)
def check_contrast(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in _iter_tokens_files(ctx):
        doc, err = _load_yaml(ctx.repo_root / rel)
        if err is not None:
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"design-tokens file could not be parsed ({err}); "
                    f"contrast cannot be verified",
                    f"{rel}#/",
                )
            )
            continue
        findings.extend(_check_tokens(rel, doc))
    return findings
