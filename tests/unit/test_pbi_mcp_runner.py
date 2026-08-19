"""Spec 149 T025-T028 -- the runner is bounded, gated, and never bypassable.

No live tenant, no network, no real ``npx``: a stub invoker drives every branch,
so acceptance is provable offline (Principle VIII).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.pbi_mcp import detect
from seshat.pbi_mcp_adapter import gate, runner

pytestmark = pytest.mark.unit


TARGET_PATH = "models/sales_model.tmdl"
OPERATION = "update_measure"


def _cleared_verdict() -> gate.GateVerdict:
    """A verdict whose every component holds.

    Built explicitly rather than by running the gate, so this module tests the
    runner in isolation. ``cleared`` is a computed property, so this cannot
    fabricate a pass that the real fields would contradict.
    """
    return gate.GateVerdict(
        target_id="sales_model",
        authorized_operation=OPERATION,
        authorized_path=TARGET_PATH,
        stage_readable=True,
        state_committed=True,
        stage_pass=True,
        approval=gate.Approval(
            stage="publish_ready",
            owner="Ahmed Shaaban (data_owner)",
            at="2026-08-18",
            note="approved for sales_model",
        ),
        approval_names_target=True,
        approval_names_operation=True,
        operation_binds=True,
        target_allowlisted=True,
        target_exists=True,
        git_safe=True,
        blockers=(),
    )


def _uncleared_verdict(**overrides: object) -> gate.GateVerdict:
    base = _cleared_verdict()
    fields = {
        **{k: getattr(base, k) for k in vars(base)},
        "blockers": (gate.BLOCKER_STAGE_NOT_PASS,),
        "stage_pass": False,
    }
    fields.update(overrides)
    return gate.GateVerdict(**fields)  # type: ignore[arg-type]


def _stub(returncode: int = 0, stdout: str = "ok", stderr: str = ""):
    calls: list[list[str]] = []

    def invoke(argv: list[str], cwd: Path):
        calls.append(argv)
        return subprocess.CompletedProcess(
            args=argv, returncode=returncode, stdout=stdout, stderr=stderr
        )

    invoke.calls = calls  # type: ignore[attr-defined]
    return invoke


# --------------------------------------------------------------------------
# T025 -- the runner refuses an uncleared gate, WITHOUT launching
# --------------------------------------------------------------------------


def test_runner_refuses_uncleared_gate(tmp_path: Path) -> None:
    """A future callsite cannot reach the runtime around the gate."""
    stub = _stub()
    result = runner.invoke(
        _uncleared_verdict(),
        repo_root=tmp_path,
        runner=stub,
    )
    assert not result.succeeded
    assert runner.BLOCKER_GATE_NOT_CLEARED in result.blockers
    assert stub.calls == [], "nothing may be launched behind an uncleared gate"


def test_refusal_reports_no_mutation_attempted(tmp_path: Path) -> None:
    """Distinguishes refused-before-launch from launched-state-unknown."""
    result = runner.invoke(
        _uncleared_verdict(),
        repo_root=tmp_path,
        runner=_stub(),
    )
    assert result.mutation_attempted is False


def test_refusal_carries_the_gate_blockers_through(tmp_path: Path) -> None:
    """The specific missing authority survives to the caller (FR-009)."""
    result = runner.invoke(
        _uncleared_verdict(blockers=(gate.BLOCKER_APPROVAL_TARGET,)),
        repo_root=tmp_path,
        runner=_stub(),
    )
    assert gate.BLOCKER_APPROVAL_TARGET in result.blockers


def test_cleared_gate_does_invoke(tmp_path: Path) -> None:
    """The positive control -- without it every refusal test above is vacuous."""
    stub = _stub()
    result = runner.invoke(
        _cleared_verdict(),
        repo_root=tmp_path,
        runner=stub,
    )
    assert result.succeeded
    assert len(stub.calls) == 1


# --------------------------------------------------------------------------
# T026 -- a stall becomes a typed outcome, never an unbounded hang
# --------------------------------------------------------------------------


def test_stall_becomes_typed_blocked_not_a_hang(tmp_path: Path) -> None:
    def stall(argv: list[str], cwd: Path):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=runner.RUN_TIMEOUT_SECONDS)

    result = runner.invoke(
        _cleared_verdict(),
        repo_root=tmp_path,
        runner=stall,
    )
    assert not result.succeeded
    assert result.exit_code == runner.TIMEOUT_EXIT_CODE
    assert runner.BLOCKER_RUNTIME_STALLED in result.blockers


def test_a_stalled_run_reports_a_mutation_was_attempted(tmp_path: Path) -> None:
    """The artifact may be half-written, so this is NOT a clean failure."""

    def stall(argv: list[str], cwd: Path):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=1)

    result = runner.invoke(
        _cleared_verdict(),
        repo_root=tmp_path,
        runner=stall,
    )
    assert result.mutation_attempted is True


def test_missing_runtime_is_typed_not_an_exception(tmp_path: Path) -> None:
    def missing(argv: list[str], cwd: Path):
        raise FileNotFoundError("npx")

    result = runner.invoke(
        _cleared_verdict(),
        repo_root=tmp_path,
        runner=missing,
    )
    assert not result.succeeded
    assert runner.BLOCKER_RUNTIME_MISSING in result.blockers
    assert result.mutation_attempted is False


def test_the_timeout_is_not_the_shared_git_cap() -> None:
    """Research R4: gitutil's short shared cap would abort a real workload.

    Pinned as a comparison against the shipped helper's own constant, so this
    cannot drift into silently reusing it.
    """
    from seshat import gitutil

    shared_cap = getattr(gitutil, "SUBPROCESS_TIMEOUT", None)
    assert runner.RUN_TIMEOUT_SECONDS >= 600
    if shared_cap is not None:
        assert runner.RUN_TIMEOUT_SECONDS > shared_cap


# --------------------------------------------------------------------------
# T028 -- the bypass flag is never constructible
# --------------------------------------------------------------------------


def test_runner_never_passes_the_bypass_flag(tmp_path: Path) -> None:
    """The built argv cannot carry the flag, whatever the caller asks for.

    Asserted on the ACTUAL argv the stub received, not on the builder's shape.
    """
    stub = _stub()
    runner.invoke(
        _cleared_verdict(),
        repo_root=tmp_path,
        runner=stub,
    )
    argv = stub.calls[0]
    assert detect._FORBIDDEN_FLAG not in " ".join(argv).lower()
    assert detect.classify_invocation_argv(argv) != detect.CONFIG_FORBIDDEN_FLAG


def test_a_bypass_flag_smuggled_into_the_argv_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defence in depth: if a future edit added the flag, the guard still fires.

    Proves the re-check in ``invoke`` is load-bearing rather than decorative --
    the reason it is there at all is that ``build_argv`` could change.
    """
    monkeypatch.setattr(
        runner,
        "build_argv",
        lambda target, operation, *, read_only: ["npx", "--skipconfirmation"],
    )
    with pytest.raises(detect.BypassFlagRefused):
        runner.invoke(
            _cleared_verdict(),
            repo_root=tmp_path,
            runner=_stub(),
        )


