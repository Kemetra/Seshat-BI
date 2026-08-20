"""Spec 149 T025-T028 + #660 -- the runner is bounded, gated, and never bypassable.

No live tenant, no network, no real ``npx``: a fake SESSION drives every branch,
so acceptance is provable offline (Principle VIII).

**Why this file changed shape at #660.** It previously asserted that the argv
contained ``--target`` and ``--operation``. Those flags do not exist on the vendor
binary (verified 2026-08-20), so those assertions pinned the bug rather than the
contract. They are replaced by assertions on the real three-call exchange:
``ConnectFolder`` -> the authorized operation -> ``ExportToTmdlFolder``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import gate, protocol, runner, session, vendor_ops

pytestmark = pytest.mark.unit


TARGET_PATH = "powerbi/Sales.SemanticModel"
OPERATION = "measure_operations.Update"


def _cleared_verdict(operation: str = OPERATION) -> gate.GateVerdict:
    """A verdict whose every component holds.

    Built explicitly rather than by running the gate, so this module tests the
    runner in isolation. ``cleared`` is a computed property, so this cannot
    fabricate a pass that the real fields would contradict.
    """
    return gate.GateVerdict(
        target_id="sales_model",
        authorized_operation=operation,
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


def _outcome(
    ok: bool = True,
    read_only: bool | None = None,
    text: str = "",
) -> protocol.ToolOutcome:
    raw = text or json.dumps({"message": "done"})
    return protocol.ToolOutcome(
        ok=ok,
        read_only_hint=read_only,
        payload=None,
        raw_text=raw,
        error=None if ok else "the vendor reported isError",
    )


class FakeSession:
    """Stands in for :class:`McpSession`; records the calls the runner makes."""

    def __init__(
        self,
        outcomes: list[protocol.ToolOutcome] | None = None,
        *,
        raise_on_handshake: bool = False,
    ):
        self.calls: list[tuple[str, dict]] = []
        self.handshaken = False
        self.closed = False
        self._outcomes = list(outcomes or [])
        self._raise_on_handshake = raise_on_handshake

    def handshake(self) -> dict:
        if self._raise_on_handshake:
            raise session.SessionError("the vendor stream closed")
        self.handshaken = True
        return {"name": "powerbi-modeling-mcp", "version": "0.5.0.0"}

    def call(self, tool: str, request: dict) -> protocol.ToolOutcome:
        self.calls.append((tool, request))
        if self._outcomes:
            return self._outcomes.pop(0)
        return _outcome()

    def close(self) -> None:
        self.closed = True

    @property
    def tools(self) -> list[str]:
        return [tool for tool, _ in self.calls]

    @property
    def operations(self) -> list[str]:
        return [request.get("operation") for _, request in self.calls]


def _factory(fake: FakeSession):
    def make(**_kwargs: object) -> FakeSession:
        return fake

    return make


# --------------------------------------------------------------------------
# #660 -- the argv no longer invents flags the vendor does not have
# --------------------------------------------------------------------------


def test_build_argv_no_longer_invents_target_or_operation_flags():
    argv = runner.build_argv(read_only=True)
    assert "--target" not in argv
    assert "--operation" not in argv
    assert argv == ["npx", "--yes", runner.VENDOR_PACKAGE, "--readonly"]


def test_build_argv_asks_for_write_mode_explicitly():
    assert "--readwrite" in runner.build_argv(read_only=False)


# --------------------------------------------------------------------------
# #660 -- the three-call write sequence, and the flush that makes it real
# --------------------------------------------------------------------------


def test_a_write_connects_operates_then_flushes(tmp_path: Path) -> None:
    """Three calls, in order. The flush is what makes the write reach disk.

    Measured 2026-08-20: Update alone returns isError:false and changes ZERO
    bytes. Without ExportToTmdlFolder the governance stack certifies a write
    that never happened.
    """
    fake = FakeSession(
        [_outcome(read_only=True), _outcome(read_only=False), _outcome(read_only=True)]
    )
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert fake.handshaken is True
    assert fake.tools == [
        "connection_operations",
        "measure_operations",
        "database_operations",
    ]
    assert fake.operations == ["ConnectFolder", "Update", "ExportToTmdlFolder"]
    assert result.succeeded is True
    assert result.mutation_attempted is True
    assert fake.closed is True


def test_the_flush_targets_the_same_folder_that_was_connected(tmp_path: Path) -> None:
    fake = FakeSession(
        [_outcome(read_only=True), _outcome(read_only=False), _outcome(read_only=True)]
    )
    runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    connected = fake.calls[0][1]["folderPath"]
    flushed = fake.calls[2][1]["tmdlFolderPath"]
    assert connected == flushed == TARGET_PATH


def test_a_read_only_operation_does_not_flush(tmp_path: Path) -> None:
    """Nothing changed in memory, so exporting would rewrite the folder for nothing."""
    fake = FakeSession([_outcome(read_only=True), _outcome(read_only=True)])
    result = runner.invoke(
        _cleared_verdict("measure_operations.List"),
        repo_root=tmp_path,
        session_factory=_factory(fake),
    )
    assert fake.tools == ["connection_operations", "measure_operations"]
    assert result.mutation_attempted is False


def test_a_failed_flush_is_a_blocker_and_never_reports_success(
    tmp_path: Path,
) -> None:
    """The in-memory mutation happened but never reached disk: indeterminate."""
    fake = FakeSession(
        [_outcome(read_only=True), _outcome(read_only=False), _outcome(ok=False)]
    )
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert result.succeeded is False
    assert runner.BLOCKER_FLUSH_FAILED in result.blockers
    assert result.mutation_attempted is True


def test_a_failed_connect_never_issues_the_operation(tmp_path: Path) -> None:
    fake = FakeSession([_outcome(ok=False)])
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert fake.tools == ["connection_operations"]
    assert result.succeeded is False
    assert result.mutation_attempted is False


def test_a_failed_operation_does_not_flush(tmp_path: Path) -> None:
    """Exporting after a failed operation would rewrite the folder for nothing."""
    fake = FakeSession([_outcome(read_only=True), _outcome(ok=False)])
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert "database_operations" not in fake.tools
    assert runner.BLOCKER_VENDOR_REFUSED in result.blockers


def test_a_write_the_vendor_calls_read_only_is_a_violation(tmp_path: Path) -> None:
    """Cross-check our classification against the vendor's per-call annotation."""
    fake = FakeSession([_outcome(read_only=True), _outcome(read_only=True)])
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert runner.BLOCKER_READONLY_VIOLATION in result.blockers
    assert result.succeeded is False
    # And it must NOT have flushed on a disagreement.
    assert "database_operations" not in fake.tools


