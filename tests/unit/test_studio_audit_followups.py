"""Studio audit follow-ups: each test pins one reported defect's fix.

Grouped by the surface they exercise. Each would fail on the pre-fix code: the
nested-workspace read returned [], thread creation stored any label, the turn
request carried only the raw prompt, command approvals were labelled low risk,
four Operations components could only read healthy, a closed tab's turn was only
reaped by a new turn, and a session expired twelve hours after bootstrap however
active it was.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

API = "/api/v1"


# --- codex executable resolution ---


def test_codex_is_never_resolved_from_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from seshat.studio import codex_process

    planted = tmp_path / ("codex.bat" if os.name == "nt" else "codex")
    planted.write_text("echo planted\n", encoding="utf-8")
    planted.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", os.pathsep.join([".", "", "relative/bin"]))
    monkeypatch.delenv("NoDefaultCurrentDirectoryInExePath", raising=False)

    assert codex_process.find_codex_executable() is None


def test_codex_on_an_absolute_path_entry_is_found_as_an_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from seshat.studio import codex_process

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    real = bin_dir / ("codex.cmd" if os.name == "nt" else "codex")
    real.write_text("echo real\n", encoding="utf-8")
    real.chmod(0o755)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setenv("PATH", str(bin_dir))

    found = codex_process.find_codex_executable()

    assert found is not None and Path(found).is_absolute()
    assert Path(found).parent == bin_dir


# --- committed reads from a nested workspace ---


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "core.fsmonitor=false", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def test_a_nested_workspace_reads_its_own_committed_store(tmp_path: Path):
    pytest.importorskip("fastapi")
    from seshat.studio import workbench_routes

    workspace = tmp_path / "ws"
    store = workspace / ".seshat" / "semantic-decisions.yaml"
    store.parent.mkdir(parents=True)
    store.write_text("decisions:\n  - id: d1\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(
        tmp_path,
        "-c",
        "user.email=t@example.invalid",
        "-c",
        "user.name=t",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-q",
        "-m",
        "init",
    )

    text = workbench_routes.CommittedReader(workspace).file_at_head(
        ".seshat/semantic-decisions.yaml"
    )

    assert text is not None and "d1" in text


# --- thread creation validates the table it is bound to ---


def _client(tmp_path: Path):
    pytest.importorskip("fastapi")
    from unit import _workbench_fixtures as fixtures

    return fixtures.studio_client(tmp_path)


@pytest.mark.parametrize("selected", ["no_such_table", 7, ["ready_sales"]])
def test_an_unknown_or_malformed_table_binding_is_refused(tmp_path: Path, selected):
    client = _client(tmp_path)

    response = client.post(f"{API}/agent/threads", json={"selected_table_id": selected})

    assert response.status_code == 422, response.text


@pytest.mark.parametrize("selected", ["ready_sales", None])
def test_a_known_table_or_no_table_is_accepted(tmp_path: Path, selected):
    client = _client(tmp_path)

    response = client.post(f"{API}/agent/threads", json={"selected_table_id": selected})

    assert response.status_code == 201, response.text


def _bound_thread(client, table: str | None = "ready_sales") -> str:
    created = client.post(f"{API}/agent/threads", json={"selected_table_id": table})
    assert created.status_code == 201, created.text
    return created.json()["thread_id"]


def _register(client, thread_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    from types import SimpleNamespace

    from seshat.studio.approval_routes import register_approval

    return register_approval(
        client.app,
        thread_id,
        client.app.state.threads.thread(thread_id),
        SimpleNamespace(payload=payload),
    )


def _produced(client, command: object, **params: object) -> dict[str, Any]:
    """An approval as the REAL producer emits it, from a fixture-shaped frame.

    Hand-built payloads cannot prove the allow path: they would pass even if
    normalization never computed the cwd verdict the relay depends on.
    """
    from seshat.studio.codex_protocol import (
        NormalizationContext,
        normalize_approval_request,
    )

    frame = {
        "jsonrpc": "2.0",
        "id": 20,
        "method": "item/commandExecution/requestApproval",
        "params": {"itemId": "item_cmd", "command": command, **params},
    }
    root = Path(client.app.state.launch.workspace_root)
    produced = normalize_approval_request(
        frame, context=NormalizationContext(workspace_root=root)
    )
    assert produced is not None
    return produced[1]


def test_ready_table_cannot_allow_a_command_while_another_table_is_blocked(
    tmp_path: Path,
):
    """A thread label must not clear a different table's mapping gate."""
    from unit import _studio_workspace_fixtures as workspace_fixtures

    client = _client(tmp_path)
    workspace_fixtures.write_blocked_table(tmp_path, table="blocked_sales")
    thread_id = _bound_thread(client)
    payload = _register(
        client,
        thread_id,
        _produced(client, "write silver SQL for blocked_sales", cwd=str(tmp_path)),
    )

    assert payload["allow_permitted"] is False
    assert any("cannot verify" in reason for reason in payload["forbidden_reasons"])
    denied = client.post(
        f"{API}/agent/threads/{thread_id}/approvals/item_cmd",
        json={"decision": "allow_once"},
    )
    assert denied.status_code == 403, denied.text


