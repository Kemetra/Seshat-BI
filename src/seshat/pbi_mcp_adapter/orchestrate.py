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

import functools
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


def _terminate(
    repo_root: Path,
    *,
    exit_code: int,
    outcome: str,
    target_id: str,
    operation_id: str,
    timestamp: str,
    mode: str,
    tool: str,
    mutation_attempted: bool,
    blockers: tuple[str, ...] = (),
    rollback_guidance: tuple[str, ...] = (),
) -> WriteReport:
    """Write the terminal evidence record and return the matching report.

    One helper for both, so the report and the record cannot disagree -- an
    earlier version substituted a fallback blocker into the record only, and exit
    3 became reachable with an empty report blocker list.
    """
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
    path = evidence.finalize(repo_root, record)
    return WriteReport(
        exit_code=exit_code,
        outcome=outcome,
        blockers=blockers,
        rollback_guidance=rollback_guidance,
        evidence_path=path,
        mutation_attempted=mutation_attempted,
    )


def _execute_and_confirm(
    root,
    *,
    verdict,
    entry,
    guidance: tuple[str, ...],
    backup_ref: str | None,
    mcp_runner: object,
    validator: object,
    terminal,
) -> WriteReport:
    """Execute the authorized mutation, then prove it did what it claimed.

    Split out of :func:`apply_write` so the pre-flight gates and the
    execute/confirm phase read as two things. Every exit here is terminal.
    """
    # A before/after snapshot, so a claim of success can be checked against what
    # actually changed. The target path and operation come from the VERDICT --
    # there is no parameter by which to substitute another.
    before = _snapshot(root)
    result = runner.invoke(verdict, repo_root=root, read_only=False, runner=mcp_runner)

    if not result.succeeded:
        # A stalled or crashed runtime may have left the artifact half-written, so
        # this is indeterminate rather than a clean failure.
        indeterminate = result.mutation_attempted
        return terminal(
            exit_code=EXIT_INDETERMINATE if indeterminate else EXIT_REFUSED,
            outcome="blocked" if indeterminate else "failed",
            tool=runner.VENDOR_PACKAGE,
            mutation_attempted=result.mutation_attempted,
            blockers=result.blockers or (runner.BLOCKER_RUNTIME_UNEXPLAINED,),
            rollback_guidance=guidance,
        )

    # Did the run do what it was authorized to do? A no-op and an out-of-scope
    # mutation both previously reported `materialized`.
    effect_blockers = _effect_blockers(before, _snapshot(root), entry.path)
    if effect_blockers:
        return terminal(
            exit_code=EXIT_VALIDATION_FAILED,
            outcome="failed",
            tool=runner.VENDOR_PACKAGE,
            mutation_attempted=True,
            blockers=effect_blockers,
            rollback_guidance=guidance,
        )

    # A zero exit from the runtime is not confirmation.
    outcome = validation.validate_semantic_model(
        root, target_path=entry.path, backup_ref=backup_ref, runner=validator
    )
    if not outcome.passed:
        return terminal(
            exit_code=EXIT_VALIDATION_FAILED,
            outcome="failed",
            tool=runner.VENDOR_PACKAGE,
            mutation_attempted=True,
            blockers=outcome.blockers,
            rollback_guidance=outcome.rollback_guidance or guidance,
        )

    # Applied AND confirmed by validation.
    return terminal(
        exit_code=EXIT_OK,
        outcome="materialized",
        tool=runner.VENDOR_PACKAGE,
        mutation_attempted=True,
    )


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

    Sequence, and it is not negotiable:
    bypass guard -> gate -> drift -> [intent record] -> execute -> effect check
    -> validate -> evidence.

    ``dry_run`` is the ``plan-write`` leg: it evaluates every precondition and
    mutates nothing. It still emits a ``deferred`` evidence record, so "every run
    produces exactly one record" stays literally true and an operator cannot probe
    the gate repeatedly without a trace.
    """
    root = Path(repo_root)
    mode = "readonly" if dry_run else "readwrite"
    terminal = functools.partial(
        _terminate,
        root,
        target_id=target_id,
        operation_id=operation_id,
        timestamp=timestamp,
        mode=mode,
    )

    # 1. The standing prohibition, before anything else, in every mode. Raises.
    refuse_if_bypass_flag(argv, config_state=config_state, context="pbi-mcp apply")

    # 2. Every precondition, all derived inside the gate.
    verdict = gate.evaluate(
        root, target_id, operation_id, tree_clean=tree_clean, backup_ref=backup_ref
    )

    # 3. Vendor preview drift. Gated on DRIFT rather than version compatibility:
    # the supported range is permanently `unknown` while both servers are
    # unreleased previews, so a compatibility gate would block forever.
    drift_blockers = (
        capability_profile.blockers
        if not dry_run and capability_profile is not None
        else ()
    )

    if not verdict.cleared or drift_blockers:
        return terminal(
            exit_code=EXIT_REFUSED,
            outcome="blocked",
            tool="none",
            mutation_attempted=False,
            blockers=(*verdict.blockers, *drift_blockers),
        )

    allowlist, _ = gate.read_allowlist(root)
    entry = allowlist[target_id]
    guidance = validation.rollback_guidance_for(entry.path, backup_ref)

    if dry_run:
        # Everything cleared, but plan-write mutates nothing by contract.
        return terminal(
            exit_code=EXIT_OK,
            outcome="deferred",
            tool="none",
            mutation_attempted=False,
        )

    # 4. Intent BEFORE the mutation, so a crash still leaves a trace.
    evidence.write_intent(
        root,
        evidence.RunIdentity(
            tool=runner.VENDOR_PACKAGE,
            mode=mode,
            target_id=target_id,
            operation_id=operation_id,
            timestamp=timestamp,
        ),
    )

    # 5-7. Execute, confirm the effect, validate.
    return _execute_and_confirm(
        root,
        verdict=verdict,
        entry=entry,
        guidance=guidance,
        backup_ref=backup_ref,
        mcp_runner=mcp_runner,
        validator=validator,
        terminal=terminal,
    )
