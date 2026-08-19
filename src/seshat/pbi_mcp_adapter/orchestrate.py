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


@dataclass(frozen=True)
class _Ending:
    """How one run ended: the exit code, the outcome, and what explains them.

    Bundled because the record and the report must describe the SAME ending. An
    earlier version passed these separately and substituted a fallback blocker
    into the record only, which made exit 3 reachable with an empty report
    blocker list. One value cannot disagree with itself.
    """

    exit_code: int
    outcome: str
    mutation_attempted: bool
    blockers: tuple[str, ...] = ()
    rollback_guidance: tuple[str, ...] = ()


def _terminate(
    repo_root: Path, identity: evidence.RunIdentity, ending: _Ending
) -> WriteReport:
    """Write the terminal evidence record and return the matching report.

    One helper for both, so the report and the record cannot disagree.

    ``identity`` carries who/what/when and ``ending`` carries how it finished;
    the caller pre-binds the four fixed identity fields and varies only ``tool``
    via :meth:`evidence.RunIdentity.with_tool`.
    """
    record = evidence.RunEvidence(
        tool=identity.tool,
        mode=identity.mode,
        target_id=identity.target_id,
        operation_id=identity.operation_id,
        timestamp=identity.timestamp,
        outcome=ending.outcome,
        mutation_attempted=ending.mutation_attempted,
        blockers=ending.blockers,
        rollback_guidance=ending.rollback_guidance,
    )
    path = evidence.finalize(repo_root, record)
    return WriteReport(
        exit_code=ending.exit_code,
        outcome=ending.outcome,
        blockers=ending.blockers,
        rollback_guidance=ending.rollback_guidance,
        evidence_path=path,
        mutation_attempted=ending.mutation_attempted,
    )


@dataclass(frozen=True)
class _Execution:
    """Everything the execute/confirm phase needs, as one value.

    Deliberately WITHOUT defaults. ``mcp_runner``, ``validator`` and ``terminal``
    are injection seams: a default would let a call site omit one and still
    construct, which is how an injected seam goes quietly dead. Requiring all
    fields makes an incomplete construction a TypeError at the call site.
    """

    verdict: object
    #: The path the GATE authorized, taken from the cleared verdict. Never
    #: re-read from the allowlist after authorization: a second read can see a
    #: different HEAD or worktree, and then the executed write, the effect check,
    #: the validation and the rollback guidance can all refer to different paths.
    authorized_path: str
    guidance: tuple[str, ...]
    backup_ref: str | None
    mcp_runner: object
    validator: object
    terminal: object


def _execute_and_confirm(root: Path, plan: _Execution) -> WriteReport:
    """Execute the authorized mutation, then prove it did what it claimed.

    Split out of :func:`_run_pipeline` so the pre-flight gates and the
    execute/confirm phase read as two things. Every exit here is terminal.
    """
    verdict = plan.verdict
    authorized_path = plan.authorized_path
    guidance = plan.guidance
    terminal = plan.terminal
    # A before/after snapshot, so a claim of success can be checked against what
    # actually changed. The target path and operation come from the VERDICT --
    # there is no parameter by which to substitute another.
    before = _snapshot(root)
    result = runner.invoke(
        verdict, repo_root=root, read_only=False, runner=plan.mcp_runner
    )

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
    effect_blockers = _effect_blockers(before, _snapshot(root), authorized_path)
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
        root,
        target_path=authorized_path,
        backup_ref=plan.backup_ref,
        runner=plan.validator,
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


@dataclass(frozen=True)
class _WriteRequest:
    """What the caller asked for, as one value.

    ``apply_write`` keeps its keyword-only public signature -- the CLI contract --
    while the pipeline helpers pass one thing rather than re-threading nine
    parameters each.
    """

    target_id: str
    operation_id: str
    timestamp: str
    tree_clean: bool | None
    backup_ref: str | None
    argv: tuple[str, ...]
    config_state: str | None
    mcp_runner: object
    validator: object
    capability_profile: drift.RuntimeCapabilityProfile | None


