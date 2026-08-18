"""Spec 149 T031-T036 -- post-write validation blocks, and cannot pass vacuously.

Review finding C2 in test form. Two independent vacuities are pinned here:

* a validator pointed at an artifact class outside its corpus examines zero bytes
  and would otherwise report clean;
* ``seshat semantic-check`` exits 0 on an empty corpus while printing "NOT a
  clean result", so exit-code-only checking is itself a fail-open.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import validation

pytestmark = pytest.mark.unit


TARGET_PATH = "models/sales_model.tmdl"


def _fake_runner(returncode: int):
    def run(repo_root: Path, args: tuple[str, ...]):
        return subprocess.CompletedProcess(
            args=list(args), returncode=returncode, stdout="", stderr=""
        )

    return run


@pytest.fixture
def repo_with_target(tmp_path: Path) -> Path:
    artifact = tmp_path / TARGET_PATH
    artifact.parent.mkdir(parents=True)
    artifact.write_text("// sales_model\n", encoding="utf-8")
    return tmp_path


# --------------------------------------------------------------------------
# C2 -- "validated" is unrepresentable when nothing was examined
# --------------------------------------------------------------------------


def test_outcome_with_no_findings_and_no_artifacts_is_refused() -> None:
    """The structural half of the fix: the invalid state cannot be built.

    A caller cannot construct a clean-looking outcome that examined nothing, so
    a future validator that quietly reads zero artifacts cannot be reported as a
    pass.
    """
    with pytest.raises(validation.ValidationInvalid):
        validation.ValidationOutcome(
            checks_run=("something",),
            artifacts_examined=(),
            failed=(),
            rollback_guidance=(),
            blockers=(),
        )


def test_read_nothing_outcome_is_blocking_not_passing() -> None:
    outcome = validation.read_nothing_outcome(("seshat semantic-check",))
    assert not outcome.passed
    assert outcome.blocking
    assert validation.BLOCKER_READ_NOTHING in outcome.blockers


def test_passed_requires_something_to_have_been_examined() -> None:
    """``passed`` has two conjuncts; dropping the second is the C2 vacuity."""
    examined = validation.ValidationOutcome(
        checks_run=("c",),
        artifacts_examined=(TARGET_PATH,),
        failed=(),
        rollback_guidance=(),
        blockers=(),
    )
    assert examined.passed

    nothing = validation.read_nothing_outcome(("c",))
    assert not nothing.passed


def test_absent_artifact_reports_read_nothing_not_success(tmp_path: Path) -> None:
    """A write that produced no artifact is not a validated write."""
    outcome = validation.validate_semantic_model(
        tmp_path, target_path=TARGET_PATH, runner=_fake_runner(0)
    )
    assert not outcome.passed
    assert validation.BLOCKER_READ_NOTHING in outcome.blockers


def test_validator_is_invoked_with_require_inputs(repo_with_target: Path) -> None:
    """The flag that turns 'no input discovered' from exit 0 into exit 1.

    Asserted on the ACTUAL argv, not on a docstring claim -- without the flag the
    validator reports clean having read nothing.
    """
    captured: dict[str, tuple[str, ...]] = {}

    def run(repo_root: Path, args: tuple[str, ...]):
        captured["args"] = args
        return subprocess.CompletedProcess(args=list(args), returncode=0, stdout="")

    validation.validate_semantic_model(
        repo_with_target, target_path=TARGET_PATH, runner=run
    )
    assert "--require-inputs" in captured["args"]


def test_validator_targets_the_semantic_model_family_not_the_report_family(
    repo_with_target: Path,
) -> None:
    """FR-013 named the R-family, which is report-layer only.

    ``rules/pbir.py`` iterates ``*.Report/definition.pbir`` and
    ``*.Report/definition/report.json``; a TMDL semantic model is in neither
    corpus, so that family would examine zero bytes of what changed.
    """
    captured: dict[str, tuple[str, ...]] = {}

    def run(repo_root: Path, args: tuple[str, ...]):
        captured["args"] = args
        return subprocess.CompletedProcess(args=list(args), returncode=0, stdout="")

    validation.validate_semantic_model(
        repo_with_target, target_path=TARGET_PATH, runner=run
    )
    assert "semantic-check" in captured["args"]


# --------------------------------------------------------------------------
# T031 / T032 -- a failure blocks and MUST carry rollback guidance
# --------------------------------------------------------------------------


def test_validation_failure_is_blocking_with_rollback(repo_with_target: Path) -> None:
    outcome = validation.validate_semantic_model(
        repo_with_target, target_path=TARGET_PATH, runner=_fake_runner(1)
    )
    assert outcome.blocking
    assert not outcome.passed
    assert outcome.rollback_guidance
    assert validation.BLOCKER_VALIDATION_FAILED in outcome.blockers


def test_guidance_cannot_be_forgotten() -> None:
    """The invalid state is unrepresentable, not merely discouraged (T032)."""
    with pytest.raises(validation.ValidationInvalid):
        validation.ValidationOutcome(
            checks_run=("c",),
            artifacts_examined=(TARGET_PATH,),
            failed=("something failed",),
            rollback_guidance=(),
            blockers=(validation.BLOCKER_VALIDATION_FAILED,),
        )


def test_failure_is_never_expressible_as_a_warning(repo_with_target: Path) -> None:
    """There is no warning level a script could ignore (FR-014)."""
    outcome = validation.validate_semantic_model(
        repo_with_target, target_path=TARGET_PATH, runner=_fake_runner(1)
    )
    assert outcome.blocking is True
    assert outcome.passed is False


# --------------------------------------------------------------------------
# T036 -- the guidance names commands that actually restore
# --------------------------------------------------------------------------


def test_rollback_guidance_uses_the_backup_ref_when_one_was_declared() -> None:
    guidance = validation.rollback_guidance_for(TARGET_PATH, "refs/tags/pre-write")
    assert any("refs/tags/pre-write" in line for line in guidance)
    assert any(line.startswith("git restore") for line in guidance)


def test_rollback_guidance_without_a_backup_restores_from_head() -> None:
    guidance = validation.rollback_guidance_for(TARGET_PATH, None)
    assert any("git restore" in line for line in guidance)
    assert all(TARGET_PATH in line for line in guidance)


def test_rollback_guidance_actually_restores_the_artifact(tmp_path: Path) -> None:
    """Runs the emitted command instead of asserting its shape.

    A string-shape assertion goes green while the command is broken -- this repo
    has shipped that defect before.
    """

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "commit.gpgsign=false", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

    git("init", "-q")
    git("config", "user.email", "t@e.invalid")
    git("config", "user.name", "T")
    artifact = tmp_path / TARGET_PATH
    artifact.parent.mkdir(parents=True)
    original = "// original\n"
    artifact.write_text(original, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "baseline", "--no-gpg-sign")

    # The "write" corrupts the artifact.
    artifact.write_text("// corrupted\n", encoding="utf-8")
    assert artifact.read_text(encoding="utf-8") != original

    guidance = validation.rollback_guidance_for(TARGET_PATH, None)
    restore = guidance[0].split("#")[0].strip()
    subprocess.run(
        restore.split(), cwd=tmp_path, check=True, capture_output=True, text=True
    )

    assert artifact.read_text(encoding="utf-8") == original, (
        "the emitted rollback command did not restore the artifact"
    )


# --------------------------------------------------------------------------
# T033 -- runtime said success but touched nothing
# --------------------------------------------------------------------------


def test_runtime_reported_success_but_touched_nothing(tmp_path: Path) -> None:
    """Validation still runs; the no-op is reported honestly.

    The artifact is absent, so nothing was examined -- reported as read-nothing
    rather than as an applied change.
    """
    outcome = validation.validate_semantic_model(
        tmp_path, target_path=TARGET_PATH, runner=_fake_runner(0)
    )
    assert not outcome.passed
    assert validation.BLOCKER_READ_NOTHING in outcome.blockers


# --------------------------------------------------------------------------
# The validator failing to run is not a pass
# --------------------------------------------------------------------------


def test_validator_timeout_is_blocking_with_rollback(repo_with_target: Path) -> None:
    """A stalled validator must not read as clean (degrade-without-reporting)."""

    def stall(repo_root: Path, args: tuple[str, ...]):
        raise subprocess.TimeoutExpired(cmd=list(args), timeout=1)

    outcome = validation.validate_semantic_model(
        repo_with_target, target_path=TARGET_PATH, runner=stall
    )
    assert outcome.blocking
    assert outcome.rollback_guidance
    assert validation.BLOCKER_VALIDATOR_ERROR in outcome.blockers


def test_validator_oserror_is_blocking(repo_with_target: Path) -> None:
    def boom(repo_root: Path, args: tuple[str, ...]):
        raise OSError("python not found")

    outcome = validation.validate_semantic_model(
        repo_with_target, target_path=TARGET_PATH, runner=boom
    )
    assert outcome.blocking
    assert validation.BLOCKER_VALIDATOR_ERROR in outcome.blockers


def test_outcome_carries_no_score(repo_with_target: Path) -> None:
    outcome = validation.validate_semantic_model(
        repo_with_target, target_path=TARGET_PATH, runner=_fake_runner(0)
    )
    for name, value in vars(outcome).items():
        if isinstance(value, bool):
            continue
        assert not isinstance(value, (int, float)), f"{name} looks like a score"


def test_every_blocker_id_has_readable_detail() -> None:
    ids = [
        value
        for name, value in vars(validation).items()
        if name.startswith("BLOCKER_") and isinstance(value, str)
    ]
    assert len(ids) == 3
    for blocker in ids:
        assert validation.BLOCKER_DETAIL.get(blocker)
        assert blocker.startswith("PBIMCP-VAL-")
