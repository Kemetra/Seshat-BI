"""T021: Codex process lifecycle, version gate, and health classification.

Written before the implementation. Nothing here starts a real Codex process: the
launch plan is a value that can be inspected, and the classifier is a pure function
over observations. That is deliberate -- a lifecycle layer only testable by spawning
the real CLI would be untested on CI, which is exactly where the handle-discipline
mistakes bite.

The risks under test:

**Handle discipline.** Under `seshat mcp`, a child that inherits stdin gets the live
JSON-RPC pipe and both processes deadlock (issue #557). This bridge needs a real stdin
to write requests, so `DEVNULL` is not the fix either -- it must be an explicit pipe.
And stderr must stay SEPARATE from stdout: provider stderr carries credential-shaped
strings, and merging it into the frame stream would feed them to the parser.

**The version gate must fail closed.** The contract is explicit that semver proximity
is not compatibility evidence: a CLI outside the tested range is `incompatible` until
its generated schema and handshake fixtures pass.

**No shell.** A fixed argv list, never an interpolated command string.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from seshat.studio import codex_process
from seshat.studio.codex_process import (
    MAXIMUM_TESTED_CODEX,
    MINIMUM_TESTED_CODEX,
    CodexLaunchPlan,
    ProbeObservations,
    classify_health,
    is_tested_version,
    redact_provider_stderr,
)

pytestmark = pytest.mark.unit

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "codex_app_server"
WORKSPACE = Path("/workspace")


# -- launch plan ------------------------------------------------------------------- #


def test_launch_plan_is_a_fixed_argv_never_a_shell_string() -> None:
    plan = CodexLaunchPlan.for_workspace(
        Path("/workspace"), executable="/usr/bin/codex"
    )
    assert plan.argv == ("/usr/bin/codex", "app-server")
    assert all(isinstance(part, str) for part in plan.argv)
    assert plan.use_shell is False


def test_launch_plan_pins_the_workspace_as_working_directory() -> None:
    """The contract supplies workspace context out of band, via cwd."""
    plan = CodexLaunchPlan.for_workspace(Path("/workspace"), executable="codex")
    assert plan.cwd == Path("/workspace")


def test_launch_plan_gives_stdin_a_pipe_and_never_inherits_it() -> None:
    """#557: an inherited stdin under `seshat mcp` is the client's JSON-RPC pipe.

    DEVNULL is equally wrong here -- unlike the one-shot helpers, this child must be
    written to. The only correct answer is an explicit pipe.
    """
    plan = CodexLaunchPlan.for_workspace(Path("/workspace"), executable="codex")
    assert plan.stdin_is_pipe is True
    assert plan.inherits_any_handle is False


def test_launch_plan_keeps_stderr_separate_from_stdout() -> None:
    """Provider stderr carries secrets; merging it would feed them to the parser."""
    plan = CodexLaunchPlan.for_workspace(Path("/workspace"), executable="codex")
    assert plan.stderr_is_separate_pipe is True


# -- version gate ------------------------------------------------------------------ #


def test_the_tested_range_is_recorded_and_covers_the_probed_build() -> None:
    assert MINIMUM_TESTED_CODEX == "0.146.0"
    assert MAXIMUM_TESTED_CODEX == "0.147.0"


@pytest.mark.parametrize("version", ["0.146.0", "0.146.5", "0.147.0"])
def test_versions_inside_the_tested_range_are_accepted(version: str) -> None:
    assert is_tested_version(version) is True


@pytest.mark.parametrize(
    "version", ["0.145.9", "0.148.0", "1.0.0", "", "not-a-version"]
)
def test_versions_outside_the_tested_range_are_refused(version: str) -> None:
    """Fail CLOSED. A newer CLI is unproven, not presumed compatible."""
    assert is_tested_version(version) is False


def test_an_untested_version_classifies_incompatible_not_healthy() -> None:
    health = classify_health(
        ProbeObservations(executable_found=True, version="0.148.0", signed_in=True)
    )
    assert health.state == "incompatible"
    assert "0.148.0" in health.summary
    assert MAXIMUM_TESTED_CODEX in health.summary


# -- health classification --------------------------------------------------------- #


def test_absent_executable_is_missing_and_keeps_deterministic_views() -> None:
    health = classify_health(
        ProbeObservations(executable_found=False, version=None, signed_in=False)
    )
    assert health.state == "missing"
    assert health.recovery_action


def test_signed_out_is_reported_without_reading_credentials() -> None:
    health = classify_health(
        ProbeObservations(executable_found=True, version="0.147.0", signed_in=False)
    )
    assert health.state == "signed_out"


def test_quota_exhaustion_preserves_the_reported_reset_detail() -> None:
    health = classify_health(
        ProbeObservations(
            executable_found=True,
            version="0.147.0",
            signed_in=True,
            rate_limit_reached=True,
            resets_at=1786652200,
        )
    )
    assert health.state == "quota_limited"
    assert "1786652200" in health.summary or "reset" in health.summary.lower()


def test_unexpected_eof_is_crashed_and_offers_restart() -> None:
    health = classify_health(
        ProbeObservations(
            executable_found=True, version="0.147.0", signed_in=True, saw_eof=True
        )
    )
    assert health.state == "crashed"
    assert "restart" in health.recovery_action.lower()


def test_a_healthy_bridge_names_codex_as_the_provider() -> None:
    health = classify_health(
        ProbeObservations(executable_found=True, version="0.147.0", signed_in=True)
    )
    assert health.state == "healthy"
    assert health.provider == "codex"
    assert health.version == "0.147.0"


def test_no_condition_switches_the_provider_to_a_billed_path() -> None:
    """FR-013: every failure stays a reported state, never an automatic fallback."""
    conditions = [
        {"executable_found": False, "version": None, "signed_in": False},
        {"executable_found": True, "version": "0.148.0", "signed_in": True},
        {"executable_found": True, "version": "0.147.0", "signed_in": False},
        {
            "executable_found": True,
            "version": "0.147.0",
            "signed_in": True,
            "saw_eof": True,
        },
        {
            "executable_found": True,
            "version": "0.147.0",
            "signed_in": True,
            "rate_limit_reached": True,
        },
    ]
    for condition in conditions:
        health = classify_health(ProbeObservations(**condition))
        assert health.provider in {"codex", "disabled"}, (
            f"{condition} switched the provider to {health.provider!r}"
        )
        assert "api" not in health.provider.lower()


# -- stderr redaction -------------------------------------------------------------- #


def test_provider_stderr_is_redacted_before_it_is_retained() -> None:
    """The negative fixture exists to be defeated here.

    Asserted on the POSITIVE transformed form as well as absence: a redactor that
    returned an empty string would pass an absence-only check while destroying every
    diagnostic.
    """
    raw = (FIXTURE_DIR / "stderr_secrets.txt").read_text(encoding="utf-8")
    cleaned = redact_provider_stderr(raw, workspace_root=WORKSPACE)

    for secret in (
        "sk-proj-FIXTUREdeadbeefFIXTUREdeadbeef",
        "sk-FIXTUREsecretvalue",
        "FIXTUREpassword",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.FIXTURE.FIXTURE",
    ):
        assert secret not in cleaned, f"stderr redaction leaked {secret[:12]}..."

    assert "starting app-server" in cleaned, "redaction destroyed the diagnostic"
    assert "listening on stdio" in cleaned


#: A credential with NO `key=value`, `Authorization:` or DSN framing -- verbatim the
#: shape OpenAI's own "Incorrect API key provided" error prints. Every secret in
#: stderr_secrets.txt carries framing the SHARED redactor already strips, so that
#: fixture passes even with the bare-token sweep dead; this string is the only one
#: that reaches `_BARE_CREDENTIAL` at all.
_UNFRAMED_STDERR = "Incorrect API key provided: sk-live-ABCDEFGH12345678. Check it."


def test_unframed_credential_is_swept_by_the_bare_token_pass() -> None:
    """Sits on the bare-token sweep, which the framed fixture cannot reach.

    Asserts the POSITIVE transformed form (`<redacted>` present) AND that the
    surrounding diagnostic survives -- an absence-only check is satisfied by a
    redactor that returns "", and by one that never runs on input lacking the secret.
    """
    cleaned = redact_provider_stderr(_UNFRAMED_STDERR, workspace_root=WORKSPACE)

    assert "sk-live-ABCDEFGH12345678" not in cleaned
    assert "<redacted>" in cleaned, "the bare-token sweep did not fire"
    assert cleaned.startswith("Incorrect API key provided: ")
    assert cleaned.endswith(". Check it."), "redaction ate the diagnostic"


def test_the_bare_token_sweep_is_load_bearing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard-disabled negative: proves the assertion above fails without the sweep.

    Without this, `test_unframed_credential_is_swept_by_the_bare_token_pass` could
    pass for the wrong reason -- e.g. if the shared redactor happened to catch the
    token. Neutering ONLY `_BARE_CREDENTIAL` must make the raw secret reappear.

    This is the check that would have caught the stray 0x08 byte: a pattern anchored
    on a control character matches nothing, so the sweep silently became this no-op.
    """
    monkeypatch.setattr(codex_process, "_BARE_CREDENTIAL", re.compile(r"(?!x)x"))

    leaked = redact_provider_stderr(_UNFRAMED_STDERR, workspace_root=WORKSPACE)

    assert "sk-live-ABCDEFGH12345678" in leaked, (
        "the shared redactor already caught this token, so the positive test above "
        "does not actually exercise the bare-token sweep -- pick an unframed shape "
        "only _BARE_CREDENTIAL can match"
    )
