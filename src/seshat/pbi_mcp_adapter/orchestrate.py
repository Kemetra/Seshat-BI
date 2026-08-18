"""Spec 149 T029 -- the one path from a write request to a terminal state.

Sequence, and it is not negotiable:

    bypass guard -> gate -> [intent record] -> execute -> validate -> evidence

Every terminal state emits exactly **one** evidence record, refusals included
(FR-015). Nothing here advances a readiness stage or writes ``approvals[]``: a
successful write leaves ``publish_ready`` exactly as it found it (FR-018).

The bypass guard is called unconditionally and first, and it *raises* -- so a
future edit that forgets to inspect a verdict still cannot reach the runtime with
the flag set. The gate is evaluated here rather than accepted from the caller,
for the same reason every precondition inside the gate is derived rather than
asserted: a caller who can hand in a cleared verdict is a caller who can lie.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from seshat.pbi_mcp.detect import refuse_if_bypass_flag
from seshat.pbi_mcp_adapter import evidence, gate, runner, validation

#: Exit codes, per contracts/cli-contract.md. 2 and 3 stay DISTINCT: collapsing
#: them would let a caller treat an indeterminate write as a clean failure.
EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_VALIDATION_FAILED = 2
EXIT_INDETERMINATE = 3


@dataclass(frozen=True)
class WriteReport:
    """What one run did, and how it ended."""

    exit_code: int
    outcome: str
    blockers: tuple[str, ...]
    rollback_guidance: tuple[str, ...]
    evidence_path: Path | None
    mutation_attempted: bool

    @property
    def succeeded(self) -> bool:
        return self.exit_code == EXIT_OK


def _finalize(
    repo_root: Path,
    *,
    target_id: str,
    operation_id: str,
    timestamp: str,
    outcome: str,
    mutation_attempted: bool,
    blockers: tuple[str, ...],
    rollback_guidance: tuple[str, ...] = (),
    mode: str,
    tool: str,
) -> Path:
    record = evidence.RunEvidence(
        tool=tool,
        mode=mode,
        target_id=target_id,
        operation_id=operation_id,
        timestamp=timestamp,
        outcome=outcome,
        mutation_attempted=mutation_attempted,
        blockers=blockers,
        rollback_guidance=rollback_guidance,
    )
    return evidence.finalize(repo_root, record)


def apply_write(
    repo_root: Path,
    *,
    target_id: str,
    operation_id: str,
    timestamp: str,
    tree_clean: bool | None = None,
    backup_ref: str | None = None,
    argv: tuple[str, ...] = (),
    config_state: str | None = None,
    dry_run: bool = False,
    mcp_runner: object = None,
    validator: object = None,
) -> WriteReport:
    """Run the governed write pipeline for one target.

    ``dry_run`` is the ``plan-write`` leg: it evaluates every precondition and
    mutates nothing. It still emits an evidence record -- a ``deferred`` one --
    so "every run produces exactly one record" stays literally true and an
    operator cannot probe the gate repeatedly without a trace.
    """
    root = Path(repo_root)
    mode = "readonly" if dry_run else "readwrite"

    # 1. The standing prohibition, before anything else, in every mode. Raises.
    refuse_if_bypass_flag(argv, config_state=config_state, context="pbi-mcp apply")

    # 2. The four (now nine) preconditions, all derived here.
    verdict = gate.evaluate(
        root,
        target_id,
        operation_id,
        tree_clean=tree_clean,
        backup_ref=backup_ref,
    )

    if not verdict.cleared:
        path = _finalize(
            root,
            target_id=target_id,
            operation_id=operation_id,
            timestamp=timestamp,
            outcome="blocked",
            mutation_attempted=False,
            blockers=verdict.blockers,
            mode=mode,
            tool="none",
        )
        return WriteReport(
            exit_code=EXIT_REFUSED,
            outcome="blocked",
            blockers=verdict.blockers,
            rollback_guidance=(),
            evidence_path=path,
            mutation_attempted=False,
        )

    allowlist, _ = gate.read_allowlist(root)
    entry = allowlist[target_id]

    if dry_run:
        # Everything cleared, but plan-write mutates nothing by contract.
        path = _finalize(
            root,
            target_id=target_id,
            operation_id=operation_id,
            timestamp=timestamp,
            outcome="deferred",
            mutation_attempted=False,
            blockers=(),
            mode=mode,
            tool="none",
        )
        return WriteReport(
            exit_code=EXIT_OK,
            outcome="deferred",
            blockers=(),
            rollback_guidance=(),
            evidence_path=path,
            mutation_attempted=False,
        )

    # 3. Intent BEFORE the mutation, so a crash still leaves a trace (M4).
    evidence.write_intent(
        root,
        tool=runner.VENDOR_PACKAGE,
        mode=mode,
        target_id=target_id,
        operation_id=operation_id,
        timestamp=timestamp,
    )

    # 4. Execute.
    result = runner.invoke(
        verdict,
        target_path=entry.path,
        operation_id=operation_id,
        repo_root=root,
        read_only=False,
        runner=mcp_runner,
    )

    guidance = validation.rollback_guidance_for(entry.path, backup_ref)

    if not result.succeeded:
        # A stalled or crashed runtime may have left the artifact half-written,
        # so this is indeterminate rather than a clean failure.
        indeterminate = result.mutation_attempted
        path = _finalize(
            root,
            target_id=target_id,
            operation_id=operation_id,
            timestamp=timestamp,
            outcome="blocked" if indeterminate else "failed",
            mutation_attempted=result.mutation_attempted,
            blockers=result.blockers or ("PBIMCP-RUN-04",),
            rollback_guidance=guidance,
            mode=mode,
            tool=runner.VENDOR_PACKAGE,
        )
        return WriteReport(
            exit_code=EXIT_INDETERMINATE if indeterminate else EXIT_REFUSED,
            outcome="blocked" if indeterminate else "failed",
            blockers=result.blockers,
            rollback_guidance=guidance,
            evidence_path=path,
            mutation_attempted=result.mutation_attempted,
        )

    # 5. Validate. A zero exit from the runtime is not confirmation.
    outcome = validation.validate_semantic_model(
        root,
        target_path=entry.path,
        backup_ref=backup_ref,
        runner=validator,
    )

    if not outcome.passed:
        path = _finalize(
            root,
            target_id=target_id,
            operation_id=operation_id,
            timestamp=timestamp,
            outcome="failed",
            mutation_attempted=True,
            blockers=outcome.blockers,
            rollback_guidance=outcome.rollback_guidance or guidance,
            mode=mode,
            tool=runner.VENDOR_PACKAGE,
        )
        return WriteReport(
            exit_code=EXIT_VALIDATION_FAILED,
            outcome="failed",
            blockers=outcome.blockers,
            rollback_guidance=outcome.rollback_guidance or guidance,
            evidence_path=path,
            mutation_attempted=True,
        )

    # 6. Materialized: applied AND confirmed by validation.
    path = _finalize(
        root,
        target_id=target_id,
        operation_id=operation_id,
        timestamp=timestamp,
        outcome="materialized",
        mutation_attempted=True,
        blockers=(),
        mode=mode,
        tool=runner.VENDOR_PACKAGE,
    )
    return WriteReport(
        exit_code=EXIT_OK,
        outcome="materialized",
        blockers=(),
        rollback_guidance=(),
        evidence_path=path,
        mutation_attempted=True,
    )