def test_read_only_mode_passes_readonly_explicitly(tmp_path: Path) -> None:
    """Silence means WRITE mode for local stdio, so --readonly must be explicit."""
    stub = _stub()
    runner.invoke(
        _cleared_verdict(),
        repo_root=tmp_path,
        read_only=True,
        runner=stub,
    )
    assert "--readonly" in stub.calls[0]
    assert "--readwrite" not in stub.calls[0]


def test_write_mode_is_explicit_too(tmp_path: Path) -> None:
    stub = _stub()
    runner.invoke(
        _cleared_verdict(),
        repo_root=tmp_path,
        read_only=False,
        runner=stub,
    )
    assert "--readwrite" in stub.calls[0]


def test_the_vendor_runtime_is_invoked_through_npx(tmp_path: Path) -> None:
    """Never vendored, never a Python dependency (Principle II / ADR 0018)."""
    stub = _stub()
    runner.invoke(
        _cleared_verdict(),
        repo_root=tmp_path,
        runner=stub,
    )
    argv = stub.calls[0]
    assert argv[0] == "npx"
    assert runner.VENDOR_PACKAGE in argv


# --------------------------------------------------------------------------
# Output handling: redact BEFORE truncating (#362)
# --------------------------------------------------------------------------


def test_output_is_redacted_before_truncation(tmp_path: Path) -> None:
    """Trimming first can split a DSN and leave an unrecognizable remainder."""
    noise = "x" * (runner.TAIL_CHARS + 500)
    leaky = f"{noise} host=db.example.com user=admin password=hunter2"
    result = runner.invoke(
        _cleared_verdict(),
        repo_root=tmp_path,
        runner=_stub(stdout=leaky),
    )
    assert "hunter2" not in result.output
    assert len(result.output) <= runner.TAIL_CHARS


