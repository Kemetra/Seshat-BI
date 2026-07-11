"""Shared readiness-blocker classifier (extracted from blocker_explainer, #229).

The fixed category rank + keyword classifier that maps a readiness blocking
reason to a category. EXTRACTED verbatim from ``blocker_explainer.py`` so both
``blocker_explainer`` (which explains blockers) and ``approver_view`` (spec 115,
which re-sequences committed evidence refutation-first for a signer) share ONE
rank definition instead of each carrying a copy.

The category ORDER is the load-bearing artifact: ``approver_view`` orders its
refusal case by this fixed rank (approval > grain > live_validation > artifact >
readiness). The rank is a committed lookup, never a computed/synthesized value
(hard rule #9). This module is stdlib-only.
"""

from __future__ import annotations

# (category, keyword markers, explanation, next_surface). ORDER IS THE RANK:
# earlier tuples outrank later ones in a refutation-first ordering.
_CATEGORY_RULES: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    (
        "approval",
        ("approval", "approved", "reviewed", "sign-off", "signoff"),
        (
            "A named human approval or review is missing or invalid; the agent "
            "must not self-grant it."
        ),
        "approval inbox",
    ),
    (
        "grain",
        ("grain", "pk", "primary key", "unique"),
        (
            "The mapping gate is blocked on grain or key certainty; resolve "
            "the named grain/PK question before silver work."
        ),
        "approval request or source-mapping review",
    ),
    (
        "live_validation",
        ("dsn", "db extra", "deferred", "validate", "orphan", "reconciliation"),
        (
            "The live validation boundary is not clear; configure the DB/live "
            "validation path or resolve the recorded live finding."
        ),
        "retail validate setup",
    ),
    (
        "artifact",
        ("missing", "absent", "does not exist", "unfilled"),
        (
            "A required committed artifact is missing or unfilled; author the "
            "artifact before proceeding."
        ),
        "readiness artifact authoring",
    ),
)
_DEFAULT_CATEGORY = (
    "readiness",
    (
        "A readiness blocker is recorded; resolve the cited fact before moving "
        "to a later stage."
    ),
    "retail next",
)

# The category names in rank order -- the refutation-first ordering key
# approver_view sorts by. Derived from _CATEGORY_RULES so it can never drift.
CATEGORY_RANK: tuple[str, ...] = tuple(rule[0] for rule in _CATEGORY_RULES) + (
    _DEFAULT_CATEGORY[0],
)


def classify(reason: str) -> tuple[str, str, str]:
    """Map a blocking reason to (category, explanation, next_surface) by the
    fixed keyword rules; the default category catches anything unmatched."""
    lowered = reason.lower()
    for category, markers, explanation, next_surface in _CATEGORY_RULES:
        if any(marker in lowered for marker in markers):
            return category, explanation, next_surface
    category, explanation, next_surface = _DEFAULT_CATEGORY
    return category, explanation, next_surface


def rank_of(category: str) -> int:
    """The refutation-first rank index of a category (lower = weigh first). An
    unknown category sorts last (after the default 'readiness' bucket)."""
    try:
        return CATEGORY_RANK.index(category)
    except ValueError:
        return len(CATEGORY_RANK)
