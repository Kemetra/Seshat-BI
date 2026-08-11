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
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from seshat.studio.redaction import scrub_payload

__all__ = [
    "CodexFrameError",
    "CodexProtocolReader",
    "PendingRequests",
    "UNMAPPED_METHODS",
    "normalize_notification",
]


class CodexFrameError(ValueError):
    """A provider frame violated the JSON-RPC envelope, or correlation failed."""


#: JSON-RPC version every frame must declare.
_JSONRPC_VERSION = "2.0"

#: Item types Studio renders. Anything absent here is dropped, including `reasoning`.
_RENDERED_ITEM_TYPES = frozenset(
    {"agentMessage", "plan", "commandExecution", "fileChange", "mcpToolCall"}
)

#: Item types that are TOOLS for rendering purposes -- they get tool_started/completed.
_TOOL_ITEM_TYPES = frozenset({"commandExecution", "fileChange", "mcpToolCall"})

#: Provider turn statuses that end a turn, mapped to Studio's two terminal events.
_TERMINAL_STATUS = {
    "completed": "turn_completed",
    "interrupted": "turn_failed",
    "failed": "turn_failed",
}

#: Notification method names seen but deliberately not mapped. Module-level so a
#: diagnostics view can report what the provider sent without widening the event set.
UNMAPPED_METHODS: set[str] = set()


class CodexProtocolReader:
    """Reassembles newline-delimited JSON frames from arbitrary chunk boundaries.

    A pipe read returns whatever the OS had buffered, which splits mid-token as often
    as not. Holding a partial line until its newline arrives is the whole job.
    """

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, chunk: str) -> Iterator[dict[str, Any]]:
        """Yield every complete frame in `chunk`, retaining any partial tail."""
        self._buffer += chunk
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


def _check_envelope(frame: dict[str, Any]) -> None:
    """Every rule a well-formed JSON-RPC frame must satisfy, gathered in one place."""
    if frame.get("jsonrpc") != _JSONRPC_VERSION:
        raise CodexFrameError("provider frame did not declare jsonrpc 2.0")
    if "method" not in frame and "result" not in frame and "error" not in frame:
        raise CodexFrameError("provider frame is neither a call nor a reply")
    if "id" in frame and not _is_valid_request_id(frame["id"]):
        raise CodexFrameError(
            f"provider frame carried a non-scalar id: {frame['id']!r}"
        )


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


def normalize_notification(
    frame: dict[str, Any],
    *,
    workspace_root: Path | None,
    secrets: Sequence[str | None] = (),
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

    for event_type, payload in _map_notification(method, params):
        yield event_type, _scrubbed(payload, workspace_root, secrets)


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


def _map_notification(
    method: str, params: dict[str, Any]
) -> Iterator[tuple[str, dict[str, Any]]]:
    if method == "thread/started":
        thread = params.get("thread") or {}
        yield "thread_started", {"provider_thread_id": thread.get("id", "")}
        return

    if method == "turn/started":
        turn = params.get("turn") or {}
        yield "turn_started", {"provider_turn_id": turn.get("id", "")}
        return

    if method == "turn/completed":
        yield _terminal_for(params)
        return

    if method == "item/agentMessage/delta":
        delta = params.get("delta")
        if isinstance(delta, str) and delta:
            yield "agent_message", {"text": delta, "streaming": True}
        return

    if method in {"item/started", "item/completed"}:
        yield from _map_item(method, params)
        return

    if method == "turn/plan/updated":
        yield "plan_updated", {"steps": _public_plan_steps(params)}
        return

    if method == "error":
        error = params.get("error") or {}
        yield (
            "turn_failed",
            {
                "category": "provider_error",
                "detail": error.get("message", "the provider reported an error"),
                "will_retry": bool(params.get("willRetry")),
            },
        )
        return

    UNMAPPED_METHODS.add(method)


def _terminal_for(params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    turn = params.get("turn") or {}
    status = turn.get("status", "completed")
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
        if method == "item/completed":
            yield "agent_message", {"text": item.get("text", "")}
        return

    if item_type == "plan":
        yield "plan_updated", {"steps": _plan_steps_from_text(item.get("text", ""))}
        return

    if item_type in _TOOL_ITEM_TYPES:
        yield _tool_event(method, item_type, item)


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
