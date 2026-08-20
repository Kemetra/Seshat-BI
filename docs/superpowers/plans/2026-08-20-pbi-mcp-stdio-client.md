# Power BI MCP stdio client (#660) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fictional one-shot CLI invocation in `pbi_mcp_adapter/runner.py` with a real MCP stdio JSON-RPC client, so an approved write can actually execute.

**Architecture:** Split transport from lifecycle, following the shipped
`studio/codex_protocol.py` precedent. A new PURE protocol module frames and
correlates newline-delimited JSON-RPC with no I/O; a new lifecycle module owns the
subprocess, the dedicated stdin pipe, and the timeout; `runner.py` becomes a thin
orchestrator that connects a TMDL folder and calls one authorized `(tool, operation)`
pair. The gate's single `authorized_operation` string becomes an explicit
`(tool, operation)` pair, because the vendor dispatches on both.

**Tech Stack:** Python 3.13, stdlib only (`subprocess`, `json`, `threading`), pytest.

**Spec:** `specs/149-pbi-mcp-write-adapter/spec.md` — plus the spike findings in
this plan's "Verified vendor facts" section, which CORRECT that spec. Read both.

## Verified vendor facts

Every fact below was measured on 2026-08-20 against
`@microsoft/powerbi-modeling-mcp@0.5.0-beta.12` (`serverInfo.version` `0.5.0.0`)
with Node v24.14.0 / npx 11.9.0. Do NOT re-derive these from assumption; if a test
needs the shape, copy it from here verbatim.

- **Transport is newline-delimited JSON** over stdin/stdout. NOT LSP
  `Content-Length` framing. Server logs go to **stderr** and are not protocol.
- **Handshake:** `initialize` (params `protocolVersion: "2025-06-18"`,
  `capabilities: {}`, `clientInfo`) → reply carries
  `serverInfo {name: "powerbi-modeling-mcp", version: "0.5.0.0"}` and
  `capabilities {tools: {listChanged: true}, prompts: {...}, logging: {}}`;
  then the client MUST send notification `notifications/initialized` (no `id`).
- **`--readonly` is accepted** as a launch flag. `--target` and `--operation`
  **DO NOT EXIST** — today's `build_argv` invents them. This is the root of #660.
- **21 tools**, each a dispatcher taking ONE `request` object whose `operation`
  field selects the action. The tools are: `database_operations`,
  `trace_operations`, `named_expression_operations`, `measure_operations`,
  `object_translation_operations`, `dax_query_operations`, `perspective_operations`,
  `column_operations`, `user_hierarchy_operations`, `calculation_group_operations`,
  `security_role_operations`, `table_operations`, `calendar_operations`,
  `relationship_operations`, `model_operations`, `culture_operations`,
  `function_operations`, `query_group_operations`, `transaction_operations`,
  `connection_operations`, `partition_operations`.
- **`measure_operations`** `inputSchema` requires `["request"]`; `request` properties
  are `connectionName, operation, definitions, references, filter,
  shouldCascadeDelete, renameDefinitions, moveDefinitions, tmdlExportOptions,
  options`. Its `operation` values: `Help, Create, Update, Delete, Get, List,
  Rename, Move, ExportTMDL`.
- **File-based path works with NO browser auth.** `connection_operations` with
  `{"operation":"ConnectFolder","folderPath":"<abs path to *.SemanticModel/definition>"}`
  returned `isError: false` and logged
  `ConnectionName=TMDL-<path>`, `IsWrite=False`. A follow-up
  `measure_operations {"operation":"List"}` returned
  `"Found 5 measures across 1 tables"` from the repo's real
  `powerbi/RetailStoreSales.SemanticModel`. The `[INFO] Authentication mode:
  InteractiveBrowser` stderr banner is the DEFAULT auth mode for the live path; it
  did not block the folder path.
- **Connection is stateful and named.** A write is therefore a multi-call sequence
  on ONE session. The gate must authorize the whole sequence, not one call.
- **A WRITE DOES NOT PERSIST WITHOUT AN EXPLICIT FLUSH.** Measured on a scratchpad
  copy with `--readwrite`: `ConnectFolder` → `measure_operations {"operation":
  "Update", "definitions":[{"name":"TotalSales","tableName":"gold fct_sales_rss",
  "formatString":"#,0.000"}]}` returned `isError: false`, stderr logged
  `IsWrite=True` — and **ZERO files changed on disk**. The vendor mutates an
  IN-MEMORY tabular model. Persistence requires a third call:
  `database_operations {"operation":"ExportToTmdlFolder","tmdlFolderPath":"<same
  folder>"}`, after which the `formatString: #,0.000` edit was present in
  `definition/tables/gold fct_sales_rss.tmdl`.

  **This is the single most important fact in this plan.** A two-call sequence
  reports success, leaves the bytes untouched, and `semantic-check` then validates
  UNCHANGED files and passes — certifying a write that never happened. That is the
  vacuous pass FR-013 exists to prevent, and it is exactly the seam #661 flags.

- **The flush rewrites the WHOLE model folder, not just the target's file.**
  `ExportToTmdlFolder` reported `fileCount: 11` and every one of the 11 TMDL files
  changed hash, including tables the operation never mentioned (dimension tables,
  `relationships.tmdl`, `model.tmdl`, `cultures/en-US.tmdl`). Any out-of-scope
  change detection MUST treat the whole `definition/` tree as in-scope for a write,
  or it will block every legitimate apply. Coordinate with #663.
- **`readOnlyHint` is PER-CALL, not a static tool annotation.** Same tool, two
  values: `measure_operations.list` → `true`, `measure_operations.update` →
  `false`. So the cross-check in Task 4 is sound. **But it tracks MODEL-STATE
  mutation, not disk writes**: `database_operations.exporttotmdlfolder` reported
  `readOnlyHint: true` while rewriting 11 files. Never use it as a disk-write oracle.
- **`ConnectFolder` resolves the `definition` level itself.** Passing
  `<name>.SemanticModel` yielded `ConnectionName=TMDL-<...>\.SemanticModel\definition`
  and `tablesLoaded: 6, measuresLoaded: 5`. Passing either level works; pass what
  the allowlist holds and do not synthesize a suffix.
- **Every result carries `_meta.annotations.readOnlyHint`** (a bool) and
  `isError`. `connection_operations.connectfolder` and `measure_operations.list`
  both reported `readOnlyHint: true`.
- **Result payloads are JSON-encoded strings** inside
  `result.content[0].text` — parse twice, and treat `isError: true` as failure even
  when the JSON-RPC envelope is a success.

## Global Constraints

- Python `>=3.13` (`pyproject.toml` `requires-python`); the repo interpreter is 3.13.
- **Never** call `gitutil.run_subprocess` for the runtime — research R4 excludes the
  execution runners; its short shared cap aborts legitimate long workloads.
- **Never** inherit stdin from the parent. Issue #322: an inherited stdin deadlocks
  the child when the parent itself speaks MCP over stdio. This client needs a
  dedicated `stdin=PIPE`; `DEVNULL` is no longer viable because we must write to it.
- **Redact BEFORE truncating** (#362), through BOTH layers (`evidence.redact`, then
  `scan.SECRET_PATTERNS`).
