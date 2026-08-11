"""Codex app-server JSON-RPC framing, correlation, and normalization (T020).

This module is deliberately PURE: it parses bytes into frames, tracks which request a
reply belongs to, and translates provider notifications into Studio's closed event
vocabulary. It starts no process and performs no I/O, so every rule in here is testable
against the committed fixtures without a Codex CLI present. Process lifecycle is T021's
concern and lives beside this, not inside it.

Three decisions carry most of the weight:

**Correlation is identity-typed.** The generated schema declares `RequestId` as
`string | int64`, so `1` and `"1"` are different requests. A pending map keyed on
`str(id)` would resolve one call with another's reply -- a silent cross-wire, not a
crash. The map therefore keys on `(type-name, value)`.

**Normalization is an explicit allowlist, never a default.** Codex emits 70 server
notifications; `EVENT_TYPES` has 11 members. A `default: passthrough` would forward
`ReasoningThreadItem`, which carries chain-of-thought, so unmapped methods produce
NOTHING and are merely recorded by name for redacted diagnostics. This is the one rule
here that is a safety property rather than a convenience.

**Malformed input raises.** A frame that cannot be parsed is not skipped: silently
dropping it would let a turn appear to proceed while its content vanished, which is a
fail-open dressed as resilience.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from seshat.studio.redaction import scrub_payload

__all__ = [
    "CodexFrameError",
    "CodexProtocolReader",
    "NormalizationContext",
    "InboundVerdict",
    "SUPPORTED_SERVER_REQUESTS",
    "classify_inbound",
    "PendingRequests",
    "UNMAPPED_METHODS",
    "normalize_notification",
]


class CodexFrameError(ValueError):
    """A provider frame violated the JSON-RPC envelope, or correlation failed."""


#: JSON-RPC version every frame must declare.
_JSONRPC_VERSION = "2.0"

#: Ceiling on one unterminated frame. Provider output is untrusted: a crashed or
#: misbehaving app-server that never emits a newline would otherwise grow this
#: buffer until Studio runs out of memory, instead of producing a protocol failure.
MAX_FRAME_BYTES = 1_000_000

#: Item types Studio renders. Anything absent here is dropped, including `reasoning`.
_RENDERED_ITEM_TYPES = frozenset(
    {"agentMessage", "plan", "commandExecution", "fileChange", "mcpToolCall"}
)

#: Item types that are TOOLS for rendering purposes -- they get tool_started/completed.
#:
#: `fileChange` is deliberately NOT here. It carries WRITE INTENT, and
#: `agent_routes._record_turn` enforces the read-only refusal by checking
#: `WRITE_INTENT_TYPES` (`file_change_proposed`, `approval_required`). Normalizing a
#: provider file change to a tool event would sail straight past that guard during a
#: `read_only` turn, and the browser would never receive the proposal it must review.
_TOOL_ITEM_TYPES = frozenset({"commandExecution", "mcpToolCall"})

#: Provider turn statuses that end a turn, mapped to Studio's two terminal events.
_TERMINAL_STATUS = {
    "completed": "turn_completed",
    "interrupted": "turn_failed",
    "failed": "turn_failed",
}

#: Notification method names seen but deliberately not mapped. Module-level so a
#: diagnostics view can report what the provider sent without widening the event set.
UNMAPPED_METHODS: set[str] = set()

#: What every notification handler returns: zero or more (event_type, payload) pairs.
_Events = tuple[tuple[str, dict[str, Any]], ...]


@dataclass(frozen=True, slots=True)
class InboundVerdict:
    """What an inbound frame is, and whether the adapter can honour it."""

    is_request: bool
    supported: bool
    method: str

    @property
    def makes_adapter_incompatible(self) -> bool:
        """An unsupported REQUEST is fatal; an unsupported notification is not.

        A notification is fire-and-forget, so ignoring one costs nothing. A request
        carries an `id` and Codex BLOCKS waiting for that response -- dropping it
        strands the turn forever. The compatibility contract calls for
        `incompatible` and no new turns, which is a visible failure rather than a
        silent stall.
        """
        return self.is_request and not self.supported


#: Server requests Studio knows how to answer. Anything else with an `id` is fatal.
SUPPORTED_SERVER_REQUESTS: frozenset[str] = frozenset(
    {
        "item/commandExecution/requestApproval",
        "item/fileChange/requestApproval",
    }
)


def classify_inbound(frame: dict[str, Any]) -> InboundVerdict:
    """Decide whether Studio can honour one inbound frame."""
    method = str(frame.get("method", ""))
    is_request = "id" in frame and "method" in frame
    if is_request:
        return InboundVerdict(
            is_request=True,
            supported=method in SUPPORTED_SERVER_REQUESTS,
            method=method,
        )
    return InboundVerdict(
        is_request=False,
        supported=method in _NOTIFICATION_MAP,
        method=method,
    )


class CodexProtocolReader:
    """Reassembles newline-delimited JSON frames from arbitrary chunk boundaries.

    A pipe read returns whatever the OS had buffered, which splits mid-token as often
    as not. Holding a partial line until its newline arrives is the whole job.
    """

    def __init__(self, *, max_frame_bytes: int = MAX_FRAME_BYTES) -> None:
        self._buffer = ""
        self._max_frame_bytes = max_frame_bytes

    def feed(self, chunk: str) -> Iterator[dict[str, Any]]:
        """Yield every complete frame in `chunk`, retaining any partial tail."""
        self._buffer += chunk
        if len(self._buffer) > self._max_frame_bytes:
            self._buffer = ""
            raise CodexFrameError(
                f"provider frame exceeded {self._max_frame_bytes} bytes without a "
                "newline; refusing to buffer untrusted output without bound"
            )
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if line:
                yield _parse_frame(line)

    @property
    def pending_bytes(self) -> int:
        """Length of the unterminated tail, for a stall diagnostic."""
        return len(self._buffer)


def _decoded(line: str) -> dict[str, Any]:
    """JSON text to a frame object, or a typed error. No envelope rules here."""
    try:
        frame = json.loads(line)
    except json.JSONDecodeError as error:
        raise CodexFrameError(f"unparseable provider frame: {error}") from error
    if not isinstance(frame, dict):
        raise CodexFrameError("provider frame was not a JSON object")
    return frame


def _declares_jsonrpc_2(frame: dict[str, Any]) -> bool:
    return frame.get("jsonrpc") == _JSONRPC_VERSION


def _is_call_or_reply(frame: dict[str, Any]) -> bool:
    return any(key in frame for key in ("method", "result", "error"))


def _has_usable_id(frame: dict[str, Any]) -> bool:
    """An absent id is fine -- notifications have none. A non-scalar one is not."""
    return "id" not in frame or _is_valid_request_id(frame["id"])


#: Envelope rules as data, each paired with what to say when it fails. Expressed this
#: way so adding a rule is appending a row rather than deepening a function -- the
#: shape that let the previous version accumulate three guards and trip the
#: complexity gate.
_ENVELOPE_RULES: tuple[tuple[Callable[[dict[str, Any]], bool], str], ...] = (
    (_declares_jsonrpc_2, "provider frame did not declare jsonrpc 2.0"),
    (_is_call_or_reply, "provider frame is neither a call nor a reply"),
    (_has_usable_id, "provider frame carried a non-scalar id"),
)


def _check_envelope(frame: dict[str, Any]) -> None:
    """Every rule a well-formed JSON-RPC frame must satisfy."""
    for rule, message in _ENVELOPE_RULES:
        if not rule(frame):
            raise CodexFrameError(message)


def _parse_frame(line: str) -> dict[str, Any]:
    frame = _decoded(line)
    _check_envelope(frame)
    return frame


def _is_valid_request_id(value: object) -> bool:
    """`RequestId` is `string | int64`. Booleans are ints in Python but not ids."""
    if isinstance(value, bool):
        return False
    return isinstance(value, (str, int))


def _id_key(value: object) -> tuple[str, object]:
    """Key that keeps `1` and `"1"` distinct, as the schema requires."""
    if not _is_valid_request_id(value):
        raise CodexFrameError(f"request id {value!r} is not a string or integer")
    return (type(value).__name__, value)


class PendingRequests:
    """Outstanding request ids, each resolvable exactly once."""

    def __init__(self) -> None:
        self._pending: dict[tuple[str, object], str] = {}

    def register(self, request_id: object, method: str) -> None:
        key = _id_key(request_id)
        if key in self._pending:
            raise CodexFrameError(f"request id {request_id!r} is already outstanding")
        self._pending[key] = method

    def resolve(self, request_id: object) -> str:
        """Return the method a reply belongs to, removing it from the pending set."""
        key = _id_key(request_id)
        try:
            return self._pending.pop(key)
        except KeyError:
            raise CodexFrameError(
                f"reply for unknown request id {request_id!r}"
            ) from None

    def outstanding(self) -> int:
        return len(self._pending)

    def methods(self) -> Sequence[str]:
        return tuple(self._pending.values())


# -- normalization ----------------------------------------------------------------- #


class _DeltaBuffer:
    """Redacts each item's message CUMULATIVELY, emitting only the new safe suffix.

    Redaction rules key on a PREFIX -- a credential name, an auth scheme, a DSN
    `scheme://` -- followed by the value. Scrubbing each delta in isolation therefore
    misses any credential the provider split across two frames: the first chunk holds
    a prefix with no value, the second a bare value matching no rule.

    So nothing is scrubbed in isolation. Each item's raw text is accumulated, the
    WHOLE accumulation is redacted every time, and only the part of that redacted
    text not yet sent is emitted. The redactor always sees complete context, so the
    splitting window does not exist -- rather than being narrowed by a heuristic.

    Keyed per ITEM, never per stream: Codex interleaves items, and one shared slot
    would splice item A's text onto item B -- corrupting the transcript and creating
    a second leak path rather than closing the first.

    Cost is O(n^2) in one message's length. Deliberate: chat-length answers make that
    irrelevant, and a smarter incremental scheme would reintroduce the very
    partial-match reasoning this design exists to avoid.
    """

    #: Deltas that arrive without an `itemId` share this slot. The provider always
    #: sends one, so this is a malformed-input path -- but a per-arrival slot would
    #: scrub each delta alone, which is exactly the defect being fixed.
    _UNKEYED = ""

    def __init__(self) -> None:
        #: item key -> (raw accumulated text, redacted text already emitted)
        self._items: dict[str, tuple[str, str]] = {}

    def push(self, item_id: str, text: str, scrub: Callable[[str], str]) -> str:
        """Accumulate `text`, returning only newly-safe redacted output.

        Returns `""` when the fresh redaction is NOT an extension of what was already
        emitted -- which happens when a redaction rewrites text already sent, as when
        `Authorization: <redacted> ` becomes `Authorization: <redacted>` once the
        token arrives. Emitting a "suffix" computed against a diverged string is
        precisely how a raw-offset implementation leaks the credential, so this
        emits nothing and lets the terminal flush reconcile the item.
        """
        key = item_id or self._UNKEYED
        raw, sent = self._items.get(key, ("", ""))
        raw += text
        redacted = scrub(raw)
        self._items[key] = (raw, redacted if redacted.startswith(sent) else sent)
        if not redacted.startswith(sent):
            return ""
        return redacted[len(sent) :]

    def flush(self, item_id: str, scrub: Callable[[str], str]) -> str:
        """Release whatever redacted text this item has not yet emitted."""
        key = item_id or self._UNKEYED
        raw, sent = self._items.pop(key, ("", ""))
        redacted = scrub(raw)
        if redacted.startswith(sent):
            return redacted[len(sent) :]
        # The redaction diverged from what was already sent: the only safe whole
        # value is the fully redacted text. A cosmetic repeat beats a leak.
        return redacted

    def flush_all(self, scrub: Callable[[str], str]) -> str:
        """Release every outstanding item, for turn-level terminal events."""
        return "".join(self.flush(key, scrub) for key in list(self._items))


@dataclass(frozen=True, slots=True)
class NormalizationContext:
    """The per-turn seams normalization needs, bundled so the signature stays small.

    `delta_buffer` carries state across frames, which is why a context OBJECT exists
    at all: streamed redaction cannot be decided from one frame in isolation. Its
    lifetime is one turn -- the caller builds a context per turn, so no held text can
    survive into a turn that never produced it.
    """

    workspace_root: Path | None
    secrets: Sequence[str | None] = ()
    delta_buffer: _DeltaBuffer = field(default_factory=_DeltaBuffer)


def normalize_notification(
    frame: dict[str, Any],
    *,
    context: NormalizationContext,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Translate one provider notification into zero or more Studio events.

    Zero is a normal, and frequently correct, answer: most of the provider's 70
    notifications carry no state Studio renders. Yielding `(type, payload)` rather than
    a `StudioEvent` keeps this module free of sequence assignment, which belongs to
    `ThreadEvents.append`.
    """
    method = frame.get("method")
    if not isinstance(method, str):
        return
    params = frame.get("params")
    if not isinstance(params, dict):
        # A notification whose params are absent or null carries no state to render.
        return

    scrub = _text_scrubber(context)

    # Streamed message text is redacted CUMULATIVELY by the buffer, which is the only
    # way a credential split across frames is caught. It arrives here already clean,
    # so it bypasses the per-payload scrub rather than being redacted twice.
    for event_type, payload in _streamed_text(
        method, params, context.delta_buffer, scrub
    ):
        yield event_type, payload

    if method == "item/agentMessage/delta":
        return

    for event_type, payload in _map_notification(method, params):
        yield event_type, _scrubbed(payload, context.workspace_root, context.secrets)


