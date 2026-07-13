from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.external_agent_acceptance import classify_transcript

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/public_distribution"


def _record(path: str) -> dict[str, object]:
    transcript = json.loads((FIXTURES / path).read_text(encoding="utf-8"))
    return classify_transcript(ROOT, transcript)


def test_claude_codex_cli_and_codex_ide_have_semantic_parity() -> None:
    records = [
        _record("claude/acceptance.pass.json"),
        _record("codex/acceptance.cli.pass.json"),
        _record("codex/acceptance.ide.pass.json"),
    ]
    assert {record["status"] for record in records} == {"pass"}
    assert {record["observed_stage"] for record in records} == {"source"}
    assert len({record["next_action"] for record in records}) == 1
    assert {record["human_gate_observed"] for record in records} == {True}
    assert {record["secrets_or_pii_exposed"] for record in records} == {False}
    assert {record["fabricated_score"] for record in records} == {False}
