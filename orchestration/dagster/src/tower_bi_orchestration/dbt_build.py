"""The governed dbt-engine bridge for the silver/gold build assets (spec 135).

When a layer resolves to ``engine: dbt``, the build asset delegates HERE instead
of applying committed migration SQL. This bridge is a THIN adapter over the
already-committed ``seshat.dbt`` control layer: it runs the SAME governed build
the ``seshat dbt build`` CLI runs -- plan -> self-accept the recomputed
accept-plan digest -> governed BUILD in isolated shadow schemas -> sanitized dbt
run-evidence -- and maps the outcome onto a dagster execution outcome.

Governance invariants this bridge preserves (FR-002/FR-003, plan-review R5):

* NO raw dbt selector, target, profile, or arbitrary argument is ever passed:
  the caller supplies only ``(table, layer)``; the governed selector is
  table-wide by governance (``seshat_table_<table>``) and lives inside
  ``seshat.dbt``. This module imports NO ``dagster_dbt`` execution API and never
  invokes the dbt binary directly -- it goes only through ``seshat.dbt``.
* The dbt build is TABLE-WIDE and LAYER-AGNOSTIC. Each dbt-resolved layer asset
  runs the full governed build independently (so a mixed configuration where
  only gold is dbt still rebuilds the whole shadow graph); ``layer`` never
  scopes the dbt node selection -- narrowing it would fork the governed selector
  and break the accept-plan digest.
* Every surfaced error passes the shared redaction before it leaves this module
  (Principle IX); a governed refusal or an absent dbt runtime becomes a concrete
  ``blocked`` reason with a named owner -- never a traceback.
"""

from __future__ import annotations

from pathlib import Path

from seshat.cli.commands.dbt import (
    ArtifactIntegrityError,
    CommandResult,
    DbtUnavailable,
    EnvironmentConfigError,
    GovernanceError,
    HandledDbtFailure,
    LockUnavailable,
    Operation,
    PlanDrift,
    load_child_environment,
    run_governed_build,
)
from seshat.dagster_adapter.redaction import redact_text

# A governed refusal / unavailable / lock contention is a BLOCK with a named
# owner; a completed-but-failed governed run (tests/parity/artifacts) is a
# FAILED asset. Neither ever fabricates a pass.
_BLOCK_OWNER = "the dbt runtime owner"

# The dbt engine's deferred boundary: the governed dbt build reads its live
# profile from the SESHAT_DBT_* child environment (spec 133), NOT from the
# migrations DSN -- so its absence, not the migrations DSN's, is what defers
# the dbt path (Codex review on PR #307).
DBT_DEFERRED_BOUNDARY = (
    "deferred: no live dbt profile (SESHAT_DBT_* absent); the governed dbt "
    "build stays [PENDING LIVE PROFILE]"
)


def profile_present(root: Path) -> bool:
    """True when the governed dbt live profile resolves for this checkout.

    Reads the same child environment the governed runner reads (.env included).
    A MALFORMED .env deliberately returns True: the build then proceeds into
    ``run_governed_build``, whose ``EnvironmentConfigError`` this bridge maps to
    a redacted ``blocked`` outcome -- one handling site, never a traceback.
    """
    try:
        environment = load_child_environment(Path(root))
    except EnvironmentConfigError:
        return True
    return bool(environment.get("SESHAT_DBT_HOST"))


# The seshat.dbt CommandResult.outcome uses the readiness word "pass" for its
# own exit-0 semantics. The dagster record MUST NEVER carry "pass" (hard rule
# #9): translate it to an execution word the moment it crosses into dagster.
_DBT_OUTCOME_TO_EXECUTION = {
    "pass": "built",
    "failed": "failed",
    "blocked": "blocked",
    "unavailable": "blocked",
}


def _measured_from_result(result: CommandResult, table: str) -> dict:
    """Derived, redaction-safe measured fields for the dagster record.

    Carries the governed selector, the translated dbt execution word, and a
    citation of the dbt evidence -- NEVER the readiness token ``pass`` and never
    a numeric score (hard rule #9). The dbt run-evidence JSON stays a DISTINCT
    artifact (FR-009); we cite its path, never merge it.
    """
    # An outcome word this map does not know is treated as BLOCKED, never as a
    # success word: a future seshat.dbt outcome must fail closed here, not be
    # translated into "built" (evidence fidelity; Fable review).
    dbt_result = _DBT_OUTCOME_TO_EXECUTION.get(result.outcome, "blocked")
    measured: dict = {
        "engine": "dbt",
        "selector": f"seshat_table_{table}",
        "dbt_result": dbt_result,
        "dbt_evidence_path": result.evidence_path,
    }
    if result.blocking_reasons:
        measured["dbt_blocking_reasons"] = [
            {k: redact_text(str(v)) for k, v in reason.items()}
            for reason in result.blocking_reasons
        ]
    if result.exit_code != 0:
        # A COMPLETED-but-non-green governed run (dbt models/tests failed, or a
        # parity block): _execute RETURNS this rather than raising. Surface the
        # dagster-facing outcome the caller halts on -- `failed` (ran-and-failed)
        # or `blocked` (precondition), NOT the generic default -- with a concrete
        # redacted reason and a named owner (evidence fidelity on the live path).
        measured["outcome"] = dbt_result
        measured["blocking_reason"] = redact_text(_first_reason(result))
        measured["owner"] = _BLOCK_OWNER
    return measured


def _first_reason(result: CommandResult) -> str:
    """The most concrete reason a completed non-green run can offer."""
    for reason in result.blocking_reasons:
        message = reason.get("message")
        if message:
            return f"governed dbt build {result.outcome}: {message}"
    return f"governed dbt build {result.outcome}"


def _blocked(reason: str, exit_code: int) -> tuple[int, dict, None]:
    measured = {
        "engine": "dbt",
        "outcome": "blocked",
        "blocking_reason": redact_text(reason),
        "owner": _BLOCK_OWNER,
    }
    return exit_code or 1, measured, None


def build_layer(
    context: object, table: str, layer: str, root: Path
) -> tuple[int, dict, str | None]:
    """Run the governed table-wide dbt build for one dbt-resolved layer asset.

    Returns ``(exit_code, measured, dbt_evidence_path)``. ``exit_code == 0`` is
    the ONLY success; the caller then runs the SAME ``seshat check`` gate.
    ``layer`` selects only WHICH asset delegated here -- it never scopes the dbt
    node selection (the governed selector is table-wide).
    """
    try:
        result = run_governed_build(Path(root), table, Operation.BUILD)
    except (
        DbtUnavailable,
        EnvironmentConfigError,
        GovernanceError,
        LockUnavailable,
        PlanDrift,
    ) as exc:
        # Governed refusal or absent/unavailable dbt runtime -> BLOCK fail-closed
        # with a concrete redacted reason and a named owner (FR-006). No traceback.
        return _blocked(str(exc), exit_code=1)
    except (HandledDbtFailure, ArtifactIntegrityError) as exc:
        # A completed governed run whose models/tests/artifacts failed -> FAILED.
        measured = {
            "engine": "dbt",
            "outcome": "failed",
            "blocking_reason": redact_text(str(exc)),
            "owner": _BLOCK_OWNER,
        }
        return 1, measured, None
    measured = _measured_from_result(result, table)
    return result.exit_code, measured, result.evidence_path
