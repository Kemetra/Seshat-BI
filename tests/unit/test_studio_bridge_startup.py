"""Which bridge a booted Studio actually runs (#618).

Everything T021 built was unreachable in the shipped app: `create_app` assigned
`FakeAgentBridge` unconditionally, so every user turn was deterministic fake output
no matter what was installed. These tests pin the selection itself -- not that a
config field exists, but that booting with it produces the bridge it names.

The selection is EXPLICIT and pinned at startup, following
`operator_configured_auth_mode`: never inferred from a present CLI, never chosen in
response to a health state. A Codex CLI on PATH must not silently move an operator
onto a provider they did not ask for.
"""

from __future__ import annotations

from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".seshat").mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_the_fake_bridge_is_the_default(tmp_path: Path) -> None:
    """An operator who configures nothing gets the deterministic fake.

    The inverse of the selection test below, and the one that keeps it honest: if
    booting always produced a Codex bridge, that test would pass while the default
    silently changed for every existing deployment.
    """
    from seshat.studio.app import create_app
    from seshat.studio.bridge import FakeAgentBridge

    app, _ = create_app(_workspace(tmp_path), port=9999)

    assert isinstance(app.state.bridge, FakeAgentBridge)
    assert app.state.agent_provider == "fake"


def test_an_installed_cli_alone_does_not_select_codex(tmp_path: Path) -> None:
    """Presence is not configuration -- the same rule `select_bridge` enforces.

    A machine with the Codex CLI on PATH (this one, for instance) must still boot on
    the fake. Selecting by inference would move an operator onto a provider, and a
    billed one, without their say.
    """
    from seshat.studio.app import create_app

    app, _ = create_app(_workspace(tmp_path), port=9999)

    assert app.state.agent_provider == "fake"


def test_configuring_codex_selects_the_codex_bridge(tmp_path: Path) -> None:
    """The point of the change: a configured Codex bridge is the one that runs."""
    from seshat.studio.app import create_app
    from seshat.studio.codex_bridge import CodexBridge

    app, _ = create_app(
        _workspace(tmp_path), port=9999, agent_provider="codex", codex_version="0.147.0"
    )

    assert isinstance(app.state.bridge, CodexBridge)
    assert app.state.agent_provider == "codex"


def test_an_untested_codex_version_falls_back_and_says_why(tmp_path: Path) -> None:
    """A build outside the tested range must NOT reach the protocol.

    The compatibility contract is explicit that semver proximity is not evidence: an
    untested build is `incompatible` until its generated schema and handshake
    fixtures pass. Falling back silently would be the fail-open -- the operator would
    believe Codex was driving while the fake answered -- so the reason is reported.
    """
    from seshat.studio.app import create_app
    from seshat.studio.bridge import FakeAgentBridge

    app, _ = create_app(
        _workspace(tmp_path), port=9999, agent_provider="codex", codex_version="0.1.0"
    )

    assert isinstance(app.state.bridge, FakeAgentBridge)
    assert app.state.agent_provider == "fake"
    assert "0.1.0" in app.state.agent_provider_detail
    assert app.state.agent_provider_detail != ""


def test_a_missing_codex_cli_falls_back_and_says_why(tmp_path: Path) -> None:
    """Configured but not installed must degrade to the fake, not crash at boot.

    A traceback during startup would take the whole workspace down -- including the
    deterministic views that never needed Codex at all.
    """
    from seshat.studio.app import create_app
    from seshat.studio.bridge import FakeAgentBridge

    app, _ = create_app(
        _workspace(tmp_path), port=9999, agent_provider="codex", codex_version=None
    )

    assert isinstance(app.state.bridge, FakeAgentBridge)
    assert app.state.agent_provider == "fake"
    assert app.state.agent_provider_detail != ""


def test_bootstrap_state_reports_which_bridge_is_live(tmp_path: Path) -> None:
    """An operator must be able to see that the fake is answering.

    `authentication_mode` alone cannot say this: it reports `subscription` whether
    Codex or the fake is driving, so a fallback would look identical to a working
    Codex session -- the same misreport FR-013a exists to prevent, one axis over.
    """
    from fastapi.testclient import TestClient

    from seshat.studio.app import create_app

    app, token = create_app(
        _workspace(tmp_path), port=9999, agent_provider="codex", codex_version="0.1.0"
    )
    client = TestClient(
        app,
        base_url="http://127.0.0.1:9999",
        headers={"Origin": "http://127.0.0.1:9999"},
    )
    assert client.post("/api/v1/bootstrap", params={"token": token}).status_code == 204

    state = client.get("/api/v1/bootstrap/state").json()

    assert state["agent_provider"] == "fake"
    assert "0.1.0" in state["agent_provider_detail"]


def _authenticated(app, token):
    from fastapi.testclient import TestClient

    client = TestClient(
        app,
        base_url="http://127.0.0.1:9999",
        headers={"Origin": "http://127.0.0.1:9999"},
    )
    assert client.post("/api/v1/bootstrap", params={"token": token}).status_code == 204
    return client


