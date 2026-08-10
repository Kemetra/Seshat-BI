"""T011 -- the typed deterministic endpoints, plus Phase 2's deferred half.

Scope: the seven DETERMINISTIC routes in `studio-api.yaml`. The six
`/agent/threads/*` routes belong to Phase 4 and are deliberately absent here.

    POST /bootstrap              -> 204 (token exchange)
    GET  /bootstrap/state        -> 200 BootstrapState
    GET  /workspace              -> 200 WorkspaceSnapshot
    GET  /tables/{table_id}      -> 200 TableJourney | 404
    GET  /decisions              -> 200 (read-only, no mutation route)
    GET  /agent/health           -> 200 AgentHealth
    GET  /health                 -> 200 (the ONLY public route)

This module also covers the items Phase 2 deferred here because they had no testable
surface until an app existed:

  (a) the ASGI security middleware in the contracted enforcement ORDER,
  (b) redacted problem responses, (c) security headers,
  (d) time-based cookie expiry, (e) unauthenticated-access refusal,
  (f) `authentication_mode` on BootstrapState (FR-013a),
  (g) `redact_for_boundary` applied at the real response boundary,
  (i) `LaunchConfiguration.port` re-pinned after bind, so `host_is_allowed` is not
      compared against the placeholder 0.

Skipped wholesale without the `studio` extra: these are HTTP behaviours, and a base
install has no web stack to exercise them with.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unit._studio_workspace_fixtures import (  # noqa: E402
    write_blocked_table,
    write_malformed_table,
    write_ready_table,
)

_SESSION_COOKIE = "seshat_studio_session"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / ".seshat").mkdir(parents=True)
    write_ready_table(tmp_path)
    write_blocked_table(tmp_path)
    return tmp_path


@pytest.fixture
def app_and_token(workspace: Path):
    """The real ASGI app plus its one-time bootstrap token."""
    pytest.importorskip("fastapi")
    from seshat.studio import app as app_module

    return app_module.create_app(workspace)


@pytest.fixture
def client(app_and_token):
    testclient = pytest.importorskip("fastapi.testclient")
    app, _token = app_and_token
    # `base_url` must match the app's expected Host exactly, or the DNS-rebinding
    # guard rejects every request -- which is the point of the guard.
    return testclient.TestClient(app, base_url=f"http://{app.state.expected_host}")


@pytest.fixture
def authed_client(client, app_and_token):
    _app, token = app_and_token
    exchanged = client.post("/api/v1/bootstrap", params={"token": token})
    assert exchanged.status_code == 204, exchanged.text
    return client


# --------------------------------------------------------------------------- #
# Contract conformance of the LIVE responses                                  #
# --------------------------------------------------------------------------- #


def _contract_document() -> dict:
    import yaml

    contract = (
        Path(__file__).resolve().parents[2]
        / "specs/139-seshat-studio-foundation/contracts/studio-api.yaml"
    )
    return yaml.safe_load(contract.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("route", "schema_name"),
    [
        ("/api/v1/workspace", "WorkspaceSnapshot"),
        ("/api/v1/bootstrap/state", "BootstrapState"),
        ("/api/v1/tables/ready_sales", "TableJourney"),
        ("/api/v1/agent/health", "AgentHealth"),
    ],
)
def test_the_live_response_validates_against_the_contract(
    authed_client, route: str, schema_name: str
) -> None:
    """The endpoint's REAL response, not just the projection dataclass.

    The projection is validated separately, but a route can still break conformance by
    wrapping, renaming, or dropping a field on the way out. Verifying the payload the
    browser actually receives is the only check that covers that.
    """
    jsonschema = pytest.importorskip("jsonschema")
    document = _contract_document()
    schema = {"$ref": f"#/components/schemas/{schema_name}", **document}
    validator = jsonschema.validators.validator_for(document)(schema)

    payload = authed_client.get(route).json()
    errors = [
        f"{list(error.absolute_path)}: {error.message}"
        for error in validator.iter_errors(payload)
    ]

    assert not errors, f"{route} violates {schema_name}:\n  " + "\n  ".join(errors)


def test_a_problem_response_validates_against_the_contract(client) -> None:
    """Failures must be contract-shaped too, or the browser cannot render them."""
    jsonschema = pytest.importorskip("jsonschema")
    document = _contract_document()
    schema = {"$ref": "#/components/schemas/Problem", **document}
    validator = jsonschema.validators.validator_for(document)(schema)

    payload = client.get("/api/v1/workspace").json()

    assert not list(validator.iter_errors(payload))


# --------------------------------------------------------------------------- #
# (e) unauthenticated access is refused                                       #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "route",
    [
        "/api/v1/bootstrap/state",
        "/api/v1/workspace",
        "/api/v1/tables/ready_sales",
        "/api/v1/decisions",
        "/api/v1/agent/health",
    ],
)
def test_a_protected_route_refuses_an_unauthenticated_request(client, route) -> None:
    """Phase 2 deferred this: there was no request pipeline to refuse anything."""
    response = client.get(route)

    assert response.status_code == 401


def test_health_is_the_only_public_route(client) -> None:
    """ "health is the only public endpoint and reveals no workspace identity"."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.text.lower()
    assert "ready_sales" not in body
    assert "blocked_sales" not in body


