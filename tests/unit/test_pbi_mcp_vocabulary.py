"""Spec 149 T002 -- the write adapter's outcome vocabulary is the shipped one.

The adapter must not own a second copy of the execution outcome words. A local
redefinition would drift silently from ``seshat.dagster_adapter`` and become a
second source of truth (research R1).

These tests pin BEHAVIOR, not the absence of a symbol: asserting
``not hasattr(module, "OUTCOMES")`` would go green the moment the capability
shipped under a different name, which is the defect this repo has already been
bitten by. Instead we assert the value the adapter actually exposes.
"""

from __future__ import annotations

import pytest

from seshat import pbi_mcp_adapter
from seshat.dagster_adapter import OUTCOMES as SHIPPED_OUTCOMES

pytestmark = pytest.mark.unit


def test_outcome_set_is_identical_to_the_shipped_vocabulary() -> None:
    """The adapter re-exports the shipped set rather than redefining it."""
    assert pbi_mcp_adapter.OUTCOMES == SHIPPED_OUTCOMES


def test_outcome_set_is_the_same_object_not_a_copy() -> None:
    """Identity, not just equality.

    An equal-but-separate frozenset is exactly the drift this task exists to
    prevent: it passes an equality check today and diverges the first time the
    shipped set gains a member.
    """
    assert pbi_mcp_adapter.OUTCOMES is SHIPPED_OUTCOMES


def test_outcome_set_has_the_five_documented_members() -> None:
    """Five values, not four (research R1 corrected an earlier assumption)."""
    assert pbi_mcp_adapter.OUTCOMES == frozenset(
        {"materialized", "failed", "skipped", "blocked", "deferred"}
    )


@pytest.mark.parametrize("readiness_token", ["pass", "warning", "blocked_stage"])
def test_readiness_tokens_are_not_execution_outcomes(readiness_token: str) -> None:
    """An execution outcome is never a readiness verdict (hard rule #9).

    ``blocked`` IS a legitimate execution outcome, so this deliberately tests
    ``blocked_stage`` rather than ``blocked`` -- the point is that no readiness
    *stage* vocabulary leaks in, not that the word is banned.
    """
    assert readiness_token not in pbi_mcp_adapter.OUTCOMES


def test_pass_is_specifically_absent() -> None:
    """Called out on its own because it is the one that would matter.

    If ``pass`` ever became an execution outcome, a green write would be
    indistinguishable from a readiness approval -- the precise conflation
    FR-018 forbids.
    """
    assert "pass" not in pbi_mcp_adapter.OUTCOMES