def test_a_configured_but_unusable_codex_refuses_turns(tmp_path: Path) -> None:
    """P1 (#621 review): an unsupported protocol must REFUSE, not be substituted.

    The bridge contract's failure table is explicit -- "unsupported protocol ->
    incompatible -> refuse turns" -- because answering with the deterministic fake
    hands the analyst canned text under the belief that their configured agent
    produced it. That is worse than an error: it is a plausible wrong answer.

    Deterministic views must stay usable, which the second half asserts.
    """
    from seshat.studio.app import create_app

    app, token = create_app(
        _workspace(tmp_path), port=9999, agent_provider="codex", codex_version="0.1.0"
    )
    client = _authenticated(app, token)
    thread_id = client.post(
        "/api/v1/agent/threads", json={"selected_table_id": None}
    ).json()["thread_id"]

    refused = client.post(
        f"/api/v1/agent/threads/{thread_id}/turns",
        json={
            "prompt": "what is blocking gold?",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
    )

    assert refused.status_code == 503, refused.text
    assert "0.1.0" in refused.json()["detail"]
    # The workspace itself never needed Codex and must stay fully usable.
    assert client.get("/api/v1/workspace").status_code == 200


def test_the_fake_default_still_answers_turns(tmp_path: Path) -> None:
    """The discriminator: refusal must be scoped to a CONFIGURED-but-broken Codex.

    Without this, refusing every turn would satisfy the test above while breaking
    the deterministic bridge for every operator who configured nothing.
    """
    from seshat.studio.app import create_app

    app, token = create_app(_workspace(tmp_path), port=9999)
    client = _authenticated(app, token)
    thread_id = client.post(
        "/api/v1/agent/threads", json={"selected_table_id": None}
    ).json()["thread_id"]

    accepted = client.post(
        f"/api/v1/agent/threads/{thread_id}/turns",
        json={
            "prompt": "what is blocking gold?",
            "snapshot_revision": "r1",
            "requested_mode": "read_only",
        },
    )

    assert accepted.status_code == 202, accepted.text


def test_the_workspace_projection_reports_the_real_agent_health(
    tmp_path: Path,
) -> None:
    """P1 (#621 review): the INTERFACE reads `/workspace`, not `/bootstrap/state`.

    `build_workspace_snapshot` hardcoded `disabled`, so a working Codex launch
    displayed as disabled and a fallback displayed identically to a healthy bridge.
    Adding fields to an endpoint the UI never reads is not reporting.
    """
    from seshat.studio.app import create_app

    configured, token = create_app(
        _workspace(tmp_path), port=9999, agent_provider="codex", codex_version="0.1.0"
    )
    health = (
        _authenticated(configured, token)
        .get("/api/v1/workspace")
        .json()["agent_health"]
    )

    assert health["state"] == "incompatible", health
    assert "0.1.0" in health["summary"], health


def test_the_fake_default_still_projects_disabled(tmp_path: Path) -> None:
    """The inverse: an operator who configured nothing sees `disabled`, as before."""
    from seshat.studio.app import create_app

    app, token = create_app(_workspace(tmp_path), port=9999)

    health = _authenticated(app, token).get("/api/v1/workspace").json()["agent_health"]

    assert health["state"] == "disabled", health


def test_a_supported_cli_is_not_claimed_to_be_signed_in(tmp_path: Path) -> None:
    """P1 (#621 review): startup runs `--version` and nothing else.

    It never starts the app-server and never calls `account/read`, so sign-in state
    is genuinely unknown. Reporting `signed_in=True` claimed "Codex is signed in and
    responding" on the strength of a version string -- a signed-out CLI would read
    healthy and the analyst would discover otherwise only when a turn failed.

    `signed_out` is the honest answer AND the more useful one: it names a recovery
    action, where a false `ready` names none. A live handshake probe at boot is
    #618's work.
    """
    from seshat.studio.app import create_app

    app, token = create_app(
        _workspace(tmp_path), port=9999, agent_provider="codex", codex_version="0.147.0"
    )

    health = _authenticated(app, token).get("/api/v1/workspace").json()["agent_health"]

    assert health["state"] != "healthy", health
    assert health["state"] == "signed_out", health
    assert health["recovery_action"], "a non-ready state must name a recovery action"


def test_the_fallback_detail_says_turns_are_refused(tmp_path: Path) -> None:
    """P2 (#621 review): the operator-facing text must match what actually happens.

    The refusal landed after these strings were written, so they still described the
    old behaviour -- "answering with the deterministic bridge" -- while every turn
    returned 503. The surface added to prevent confusion about which agent answered
    was stating the opposite of the truth.
    """
    from seshat.studio.app import create_app

    for version in ("0.1.0", None):
        app, _ = create_app(
            _workspace(tmp_path / f"ws{version}"),
            port=9999,
            agent_provider="codex",
            codex_version=version,
        )
        detail = app.state.agent_provider_detail

        assert "refused" in detail, detail
        assert "deterministic bridge is answering" not in detail, detail
