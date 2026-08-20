"""Spec 149 / #660 -- JSON-RPC framing for Microsoft's Power BI modeling MCP.

This module is deliberately PURE, following ``studio/codex_protocol.py``: it turns
dicts into bytes and bytes into dicts. It starts no process and performs no I/O, so
every rule here is testable without npx or a tenant.

Three decisions carry the weight:

**Framing is newline-delimited JSON.** Measured against the real server, not
assumed: it does NOT use LSP ``Content-Length`` headers. Getting this wrong
produces a server that simply never replies, which reads like "no tools".

**Malformed input raises.** A frame that cannot be parsed is never skipped:
dropping it silently would let a write appear to proceed while its result
vanished -- a fail-open dressed as resilience.

**``readOnlyHint`` absent is ``None``, never ``False``.** The vendor self-declares
whether a call mutated model state. Absent means UNKNOWN, and collapsing unknown
into "write" or "read" invents a governance fact nobody computed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

__all__ = [
    "MAX_FRAME_BYTES",
    "PROTOCOL_VERSION",
    "McpFrameError",
    "ToolOutcome",
    "decode_frame",
    "encode_frame",
    "initialize_request",
    "initialized_notification",
    "parse_tool_result",
    "tool_call_request",
]

#: Declared to the server at handshake. Probed value, 2026-08-20.
PROTOCOL_VERSION = "2025-06-18"

#: Ceiling on ONE frame. Vendor output is untrusted: a misbehaving server that
#: never emits a newline would otherwise grow the buffer until we exhaust memory.
MAX_FRAME_BYTES = 1_000_000

_JSONRPC = "2.0"


class McpFrameError(ValueError):
    """A vendor frame violated the JSON-RPC envelope."""


def encode_frame(obj: dict[str, Any]) -> bytes:
    """One outbound frame: compact JSON plus the terminating newline."""
    return (json.dumps(obj) + "\n").encode("utf-8")


def decode_frame(line: bytes) -> dict[str, Any]:
    """One inbound frame. Raises rather than returning a sentinel."""
    if len(line) > MAX_FRAME_BYTES:
        raise McpFrameError(f"frame exceeds {MAX_FRAME_BYTES} bytes")
    text = line.decode("utf-8", errors="replace").strip()
    if not text:
        raise McpFrameError("empty frame")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise McpFrameError(f"unparseable frame: {exc}") from exc
    if not isinstance(parsed, dict):
        raise McpFrameError("frame is not a JSON object")
    return parsed


def initialize_request(request_id: int) -> dict[str, Any]:
    """The handshake opener."""
    return {
        "jsonrpc": _JSONRPC,
        "id": request_id,
        "method": "initialize",
        "params": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "seshat-bi", "version": "1"},
        },
    }


def initialized_notification() -> dict[str, Any]:
    """A NOTIFICATION: no ``id``, so the server sends no reply."""
    return {"jsonrpc": _JSONRPC, "method": "notifications/initialized", "params": {}}


def tool_call_request(
    request_id: int, tool: str, request: dict[str, Any]
) -> dict[str, Any]:
    """Every vendor tool takes exactly one nested ``request`` object."""
    return {
        "jsonrpc": _JSONRPC,
        "id": request_id,
        "method": "tools/call",
        "params": {"name": tool, "arguments": {"request": request}},
    }


@dataclass(frozen=True)
class ToolOutcome:
    """One ``tools/call`` result, already unwrapped from its double encoding."""

    ok: bool
    read_only_hint: bool | None
    payload: dict[str, Any] | None
    raw_text: str
    error: str | None = None


def _extract_text(result: dict[str, Any]) -> str:
    content = result.get("content")
    if isinstance(content, list) and content and isinstance(content[0], dict):
        return str(content[0].get("text") or "")
    return ""


def _extract_hint(result: dict[str, Any]) -> bool | None:
    meta = result.get("_meta")
    if not isinstance(meta, dict):
        return None
    annotations = meta.get("annotations")
    if not isinstance(annotations, dict):
        return None
    hint = annotations.get("readOnlyHint")
    return hint if isinstance(hint, bool) else None


def parse_tool_result(frame: dict[str, Any]) -> ToolOutcome:
    """Unwrap a tools/call reply.

    Two independent failure channels, and BOTH must be honoured: a JSON-RPC
    ``error`` member, and a successful envelope carrying ``isError: true``.
    Checking only the envelope reports a refused mutation as a success.
    """
    if "error" in frame:
        err = frame["error"]
        message = err.get("message") if isinstance(err, dict) else str(err)
        return ToolOutcome(
            ok=False, read_only_hint=None, payload=None, raw_text="", error=str(message)
        )

    result = frame.get("result")
    if not isinstance(result, dict):
        return ToolOutcome(
            ok=False,
            read_only_hint=None,
            payload=None,
            raw_text="",
            error="reply carried no result object",
        )

    raw_text = _extract_text(result)
    payload: dict[str, Any] | None = None
    if raw_text:
        try:
            decoded = json.loads(raw_text)
            payload = decoded if isinstance(decoded, dict) else None
        except json.JSONDecodeError:
            payload = None

    is_error = bool(result.get("isError"))
    return ToolOutcome(
        ok=not is_error,
        read_only_hint=_extract_hint(result),
        payload=payload,
        raw_text=raw_text,
        error="the vendor reported isError" if is_error else None,
    )
