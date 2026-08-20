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
from seshat.pbi_mcp_adapter import evidence, gate, orchestrate, protocol, session

pytestmark = pytest.mark.unit


TARGET = "sales_model"
#: A (tool, operation) PAIR, per #660: the vendor dispatches on both, and the
#: pre-#660 single token encoded a `--operation` CLI flag that never existed.
#:
#: `Rename`, not `Update`: the server documents Create/Update as requiring a
#: `Definitions` payload, which this adapter is forbidden to invent, so those
#: pairs are REFUSED with PBIMCP-RUN-09 (re-review C2). `Rename` uses
#: `RenameDefinitions` and is a genuine write needing no approved definition, so
#: it exercises the connect/operate/flush path honestly.
OPERATION = "measure_operations.Rename"
#: Under `*.SemanticModel/definition/`, because that is the ONLY corpus
#: `seshat semantic-check` discovers. A fixture at `models/*.tmdl` is never
#: examined by the validator, so post-write validation could not really pass --
#: previously masked by the injected validator stub (Codex review, PR #659).
TARGET_PATH = f"Sales.SemanticModel/definition/{TARGET}.tmdl"

#: Real TMDL, not a placeholder comment. ``seshat semantic-check`` skips a
#: ``*.tmdl`` with no top-level ``table`` block, so a fixture using
#: ``// original`` gave the validator nothing to parse -- invisible here only
#: because these tests inject a validator stub returning 0.
#: ``validation._target_was_examined`` reads the artifact itself, so the content
#: has to be honest (Codex review, PR #659).
BASELINE_TMDL = "table sales_model\n\n\tcolumn Amount\n\t\tdataType: double\n"
MUTATED_TMDL = BASELINE_TMDL + "\n\tmeasure Total = SUM(sales_model[Amount])\n"
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
    f"    note: 'approved for {TARGET}: {OPERATION}'\n"
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
    _write(tmp_path, TARGET_PATH, BASELINE_TMDL)
    _write(tmp_path, "README.md", "fixture\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline", "--no-gpg-sign")
    return tmp_path


def _mcp(returncode: int = 0, mutates: str | None = None):
    """A stub MCP SESSION that optionally edits the artifact, like the real one.

    Shaped to the #660 contract: the runtime is an MCP stdio server, so the
    injected double is a session factory, not a subprocess invoker. It writes the
    artifact on the ``ExportToTmdlFolder`` call rather than on the operation --
    faithful to the real vendor, which mutates an in-memory model and only
    touches disk on the explicit flush (verified 2026-08-20).
    """

    class _Session:
        def __init__(self, cwd: Path):
            self._cwd = Path(cwd)
            self.calls: list[tuple[str, dict]] = []

        def handshake(self) -> dict:
            return {"name": "powerbi-modeling-mcp", "version": "0.5.0.0"}

        def call(self, tool: str, request: dict):
            self.calls.append((tool, request))
            operation = request.get("operation")
            if operation == "ExportToTmdlFolder" and mutates is not None:
                (self._cwd / TARGET_PATH).write_text(mutates, encoding="utf-8")
            ok = returncode == 0
            return protocol.ToolOutcome(
                ok=ok,
                # The vendor annotates per call: reads/connect/flush true, the
                # mutating operation false.
                read_only_hint=operation != "Rename",
                payload=None,
                raw_text="ok",
                error=None if ok else "the vendor reported isError",
            )

        def close(self) -> None:
            return None

    def factory(*, argv: list[str], cwd: Path, **_extra: object):  # noqa: ARG001
        return _Session(cwd)

    return factory


def _mcp_session(on_flush=None, *, returncode: int = 0, on_call=None):
    """Build a session-factory double from a side effect.

    ``on_flush(cwd)`` runs when the flush call arrives -- the only point at which
    the real vendor touches disk. ``on_call(cwd)`` runs on every call, for tests
    that need to observe ordering rather than disk state.
    """

    class _Session:
        def __init__(self, cwd: Path):
            self._cwd = Path(cwd)

        def handshake(self) -> dict:
            return {"name": "powerbi-modeling-mcp", "version": "0.5.0.0"}

        def call(self, tool: str, request: dict):
            operation = request.get("operation")
            if on_call is not None:
                on_call(self._cwd)
            if operation == "ExportToTmdlFolder" and on_flush is not None:
                on_flush(self._cwd)
            ok = returncode == 0
            return protocol.ToolOutcome(
                ok=ok,
                read_only_hint=operation != "Rename",
                payload=None,
                raw_text="ok" if ok else "",
                error=None if ok else "the vendor reported isError",
            )

        def close(self) -> None:
            return None

    def factory(*, argv: list[str], cwd: Path, **_extra: object):  # noqa: ARG001
        return _Session(cwd)

    return factory


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
        "mcp_runner": _mcp(mutates=MUTATED_TMDL),
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
    assert (ready_repo / TARGET_PATH).read_text(encoding="utf-8") == MUTATED_TMDL


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
# Codex (PR #659): git C-quotes unusual paths, so the snapshot must use -z
# --------------------------------------------------------------------------