def test_stderr_is_captured_alongside_stdout(tmp_path: Path) -> None:
    result = runner.invoke(
        _cleared_verdict(),
        repo_root=tmp_path,
        runner=_stub(returncode=1, stdout="out", stderr="boom"),
    )
    assert "boom" in result.output


def test_nonzero_exit_is_not_succeeded(tmp_path: Path) -> None:
    result = runner.invoke(
        _cleared_verdict(),
        repo_root=tmp_path,
        runner=_stub(returncode=2),
    )
    assert not result.succeeded


def test_result_is_immutable(tmp_path: Path) -> None:
    result = runner.invoke(
        _cleared_verdict(),
        repo_root=tmp_path,
        runner=_stub(),
    )
    with pytest.raises(Exception):
        result.exit_code = 0  # type: ignore[misc]


# --------------------------------------------------------------------------
# CRITICAL: a cleared verdict is not replayable against another op/path
# --------------------------------------------------------------------------


def test_the_runner_executes_only_what_the_verdict_authorized(tmp_path: Path) -> None:
    """The argv comes from the VERDICT, never from a parameter.

    The hole this closes: ``invoke`` used to take its own ``target_path`` and
    ``operation_id`` and check only ``verdict.cleared``, so a verdict legitimately
    cleared for sales_model/update_measure launched ``drop_all_tables`` against
    ``../outside.tmdl`` -- defeating the containment check the gate had just
    performed.
    """
    stub = _stub()
    runner.invoke(_cleared_verdict(), repo_root=tmp_path, runner=stub)
    argv = stub.calls[0]
    assert argv[argv.index("--target") + 1] == TARGET_PATH
    assert argv[argv.index("--operation") + 1] == OPERATION


def test_invoke_accepts_no_target_or_operation_parameter() -> None:
    """Pins the CAPABILITY: there is no parameter by which to substitute one.

    Asserted against the real signature, so re-adding either name fails here
    rather than silently reopening the replay path.
    """
    import inspect

    params = set(inspect.signature(runner.invoke).parameters)
    for forbidden in ("target_path", "operation_id", "target", "operation"):
        assert forbidden not in params, f"invoke must not accept {forbidden}"


def test_a_verdict_naming_no_path_is_refused(tmp_path: Path) -> None:
    """Defence in depth for a hand-built verdict with the pair missing."""
    base = _cleared_verdict()
    fields = {k: getattr(base, k) for k in vars(base)}
    fields["authorized_path"] = None
    verdict = gate.GateVerdict(**fields)  # type: ignore[arg-type]
    stub = _stub()
    result = runner.invoke(verdict, repo_root=tmp_path, runner=stub)
    assert not result.succeeded
    assert stub.calls == []


# --------------------------------------------------------------------------
# MED: vendor output goes through BOTH redaction layers
# --------------------------------------------------------------------------


def test_runner_output_scrubs_tenant_guids_and_user_paths(tmp_path: Path) -> None:
    """``redact`` alone cannot see these -- its own docstring says so.

    Vendor output is exactly where they appear, since the runtime prints local
    project paths.
    """
    leaky = (
        "tenant=3f2504e0-4f89-11d3-9a0c-0305e82c3301 "
        r"project=C:\Users\ahmed\models\sales.tmdl"
    )
    result = runner.invoke(
        _cleared_verdict(),
        repo_root=tmp_path,
        runner=_stub(stdout=leaky),
    )
    assert "3f2504e0-4f89-11d3-9a0c-0305e82c3301" not in result.output
    assert "ahmed" not in result.output
    assert "REDACTED" in result.output


