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
from seshat.pbi_mcp_adapter import drift, evidence, gate, runner, validation

#: Exit codes, per contracts/cli-contract.md. 2 and 3 stay DISTINCT: collapsing
#: them would let a caller treat an indeterminate write as a clean failure.
EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_VALIDATION_FAILED = 2
EXIT_INDETERMINATE = 3


#: A runtime exit of 0 is a claim, not proof. These name what the claim failed.
BLOCKER_TARGET_UNCHANGED = "PBIMCP-EFF-01"
BLOCKER_OUT_OF_SCOPE_CHANGE = "PBIMCP-EFF-02"

BLOCKER_DETAIL: dict[str, str] = {
    BLOCKER_TARGET_UNCHANGED: (
        "the runtime reported success but the target's bytes are unchanged; a "
        "no-op is reported honestly, never as an applied change"
    ),
    BLOCKER_OUT_OF_SCOPE_CHANGE: (
        "the run modified files outside the authorized target; only the resolved "
        "allowlist path may change"
    ),
}


def _digest(path: Path) -> str | None:
    """SHA-256 of ``path``, or None when absent."""
    import hashlib

    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _snapshot(repo_root: Path) -> dict[str, str]:
    """Digest every tracked-or-untracked file, so an out-of-scope write is visible.

    Uses git so ignored files (including this adapter's own evidence artifact) are
    excluded -- otherwise the evidence write would itself look like scope creep.
    """
    from seshat.gitstate import run_git

    try:
        listed = run_git(
            repo_root, "ls-files", "--cached", "--others", "--exclude-standard"
        )
    except (OSError, RuntimeError):
        return {}
    if listed.returncode != 0:
        return {}
    snapshot: dict[str, str] = {}
    for line in listed.stdout.splitlines():
        rel = line.strip().strip('"')
        if not rel:
            continue
        digest = _digest(repo_root / rel)
        if digest is not None:
            snapshot[rel] = digest
    return snapshot


def _effect_blockers(
    before: dict[str, str], after: dict[str, str], authorized: str
) -> tuple[str, ...]:
    """What the run actually did, versus what it was authorized to do.

    Exit 0 from the vendor runtime proves only that the process ended well. It
    does not prove the intended artifact changed, nor that nothing else did.
    """
    found: list[str] = []
    target = authorized.replace("\\", "/")
    changed = {
        rel for rel in set(before) | set(after) if before.get(rel) != after.get(rel)
    }
    if target not in changed:
        found.append(BLOCKER_TARGET_UNCHANGED)
    if changed - {target}:
        found.append(BLOCKER_OUT_OF_SCOPE_CHANGE)
    return tuple(found)


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
    capability_profile: drift.RuntimeCapabilityProfile | None = None,
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

    # 2b. Vendor preview drift. Gated on DRIFT rather than version compatibility:
    # the supported range is permanently `unknown` while both servers are
    # unreleased previews, so a compatibility gate would block forever. A drifted
    # runtime may have moved the very flag names the bypass matcher pins.
    drift_blockers: tuple[str, ...] = ()
    if not dry_run and capability_profile is not None:
        drift_blockers = capability_profile.blockers

    if not verdict.cleared or drift_blockers:
        combined = (*verdict.blockers, *drift_blockers)
        path = _finalize(
            root,
            target_id=target_id,
            operation_id=operation_id,
            timestamp=timestamp,
            outcome="blocked",
            mutation_attempted=False,
            blockers=combined,
            mode=mode,
            tool="none",
        )
        return WriteReport(
            exit_code=EXIT_REFUSED,
            outcome="blocked",
            blockers=combined,
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

    # 4. Execute, with a before/after snapshot so a claim of success can be
    # checked against what actually changed.
    before = _snapshot(root)
    result = runner.invoke(
        verdict,
        repo_root=root,
        read_only=False,
        runner=mcp_runner,
    )

    guidance = validation.rollback_guidance_for(entry.path, backup_ref)

    if not result.succeeded:
        # A stalled or crashed runtime may have left the artifact half-written,
        # so this is indeterminate rather than a clean failure.
        indeterminate = result.mutation_attempted
        # Computed ONCE: passing result.blockers to the report while substituting
        # a fallback into the evidence made the two disagree, and exit 3 was
        # reachable with an empty blocker list.
        reported_blockers = result.blockers or (runner.BLOCKER_RUNTIME_UNEXPLAINED,)
        path = _finalize(
            root,
            target_id=target_id,
            operation_id=operation_id,
            timestamp=timestamp,
            outcome="blocked" if indeterminate else "failed",
            mutation_attempted=result.mutation_attempted,
            blockers=reported_blockers,
            rollback_guidance=guidance,
            mode=mode,
            tool=runner.VENDOR_PACKAGE,
        )
        return WriteReport(
            exit_code=EXIT_INDETERMINATE if indeterminate else EXIT_REFUSED,
            outcome="blocked" if indeterminate else "failed",
            blockers=reported_blockers,
            rollback_guidance=guidance,
            evidence_path=path,
            mutation_attempted=result.mutation_attempted,
        )

    # 4b. Did the run do what it was authorized to do? A no-op and an
    # out-of-scope mutation both previously reported `materialized`.
    effect_blockers = _effect_blockers(before, _snapshot(root), entry.path)
    if effect_blockers:
        path = _finalize(
            root,
            target_id=target_id,
            operation_id=operation_id,
            timestamp=timestamp,
            outcome="failed",
            mutation_attempted=True,
            blockers=effect_blockers,
            rollback_guidance=guidance,
            mode=mode,
            tool=runner.VENDOR_PACKAGE,
        )
        return WriteReport(
            exit_code=EXIT_VALIDATION_FAILED,
            outcome="failed",
            blockers=effect_blockers,
            rollback_guidance=guidance,
            evidence_path=path,
            mutation_attempted=True,
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