- `encoding="utf-8", errors="replace"` on any decode — Windows locale raises
  `UnicodeDecodeError` mid-run on a stray byte (#404).
- Every new module gets `pytestmark = pytest.mark.unit` — an unmarked
  `tests/unit` file is deselected by BOTH CI lanes and never runs.
- Bounded reads only: cap one frame's size and the total transcript. Vendor output
  is untrusted.
- No live vendor run in any test. Tests use a fake transport, never `npx`.
- Run `ruff check` AND `ruff format --check src tests scripts` before every commit.

---

### Task 1: Pure JSON-RPC framing and correlation

**Files:**
- Create: `src/seshat/pbi_mcp_adapter/protocol.py`
- Test: `tests/unit/test_pbi_mcp_protocol.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `encode_frame(obj: dict) -> bytes`;
  `decode_frame(line: bytes) -> dict` (raises `McpFrameError`);
  `McpFrameError(ValueError)`; `MAX_FRAME_BYTES: int = 1_000_000`;
  `initialize_request(request_id: int) -> dict`;
  `initialized_notification() -> dict`;
  `tool_call_request(request_id: int, tool: str, request: dict) -> dict`;
  `ToolOutcome` frozen dataclass with fields
  `ok: bool, read_only_hint: bool | None, payload: dict | None, raw_text: str, error: str | None`;
  `parse_tool_result(frame: dict) -> ToolOutcome`.

- [ ] **Step 1: Write the failing test**

```python
"""Spec 149 / #660 -- pure JSON-RPC framing for the vendor MCP.

Shapes here are COPIED from a live probe of
@microsoft/powerbi-modeling-mcp@0.5.0-beta.12 (2026-08-20), not invented.
"""

from __future__ import annotations

import json

import pytest

from seshat.pbi_mcp_adapter import protocol

pytestmark = pytest.mark.unit


def test_encode_frame_is_newline_delimited_json_not_content_length():
    raw = protocol.encode_frame({"jsonrpc": "2.0", "id": 1, "method": "ping"})
    assert raw.endswith(b"\n")
    assert b"Content-Length" not in raw
    assert json.loads(raw.decode("utf-8"))["method"] == "ping"


def test_decode_frame_rejects_malformed_instead_of_skipping():
    with pytest.raises(protocol.McpFrameError):
        protocol.decode_frame(b"{not json\n")


def test_decode_frame_refuses_an_oversized_frame():
    huge = b'{"a":"' + b"x" * (protocol.MAX_FRAME_BYTES + 10) + b'"}\n'
    with pytest.raises(protocol.McpFrameError):
        protocol.decode_frame(huge)


def test_initialize_request_declares_the_probed_protocol_version():
    req = protocol.initialize_request(1)
    assert req["method"] == "initialize"
    assert req["id"] == 1
    assert req["params"]["protocolVersion"] == "2025-06-18"


def test_initialized_notification_carries_no_id():
    note = protocol.initialized_notification()
    assert note["method"] == "notifications/initialized"
    assert "id" not in note


def test_tool_call_request_nests_the_request_object():
    req = protocol.tool_call_request(7, "measure_operations", {"operation": "List"})
    assert req["method"] == "tools/call"
    assert req["params"]["name"] == "measure_operations"
    assert req["params"]["arguments"] == {"request": {"operation": "List"}}


def test_parse_tool_result_reads_the_doubly_encoded_payload():
    # Verbatim shape from the live probe: JSON string inside content[0].text.
    inner = json.dumps({"message": "Found 5 measures across 1 tables"})
    frame = {
        "jsonrpc": "2.0",
        "id": 12,
        "result": {
            "content": [{"type": "text", "text": inner}],
            "isError": False,
            "_meta": {"annotations": {"readOnlyHint": True}},
        },
    }
    outcome = protocol.parse_tool_result(frame)
    assert outcome.ok is True
    assert outcome.read_only_hint is True
    assert outcome.payload["message"] == "Found 5 measures across 1 tables"


def test_parse_tool_result_treats_is_error_true_as_failure():
    frame = {
        "jsonrpc": "2.0",
        "id": 5,
        "result": {"content": [{"type": "text", "text": "boom"}], "isError": True},
    }
    outcome = protocol.parse_tool_result(frame)
    assert outcome.ok is False


def test_parse_tool_result_treats_a_jsonrpc_error_as_failure():
    frame = {"jsonrpc": "2.0", "id": 5, "error": {"code": -32601, "message": "nope"}}
    outcome = protocol.parse_tool_result(frame)
    assert outcome.ok is False
    assert "nope" in (outcome.error or "")


def test_parse_tool_result_reports_unknown_hint_as_none_not_false():
    """A missing hint must not read as 'the vendor said this is a write'."""
    frame = {
        "jsonrpc": "2.0",
        "id": 5,
        "result": {"content": [{"type": "text", "text": "{}"}], "isError": False},
    }
    assert protocol.parse_tool_result(frame).read_only_hint is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_protocol.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.pbi_mcp_adapter.protocol'`

- [ ] **Step 3: Write minimal implementation**

```python
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
whether a call mutated. Absent means UNKNOWN, and collapsing unknown into "write"
or "read" invents a governance fact nobody computed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

__all__ = [
    "MAX_FRAME_BYTES",
    "McpFrameError",
    "PROTOCOL_VERSION",
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

    content = result.get("content")
    raw_text = ""
    if isinstance(content, list) and content and isinstance(content[0], dict):
        raw_text = str(content[0].get("text") or "")

    payload: dict[str, Any] | None = None
    if raw_text:
        try:
            decoded = json.loads(raw_text)
            payload = decoded if isinstance(decoded, dict) else None
        except json.JSONDecodeError:
            payload = None

    hint = (result.get("_meta") or {}).get("annotations", {}).get("readOnlyHint")
    is_error = bool(result.get("isError"))
    return ToolOutcome(
        ok=not is_error,
        read_only_hint=hint if isinstance(hint, bool) else None,
        payload=payload,
        raw_text=raw_text,
        error="the vendor reported isError" if is_error else None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_protocol.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Lint and commit**

```bash
ruff check src/seshat/pbi_mcp_adapter/protocol.py tests/unit/test_pbi_mcp_protocol.py
ruff format --check src tests scripts
git add src/seshat/pbi_mcp_adapter/protocol.py tests/unit/test_pbi_mcp_protocol.py
git commit -m "feat: add pure JSON-RPC framing for the vendor MCP (#660)"
```

---

### Task 2: Bounded stdio session lifecycle

**Files:**
- Create: `src/seshat/pbi_mcp_adapter/session.py`
- Test: `tests/unit/test_pbi_mcp_session.py`

**Interfaces:**
- Consumes: Task 1's `protocol` module.
- Produces: `McpSession` class with
  `__init__(self, transport: Transport, *, deadline_seconds: int = 900)`,
  `handshake() -> dict` (returns `serverInfo`), `call(tool: str, request: dict) -> ToolOutcome`,
  `close() -> None`; `Transport` Protocol with
  `write(data: bytes) -> None`, `read_line() -> bytes`, `terminate() -> None`,
  `stderr_text() -> str`; `SessionError(RuntimeError)`;
  `SubprocessTransport(argv: list[str], cwd: Path, env: dict[str, str])`.

- [ ] **Step 1: Write the failing test**

```python
"""Spec 149 / #660 -- session lifecycle against a FAKE transport.

No npx, no tenant, no network. The fake replays frames captured from the real
server so the sequencing rules are pinned without a live run.
"""

from __future__ import annotations

import json

import pytest

from seshat.pbi_mcp_adapter import protocol, session

pytestmark = pytest.mark.unit


class FakeTransport:
    """Records what we wrote; replays scripted replies."""

    def __init__(self, replies: list[dict]):
        self.written: list[dict] = []
        self._replies = [protocol.encode_frame(r) for r in replies]
        self.terminated = False

    def write(self, data: bytes) -> None:
        self.written.append(json.loads(data.decode("utf-8")))

    def read_line(self) -> bytes:
        if not self._replies:
            return b""
        return self._replies.pop(0)

    def terminate(self) -> None:
        self.terminated = True

    def stderr_text(self) -> str:
        return "[INFO] Authentication mode: InteractiveBrowser"


def _init_reply(request_id: int = 1) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {"listChanged": True}},
            "serverInfo": {"name": "powerbi-modeling-mcp", "version": "0.5.0.0"},
        },
    }


