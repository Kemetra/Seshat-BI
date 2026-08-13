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
    (tmp_path / ".seshat").mkdir(parents=True)
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
