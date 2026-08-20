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

import os
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from seshat.pbi_mcp.detect import VENDOR_PACKAGE, refuse_if_bypass_flag
from seshat.pbi_mcp.scan import SECRET_PATTERNS
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


#: The ONLY variables forwarded to the vendor process.
#:
#: Deny by default, EXACT keys, and deliberately no prefix rules. Measured rather
#: than guessed: `npx --yes cowsay@1.6.0 hi` fetches AND executes a real package
#: with only these present, so nothing here is speculative and nothing is missing
#: for the general `npx` case.
#:
#: This is a SIBLING of `dagster_adapter.environment.allowed_child_environment`,
#: not a reuse of it. That helper forwards `DATABASE_URL`, `ANALYTICS_DB_*` and
#: `PYTHONPATH` by design, because it feeds a governed Seshat connection to our own
#: code. The vendor runtime is external, unforked and a public preview (ADR 0018) --
#: handing it a database credential would be worse than inheriting one by accident,
#: because it would look deliberate.
_VENDOR_ENV_KEYS = frozenset(
    {
        # Executable resolution.
        "PATH",
        "PATHEXT",
        "COMSPEC",
        # Windows runtime.
        "SYSTEMROOT",
        "WINDIR",
        # npm/npx cache and config discovery, so repeat runs reuse the cache
        # rather than re-downloading (and stay quiet about it).
        "APPDATA",
        "LOCALAPPDATA",
        "USERPROFILE",
        "HOME",
        # Scratch space for the package extract.
        "TEMP",
        "TMP",
        "TMPDIR",
        # TLS trust: whether the certificate chain VERIFIES. These do not say
        # which host to connect to -- that is the routing block below, and
        # conflating the two is what left a proxy-only network unable to fetch.
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
        "NODE_EXTRA_CA_CERTS",
        # Proxy ROUTING, so `npx` reaches the registry at all where egress is
        # proxy-only. npm honours these directly (`using-npm/config.md`), and
        # without them the fetch attempts a direct connection and fails before
        # the vendor runtime ever starts.
        #
        # These are forwarded VERBATIM, including any `user:pw@` userinfo. That
        # is deliberate and is not a hole in #658: an authenticated proxy is the
        # credential for the network hop this subprocess is about to make on the
        # caller's behalf, unlike `DATABASE_URL`, which the vendor has no business
        # seeing at all. Stripping the userinfo would not be safer -- it would
        # route to the proxy and earn a 407, so there is no sanitized form that
        # still works. Deny-by-default with exact keys is intact; this adds three
        # named keys, not a parsing rule.
        #
        # Three entries cover six variables: the filter compares `key.upper()`,
        # so the Unix lowercase forms match, and the emitted dict keeps the
        # SOURCE spelling so `http_proxy` reaches the child as `http_proxy`.
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
    }
)


def allowed_vendor_environment(source: Mapping[str, str]) -> dict[str, str]:
    """The least-privilege environment for the vendor runtime.

    Everything not in :data:`_VENDOR_ENV_KEYS` is dropped -- including every
    credential-bearing variable that happens to be set in the parent for unrelated
    reasons. Comparison is case-insensitive because Windows environment keys are.

    Note what is NOT forwarded and why it matters: no `DATABASE_URL`, no
    `ANALYTICS_DB_*`, no `SESHAT_*`, no cloud or token variables. The vendor needs
    none of them, and this adapter never passes a credential to it -- the Power BI
    connection is the vendor's own concern, discovered from the local Desktop
    session, not something Seshat hands over.
    """
    return {
        key: value for key, value in source.items() if key.upper() in _VENDOR_ENV_KEYS
    }


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv shape, no shell
        argv,
        cwd=cwd,
        # An EXPLICIT environment, never the inherited one: the vendor is an
        # external preview binary, so every variable in the parent -- including
        # credentials present for unrelated reasons -- would otherwise be visible
        # to a third party (#658).
        env=allowed_vendor_environment(os.environ),
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
    runner: object = None,
) -> RunResult:
    """Invoke the vendor runtime, but only behind a cleared gate.

    The target path and operation come from the VERDICT, not from parameters.
    That is the whole point: this function previously took ``target_path`` and
    ``operation_id`` of its own and only checked ``verdict.cleared``, so a verdict
    legitimately cleared for one target/operation could be replayed to launch a
    different operation against a different path -- including one outside the
    repository, defeating the containment check the gate had just performed.

    A verdict authorizes a specific mutation. There is now no parameter by which
    a caller can substitute another.
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