def _ok_reply(request_id: int, message: str, read_only: bool = True) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [{"type": "text", "text": json.dumps({"message": message})}],
            "isError": False,
            "_meta": {"annotations": {"readOnlyHint": read_only}},
        },
    }


def test_handshake_sends_initialize_then_the_initialized_notification():
    t = FakeTransport([_init_reply()])
    s = session.McpSession(t)
    info = s.handshake()
    assert info["name"] == "powerbi-modeling-mcp"
    methods = [m.get("method") for m in t.written]
    assert methods == ["initialize", "notifications/initialized"]


def test_call_before_handshake_is_refused():
    t = FakeTransport([])
    s = session.McpSession(t)
    with pytest.raises(session.SessionError):
        s.call("measure_operations", {"operation": "List"})


def test_call_correlates_on_request_id_not_arrival_order():
    """An out-of-order reply must not resolve the wrong call."""
    t = FakeTransport(
        [_init_reply(), _ok_reply(99, "stale"), _ok_reply(2, "the real one")]
    )
    s = session.McpSession(t)
    s.handshake()
    outcome = s.call("measure_operations", {"operation": "List"})
    assert outcome.payload["message"] == "the real one"


def test_a_closed_stream_before_a_reply_raises_rather_than_hanging():
    t = FakeTransport([_init_reply()])
    s = session.McpSession(t)
    s.handshake()
    with pytest.raises(session.SessionError):
        s.call("measure_operations", {"operation": "List"})


def test_handshake_rejects_a_server_that_names_itself_differently():
    bad = _init_reply()
    bad["result"]["serverInfo"]["name"] = "not-the-vendor"
    t = FakeTransport([bad])
    s = session.McpSession(t)
    with pytest.raises(session.SessionError):
        s.handshake()


def test_close_terminates_the_transport():
    t = FakeTransport([_init_reply()])
    s = session.McpSession(t)
    s.handshake()
    s.close()
    assert t.terminated is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_session.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.pbi_mcp_adapter.session'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Spec 149 / #660 -- the bounded stdio session for the vendor MCP.

Lifecycle lives HERE, framing lives in ``protocol``. That split is the shipped
``studio/codex_protocol.py`` (pure) + T021 (lifecycle) pattern, and it is what
makes every sequencing rule testable without npx.

**The stdin constraint is inverted from the old runner, deliberately.** The
previous code used ``stdin=DEVNULL`` citing #322, where an INHERITED stdin
deadlocked a child. A stdio MCP client must write to the child's stdin, so
DEVNULL is not available -- but the #322 lesson still binds: the pipe is
DEDICATED (``stdin=PIPE``), never inherited from the parent. Those are different
things, and conflating them is what made #660 look like a safe choice.

**Correlation is by request id.** The server may interleave notifications and
log frames; resolving a call with whatever arrives next would silently cross-wire
one result onto another request.

**The server identity is checked at handshake.** ``npx`` resolves a name from a
registry; if something else answers, we refuse rather than issue writes to it.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Protocol

from seshat.pbi_mcp_adapter import protocol as proto

__all__ = [
    "EXPECTED_SERVER_NAME",
    "McpSession",
    "SessionError",
    "SubprocessTransport",
    "Transport",
]

#: The server must identify as this. Probed 2026-08-20.
EXPECTED_SERVER_NAME = "powerbi-modeling-mcp"

#: Sized for a model operation, not a git command (research R4).
DEFAULT_DEADLINE_SECONDS = 900


class SessionError(RuntimeError):
    """The session could not be established or a call could not be completed."""


class Transport(Protocol):
    """The byte-level seam. A fake implements this; no process is required."""

    def write(self, data: bytes) -> None: ...
    def read_line(self) -> bytes: ...
    def terminate(self) -> None: ...
    def stderr_text(self) -> str: ...


class McpSession:
    """One handshake-then-calls conversation with the vendor server."""

    def __init__(
        self, transport: Transport, *, deadline_seconds: int = DEFAULT_DEADLINE_SECONDS
    ) -> None:
        self._t = transport
        self._deadline = deadline_seconds
        self._next_id = 1
        self._ready = False

    def _send(self, frame: dict[str, Any]) -> None:
        self._t.write(proto.encode_frame(frame))

    def _await_id(self, request_id: int) -> dict[str, Any]:
        """Read frames until the one matching ``request_id`` arrives."""
        started = time.monotonic()
        while True:
            if time.monotonic() - started > self._deadline:
                raise SessionError(f"no reply to request {request_id} within deadline")
            line = self._t.read_line()
            if not line:
                raise SessionError(
                    f"the vendor stream closed before replying to {request_id}"
                )
            try:
                frame = proto.decode_frame(line)
            except proto.McpFrameError:
                # A log line or partial frame: skip it, keep waiting for our id.
                continue
            if frame.get("id") == request_id:
                return frame

    def handshake(self) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self._send(proto.initialize_request(request_id))
        reply = self._await_id(request_id)
        result = reply.get("result") or {}
        info = result.get("serverInfo") or {}
        if info.get("name") != EXPECTED_SERVER_NAME:
            raise SessionError(
                f"unexpected server identity: {info.get('name')!r} "
                f"(expected {EXPECTED_SERVER_NAME!r})"
            )
        # Required by the protocol: the server may reject calls until it lands.
        self._send(proto.initialized_notification())
        self._ready = True
        return dict(info)

    def call(self, tool: str, request: dict[str, Any]) -> proto.ToolOutcome:
        if not self._ready:
            raise SessionError("call() before a completed handshake")
        request_id = self._next_id
        self._next_id += 1
        self._send(proto.tool_call_request(request_id, tool, request))
        return proto.parse_tool_result(self._await_id(request_id))

    def close(self) -> None:
        self._t.terminate()


