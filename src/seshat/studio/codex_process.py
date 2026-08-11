"""Codex process lifecycle, version gate, and health classification (T021).

The launch is expressed as a PLAN -- an inspectable value -- rather than a call that
immediately spawns. That is what lets the handle discipline below be unit-tested on a
runner with no Codex CLI installed, which matters because handle mistakes are invisible
until they deadlock in production.

**Why this does not route through `gitutil.run_subprocess`.** That helper sets
`stdin=DEVNULL` and a timeout cap, both correct for the one-shot git calls it serves and
both wrong here. The app-server is long-lived, so a shared timeout would kill a healthy
session mid-turn; and this child must be WRITTEN to, so `DEVNULL` would break the
protocol outright. What the helper's docstring is really guarding is issue #557 --
INHERITING the parent's stdin, which under `seshat mcp` is the client's live JSON-RPC
pipe. An explicit pipe satisfies that guarantee without the two settings that do not
fit. Do not "simplify" this by routing through the helper.

**stderr stays a separate pipe.** Provider stderr carries credential-shaped strings --
bearer tokens, `sk-` keys, a DSN. Merging it into stdout would feed those to the frame
parser and into any diagnostic that retained the stream, so it is read separately and
redacted before retention.

**The version gate fails closed.** The bridge contract states that a CLI outside the
tested range stays `incompatible` until its generated schema and handshake fixtures
pass, and that semantic-version proximity alone is not compatibility evidence. A build
NEWER than the tested maximum is therefore refused, not waved through.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from seshat.studio.projection import AgentHealth
from seshat.studio.redaction import redact_for_boundary

__all__ = [
    "MAXIMUM_TESTED_CODEX",
    "MINIMUM_TESTED_CODEX",
    "CodexLaunchPlan",
    "classify_health",
    "find_codex_executable",
    "is_tested_version",
    "redact_provider_stderr",
]

#: The Codex CLI range Studio has actually exercised.
#:
#: 0.146.0 is the build the bridge contract's provider mapping was verified against.
#: 0.147.0 was re-probed on 2026-08-11: all 19 methods that mapping depends on are
#: present in its generated schema (see `tests/fixtures/codex_app_server/README.md`).
#: Widening this range REQUIRES re-deriving the fixtures against the new build --
#: bumping the constant alone would assert a compatibility no one tested.
MINIMUM_TESTED_CODEX = "0.146.0"
MAXIMUM_TESTED_CODEX = "0.147.0"

_VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def _version_tuple(version: str) -> tuple[int, int, int] | None:
    match = _VERSION_PATTERN.match(version.strip())
    if match is None:
        return None
    return (int(match[1]), int(match[2]), int(match[3]))


def is_tested_version(version: str | None) -> bool:
    """True only for a build inside the recorded range. Unparseable is False."""
    if not version:
        return False
    parsed = _version_tuple(version)
    if parsed is None:
        return False
    low = _version_tuple(MINIMUM_TESTED_CODEX)
    high = _version_tuple(MAXIMUM_TESTED_CODEX)
    assert low is not None and high is not None  # module constants are well-formed
    return low <= parsed <= high


def find_codex_executable() -> str | None:
    """Locate `codex` on PATH without ever building a shell command string."""
    return shutil.which("codex")


@dataclass(frozen=True, slots=True)
class CodexLaunchPlan:
    """Everything needed to spawn the app-server, as an inspectable value.

    Every field here is an assertion target. A plan that cannot be examined without
    spawning would push the handle rules into an integration test that CI cannot run.
    """

    argv: tuple[str, ...]
    cwd: Path

    #: Explicitly piped, never inherited and never DEVNULL -- see the module docstring.
    stdin_is_pipe: bool = True
    stdout_is_pipe: bool = True
    #: Kept apart from stdout so credential-shaped stderr never reaches the parser.
    stderr_is_separate_pipe: bool = True
    use_shell: bool = False

    @classmethod
    def for_workspace(cls, workspace: Path, *, executable: str) -> CodexLaunchPlan:
        return cls(argv=(executable, "app-server"), cwd=workspace)

    @property
    def inherits_any_handle(self) -> bool:
        """False when all three streams are explicitly ours. Guards issue #557."""
        return not (
            self.stdin_is_pipe and self.stdout_is_pipe and self.stderr_is_separate_pipe
        )


def redact_provider_stderr(raw: str, *, workspace_root: Path | None = None) -> str:
    """Strip credentials and absolute paths from provider stderr before retention.

    Reuses the shared boundary redactor rather than a local regex: a second
    implementation would drift from the one the event path uses, and stderr is exactly
    where a drifted redactor goes unnoticed.
    """
    return redact_for_boundary(raw, secrets=(), workspace_root=workspace_root)


def classify_health(
    *,
    executable_found: bool,
    version: str | None,
    signed_in: bool,
    rate_limit_reached: bool = False,
    resets_at: int | None = None,
    saw_eof: bool = False,
    disabled: bool = False,
) -> AgentHealth:
    """Map observations to one of the contract's seven states.

    Ordered most-fundamental first: a missing executable makes every later question
    meaningless, and an untested protocol makes sign-in state irrelevant. No branch
    returns a provider other than `codex` or `disabled` -- FR-013 forbids any condition
    here from switching Studio to a billed path on its own.
    """
    if disabled:
        return AgentHealth(
            state="disabled",
            summary="The agent bridge is switched off for this workspace.",
            recovery_action="Deterministic workspace views remain fully usable.",
            provider="disabled",
            version=None,
        )

    if not executable_found:
        return AgentHealth(
            state="missing",
            summary="The Codex CLI was not found on PATH.",
            recovery_action=(
                "Install the Codex CLI, then reload. Deterministic workspace views "
                "stay enabled meanwhile."
            ),
            provider="codex",
            version=None,
        )

    if not is_tested_version(version):
        observed = version or "an unreadable version"
        return AgentHealth(
            state="incompatible",
            summary=(
                f"Codex reports {observed}; Studio has only exercised "
                f"{MINIMUM_TESTED_CODEX} to {MAXIMUM_TESTED_CODEX}."
            ),
            recovery_action=(
                "Turns are refused until this build's generated schema and handshake "
                "fixtures are re-derived and pass. Version proximity is not evidence."
            ),
            provider="codex",
            version=version,
        )

    if saw_eof:
        return AgentHealth(
            state="crashed",
            summary="The Codex app-server exited unexpectedly.",
            recovery_action="Restart the bridge; the interrupted turn was not applied.",
            provider="codex",
            version=version,
        )

    if not signed_in:
        return AgentHealth(
            state="signed_out",
            summary="Codex is installed but no ChatGPT subscription is signed in.",
            recovery_action=(
                "Sign in through Codex itself; Studio never handles the credential."
            ),
            provider="codex",
            version=version,
        )

    if rate_limit_reached:
        detail = f" Usage resets at {resets_at}." if resets_at is not None else ""
        return AgentHealth(
            state="quota_limited",
            summary=f"The Codex subscription has reached its usage limit.{detail}",
            recovery_action=(
                "Wait for the reported reset. Any drafted prompt is preserved, and "
                "Studio will not switch to a billed path on its own."
            ),
            provider="codex",
            version=version,
        )

    return AgentHealth(
        state="healthy",
        summary="Codex is signed in and responding.",
        recovery_action="",
        provider="codex",
        version=version,
    )
