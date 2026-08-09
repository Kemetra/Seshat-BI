"""Spec 152: upstream-backed Seshat owners must declare their delta.

Spec 118's ownership oracle already required a declared ``seshat-adapter`` to
say what Seshat adds. Phase 11 showed that guard was constructible-around: a
non-adapter Seshat owner (``seshat-orchestrator``, ``seshat-governance``, ...)
could name an ``upstream_project`` and still declare no differentiated
responsibility. These cases pin the widened rule and, just as importantly, its
boundaries -- an upstream owner is never obliged to invent a Seshat delta, and
internal Seshat ownership keeps its existing contract.

The detector under test lives in ``_capability_public_ownership``; the O1-O8
inventory cases stay in ``test_capability_inventory``.
"""

from __future__ import annotations

import pytest

from tests.unit import _capability_public_ownership as oracle

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("delta", [None, "", "   "])
def test_ownership_rejects_upstream_backed_seshat_owner_without_delta(
    delta: str | None,
) -> None:
    """Spec 152 FR-001: every upstream-backed Seshat layer states its delta."""
    ownership: dict[str, object] = {
        "capability_owner": "seshat-orchestrator",
        "upstream_project": "official-project",
    }
    if delta is not None:
        ownership["seshat_delta"] = delta

    problems = oracle.ownership_violations(
        {"id": "upstream-wrapper", "ownership": ownership}
    )

    assert problems, f"upstream-backed Seshat owner with delta={delta!r} was accepted"
    assert any("upstream-wrapper" in problem for problem in problems)
    assert any("seshat_delta" in problem for problem in problems)


@pytest.mark.parametrize(
    "owner",
    sorted(token for token in oracle.OWNERSHIP_OWNERS if token.startswith("seshat-")),
)
def test_every_upstream_backed_seshat_owner_requires_delta(owner: str) -> None:
    """Spec 152 FR-002: derive Seshat owners from the existing vocabulary."""
    problems = oracle.ownership_violations(
        {
            "id": f"upstream-{owner}",
            "ownership": {
                "capability_owner": owner,
                "upstream_project": "official-project",
            },
        }
    )

    assert any("seshat_delta" in problem for problem in problems), problems


@pytest.mark.parametrize("owner", ["official-upstream", "vendored-upstream"])
def test_non_seshat_upstream_owner_does_not_require_delta(owner: str) -> None:
    """Spec 152 FR-004: upstream owners do not invent a Seshat delta."""
    entry = {
        "id": f"upstream-{owner}",
        "ownership": {
            "capability_owner": owner,
            "upstream_project": "official-project",
        },
    }

    assert oracle.ownership_violations(entry) == []


def test_internal_seshat_owner_without_upstream_does_not_require_delta() -> None:
    """Spec 152 FR-004: internal Seshat ownership keeps its existing contract."""
    entry = {
        "id": "internal-governance",
        "ownership": {"capability_owner": "seshat-governance"},
    }

    assert oracle.ownership_violations(entry) == []


def test_upstream_backed_seshat_owner_accepts_concrete_delta() -> None:
    """Spec 152 FR-001: a concrete differentiated responsibility is valid."""
    entry = {
        "id": "governed-wrapper",
        "ownership": {
            "capability_owner": "seshat-governance",
            "upstream_project": "official-project",
            "seshat_delta": "applies the pre-gate and records normalized evidence",
        },
    }

    assert oracle.ownership_violations(entry) == []
