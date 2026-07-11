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
    "Categorical data_colors entries meet the declared whole-set deltaE76 "
    "distinctness floor",
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