def test_a_forged_session_cookie_is_refused(client) -> None:
    client.cookies.set(_SESSION_COOKIE, "forged-cookie-value")

    assert client.get("/api/v1/workspace").status_code == 401


# --------------------------------------------------------------------------- #
# Bootstrap token exchange (FR-004)                                           #
# --------------------------------------------------------------------------- #


def test_the_token_exchange_sets_a_hardened_cookie(client, app_and_token) -> None:
    _app, token = app_and_token

    response = client.post("/api/v1/bootstrap", params={"token": token})

    assert response.status_code == 204
    cookie_header = response.headers.get("set-cookie", "")
    assert "httponly" in cookie_header.lower()
    assert "samesite=strict" in cookie_header.lower().replace(" ", "")
    assert "path=/" in cookie_header.lower()
    assert "domain=" not in cookie_header.lower()


def test_the_token_may_be_exchanged_only_once(client, app_and_token) -> None:
    _app, token = app_and_token

    assert client.post("/api/v1/bootstrap", params={"token": token}).status_code == 204
    second = client.post("/api/v1/bootstrap", params={"token": token})

    assert second.status_code in {401, 409}


def test_a_wrong_token_is_refused(client) -> None:
    response = client.post("/api/v1/bootstrap", params={"token": "x" * 43})

    assert response.status_code == 401


# --------------------------------------------------------------------------- #
# (a) enforcement order -- Host and Origin before endpoint logic              #
# --------------------------------------------------------------------------- #


def test_a_mismatched_host_is_refused_before_the_endpoint(authed_client) -> None:
    """The DNS-rebinding guard. `localhost` must NOT be accepted."""
    response = authed_client.get("/api/v1/workspace", headers={"Host": "localhost:1"})

    assert response.status_code == 403


def test_a_mutating_request_requires_an_exact_origin(client, app_and_token) -> None:
    """ "Mutating requests with a missing origin are rejected." CORS stays off."""
    _app, token = app_and_token

    response = client.post(
        "/api/v1/bootstrap",
        params={"token": token},
        headers={"Origin": "http://evil.example.com"},
    )

    assert response.status_code == 403


def test_no_cors_headers_are_ever_emitted(authed_client) -> None:
    response = authed_client.get("/api/v1/workspace")

    assert "access-control-allow-origin" not in {
        key.lower() for key in response.headers
    }


# --------------------------------------------------------------------------- #
# (c) security headers                                                        #
# --------------------------------------------------------------------------- #


def test_security_headers_are_present_on_every_response(authed_client) -> None:
    response = authed_client.get("/api/v1/workspace")
    headers = {key.lower(): value for key, value in response.headers.items()}

    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options", "").upper() in {"DENY", "SAMEORIGIN"}
    assert "default-src" in headers.get("content-security-policy", "")
    assert headers.get("referrer-policy")


# --------------------------------------------------------------------------- #
# (d) time-based cookie expiry                                                #
# --------------------------------------------------------------------------- #


def test_an_expired_session_is_refused(client, app_and_token) -> None:
    """Phase 2's SessionStore invalidated on exchange and shutdown, never on a clock."""
    app, token = app_and_token
    assert client.post("/api/v1/bootstrap", params={"token": token}).status_code == 204
    assert client.get("/api/v1/workspace").status_code == 200

    app.state.sessions.expire_now()

    assert client.get("/api/v1/workspace").status_code == 401


# --------------------------------------------------------------------------- #
# Deterministic payloads (FR-034)                                             #
# --------------------------------------------------------------------------- #


def test_the_workspace_route_returns_the_projection(authed_client) -> None:
    response = authed_client.get("/api/v1/workspace")

    assert response.status_code == 200
    body = response.json()
    assert {"identity", "generated_at", "tables", "agent_health"} <= set(body)
    assert [table["table_id"] for table in body["tables"]] == [
        "blocked_sales",
        "ready_sales",
    ]


def test_one_table_route_returns_that_journey(authed_client) -> None:
    response = authed_client.get("/api/v1/tables/ready_sales")

    assert response.status_code == 200
    assert response.json()["table_id"] == "ready_sales"
    assert len(response.json()["stages"]) == 7


def test_an_unknown_table_is_a_404(authed_client) -> None:
    assert authed_client.get("/api/v1/tables/nope").status_code == 404


def test_a_table_id_cannot_traverse_out_of_the_workspace(authed_client) -> None:
    """A path-shaped table id must not become a filesystem read."""
    response = authed_client.get("/api/v1/tables/..%2F..%2Fetc%2Fpasswd")

    assert response.status_code in {400, 404}


# --------------------------------------------------------------------------- #
# (f) FR-013a -- authentication_mode on BootstrapState                        #
# --------------------------------------------------------------------------- #


def test_the_bootstrap_state_names_the_active_authentication_mode(
    authed_client,
) -> None:
    """FR-013a: the analyst must always be able to tell which path is in use."""
    body = authed_client.get("/api/v1/bootstrap/state").json()

    assert body["authentication_mode"] == "subscription"