class SubprocessTransport:
    """The real transport: npx over dedicated pipes.

    ``stdin=PIPE`` is required (we speak to the child) and is NOT the #322 defect,
    which was an INHERITED stdin. The pipe here is ours alone.
    """

    def __init__(
        self, argv: list[str], cwd: Path, env: dict[str, str] | None = None
    ) -> None:
        self._proc = subprocess.Popen(  # noqa: S603 - fixed argv shape, no shell
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        self._stderr: list[bytes] = []

    def write(self, data: bytes) -> None:
        if self._proc.stdin is None:
            raise SessionError("the child has no stdin pipe")
        self._proc.stdin.write(data)
        self._proc.stdin.flush()

    def read_line(self) -> bytes:
        if self._proc.stdout is None:
            return b""
        return self._proc.stdout.readline()

    def terminate(self) -> None:
        try:
            if self._proc.stdin and not self._proc.stdin.closed:
                self._proc.stdin.close()
            self._proc.terminate()
            self._proc.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            self._proc.kill()

    def stderr_text(self) -> str:
        if self._proc.stderr is None:
            return ""
        return b"".join(self._stderr).decode("utf-8", errors="replace")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_session.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Lint and commit**

```bash
ruff check src/seshat/pbi_mcp_adapter/session.py tests/unit/test_pbi_mcp_session.py
ruff format --check src tests scripts
git add src/seshat/pbi_mcp_adapter/session.py tests/unit/test_pbi_mcp_session.py
git commit -m "feat: add the bounded MCP stdio session lifecycle (#660)"
```

---

### Task 3: Make the authorized operation a (tool, operation) pair

**Files:**
- Modify: `src/seshat/pbi_mcp_adapter/gate.py` (add to `AllowlistEntry` region ~line 385, and the `GateVerdict` construction ~line 686)
- Create: `src/seshat/pbi_mcp_adapter/vendor_ops.py`
- Test: `tests/unit/test_pbi_mcp_vendor_ops.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-2.
- Produces: `VENDOR_TOOLS: frozenset[str]` (all 21 probed names);
  `WRITE_OPERATIONS: frozenset[str]`;
  `parse_operation_id(operation_id: str) -> tuple[str, str]` raising
  `UnknownVendorOperation`; `is_write(operation: str) -> bool`;
  `UnknownVendorOperation(ValueError)`.

**Why this task exists:** the gate stores ONE `authorized_operation` string, but the
vendor dispatches on a tool AND an operation inside the request. Without an explicit
pair, an approval for `measure_operations/Update` cannot be distinguished from
`table_operations/Delete`. The allowlist format becomes `"<tool>.<operation>"`.

- [ ] **Step 1: Write the failing test**

```python
"""Spec 149 / #660 -- the vendor's (tool, operation) vocabulary.

Tool names are the 21 probed from the live server on 2026-08-20. A name absent
from that set is refused rather than forwarded: `npx` will happily start a server
that does not implement what we ask, and a typo must fail closed.
"""

from __future__ import annotations

import pytest

from seshat.pbi_mcp_adapter import vendor_ops

pytestmark = pytest.mark.unit


def test_the_probed_tool_set_is_closed_and_complete():
    assert len(vendor_ops.VENDOR_TOOLS) == 21
    assert "measure_operations" in vendor_ops.VENDOR_TOOLS
    assert "connection_operations" in vendor_ops.VENDOR_TOOLS
    # The invented names the old stub used must NOT be present.
    assert "update_measure" not in vendor_ops.VENDOR_TOOLS
    assert "list_measures" not in vendor_ops.VENDOR_TOOLS


def test_parse_operation_id_splits_a_dotted_pair():
    assert vendor_ops.parse_operation_id("measure_operations.Update") == (
        "measure_operations",
        "Update",
    )


def test_parse_operation_id_refuses_an_unknown_tool():
    with pytest.raises(vendor_ops.UnknownVendorOperation):
        vendor_ops.parse_operation_id("update_measure.Update")


def test_parse_operation_id_refuses_an_unpaired_id():
    """The pre-#660 single-token form must not silently become a tool name."""
    with pytest.raises(vendor_ops.UnknownVendorOperation):
        vendor_ops.parse_operation_id("update_measure")


def test_parse_operation_id_refuses_an_unknown_operation():
    with pytest.raises(vendor_ops.UnknownVendorOperation):
        vendor_ops.parse_operation_id("measure_operations.Obliterate")


def test_is_write_classifies_the_mutating_operations():
    assert vendor_ops.is_write("Create") is True
    assert vendor_ops.is_write("Update") is True
    assert vendor_ops.is_write("Delete") is True
    assert vendor_ops.is_write("List") is False
    assert vendor_ops.is_write("Help") is False


def test_an_unrecognised_operation_is_treated_as_a_write():
    """Fail closed: an unknown verb must never be assumed read-only."""
    assert vendor_ops.is_write("SomethingNew") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_vendor_ops.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.pbi_mcp_adapter.vendor_ops'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Spec 149 / #660 -- the vendor's closed (tool, operation) vocabulary.

The vendor exposes 21 coarse dispatcher tools, each taking a ``request`` object
whose ``operation`` field selects the action. So an authorized write is a PAIR,
not a single token, and the allowlist stores ``"<tool>.<operation>"``.

Two fail-closed rules:

* An unknown tool or operation RAISES. ``npx`` starts whatever the registry
  resolves; a typo that silently became a no-op would report success for a
  mutation that never happened.
* An unrecognised operation verb counts as a WRITE. Guessing read-only on an
  unknown verb is the fail-open direction, and this gate exists to prevent it.

**Why the connection and flush verbs sit in ``WRITE_OPERATIONS`` even though the
vendor annotates them ``readOnlyHint: true``.** Measured 2026-08-20:
``connection_operations.connectfolder`` and
``database_operations.exporttotmdlfolder`` both report ``readOnlyHint: true``, yet
the export rewrote all 11 TMDL files. The vendor's hint tracks MODEL-STATE
mutation; this vocabulary tracks "may this verb be issued without a cleared write
gate". Those are different questions, and for the gate's purpose the flush is
unambiguously a write. The two classifications are allowed to disagree; the runner
therefore applies the ``readOnlyHint`` cross-check ONLY to the authorized
operation, never to the connect or flush calls it issues itself.
"""

from __future__ import annotations

__all__ = [
    "READ_OPERATIONS",
    "UnknownVendorOperation",
    "VENDOR_TOOLS",
    "WRITE_OPERATIONS",
    "is_write",
    "parse_operation_id",
]

#: The 21 tools the server advertised via tools/list, probed 2026-08-20 against
#: @microsoft/powerbi-modeling-mcp@0.5.0-beta.12. A closed set on purpose.
VENDOR_TOOLS: frozenset[str] = frozenset(
    {
        "calculation_group_operations",
        "calendar_operations",
        "column_operations",
        "connection_operations",
        "culture_operations",
        "database_operations",
        "dax_query_operations",
        "function_operations",
        "measure_operations",
        "model_operations",
        "named_expression_operations",
        "object_translation_operations",
        "partition_operations",
        "perspective_operations",
        "query_group_operations",
        "relationship_operations",
        "security_role_operations",
        "table_operations",
        "trace_operations",
        "transaction_operations",
        "user_hierarchy_operations",
    }
)

#: Verbs that do not mutate. Everything else is treated as a write.
READ_OPERATIONS: frozenset[str] = frozenset(
    {"Help", "Get", "List", "Find", "Validate", "ExportTMDL", "GetConnection",
     "ListConnections", "ListLocalInstances", "GetStatus", "ListActive"}
)

#: The mutating verbs seen across the probed tool descriptions.
WRITE_OPERATIONS: frozenset[str] = frozenset(
    {"Create", "Update", "Delete", "Rename", "Move", "ImportFromTmdlFolder",
     "ImportFromBimFile", "DeployToFabric", "Connect", "ConnectFolder",
     "ConnectFabric", "ConnectBimFile", "Disconnect", "Begin", "Commit",
     "Rollback", "Start", "Stop", "Clear", "RefreshWithXMLA", "RefreshWithAPI"}
)


class UnknownVendorOperation(ValueError):
    """The allowlist named a tool or operation the vendor does not expose."""


def parse_operation_id(operation_id: str) -> tuple[str, str]:
    """Split ``"<tool>.<operation>"`` and validate BOTH halves.

    The pre-#660 single-token form is rejected rather than reinterpreted: it
    encoded a CLI flag that never existed, so accepting it would carry the bug
    forward under a new name.
    """
    tool, separator, operation = operation_id.partition(".")
    if not separator or not operation:
        raise UnknownVendorOperation(
            f"{operation_id!r} is not a '<tool>.<operation>' pair"
        )
    if tool not in VENDOR_TOOLS:
        raise UnknownVendorOperation(f"unknown vendor tool: {tool!r}")
    if operation not in READ_OPERATIONS and operation not in WRITE_OPERATIONS:
        raise UnknownVendorOperation(f"unknown vendor operation: {operation!r}")
    return tool, operation


def is_write(operation: str) -> bool:
    """True unless the verb is a KNOWN read. Unknown verbs fail closed."""
    return operation not in READ_OPERATIONS
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_vendor_ops.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Lint and commit**

```bash
ruff check src/seshat/pbi_mcp_adapter/vendor_ops.py tests/unit/test_pbi_mcp_vendor_ops.py
ruff format --check src tests scripts
git add src/seshat/pbi_mcp_adapter/vendor_ops.py tests/unit/test_pbi_mcp_vendor_ops.py
git commit -m "feat: model the vendor's (tool, operation) pair vocabulary (#660)"
```

---

### Task 4: Rewrite the runner onto the session

**Files:**
- Modify: `src/seshat/pbi_mcp_adapter/runner.py` (replace `build_argv` lines 97-109, `_run` 112-124, and the `invoke` body 147-221)
- Test: `tests/unit/test_pbi_mcp_runner.py` (existing — update), `tests/unit/test_pbi_mcp_argv_invariant.py` (existing — update)

**Interfaces:**
- Consumes: `session.McpSession`, `session.SubprocessTransport`, `session.SessionError`,
  `protocol.ToolOutcome`, `vendor_ops.parse_operation_id`, `vendor_ops.is_write`,
  `gate.GateVerdict`.
- Produces: `build_argv(*, read_only: bool) -> list[str]` (NOTE: no more
  `target_path`/`operation_id` params); `invoke(verdict, *, repo_root, read_only=False,
  session_factory=None) -> RunResult`; new blocker
  `BLOCKER_VENDOR_REFUSED = "PBIMCP-RUN-05"`;
  `BLOCKER_READONLY_VIOLATION = "PBIMCP-RUN-06"`;
  `BLOCKER_UNKNOWN_OPERATION = "PBIMCP-RUN-07"`;
  `BLOCKER_FLUSH_FAILED = "PBIMCP-RUN-08"`.

**The write sequence is THREE calls, not two:** `ConnectFolder` →
`<tool>/<operation>` → `database_operations/ExportToTmdlFolder`. The third is what
makes the write real; see "Verified vendor facts". A read-only operation skips it.

- [ ] **Step 1: Write the failing test**

```python
"""Spec 149 / #660 -- the runner drives a real MCP session, not a fake CLI.

The old tests asserted `--target` and `--operation` were in the argv. Those flags
DO NOT EXIST on the vendor binary (probed 2026-08-20), so those assertions pinned
a bug. They are replaced here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import protocol, runner

pytestmark = pytest.mark.unit


class RecordingSession:
    """Stands in for McpSession; records the calls the runner makes."""

    def __init__(self, outcomes: list[protocol.ToolOutcome] | None = None):
        self.calls: list[tuple[str, dict]] = []
        self.handshaken = False
        self.closed = False
        self._outcomes = outcomes or []

    def handshake(self) -> dict:
        self.handshaken = True
        return {"name": "powerbi-modeling-mcp", "version": "0.5.0.0"}

    def call(self, tool: str, request: dict) -> protocol.ToolOutcome:
        self.calls.append((tool, request))
        if self._outcomes:
            return self._outcomes.pop(0)
        return protocol.ToolOutcome(
            ok=True, read_only_hint=False, payload={"message": "ok"}, raw_text="{}"
        )

    def close(self) -> None:
        self.closed = True


def _ok(read_only: bool = False) -> protocol.ToolOutcome:
    return protocol.ToolOutcome(
        ok=True,
        read_only_hint=read_only,
        payload={"message": "done"},
        raw_text=json.dumps({"message": "done"}),
    )


def test_build_argv_no_longer_invents_target_or_operation_flags():
    argv = runner.build_argv(read_only=True)
    assert "--target" not in argv
    assert "--operation" not in argv
    assert "--readonly" in argv
    assert argv[:3] == ["npx", "--yes", runner.VENDOR_PACKAGE]


def test_a_write_connects_operates_then_FLUSHES(tmp_path, gate_verdict):
    """Three calls, in order. The flush is what makes the write real.

    Measured 2026-08-20: Update alone returns isError:false and changes ZERO
    bytes on disk. Without ExportToTmdlFolder the whole governance stack
    certifies a write that never happened.
    """
    sess = RecordingSession([_ok(read_only=True), _ok(read_only=False), _ok(read_only=True)])
    verdict = gate_verdict(
        path=str(tmp_path / "m.SemanticModel"),
        operation="measure_operations.Update",
    )
    result = runner.invoke(
        verdict, repo_root=tmp_path, session_factory=lambda **_: sess
    )
    assert sess.handshaken is True
    assert [t for t, _ in sess.calls] == [
        "connection_operations",
        "measure_operations",
        "database_operations",
    ]
    assert sess.calls[0][1]["operation"] == "ConnectFolder"
    assert sess.calls[1][1]["operation"] == "Update"
    assert sess.calls[2][1]["operation"] == "ExportToTmdlFolder"
    # The flush must target the SAME folder that was connected.
    assert sess.calls[2][1]["tmdlFolderPath"] == sess.calls[0][1]["folderPath"]
    assert result.succeeded is True
    assert sess.closed is True


def test_a_read_only_operation_does_NOT_flush(tmp_path, gate_verdict):
    """Nothing changed in memory, so exporting would rewrite 11 files for nothing."""
    sess = RecordingSession([_ok(read_only=True), _ok(read_only=True)])
    verdict = gate_verdict(operation="measure_operations.List")
    runner.invoke(verdict, repo_root=tmp_path, session_factory=lambda **_: sess)
    assert [t for t, _ in sess.calls] == ["connection_operations", "measure_operations"]


def test_a_failed_flush_is_a_blocker_and_never_reports_success(tmp_path, gate_verdict):
    """The operation succeeded in memory but did not reach disk: NOT materialized."""
    bad_flush = protocol.ToolOutcome(
        ok=False, read_only_hint=None, payload=None, raw_text="", error="export failed"
    )
    sess = RecordingSession([_ok(read_only=True), _ok(read_only=False), bad_flush])
    verdict = gate_verdict(operation="measure_operations.Update")
    result = runner.invoke(
        verdict, repo_root=tmp_path, session_factory=lambda **_: sess
    )
    assert result.succeeded is False
    assert runner.BLOCKER_FLUSH_FAILED in result.blockers
    # The in-memory mutation DID happen, so this is indeterminate, not "no write".
    assert result.mutation_attempted is True


def test_invoke_refuses_an_uncleared_gate_without_starting_a_session(tmp_path,
                                                                    gate_verdict):
    sess = RecordingSession()
    verdict = gate_verdict(cleared=False)
    result = runner.invoke(
        verdict, repo_root=tmp_path, session_factory=lambda **_: sess
    )
    assert result.mutation_attempted is False
    assert sess.handshaken is False
    assert runner.BLOCKER_GATE_NOT_CLEARED in result.blockers


def test_a_vendor_is_error_becomes_a_blocker_not_a_success(tmp_path, gate_verdict):
    failing = protocol.ToolOutcome(
        ok=False, read_only_hint=None, payload=None, raw_text="boom",
        error="the vendor reported isError",
    )
    sess = RecordingSession([_ok(read_only=True), failing])
    verdict = gate_verdict(operation="measure_operations.Update")
    result = runner.invoke(
        verdict, repo_root=tmp_path, session_factory=lambda **_: sess
    )
    assert result.succeeded is False
    assert runner.BLOCKER_VENDOR_REFUSED in result.blockers


def test_a_write_the_vendor_calls_read_only_is_a_violation(tmp_path, gate_verdict):
    """Cross-check our classification against the vendor's own annotation."""
    sess = RecordingSession([_ok(read_only=True), _ok(read_only=True)])
    verdict = gate_verdict(operation="measure_operations.Update")
    result = runner.invoke(
        verdict, repo_root=tmp_path, session_factory=lambda **_: sess
    )
    assert runner.BLOCKER_READONLY_VIOLATION in result.blockers


def test_a_failed_connect_never_issues_the_operation(tmp_path, gate_verdict):
    bad_connect = protocol.ToolOutcome(
        ok=False, read_only_hint=None, payload=None, raw_text="", error="no folder"
    )
    sess = RecordingSession([bad_connect])
    verdict = gate_verdict(operation="measure_operations.Update")
    result = runner.invoke(
        verdict, repo_root=tmp_path, session_factory=lambda **_: sess
    )
    assert [t for t, _ in sess.calls] == ["connection_operations"]
    assert result.succeeded is False


def test_an_unknown_operation_pair_is_refused_before_launch(tmp_path, gate_verdict):
    sess = RecordingSession()
    verdict = gate_verdict(operation="update_measure")  # the pre-#660 form
    result = runner.invoke(
        verdict, repo_root=tmp_path, session_factory=lambda **_: sess
    )
    assert sess.handshaken is False
    assert result.mutation_attempted is False


def test_output_is_redacted_through_both_layers(tmp_path, gate_verdict):
    leaky = protocol.ToolOutcome(
        ok=True, read_only_hint=False,
        payload=None,
        raw_text="postgresql://u:secret@host/db",
    )
    sess = RecordingSession([_ok(read_only=True), leaky])
    verdict = gate_verdict(operation="measure_operations.Update")
    result = runner.invoke(
        verdict, repo_root=tmp_path, session_factory=lambda **_: sess
    )
    assert "secret" not in result.output
```

Add this fixture to `tests/unit/test_pbi_mcp_runner.py` (or reuse
`_pbi_mcp_gate_fixtures.py` if it already exposes an equivalent — check first
and prefer the existing helper):

```python
@pytest.fixture
def gate_verdict():
    """Build a GateVerdict with sane cleared defaults."""
    from seshat.pbi_mcp_adapter import gate

    def _make(*, cleared: bool = True, path: str = "/repo/m.SemanticModel",
              operation: str = "measure_operations.Update"):
        return gate.GateVerdict(
            target_id="t1",
            authorized_operation=operation,
            authorized_path=path if cleared else None,
            stage_readable=cleared,
            state_committed=cleared,
            stage_pass=cleared,
            approval=None,
            approval_names_target=cleared,
            approval_names_operation=cleared,
            blockers=() if cleared else ("PBIMCP-GATE-01",),
        )

    return _make
```

Note: `GateVerdict` has more fields than shown at lines 151-207 — read the full
dataclass and supply every required field; `cleared` is a derived property, never
passed in. If `_pbi_mcp_gate_fixtures.py` already builds verdicts, import from
there instead of duplicating.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_runner.py -v`
Expected: FAIL — `build_argv()` still requires `target_path`/`operation_id`;
`invoke()` has no `session_factory`.

- [ ] **Step 3: Write the implementation**

Replace `build_argv`, `_run`, and the `invoke` body in `runner.py`. Keep the module
docstring's four constraints but CORRECT the stdin bullet (see Task 2's docstring
reasoning — a dedicated pipe is not an inherited one). Keep `_redact_and_tail`
unchanged.