def _preflight(
    root: Path, request: _WriteRequest, *, dry_run: bool
) -> tuple[object, tuple[str, ...]]:
    """Steps 1-3: the standing prohibition, the gate, then vendor drift.

    Extracted as a unit because the three run in a fixed order and none may be
    reordered or skipped. Returns the verdict plus any drift blockers; it decides
    nothing terminal, so the caller still owns every exit and the evidence record
    that goes with it.
    """
    # 1. The standing prohibition, before anything else, in every mode. Raises.
    refuse_if_bypass_flag(
        request.argv, config_state=request.config_state, context="pbi-mcp apply"
    )

    # 2. Every precondition, all derived inside the gate.
    verdict = gate.evaluate(
        root,
        request.target_id,
        request.operation_id,
        gate.GitState(tree_clean=request.tree_clean, backup_ref=request.backup_ref),
    )

    # 3. Vendor preview drift. Gated on DRIFT rather than version compatibility:
    # the supported range is permanently `unknown` while both servers are
    # unreleased previews, so a compatibility gate would block forever.
    profile = request.capability_profile
    drift_blockers = profile.blockers if not dry_run and profile is not None else ()
    return verdict, drift_blockers


def _run_pipeline(root: Path, request: _WriteRequest, *, dry_run: bool) -> WriteReport:
    """The governed sequence itself, over an already-bundled request.

    Sequence, and it is not negotiable:
    bypass guard -> gate -> drift -> [intent record] -> execute -> effect check
    -> validate -> evidence.

    Separated from the public :func:`apply_write` so the keyword-only CLI
    signature stays exactly as the contract specifies while the pipeline reads
    against one value.
    """
    mode = "readonly" if dry_run else "readwrite"
    identity = evidence.RunIdentity(
        tool="none",
        mode=mode,
        target_id=request.target_id,
        operation_id=request.operation_id,
        timestamp=request.timestamp,
    )

    def terminal(*, tool: str, **kwargs: object) -> WriteReport:
        """Terminate with ``tool`` swapped into the pre-bound identity."""
        return _terminate(root, identity.with_tool(tool), _Ending(**kwargs))  # type: ignore[arg-type]

    # 1-3. Bypass guard, gate, drift -- in that order, none skippable.
    verdict, drift_blockers = _preflight(root, request, dry_run=dry_run)

    if not verdict.cleared or drift_blockers:
        return terminal(
            exit_code=EXIT_REFUSED,
            outcome="blocked",
            tool="none",
            mutation_attempted=False,
            blockers=(*verdict.blockers, *drift_blockers),
        )

    # The gate already resolved and bound the target. `cleared` requires
    # `authorized_path is not None`, so past the refusal above it is present --
    # and re-reading the allowlist here would both risk a KeyError BEFORE any
    # evidence record exists (violating FR-015) and let the executed path drift
    # from the authorized one (Codex review, PR #659).
    authorized_path = str(verdict.authorized_path)
    guidance = validation.rollback_guidance_for(authorized_path, request.backup_ref)

    if dry_run:
        # Everything cleared, but plan-write mutates nothing by contract.
        return terminal(
            exit_code=EXIT_OK,
            outcome="deferred",
            tool="none",
            mutation_attempted=False,
        )

    # 4. Intent BEFORE the mutation, so a crash still leaves a trace.
    evidence.write_intent(root, identity.with_tool(runner.VENDOR_PACKAGE))

    # 5-7. Execute, confirm the effect, validate.
    return _execute_and_confirm(
        root,
        _Execution(
            verdict=verdict,
            authorized_path=authorized_path,
            guidance=guidance,
            backup_ref=request.backup_ref,
            mcp_runner=request.mcp_runner,
            validator=request.validator,
            terminal=terminal,
        ),
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

    The public entry point, whose keyword-only signature is the CLI contract in
    ``contracts/cli-contract.md``. It bundles the request and delegates; the
    sequence lives in :func:`_run_pipeline`.

    ``dry_run`` is the ``plan-write`` leg: it evaluates every precondition and
    mutates nothing. It still emits a ``deferred`` evidence record, so "every run
    produces exactly one record" stays literally true and an operator cannot probe
    the gate repeatedly without a trace.
    """
    return _run_pipeline(
        Path(repo_root),
        _WriteRequest(
            target_id=target_id,
            operation_id=operation_id,
            timestamp=timestamp,
            tree_clean=tree_clean,
            backup_ref=backup_ref,
            argv=argv,
            config_state=config_state,
            mcp_runner=mcp_runner,
            validator=validator,
            capability_profile=capability_profile,
        ),
        dry_run=dry_run,
    )
