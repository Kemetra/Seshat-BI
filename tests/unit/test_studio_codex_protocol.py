"""T020: JSON-RPC framing, correlation, and normalization (FR-011, FR-014, FR-015).

Written before the implementation. Every test here reads the committed fixtures
derived in T019, so the oracle is the provider's own schema rather than this
module's expectations.

Three risks drive the shape of this file:

**Correlation.** `RequestId` is `string | int64` in the real schema. `1` and `"1"`
are therefore distinct requests, and a pending-request map that stringifies its keys
would resolve one with the other's reply.

**Closed normalization.** Codex emits 70 server notifications; Studio's event enum
has 11 members. The mapping must be an explicit allowlist -- a `default: drop` is one
refactor away from becoming `default: passthrough`, and the payload it would then
pass through includes hidden reasoning.

**Absolute paths.** `Thread.cwd`, `CommandExecutionThreadItem.cwd`, and an approval's
`grantRoot` are all absolute in the real schema. FR-026 was already defeated once in
this codebase by a redaction call that silently skipped path handling, so the tests
assert on out-of-workspace values specifically, not just on "some redaction ran".
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.studio.codex_protocol import (
    CodexFrameError,
    CodexProtocolReader,
    NormalizationContext,
    PendingRequests,
    normalize_notification,
)

pytestmark = pytest.mark.unit

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "codex_app_server"
WORKSPACE = Path("/workspace")


def _frames(name: str) -> list[dict]:
    body = (FIXTURE_DIR / name).read_text(encoding="utf-8")
    return [json.loads(line) for line in body.splitlines() if line.strip()]


# -- framing --------------------------------------------------------------------- #


def test_reader_parses_newline_delimited_frames() -> None:
    reader = CodexProtocolReader()
    raw = (FIXTURE_DIR / "handshake.jsonl").read_text(encoding="utf-8")
    frames = list(reader.feed(raw))
    assert [frame.get("method") for frame in frames] == [
        "initialize",
        None,
        "initialized",
    ]


def test_reader_reassembles_a_frame_split_across_chunks() -> None:
    """A pipe read boundary lands wherever the OS puts it, not on newlines."""
    reader = CodexProtocolReader()
    line = '{"jsonrpc":"2.0","id":1,"method":"initialized"}\n'
    first = list(reader.feed(line[:20]))
    assert first == [], "a partial frame must not be emitted"
    rest = list(reader.feed(line[20:]))
    assert [frame["method"] for frame in rest] == ["initialized"]


def test_reader_tolerates_a_trailing_carriage_return() -> None:
    """Defence in depth for the CRLF hazard the fixtures are pinned against."""
    reader = CodexProtocolReader()
    frames = list(reader.feed('{"jsonrpc":"2.0","method":"initialized"}\r\n'))
    assert [frame["method"] for frame in frames] == ["initialized"]


def test_reader_rejects_unparseable_and_malformed_frames() -> None:
    """Malformed input is reported, never silently dropped.

    Silent degradation on an unreadable frame is a fail-open: the turn would appear
    to proceed while its content vanished.
    """
    reader = CodexProtocolReader()
    body = (FIXTURE_DIR / "malformed.jsonl").read_text(encoding="utf-8")
    rejected = 0
    accepted = 0
    for line in body.splitlines():
        if not line.strip():
            continue
        try:
            accepted += len(list(reader.feed(line + "\n")))
        except CodexFrameError:
            rejected += 1
    assert rejected >= 4, "malformed frames must raise, not be skipped"


# -- correlation ------------------------------------------------------------------ #


def test_string_and_integer_ids_are_distinct_requests() -> None:
    """`RequestId` is `string | int64`; conflating them resolves the wrong call."""
    pending = PendingRequests()
    pending.register(1, "account/read")
    pending.register("1", "account/rateLimits/read")

    assert pending.resolve(1) == "account/read"
    assert pending.resolve("1") == "account/rateLimits/read"
    assert pending.outstanding() == 0


def test_resolving_an_unknown_id_is_an_error() -> None:
    pending = PendingRequests()
    with pytest.raises(CodexFrameError):
        pending.resolve(9999)


def test_an_id_resolves_exactly_once() -> None:
    """A duplicated reply must not resolve a second, unrelated request."""
    pending = PendingRequests()
    pending.register(7, "thread/start")
    assert pending.resolve(7) == "thread/start"
    with pytest.raises(CodexFrameError):
        pending.resolve(7)


def test_unhashable_ids_are_refused() -> None:
    """The malformed fixture carries `id: {...}`; it must never become a map key."""
    pending = PendingRequests()
    with pytest.raises(CodexFrameError):
        pending.register({"nested": "object"}, "thread/start")


# -- normalization ---------------------------------------------------------------- #


def test_visible_stream_normalizes_to_the_closed_event_set() -> None:
    from seshat.studio.events import EVENT_TYPES

    produced = [
        event
        for frame in _frames("thread_turn.jsonl")
        if frame.get("method")
        for event in normalize_notification(
            frame, context=NormalizationContext(workspace_root=WORKSPACE)
        )
    ]
    assert produced, "the visible stream produced no events"
    for event_type, _payload in produced:
        assert event_type in EVENT_TYPES


def test_agent_message_and_plan_are_rendered() -> None:
    produced = {
        event_type
        for frame in _frames("thread_turn.jsonl")
        if frame.get("method")
        for event_type, _ in normalize_notification(
            frame, context=NormalizationContext(workspace_root=WORKSPACE)
        )
    }
    assert "agent_message" in produced
    assert "plan_updated" in produced
    assert "tool_started" in produced
    assert "tool_completed" in produced
    assert "turn_completed" in produced


def test_hidden_reasoning_never_reaches_a_studio_event() -> None:
    """The single most important assertion in this file.

    `ReasoningThreadItem` carries chain-of-thought. The fixture's reasoning content
    is a distinctive string; if any normalized payload contains it, the mapping
    defaulted to passthrough somewhere.
    """
    secret = "hidden chain of thought that must never be rendered"
    for frame in _frames("thread_turn.jsonl"):
        if not frame.get("method"):
            continue
        for _event_type, payload in normalize_notification(
            frame, context=NormalizationContext(workspace_root=WORKSPACE)
        ):
            assert secret not in json.dumps(payload)


def test_unknown_notifications_are_ignored_without_inventing_an_event() -> None:
    frame = {
        "jsonrpc": "2.0",
        "method": "totally/unknown/notification",
        "params": {"threadId": "thr_fixture"},
    }
    assert (
        list(
            normalize_notification(
                frame, context=NormalizationContext(workspace_root=WORKSPACE)
            )
        )
        == []
    )


def _command_frame(command: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "method": "item/started",
        "params": {
            "threadId": "thr_fixture",
            "turnId": "turn_fixture",
            "startedAtMs": 1,
            "item": {
                "type": "commandExecution",
                "id": "item_cmd",
                "command": command,
                "commandActions": [],
                "cwd": "/workspace/mappings",
                "status": "inProgress",
            },
        },
    }


def test_absolute_paths_in_a_rendered_payload_are_redacted() -> None:
    """FR-026, asserted on a value that actually REACHES the payload.

    An earlier version of this test asserted `"/workspace" not in payload` for a
    command whose path never entered the payload at all -- so it passed with the
    redaction call's `workspace_root` removed, which is precisely the defect #611
    fixed. Proven by mutation: drop `workspace_root` from `_scrubbed` and this test
    must fail.

    The command string is the carrier because `_public_tool_label` echoes its head,
    so a path there is genuinely rendered to the browser.
    """
    events = list(
        normalize_notification(
            _command_frame("/home/operator/secrets/list.sh --all"),
            context=NormalizationContext(workspace_root=WORKSPACE),
        )
    )
    assert events, "a command execution must produce a tool event"
    rendered = json.dumps([payload for _, payload in events])
    assert "/home/operator" not in rendered, "an out-of-workspace path was rendered"
    assert "<redacted-path>" in rendered, (
        "the path was neither relativized nor redacted, so redaction did not run"
    )


def test_in_workspace_paths_are_relativized_rather_than_blanked() -> None:
    """The workspace-relative form is what makes a tool label useful at all."""
    events = list(
        normalize_notification(
            _command_frame("/workspace/mappings/run.sh"),
            context=NormalizationContext(workspace_root=WORKSPACE),
        )
    )
    rendered = json.dumps([payload for _, payload in events])
    assert "/workspace" not in rendered
    assert "mappings/run.sh" in rendered


# -- Codex review findings, reproduced before fixing ------------------------------- #


def _file_change_frame(method: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": {
            "threadId": "thr_fixture",
            "turnId": "turn_fixture",
            "startedAtMs": 1,
            "completedAtMs": 2,
            "item": {
                "type": "fileChange",
                "id": "item_file",
                "status": "completed",
                "changes": [{"path": "mappings/source-map.yaml"}],
            },
        },
    }


def test_a_provider_file_change_becomes_write_intent_not_a_tool_event() -> None:
    """P1 (Codex review on #612): mapping `fileChange` to a tool event bypasses the
    read-only refusal.

    `agent_routes._pump_turn` refuses write intent during a `read_only` turn by
    checking `WRITE_INTENT_TYPES`, which holds `file_change_proposed` and
    `approval_required`. A `fileChange` item normalized to `tool_started`/
    `tool_completed` is not in that set, so it passes the binding guard and the
    browser never sees the proposal it is supposed to review.
    """
    produced = [
        event_type
        for frame in (
            _file_change_frame("item/started"),
            _file_change_frame("item/completed"),
        )
        for event_type, _ in normalize_notification(
            frame, context=NormalizationContext(workspace_root=WORKSPACE)
        )
    ]
    assert "file_change_proposed" in produced, (
        "a provider file change must normalize to write intent so the read-only "
        "guard can refuse it"
    )
    assert "tool_started" not in produced, (
        "the file change was normalized to a tool event, which the read-only guard "
        "does not inspect"
    )

    # Cross-checked against the REAL constant the guard reads, so this test cannot
    # drift from `agent_routes` by hardcoding the literal. Guarded because importing
    # that module pulls in fastapi, which the unit job does not install -- the
    # assertions above still run there, and this one runs wherever the app deps are.
    pytest.importorskip("fastapi")
    from seshat.studio.agent_routes import WRITE_INTENT_TYPES

    assert set(produced) & WRITE_INTENT_TYPES


def test_a_terminal_notification_without_a_status_fails_closed() -> None:
    """P2 (Codex review): a malformed `turn/completed` must not read as success."""
    frame = {"jsonrpc": "2.0", "method": "turn/completed", "params": {"turn": {}}}
    produced = dict(
        normalize_notification(
            frame, context=NormalizationContext(workspace_root=WORKSPACE)
        )
    )
    assert "turn_completed" not in produced, (
        "a terminal notification with no status became a successful turn"
    )
    assert "turn_failed" in produced


def test_provider_thread_and_turn_identifiers_stay_internal() -> None:
    """P2 (Codex review): the bridge contract keeps provider ids out of the browser."""
    frame = {
        "jsonrpc": "2.0",
        "method": "thread/started",
        "params": {"thread": {"id": "thr_provider_secret"}},
    }
    produced = list(
        normalize_notification(
            frame, context=NormalizationContext(workspace_root=WORKSPACE)
        )
    )
    rendered = json.dumps([payload for _, payload in produced])
    assert "thr_provider_secret" not in rendered


def test_an_unterminated_frame_cannot_grow_without_bound() -> None:
    """P2 (Codex review): untrusted provider output must not exhaust memory."""
    reader = CodexProtocolReader()
    with pytest.raises(CodexFrameError):
        for _ in range(200):
            list(reader.feed("x" * 10_000))


def test_an_unknown_provider_REQUEST_is_reported_not_silently_dropped() -> None:
    """P1 (Codex review): a request carries an `id` and expects an answer.

    A notification may be ignored -- it is fire-and-forget. A REQUEST cannot: Codex
    blocks waiting for a response to that id. Treating an unsupported request like an
    ignorable notification leaves the turn stalled indefinitely instead of failing
    closed as the compatibility contract requires.
    """
    from seshat.studio.codex_protocol import classify_inbound

    request = {
        "jsonrpc": "2.0",
        "id": 43,
        "method": "some/futureRequiredMethod",
        "params": {"threadId": "thr_fixture"},
    }
    verdict = classify_inbound(request)
    assert verdict.is_request is True
    assert verdict.supported is False
    assert verdict.makes_adapter_incompatible is True

    notification = {"jsonrpc": "2.0", "method": "totally/unknown", "params": {}}
    ignorable = classify_inbound(notification)
    assert ignorable.is_request is False
    assert ignorable.makes_adapter_incompatible is False


def test_a_streamed_message_is_not_replayed_whole_on_completion() -> None:
    """P2 (Codex review): deltas then a full copy renders the answer twice."""
    produced = [
        (event_type, payload)
        for frame in _frames("thread_turn.jsonl")
        if frame.get("method")
        for event_type, payload in normalize_notification(
            frame, context=NormalizationContext(workspace_root=WORKSPACE)
        )
    ]
    messages = [
        payload for event_type, payload in produced if event_type == "agent_message"
    ]
    streamed = [m for m in messages if m.get("streaming")]
    finals = [m for m in messages if not m.get("streaming")]
    assert streamed, "the fixture streams deltas"
    assert not finals, (
        "the completed item replayed the whole message after its deltas; the browser "
        "renders each agent_message as a row, so the answer appears twice"
    )


# --------------------------------------------------------------------------- #
# The provider's real envelope shape                                          #
# --------------------------------------------------------------------------- #


def test_a_frame_without_a_jsonrpc_field_is_accepted() -> None:
    """The real Codex app-server omits `jsonrpc`, and its schema never declares it.

    `JSONRPCResponse` requires only `id` and `result`; `JSONRPCNotification` only
    `method`. Neither lists `jsonrpc`. Requiring it rejected EVERY frame a live
    0.147.0 build emits -- the bridge could not read one word from a real provider.

    Every committed fixture carries `"jsonrpc":"2.0"` because they were written by
    hand from the same assumption the client made, so fixtures and client agreed
    with each other while both diverged from the provider. Only the integration
    test against the installed CLI could see it. This unit test is what keeps the
    fix verified on CI, where that integration test skips.
    """
    reader = CodexProtocolReader()

    response = list(reader.feed('{"id":1,"result":{"userAgent":"codex/0.147.0"}}\n'))
    notification = list(
        reader.feed('{"method":"remoteControl/status/changed","params":{}}\n')
    )

    assert len(response) == 1, "a real response frame was rejected"
    assert response[0]["id"] == 1
    assert len(notification) == 1, "a real notification frame was rejected"
    assert notification[0]["method"] == "remoteControl/status/changed"


def test_a_frame_declaring_the_wrong_jsonrpc_version_is_still_refused() -> None:
    """Absence is this provider's shape; a WRONG value is a different protocol.

    Without this, the fix above could have been written as "drop the rule", which
    would accept `"jsonrpc":"1.0"` -- a frame from something Studio has never been
    tested against -- as readily as the real one.
    """
    reader = CodexProtocolReader()

    with pytest.raises(CodexFrameError):
        list(reader.feed('{"jsonrpc":"1.0","id":1,"result":{}}\n'))
