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


def test_decode_frame_refuses_a_bare_json_scalar():
    with pytest.raises(protocol.McpFrameError):
        protocol.decode_frame(b"42\n")


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
    assert outcome.payload is not None
    assert outcome.payload["message"] == "Found 5 measures across 1 tables"


def test_parse_tool_result_treats_is_error_true_as_failure():
    frame = {
        "jsonrpc": "2.0",
        "id": 5,
        "result": {"content": [{"type": "text", "text": "boom"}], "isError": True},
    }
    assert protocol.parse_tool_result(frame).ok is False


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


def test_parse_tool_result_survives_a_non_json_text_payload():
    """Vendor prose is not an error; it just has no structured payload."""
    frame = {
        "jsonrpc": "2.0",
        "id": 5,
        "result": {"content": [{"type": "text", "text": "plain words"}]},
    }
    outcome = protocol.parse_tool_result(frame)
    assert outcome.ok is True
    assert outcome.payload is None
    assert outcome.raw_text == "plain words"


def test_the_real_update_reply_reports_hint_false():
    """Verbatim from the write probe: update is per-call annotated as a write."""
    frame = {
        "jsonrpc": "2.0",
        "id": 12,
        "result": {
            "content": [{"type": "text", "text": "{}"}],
            "isError": False,
            "_meta": {
                "annotations": {
                    "title": "measure_operations.update",
                    "readOnlyHint": False,
                }
            },
        },
    }
    assert protocol.parse_tool_result(frame).read_only_hint is False