def test_bound_thread_can_allow_an_exact_read_run_inside_the_workspace(
    tmp_path: Path,
):
    """The technical Allow path is reachable, end to end from the provider frame."""
    client = _client(tmp_path)
    thread_id = _bound_thread(client)
    produced = _produced(client, "rg --files", cwd=str(tmp_path))
    # No live Codex child is blocked on this request here, so drop its transport id
    # as the fake bridge does: this pins the readiness gate, not delivery.
    produced.pop("provider_request_id")
    payload = _register(client, thread_id, produced)

    assert payload["allow_permitted"] is True
    assert "cwd_in_workspace" not in payload  # a relay input, not a streamed field
    allowed = client.post(
        f"{API}/agent/threads/{thread_id}/approvals/item_cmd",
        json={"decision": "allow_once"},
    )
    assert allowed.status_code == 204, allowed.text


@pytest.mark.parametrize("where", ["outside", "absent", "malformed"])
def test_an_exact_read_outside_the_workspace_is_refused(tmp_path: Path, where: str):
    """`rg --files` from another directory is still a read beyond the workspace."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    client = _client(workspace)
    cwd = {"outside": {"cwd": str(tmp_path)}, "absent": {}, "malformed": {"cwd": 7}}
    thread_id = _bound_thread(client)
    payload = _register(
        client, thread_id, _produced(client, "rg --files", **cwd[where])
    )

    assert payload["allow_permitted"] is False


def test_an_unbound_thread_cannot_allow_even_an_exact_read(tmp_path: Path):
    client = _client(tmp_path)
    thread_id = _bound_thread(client, None)
    payload = _register(client, thread_id, _produced(client, "pwd", cwd=str(tmp_path)))

    assert payload["allow_permitted"] is False


@pytest.mark.parametrize(
    "command",
    [
        "rg --files; echo bypass",
        "rg --files && echo bypass",
        "python -c 'print(1)'",
        ["rg", "--files"],
    ],
)
def test_opaque_compound_or_malformed_commands_are_not_unlocked(
    tmp_path: Path, command: object
):
    """A ready label cannot bless a shell program Studio cannot inspect."""
    client = _client(tmp_path)
    thread_id = _bound_thread(client)
    payload = _register(
        client, thread_id, _produced(client, command, cwd=str(tmp_path))
    )

    assert payload["allow_permitted"] is False
    assert payload["forbidden_reasons"]


def test_a_hand_built_payload_without_the_cwd_verdict_fails_closed(tmp_path: Path):
    """A bridge that never ran normalization (the fake one) cannot reach Allow."""
    client = _client(tmp_path)
    thread_id = _bound_thread(client)
    payload = _register(
        client,
        thread_id,
        {
            "approval_id": "hand-built",
            "required_authority": "technical",
            "action": "run_command",
            "target": "rg --files",
        },
    )

    assert payload["allow_permitted"] is False


# --- the turn context reaches the provider ---


class _RecordingSession:
    sent: list[dict[str, Any]] = []

    def __init__(self, plan: Any) -> None:
        self.plan = plan
        _RecordingSession.sent = []

    def start(self) -> None:
        return None

    def close(self) -> None:
        return None

    def send(self, frame: dict[str, Any]) -> None:
        _RecordingSession.sent.append(frame)

    def frames(self, timeout: float = 0.0, *, patience=None):
        yield {"id": 1, "result": {}}
        yield {"id": 2, "result": {"thread": {"id": "thr_x"}}}
        yield {"method": "turn/completed", "params": {"turn": {"status": "completed"}}}


def test_the_turn_request_carries_the_governance_context(
    monkeypatch: pytest.MonkeyPatch,
):
    from seshat.studio import codex_bridge
    from seshat.studio.codex_process import CodexLaunchPlan
    from seshat.studio.turn_context import BUSINESS_APPROVAL_REMINDER

    monkeypatch.setattr(codex_bridge, "CodexSession", _RecordingSession)
    bridge = codex_bridge.CodexBridge(
        CodexLaunchPlan(argv=(sys.executable,), cwd=Path.cwd())
    )

    list(
        bridge.run_turn(
            prompt="approve the mapping",
            turn_id="t1",
            requested_mode="propose_changes",
            turn_context=f"Mode: propose_changes\n{BUSINESS_APPROVAL_REMINDER}",
        )
    )

    start = next(f for f in _RecordingSession.sent if f.get("method") == "turn/start")
    texts = [item["text"] for item in start["params"]["input"]]
    assert BUSINESS_APPROVAL_REMINDER in texts[0]
    assert texts[-1] == "approve the mapping"


def test_the_route_builds_the_context_for_a_context_aware_bridge(tmp_path: Path):
    client = _client(tmp_path)
    app = client.app
    captured: dict[str, Any] = {}
    fake = app.state.bridge

    class _Capturing:
        def describe(self) -> dict[str, Any]:
            return fake.describe()

        def run_turn(self, *, prompt, turn_id, requested_mode, turn_context=None):
            captured["turn_context"] = turn_context
            return fake.run_turn(
                prompt=prompt, turn_id=turn_id, requested_mode=requested_mode
            )

    app.state.bridge = _Capturing()
    thread = client.post(
        f"{API}/agent/threads", json={"selected_table_id": "ready_sales"}
    ).json()["thread_id"]

    started = client.post(
        f"{API}/agent/threads/{thread}/turns",
        json={"prompt": "what next?", "requested_mode": "read_only"},
    )

    assert started.status_code == 202, started.text
    from seshat.studio.turn_context import BUSINESS_APPROVAL_REMINDER

    context = captured["turn_context"]
    assert BUSINESS_APPROVAL_REMINDER in context
    assert "Selected table: ready_sales" in context
    assert "Requested mode: read_only" in context


# --- approval labels are not invented ---


def test_a_command_approval_claims_no_scope_or_risk_the_provider_did_not_state():
    from seshat.studio.codex_protocol import (
        NormalizationContext,
        normalize_approval_request,
    )

    frame = {
        "id": 20,
        "method": "item/commandExecution/requestApproval",
        "params": {"itemId": "i1", "command": "git push --force", "reason": "sync"},
    }

    _, payload = normalize_approval_request(
        frame, context=NormalizationContext(workspace_root=None)
    )

    assert "scope" not in payload
    assert "risk" not in payload


def test_a_grant_root_request_is_still_marked_high_risk():
    from seshat.studio.codex_protocol import (
        NormalizationContext,
        normalize_approval_request,
    )

    frame = {
        "id": 22,
        "method": "item/fileChange/requestApproval",
        "params": {"itemId": "i2", "grantRoot": "/etc"},
    }

    _, payload = normalize_approval_request(
        frame, context=NormalizationContext(workspace_root=None)
    )

    assert payload["risk"] == "high"


# --- Operations components have real probes ---


def test_operations_components_reflect_their_probes(tmp_path: Path):
    from seshat.studio import operations
    from seshat.studio.projection import AgentHealth

    missing = AgentHealth(
        state="missing",
        summary="The Codex CLI was not found on PATH.",
        recovery_action="Install it.",
        provider="codex",
        version=None,
    )

    report = {
        d.component: d
        for d in operations.report(
            tmp_path, agent_health=missing, static_dir=tmp_path / "absent"
        )
    }

    assert report["codex_adapter"].state == "missing"
    assert report["frontend_assets"].state == "missing"
    assert report["live_boundary"].state == "deferred"
    assert operations.PENDING_LIVE_MARKER in (report["live_boundary"].blocker or "")
    assert report["package_extras"].state in operations.COMPONENT_STATES
    assert report["package_extras"].evidence, "a probed state names its evidence"


def test_a_component_without_a_probe_never_reads_healthy(tmp_path: Path):
    from seshat.studio import operations

    report = {d.component: d for d in operations.report(tmp_path)}

    assert report["codex_adapter"].state == "deferred"
    assert report["live_boundary"].state == "deferred"


# --- an abandoned turn is reaped on any poll ---


def test_an_abandoned_turn_is_reaped_by_a_poll_on_another_thread(tmp_path: Path):
    client = _client(tmp_path)  # skips first when the app extra is absent
    from seshat.studio import agent_routes

    app = client.app
    fake = app.state.bridge

    class _Parked:
        def describe(self) -> dict[str, Any]:
            return fake.describe()

        def run_turn(self, *, prompt, turn_id, requested_mode):
            events = fake.run_turn(
                prompt=prompt, turn_id=turn_id, requested_mode=requested_mode
            )
            yield next(events)  # opens, then the tab closes: never advanced again

    app.state.bridge = _Parked()
    abandoned = client.post(f"{API}/agent/threads", json={}).json()["thread_id"]
    other = client.post(f"{API}/agent/threads", json={}).json()["thread_id"]
    client.post(
        f"{API}/agent/threads/{abandoned}/turns",
        json={"prompt": "hi", "requested_mode": "read_only"},
    )
    app.state.pending_turns[abandoned].last_touched = (
        time.monotonic() - agent_routes.ABANDONED_TURN_SECONDS - 1
    )

    client.get(f"{API}/agent/threads/{other}/events")

    assert abandoned not in app.state.pending_turns


# --- an active session slides its expiry ---


def test_an_active_session_is_renewed_on_use():
    from seshat.studio import session

    now = [0.0]
    store = session.SessionStore("t" * 43, ttl_seconds=100, clock=lambda: now[0])
    cookie = store.exchange("t" * 43)
    assert cookie is not None

    for _ in range(5):
        now[0] += 60
        assert store.is_valid_session(cookie)

    now[0] += 101
    assert not store.is_valid_session(cookie)