```python
def build_argv(*, read_only: bool) -> list[str]:
    """The exact argv for one server launch.

    NOTE: there is no ``--target`` and no ``--operation``. The pre-#660 code
    invented both; the real server takes the target via a ``ConnectFolder`` tool
    call and the operation inside a ``tools/call`` request (probed 2026-08-20).
    ``--readonly`` IS real and is passed explicitly on the read-only path,
    because local stdio defaults to write-enabled.
    """
    argv = ["npx", "--yes", VENDOR_PACKAGE]
    argv.append("--readonly" if read_only else "--readwrite")
    return argv


def _default_session_factory(*, argv: list[str], cwd: Path) -> session.McpSession:
    transport = session.SubprocessTransport(
        argv, cwd, env=allowed_vendor_environment()
    )
    return session.McpSession(transport, deadline_seconds=RUN_TIMEOUT_SECONDS)


def invoke(
    verdict: GateVerdict,
    *,
    repo_root: Path,
    read_only: bool = False,
    session_factory: object = None,
) -> RunResult:
    """Execute the verdict's authorized (tool, operation) over MCP stdio.

    The target path and operation come from the VERDICT, never from parameters --
    a verdict authorizes ONE mutation and there is no parameter to substitute
    another. Unchanged from the pre-#660 contract; only the transport moved.
    """
    if not verdict.cleared:
        return RunResult(
            exit_code=1,
            output="refused: the write gate is not cleared",
            mutation_attempted=False,
            blockers=(BLOCKER_GATE_NOT_CLEARED, *verdict.blockers),
        )

    target_path = verdict.authorized_path
    operation_id = verdict.authorized_operation
    if target_path is None or not operation_id:  # pragma: no cover
        return RunResult(
            exit_code=1,
            output="refused: the verdict names no authorized target or operation",
            mutation_attempted=False,
            blockers=(BLOCKER_GATE_NOT_CLEARED,),
        )

    try:
        tool, operation = vendor_ops.parse_operation_id(operation_id)
    except vendor_ops.UnknownVendorOperation as exc:
        return RunResult(
            exit_code=1,
            output=f"refused: {exc}",
            mutation_attempted=False,
            blockers=(BLOCKER_UNKNOWN_OPERATION,),
        )

    argv = build_argv(read_only=read_only)
    refuse_if_bypass_flag(argv, context="pbi-mcp runner")

    factory = session_factory or _default_session_factory
    try:
        sess = factory(argv=argv, cwd=Path(repo_root))  # type: ignore[operator]
    except (OSError, session.SessionError):
        return RunResult(
            exit_code=1,
            output="the vendor runtime could not be launched (is npx on PATH?)",
            mutation_attempted=False,
            blockers=(BLOCKER_RUNTIME_MISSING,),
        )

    blockers: list[str] = []
    transcript: list[str] = []
    attempted = False
    try:
        sess.handshake()

        connected = sess.call(
            "connection_operations",
            {"operation": "ConnectFolder", "folderPath": str(target_path)},
        )
        transcript.append(connected.raw_text)
        if not connected.ok:
            return RunResult(
                exit_code=1,
                output=_redact_and_tail("\n".join(transcript), TAIL_CHARS),
                mutation_attempted=False,
                blockers=(BLOCKER_VENDOR_REFUSED,),
            )

        is_write = vendor_ops.is_write(operation)
        attempted = is_write
        outcome = sess.call(tool, {"operation": operation})
        transcript.append(outcome.raw_text)

        if not outcome.ok:
            blockers.append(BLOCKER_VENDOR_REFUSED)
        # Cross-check OUR classification against the vendor's own annotation.
        # Per-call, verified: update -> false, list -> true. Disagreement means
        # one of us is wrong about whether MODEL STATE changed.
        elif is_write and outcome.read_only_hint is True:
            blockers.append(BLOCKER_READONLY_VIOLATION)

        # THE FLUSH. A write mutates an in-memory model only; without this the
        # TMDL bytes are unchanged and every downstream check validates stale
        # files and passes. Verified 2026-08-20. Only on a write, and only if
        # the operation itself succeeded -- exporting after a failed operation
        # would rewrite all 11 files for no reason.
        if is_write and not blockers:
            flushed = sess.call(
                "database_operations",
                {"operation": "ExportToTmdlFolder", "tmdlFolderPath": str(target_path)},
            )
            transcript.append(flushed.raw_text)
            if not flushed.ok:
                # The in-memory mutation happened but never reached disk.
                # Indeterminate, never a success.
                blockers.append(BLOCKER_FLUSH_FAILED)
    except session.SessionError as exc:
        return RunResult(
            exit_code=TIMEOUT_EXIT_CODE,
            output=_redact_and_tail(f"{'\n'.join(transcript)}\n{exc}", TAIL_CHARS),
            mutation_attempted=attempted,
            blockers=(BLOCKER_RUNTIME_STALLED,),
        )
    finally:
        sess.close()

    return RunResult(
        exit_code=1 if blockers else 0,
        output=_redact_and_tail("\n".join(t for t in transcript if t), TAIL_CHARS),
        mutation_attempted=attempted,
        blockers=tuple(blockers),
    )
```

