"""Shared coverage-status vocabulary (SL1's closed five-value enum).

Extracted from ``rules/scorecard.py`` (spec 117) so the SL1 rule and the
read-only ``gap_detector`` surface share ONE status vocabulary instead of two
parallel copies that could drift. The move is behavior-preserving: ``_ENUM`` and
``_norm`` are unchanged, so SL1's rule output stays byte-identical (regression-
locked by ``tests/unit/test_scorecard.py``).

The vocabulary is a status + named blocker, NEVER a number (hard rule #9).
"""

from __future__ import annotations

import re

# The five closed coverage statuses (F8 vocabulary). Compared after dash-
# normalization so an ASCII "--" and a unicode em-dash both match.
_ENUM: frozenset[str] = frozenset(
    {
        "covered",
        "blocked -- missing field",
        "blocked -- needs business definition",
        "planned",
        "out of scope",
    }
)

# Proper-case ASCII display forms (Principle IX: "--", never an em-dash). Each
# normalizes back into _ENUM -- asserted by a test so the two never drift.
COVERED = "Covered"
BLOCKED_MISSING_FIELD = "Blocked -- missing field"
BLOCKED_NEEDS_DEFINITION = "Blocked -- needs business definition"
PLANNED = "Planned"
OUT_OF_SCOPE = "Out of scope"

# Fixed display order (no computed rank; used only for stable rendering).
STATUSES: tuple[str, ...] = (
    COVERED,
    BLOCKED_MISSING_FIELD,
    BLOCKED_NEEDS_DEFINITION,
    PLANNED,
    OUT_OF_SCOPE,
)


def _norm(cell: str) -> str:
    """Lower-case, strip backticks, and normalize dashes for the enum compare."""
    s = cell.strip().strip("`").strip().lower()
    s = s.replace("—", "--").replace("–", "--")  # em/en dash -> --
    s = re.sub(r"\s*--\s*", " -- ", s)  # collapse spacing around --
    return re.sub(r"\s+", " ", s).strip()


def is_member(status: str) -> bool:
    """True if ``status`` (any dash/case form) is one of the five SL1 statuses."""
    return _norm(status) in _ENUM
