"""Design-lint rule DL1: theme JSON purity (surface 3).

Enforces the surface-3 purity contract in ``docs/powerbi/theme-json.md``: a theme
file carries styling DEFAULTS only (colors, fonts, visual/page/filter-pane
defaults, sentiment COLORS) and MUST NOT carry business logic -- DAX, measures,
calculated columns/tables, metric definitions, semantic-model relationships,
source mapping, sentiment thresholds/rules, or data validation. A forbidden key
in a committed theme file is an ERROR with a file-plus-pointer locator; a clean
styling-only file produces no findings.

Vocabulary is the frozen, generic literal set resolved in the spec's
Clarifications (RESOLVED 2026-07-01), derived verbatim from the theme-json.md
MUST-NOT categories -- no tenant/example/brand literal (Principle VII). The scan
is categorical over KEY NAMES only, never over free-text values (FR-005).

Matching is deliberately SUBSTRING containment on the normalized key (so
``calculatedTable`` and ``calculated-table`` both match ``calculated``). Two
consequences are intentional, frozen trade-offs (FR-013), not defects:
- Possible FALSE POSITIVE: a future non-standard styling key whose normalized
  name merely contains a short token (``rule``, ``measure``) would be flagged
  (e.g. a hypothetical ``rulerColor``). No real Microsoft-documented theme key
  or the committed starter theme collides today; a contributor who hits a
  surprise DL1 failure on a genuinely-innocuous key resolves it by adding that
  key to ``_ALLOWED_KEYS`` (a deliberate, reviewed vocabulary change).
- Deliberate FALSE NEGATIVE: business-flavored keys that contain none of the 12
  tokens (e.g. ``sourceColumn``, ``kpiGoalValue``) are MUST-NOT-only out of
  scope; widening the vocabulary is a follow-on rule change, never a silent edit.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "DL1"

# Committed theme files are discovered generically by this suffix (never an
# enumerated or tenant-specific list -- Principle VII, FR-002).
_THEME_SUFFIX = ".theme.json"

# FROZEN forbidden token set -- the resolved Principle-V vocabulary (spec
# Clarifications 2026-07-01), derived directly from the theme-json.md MUST-NOT
# categories. A key is a violation when its NORMALIZED name (lowercased,
# separators removed) equals or CONTAINS any of these tokens (so
# ``calculated-table``, ``calculatedTable`` and ``calculated_table`` all match).
# Generic only: no tenant/example/brand literal appears here.
_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "dax",
    "measure",
    "calculatedcolumn",
    "calculatedtable",
    "calculated",
    "expression",
    "threshold",
    "rule",
    "relationship",
    "sourcemapping",
    "validation",
    "metricdefinition",
)

# Sentiment-adjacent COLOR keys and structural color/accent keys stay ALLOWED
# explicitly: a sentiment COLOR is styling; a sentiment THRESHOLD/RULE is
# business meaning (forbidden above). Normalized (lowercased, separators
# removed) for a stable match. Any key in this set is never flagged even if it
# would otherwise contain a forbidden token.
_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "good",
        "neutral",
        "bad",
        "datacolors",
        "foreground",
        "background",
        "tableaccent",
    }
)


def _normalize(key: str) -> str:
    """Lowercase and strip separators (-, _, spaces) for a stable token match."""
    return key.lower().replace("-", "").replace("_", "").replace(" ", "")


def _iter_theme_files(ctx: RuleContext) -> list[str]:
    """Committed theme files, generic discovery, test fixtures exempted (FR-010)."""
    return [
        p
        for p in ctx.tracked_files
        if p.endswith(_THEME_SUFFIX) and not is_test_path(p)
    ]


def _is_forbidden(key: str) -> str | None:
    """Return the matched forbidden token for ``key``, or None if allowed.

    Categorical present/absent check on the KEY NAME only (FR-005). An explicit
    allowed key is never flagged even if it contains a forbidden substring.
    """
    normalized = _normalize(key)
    if normalized in _ALLOWED_KEYS:
        return None
    for token in _FORBIDDEN_TOKENS:
        if token in normalized:
            return token
    return None


def _walk(node: Any, pointer: str, rel: str) -> Iterable[Finding]:
    """Recursively walk a parsed JSON node, flagging forbidden KEY names.

    Emits one finding per distinct forbidden-key occurrence (FR-004); the
    locator is ``file#/json/pointer`` to the offending key so no violation is
    masked by another (each occurrence has its own pointer path).
    """
    if isinstance(node, dict):
        for key, value in node.items():
            child_pointer = f"{pointer}/{key}"
            token = _is_forbidden(key)
            if token is not None:
                yield Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"theme file carries a forbidden business-logic key "
                        f"{key!r} (matches {token!r}); a theme is styling "
                        f"defaults only, business meaning belongs in another "
                        f"surface (see docs/powerbi/theme-json.md)"
                    ),
                    locator=f"{rel}#{child_pointer}",
                )
            # Recurse into the value regardless: a forbidden key may be nested
            # inside an otherwise-allowed object (FR-003, C2).
            yield from _walk(value, child_pointer, rel)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _walk(item, f"{pointer}/{index}", rel)
    # Scalars (str/int/float/bool/None) are VALUES, never scanned (FR-005).


@register(RULE_ID, "Theme JSON carries styling defaults only, no business logic")
def check_theme_purity(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in _iter_theme_files(ctx):
        path = ctx.repo_root / rel
        try:
            with path.open(encoding="utf-8-sig") as fh:
                doc: Any = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            # FR-009: a committed theme file that cannot be parsed is surfaced as
            # a finding -- never a crash, never a silent pass.
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"theme file could not be parsed as JSON "
                        f"({exc.__class__.__name__}); it cannot be verified for "
                        f"purity and must be valid JSON"
                    ),
                    locator=f"{rel}#/",
                )
            )
            continue
        findings.extend(_walk(doc, "", rel))
    return findings
