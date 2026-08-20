"""Spec 149 -- the bounded invocation of Microsoft's official Power BI MCP.

The runtime is external, unforked, and invoked through ``npx``: never vendored,
never a Python dependency (ADR 0018 rejected alternative; Principle II).

Four hard-won constraints from the shipped ``dagster_adapter/runner.py``, each of
which this repo paid for once already:

* **A DEDICATED stdin pipe, never an inherited one.** The parent may itself be
  speaking MCP over stdio, and an INHERITED stdin deadlocks the child (#322).
  The pre-#660 code read that lesson as ``stdin=DEVNULL`` -- but this runtime is
  an MCP stdio SERVER, so we must write to its stdin to say anything at all.
  ``DEVNULL`` is why no write could ever execute (#660). The #322 constraint is
  satisfied by owning the pipe, not by discarding it.
* **Its own workload-sized timeout, NOT ``gitutil.run_subprocess``.** That
  helper's docstring explicitly excludes the execution runners, because its short
  shared cap would abort legitimately long user workloads (research R4). Never
  call ``subprocess`` bare either -- a run with no bound can hang forever.
* **``encoding="utf-8", errors="replace"``.** Windows defaults to
  ``locale.getpreferredencoding()`` and raises ``UnicodeDecodeError`` mid-run on a
  stray byte (#404).
* **Redact BEFORE truncating** (#362): slicing first can cut a DSN's ``scheme://``
  into the discarded front, leaving a schemeless credential remainder that every
  later redaction pass misses.

The runner refuses to execute against an uncleared gate. That is not politeness:
it is the last line of defence if a future callsite reaches the runtime without
going through the orchestration entry.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from seshat.pbi_mcp.detect import VENDOR_PACKAGE, refuse_if_bypass_flag
from seshat.pbi_mcp.scan import SECRET_PATTERNS
from seshat.pbi_mcp_adapter import protocol, session, vendor_ops
from seshat.pbi_mcp_adapter.evidence import redact
from seshat.pbi_mcp_adapter.gate import GateVerdict

#: The vendor package, invoked through npx. Never vendored, never pinned into
#: pyproject: it is a preview binary, not shippable payload.
#: Re-exported from :mod:`seshat.pbi_mcp.detect`, which owns the single
#: definition -- two copies could drift and one of them gates a refusal.
__all__ = ["VENDOR_PACKAGE"]

#: Sized for a model operation on a real semantic model, not for a git command.
RUN_TIMEOUT_SECONDS = 900

#: Keep the tail of a long transcript; the front is usually banner noise.
TAIL_CHARS = 20_000

#: Exit code convention for a timed-out child, matching the shipped runner.
TIMEOUT_EXIT_CODE = 124

BLOCKER_GATE_NOT_CLEARED = "PBIMCP-RUN-01"
BLOCKER_RUNTIME_STALLED = "PBIMCP-RUN-02"
BLOCKER_RUNTIME_MISSING = "PBIMCP-RUN-03"
BLOCKER_RUNTIME_UNEXPLAINED = "PBIMCP-RUN-04"
BLOCKER_VENDOR_REFUSED = "PBIMCP-RUN-05"
BLOCKER_READONLY_VIOLATION = "PBIMCP-RUN-06"
BLOCKER_UNKNOWN_OPERATION = "PBIMCP-RUN-07"
BLOCKER_FLUSH_FAILED = "PBIMCP-RUN-08"
BLOCKER_PAYLOAD_UNAVAILABLE = "PBIMCP-RUN-09"

BLOCKER_DETAIL: dict[str, str] = {
    BLOCKER_GATE_NOT_CLEARED: (
        "the runner was called with an uncleared gate verdict; no invocation was "
        "attempted"
    ),
    BLOCKER_RUNTIME_STALLED: (
        f"the vendor runtime did not finish within {RUN_TIMEOUT_SECONDS}s and was "
        "killed"
    ),
    BLOCKER_RUNTIME_MISSING: "the vendor runtime could not be launched",
    BLOCKER_VENDOR_REFUSED: (
        "the vendor reported the operation as failed; treated as indeterminate "
        "because the artifact may have been partially written"
    ),
    BLOCKER_READONLY_VIOLATION: (
        "the operation is classified as a write but the vendor annotated the "
        "result read-only; the two disagree, so no write is claimed"
    ),
    BLOCKER_UNKNOWN_OPERATION: (
        "the allowlist named a tool or operation the vendor does not expose; no "
        "invocation was attempted"
    ),
    BLOCKER_FLUSH_FAILED: (
        "the operation mutated the in-memory model but the TMDL export failed, "
        "so the change never reached disk; indeterminate, never a success"
    ),
    BLOCKER_PAYLOAD_UNAVAILABLE: (
        "the operation requires an approved definition payload, which this "
        "adapter is forbidden to invent and no approved_definitions record "
        "supplies; refused rather than executed as a no-op"
    ),
    BLOCKER_RUNTIME_UNEXPLAINED: (
        "the vendor runtime failed without naming a cause; treated as "
        "indeterminate because the artifact may have been partially written"
    ),
}


class RunnerRefused(RuntimeError):
    """The runner declined to invoke the runtime."""


@dataclass(frozen=True)
class RunResult:
    """One invocation's bounded, redacted outcome.

    ``mutation_attempted`` records whether the child was actually started, which
    is what separates "refused before launching" from "launched, state unknown".
    """

    exit_code: int
    output: str
    mutation_attempted: bool
    blockers: tuple[str, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.blockers


def build_argv(*, read_only: bool) -> list[str]:
    """The exact argv for one server LAUNCH.

    There is no ``--target`` and no ``--operation``: the pre-#660 code invented
    both. Verified against the real binary (2026-08-20) -- the runtime is an MCP
    stdio server that takes its target through a ``ConnectFolder`` tool call and
    its operation inside a ``tools/call`` request.

    ``--readonly`` IS real and is passed explicitly on the read-only path rather
    than relying on a default: the vendor documents local stdio as write-enabled
    by default, so silence means write mode.
    """
    return [
        "npx",
        "--yes",
        VENDOR_PACKAGE,
        "--readonly" if read_only else "--readwrite",
    ]


def _default_session_factory(*, argv: list[str], cwd: Path) -> session.McpSession:
    """The real session. Kept tiny so tests can substitute a fake wholesale."""
    transport = session.SubprocessTransport(argv, cwd)
    return session.McpSession(transport, deadline_seconds=RUN_TIMEOUT_SECONDS)


def _redact_and_tail(text: str, limit: int) -> str:
    """Redact FIRST, then trim (#362), through BOTH layers.

    Trimming first can split a DSN across the discarded boundary and leave a
    remainder no later redaction pass recognizes.

    ``redact`` is the DSN-shaped layer only -- its own docstring says it cannot see
    a tenant GUID or a user path and must never be the last thing a writer calls.
    Vendor output is exactly where those appear (the runtime prints local project
    paths), so the comprehensive scanner runs afterwards. Unlike the evidence
    writer this SCRUBS rather than refuses: a leaky transcript must not discard the
    record of a mutation that already happened, so the classes derive-then-replace
    cannot handle are masked by label instead.
    """
    scrubbed = redact(text)
    for label, pattern in SECRET_PATTERNS:
        scrubbed = pattern.sub(f"[REDACTED:{label}]", scrubbed)
    return scrubbed if len(scrubbed) <= limit else scrubbed[-limit:]


def _refused(output: str, *blockers: str) -> RunResult:
    """A refusal decided BEFORE the runtime is launched.

    Every such result shares `mutation_attempted=False`, and that is the
    property worth centralising: nothing has run, so nothing can have been
    half-written. A refusal that reported True would send the operator hunting
    for damage that cannot exist.
    """
    return RunResult(
        exit_code=1,
        output=output,
        mutation_attempted=False,
        blockers=blockers,
    )


def _authorized_call(verdict: GateVerdict) -> tuple[str, str, str] | RunResult:
    """Resolve the verdict into the (tool, operation, target) it authorizes.

    Every precondition that can refuse the run lives here, so :func:`invoke`
    reads as launch-and-converse rather than a wall of guard clauses. Returning
    a `RunResult` means refused; a tuple means cleared.

    The target and operation are read from the VERDICT, never from parameters --
    that is the containment property: a verdict cleared for one target cannot be
    replayed against another.
    """
    if not verdict.cleared:
        return _refused(
            "refused: the write gate is not cleared",
            BLOCKER_GATE_NOT_CLEARED,
            *verdict.blockers,
        )

    target_path = verdict.authorized_path
    operation_id = verdict.authorized_operation
    if target_path is None or not operation_id:  # pragma: no cover
        return _refused(
            "refused: the verdict names no authorized target or operation",
            BLOCKER_GATE_NOT_CLEARED,
        )

    # The allowlist stores a (tool, operation) PAIR because the vendor
    # dispatches on both. An unknown half is refused before anything launches.
    try:
        tool, operation = vendor_ops.parse_operation_id(operation_id)
    except vendor_ops.UnknownVendorOperation as exc:
        return _refused(f"refused: {exc}", BLOCKER_UNKNOWN_OPERATION)

    # LOUD refusal, not a hollow success. The server documents Create/Update as
    # requiring a `Definitions` block; issued from a verb alone they mutate
    # nothing, so executing one would report success for a no-op -- and after
    # #660's other fixes this path is REACHABLE, where before it was not.
    #
    # This adapter is forbidden to invent the definition (spec.md: "the adapter
    # never invents the definition") and the `approved_definitions[]` record
    # that would supply one is deferred to a companion spec. So the honest
    # answer is a refusal naming the missing input, never a run that certifies
    # nothing happened (issue #660 re-review, C2).
    if vendor_ops.requires_payload(tool, operation):
        return _refused(
            (
                f"refused: {tool}.{operation} requires an approved definition "
                "payload. This adapter never invents a definition, and no "
                "approved_definitions record supplies one (FR-011b, deferred "
                "to a companion spec). Executing it would report success for "
                "a no-op."
            ),
            BLOCKER_PAYLOAD_UNAVAILABLE,
        )

    return tool, operation, str(target_path)


def invoke(
    verdict: GateVerdict,
    *,
    repo_root: Path,
    read_only: bool = False,
    session_factory: Callable[..., session.McpSession] | None = None,
) -> RunResult:
    """Execute the verdict's authorized (tool, operation) over MCP stdio.

    The target path and operation come from the VERDICT, not from parameters.
    That is the whole point: this function previously took ``target_path`` and
    ``operation_id`` of its own and only checked ``verdict.cleared``, so a verdict
    legitimately cleared for one target/operation could be replayed to launch a
    different operation against a different path -- including one outside the
    repository, defeating the containment check the gate had just performed.

    A verdict authorizes a specific mutation. There is no parameter by which a
    caller can substitute another.

    **A write is THREE calls, and the third is what makes it real.** Verified
    2026-08-20 against the real binary: ``ConnectFolder`` then
    ``measure_operations/Update`` returns ``isError: false`` and changes ZERO
    bytes on disk, because the vendor mutates an in-memory tabular model. Without
    the ``ExportToTmdlFolder`` flush, every downstream check validates stale files
    and passes -- certifying a write that never happened.
    """
    resolved = _authorized_call(verdict)
    if isinstance(resolved, RunResult):
        return resolved
    tool, operation, target_path = resolved

    argv = build_argv(read_only=read_only)
    # The standing prohibition, re-checked on the argv actually about to run.
    # Belt and braces: build_argv cannot add the flag, but a future edit could.
    refuse_if_bypass_flag(argv, context="pbi-mcp runner")

    factory = (
        session_factory if session_factory is not None else _default_session_factory
    )
    try:
        live = factory(argv=argv, cwd=Path(repo_root))
    except (OSError, session.SessionError):
        return _refused(
            "the vendor runtime could not be launched (is npx on PATH?)",
            BLOCKER_RUNTIME_MISSING,
        )

    return _converse(
        live,
        tool=tool,
        operation=operation,
        target_path=target_path,
    )


def _trace(outcome: "protocol.ToolOutcome") -> str:
    """What to record for one call: the payload, or the error if there is none.

    A JSON-RPC error frame carries no ``content``, so ``raw_text`` is empty --
    which shipped ``BLOCKER_VENDOR_REFUSED`` with no diagnosis on the single most
    important failure path (review M3).
    """
    if outcome.raw_text:
        return outcome.raw_text
    return f"vendor error: {outcome.error}" if outcome.error else ""


@dataclass
class _Exchange:
    """What one vendor conversation needs to know about itself.

    A bundle rather than six positional seams: the tool, the verb, the folder
    they act on, and whether that verb writes travel together for the whole
    exchange.

    NOT frozen, and `attempted` is why. It is set to True BEFORE the operation
    call is issued, so that if the vendor hangs or dies mid-write the caller's
    exception handler can still see that a mutation was in flight. Returning the
    flag only on a normal return loses exactly the case that matters: an
    indeterminate, possibly half-written artifact would be reported as "nothing
    was attempted", sending the operator away without checking for damage.
    """

    tool: str
    operation: str
    target_path: str
    writes: bool
    attempted: bool = False


def _exchange(
    live: session.McpSession,
    spec: _Exchange,
    transcript: list[str],
) -> tuple[list[str], bool]:
    """The three vendor calls, in order. Returns (blockers, attempted).

    Split from :func:`_converse` so the session lifecycle and exception
    dispatch live in one function and the protocol sequence in another.

    **A write is THREE calls and the third is what makes it real** -- bind the
    folder, run the operation, flush to disk. Appends to `transcript` in place
    so a caller that aborts mid-sequence still reports what already happened.
    """
    connected = live.call(
        "connection_operations",
        {"operation": "ConnectFolder", "folderPath": spec.target_path},
    )
    transcript.append(_trace(connected))
    if not connected.ok:
        # Nothing was attempted: the bind failed, so no operation was issued.
        return [BLOCKER_VENDOR_REFUSED], False

    blockers: list[str] = []
    # BEFORE the call, never after: a stall here is indeterminate, and the
    # caller reads this flag from the exception path.
    spec.attempted = spec.writes
    outcome = live.call(spec.tool, {"operation": spec.operation})
    transcript.append(_trace(outcome))
    if not outcome.ok:
        blockers.append(BLOCKER_VENDOR_REFUSED)
    elif spec.writes and outcome.read_only_hint is True:
        # Cross-check OUR classification against the vendor's own per-call
        # annotation. Disagreement means one of us is wrong about whether model
        # state changed, so claim nothing.
        blockers.append(BLOCKER_READONLY_VIOLATION)

    # THE FLUSH. Only on a write, and only if the operation held: an export
    # after a failed operation would rewrite the whole folder for nothing.
    # Without this the bytes on disk never change (#660).
    if spec.writes and not blockers:
        flushed = live.call(
            "database_operations",
            {"operation": "ExportToTmdlFolder", "tmdlFolderPath": spec.target_path},
        )
        transcript.append(_trace(flushed))
        if not flushed.ok:
            blockers.append(BLOCKER_FLUSH_FAILED)

    return blockers, spec.attempted


def _converse(
    live: session.McpSession,
    *,
    tool: str,
    operation: str,
    target_path: str,
) -> RunResult:
    """The connect / operate / flush exchange on an established session.

    Split out of :func:`invoke` so the precondition checks and the conversation
    are each small enough to read whole.
    """
    spec = _Exchange(
        tool=tool,
        operation=operation,
        target_path=target_path,
        # Classified against THIS tool, not globally: a verb evidenced as a read
        # under one tool says nothing about another (re-review H4).
        writes=vendor_ops.is_write(operation, tool),
    )
    transcript: list[str] = []
    blockers: list[str] = []
    attempted = False
    try:
        live.handshake()
        blockers, attempted = _exchange(live, spec, transcript)
        if blockers == [BLOCKER_VENDOR_REFUSED] and not attempted:
            # The bind itself failed, so the transcript is the whole story.
            return RunResult(
                exit_code=1,
                output=_redact_and_tail("\n".join(transcript), TAIL_CHARS),
                mutation_attempted=False,
                blockers=(BLOCKER_VENDOR_REFUSED,),
            )
    except session.SessionStalled as exc:
        # A hung child: indeterminate, the artifact may be half-written.
        return RunResult(
            exit_code=TIMEOUT_EXIT_CODE,
            output=_redact_and_tail("\n".join([*transcript, str(exc)]), TAIL_CHARS),
            mutation_attempted=spec.attempted,
            blockers=(BLOCKER_RUNTIME_STALLED,),
        )
    except session.SessionError as exc:
        # A closed stream or a refused handshake is NOT a stall. Reporting it as
        # "did not finish within 900s and was killed" tells the operator
        # something false about what happened (review M2). Dispatch is on the
        # TYPE, never on the message text.
        return RunResult(
            exit_code=1,
            output=_redact_and_tail("\n".join([*transcript, str(exc)]), TAIL_CHARS),
            mutation_attempted=spec.attempted,
            blockers=(BLOCKER_RUNTIME_UNEXPLAINED,),
        )
    except (OSError, ValueError) as exc:  # UnicodeDecodeError is a ValueError
        # NEVER let this escape as a traceback (review H3). An exception leaving
        # `invoke` means no RunResult, so `orchestrate` never reaches `_terminate`
        # and writes NO evidence record -- violating FR-015 on the one path where
        # the record matters most. Indeterminate, because the artifact may be
        # half-written.
        return RunResult(
            exit_code=1,
            output=_redact_and_tail(
                "\n".join([*transcript, f"{type(exc).__name__}: {exc}"]), TAIL_CHARS
            ),
            mutation_attempted=spec.attempted,
            blockers=(BLOCKER_RUNTIME_UNEXPLAINED,),
        )
    finally:
        live.close()

    return RunResult(
        exit_code=1 if blockers else 0,
        output=_redact_and_tail(
            "\n".join(part for part in transcript if part), TAIL_CHARS
        ),
        mutation_attempted=spec.attempted,
        blockers=tuple(blockers),
    )
