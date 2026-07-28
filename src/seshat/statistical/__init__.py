"""Governed statistical evidence contracts.

The numerical implementations are imported lazily by the method registry.
Importing this package keeps every optional numerical dependency unloaded.
"""

from .contracts import (
    AnalysisEvidence,
    AnalysisSpec,
    Blocker,
    ColumnBinding,
    Diagnostic,
    Estimate,
    Interval,
    MethodSpec,
    Outcome,
    TestStatistic,
)

ENGINE_VERSION = "1.0"

__all__ = [
    "ENGINE_VERSION",
    "AnalysisEvidence",
    "AnalysisSpec",
    "Blocker",
    "ColumnBinding",
    "Diagnostic",
    "Estimate",
    "Interval",
    "MethodSpec",
    "Outcome",
    "TestStatistic",
]
