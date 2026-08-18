"""Spec 149 T029/T030 -- the end-to-end pipeline, offline.

The most important assertions here are the two the whole feature exists for:
a successful write moves **no** readiness stage (FR-018), and every terminal
state -- refusals included -- leaves exactly **one** evidence record (FR-015).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from seshat.pbi_mcp import detect
from seshat.pbi_mcp_adapter import evidence, gate, orchestrate

pytestmark = pytest.mark.unit


TARGET = "sales_model"
OPERATION = "update_measure"
TARGET_PATH = f"models/{TARGET}.tmdl"
STAMP = "2026-08-18T00:00:00Z"
OWNER = "Ahmed Shaaban (data_owner)"

READINESS = (
    "stages:\n"
    "  semantic_model_ready:\n    status: pass\n"
    "  publish_ready:\n    status: not_started\n"
    "approvals:\n"
    "  - stage: publish_ready\n"
    f"    owner: {OWNER!r}\n"
    "    at: '2026-08-18'\n"
    f"    note: 'approved for {TARGET}'\n"
)

ALLOWLIST = (
    f"targets:\n  - target_id: {TARGET}\n"
    f"    path: {TARGET_PATH}\n"
    f"    operations:\n      - {OPERATION}\n"
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _write(repo: Path, relpath: str, text: str) -> None:
    path = repo / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def ready_repo(tmp_path: Path) -> Path:
    """A repo where every precondition holds, all state COMMITTED."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@e.invalid")
    _git(tmp_path, "config", "user.name", "T")
    _write(tmp_path, f"mappings/{TARGET}/readiness-status.yaml", READINESS)
    _write(tmp_path, gate.TARGET_ALLOWLIST_RELPATH, ALLOWLIST)
    _write(tmp_path, TARGET_PATH, "// original\n")
    _write(tmp_path, "README.md", "fixture\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline", "--no-gpg-sign")
    return tmp_path


def _mcp(returncode: int = 0, mutates: str | None = None):
    """A stub runtime that optionally edits the artifact, like the real one."""

    def invoke(argv: list[str], cwd: Path):
        if mutates is not None:
            (Path(cwd) / TARGET_PATH).write_text(mutates, encoding="utf-8")
        return subprocess.CompletedProcess(
            args=argv, returncode=returncode, stdout="ok"
        )

    return invoke


def _validator(returncode: int = 0):
    def run(repo_root: Path, args: tuple[str, ...]):
        return subprocess.CompletedProcess(args=list(args), returncode=returncode)

    return run


def _apply(repo: Path, **kwargs: object) -> orchestrate.WriteReport:
    params: dict[str, object] = {
        "target_id": TARGET,
        "operation_id": OPERATION,
        "timestamp": STAMP,
        "tree_clean": True,
        "mcp_runner": _mcp(mutates="// mutated\n"),
        "validator": _validator(0),
    }
    params.update(kwargs)
    return orchestrate.apply_write(repo, **params)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# T030 -- the happy path
# --------------------------------------------------------------------------


def test_successful_write_reports_materialized(ready_repo: Path) -> None:
    report = _apply(ready_repo)
    assert report.succeeded, report.blockers
    assert report.outcome == "materialized"
    assert report.exit_code == orchestrate.EXIT_OK


def test_successful_write_changed_the_artifact(ready_repo: Path) -> None:
    _apply(ready_repo)
    assert (ready_repo / TARGET_PATH).read_text(encoding="utf-8") == "// mutated\n"


def test_successful_write_leaves_exactly_one_evidence_record(
    ready_repo: Path,
) -> None:
    report = _apply(ready_repo)
    assert report.evidence_path is not None
    records = list((ready_repo / ".seshat").glob("pbi-mcp-write-evidence*"))
    assert len(records) == 1
    payload = json.loads(report.evidence_path.read_text(encoding="utf-8"))
    assert payload["outcome"] == "materialized"
    assert payload["mutation_attempted"] is True


# --------------------------------------------------------------------------
# FR-018 -- THE assertion: no stage moves, ever
# --------------------------------------------------------------------------


def test_a_successful_write_moves_no_readiness_stage(ready_repo: Path) -> None:
    """Byte-identical readiness record before and after a green write.

    A green write is not an approval and never becomes one.
    """
    record = ready_repo / "mappings" / TARGET / "readiness-status.yaml"
    before = record.read_text(encoding="utf-8")
    report = _apply(ready_repo)
    assert report.succeeded
    assert record.read_text(encoding="utf-8") == before


def test_publish_ready_is_still_not_started_after_a_green_write(
    ready_repo: Path,
) -> None:
    """Named explicitly, because this is the stage a write might be mistaken for."""
    _apply(ready_repo)
    text = (ready_repo / "mappings" / TARGET / "readiness-status.yaml").read_text(
        encoding="utf-8"
    )
    assert "publish_ready:\n    status: not_started" in text


def test_no_approval_row_is_added_by_a_write(ready_repo: Path) -> None:
    record = ready_repo / "mappings" / TARGET / "readiness-status.yaml"
    before = record.read_text(encoding="utf-8").count("- stage:")
    _apply(ready_repo)
    assert record.read_text(encoding="utf-8").count("- stage:") == before


# --------------------------------------------------------------------------
# Refusals: one record, nothing mutated
# --------------------------------------------------------------------------


