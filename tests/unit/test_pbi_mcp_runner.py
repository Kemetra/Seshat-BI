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
OPERATION = "measure_operations.Rename"


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
        handshake_error: Exception | None = None,
    ):
        self.calls: list[tuple[str, dict]] = []
        self.handshaken = False
        self.closed = False
        self._outcomes = list(outcomes or [])
        self._raise_on_handshake = raise_on_handshake or handshake_error is not None
        self._handshake_error = handshake_error or session.SessionStalled(
            "no reply within deadline"
        )

    def handshake(self) -> dict:
        if self._raise_on_handshake:
            raise self._handshake_error
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
    # The package slot carries the version-floored SPEC since #658, not the bare
    # identity constant -- see `test_the_argv_floors_the_version_npx_may_resolve`.
    assert argv == ["npx", "--yes", runner.VENDOR_PACKAGE_SPEC, "--readonly"]


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
    assert fake.operations == ["ConnectFolder", "Rename", "ExportToTmdlFolder"]
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
    # Substring, not membership: the arg is the version-floored spec (#658), and
    # it must still CONTAIN the identity the bypass matcher keys on.
    assert any(runner.VENDOR_PACKAGE in arg for arg in argv)


def test_the_operation_vocabulary_is_the_shared_one() -> None:
    """The runner must not carry its own copy of the tool list."""
    assert "measure_operations" in vendor_ops.VENDOR_TOOLS


# --------------------------------------------------------------------------
# Review fixes -- M2 (cause fidelity), M3 (diagnosis), H3 (no escaping traceback)
# --------------------------------------------------------------------------


def test_a_closed_stream_is_not_reported_as_a_timeout(tmp_path: Path) -> None:
    """M2: a crash and a stall are different causes.

    Reporting a closed stream as "did not finish within 900s and was killed"
    tells the operator something false. Dispatch is on the exception TYPE.
    """
    fake = FakeSession(handshake_error=session.SessionError("the vendor stream closed"))
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert runner.BLOCKER_RUNTIME_STALLED not in result.blockers
    assert runner.BLOCKER_RUNTIME_UNEXPLAINED in result.blockers
    assert result.exit_code != runner.TIMEOUT_EXIT_CODE


def test_a_true_stall_still_reports_the_timeout(tmp_path: Path) -> None:
    fake = FakeSession(
        handshake_error=session.SessionStalled("the vendor sent nothing for 900s")
    )
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert runner.BLOCKER_RUNTIME_STALLED in result.blockers
    assert result.exit_code == runner.TIMEOUT_EXIT_CODE


def test_a_jsonrpc_error_frame_still_carries_a_diagnosis(tmp_path: Path) -> None:
    """M3: an error frame has no content, so raw_text is empty.

    Shipping BLOCKER_VENDOR_REFUSED with empty output left the operator nothing
    to diagnose on the most important failure path.
    """
    errored = protocol.ToolOutcome(
        ok=False,
        read_only_hint=None,
        payload=None,
        raw_text="",
        error="Method not found",
    )
    fake = FakeSession([_outcome(read_only=True), errored])
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert runner.BLOCKER_VENDOR_REFUSED in result.blockers
    assert "Method not found" in result.output


def test_an_os_error_mid_call_never_escapes_as_a_traceback(tmp_path: Path) -> None:
    """H3: an escaping exception means no RunResult, so NO evidence record.

    orchestrate only reaches `_terminate` if invoke returns, so a raw OSError
    violated FR-015 on the one path where the record matters most.
    """

    class Exploding(FakeSession):
        def call(self, tool: str, request: dict) -> protocol.ToolOutcome:
            self.calls.append((tool, request))
            raise OSError("pipe died mid-read")

    fake = Exploding()
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )
    assert isinstance(result, runner.RunResult)
    assert result.succeeded is False
    assert runner.BLOCKER_RUNTIME_UNEXPLAINED in result.blockers
    assert fake.closed is True


def test_a_read_pair_reports_no_mutation_attempted(tmp_path: Path) -> None:
    """M1's runner half: a read must not claim an attempted mutation."""
    fake = FakeSession([_outcome(read_only=True), _outcome(read_only=True)])
    result = runner.invoke(
        _cleared_verdict("measure_operations.List"),
        repo_root=tmp_path,
        session_factory=_factory(fake),
    )
    assert result.mutation_attempted is False
    assert result.succeeded is True


# --------------------------------------------------------------------------
# Re-review C2 -- a payload-needing write is REFUSED, never run hollow
# --------------------------------------------------------------------------


