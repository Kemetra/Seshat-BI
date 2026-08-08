"""Governed dbt transformation adapter.

This package deliberately imports no dbt module or database driver. External dbt
execution is resolved lazily by the runner in the active Python environment.
"""

from __future__ import annotations

DBT_CORE_VERSION = "1.12.0"
DBT_POSTGRES_VERSION = "1.10.2"
PROFILE_NAME = "seshat_bi_warehouse"
TARGET_NAME = "shadow"

# ``CommandResult.outcome`` / ``RunEvidence.outcome`` spell exit-0 as the word
# "pass", which is ALSO a readiness four-status token. Anything that reports a
# dbt result outside the adapter must translate it first, so an execution result
# can never be read as a stage verdict (hard rule #9). This is the ONE
# definition: the dagster adapter and the evidence reader both import it rather
# than keeping private copies.
OUTCOME_TO_EXECUTION = {
    "pass": "built",
    "failed": "failed",
    "blocked": "blocked",
    "unavailable": "blocked",
}

# An outcome this mapping does not know is not a success. Callers resolve it via
# ``OUTCOME_TO_EXECUTION.get(outcome, UNKNOWN_EXECUTION)`` so an unrecognized
# upstream status fails closed.
UNKNOWN_EXECUTION = "blocked"

__all__ = [
    "DBT_CORE_VERSION",
    "DBT_POSTGRES_VERSION",
    "OUTCOME_TO_EXECUTION",
    "PROFILE_NAME",
    "TARGET_NAME",
    "UNKNOWN_EXECUTION",
]
