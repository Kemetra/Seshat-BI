"""seshat.pbi_mcp_adapter -- control layer for the Power BI MCP write adapter.

Spec 149 (F016 slice 5), authorized by ADR 0018. Constants and small read-only
units only; this package NEVER imports the vendor runtime -- Microsoft's
official Power BI Modeling MCP always runs as a child process invoked through
``npx`` (external, unforked, never vendored: ADR 0018 rejected alternative,
Principle II).

Authority boundary: the four write preconditions and the named human decide
every readiness stage. Nothing in this package writes a readiness ``status``, a
``Gate status``, or an ``approvals[]`` entry. A successful mutation moves no
stage (FR-018) -- evidence is proof of what ran, never an approval.

Read-only is the resting state (FR-001). Write mode is an armed exception that
is unreachable until all four preconditions clear, and ``--skipconfirmation`` is
refused in every mode including read-only and including in tests (FR-002).
"""

from __future__ import annotations

# The execution outcome vocabulary. Imported, NOT redefined: a second local
# copy would drift from the shipped adapter and become a second source of truth
# (research R1). NEVER contains the readiness token "pass" (hard rule #9) --
# an execution outcome is not a readiness verdict, and the vocabulary test
# asserts that separation directly.
from seshat.dagster_adapter import OUTCOMES

__all__ = ["OUTCOMES"]
