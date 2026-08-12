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


#: A bare JWT shape with NO `Bearer`/`Basic`/`Token` word, and no `key=`/`key:`
#: assignment, anywhere near it. Round 2's version used "auth failed for
#: token <jwt>" -- "token" sits immediately before the value, which is exactly
#: the shape `_AUTHORIZATION_HEADER` (`\b(?:Bearer|Basic|Token)\s+<value>`) in
#: the shared redactor matches on its own, so that string got redacted even
#: with `_BARE_CREDENTIAL` disabled and proved nothing about this leg. This
#: string avoids every word in `_CREDENTIAL_NAMES` and every `Bearer|Basic|
#: Token` prefix; verified below in `test_disabling_the_bare_token_regex_...`
#: that the raw JWT actually leaks when the guard is off, which is what makes
#: this string a real discriminator rather than an assumption.
_BARE_JWT_LINE = (
    "refresh rejected by upstream: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.ABCDEFGHIJK"
)


def test_bare_token_with_no_keyword_framing_is_redacted() -> None:
    """Exercises `_BARE_CREDENTIAL` specifically, not the shared boundary redactor.

    `test_provider_stderr_is_redacted_before_it_is_retained` above drives
    `stderr_secrets.txt`, but every secret there is `key=value` or
    `Authorization: Bearer <value>` framed -- shapes the shared
    `redact_for_boundary` path already strips on its own. None of them needs
    `_BARE_CREDENTIAL` to be alive at all, so that test would pass unchanged
    even if the bare-token regex never matched anything (this is exactly what
    happened when a stray control byte made `_BARE_CREDENTIAL` unmatchable).
    This test drives a standalone `sk-...` and a standalone JWT with no
    keyword prefix in front of either -- the shape OpenAI's own "Incorrect API
    key provided" error uses, which is what the module's docstring says this
    regex exists to catch.
    """
    raw = f"Incorrect API key provided: sk-live-ABCDEFGH12345678\n{_BARE_JWT_LINE}\n"
    cleaned = redact_provider_stderr(raw, workspace_root=WORKSPACE)

    assert "sk-live-ABCDEFGH12345678" not in cleaned
    assert "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.ABCDEFGHIJK" not in cleaned
    assert "<redacted>" in cleaned
    assert "Incorrect API key provided" in cleaned
    assert "refresh rejected by upstream" in cleaned


def test_disabling_the_bare_token_regex_lets_the_raw_token_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Proves `_BARE_CREDENTIAL` itself does the redacting above, not luck.

    Patches the regex object directly, in the `codex_process` namespace,
    rather than `redact_provider_stderr` as a whole -- pinning that THIS leg,
    not `redact_for_boundary` catching the shape incidentally, is what makes
    the test above pass. Reproduces the exact confusion that hid the stray
    control byte: `redact_provider_stderr` looked like it worked because it
    called something, without proving which something did the work.

    This is also the check that would have caught the 0x08 byte directly: a
    pattern anchored on a control character matches nothing, so the sweep had
    silently become exactly the no-op this test installs on purpose.

    Covers BOTH alternations in `_BARE_CREDENTIAL` (`sk-...` and the JWT
    shape) separately, so a regression in either half is caught. Round 2's
    single JWT assertion used framing the shared redactor also catches, so it
    would have kept passing even with the JWT alternation deleted outright --
    this uses `_BARE_JWT_LINE`, already proven neutral above.
    """
    monkeypatch.setattr(codex_process, "_BARE_CREDENTIAL", re.compile(r"(?!)"))

    sk_cleaned = redact_provider_stderr(
        "Incorrect API key provided: sk-live-ABCDEFGH12345678\n",
        workspace_root=WORKSPACE,
    )
    jwt_cleaned = redact_provider_stderr(
        _BARE_JWT_LINE + "\n", workspace_root=WORKSPACE
    )

    assert "sk-live-ABCDEFGH12345678" in sk_cleaned, (
        "the shared redactor already caught this token, so the positive test above "
        "does not actually exercise the bare-token sweep -- pick an unframed shape "
        "only _BARE_CREDENTIAL can match"
    )
    assert "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.ABCDEFGHIJK" in jwt_cleaned, (
        "same, for the JWT alternation -- _BARE_JWT_LINE must avoid every "
        "Bearer/Basic/Token prefix and every _CREDENTIAL_NAMES word"
    )
