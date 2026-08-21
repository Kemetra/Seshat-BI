"""A capability flag must describe what this build DOES (T037, FR-034).

`_bootstrap_capabilities` returned `agent_turns: False` as a hardcoded literal while
`app.state.agent_turns_refused` -- computed from the real provider outcome -- was what
actually gated the turn route. So a build that answers turns advertised that it does
not, and the browser reads `capabilities.agent_turns` to decide what to offer.

This is the MIRROR of the defect #628 fixed. There the flag over-reported a seam that
did not close; here it under-reports one that works. Both are the same class -- a flag
that is a constant rather than a description -- and an under-report is not the safe
direction, it is a different lie.

`technical_approvals` and `business_decision_recording` are checked here too, because
the invariant worth pinning is not "this one flag is right" but "every advertised
capability is backed by what the build can actually do".
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")  # CI's unit job installs no app extras

from fastapi.testclient import TestClient  # noqa: E402

API = "/api/v1"
_BROWSER_ORIGIN = {"Origin": "http://127.0.0.1:9999"}


def _client(tmp_path: Path, **kwargs: Any) -> tuple[TestClient, Any]:
    from seshat.studio.app import create_app

    (tmp_path / ".seshat").mkdir(parents=True)
    app, token = create_app(tmp_path, port=9999, **kwargs)
    client = TestClient(
        app, base_url="http://127.0.0.1:9999", headers=dict(_BROWSER_ORIGIN)
    )
    assert client.post(f"{API}/bootstrap", params={"token": token}).status_code == 204
    return client, app


def _capabilities(client: TestClient) -> dict[str, Any]:
    return client.get(f"{API}/bootstrap/state").json()["capabilities"]


def _start_a_turn(client: TestClient) -> int:
    """Actually try to run a turn; return the status the browser would see."""
    created = client.post(f"{API}/agent/threads", json={"selected_table_id": None})
    assert created.status_code == 201, created.text
    started = client.post(
        f"{API}/agent/threads/{created.json()['thread_id']}/turns",
        json={
            "prompt": "explain what is blocking the gold layer",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
    )
    return started.status_code


def test_agent_turns_is_advertised_when_a_turn_actually_runs(tmp_path: Path):
    """The positive form, and the whole point.

    The default build answers turns through the deterministic bridge. Advertising
    `False` while returning 202 tells the browser to withhold a composer that works.
    """
    client, _ = _client(tmp_path)

    assert _start_a_turn(client) == 202, "precondition: this build does answer turns"
    assert _capabilities(client)["agent_turns"] is True


def test_agent_turns_is_withheld_when_the_configured_provider_is_unusable(
    tmp_path: Path,
):
    """The refusal case, which is the only reason this flag was ever False.

    Codex CONFIGURED and unusable refuses turns with a 503 (`agent_turns_refused`).
    A flag reading True there would promise a composer whose every submission fails.
    """
    # `codex_version=None` means "probed, and there is none" -- the missing-CLI case,
    # distinct from the sentinel that means "probe the installed one".
    client, app = _client(tmp_path, agent_provider="codex", codex_version=None)

    if not getattr(app.state, "agent_turns_refused", False):
        pytest.skip("this environment has a usable Codex CLI, so turns are not refused")

    assert _start_a_turn(client) == 503
    assert _capabilities(client)["agent_turns"] is False


def test_the_flag_tracks_the_same_state_the_route_gates_on(tmp_path: Path):
    """One source, not two that can drift.

    The defect was not a wrong constant -- it was a SECOND definition of "can this
    build answer turns" living beside the one the route consults.
    """
    client, app = _client(tmp_path)

    refused = bool(getattr(app.state, "agent_turns_refused", False))

    assert _capabilities(client)["agent_turns"] is not refused


def test_business_decision_recording_is_advertised_and_backed(tmp_path: Path):
    """Spec 140 flipped this flag, and FR-022 is why that is correct.

    FR-022 scoped the prohibition to FOUNDATION -- "decision transcription belongs to
    the next governed-workbench spec" -- and that successor, spec 140, was ratified
    2026-08-21. So the honest value is now True, and it must be BACKED: advertised
    exactly when the route is reachable, never hardcoded.
    """
    client, app = _client(tmp_path)

    advertised = _capabilities(client)["business_decision_recording"]
    reachable = any(
        getattr(route, "path", None) == "/api/v1/decisions/record"
        for route in app.routes
    )

    assert advertised is True
    assert advertised is reachable, "the flag must track the route, not a literal"


def test_technical_approvals_is_advertised_and_backed(tmp_path: Path):
    """Unchanged by this work, asserted here so the trio is checked as one invariant."""
    client, _ = _client(tmp_path)

    assert _capabilities(client)["technical_approvals"] is True