Add the two new blocker constants and their `BLOCKER_DETAIL` entries alongside the
existing ones (~line 53), plus `BLOCKER_UNKNOWN_OPERATION = "PBIMCP-RUN-07"`:

```python
BLOCKER_VENDOR_REFUSED = "PBIMCP-RUN-05"
BLOCKER_READONLY_VIOLATION = "PBIMCP-RUN-06"
BLOCKER_UNKNOWN_OPERATION = "PBIMCP-RUN-07"
BLOCKER_FLUSH_FAILED = "PBIMCP-RUN-08"
```

```python
    BLOCKER_VENDOR_REFUSED: (
        "the vendor reported the operation as failed; treated as indeterminate "
        "because the artifact may have been partially written"
    ),
    BLOCKER_READONLY_VIOLATION: (
        "the operation is classified as a write but the vendor annotated the "
        "result read-only; the two disagree, so no write is claimed"
    ),
    BLOCKER_UNKNOWN_OPERATION: (
        "the allowlist named a tool or operation the vendor does not expose; "
        "no invocation was attempted"
    ),
    BLOCKER_FLUSH_FAILED: (
        "the operation mutated the in-memory model but ExportToTmdlFolder failed, "
        "so the change never reached disk; indeterminate, never a success"
    ),
```

Import at the top: `from seshat.pbi_mcp_adapter import session, vendor_ops` and
`from seshat.pbi_mcp_adapter.runner_env import allowed_vendor_environment` — if
PR #668 has merged, reuse its helper; if not, pass `env=None` and leave a
`# TODO(#658)` noting the env allowlist lands with that PR. Check
`git log --oneline --all | grep 668` first.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_runner.py tests/unit/test_pbi_mcp_argv_invariant.py -v`
Expected: PASS. Any old assertion demanding `--target`/`--operation` must be
DELETED, not adapted — it pinned the #660 bug.

- [ ] **Step 5: Lint and commit**

```bash
ruff check src/seshat/pbi_mcp_adapter/runner.py tests/unit/test_pbi_mcp_runner.py
ruff format --check src tests scripts
git add src/seshat/pbi_mcp_adapter/runner.py tests/unit/test_pbi_mcp_runner.py tests/unit/test_pbi_mcp_argv_invariant.py
git commit -m "fix: drive the vendor MCP over stdio JSON-RPC instead of fake CLI flags (#660)"
```

---

### Task 5: Correct the stub fixture's invented tool names

**Files:**
- Modify: `tests/unit/_pbi_mcp_stub.py` (`STUB_TOOLS`, ~line 33)
- Test: `tests/unit/test_pbi_mcp_stub_fixture.py` (existing), `tests/unit/test_pbi_mcp_drift.py` (existing)

**Interfaces:**
- Consumes: `vendor_ops.VENDOR_TOOLS` from Task 3.
- Produces: corrected `STUB_TOOLS` derived from the real vocabulary.

**Why:** `STUB_TOOLS` currently names `list_tables`, `list_measures`,
`update_measure` — none of which the vendor exposes. Tests pass against fiction.
This is the `fixtures-must-come-from-the-real-producer` defect, third recurrence.

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_pbi_mcp_stub_fixture.py`:

