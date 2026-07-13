from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.external_agent_acceptance import classify_transcript

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/public_distribution/codex"


def _load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("client", ["cli", "ide"])
def test_external_codex_clients_discover_and_invoke_skills(client: str) -> None:
    transcript = _load(f"acceptance.{client}.pass.json")
    record = classify_transcript(ROOT, transcript)
    assert record["status"] == "pass"
    assert record["client"] == client
    assert record["observed_stage"] == "source"
    assert record["human_gate_observed"] is True
    assert transcript["router_invocation"] == "$seshat-bi"
    assert str(transcript["knowledge_invocation"]).startswith("$")


def test_external_codex_rejects_undeclared_capability() -> None:
    record = classify_transcript(ROOT, _load("acceptance.capability-fail.json"))
    assert record["status"] == "fail"
    assert any("undeclared" in blocker for blocker in record["blockers"])
