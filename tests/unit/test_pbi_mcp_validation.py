"""Spec 149 T031-T036 -- post-write validation blocks, and cannot pass vacuously.

Review finding C2 in test form. Two independent vacuities are pinned here:

* a validator pointed at an artifact class outside its corpus examines zero bytes
  and would otherwise report clean;
* ``seshat semantic-check`` exits 0 on an empty corpus while printing "NOT a
  clean result", so exit-code-only checking is itself a fail-open.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import validation

pytestmark = pytest.mark.unit


TARGET_PATH = "models/sales_model.tmdl"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


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


# --------------------------------------------------------------------------
# Codex P1 (PR #659): exit 0 does not prove the TARGET was examined
# --------------------------------------------------------------------------


def test_unparseable_target_is_a_failure_not_a_silent_pass(tmp_path: Path) -> None:
    """A corrupted target must fail validation even when the repo exits 0.

    ``semantic-check`` SKIPS a ``*.tmdl`` whose top-level ``table`` block is gone
    (``parse_tmdl`` returns ``None`` -> ``continue``). With another discoverable
    input present the command still prints "no drift" and exits 0, so asserting
    ``artifacts_examined = (target_path,)`` from the exit code alone reports a
    mutation that DESTROYED the target as ``materialized``.

    Runs the REAL validator, not a stub: a fake returning 0 cannot tell
    "examined and clean" from "skipped", which is the entire defect. The fixture
    is real for the same reason -- discovery requires a TRACKED path under
    ``*.SemanticModel/definition/``, so a ``models/x.tmdl`` fixture trips the
    empty-corpus guard and would pass for the wrong reason.

    Codex review, PR #659 (P1).
    """
    definition = tmp_path / "Sales.SemanticModel" / "definition"
    definition.mkdir(parents=True)
    # Measure-free tables, so L3 contract checks cannot supply the exit code.
    (definition / "other_model.tmdl").write_text(
        "table other_model\n\n\tcolumn Region\n\t\tdataType: string\n",
        encoding="utf-8",
    )
    target_rel = "Sales.SemanticModel/definition/sales_model.tmdl"
    target = tmp_path / target_rel
    target.write_text(
        "table sales_model\n\n\tcolumn Amount\n\t\tdataType: double\n",
        encoding="utf-8",
    )
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@e.invalid")
    _git(tmp_path, "config", "user.name", "T")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline", "--no-gpg-sign")

    # The write destroyed the target: no top-level `table` block survives.
    target.write_text("this is not tmdl at all\n", encoding="utf-8")

    outcome = validation.validate_semantic_model(
        tmp_path, target_path=target_rel, backup_ref=None
    )

    assert not outcome.passed, (
        "a DESTROYED target reported clean -- "
        f"examined={outcome.artifacts_examined} failed={outcome.failed}"
    )
    assert outcome.blockers, "a failure with no blocker is not actionable"
    assert outcome.rollback_guidance, "a destroyed target needs rollback guidance"


def test_rollback_guidance_survives_a_path_with_spaces(tmp_path: Path) -> None:
    """A PBIP path with spaces must still produce a runnable command.

    Windows PBIP projects routinely live under paths with spaces. Unquoted
    interpolation splits one pathspec into several, so the promised copy-paste
    rollback fails precisely when it is needed -- right after a bad write. Parsed
    with ``shlex.split`` (what a shell does), not ``str.split``, so the quoting is
    what is under test rather than the test's own tokenizer.

    Codex review, PR #659.
    """
    spaced = "My Model.SemanticModel/definition/sales model.tmdl"

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
    artifact = tmp_path / spaced
    artifact.parent.mkdir(parents=True)
    original = "table sales_model\n"
    artifact.write_text(original, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "baseline", "--no-gpg-sign")

    artifact.write_text("corrupted\n", encoding="utf-8")

    guidance = validation.rollback_guidance_for(spaced, None)
    restore = shlex.split(guidance[0].split("#")[0].strip())
    subprocess.run(restore, cwd=tmp_path, check=True, capture_output=True, text=True)

    assert artifact.read_text(encoding="utf-8") == original, (
        "the emitted rollback did not restore a path containing spaces: "
        f"{guidance[0]!r}"
    )


def test_rollback_guidance_neutralizes_a_hostile_ref(tmp_path: Path) -> None:
    """A backup ref is user input, so it must not be able to inject a command.

    Asserts on the TOKENS a shell would produce: the ref must arrive as one
    argument to ``--source=``, never as a second command.
    """
    hostile = "HEAD; rm -rf ."
    guidance = validation.rollback_guidance_for(TARGET_PATH, hostile)
    tokens = shlex.split(guidance[0])
    assert "rm" not in tokens, f"ref split into a second command: {tokens}"
    assert any(t == f"--source={hostile}" for t in tokens), (
        f"the ref did not survive as a single argument: {tokens}"
    )


def test_validator_runs_the_active_interpreter_not_path_python(
    repo_with_target: Path,
) -> None:
    """The subprocess must use ``sys.executable``.

    On the documented pipx install -- or any system exposing only ``python3`` --
    a bare ``python`` is absent or lacks Seshat. The mutation would succeed and
    then EVERY apply would report a post-mutation validation failure with
    rollback guidance for a write that was actually fine.

    Pins the CAPABILITY (an interpreter that can import seshat) rather than the
    literal string, so a future switch to a different absolute path still passes
    while a regression to a bare name does not.

    Codex review, PR #659.
    """
    seen: dict[str, tuple[str, ...]] = {}

    def capture(repo_root: Path, args: tuple[str, ...]):
        seen["args"] = tuple(args)
        return subprocess.CompletedProcess(args=list(args), returncode=0)

    validation.validate_semantic_model(
        repo_with_target, target_path=TARGET_PATH, runner=capture
    )

    interpreter = seen["args"][0]
    assert interpreter == sys.executable, (
        f"validator ran {interpreter!r}, not the active interpreter"
    )
    # A bare name would be resolved through PATH, which is the defect.
    assert Path(interpreter).is_absolute(), f"{interpreter!r} is PATH-resolved"
    assert Path(interpreter).exists(), f"{interpreter!r} does not exist"


def test_a_target_outside_the_validator_corpus_is_not_examined(
    tmp_path: Path,
) -> None:
    """Parseable is not the same as DISCOVERED.

    `semantic-check` only discovers tracked TMDL under `*.SemanticModel/definition/`,
    while the committed allowlist accepts any contained path. So a perfectly
    parseable target at `models/x.tmdl` is SKIPPED by the validator, and with
    another discoverable input present the command still exits 0.

    The first version of `_target_was_examined` parsed the target independently,
    which proved only that it COULD be parsed -- not that the subprocess looked at
    it. That is the same fail-open one level in.

    Codex review, PR #659 (follow-up on the ee218146 fix).
    """
    definition = tmp_path / "Sales.SemanticModel" / "definition"
    definition.mkdir(parents=True)
    # Discoverable, so the corpus is non-empty and semantic-check exits 0.
    (definition / "other.tmdl").write_text(
        "table other\n\n\tcolumn A\n\t\tdataType: string\n", encoding="utf-8"
    )
    # The TARGET: tracked and perfectly parseable, but OUTSIDE the corpus.
    target_rel = "models/sales_model.tmdl"
    target = tmp_path / target_rel
    target.parent.mkdir(parents=True)
    target.write_text(
        "table sales_model\n\n\tcolumn Amount\n\t\tdataType: double\n",
        encoding="utf-8",
    )
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@e.invalid")
    _git(tmp_path, "config", "user.name", "T")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline", "--no-gpg-sign")

    outcome = validation.validate_semantic_model(
        tmp_path, target_path=target_rel, backup_ref=None
    )

    assert not outcome.passed, (
        "a target the validator never discovers reported clean -- "
        f"examined={outcome.artifacts_examined}"
    )
    assert outcome.blockers, "a failure with no blocker is not actionable"


def test_a_target_inside_the_corpus_still_passes(tmp_path: Path) -> None:
    """The positive control: containment must not refuse everything.

    Without this, a fix that always returned "not examined" would satisfy the
    test above while breaking every real write.
    """
    definition = tmp_path / "Sales.SemanticModel" / "definition"
    definition.mkdir(parents=True)
    target_rel = "Sales.SemanticModel/definition/sales_model.tmdl"
    (tmp_path / target_rel).write_text(
        "table sales_model\n\n\tcolumn Amount\n\t\tdataType: double\n",
        encoding="utf-8",
    )
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@e.invalid")
    _git(tmp_path, "config", "user.name", "T")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline", "--no-gpg-sign")

    outcome = validation.validate_semantic_model(
        tmp_path, target_path=target_rel, backup_ref=None
    )

    assert outcome.passed, f"a discoverable target was refused: {outcome.blockers}"
    assert outcome.artifacts_examined == (target_rel,)