```python
def test_stub_tools_are_all_real_vendor_tools():
    """A stub naming tools the vendor does not expose proves nothing."""
    from seshat.pbi_mcp_adapter import vendor_ops

    from tests.unit import _pbi_mcp_stub

    unknown = set(_pbi_mcp_stub.STUB_TOOLS) - vendor_ops.VENDOR_TOOLS
    assert unknown == set(), f"stub names non-existent vendor tools: {unknown}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_stub_fixture.py -v`
Expected: FAIL — `stub names non-existent vendor tools: {'list_tables', 'list_measures', 'update_measure'}`

- [ ] **Step 3: Write minimal implementation**

In `tests/unit/_pbi_mcp_stub.py`, replace the invented names and record why:

```python
# The tools the REAL server advertises (probed 2026-08-20). The previous values
# -- list_tables / list_measures / update_measure -- do not exist on the vendor
# binary at all, so every test asserting against them proved only that the code
# agreed with an invention. Derived from the shipped vocabulary so a vendor
# change breaks this loudly.
STUB_TOOLS: tuple[str, ...] = (
    "connection_operations",
    "measure_operations",
    "table_operations",
)
```

Then update `STUB_SERVER_VERSION` to `"0.5.0.0"` if any drift test asserts a
version shape, and fix whatever those tests expect. Run the full pbi_mcp suite —
`test_pbi_mcp_drift.py` perturbs one field at a time and will surface anything
keyed to the old names.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/ -k pbi_mcp -v`
Expected: PASS across the whole pbi_mcp suite.

- [ ] **Step 5: Lint and commit**

```bash
ruff check tests/unit/_pbi_mcp_stub.py
ruff format --check src tests scripts
git add tests/unit/_pbi_mcp_stub.py tests/unit/test_pbi_mcp_stub_fixture.py
git commit -m "fix: derive the MCP stub's tool names from the real vendor surface (#660)"
```

---

### Task 6: Correct the spec, allowlist format, and docs

**Files:**
- Modify: `specs/149-pbi-mcp-write-adapter/spec.md` (the FR describing invocation)
- Modify: `specs/149-pbi-mcp-write-adapter/research.md` (add an R-entry for the probe)
- Modify: `templates/pbi-mcp-adapter-contract.md` (operation id format)
- Modify: `CLAUDE.md` and `AGENTS.md` (the SPECKIT block — it still says "no implementation code exists yet")

**Interfaces:**
- Consumes: everything above.
- Produces: no code.

- [ ] **Step 1: Record the probe as a research finding**

Append to `research.md` a new entry (follow the existing R-number sequence) stating:
the vendor is an MCP stdio server, not a CLI; `--target`/`--operation` do not exist;
21 dispatcher tools; `ConnectFolder` gives the file-based path with no browser auth;
`_meta.annotations.readOnlyHint` is a cross-check; and that `serverInfo.version`
reads `0.5.0.0` for package `0.5.0-beta.12`. Cite the date and the package version.

- [ ] **Step 2: Correct the spec's invocation requirement**

Find the FR that describes passing the target and operation to the runtime and
rewrite it to the two-call sequence. Mark the old wording as corrected by the probe
rather than deleting the history — this repo distinguishes frozen records from live
guidance.

- [ ] **Step 3: Update the allowlist operation-id format -- AS ITS OWN COMMIT**

The allowlist's `operations` entries become `"<tool>.<operation>"`. Update
`templates/pbi-mcp-adapter-contract.md` and any committed allowlist fixture.
Grep for existing values first: `grep -rn 'operations:' --include='*.yaml' . | grep -i pbi`

**Commit this separately from the docs changes.** The allowlist is a GATE INPUT,
and delegated authority excludes quietly mutating approved gate inputs. The change
is forced by vendor reality (the old single-token form encoded a CLI flag that does
not exist), so make it -- but in a commit whose message states exactly that, so the
owner can review the moved boundary on its own:

```bash
git add templates/pbi-mcp-adapter-contract.md <allowlist fixtures>
git commit -m "fix!: allowlist operations become <tool>.<operation> pairs (#660)