def _text_scrubber(context: NormalizationContext) -> Callable[[str], str]:
    """Redact a bare string with the same rules the payload scrub applies."""

    def scrub(text: str) -> str:
        cleaned = _scrubbed(
            {"text": text}, context.workspace_root, context.secrets
        ).get("text")
        return cleaned if isinstance(cleaned, str) else ""

    return scrub


def _streamed_text(
    method: str,
    params: dict[str, Any],
    buffer: _DeltaBuffer,
    scrub: Callable[[str], str],
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Cumulative-redaction output for a delta, or a terminal event's remainder."""
    if method == "item/agentMessage/delta":
        delta = params.get("delta")
        if not isinstance(delta, str) or not delta:
            return
        safe = buffer.push(str(params.get("itemId", "")), delta, scrub)
        if safe:
            yield "agent_message", {"text": safe, "streaming": True}
        return

    # Terminal paths MUST release text the cumulative redaction has not yet emitted,
    # or the analyst's answer is silently truncated. `item/completed` for an
    # agentMessage is deliberately silent about the ASSEMBLED text (the deltas already
    # streamed it), so this emits only the outstanding remainder -- never a duplicate.
    yield from _terminal_flush(method, params, buffer, scrub)


def _terminal_flush(
    method: str,
    params: dict[str, Any],
    buffer: _DeltaBuffer,
    scrub: Callable[[str], str],
) -> _Events:
    """The not-yet-emitted remainder, released by whichever terminal event arrived."""
    if method == "item/completed":
        item = params.get("item")
        item_id = str(item.get("id", "")) if isinstance(item, dict) else ""
        remainder = buffer.flush(item_id, scrub)
    elif method in {"turn/completed", "error"}:
        remainder = buffer.flush_all(scrub)
    else:
        return ()
    if not remainder:
        return ()
    return (("agent_message", {"text": remainder, "streaming": True}),)


def _scrubbed(
    payload: dict[str, Any],
    workspace_root: Path | None,
    secrets: Sequence[str | None],
) -> dict[str, Any]:
    """Redact on the way OUT of this module, so no caller can forget to.

    `workspace_root` is passed through because it is what gates path relativization --
    omitting it was the exact defect that disabled FR-026 redaction for every event in
    an earlier revision of the event store.
    """
    scrubbed = scrub_payload(payload, secrets=secrets, workspace_root=workspace_root)
    return scrubbed if isinstance(scrubbed, dict) else {}


def _thread_started(params: dict[str, Any]) -> _Events:
    """The Studio thread id already rides the event envelope.

    The bridge contract requires provider identifiers to stay internal, so the raw
    Codex thread id is deliberately NOT copied into a browser-bound payload.
    """
    del params
    return (("thread_started", {}),)


def _turn_started(params: dict[str, Any]) -> _Events:
    del params
    return (("turn_started", {}),)


def _turn_completed(params: dict[str, Any]) -> _Events:
    return (_terminal_for(params),)


def _agent_message_delta(params: dict[str, Any]) -> _Events:
    delta = params.get("delta")
    if isinstance(delta, str) and delta:
        return (("agent_message", {"text": delta, "streaming": True}),)
    return ()


def _plan_updated(params: dict[str, Any]) -> _Events:
    return (("plan_updated", {"steps": _public_plan_steps(params)}),)


def _turn_error(params: dict[str, Any]) -> _Events:
    error = params.get("error") or {}
    return (
        (
            "turn_failed",
            {
                "category": "provider_error",
                "detail": error.get("message", "the provider reported an error"),
                "will_retry": bool(params.get("willRetry")),
            },
        ),
    )


def _item_started(params: dict[str, Any]) -> _Events:
    return tuple(_map_item("item/started", params))


def _item_completed(params: dict[str, Any]) -> _Events:
    return tuple(_map_item("item/completed", params))


#: The allowlist, as data. A method absent from this table produces NOTHING -- which
#: is why it is a dict rather than an if-chain ending in an else: there is no branch
#: for "anything else", so a passthrough cannot be introduced by accident.
_NOTIFICATION_MAP: dict[str, Callable[[dict[str, Any]], _Events]] = {
    "thread/started": _thread_started,
    "turn/started": _turn_started,
    "turn/completed": _turn_completed,
    "item/agentMessage/delta": _agent_message_delta,
    "item/started": _item_started,
    "item/completed": _item_completed,
    "turn/plan/updated": _plan_updated,
    "error": _turn_error,
}


def _map_notification(
    method: str, params: dict[str, Any]
) -> Iterator[tuple[str, dict[str, Any]]]:
    handler = _NOTIFICATION_MAP.get(method)
    if handler is None:
        UNMAPPED_METHODS.add(method)
        return
    yield from handler(params)


def _terminal_for(params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """A terminal notification with no readable status is a protocol defect.

    Defaulting it to `completed` would turn a malformed frame into a successful
    turn, so an interrupted or invalid response would render as a finished answer.
    """
    turn = params.get("turn") or {}
    status = turn.get("status")
    if not isinstance(status, str) or status not in _TERMINAL_STATUS:
        return (
            "turn_failed",
            {
                "category": "protocol_error",
                "detail": (
                    "the provider ended the turn without a readable status; the "
                    "result cannot be reported as successful"
                ),
            },
        )
    event_type = _TERMINAL_STATUS.get(status, "turn_failed")
    if event_type == "turn_completed":
        return event_type, {"outcome": "answered"}
    error = turn.get("error") or {}
    return event_type, {
        "category": status,
        "detail": error.get("message", f"the turn ended as {status}"),
    }


def _map_item(
    method: str, params: dict[str, Any]
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Render only the public subset of a thread item.

    An item type absent from `_RENDERED_ITEM_TYPES` yields nothing at all -- notably
    `reasoning`, whose `content` is chain-of-thought.
    """
    item = params.get("item")
    if not isinstance(item, dict):
        return
    item_type = item.get("type")
    if item_type not in _RENDERED_ITEM_TYPES:
        return

    if item_type == "agentMessage":
        # Deliberately silent on `item/completed`. The deltas already streamed this
        # text, and the browser renders every `agent_message` as its own row rather
        # than coalescing on item id -- so emitting the assembled message here shows
        # the analyst the fragments followed by a duplicate full answer.
        return

    if item_type == "plan":
        yield "plan_updated", {"steps": _plan_steps_from_text(item.get("text", ""))}
        return

    if item_type == "fileChange":
        # Emitted on `item/started` only: one proposal per item, not two. A second
        # event on completion would ask the analyst to review the same change twice.
        if method == "item/started":
            yield _file_change_event(item)
        return

    if item_type in _TOOL_ITEM_TYPES:
        yield _tool_event(method, item_type, item)


def _file_change_event(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Write intent, in the shape the read-only guard and the browser both expect."""
    changes = item.get("changes") or ()
    paths = [
        str(change.get("path", ""))
        for change in changes
        if isinstance(change, dict) and change.get("path")
    ]
    return (
        "file_change_proposed",
        {
            "paths": paths,
            "summary": (
                f"{len(paths)} file change{'s' if len(paths) != 1 else ''} proposed"
            ),
            "diff_available": bool(paths),
        },
    )


def _tool_event(
    method: str, item_type: str, item: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    label = _public_tool_label(item_type, item)
    if method == "item/started":
        return "tool_started", {"name": item_type, "public_label": label}
    return (
        "tool_completed",
        {
            "name": item_type,
            "public_label": label,
            "outcome": _tool_outcome(item),
        },
    )


def _public_tool_label(item_type: str, item: dict[str, Any]) -> str:
    """A human label that names the action without echoing raw provider detail."""
    if item_type == "commandExecution":
        command = str(item.get("command", "")).strip()
        head = command.split()[0] if command else "command"
        return f"Running {head}"
    if item_type == "fileChange":
        count = len(item.get("changes") or ())
        return f"Preparing {count} file change{'s' if count != 1 else ''}"
    return "Calling a tool"


def _tool_outcome(item: dict[str, Any]) -> str:
    status = item.get("status")
    if status in {"completed", "success"}:
        return "ok"
    if status in {"failed", "error"}:
        return "failed"
    return str(status or "unknown")


def _plan_steps_from_text(text: str) -> list[dict[str, str]]:
    """Plan items arrive as free text; render each non-empty line as a public step."""
    return [
        {"label": line.strip(), "state": "pending"}
        for line in text.splitlines()
        if line.strip()
    ]


def _public_plan_steps(params: dict[str, Any]) -> list[dict[str, str]]:
    steps: list[dict[str, str]] = []
    for entry in params.get("plan") or ():
        if isinstance(entry, dict):
            label = entry.get("step") or entry.get("label") or ""
            if label:
                steps.append(
                    {"label": str(label), "state": str(entry.get("status", "pending"))}
                )
    return steps
