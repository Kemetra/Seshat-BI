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


#: A concrete port for the in-process TestClient. `create_app` requires one and has no
#: default on purpose: production resolves the OS-assigned port by binding first, and a
#: default here is what previously let the app enforce a port nothing listened on.
_TEST_PORT = 8931


@pytest.fixture
def app_and_token(workspace: Path):
    """The real ASGI app plus its one-time bootstrap token."""
    pytest.importorskip("fastapi")
    from seshat.studio import app as app_module

    return app_module.create_app(workspace, port=_TEST_PORT)


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


def test_a_mutating_request_with_no_origin_is_refused(authed_client) -> None:
    """The contract: "Mutating requests with a missing origin are rejected."

    An earlier revision only rejected a PRESENT but wrong origin, so any client that
    simply omitted the header reached a mutating route. Absence is not proof of
    same-origin. Asserted on a non-bootstrap mutation, since `/bootstrap` is the one
    documented exemption.
    """
    response = authed_client.post("/api/v1/decisions", json={})

    assert response.status_code == 403, (
        "a mutating request with no Origin must be refused before routing, so it "
        "never even reaches the 405 for an unsupported method"
    )


def test_bootstrap_is_exempt_from_the_origin_requirement(client, app_and_token) -> None:
    """The "Origin, WHEN REQUIRED" seam.

    `/bootstrap` establishes the session, so it can be a top-level navigation with no
    Origin at all -- requiring one would break the documented one-time-link flow. Its
    defence is the 256-bit single-use token plus exact Host enforcement.
    """
    _app, token = app_and_token

    response = client.post("/api/v1/bootstrap", params={"token": token})

    assert response.status_code == 204


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


def test_the_decisions_route_is_read_only(authed_client, app_and_token) -> None:
    """FR-022 -- read-only, with no mutation route to reach.

    The POST is sent WITH a valid Origin so it gets past the same-origin guard: the
    point is that no mutating handler exists (405), not that the middleware stopped it.
    Without the header the request is refused at step 2 and never reaches routing,
    which would prove something weaker.
    """
    app, _token = app_and_token
    origin = {"Origin": f"http://{app.state.expected_host}"}

    assert authed_client.get("/api/v1/decisions").status_code == 200
    assert (
        authed_client.post("/api/v1/decisions", json={}, headers=origin).status_code
        == 405
    )


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


def test_the_response_boundary_actually_scrubs_the_payload(
    authed_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(g) must be WIRED, not merely present.

    Deleting the `scrub_payload` call left all 194 tests green, because the projection
    already emits workspace-relative references -- so nothing in the fixtures needed
    scrubbing. Injecting a value that DOES need it proves the boundary call is on the
    real path, which is what stops a future refactor from silently removing it.
    """
    from seshat.studio import projection

    leaky = "/absolute/operator/layout/secret.yaml"
    original = projection.build_workspace_snapshot

    def with_a_leak(root, **kwargs):  # type: ignore[no-untyped-def]
        snapshot = original(root, **kwargs)
        defect = projection.InputDefect(
            code="synthetic",
            message=f"failed reading {leaky}",
            source_ref=leaky,
            recovery_action="none",
        )
        return projection.WorkspaceSnapshot(
            identity=snapshot.identity,
            generated_at=snapshot.generated_at,
            agent_health=snapshot.agent_health,
            tables=snapshot.tables,
            input_defects=(defect,),
        )

    monkeypatch.setattr(projection, "build_workspace_snapshot", with_a_leak)

    body = authed_client.get("/api/v1/workspace").text

    assert leaky not in body, (
        "an absolute path reached the browser; the boundary scrub is not applied"
    )
    assert "redacted" in body.lower()


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


# --------------------------------------------------------------------------- #
# The bound port must be the port the app enforces (release blocker)          #
# --------------------------------------------------------------------------- #


def test_the_app_enforces_the_port_it_was_actually_given(workspace: Path) -> None:
    """FR-003 requires an OS-ASSIGNED port, and the Host guard must match it.

    A hardcoded port broke the serving path completely: the app demanded
    `127.0.0.1:8931` while uvicorn bound port 0 (a random one), so every request --
    including the public /health -- was refused by the Host guard.
    """
    pytest.importorskip("fastapi")
    from seshat.studio import app as app_module

    app, _token = app_module.create_app(workspace, port=54321)

    assert app.state.launch.port == 54321
    assert app.state.expected_host == "127.0.0.1:54321"


def test_creating_the_app_never_invents_a_fixed_port(workspace: Path) -> None:
    """A predictable port is a target, and FR-003 forbids choosing one."""
    pytest.importorskip("fastapi")
    from seshat.studio import app as app_module

    app, _token = app_module.create_app(workspace, port=1)

    assert app.state.launch.port == 1, (
        "create_app must use the port it is GIVEN, never a literal of its own"
    )


def test_the_launcher_binds_first_then_enforces_that_port(
    workspace: Path, assets_present, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The launcher must resolve a real port BEFORE building the app.

    Otherwise the Host guard and the listening socket disagree and nothing works.
    """
    pytest.importorskip("fastapi")
    from seshat.studio import __main__ as launcher

    served: dict[str, object] = {}

    def fake_run(application, **kwargs):  # type: ignore[no-untyped-def]
        served["expected_host"] = application.state.expected_host
        served["port"] = kwargs.get("port")
        served["host"] = kwargs.get("host")

    monkeypatch.setattr(launcher, "_serve", fake_run)

    assert launcher.main(["--repo", str(workspace)]) == 0

    assert served["port"] not in (None, 0), "uvicorn was handed the placeholder port"
    assert served["expected_host"] == f"{served['host']}:{served['port']}", (
        "the app enforces a different port than the one being served"
    )


def test_the_launcher_refuses_when_the_frontend_is_absent(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A wheel built without the frontend must say so, not serve a blank page.

    The absence is CREATED here rather than assumed: whether `studio-ui/dist` has been
    built is ambient state (CI builds it, a fresh clone has not), so a test that relied
    on it would pass or fail depending on who ran it.
    """
    pytest.importorskip("fastapi")
    from seshat.studio import __main__ as launcher
    from seshat.studio import assets

    monkeypatch.setattr(
        assets,
        "packaged_static_directory",
        lambda: workspace / "definitely-not-built",
    )

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


@pytest.mark.parametrize("bogus", [0, -1, -8931])
def test_repinning_to_a_non_port_is_refused(workspace: Path, bogus: int) -> None:
    """The guard was deletable with the whole suite green.

    `OS_ASSIGNED_PORT` (0) is a REQUEST for any free port, not a result. Accepting it
    as a bound port is what produced the shipped-broken serving path, so the refusal
    needs its own test rather than only a docstring.
    """
    from seshat.studio import config

    launch = config.LaunchConfiguration.for_workspace(workspace)

    with pytest.raises(ValueError, match="real port"):
        launch.with_bound_port(bogus)


def test_a_repinned_port_is_what_host_enforcement_compares(workspace: Path) -> None:
    from seshat.studio import config, session

    bound = config.LaunchConfiguration.for_workspace(workspace).with_bound_port(54321)

    assert session.host_is_allowed(
        f"{bound.bind_host}:{bound.port}", bound.bind_host, bound.port
    )
    assert not session.host_is_allowed(
        f"{bound.bind_host}:0", bound.bind_host, bound.port
    )
