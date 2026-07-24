"""Read-only preflight tests (#450 slice 4) -- all through a fake in-memory
transport; the real MCP runtime is never present and never needed."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from seshat.pbi_mcp.preflight import (
    ARTIFACT_RELPATH,
    STATUS_BLOCKED,
    STATUS_OK,
    STATUS_SKIPPED,
    SUPPORTED_PROTOCOL_VERSIONS,
    MissingRuntimeTransport,
    PreflightRequest,
    PreflightResult,
    RuntimeUnavailable,
    ServerDescription,
    render_result_json,
    run_preflight,
    write_artifact,
)

pytestmark = pytest.mark.unit

_PROTO = SUPPORTED_PROTOCOL_VERSIONS[-1]


@dataclass(frozen=True)
class FakeTransport:
    """In-memory MCP adapter: returns a canned description, counts contacts."""

    description: ServerDescription

    def describe(self) -> ServerDescription:
        return self.description


class ExplodingTransport:
    """Proves fail-closed paths never contact the server."""

    def describe(self) -> ServerDescription:
        raise AssertionError("the server was contacted on a fail-closed path")


def _server(
    tools: tuple[str, ...] = ("get_model", "list_tables"),
    protocol: str = _PROTO,
) -> ServerDescription:
    return ServerDescription(
        name="powerbi-modeling-mcp",
        version="0.0.0-preview",
        protocol_version=protocol,
        tools=tools,
    )


def _ready_repo(tmp_path: Path) -> Path:
    record = tmp_path / "mappings" / "orders" / "readiness-status.yaml"
    record.parent.mkdir(parents=True)
    record.write_text(
        'stages:\n  semantic_model_ready:\n    status: "pass"\napprovals: []\n',
        encoding="utf-8",
    )
    return tmp_path


def _table_readiness(root: Path, table: str, status: str) -> Path:
    """Record ``semantic_model_ready: <status>`` for ONE table under root."""
    record = root / "mappings" / table / "readiness-status.yaml"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(
        f'stages:\n  semantic_model_ready:\n    status: "{status}"\napprovals: []\n',
        encoding="utf-8",
    )
    return root


def _write_mcp_json(root: Path, args: list[str]) -> None:
    (root / ".mcp.json").write_text(
        json.dumps(
            {"mcpServers": {"powerbi-modeling": {"command": "x", "args": args}}}
        ),
        encoding="utf-8",
    )


def _blocker_ids(result: PreflightResult) -> set[str]:
    return {blocker.id for blocker in result.blockers}


# --------------------------------------------------------------------------- #
# capability + version + target validation
# --------------------------------------------------------------------------- #


def test_capability_match_passes(tmp_path: Path) -> None:
    result = run_preflight(
        PreflightRequest(
            _ready_repo(tmp_path),
            FakeTransport(_server()),
            required_tools=("get_model",),
            target="orders",
            target_allowlist=("orders",),
        )
    )
    assert result.status == STATUS_OK
    assert result.tools_present == ("get_model",)
    assert result.target_allowlisted is True
    assert result.blockers == ()


def test_capability_mismatch_blocks_naming_the_tool(tmp_path: Path) -> None:
    result = run_preflight(
        PreflightRequest(
            _ready_repo(tmp_path),
            FakeTransport(_server(tools=("get_model",))),
            required_tools=("get_model", "export_tmdl"),
        )
    )
    assert result.status == STATUS_BLOCKED
    assert "PBIMCP-CAP-01" in _blocker_ids(result)
    assert any("export_tmdl" in blocker.detail for blocker in result.blockers)
    assert result.tools_missing == ("export_tmdl",)


def test_empty_tool_list_blocks(tmp_path: Path) -> None:
    result = run_preflight(
        PreflightRequest(_ready_repo(tmp_path), FakeTransport(_server(tools=())))
    )
    assert result.status == STATUS_BLOCKED
    assert "PBIMCP-CAP-02" in _blocker_ids(result)


def test_unsupported_protocol_version_blocks_naming_it(tmp_path: Path) -> None:
    result = run_preflight(
        PreflightRequest(
            _ready_repo(tmp_path),
            FakeTransport(_server(protocol="1999-01-01")),
        )
    )
    assert result.status == STATUS_BLOCKED
    assert "PBIMCP-VER-01" in _blocker_ids(result)
    assert any("1999-01-01" in blocker.detail for blocker in result.blockers)
    assert any("never compatible" in blocker.detail for blocker in result.blockers)


def test_target_off_allowlist_blocks(tmp_path: Path) -> None:
    # prod-model records its OWN readiness pass, so only the allowlist can
    # block here: being ready never authorizes an unlisted target.
    root = _table_readiness(_ready_repo(tmp_path), "prod-model", "pass")
    result = run_preflight(
        PreflightRequest(
            root,
            FakeTransport(_server()),
            target="prod-model",
            target_allowlist=("orders",),
        )
    )
    assert result.status == STATUS_BLOCKED
    assert "PBIMCP-TGT-01" in _blocker_ids(result)
    assert result.target_allowlisted is False


def test_target_without_any_allowlist_blocks(tmp_path: Path) -> None:
    result = run_preflight(
        PreflightRequest(
            _ready_repo(tmp_path), FakeTransport(_server()), target="orders"
        )
    )
    assert result.status == STATUS_BLOCKED
    assert "PBIMCP-TGT-02" in _blocker_ids(result)


# --------------------------------------------------------------------------- #
# read-only enforcement + gate fail-closed (server never contacted)
# --------------------------------------------------------------------------- #


def test_write_mode_config_is_refused_before_contact(tmp_path: Path) -> None:
    root = _ready_repo(tmp_path)
    _write_mcp_json(root, ["--readwrite"])
    result = run_preflight(PreflightRequest(root, ExplodingTransport()))
    assert result.status == STATUS_BLOCKED
    assert "PBIMCP-CONF-02" in _blocker_ids(result)
    assert result.server is None


def test_skipconfirmation_anywhere_is_a_hard_refusal(tmp_path: Path) -> None:
    root = _ready_repo(tmp_path)
    _write_mcp_json(root, ["--readonly", "--skipconfirmation"])
    result = run_preflight(PreflightRequest(root, ExplodingTransport()))
    assert result.status == STATUS_BLOCKED
    assert "PBIMCP-CONF-01" in _blocker_ids(result)
    assert any("forbidden" in blocker.detail for blocker in result.blockers)


def test_gate_not_passed_blocks_naming_the_gate(tmp_path: Path) -> None:
    # No readiness record at all -> fail-closed, gate named, no contact.
    result = run_preflight(PreflightRequest(tmp_path, ExplodingTransport()))
    assert result.status == STATUS_BLOCKED
    assert "PBIMCP-GATE-01" in _blocker_ids(result)
    assert any("semantic_model_ready" in blocker.detail for blocker in result.blockers)


def test_missing_runtime_skips_gracefully(tmp_path: Path) -> None:
    result = run_preflight(
        PreflightRequest(_ready_repo(tmp_path), MissingRuntimeTransport())
    )
    assert result.status == STATUS_SKIPPED
    assert result.blockers == ()
    assert any("preflight skipped" in note for note in result.notes)


def test_shipped_transport_raises_the_graceful_signal() -> None:
    with pytest.raises(RuntimeUnavailable, match="preflight skipped"):
        MissingRuntimeTransport().describe()


# --------------------------------------------------------------------------- #
# readiness is resolved for the DECLARED TARGET, never borrowed (#477)
# --------------------------------------------------------------------------- #


def test_another_tables_pass_does_not_unblock_the_declared_target(
    tmp_path: Path,
) -> None:
    """#477: table_a passing must not arm a preflight declared for table_b.

    ExplodingTransport also proves this blocks BEFORE any contact.
    """
    root = _table_readiness(tmp_path, "table_a", "pass")
    result = run_preflight(
        PreflightRequest(
            root,
            ExplodingTransport(),
            target="table_b",
            target_allowlist=("table_b",),
            required_tools=("get_model",),
        )
    )
    assert result.status == STATUS_BLOCKED
    assert "PBIMCP-GATE-03" in _blocker_ids(result)
    assert any("table_b" in blocker.detail for blocker in result.blockers)


def test_declared_target_recording_not_pass_blocks(tmp_path: Path) -> None:
    root = _table_readiness(tmp_path, "table_b", "warning")
    result = run_preflight(
        PreflightRequest(
            root,
            ExplodingTransport(),
            target="table_b",
            target_allowlist=("table_b",),
        )
    )
    assert result.status == STATUS_BLOCKED
    assert "PBIMCP-GATE-02" in _blocker_ids(result)
    assert any("table_b" in blocker.detail for blocker in result.blockers)


def test_generated_remote_config_does_not_block_the_preflight(tmp_path: Path) -> None:
    """#477: the remote HTTP server has no --readonly arg to carry, so the
    detector must not read its absence as write mode."""
    from seshat.pbi_mcp.generate import render_mcp_template

    root = _ready_repo(tmp_path)
    (root / ".mcp.json").write_text(render_mcp_template("remote"), encoding="utf-8")
    result = run_preflight(
        PreflightRequest(
            root,
            FakeTransport(_server()),
            target="orders",
            target_allowlist=("orders",),
        )
    )
    assert result.status == STATUS_OK


def test_generated_both_config_does_not_block_the_preflight(tmp_path: Path) -> None:
    from seshat.pbi_mcp.generate import render_mcp_template

    root = _ready_repo(tmp_path)
    (root / ".mcp.json").write_text(render_mcp_template("both"), encoding="utf-8")
    result = run_preflight(
        PreflightRequest(
            root,
            FakeTransport(_server()),
            target="orders",
            target_allowlist=("orders",),
        )
    )
    assert result.status == STATUS_OK


# --------------------------------------------------------------------------- #
# an uncontacted server is never verified success (#477)
# --------------------------------------------------------------------------- #


def test_required_capabilities_cannot_be_satisfied_by_a_skip(tmp_path: Path) -> None:
    """Discovery never happened, so a demanded capability is unverified.

    The shipped CLI always constructs MissingRuntimeTransport, so without this
    a caller could demand a tool, contact nothing, and still read exit 0.
    """
    result = run_preflight(
        PreflightRequest(
            _ready_repo(tmp_path),
            MissingRuntimeTransport(),
            required_tools=("get_model",),
        )
    )
    assert result.status == STATUS_BLOCKED
    assert "PBIMCP-CAP-03" in _blocker_ids(result)
    assert result.capabilities_verified is False


def test_plain_skip_without_required_tools_stays_advisory(tmp_path: Path) -> None:
    result = run_preflight(
        PreflightRequest(_ready_repo(tmp_path), MissingRuntimeTransport())
    )
    assert result.status == STATUS_SKIPPED
    assert result.blockers == ()
    assert result.capabilities_verified is False


def test_contacted_server_with_its_tools_reports_verified(tmp_path: Path) -> None:
    result = run_preflight(
        PreflightRequest(
            _ready_repo(tmp_path),
            FakeTransport(_server()),
            required_tools=("get_model",),
            target="orders",
            target_allowlist=("orders",),
        )
    )
    assert result.status == STATUS_OK
    assert result.capabilities_verified is True


def test_rendered_json_exposes_capabilities_verified(tmp_path: Path) -> None:
    result = run_preflight(
        PreflightRequest(_ready_repo(tmp_path), MissingRuntimeTransport())
    )
    payload = json.loads(render_result_json(result, "2026-07-24T00:00:00Z"))
    assert payload["capabilities_verified"] is False
    assert payload["status"] == "skipped"


# --------------------------------------------------------------------------- #
# artifact shape: derived evidence only, no score
# --------------------------------------------------------------------------- #


def test_artifact_shape_and_write(tmp_path: Path) -> None:
    root = _ready_repo(tmp_path)
    result = run_preflight(
        PreflightRequest(
            root,
            FakeTransport(_server()),
            target="orders",
            target_allowlist=("orders",),
        )
    )
    written = write_artifact(root, result, generated_at="2026-07-24T00:00:00Z")
    assert written == root / ARTIFACT_RELPATH
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["authority"] == "derived-evidence-only"
    assert payload["readiness_effect"] == "none; named-human approval required"
    assert payload["mode"] == "read-only"
    assert payload["status"] == "ok"
    assert payload["server"]["name"] == "powerbi-modeling-mcp"
    assert payload["target"] == {"declared": "orders", "allowlisted": True}

    # No numeric-score FIELD anywhere in the artifact (hard rule #9); the
    # generated_note's prose "no score" is the contract, not a field.
    def _no_score_key(node: object) -> bool:
        if isinstance(node, dict):
            return all("score" not in key.lower() for key in node) and all(
                _no_score_key(value) for value in node.values()
            )
        if isinstance(node, list):
            return all(_no_score_key(item) for item in node)
        return True

    assert _no_score_key(payload)


def test_blocked_artifact_records_blockers_and_no_server(tmp_path: Path) -> None:
    result = run_preflight(PreflightRequest(tmp_path, ExplodingTransport()))
    text = render_result_json(result, "2026-07-24T00:00:00Z")
    payload = json.loads(text)
    assert payload["status"] == "blocked"
    assert payload["server"] is None
    assert payload["blockers"][0]["id"] == "PBIMCP-GATE-01"
    assert payload["notes"] == ["server not contacted -- blocked before discovery"]
    assert text.isascii()


def test_render_is_deterministic() -> None:
    result = PreflightResult(
        status=STATUS_SKIPPED,
        mode="read-only",
        server=None,
        tools_present=(),
        tools_missing=(),
        target=None,
        target_allowlisted=None,
        blockers=(),
        notes=("runtime not present",),
    )
    stamp = "2026-07-24T00:00:00Z"
    assert render_result_json(result, stamp) == render_result_json(result, stamp)
