"""CLI-level tests for `seshat pbi-mcp` -- through the wired ``_DISPATCH``
entry via ``seshat.cli.main``, mirroring ``test_pbir_validate_bindings_cli``.

The doctor's environment detection is made deterministic by pointing --repo at
a controlled tmp tree; PATH-dependent node detection only widens prerequisites
(never the surface), so assertions pin surfaces and exit codes, not the node
fact.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.unit


def _ready_repo(tmp_path: Path) -> Path:
    record = tmp_path / "mappings" / "orders" / "readiness-status.yaml"
    record.parent.mkdir(parents=True)
    record.write_text(
        'stages:\n  semantic_model_ready:\n    status: "pass"\napprovals: []\n',
        encoding="utf-8",
    )
    return tmp_path


def _write_mcp_json(root: Path, args: list[str]) -> None:
    (root / ".mcp.json").write_text(
        json.dumps(
            {"mcpServers": {"powerbi-modeling": {"command": "x", "args": args}}}
        ),
        encoding="utf-8",
    )


# --------------------------------------------------------------------------- #
# doctor
# --------------------------------------------------------------------------- #


def test_doctor_recommends_and_exits_zero(tmp_path: Path, capsys) -> None:
    root = _ready_repo(tmp_path)
    code = main(
        ["pbi-mcp", "doctor", "--repo", str(root), "--intent", "report-formatting"]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "pbir-authoring-adapter" in out
    assert "grants no approval" in out


def test_doctor_blocked_gate_exits_two_and_names_the_gate(
    tmp_path: Path, capsys
) -> None:
    code = main(
        ["pbi-mcp", "doctor", "--repo", str(tmp_path), "--intent", "model-edit"]
    )
    out = capsys.readouterr().out
    assert code == 2
    assert "blocked-on-semantic-readiness" in out
    assert "semantic_model_ready" in out


def test_doctor_write_advisory_once_then_refuses(tmp_path: Path, capsys) -> None:
    root = _ready_repo(tmp_path)
    argv = [
        "pbi-mcp",
        "doctor",
        "--repo",
        str(root),
        "--intent",
        "ci-validation",
        "--write-advisory",
    ]
    assert main(argv) == 0
    advisory = root / ".seshat" / "powerbi-mcp-recommendation.yaml"
    assert advisory.is_file()
    assert "advisory written" in capsys.readouterr().out
    assert main(argv) == 2  # write-once: the second write is refused
    assert "write-once" in capsys.readouterr().err


def test_doctor_json_output_is_parseable(tmp_path: Path, capsys) -> None:
    root = _ready_repo(tmp_path)
    code = main(
        [
            "pbi-mcp",
            "doctor",
            "--repo",
            str(root),
            "--intent",
            "published-query",
            "--json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendation"]["surface"] == "remote-powerbi-mcp"
    assert payload["detected"]["semantic_model_ready"] == "pass"


def test_doctor_unknown_intent_is_a_usage_error(tmp_path: Path) -> None:
    code = main(
        ["pbi-mcp", "doctor", "--repo", str(tmp_path), "--intent", "publish-now"]
    )
    assert code == 2  # argparse usage exit, surfaced by main


# --------------------------------------------------------------------------- #
# generate-config
# --------------------------------------------------------------------------- #


def test_generate_config_stdout_is_read_only_json(capsys) -> None:
    assert main(["pbi-mcp", "generate-config"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "--readonly" in payload["mcpServers"]["powerbi-modeling"]["args"]


def test_generate_config_out_refuses_overwrite(tmp_path: Path, capsys) -> None:
    target = tmp_path / "mcp.json"
    argv = ["pbi-mcp", "generate-config", "--out", str(target)]
    assert main(argv) == 0
    assert target.is_file()
    capsys.readouterr()
    assert main(argv) == 2
    assert "never overwrites" in capsys.readouterr().err


def test_generate_setup_doc_to_stdout(capsys) -> None:
    assert main(["pbi-mcp", "generate-config", "--setup-doc"]) == 0
    out = capsys.readouterr().out
    assert "GENERATED -- do not hand-edit" in out


# --------------------------------------------------------------------------- #
# preflight
# --------------------------------------------------------------------------- #


def test_preflight_missing_runtime_is_graceful_exit_zero(
    tmp_path: Path, capsys
) -> None:
    root = _ready_repo(tmp_path)
    code = main(["pbi-mcp", "preflight", "--repo", str(root)])
    out = capsys.readouterr().out
    assert code == 0
    assert "skipped" in out
    assert "runtime not present" in out


def test_preflight_write_mode_config_blocks_exit_two(tmp_path: Path, capsys) -> None:
    root = _ready_repo(tmp_path)
    _write_mcp_json(root, ["--read-write"])
    code = main(["pbi-mcp", "preflight", "--repo", str(root)])
    out = capsys.readouterr().out
    assert code == 2
    assert "PBIMCP-CONF-02" in out


def test_preflight_skipconfirmation_blocks_exit_two(tmp_path: Path, capsys) -> None:
    root = _ready_repo(tmp_path)
    _write_mcp_json(root, ["--readonly", "--skipconfirmation"])
    code = main(["pbi-mcp", "preflight", "--repo", str(root), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["blockers"][0]["id"] == "PBIMCP-CONF-01"


def test_preflight_write_artifact_writes_the_advisory_json(
    tmp_path: Path, capsys
) -> None:
    root = _ready_repo(tmp_path)
    code = main(["pbi-mcp", "preflight", "--repo", str(root), "--write-artifact"])
    assert code == 0
    artifact = root / ".seshat" / "powerbi-mcp-preflight.json"
    assert artifact.is_file()
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["authority"] == "derived-evidence-only"
    assert payload["status"] == "skipped"
    assert "artifact written" in capsys.readouterr().out
