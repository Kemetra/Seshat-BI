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

from dataclasses import dataclass

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


# ---------------------------------------------------------------------------
# Remediation metadata -- WHO acts on a blocker, from a committed allowlist.
#
# `classify` answers what is blocked and which surface is next. It does not
# answer the question that decides who acts. That answer is a COMMITTED LOOKUP
# keyed by category -- never advice generated per blocker, because free-form
# remediation text is exactly where an agent would start inventing steps the
# governance model does not sanction.
#
# `classify`'s return shape is deliberately UNCHANGED: `blocker_explainer` and
# `approver_view` both consume it, so this is added alongside rather than folded
# in.
# ---------------------------------------------------------------------------

# Two values only, no numeric axis (hard rule #9):
#   human_only -- cannot be cleared without a named human decision.
#   mechanical -- an agent can produce the next artifact or setup step. It does
#                 NOT mean the stage then clears on its own; a stage that
#                 requires approval still requires the named human.
_HUMAN_ONLY = "human_only"
_MECHANICAL = "mechanical"


@dataclass(frozen=True)
class Remediation:
    """Who acts on a blocker of one category, where to read, and when to stop."""

    remediation: str
    doc: str
    stop_condition: str


_REMEDIATION: dict[str, Remediation] = {
    "approval": Remediation(
        remediation=_HUMAN_ONLY,
        doc="docs/readiness/readiness-model.md",
        stop_condition=(
            "stop and request the named human's decision; never record an "
            "approval on their behalf"
        ),
    ),
    "grain": Remediation(
        remediation=_HUMAN_ONLY,
        doc="docs/readiness/mapping-ready.md",
        stop_condition=(
            "stop at the grain/PK question; propose options with evidence and "
            "let the owner rule"
        ),
    ),
    "live_validation": Remediation(
        remediation=_MECHANICAL,
        doc="docs/readiness/gold-ready.md",
        stop_condition=(
            "stop if the boundary is unavailable -- record [PENDING LIVE "
            "PROFILE] and a warning, never a fabricated pass"
        ),
    ),
    "artifact": Remediation(
        remediation=_MECHANICAL,
        doc="docs/readiness/source-ready.md",
        stop_condition=(
            "stop before filling any judgment call the artifact asks for; "
            "author the structure, propose the semantics"
        ),
    ),
    "readiness": Remediation(
        remediation=_HUMAN_ONLY,
        doc="docs/readiness/readiness-model.md",
        stop_condition=(
            "stop and surface the recorded blocker verbatim; it is unclassified, "
            "so do not infer a fix"
        ),
    ),
}

# Fail-safe default. An UNCLASSIFIED category must never be reported as
# agent-fixable: defaulting to `mechanical` would invite an agent to act on a
# blocker nobody categorized. The safe direction is always toward the human.
_UNKNOWN_REMEDIATION = Remediation(
    remediation=_HUMAN_ONLY,
    doc="docs/readiness/readiness-model.md",
    stop_condition=(
        "stop: this blocker's category is unrecognized, so no remediation is "
        "sanctioned -- escalate to a named human"
    ),
)


def remediation_of(category: str) -> Remediation:
    """The committed remediation metadata for ``category``.

    An unknown category returns the fail-safe ``human_only`` entry rather than
    raising: a blocker report must still render when a category is unrecognized,
    and it must not claim the blocker is agent-fixable.
    """
    return _REMEDIATION.get(category, _UNKNOWN_REMEDIATION)
