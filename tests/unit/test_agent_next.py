"""Tests for the agent-facing next-action document (Seshat Agent-Driven v0.1).

``retail next`` without ``--table`` (and ``--format agent``) must answer the
guarded-agent questions with STABLE keys, degrade conservatively when evidence
is missing, never fabricate readiness, and stay read-only + deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from retail.agent_next import build_agent_next_document
from retail.cli import main

pytestmark = pytest.mark.unit

REQUIRED_KEYS = (
    "current_stage",
    "readiness_state",
    "evidence",
    "blocking_reasons",
    "next_allowed_action",
    "forbidden_scope",
    "validation_commands",
    "stop_point",
)


def _write_status(tmp_path: Path, table_dir: str, body: str) -> Path:
    path = tmp_path / "mappings" / table_dir / "readiness-status.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


_MAPPING_NOT_STARTED = """\
table: "silver.orders"
current_stage: "mapping_ready"
stages:
  source_ready:
    status: "pass"
    evidence: ["mappings/orders/source-profile.md"]
  mapping_ready: {status: "not_started"}
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals: []
next_action: "Begin Mapping Ready (Stage 2) -- the source-mapping gate."
"""


def test_cli_next_without_table_emits_valid_json(tmp_path: Path, capsys) -> None:
    _write_status(tmp_path, "orders", _MAPPING_NOT_STARTED)
    exit_code = main(["next", "--repo", str(tmp_path), "--format", "json"])
    assert exit_code == 0
    parsed = json.loads(capsys.readouterr().out)  # whole stdout is ONE document
    for key in REQUIRED_KEYS:
        assert key in parsed, f"missing required key {key!r}"


def test_cli_next_agent_format_does_not_crash(tmp_path: Path, capsys) -> None:
    _write_status(tmp_path, "orders", _MAPPING_NOT_STARTED)
    exit_code = main(["next", "--repo", str(tmp_path), "--format", "agent"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "next_allowed_action:" in out
    assert "stop_point:" in out
    assert "read_only_proof: true" in out


def test_cli_next_agent_format_on_empty_repo_does_not_crash(
    tmp_path: Path, capsys
) -> None:
    exit_code = main(["next", "--repo", str(tmp_path), "--format", "agent"])
    assert exit_code == 0
    assert "next_allowed_action:" in capsys.readouterr().out


def test_fresh_repo_produces_conservative_evidence_first_action(
    tmp_path: Path,
) -> None:
    document = build_agent_next_document(tmp_path)
    assert document["current_stage"] == "source_ready"
    assert document["readiness_state"] == "not_started"
    assert document["evidence"] == []
    assert "Source Ready" in document["next_allowed_action"]
    # Every downstream gate is still closed on a fresh project.
    joined = " ".join(document["forbidden_scope"])
    assert "No silver work" in joined
    assert "No gold work" in joined
    assert "No dashboard work" in joined
    assert "No live publish" in joined


def test_missing_evidence_is_never_invented(tmp_path: Path) -> None:
    """A repo with no readiness files must not claim any stage passed."""
    document = build_agent_next_document(tmp_path)
    assert document["readiness_state"] != "pass"
    assert document["outcome"] != "terminal_pass"
    assert document["evidence"] == []
    dumped = json.dumps(document).lower()
    for banned in ("score", "confidence", "health", "maturity"):
        assert banned not in dumped


def test_gate_rule_no_silver_before_mapping_ready(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _MAPPING_NOT_STARTED)
    document = build_agent_next_document(tmp_path)
    assert document["current_stage"] == "mapping_ready"
    assert document["readiness_state"] == "not_started"
    joined = " ".join(document["forbidden_scope"])
    assert "No silver work" in joined
    # The recorded Source Ready evidence is surfaced verbatim.
    assert document["evidence"][0]["stage"] == "source_ready"
    assert document["evidence"][0]["items"] == ["mappings/orders/source-profile.md"]


def test_blocked_table_surfaces_verbatim_reasons_and_stops(tmp_path: Path) -> None:
    _write_status(
        tmp_path,
        "orders",
        """\
table: "silver.orders"
current_stage: "mapping_ready"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready:
    status: "blocked"
    blocking_reasons: ["grain not confirmed unique on data"]
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals: []
next_action: "resolve grain"
""",
    )
    document = build_agent_next_document(tmp_path)
    assert document["readiness_state"] == "blocked"
    assert document["blocking_reasons"] == ["grain not confirmed unique on data"]
    assert document["next_allowed_action"].startswith("STOP")
    assert "Stopped now" in document["stop_point"]


def test_focus_picks_earliest_stage_deterministically(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _MAPPING_NOT_STARTED)
    _write_status(
        tmp_path,
        "done_table",
        """\
table: "silver.done_table"
current_stage: "publish_ready"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "pass", evidence: ["map"]}
  silver_ready: {status: "pass", evidence: ["silver"]}
  gold_ready: {status: "pass", evidence: ["gold"]}
  semantic_model_ready: {status: "pass", evidence: ["model"]}
  dashboard_ready: {status: "pass", evidence: ["dashboard"]}
  publish_ready: {status: "pass", evidence: ["handoff"]}
approvals:
  - {stage: mapping_ready, owner: "Ada Lovelace (analyst)", at: "2026-07-01"}
  - stage: semantic_model_ready
    owner: "Grace Hopper (metric_owner)"
    at: "2026-07-01"
  - {stage: dashboard_ready, owner: "Katherine Johnson (governance)", at: "2026-07-01"}
  - {stage: publish_ready, owner: "Ahmed Shaaban (data_owner)", at: "2026-07-01"}
next_action: "done"
""",
    )
    first = build_agent_next_document(tmp_path)
    second = build_agent_next_document(tmp_path)
    assert first == second  # deterministic over the same committed state
    assert first["table"] == "silver.orders"  # earliest stage wins the focus
    assert len(first["tables"]) == 2


def test_table_argument_focuses_that_table(tmp_path: Path) -> None:
    _write_status(tmp_path, "orders", _MAPPING_NOT_STARTED)
    document = build_agent_next_document(tmp_path, "silver.orders")
    assert document["table"] == "silver.orders"
    assert document["current_stage"] == "mapping_ready"


def test_validation_commands_are_present_and_runnable_shapes(
    tmp_path: Path,
) -> None:
    document = build_agent_next_document(tmp_path)
    commands = document["validation_commands"]
    assert "python -m retail.cli check --repo ." in commands
    assert "python -m retail.cli status --repo . --format json" in commands
    assert "python -m retail.cli next --repo . --format json" in commands


def test_agent_document_is_read_only(tmp_path: Path, capsys) -> None:
    _write_status(tmp_path, "orders", _MAPPING_NOT_STARTED)
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    main(["next", "--repo", str(tmp_path), "--format", "json"])
    capsys.readouterr()
    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert before == after


def test_per_table_json_path_is_unchanged(tmp_path: Path, capsys) -> None:
    """Backward compatibility: --table with --format json still emits the
    original spec-080 response shape."""
    _write_status(tmp_path, "orders", _MAPPING_NOT_STARTED)
    exit_code = main(
        [
            "next",
            "--repo",
            str(tmp_path),
            "--table",
            "silver.orders",
            "--format",
            "json",
        ]
    )
    assert exit_code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["outcome"] == "next_action"
    assert parsed["stage"] == "mapping_ready"
    assert "next_allowed_action" not in parsed