def test_an_unknown_hint_is_not_treated_as_a_violation(tmp_path: Path) -> None:
    """Absent means unknown; refusing on unknown would block every real write."""
    fake = FakeSession(
        [_outcome(read_only=True), _outcome(read_only=None), _outcome(read_only=True)]
    )
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert runner.BLOCKER_READONLY_VIOLATION not in result.blockers
    assert result.succeeded is True


# --------------------------------------------------------------------------
# T025 -- the runner refuses an uncleared gate, WITHOUT launching
# --------------------------------------------------------------------------


def test_runner_refuses_uncleared_gate(tmp_path: Path) -> None:
    fake = FakeSession()
    result = runner.invoke(
        _uncleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert result.mutation_attempted is False
    assert fake.handshaken is False
    assert fake.calls == []
    assert runner.BLOCKER_GATE_NOT_CLEARED in result.blockers


def test_an_unknown_operation_pair_is_refused_before_launch(tmp_path: Path) -> None:
    """The pre-#660 single-token form is rejected, not reinterpreted."""
    fake = FakeSession()
    result = runner.invoke(
        _cleared_verdict("update_measure"),
        repo_root=tmp_path,
        session_factory=_factory(fake),
    )
    assert fake.handshaken is False
    assert result.mutation_attempted is False
    assert runner.BLOCKER_UNKNOWN_OPERATION in result.blockers


def test_an_unknown_tool_is_refused_before_launch(tmp_path: Path) -> None:
    fake = FakeSession()
    result = runner.invoke(
        _cleared_verdict("not_a_tool.Update"),
        repo_root=tmp_path,
        session_factory=_factory(fake),
    )
    assert fake.handshaken is False
    assert runner.BLOCKER_UNKNOWN_OPERATION in result.blockers


# --------------------------------------------------------------------------
# T026/T027 -- failure modes are typed results, never exceptions
# --------------------------------------------------------------------------


def test_a_stalled_session_reports_a_mutation_was_attempted(tmp_path: Path) -> None:
    """A hung child is a blocked run with the artifact possibly half-written."""
    fake = FakeSession(raise_on_handshake=True)
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert runner.BLOCKER_RUNTIME_STALLED in result.blockers
    assert result.exit_code == runner.TIMEOUT_EXIT_CODE
    assert fake.closed is True


def test_missing_runtime_is_typed_not_an_exception(tmp_path: Path) -> None:
    def exploding(**_kwargs: object):
        raise OSError("npx not found")

    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=exploding
    )
    assert result.mutation_attempted is False
    assert runner.BLOCKER_RUNTIME_MISSING in result.blockers


# --------------------------------------------------------------------------
# T028 -- redaction, through BOTH layers, before truncation
# --------------------------------------------------------------------------


def test_output_is_redacted_through_both_layers(tmp_path: Path) -> None:
    leaky = _outcome(read_only=False, text="postgresql://u:hunter2@host/db")
    fake = FakeSession([_outcome(read_only=True), leaky, _outcome(read_only=True)])
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert "hunter2" not in result.output


def test_the_transcript_is_bounded(tmp_path: Path) -> None:
    huge = _outcome(read_only=False, text="x" * (runner.TAIL_CHARS * 2))
    fake = FakeSession([_outcome(read_only=True), huge, _outcome(read_only=True)])
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert len(result.output) <= runner.TAIL_CHARS


# --------------------------------------------------------------------------
# The standing bypass prohibition
# --------------------------------------------------------------------------


def test_runner_never_passes_the_bypass_flag(tmp_path: Path) -> None:
    fake = FakeSession(
        [_outcome(read_only=True), _outcome(read_only=False), _outcome(read_only=True)]
    )
    runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert "--skipconfirmation" not in runner.build_argv(read_only=False)


def test_a_bypass_flag_smuggled_into_the_argv_still_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The re-check exists because ``build_argv`` could change."""
    monkeypatch.setattr(
        runner, "build_argv", lambda *, read_only: ["npx", "--skipconfirmation"]
    )
    with pytest.raises(Exception):  # noqa: B017, PT011 - refusal type is detect's
        runner.invoke(
            _cleared_verdict(),
            repo_root=tmp_path,
            session_factory=_factory(FakeSession()),
        )


def test_the_vendor_runtime_is_invoked_through_npx(tmp_path: Path) -> None:
    argv = runner.build_argv(read_only=False)
    assert argv[0] == "npx"
    assert runner.VENDOR_PACKAGE in argv


def test_the_operation_vocabulary_is_the_shared_one() -> None:
    """The runner must not carry its own copy of the tool list."""
    assert "measure_operations" in vendor_ops.VENDOR_TOOLS
