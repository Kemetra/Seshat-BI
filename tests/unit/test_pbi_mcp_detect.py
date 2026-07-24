"""Detection permutations for the pbi-mcp doctor (#450 slice 2).

Everything runs against ``tmp_path`` with an injectable ``which`` -- no PATH
dependence, no network, no MCP runtime, no git.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.pbi_mcp.detect import (
    ABSENT,
    APPROVAL_ABSENT,
    APPROVAL_RECORDED,
    CONFIG_ABSENT,
    CONFIG_FORBIDDEN_FLAG,
    CONFIG_READ_ONLY,
    CONFIG_UNPARSEABLE,
    CONFIG_WRITE_MODE,
    PRESENT,
    READINESS_MISSING,
    READINESS_NOT_PASS,
    READINESS_PASS,
    classify_mcp_config,
    detect_facts,
    read_semantic_readiness,
)

pytestmark = pytest.mark.unit

_NO_NODE = lambda name: None  # noqa: E731
_WITH_NODE = lambda name: "/fake/bin/node"  # noqa: E731


def _write_mcp_json(root: Path, args: list[str]) -> None:
    (root / ".mcp.json").write_text(
        json.dumps(
            {"mcpServers": {"powerbi-modeling": {"command": "x", "args": args}}}
        ),
        encoding="utf-8",
    )


def _write_readiness(root: Path, table: str, status: str, approve: bool) -> None:
    record = root / "mappings" / table / "readiness-status.yaml"
    record.parent.mkdir(parents=True, exist_ok=True)
    approvals = (
        '\napprovals:\n  - stage: "publish_ready"\n    owner: "A Person (owner)"\n'
        '    at: "2026-07-24"\n'
        if approve
        else "\napprovals: []\n"
    )
    record.write_text(
        f'stages:\n  semantic_model_ready:\n    status: "{status}"\n{approvals}',
        encoding="utf-8",
    )


# --------------------------------------------------------------------------- #
# runtime + project detection
# --------------------------------------------------------------------------- #


def test_no_node_no_vendored_no_config_no_pbip(tmp_path: Path) -> None:
    facts = detect_facts(tmp_path, which=_NO_NODE)
    assert facts.node_runtime == ABSENT
    assert facts.vendored_runtime == ABSENT
    assert facts.mcp_config == CONFIG_ABSENT
    assert facts.pbip_project == ABSENT
    assert facts.semantic_model_ready == READINESS_MISSING


def test_node_and_vendored_and_pbip_detected(tmp_path: Path) -> None:
    (tmp_path / "tools" / "powerbi-modeling-mcp").mkdir(parents=True)
    (tmp_path / "powerbi" / "Demo.SemanticModel").mkdir(parents=True)
    facts = detect_facts(tmp_path, which=_WITH_NODE)
    assert facts.node_runtime == PRESENT
    assert facts.vendored_runtime == PRESENT
    assert facts.pbip_project == PRESENT


def test_pbip_pointer_file_detected(tmp_path: Path) -> None:
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "Demo.pbip").write_text("{}", encoding="utf-8")
    facts = detect_facts(tmp_path, which=_NO_NODE)
    assert facts.pbip_project == PRESENT


# --------------------------------------------------------------------------- #
# .mcp.json classification
# --------------------------------------------------------------------------- #


def test_config_read_only(tmp_path: Path) -> None:
    _write_mcp_json(tmp_path, ["--readonly", "--compatibility=powerbi"])
    assert classify_mcp_config(tmp_path / ".mcp.json") == CONFIG_READ_ONLY


@pytest.mark.parametrize("flag", ["--readwrite", "--read-write"])
def test_config_write_mode_explicit(tmp_path: Path, flag: str) -> None:
    _write_mcp_json(tmp_path, [flag])
    assert classify_mcp_config(tmp_path / ".mcp.json") == CONFIG_WRITE_MODE


def test_config_write_mode_when_readonly_absent(tmp_path: Path) -> None:
    # Microsoft's local server DEFAULTS to write mode: no flag == write mode.
    _write_mcp_json(tmp_path, ["--compatibility=powerbi"])
    assert classify_mcp_config(tmp_path / ".mcp.json") == CONFIG_WRITE_MODE


def test_config_forbidden_flag_wins_over_everything(tmp_path: Path) -> None:
    _write_mcp_json(tmp_path, ["--readonly", "--skipconfirmation"])
    assert classify_mcp_config(tmp_path / ".mcp.json") == CONFIG_FORBIDDEN_FLAG


def test_config_unparseable(tmp_path: Path) -> None:
    (tmp_path / ".mcp.json").write_text("{not json", encoding="utf-8")
    assert classify_mcp_config(tmp_path / ".mcp.json") == CONFIG_UNPARSEABLE


def test_unrelated_server_does_not_flip_the_verdict(tmp_path: Path) -> None:
    (tmp_path / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "docs-helper": {"command": "docs-mcp", "args": ["--write"]},
                    "powerbi-modeling": {"command": "x", "args": ["--readonly"]},
                }
            }
        ),
        encoding="utf-8",
    )
    assert classify_mcp_config(tmp_path / ".mcp.json") == CONFIG_READ_ONLY


def test_config_with_no_powerbi_server_reads_absent(tmp_path: Path) -> None:
    (tmp_path / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"docs-helper": {"command": "docs-mcp"}}}),
        encoding="utf-8",
    )
    assert classify_mcp_config(tmp_path / ".mcp.json") == CONFIG_ABSENT


# --------------------------------------------------------------------------- #
# readiness read (gate-reader style: verbatim, fail-closed)
# --------------------------------------------------------------------------- #


def test_readiness_missing_when_no_mappings(tmp_path: Path) -> None:
    status, tables, approval = read_semantic_readiness(tmp_path)
    assert status == READINESS_MISSING
    assert tables == ()
    assert approval == APPROVAL_ABSENT


def test_readiness_pass_names_the_passing_table(tmp_path: Path) -> None:
    _write_readiness(tmp_path, "orders", "pass", approve=True)
    _write_readiness(tmp_path, "sales", "not_started", approve=False)
    status, tables, approval = read_semantic_readiness(tmp_path)
    assert status == READINESS_PASS
    assert tables == ("orders",)
    assert approval == APPROVAL_RECORDED


def test_readiness_not_pass_never_inferred(tmp_path: Path) -> None:
    _write_readiness(tmp_path, "sales", "blocked", approve=False)
    status, tables, approval = read_semantic_readiness(tmp_path)
    assert status == READINESS_NOT_PASS
    assert tables == ()
    assert approval == APPROVAL_ABSENT


def test_unreadable_record_reads_not_pass_never_pass(tmp_path: Path) -> None:
    record = tmp_path / "mappings" / "sales" / "readiness-status.yaml"
    record.parent.mkdir(parents=True)
    record.write_text("stages: [broken", encoding="utf-8")
    status, tables, _ = read_semantic_readiness(tmp_path)
    assert status == READINESS_NOT_PASS
    assert tables == ()