def test_the_bootstrap_state_declares_business_decisions_unrecordable(
    authed_client,
) -> None:
    """FR-022 -- Foundation records no named-human business decision."""
    body = authed_client.get("/api/v1/bootstrap/state").json()

    assert body["capabilities"]["business_decision_recording"] is False


# --------------------------------------------------------------------------- #
# FR-022 -- read-only decisions, no mutation route                            #
# --------------------------------------------------------------------------- #


def test_the_decisions_route_is_read_only(authed_client) -> None:
    assert authed_client.get("/api/v1/decisions").status_code == 200
    assert authed_client.post("/api/v1/decisions", json={}).status_code == 405


# --------------------------------------------------------------------------- #
# (b) + (g) redacted problem responses at the real boundary                    #
# --------------------------------------------------------------------------- #


def test_a_problem_response_never_leaks_an_absolute_path(
    client, app_and_token, workspace: Path
) -> None:
    """(g) `redact_for_boundary` must be applied where responses are actually built."""
    _app, token = app_and_token
    client.post("/api/v1/bootstrap", params={"token": token})

    write_malformed_table(workspace)
    response = client.get("/api/v1/workspace")

    assert str(workspace) not in response.text


def test_an_error_response_is_a_problem_document(client) -> None:
    """Failures return a redacted problem response, not a traceback."""
    response = client.get("/api/v1/workspace")

    assert response.status_code == 401
    assert "traceback" not in response.text.lower()
    body = response.json()
    assert {"title", "status", "detail", "recovery_action"} <= set(body)


# --------------------------------------------------------------------------- #
# The launcher reaches the app -- `--no-serve` exercises startup without a port #
# --------------------------------------------------------------------------- #


@pytest.fixture
def assets_present(monkeypatch: pytest.MonkeyPatch):
    """Stand in for the prebuilt frontend, which T012 produces.

    Without this the launcher correctly REFUSES with exit 2 -- `studio-ui/dist` does
    not exist until T012, so `describe_missing_assets` reports it. That refusal is
    itself covered by `test_studio_package_contract.py`; these tests are about what
    happens once the assets are there.
    """
    from seshat.studio import assets

    monkeypatch.setattr(assets, "describe_missing_assets", lambda directory: None)


def test_the_launcher_refuses_when_the_frontend_is_absent(
    workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The real state today: no `studio-ui/dist`, so the launcher must refuse."""
    pytest.importorskip("fastapi")
    from seshat.studio import __main__ as launcher

    assert launcher.main(["--repo", str(workspace), "--no-serve"]) == 2

    err = capsys.readouterr().err
    assert "assets are missing" in err
    assert str(workspace) not in err, "the diagnostic must not leak the layout"


def test_the_launcher_builds_the_app_without_binding_a_port(
    workspace: Path, assets_present, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--no-serve` must exercise the WHOLE startup path, then stop.

    An exit path with no test is how a validator ends up with zero callers, so this
    proves the launcher really reaches app construction and emits a one-time link.
    """
    pytest.importorskip("fastapi")
    from seshat.studio import __main__ as launcher

    exit_code = launcher.main(["--repo", str(workspace), "--no-serve"])

    assert exit_code == 0
    err = capsys.readouterr().err
    assert "/api/v1/bootstrap?token=" in err
    assert str(workspace) not in err, "the launch message must not leak the layout"


def test_the_bootstrap_link_carries_a_high_entropy_token(
    workspace: Path, assets_present, capsys: pytest.CaptureFixture[str]
) -> None:
    pytest.importorskip("fastapi")
    from seshat.studio import __main__ as launcher

    launcher.main(["--repo", str(workspace), "--no-serve"])
    err = capsys.readouterr().err

    token = err.split("token=", 1)[1].split()[0]
    assert len(token) >= 43, "a 256-bit urlsafe token is at least 43 characters"


# --------------------------------------------------------------------------- #
# (i) the port is re-pinned after bind                                        #
# --------------------------------------------------------------------------- #


def test_the_launch_configuration_can_be_repinned_to_the_bound_port(
    workspace: Path,
) -> None:
    """`host_is_allowed` compares against the configured port.

    `OS_ASSIGNED_PORT` is 0 until the socket is bound, so without a re-pin the guard
    would compare every request against port 0 -- failing closed, but always.
    """
    from seshat.studio import config

    launch = config.LaunchConfiguration.for_workspace(workspace)
    assert launch.port == config.OS_ASSIGNED_PORT

    bound = launch.with_bound_port(54321)

    assert bound.port == 54321
    assert bound.workspace_root == launch.workspace_root
    assert launch.port == config.OS_ASSIGNED_PORT, "the original must stay immutable"


def test_a_repinned_port_is_what_host_enforcement_compares(workspace: Path) -> None:
    from seshat.studio import config, session

    bound = config.LaunchConfiguration.for_workspace(workspace).with_bound_port(54321)

    assert session.host_is_allowed(
        f"{bound.bind_host}:{bound.port}", bound.bind_host, bound.port
    )
    assert not session.host_is_allowed(
        f"{bound.bind_host}:0", bound.bind_host, bound.port
    )