def test_an_operation_needing_a_definitions_payload_is_refused(tmp_path: Path) -> None:
    """C2: Update from a verb alone mutates nothing, so running it certifies a no-op.

    The server documents "For Create and Update use Definitions". This adapter is
    forbidden to invent the definition, and the approved_definitions record that
    would supply one is deferred -- so the honest answer is a LOUD refusal naming
    the missing input, never a run that reports success for nothing.

    Before #660's other fixes this path was unreachable; afterwards it executes,
    which is why the refusal has to be explicit.
    """
    fake = FakeSession()
    result = runner.invoke(
        _cleared_verdict("measure_operations.Update"),
        repo_root=tmp_path,
        session_factory=_factory(fake),
    )
    assert result.succeeded is False
    assert runner.BLOCKER_PAYLOAD_UNAVAILABLE in result.blockers
    # Nothing was launched: the refusal precedes the session entirely.
    assert fake.handshaken is False
    assert fake.calls == []
    assert result.mutation_attempted is False
    assert "never invents a definition" in result.output


def test_a_payload_free_write_is_still_executed(tmp_path: Path) -> None:
    """The refusal must be narrow: Rename needs no Definitions block."""
    fake = FakeSession(
        [_outcome(read_only=True), _outcome(read_only=False), _outcome(read_only=True)]
    )
    result = runner.invoke(
        _cleared_verdict("measure_operations.Rename"),
        repo_root=tmp_path,
        session_factory=_factory(fake),
    )
    assert runner.BLOCKER_PAYLOAD_UNAVAILABLE not in result.blockers
    assert result.succeeded is True
    assert fake.operations == ["ConnectFolder", "Rename", "ExportToTmdlFolder"]


def test_a_read_is_never_refused_for_a_missing_payload(tmp_path: Path) -> None:
    fake = FakeSession([_outcome(read_only=True), _outcome(read_only=True)])
    result = runner.invoke(
        _cleared_verdict("measure_operations.List"),
        repo_root=tmp_path,
        session_factory=_factory(fake),
    )
    assert runner.BLOCKER_PAYLOAD_UNAVAILABLE not in result.blockers
    assert result.succeeded is True


def test_a_cross_product_pair_is_refused_before_launch(tmp_path: Path) -> None:
    """H4 at the runner: a verb the named tool does not have never launches."""
    fake = FakeSession()
    result = runner.invoke(
        _cleared_verdict("dax_query_operations.Update"),
        repo_root=tmp_path,
        session_factory=_factory(fake),
    )
    assert runner.BLOCKER_UNKNOWN_OPERATION in result.blockers
    assert fake.handshaken is False


# --------------------------------------------------------------------------
# #658 -- name what actually executed, and floor what npx may resolve
# --------------------------------------------------------------------------


def test_the_resolved_runtime_version_is_captured(tmp_path: Path) -> None:
    """`npx` resolves a floating tag, so the record must name the BUILD that ran.

    Without this the invocation is not merely unpinned, it is untraceable: the
    handshake already reports `serverInfo.version` and the runner discarded it.
    """
    fake = FakeSession(
        [_outcome(read_only=True), _outcome(read_only=False), _outcome(read_only=True)]
    )
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )

    assert result.runtime_version == "0.5.0.0"


def test_a_refused_handshake_records_no_version_rather_than_a_guess(
    tmp_path: Path,
) -> None:
    """None, never the string "unknown": a fabricated value would be mistaken
    for a measured one by anyone reading the record."""
    fake = FakeSession(handshake_error=session.SessionError("refused"))
    result = runner.invoke(
        _cleared_verdict(), repo_root=tmp_path, session_factory=_factory(fake)
    )

    assert result.runtime_version is None


def test_the_argv_floors_the_version_npx_may_resolve() -> None:
    """A floor, not a pin: the package publishes only prereleases (measured
    2026-08-20 -- 0.5.0-beta.2 through beta.12, no stable release), so there is
    nothing to pin to. The range still refuses a surprise jump to an
    incompatible future major.
    """
    argv = runner.build_argv(read_only=True)
    spec = argv[2]

    assert spec == runner.VENDOR_PACKAGE_SPEC
    assert spec.startswith(runner.VENDOR_PACKAGE)
    assert "@^0.5.0-beta" in spec


def test_the_identity_constant_stays_free_of_a_version_range() -> None:
    """`VENDOR_PACKAGE` gates a REFUSAL and labels every evidence record.

    `pbi_mcp.detect` matches it as a substring of a configured server's args, so
    a version suffix on the shared identity would change what the bypass
    prohibition recognises. The range belongs to the argv only.
    """
    assert "@^" not in runner.VENDOR_PACKAGE
    assert runner.VENDOR_PACKAGE == "@microsoft/powerbi-modeling-mcp"


def test_the_bypass_matcher_still_recognises_a_version_suffixed_arg() -> None:
    """The floor must not create a hole in the bypass prohibition."""
    from seshat.pbi_mcp.detect import _is_powerbi_server

    entry = {"command": "npx", "args": ["--yes", runner.VENDOR_PACKAGE_SPEC]}

    assert _is_powerbi_server("unrelated-name", entry) is True
