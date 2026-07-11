import asyncio
from pathlib import Path

from seshat.governor.mcp_server import create_server
from seshat.governor.service import OPERATIONS


def test_mcp_lists_exactly_six_read_only_tools(tmp_path: Path) -> None:
    server = create_server(tmp_path)
    tools = asyncio.run(server.list_tools())
    assert {tool.name for tool in tools} == set(OPERATIONS)
    for tool in tools:
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.outputSchema["type"] == "object"


def test_mcp_call_returns_structured_governor_response(tmp_path: Path) -> None:
    server = create_server(tmp_path)
    _content, result = asyncio.run(
        server.call_tool("seshat_get_status", {"workspace": str(tmp_path)})
    )
    assert result["operation"] == "seshat_get_status"
    assert result["read_only_proof"] is True


def test_mcp_error_response_contains_no_absolute_server_root(tmp_path: Path) -> None:
    server = create_server(tmp_path)
    _content, result = asyncio.run(
        server.call_tool("seshat_get_status", {"workspace": str(tmp_path.parent)})
    )
    assert result["outcome"] == "input_defect"
    assert str(tmp_path) not in str(result)
