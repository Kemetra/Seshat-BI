"""Supply-chain guardrails for the Dagster smoke workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def test_dagster_smoke_pins_actions_and_minimizes_permissions() -> None:
    text = (ROOT / ".github/workflows/dagster-smoke.yml").read_text(encoding="utf-8")

    assert "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0" in text
    assert "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1" in text
    assert "permissions:" in text and "contents: read" in text
    assert "actions/checkout@v" not in text
    assert "actions/setup-python@v" not in text
