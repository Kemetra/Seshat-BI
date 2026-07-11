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