def test_snapshot_sees_a_non_ascii_path(tmp_path: Path) -> None:
    """`git ls-files` C-quotes non-ASCII names, and stripping quotes is not decoding.

    `git ls-files` emits `"caf\303\251.tmdl"` for `café.tmdl` by default. Removing
    the surrounding quotes leaves the octal escapes intact, so `_digest` reads a
    path that does not exist, returns None, and the file DISAPPEARS from the
    snapshot -- which is what makes an out-of-scope write to such a file
    invisible to the effect check.
    """
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@e.invalid")
    _git(tmp_path, "config", "user.name", "T")
    (tmp_path / "plain.tmdl").write_text("a\n", encoding="utf-8")
    (tmp_path / "caf\u00e9.tmdl").write_text("b\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline", "--no-gpg-sign")

    snapshot = orchestrate._snapshot(tmp_path)

    assert "caf\u00e9.tmdl" in snapshot, (
        f"the non-ASCII path is missing from the snapshot: {sorted(snapshot)}"
    )
    assert "plain.tmdl" in snapshot


def test_an_out_of_scope_write_to_a_quoted_path_is_caught(tmp_path: Path) -> None:
    """The consequence: such a file must not be a blind spot for the scope check.

    This is the assertion that matters -- a runtime writing outside its authorized
    target is exactly what `_effect_blockers` exists to catch, and a path git
    quotes must not be a way around it.
    """
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@e.invalid")
    _git(tmp_path, "config", "user.name", "T")
    target = "authorized.tmdl"
    (tmp_path / target).write_text("original\n", encoding="utf-8")
    sneaky = tmp_path / "caf\u00e9.tmdl"
    sneaky.write_text("before\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline", "--no-gpg-sign")

    before = orchestrate._snapshot(tmp_path)
    # The "runtime" changes BOTH the authorized target and the quoted-path file.
    (tmp_path / target).write_text("mutated\n", encoding="utf-8")
    sneaky.write_text("after\n", encoding="utf-8")
    after = orchestrate._snapshot(tmp_path)

    blockers = orchestrate._effect_blockers(before, after, target)
    assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE in blockers, (
        "an out-of-scope write to a git-quoted path was not detected"
    )


def test_a_pre_launch_runtime_failure_is_blocked_not_failed(ready_repo: Path) -> None:
    """Exit 1 with no mutation is `blocked` per the CLI contract, not `failed`.

    `contracts/cli-contract.md` row for exit 1: "Refused before execution
    (invariant or precondition). Evidence outcome `blocked`. Nothing was mutated."
    When `npx` is absent the runtime never starts, so `mutation_attempted` is
    False and exit 1 is correct -- but the record said `failed`, giving evidence
    consumers a state the contract does not define for that exit code.

    Codex review, PR #659.
    """

    def cannot_launch(argv: list[str], cwd: Path):
        raise FileNotFoundError("npx not found")

    report = _apply(ready_repo, mcp_runner=cannot_launch)

    assert report.exit_code == orchestrate.EXIT_REFUSED
    assert not report.mutation_attempted
    assert report.outcome == "blocked", (
        f"exit 1 with no mutation recorded outcome {report.outcome!r}; the "
        "contract defines that state as 'blocked'"
    )
    payload = json.loads(report.evidence_path.read_text(encoding="utf-8"))
    assert payload["outcome"] == "blocked"
    assert payload["mutation_attempted"] is False


# --------------------------------------------------------------------------
# Review M1 -- the evidence record must not assert a mutation that never happened
# --------------------------------------------------------------------------


def test_a_read_pair_records_no_mutation_attempted(ready_repo: Path) -> None:
    """M1: orchestrate hardcoded mutation_attempted=True, discarding the runner.

    An allowlisted READ pair attempts nothing, issues no flush, and must not
    drive rollback guidance -- the evidence record asserting True for such a run
    tells an auditor a mutation was tried when none was.

    Missed before because this module defined only an `Update` pair.
    """
    read_operation = "measure_operations.List"
    read_allowlist = ALLOWLIST.replace(OPERATION, read_operation)
    _write(ready_repo, gate.TARGET_ALLOWLIST_RELPATH, read_allowlist)
    readiness = READINESS.replace(OPERATION, read_operation)
    _write(ready_repo, f"mappings/{TARGET}/readiness-status.yaml", readiness)
    _git(ready_repo, "add", "-A")
    _git(ready_repo, "commit", "-q", "-m", "read pair", "--no-gpg-sign")

    report = _apply(
        ready_repo,
        operation_id=read_operation,
        mcp_runner=_mcp_session(),
    )
    assert report.mutation_attempted is False, report.blockers
    payload = json.loads(report.evidence_path.read_text(encoding="utf-8"))
    assert payload["mutation_attempted"] is False


# --------------------------------------------------------------------------
# Review C1/H1 -- a FOLDER target: the vendor connects and flushes a directory
# --------------------------------------------------------------------------

