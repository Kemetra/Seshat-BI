"""The CLI seam of the provisioning-approval gate (spec 154, issue #671).

The reproduction that opened #671, inverted into regression tests: an agent
supplying every caller-controlled signal available to it -- execute intent,
non-interactivity, a piped stdin answer, an attended terminal -- must not be able
to provision anything without a committed approval.
"""

from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from seshat import integrations_setup
from seshat.cli.commands.integrations import integrations_main
from seshat.integrations.approval import ApprovalVerdict
from tests.unit.test_integrations_setup import _canonical_outcome

pytestmark = pytest.mark.unit


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".seshat").mkdir()
    return tmp_path


def _args(root: Path, **overrides: object) -> Namespace:
    values: dict[str, object] = {
        "repo": str(root),
        "profile": "analytics-full",
        "refresh": False,
        "apply": False,
        "yes": False,
        "as_json": False,
    }
    values.update(overrides)
    return Namespace(**values)


@pytest.fixture
def planned(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Plan succeeds; apply FAILS the test if reached."""

    calls: list[str] = []
    outcome = _canonical_outcome(status="planned")
    monkeypatch.setattr(integrations_setup, "live_resolvers", lambda: object())
    monkeypatch.setattr(
        integrations_setup,
        "plan_profile",
        lambda *a, **k: calls.append("plan") or outcome,
    )
    monkeypatch.setattr(
        integrations_setup,
        "apply_profile",
        lambda *a, **k: (
            calls.append("apply")
            or pytest.fail("provisioning ran without a committed approval")
        ),
    )
    return calls


def test_apply_yes_without_committed_approval_does_not_provision(
    tmp_path: Path, planned: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """T028 (FR-001, FR-005): the #671 reproduction, now a regression test.

    `Namespace(apply=True, yes=True)` is exactly what an agent constructs for
    itself. Before the fix this reached `apply_profile`.
    """
    root = _workspace(tmp_path)
    exit_code = integrations_main(_args(root, refresh=True, apply=True, yes=True))
    assert "apply" not in planned
    assert exit_code != 0
    assert "approval" in capsys.readouterr().err.lower()


def test_tty_confirmation_without_committed_approval_does_not_provision(
    tmp_path: Path, planned: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """T029 (FR-006): an interactive yes is not authority."""
    root = _workspace(tmp_path)
    monkeypatch.setattr(
        "seshat.cli.commands.integrations._attended", lambda: True, raising=False
    )
    monkeypatch.setattr(integrations_setup, "confirm", lambda *a, **k: True)
    integrations_main(_args(root, refresh=True, apply=True))
    assert "apply" not in planned


def test_stdin_answer_without_committed_approval_does_not_provision(
    tmp_path: Path, planned: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """T030 (FR-006): a piped answer is not authority either."""
    import io

    root = _workspace(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO("y\n"))
    integrations_main(_args(root, refresh=True, apply=True))
    assert "apply" not in planned


def test_yes_is_never_passed_to_the_gate(
    tmp_path: Path, planned: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """T032 (FR-008): `--yes` suppresses prompting; it reaches no gate input.

    Asserted by capturing the gate's actual arguments -- a caller-controlled
    signal must not be among them.
    """
    root = _workspace(tmp_path)
    seen: list[tuple] = []

    def _spy(repo_root: Path, components: tuple[str, ...]) -> ApprovalVerdict:
        seen.append((repo_root, components))
        return ApprovalVerdict(False, "absent", "record one")

    monkeypatch.setattr("seshat.integrations.approval.evaluate", _spy)
    integrations_main(_args(root, refresh=True, apply=True, yes=True))
    assert seen, "the gate was not consulted at all"
    for call in seen:
        assert True not in call
        assert False not in call


def test_valid_committed_approval_permits_provisioning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T031 (FR-007): with real authority, provisioning proceeds and does not prompt.

    The gate is stubbed to `authorized` here ON PURPOSE: this test asserts the
    CLI honours a positive verdict. That the verdict itself cannot be faked is
    proved against the real artifact in test_integrations_approval.py.
    """

    root = _workspace(tmp_path)
    calls: list[str] = []
    outcome = _canonical_outcome(status="installed")
    monkeypatch.setattr(integrations_setup, "live_resolvers", lambda: object())
    monkeypatch.setattr(
        integrations_setup,
        "plan_profile",
        lambda *a, **k: calls.append("plan") or outcome,
    )
    monkeypatch.setattr(
        integrations_setup,
        "apply_profile",
        lambda *a, **k: calls.append("apply") or outcome,
    )
    monkeypatch.setattr(
        "seshat.integrations.approval.evaluate",
        lambda *a, **k: ApprovalVerdict(
            True, "authorized", "", owner="A B (governance)"
        ),
    )
    monkeypatch.setattr(
        integrations_setup,
        "confirm",
        lambda *a, **k: pytest.fail("prompted despite a committed approval"),
    )

    assert integrations_main(_args(root, refresh=True, apply=True, yes=True)) == 0
    assert calls == ["plan", "apply"]


def test_apply_without_refresh_still_refuses_for_exact_pins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T033b (FR-009): the pre-existing network/write preconditions are unchanged.

    This feature ADDS authorization; it relaxes nothing. With a valid approval but
    no `--refresh`, the exact-pin refusal must still fire.
    """

    root = _workspace(tmp_path)
    outcome = _canonical_outcome(status="planned")
    monkeypatch.setattr(integrations_setup, "plan_profile", lambda *a, **k: outcome)
    monkeypatch.setattr(
        integrations_setup,
        "apply_profile",
        lambda *a, **k: pytest.fail("applied without --refresh"),
    )
    monkeypatch.setattr(
        "seshat.integrations.approval.evaluate",
        lambda *a, **k: ApprovalVerdict(
            True, "authorized", "", owner="A B (governance)"
        ),
    )

    assert integrations_main(_args(root, apply=True, yes=True)) == 2


def test_gate_disabled_restores_the_old_insecure_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T034: prove the GATE is what refuses, not incidental surrounding code.

    Monkeypatch ONLY the gate to `authorized` and the pre-fix behaviour returns:
    `--apply --yes` provisions. If this test cannot make provisioning happen,
    the other refusal tests are passing for the wrong reason.
    """

    root = _workspace(tmp_path)
    calls: list[str] = []
    outcome = _canonical_outcome(status="installed")
    monkeypatch.setattr(integrations_setup, "live_resolvers", lambda: object())
    monkeypatch.setattr(integrations_setup, "plan_profile", lambda *a, **k: outcome)
    monkeypatch.setattr(
        integrations_setup,
        "apply_profile",
        lambda *a, **k: calls.append("apply") or outcome,
    )
    monkeypatch.setattr(
        "seshat.integrations.approval.evaluate",
        lambda *a, **k: ApprovalVerdict(
            True, "authorized", "", owner="A B (governance)"
        ),
    )

    integrations_main(_args(root, refresh=True, apply=True, yes=True))
    assert calls == ["apply"]


def test_refusal_output_names_a_next_action(
    tmp_path: Path, planned: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """T014/FR-014: a refusal must tell the human what to do, machine-readably."""
    root = _workspace(tmp_path)
    integrations_main(_args(root, refresh=True, apply=True, yes=True))
    err = capsys.readouterr().err
    assert "contracts/provisioning-approvals.yaml" in err


def test_no_platform_specific_literal_in_the_gate_source() -> None:
    """T036: an assertion keyed to a Windows literal goes vacuous on Linux CI."""
    from seshat.integrations import approval

    source = Path(approval.__file__).read_text(encoding="utf-8")
    assert ".exe" not in source


def test_exactly_one_approval_shape_validator_exists() -> None:
    """T040 (FR-003): the gate delegates shape validity; it does not fork it."""
    from seshat.integrations import approval

    source = Path(approval.__file__).read_text(encoding="utf-8")
    assert "from seshat.rules.readiness_status import approval_is_shape_valid" in source
    assert "def approval_is_shape_valid" not in source


def test_gate_module_performs_no_subprocess_or_network_call() -> None:
    """FR-013: the gate is read-only -- it reads committed text and nothing else."""
    from seshat.integrations import approval

    source = Path(approval.__file__).read_text(encoding="utf-8")
    for forbidden in ("subprocess", "urllib", "requests", "socket", "os.system"):
        assert forbidden not in source, forbidden
    assert subprocess is not None  # the test module may use it; the gate may not


def test_authorization_is_not_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T038 (FR-016): a valid approval does not make a failed install "ready".

    Authorization and verification are different questions. When apply runs under
    a real approval but the resulting plan still needs operator action, the run
    must report non-zero rather than success.
    """
    root = _workspace(tmp_path)
    failed = _canonical_outcome(status="failed")
    monkeypatch.setattr(integrations_setup, "live_resolvers", lambda: object())
    monkeypatch.setattr(integrations_setup, "plan_profile", lambda *a, **k: failed)
    monkeypatch.setattr(integrations_setup, "apply_profile", lambda *a, **k: failed)
    monkeypatch.setattr(
        "seshat.integrations.approval.evaluate",
        lambda *a, **k: ApprovalVerdict(
            True, "authorized", "", owner="A B (governance)"
        ),
    )

    assert integrations_main(_args(root, refresh=True, apply=True, yes=True)) != 0