def test_refusal_leaves_the_artifact_byte_identical(ready_repo: Path) -> None:
    before = (ready_repo / TARGET_PATH).read_text(encoding="utf-8")
    report = _apply(ready_repo, operation_id="not_approved")
    assert report.exit_code == orchestrate.EXIT_REFUSED
    assert (ready_repo / TARGET_PATH).read_text(encoding="utf-8") == before


def test_refusal_still_writes_exactly_one_evidence_record(ready_repo: Path) -> None:
    """A refusal is a run (FR-015)."""
    report = _apply(ready_repo, operation_id="not_approved")
    assert report.evidence_path is not None
    payload = json.loads(report.evidence_path.read_text(encoding="utf-8"))
    assert payload["outcome"] == "blocked"
    assert payload["mutation_attempted"] is False
    assert payload["blockers"]


def test_refusal_names_the_specific_missing_authority(ready_repo: Path) -> None:
    report = _apply(ready_repo, tree_clean=False)
    assert gate.BLOCKER_GIT_UNSAFE in report.blockers


def test_unprobed_git_state_refuses(ready_repo: Path) -> None:
    report = _apply(ready_repo, tree_clean=None)
    assert report.exit_code == orchestrate.EXIT_REFUSED
    assert gate.BLOCKER_GIT_UNPROBED in report.blockers


# --------------------------------------------------------------------------
# The bypass guard runs FIRST, and raises
# --------------------------------------------------------------------------


def test_bypass_flag_raises_before_anything_runs(ready_repo: Path) -> None:
    """No gate evaluation, no invocation, no record -- it simply refuses."""
    before = (ready_repo / TARGET_PATH).read_text(encoding="utf-8")
    with pytest.raises(detect.BypassFlagRefused):
        _apply(ready_repo, argv=("--skipconfirmation",))
    assert (ready_repo / TARGET_PATH).read_text(encoding="utf-8") == before
    assert not evidence.evidence_path(ready_repo).is_file()


def test_bypass_flag_in_the_config_also_raises(ready_repo: Path) -> None:
    with pytest.raises(detect.BypassFlagRefused):
        _apply(ready_repo, config_state=detect.CONFIG_FORBIDDEN_FLAG)


# --------------------------------------------------------------------------
# Validation failure: exit 2, blocking, with guidance
# --------------------------------------------------------------------------


def test_validation_failure_is_exit_two_with_rollback(ready_repo: Path) -> None:
    report = _apply(ready_repo, validator=_validator(1))
    assert report.exit_code == orchestrate.EXIT_VALIDATION_FAILED
    assert report.rollback_guidance
    assert report.outcome == "failed"


def test_validation_failure_records_that_a_mutation_happened(
    ready_repo: Path,
) -> None:
    report = _apply(ready_repo, validator=_validator(1))
    payload = json.loads(report.evidence_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
    assert payload["mutation_attempted"] is True
    assert payload["rollback_guidance"]


def test_runtime_success_but_no_artifact_change_is_not_materialized(
    ready_repo: Path,
) -> None:
    """A no-op is reported honestly, not as an applied change (T033)."""
    (ready_repo / TARGET_PATH).unlink()
    report = _apply(ready_repo, mcp_runner=_mcp(returncode=0))
    assert not report.succeeded


# --------------------------------------------------------------------------
# A stalled runtime is INDETERMINATE (exit 3), not a clean failure
# --------------------------------------------------------------------------


def test_stalled_runtime_is_exit_three_not_exit_one(ready_repo: Path) -> None:
    """Exits 2 and 3 stay distinct: an indeterminate write is not a clean fail."""

    def stall(argv: list[str], cwd: Path):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=1)

    report = _apply(ready_repo, mcp_runner=stall)
    assert report.exit_code == orchestrate.EXIT_INDETERMINATE
    assert report.rollback_guidance
    assert report.mutation_attempted is True


def test_all_four_exit_codes_are_distinct() -> None:
    codes = {
        orchestrate.EXIT_OK,
        orchestrate.EXIT_REFUSED,
        orchestrate.EXIT_VALIDATION_FAILED,
        orchestrate.EXIT_INDETERMINATE,
    }
    assert codes == {0, 1, 2, 3}


# --------------------------------------------------------------------------
# plan-write: evaluates everything, mutates nothing, still records
# --------------------------------------------------------------------------


def test_dry_run_mutates_nothing(ready_repo: Path) -> None:
    before = (ready_repo / TARGET_PATH).read_text(encoding="utf-8")
    report = _apply(ready_repo, dry_run=True)
    assert report.succeeded
    assert report.outcome == "deferred"
    assert (ready_repo / TARGET_PATH).read_text(encoding="utf-8") == before


def test_dry_run_still_records_evidence(ready_repo: Path) -> None:
    """So the gate cannot be probed repeatedly without a trace.

    Keeps "every run produces exactly one record" literally true.
    """
    report = _apply(ready_repo, dry_run=True)
    assert report.evidence_path is not None
    payload = json.loads(report.evidence_path.read_text(encoding="utf-8"))
    assert payload["outcome"] == "deferred"
    assert payload["mutation_attempted"] is False


def test_dry_run_reports_the_same_blockers_as_apply(ready_repo: Path) -> None:
    """plan-write must be a usable preflight for apply.

    If they disagreed, the recommended dry run would be worthless.
    """
    dry = _apply(ready_repo, dry_run=True, tree_clean=False)
    wet = _apply(ready_repo, tree_clean=False)
    assert dry.blockers == wet.blockers