FOLDER_TARGET = "Sales.SemanticModel"


#: Siblings inside the model folder, COMMITTED by `_folder_repo`. They must be
#: tracked: `_semantic_files` discovers from git with `include_untracked=False`,
#: so a file created mid-test is invisible to the validator's own corpus.
SIBLINGS = ("dim_customer", "dim_date", "dim_product")


def _sibling_tmdl(name: str) -> str:
    return f"table {name}\n\n\tcolumn Key\n\t\tdataType: string\n"


def _folder_repo(repo: Path) -> Path:
    """Re-point the committed allowlist at the model FOLDER, not one file."""
    _write(
        repo,
        gate.TARGET_ALLOWLIST_RELPATH,
        ALLOWLIST.replace(f"path: {TARGET_PATH}", f"path: {FOLDER_TARGET}"),
    )
    for name in SIBLINGS:
        _write(
            repo,
            f"{FOLDER_TARGET}/definition/tables/{name}.tmdl",
            _sibling_tmdl(name),
        )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "folder target", "--no-gpg-sign")
    return repo


def test_a_folder_target_clears_the_gate(ready_repo: Path) -> None:
    """C1: requiring is_file() made folder targets unusable.

    The vendor binds a TMDL *folder* and flushes it back, so a write target is
    legitimately a directory. Before this fix, a file target cleared the gate but
    could not be connected, and a folder target could be connected but never
    cleared -- the two branches were mutually exclusive and no write could run.
    """
    report = _apply(_folder_repo(ready_repo))
    assert gate.BLOCKER_TARGET_ABSENT not in report.blockers, report.blockers


def test_a_folder_write_touching_many_files_is_in_scope(ready_repo: Path) -> None:
    """H1: ExportToTmdlFolder rewrites the WHOLE folder -- 11 files, measured.

    Scoping a folder write to a single path reports an out-of-scope change on
    every legitimate apply.
    """

    def _rewrite_whole_folder(cwd: Path) -> None:
        # Faithful to the real flush: the authorized artifact AND its siblings in
        # the same model folder are all rewritten. Sibling content is valid TMDL
        # so the post-write validator has real bytes to parse -- an invalid
        # sibling would fail on PBIMCP-VAL-02 (read nothing) and prove nothing
        # about scope, which is what this test is for.
        tables = cwd / FOLDER_TARGET / "definition" / "tables"
        (cwd / TARGET_PATH).write_text(MUTATED_TMDL, encoding="utf-8")
        for name in SIBLINGS:
            (tables / f"{name}.tmdl").write_text(
                _sibling_tmdl(name) + "\tcolumn Extra\n\t\tdataType: int64\n",
                encoding="utf-8",
            )

    report = _apply(
        _folder_repo(ready_repo), mcp_runner=_mcp_session(_rewrite_whole_folder)
    )
    assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE not in report.blockers, (
        report.blockers
    )
    assert report.succeeded, report.blockers


def test_a_folder_write_escaping_the_subtree_is_STILL_refused(
    ready_repo: Path,
) -> None:
    """Widening to a subtree must not license changes outside it."""

    def _stray(cwd: Path) -> None:
        (cwd / TARGET_PATH).write_text(MUTATED_TMDL, encoding="utf-8")
        (cwd / "README.md").write_text("not in the model folder\n", encoding="utf-8")

    report = _apply(_folder_repo(ready_repo), mcp_runner=_mcp_session(_stray))
    assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE in report.blockers


def test_a_folder_write_that_changes_nothing_is_not_materialized(
    ready_repo: Path,
) -> None:
    """A no-op folder write must not report success."""
    report = _apply(_folder_repo(ready_repo), mcp_runner=_mcp_session())
    assert orchestrate.BLOCKER_TARGET_UNCHANGED in report.blockers
    assert report.succeeded is False


def test_a_prefix_sharing_sibling_is_NOT_admitted_as_in_scope() -> None:
    """Subtree scoping must not become a prefix match.

    `Sales.SemanticModel.backup/x.tmdl` shares a string prefix with the target
    but is a DIFFERENT directory. Admitting it would be a scope escape the old
    exact-match comparison did not have -- a regression introduced by the H1 fix.
    """
    target = "Sales.SemanticModel"
    for stray in (
        "Sales.SemanticModel.backup/x.tmdl",
        "Sales.SemanticModelOther/y.tmdl",
        "Sales.SemanticModel2/z.tmdl",
    ):
        blockers = orchestrate._effect_blockers({stray: "old"}, {stray: "new"}, target)
        assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE in blockers, stray


def test_a_file_target_still_authorizes_exactly_itself() -> None:
    """Widening for folders must not loosen a file target."""
    target = "Sales.SemanticModel/definition/x.tmdl"
    sibling = "Sales.SemanticModel/definition/y.tmdl"
    blockers = orchestrate._effect_blockers(
        {target: "a", sibling: "a"}, {target: "b", sibling: "b"}, target
    )
    assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE in blockers
