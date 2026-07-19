"""The fresh-workspace next-action guidance names `scaffold-source` (#339)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_fresh_next_action_mentions_scaffold_source() -> None:
    from seshat.agent_next import _FRESH_NEXT_ACTION

    assert "scaffold-source" in _FRESH_NEXT_ACTION