def test_runner_output_still_scrubs_dsn_spans(tmp_path: Path) -> None:
    """The DSN layer must keep working alongside the scanner layer."""
    result = runner.invoke(
        _cleared_verdict(),
        repo_root=tmp_path,
        runner=_stub(stdout="host=db.example.com user=admin password=hunter2"),
    )
    assert "hunter2" not in result.output


# --------------------------------------------------------------------------
# Issue #658: the vendor process must not inherit the parent environment
# --------------------------------------------------------------------------


def test_credentials_never_reach_the_vendor_environment() -> None:
    """Deny by default. This is the assertion that makes the helper a gate.

    The vendor runtime is external, unforked and a public preview (ADR 0018), so
    anything in the parent environment is visible to a third party. An ABSENCE
    assertion is what catches a later edit that copies the Dagster adapter's
    prefix rules over -- that helper forwards `DATABASE_URL` and `ANALYTICS_DB_*`
    BY DESIGN, because it feeds governed Seshat connections. Forwarding a database
    credential to a preview binary would be worse than inheriting it by accident,
    because it would look deliberate.

    Issue #658.
    """
    hostile = {
        "PATH": "/usr/bin",
        "SYSTEMROOT": "C:\\Windows",
        "DATABASE_URL": "postgres://u:p@host:5432/db",
        "ANALYTICS_DB_PASSWORD": "hunter2",
        "SESHAT_DBT_PROFILE": "prod",
        "AWS_SECRET_ACCESS_KEY": "AKIAsecret",
        "GITHUB_TOKEN": "ghp_realtokenvalue",
        "AZURE_CLIENT_SECRET": "s3cret",
    }

    env = runner.allowed_vendor_environment(hostile)

    leaked = sorted(set(env) - {"PATH", "SYSTEMROOT"})
    assert not leaked, f"credential-bearing variables reached the vendor: {leaked}"
    for value in ("hunter2", "AKIAsecret", "ghp_realtokenvalue", "s3cret"):
        assert value not in "".join(env.values())


def test_the_vendor_environment_keeps_what_npx_needs() -> None:
    """Positive control: a helper returning {} would satisfy the absence test.

    Measured against the real toolchain rather than guessed:
    `npx --yes cowsay@1.6.0 hi` fetches AND executes with only PATH, SYSTEMROOT
    and PATHEXT present.
    """
    source = {
        "PATH": "/usr/bin",
        "PATHEXT": ".COM;.EXE",
        "SYSTEMROOT": "C:\\Windows",
        "APPDATA": "C:\\Users\\u\\AppData\\Roaming",
        "SECRET": "nope",
    }

    env = runner.allowed_vendor_environment(source)

    assert env["PATH"] == "/usr/bin"
    assert env["PATHEXT"] == ".COM;.EXE"
    assert "SECRET" not in env


def test_no_prefix_wildcard_widens_the_vendor_allowlist() -> None:
    """The allowlist is EXACT keys only -- no prefix rules.

    A prefix rule is how an allowlist grows silently: one governed family today,
    an unrelated match tomorrow. The Dagster helper needs prefixes; this one
    forwards no connection variables at all, so it must not have them.
    """
    invented = {
        "SESHAT_ANYTHING": "x",
        "ANALYTICS_DB_HOST": "y",
        "PBI_MCP_TOKEN": "z",
        "PATH": "/usr/bin",
    }

    env = runner.allowed_vendor_environment(invented)

    assert set(env) == {"PATH"}


def test_the_runner_passes_the_sanitized_environment() -> None:
    """The helper must actually be WIRED, not merely present.

    An injected seam that nothing calls is a tested-but-dead feature -- this
    adapter has already shipped that defect once (`config_state`), so the wiring
    gets its own assertion.
    """
    import inspect

    source = inspect.getsource(runner._run)
    assert "env=" in source, "_run does not pass an explicit environment"
    assert "allowed_vendor_environment" in source, (
        "_run does not use the sanitizing helper"
    )