The pre-#660 single-token form encoded --operation, a CLI flag the vendor does
not expose. The vendor dispatches on a tool AND an operation, so an approval must
name both. This changes a gate input and is therefore called out separately."
```

- [ ] **Step 4: Fix the stale SPECKIT block**

In BOTH `CLAUDE.md` and `AGENTS.md`, replace "no implementation code exists yet"
with the current state: implementation merged (PR #659) in
`src/seshat/pbi_mcp_adapter/`; #660 fixed by this work; #657/#661/#663 open.
Nothing generates this block, so nothing else will fix it.

- [ ] **Step 5: Commit**

```bash
git add specs/149-pbi-mcp-write-adapter/ templates/pbi-mcp-adapter-contract.md CLAUDE.md AGENTS.md
git commit -m "docs: correct the spec-149 invocation model from the live vendor probe (#660)"
```

---

### Task 7: Full-suite verification and gate pre-flight

- [ ] **Step 1: Run the whole unit lane**

Run: `PYTHONPATH=src python -m pytest tests/unit -m unit -q`
Expected: no failures. Note the baseline is ~5745 passed / 0 failed; a drop in
COLLECTED count means a file lost its marker and silently left the lane.

- [ ] **Step 2: Confirm the new tests actually run in the lane**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_pbi_mcp_protocol.py tests/unit/test_pbi_mcp_session.py tests/unit/test_pbi_mcp_vendor_ops.py -m unit -q`
Expected: all three collected and passing. If any collects 0, its `pytestmark` is
missing and CI would never run it.

- [ ] **Step 3: Falsify the wiring at the consumer**

Temporarily make `vendor_ops.parse_operation_id` return `("measure_operations",
"List")` unconditionally. Re-run `test_pbi_mcp_runner.py`. At least one test MUST
fail — if all still pass, the runner is not really consuming the parser and the
tests are green against dead wiring. Revert the change.

- [ ] **Step 4: Lint the exact CI scope**

```bash
ruff check src tests scripts
ruff format --check src tests scripts
```

- [ ] **Step 5: CodeScene pre-flight**

Run the local `analyze_change_set` against the branch delta before pushing. The
gate fails at equal-to threshold, so check the value-before for any file whose
mean complexity this changes.

- [ ] **Step 6: Commit and open the PR**

Before opening, run an adversarial external review as a gate (Opus). Then:

```bash
git push -u origin fix/660-mcp-stdio-client
gh pr create --title "fix: drive the vendor Power BI MCP over stdio JSON-RPC (#660)" --body "..."
```

---

## Self-Review

**Spec coverage.** #660's stated defect (CLI invocation of a stdio server) is
Tasks 1, 2, 4. The `(tool, operation)` consequence the issue did not anticipate is
Task 3. The invented-fixture defect found while planning is Task 5. Spec and doc
correction is Task 6. Verification is Task 7. Issues #657, #661, #663 are
deliberately NOT covered — they are separate, and #661/#663 depend on this landing
first.

**Placeholders.** One conditional remains by design: Task 4 Step 3's
`allowed_vendor_environment` import depends on whether PR #668 has merged, with an
explicit check and a stated fallback. Everything else carries real code.

**Type consistency.** `ToolOutcome` fields (`ok`, `read_only_hint`, `payload`,
`raw_text`, `error`) are used identically in Tasks 1, 2, 4. `parse_operation_id`
returns `tuple[str, str]` in Task 3 and is destructured as `tool, operation` in
Task 4. `McpSession.call(tool, request)` matches the `RecordingSession` fake.
`build_argv` loses two parameters in Task 4 — the old two-positional call sites
are all inside `runner.py` and its tests, both updated in that task.

**Known risk.** No test exercises the real `SubprocessTransport` against `npx`
(deliberate: no live vendor run in tests). Its correctness rests on the two spike
probes. A follow-up smoke test behind an opt-in marker would be worth filing once
#660 lands.
