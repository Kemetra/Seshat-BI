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
from seshat.pbi_mcp_adapter import session, vendor_ops
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
    if not verdict.cleared:
        return RunResult(
            exit_code=1,
            output="refused: the write gate is not cleared",
            mutation_attempted=False,
            blockers=(BLOCKER_GATE_NOT_CLEARED, *verdict.blockers),
        )

    # Read from the verdict. `cleared` guarantees both are populated.
    target_path = verdict.authorized_path
    operation_id = verdict.authorized_operation
    if (
        target_path is None or not operation_id
    ):  # pragma: no cover - cleared implies both
        return RunResult(
            exit_code=1,
            output="refused: the verdict names no authorized target or operation",
            mutation_attempted=False,
            blockers=(BLOCKER_GATE_NOT_CLEARED,),
        )

    # The allowlist stores a (tool, operation) PAIR because the vendor dispatches
    # on both. An unknown half is refused before anything is launched.
    try:
        tool, operation = vendor_ops.parse_operation_id(operation_id)
    except vendor_ops.UnknownVendorOperation as exc:
        return RunResult(
            exit_code=1,
            output=f"refused: {exc}",
            mutation_attempted=False,
            blockers=(BLOCKER_UNKNOWN_OPERATION,),
        )

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
        return RunResult(
            exit_code=1,
            output="the vendor runtime could not be launched (is npx on PATH?)",
            mutation_attempted=False,
            blockers=(BLOCKER_RUNTIME_MISSING,),
        )

    return _converse(
        live,
        tool=tool,
        operation=operation,
        target_path=str(target_path),
    )


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
    writes = vendor_ops.is_write(operation)
    transcript: list[str] = []
    blockers: list[str] = []
    attempted = False
    try:
        live.handshake()

        # 1. Bind the folder. Stateful and named: everything after this call
        #    operates on the connection it established.
        connected = live.call(
            "connection_operations",
            {"operation": "ConnectFolder", "folderPath": target_path},
        )
        transcript.append(connected.raw_text)
        if not connected.ok:
            return RunResult(
                exit_code=1,
                output=_redact_and_tail("\n".join(transcript), TAIL_CHARS),
                mutation_attempted=False,
                blockers=(BLOCKER_VENDOR_REFUSED,),
            )

        # 2. The authorized operation.
        attempted = writes
        outcome = live.call(tool, {"operation": operation})
        transcript.append(outcome.raw_text)
        if not outcome.ok:
            blockers.append(BLOCKER_VENDOR_REFUSED)
        elif writes and outcome.read_only_hint is True:
            # Cross-check OUR classification against the vendor's own per-call
            # annotation. Disagreement means one of us is wrong about whether
            # model state changed, so claim nothing.
            blockers.append(BLOCKER_READONLY_VIOLATION)

        # 3. THE FLUSH. Only on a write, and only if the operation held: an
        #    export after a failed operation would rewrite the whole folder for
        #    nothing. Without this the bytes on disk never change (#660).
        if writes and not blockers:
            flushed = live.call(
                "database_operations",
                {"operation": "ExportToTmdlFolder", "tmdlFolderPath": target_path},
            )
            transcript.append(flushed.raw_text)
            if not flushed.ok:
                blockers.append(BLOCKER_FLUSH_FAILED)
    except session.SessionError as exc:
        return RunResult(
            exit_code=TIMEOUT_EXIT_CODE,
            output=_redact_and_tail("\n".join([*transcript, str(exc)]), TAIL_CHARS),
            mutation_attempted=attempted,
            blockers=(BLOCKER_RUNTIME_STALLED,),
        )
    finally:
        live.close()

    return RunResult(
        exit_code=1 if blockers else 0,
        output=_redact_and_tail(
            "\n".join(part for part in transcript if part), TAIL_CHARS
        ),
        mutation_attempted=attempted,
        blockers=tuple(blockers),
    )
