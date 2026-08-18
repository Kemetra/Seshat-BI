"""Spec 149 -- the bounded invocation of Microsoft's official Power BI MCP.

The runtime is external, unforked, and invoked through ``npx``: never vendored,
never a Python dependency (ADR 0018 rejected alternative; Principle II).

Four hard-won constraints from the shipped ``dagster_adapter/runner.py``, each of
which this repo paid for once already:

* **``stdin=subprocess.DEVNULL``.** The parent may itself be speaking MCP over
  stdio; an inherited stdin deadlocks the child (#322).
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

import subprocess
from dataclasses import dataclass
from pathlib import Path

from seshat.pbi_mcp.detect import refuse_if_bypass_flag
from seshat.pbi_mcp_adapter.evidence import redact
from seshat.pbi_mcp_adapter.gate import GateVerdict

#: The vendor package, invoked through npx. Never vendored, never pinned into
#: pyproject: it is a preview binary, not shippable payload.
VENDOR_PACKAGE = "@microsoft/powerbi-modeling-mcp"

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


def build_argv(target_path: str, operation_id: str, *, read_only: bool) -> list[str]:
    """The exact argv for one invocation.

    ``--readonly`` is passed explicitly on the read-only path rather than relying
    on a default: the vendor documents local stdio as write-enabled by default, so
    silence means write mode (see ``detect._transport_verdict``). The bypass flag
    is never constructible here -- there is no parameter that could add it, and
    :func:`invoke` re-checks the built argv anyway.
    """
    argv = ["npx", "--yes", VENDOR_PACKAGE]
    argv.append("--readonly" if read_only else "--readwrite")
    argv.extend(["--target", target_path, "--operation", operation_id])
    return argv


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv shape, no shell
        argv,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        timeout=RUN_TIMEOUT_SECONDS,
        check=False,
    )


def _redact_and_tail(text: str, limit: int) -> str:
    """Redact FIRST, then trim (#362).

    Trimming first can split a DSN across the discarded boundary and leave a
    remainder no later redaction pass recognizes.
    """
    scrubbed = redact(text)
    return scrubbed if len(scrubbed) <= limit else scrubbed[-limit:]


def invoke(
    verdict: GateVerdict,
    *,
    target_path: str,
    operation_id: str,
    repo_root: Path,
    read_only: bool = False,
    runner: object = None,
) -> RunResult:
    """Invoke the vendor runtime, but only behind a cleared gate.

    Refuses -- without launching anything -- when the gate is not cleared. A
    caller cannot pass a hand-built "cleared" verdict cheaply either: every field
    of :class:`GateVerdict` is derived by ``gate.evaluate``, and ``cleared`` is a
    computed property rather than a stored flag.
    """
    if not verdict.cleared:
        return RunResult(
            exit_code=1,
            output="refused: the write gate is not cleared",
            mutation_attempted=False,
            blockers=(BLOCKER_GATE_NOT_CLEARED, *verdict.blockers),
        )

    argv = build_argv(target_path, operation_id, read_only=read_only)
    # The standing prohibition, re-checked on the argv actually about to run.
    # Belt and braces: build_argv cannot add the flag, but a future edit could.
    refuse_if_bypass_flag(argv, context="pbi-mcp runner")

    invoker = runner if runner is not None else _run
    try:
        completed = invoker(argv, Path(repo_root))  # type: ignore[operator]
    except subprocess.TimeoutExpired:
        # Fail closed: a hung child is a blocked run with the artifact possibly
        # half-written -- never an exception a caller might swallow into a green
        # result.
        return RunResult(
            exit_code=TIMEOUT_EXIT_CODE,
            output=f"the vendor runtime timed out after {RUN_TIMEOUT_SECONDS}s",
            mutation_attempted=True,
            blockers=(BLOCKER_RUNTIME_STALLED,),
        )
    except (OSError, FileNotFoundError):
        return RunResult(
            exit_code=1,
            output="the vendor runtime could not be launched (is npx on PATH?)",
            mutation_attempted=False,
            blockers=(BLOCKER_RUNTIME_MISSING,),
        )

    combined = (completed.stdout or "") + (
        "\n" + completed.stderr if completed.stderr else ""
    )
    return RunResult(
        exit_code=completed.returncode,
        output=_redact_and_tail(combined, TAIL_CHARS),
        mutation_attempted=True,
        blockers=(),
    )
