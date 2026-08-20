"""Orchestrate behaviour: the FR-level guarantees of one approved write."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.pbi_mcp import detect
from seshat.pbi_mcp_adapter import evidence, gate, orchestrate, protocol, session
from tests.unit._pbi_mcp_orchestrate_fixtures import (
    MUTATED_TMDL,
    OPERATION,
    TARGET,
    TARGET_PATH,
    _apply,
    _mcp,
    _mcp_session,
    _validator,
)

pytestmark = pytest.mark.unit

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
    assert (ready_repo / TARGET_PATH).read_text(encoding="utf-8") == MUTATED_TMDL


def test_successful_write_leaves_exactly_one_evidence_record(
    ready_repo: Path,
) -> None:
    report = _apply(ready_repo)
    assert report.evidence_path is not None
    # The LATEST-run artifact carries exactly one record: `finalize` replaced the
    # `deferred` intent rather than accumulating. Asserted against the file
    # itself rather than a directory glob, which since issue #657 legitimately
    # also matches the append-only history sibling.
    assert report.evidence_path.name == "pbi-mcp-write-evidence.json"
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

    def stall(*, argv: list[str], cwd: Path, **_extra: object):  # noqa: ARG001
        class _Stalling:
            def handshake(self) -> dict:
                return {"name": "powerbi-modeling-mcp", "version": "0.5.0.0"}

            def call(self, tool: str, request: dict):
                # Stall on the OPERATION, not on the connect: a server that hangs
                # before the write is attempted is a clean refusal, whereas one
                # that hangs mid-write may have left the artifact half-written.
                # The latter is the indeterminate case this test is about.
                if request.get("operation") == "ConnectFolder":
                    return protocol.ToolOutcome(
                        ok=True,
                        read_only_hint=True,
                        payload=None,
                        raw_text="connected",
                    )
                # At #660 a stall surfaces as SessionError from the bounded read,
                # not as subprocess.TimeoutExpired.
                raise session.SessionError("no reply within deadline")

            def close(self) -> None:
                return None

        return _Stalling()

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


# --------------------------------------------------------------------------
# HIGH: the drift gate must actually GATE, not just exist as a library
# --------------------------------------------------------------------------


def test_a_drifted_runtime_refuses_the_write(ready_repo: Path) -> None:
    """Drift blocks the pipeline (FR-019).

    Before this wiring, ``drift.py``'s only importer was its own test file: 15
    green tests and a dead feature. The PBIMCP-DRIFT-* blockers could never
    appear in a real verdict, so "add the drift gate" had added a library.
    """
    from seshat.pbi_mcp_adapter import drift

    profile = drift.RuntimeCapabilityProfile(
        observed_tools=("unexpected_tool",),
        recorded_tools=("update_measure",),
    )
    before = (ready_repo / TARGET_PATH).read_text(encoding="utf-8")
    report = _apply(ready_repo, capability_profile=profile)

    assert report.exit_code == orchestrate.EXIT_REFUSED
    assert drift.BLOCKER_CAPABILITY_DRIFT in report.blockers
    assert (ready_repo / TARGET_PATH).read_text(encoding="utf-8") == before


def test_a_matching_runtime_profile_does_not_block(ready_repo: Path) -> None:
    """The positive control: a non-drifted profile must not refuse."""
    from seshat.pbi_mcp_adapter import drift

    profile = drift.RuntimeCapabilityProfile(
        observed_tools=("update_measure",),
        recorded_tools=("update_measure",),
    )
    report = _apply(ready_repo, capability_profile=profile)
    assert report.succeeded, report.blockers


def test_an_unknown_supported_range_alone_does_not_block(ready_repo: Path) -> None:
    """`unknown` is never COMPATIBLE, but it must not block a write forever.

    Both servers are unreleased previews for the life of this spec, so gating on
    version compatibility would make the feature permanently unusable.
    """
    from seshat.pbi_mcp_adapter import drift

    profile = drift.RuntimeCapabilityProfile(
        observed_tools=("update_measure",),
        recorded_tools=("update_measure",),
        supported_range=drift.UNKNOWN_RANGE,
    )
    report = _apply(ready_repo, capability_profile=profile)
    assert not profile.range_is_compatible
    assert report.succeeded, report.blockers


def test_drift_blockers_reach_the_evidence_record(ready_repo: Path) -> None:
    from seshat.pbi_mcp_adapter import drift

    profile = drift.RuntimeCapabilityProfile(
        observed_tools=(), recorded_tools=("update_measure",)
    )
    report = _apply(ready_repo, capability_profile=profile)
    payload = json.loads(report.evidence_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
    assert drift.BLOCKER_CAPABILITY_DRIFT in payload["blockers"]


# --------------------------------------------------------------------------
# MED: report and evidence blockers must never disagree
# --------------------------------------------------------------------------


def test_report_and_evidence_blockers_agree_on_an_unexplained_failure(
    ready_repo: Path,
) -> None:
    """Exit 3 was reachable with an EMPTY report blocker list.

    The fallback was substituted into the evidence record only, so an auditor
    reading records saw a cause the caller never got -- and the id used was not
    in any BLOCKER_DETAIL map.
    """

    silent_failure = _mcp_session(returncode=1)

    report = _apply(ready_repo, mcp_runner=silent_failure)
    payload = json.loads(report.evidence_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]

    assert report.blockers, "exit 3 must never be reported with no blocker"
    assert list(report.blockers) == payload["blockers"]
    from seshat.pbi_mcp_adapter import runner as runner_mod

    assert runner_mod.BLOCKER_RUNTIME_UNEXPLAINED in runner_mod.BLOCKER_DETAIL


# --------------------------------------------------------------------------
# HIGH: exit 0 from the runtime is a CLAIM, not proof of the intended mutation
# --------------------------------------------------------------------------


def test_a_no_op_run_is_not_materialized(ready_repo: Path) -> None:
    """The spec's own edge case: "returns success but touched nothing".

    Both the runtime and the validator exit 0, and the artifact is byte-identical.
    Previously reported ``materialized``.
    """
    before = (ready_repo / TARGET_PATH).read_text(encoding="utf-8")
    report = _apply(ready_repo, mcp_runner=_mcp(returncode=0))
    assert report.outcome == "failed"
    assert orchestrate.BLOCKER_TARGET_UNCHANGED in report.blockers
    assert (ready_repo / TARGET_PATH).read_text(encoding="utf-8") == before


def test_a_mutation_outside_the_authorized_target_is_rejected(
    ready_repo: Path,
) -> None:
    """Only the resolved allowlist path may change.

    A runtime that edited README.md instead previously reported ``materialized``,
    so the adapter certified a change it had not authorized.
    """

    def _hijack(cwd: Path) -> None:
        (cwd / "README.md").write_text("HIJACKED\n", encoding="utf-8")

    report = _apply(ready_repo, mcp_runner=_mcp_session(_hijack))
    assert report.outcome == "failed"
    assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE in report.blockers


def test_a_run_touching_target_AND_another_file_is_rejected(
    ready_repo: Path,
) -> None:
    """Changing the right file does not license changing others too."""

    def _both(cwd: Path) -> None:
        (cwd / TARGET_PATH).write_text(MUTATED_TMDL, encoding="utf-8")
        (cwd / "README.md").write_text("also me\n", encoding="utf-8")

    report = _apply(ready_repo, mcp_runner=_mcp_session(_both))
    assert report.outcome == "failed"
    assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE in report.blockers


def test_a_genuine_in_scope_mutation_still_materializes(ready_repo: Path) -> None:
    """The positive control.

    Without it the effect check could reject every run and still pass the three
    tests above.
    """
    report = _apply(ready_repo)
    assert report.succeeded, report.blockers
    assert report.outcome == "materialized"


def test_effect_blockers_reach_the_evidence_record(ready_repo: Path) -> None:
    report = _apply(ready_repo, mcp_runner=_mcp(returncode=0))
    payload = json.loads(report.evidence_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
    assert orchestrate.BLOCKER_TARGET_UNCHANGED in payload["blockers"]
    assert payload["rollback_guidance"]


def test_every_effect_blocker_has_readable_detail() -> None:
    ids = [
        value
        for name, value in vars(orchestrate).items()
        if name.startswith("BLOCKER_") and isinstance(value, str)
    ]
    assert len(ids) == 2
    for blocker in ids:
        assert orchestrate.BLOCKER_DETAIL.get(blocker)
        assert blocker.startswith("PBIMCP-EFF-")


# --------------------------------------------------------------------------
# The intent record lands BEFORE the mutation (FR-015 crash-survivability)
# --------------------------------------------------------------------------


def test_intent_record_exists_before_the_mutation_runs(ready_repo: Path) -> None:
    """A crash mid-write must still leave a trace naming what was attempted.

    Pinned by OBSERVATION rather than by call order: the stub runtime reads the
    evidence file at the moment it mutates, so moving `write_intent` after the
    runner -- or dropping it -- fails here. A test asserting only that a record
    exists afterwards passes either way, which is why that shape is not used.
    """
    seen: dict[str, object] = {}

    def _observe(cwd: Path) -> None:
        # Recorded on the FIRST call, so the observation is of the state before
        # any mutation -- the intent record must already exist by then.
        if "existed" in seen:
            return
        path = evidence.evidence_path(cwd)
        seen["existed"] = path.is_file()
        seen["payload"] = (
            json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
        )

    def _mutate(cwd: Path) -> None:
        (cwd / TARGET_PATH).write_text(MUTATED_TMDL, encoding="utf-8")

    report = _apply(ready_repo, mcp_runner=_mcp_session(_mutate, on_call=_observe))

    assert report.succeeded, report.blockers
    assert seen["existed"], "no intent record existed when the mutation ran"
    payload = seen["payload"]
    assert payload is not None
    assert payload["outcome"] == "deferred"
    assert payload["mutation_attempted"] is True
    assert payload["target_id"] == TARGET
    assert payload["operation_id"] == OPERATION


# --------------------------------------------------------------------------
# Issue #663 gaps 1 + 2 -- scope snapshot: ignored files, and a lossless read.
# --------------------------------------------------------------------------


def test_a_snapshot_survives_a_filename_the_locale_codec_cannot_decode(
    tmp_path: Path,
) -> None:
    """`_snapshot` caught (OSError, RuntimeError) -- the real failure is neither.

    A dead reader thread yields `stdout is None`, so `.split` raises
    AttributeError, which escapes uncaught. That abort happens AFTER
    `write_intent` has landed the `deferred` record, leaving a permanent
    "mutation attempted, never finalized" trace for a run that never mutated.
    """
    from tests.unit._gitfix import commit_all, make_git_repo

    repo = make_git_repo(tmp_path)
    (repo / "Ё.tmdl").write_text("table x\n", encoding="utf-8")
    commit_all(repo, "add a non-cp1252 filename")

    snapshot = orchestrate._snapshot(repo)

    assert "Ё.tmdl" in snapshot, f"the file vanished from the snapshot: {snapshot}"


def test_an_ignored_out_of_scope_change_is_still_out_of_scope(
    tmp_path: Path,
) -> None:
    """`--exclude-standard` without `--ignored` hid every gitignored file.

    So a vendor run that changed the authorized target AND an ignored file
    reported `materialized` with no out-of-scope blocker.
    """
    from tests.unit._gitfix import commit_all, make_git_repo

    repo = make_git_repo(tmp_path)
    (repo / ".gitignore").write_text("build/\n", encoding="utf-8")
    (repo / "target.tmdl").write_text("table x\n", encoding="utf-8")
    commit_all(repo, "seed")
    (repo / "build").mkdir()
    (repo / "build" / "leaked.txt").write_text("before\n", encoding="utf-8")

    before = orchestrate._snapshot(repo)
    (repo / "target.tmdl").write_text("table x2\n", encoding="utf-8")
    (repo / "build" / "leaked.txt").write_text("after\n", encoding="utf-8")
    after = orchestrate._snapshot(repo)

    blockers = orchestrate._effect_blockers(before, after, "target.tmdl")
    assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE in blockers, (
        f"an ignored file changed out of scope and was not reported: {blockers}"
    )


def test_the_adapters_own_evidence_artifacts_are_never_scope_creep(
    tmp_path: Path,
) -> None:
    """Both are gitignored AND written mid-run, so both must be excluded.

    The history log is append-only, so it provably differs between the two
    snapshots. Excluding only the latest-run file would make every single apply
    report out-of-scope change against itself.
    """
    from seshat.pbi_mcp_adapter import evidence
    from tests.unit._gitfix import commit_all, make_git_repo

    repo = make_git_repo(tmp_path)
    (repo / ".gitignore").write_text(
        f"{evidence.ARTIFACT_RELPATH}\n{evidence.HISTORY_RELPATH}\n", encoding="utf-8"
    )
    (repo / "target.tmdl").write_text("table x\n", encoding="utf-8")
    commit_all(repo, "seed")

    identity = evidence.RunIdentity(
        tool="t",
        mode="readwrite",
        target_id="target.tmdl",
        operation_id="op",
        timestamp="2026-08-20T00:00:00Z",
    )
    evidence.write_intent(repo, identity)
    before = orchestrate._snapshot(repo)

    (repo / "target.tmdl").write_text("table x2\n", encoding="utf-8")
    evidence.finalize(
        repo,
        evidence.RunEvidence(
            tool="t",
            mode="readwrite",
            target_id="target.tmdl",
            operation_id="op",
            timestamp="2026-08-20T00:00:00Z",
            outcome="materialized",
            mutation_attempted=True,
        ),
    )
    after = orchestrate._snapshot(repo)

    blockers = orchestrate._effect_blockers(before, after, "target.tmdl")
    assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE not in blockers, (
        f"the adapter reported its own evidence write as scope creep: {blockers}"
    )


def test_a_non_evidence_ignored_file_is_still_visible_to_the_scope_check(
    tmp_path: Path,
) -> None:
    """The exclusion is two EXACT paths, never a `.seshat/` prefix.

    A prefix exclusion would blind the check to everything under that directory
    -- measured: `.seshat/some-other-artifact.json` is a legitimate file the
    scope check must still see.
    """
    from tests.unit._gitfix import commit_all, make_git_repo

    repo = make_git_repo(tmp_path)
    (repo / ".gitignore").write_text(".seshat/\n", encoding="utf-8")
    (repo / "target.tmdl").write_text("table x\n", encoding="utf-8")
    commit_all(repo, "seed")
    (repo / ".seshat").mkdir(exist_ok=True)
    other = repo / ".seshat" / "some-other-artifact.json"
    other.write_text("before\n", encoding="utf-8")

    before = orchestrate._snapshot(repo)
    (repo / "target.tmdl").write_text("table x2\n", encoding="utf-8")
    other.write_text("after\n", encoding="utf-8")
    after = orchestrate._snapshot(repo)

    blockers = orchestrate._effect_blockers(before, after, "target.tmdl")
    assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE in blockers, (
        "a non-evidence ignored file was excluded by a prefix rule; the "
        f"exclusion must be exact-path only: {blockers}"
    )


def test_a_pre_existing_finding_elsewhere_does_not_block_an_apply(
    ready_repo: Path,
) -> None:
    """End to end for #663 gap 3.

    The corpus is repo-wide, so an error in a model this apply never touched
    must not fail the apply nor recommend rolling it back -- that rollback
    cannot fix the reported error.
    """
    other = ready_repo / "Other.SemanticModel" / "definition"
    other.mkdir(parents=True, exist_ok=True)
    (other / "other.tmdl").write_text(
        "table Other\n\tmeasure Unapproved = SUM(Other[X])\n\tcolumn X\n"
        "\t\tdataType: double\n",
        encoding="utf-8",
    )

    report = _apply(ready_repo)

    assert report.outcome == "materialized", f"blocked by: {report.blockers}"
    assert report.rollback_guidance == ()


def test_an_apply_records_the_runtime_build_that_ran(ready_repo: Path) -> None:
    """#658 end to end: the field is useless unless the apply path fills it.

    Guards the dead-field trap -- `RunResult` carrying a version that never
    reaches the record would pass every unit test and record nothing.
    """
    report = _apply(ready_repo)

    assert report.evidence_path is not None
    payload = json.loads(report.evidence_path.read_text(encoding="utf-8"))
    assert payload["runtime_version"] == "0.5.0.0", (
        f"the resolved runtime version never reached the record: {payload}"
    )
