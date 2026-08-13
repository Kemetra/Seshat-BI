"""The Studio ASGI application: seven deterministic endpoints (T011, FR-034).

Also the home of the half of Phase 2 that had no testable surface until an app
existed: the security middleware in the contracted enforcement ORDER, redacted problem
responses, security headers, time-based cookie expiry, and unauthenticated refusal.

**Import discipline.** FastAPI is imported at MODULE scope here, which is safe because
nothing outside the ``studio`` extra imports this module: the launcher reaches it only
after proving the web stack is present, and `seshat.cli` / `seshat.rules` never touch
it. That keeps the B1 never-execute boundary intact -- see
``test_importing_the_launcher_module_pulls_in_no_web_stack``.

**Enforcement order** (security-boundary.md, "Request Enforcement Order"), applied by
one middleware before any endpoint runs:

1. ``Host`` equals the selected loopback host and port;
2. ``Origin``, when required, exactly equals the Studio origin;
3. the session cookie is present, valid, and unexpired.

Ordering matters: a request from the wrong host must be refused before its cookie is
even looked at, so an attacker cannot learn whether a session exists.
"""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from . import (
    agent_routes,
    bridge,
    bridge_selection,
    codex_bridge,
    codex_process,
    config,
    events,
    projection,
    redaction,
    session,
)
from .bridge_selection import select_bridge

#: Distinguishes "probe the installed CLI" from an explicit `None` meaning "there is
#: none". A default of `None` would make the missing-CLI branch untestable without
#: uninstalling Codex from the machine running the tests.
_PROBE_CODEX = object()

#: Every route lives under this prefix, matching the contract's server URL.
API_PREFIX = "/api/v1"

#: Reachable without a session.
#:
#: `/health` is the contract's one public API endpoint. The DOCUMENT ROOT and the
#: bundled assets are also public, and must be: the page served at `/` is what PERFORMS
#: the token exchange, so requiring a session to fetch it would deadlock -- the browser
#: cannot obtain a session without first running the JavaScript that `/` delivers.
#: Serving them reveals nothing: the bundle is the same in every install and carries no
#: workspace content.
_PUBLIC_PATHS = frozenset({f"{API_PREFIX}/health", "/", "/index.html"})

#: Asset requests are public for the same reason as the document root.
_PUBLIC_PREFIXES = ("/assets/",)

#: Methods that mutate, and therefore must prove same-origin.
_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

#: Applied to every response. `frame-ancestors 'none'` plus `X-Frame-Options` covers
#: both the modern and legacy clickjacking defence; `default-src 'self'` keeps the
#: bundled frontend from reaching any third-party origin.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'"
    ),
    "Cache-Control": "no-store",
}


def _problem(
    status: int, title: str, detail: str, recovery_action: str
) -> JSONResponse:
    """A redacted problem document -- never a traceback, never a raw path.

    Shape matches the contract's `Problem` schema so a browser can render any failure
    the same way it renders a successful projection.
    """
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "recovery_action": recovery_action,
        },
    )


def _bootstrap_capabilities() -> dict[str, Any]:
    """What this build can do. `business_decision_recording` is const false (FR-022)."""
    return {
        "agent_turns": False,
        "technical_approvals": False,
        "business_decision_recording": False,
    }


def _check_host(request: Request, app: FastAPI) -> JSONResponse | None:
    """Step 1 -- the DNS-rebinding guard.

    First, deliberately: a request from the wrong host is refused before its cookie is
    ever inspected, so an attacker cannot learn whether a session exists.
    """
    if session.host_is_allowed(
        request.headers.get("host", ""),
        app.state.launch.bind_host,
        app.state.launch.port,
    ):
        return None
    return _problem(
        403,
        "Forbidden host",
        "The request Host does not match this Studio instance.",
        f"Open Studio at http://{app.state.expected_host} and retry.",
    )


def _check_origin(request: Request, app: FastAPI) -> JSONResponse | None:
    """Step 2 -- exact same-origin proof for anything that mutates.

    A MISSING Origin is refused, not waved through: "Mutating requests with a missing
    origin are rejected". An earlier revision rejected only a *present but wrong*
    origin, so any client that simply omitted the header reached a mutating route.

    ``/bootstrap`` is the one exemption, and it is what the contract's "``Origin``,
    **when required**" qualifier is for. That request is what ESTABLISHES the session,
    so it can be a top-level navigation carrying no Origin at all; requiring one would
    break the documented one-time-link flow. Its defence is the pair the contract
    actually specifies for it -- an unguessable 256-bit single-use token, plus exact
    Host enforcement from step 1 -- not same-origin proof.
    """
    if request.method not in _MUTATING_METHODS:
        return None

    origin = request.headers.get("origin")
    if origin and session.origin_is_allowed(
        origin, app.state.launch.bind_host, app.state.launch.port
    ):
        return None

    # ABSENT origin is tolerated only on `/bootstrap`. A PRESENT but wrong origin is
    # refused everywhere, including there: a cross-origin page attempting the token
    # exchange has no legitimate reason to, and exempting the route from the exemption's
    # own weakness costs nothing.
    if origin is None and request.url.path == f"{API_PREFIX}/bootstrap":
        return None
    return _problem(
        403,
        "Forbidden origin",
        "A mutating request must prove it came from the Studio origin.",
        f"Use the Studio window at http://{app.state.expected_host}.",
    )


def _requires_session(path: str) -> bool:
    """Everything but the public routes and the exchange that mints a session."""
    if path in _PUBLIC_PATHS or path == f"{API_PREFIX}/bootstrap":
        return False
    return not path.startswith(_PUBLIC_PREFIXES)


def _check_session(request: Request, app: FastAPI) -> JSONResponse | None:
    """Step 3 -- a present, valid, unexpired session cookie."""
    if not _requires_session(request.url.path):
        return None
    cookie = request.cookies.get(session.SESSION_COOKIE_NAME, "")
    if cookie and app.state.sessions.is_valid_session(cookie):
        return None
    return _problem(
        401,
        "Unauthenticated",
        "No valid Studio session is present.",
        "Reopen Studio from the agent to start a new session.",
    )


#: The contracted enforcement order. A list rather than inline branches so the ORDER is
#: reviewable at a glance and each step is testable on its own.
_ENFORCEMENT_STEPS = (_check_host, _check_origin, _check_session)


def _install_security_middleware(app: FastAPI) -> None:
    """Apply every enforcement step, in order, before any endpoint logic."""

    @app.middleware("http")
    async def enforce(request: Request, call_next):  # type: ignore[no-untyped-def]
        for step in _ENFORCEMENT_STEPS:
            refusal = step(request, app)
            if refusal is not None:
                return _with_headers(refusal)
        return _with_headers(await call_next(request))


def _with_headers(response: Response) -> Response:
    for header, value in _SECURITY_HEADERS.items():
        response.headers[header] = value
    return response


def _register_routes(app: FastAPI) -> None:
    """The seven deterministic routes. Agent-thread routes belong to Phase 4."""

    def _snapshot() -> projection.WorkspaceSnapshot:
        return projection.build_workspace_snapshot(app.state.launch.workspace_root)

    def _redact(payload: Any) -> Any:
        """Scrub the payload at the REAL boundary, not just in tests.

        The projection already emits workspace-relative references, so this is a
        belt-and-braces pass that catches anything a future field adds.
        """
        return redaction.scrub_payload(
            payload, workspace_root=app.state.launch.workspace_root
        )

    @app.get(f"{API_PREFIX}/health")
    async def health() -> dict[str, str]:
        """The ONLY public route, and it reveals no workspace identity."""
        return {"status": "ok"}

    @app.post(f"{API_PREFIX}/bootstrap", status_code=204)
    async def bootstrap(token: str, response: Response) -> Response:
        cookie = app.state.sessions.exchange(token)
        if cookie is None:
            return _problem(
                401,
                "Invalid bootstrap token",
                "The bootstrap token is wrong or has already been used.",
                "Reopen Studio from the agent to get a fresh link.",
            )
        response.set_cookie(
            session.SESSION_COOKIE_NAME,
            cookie,
            **session.session_cookie_attributes(),
        )
        response.status_code = 204
        return response

    @app.get(f"{API_PREFIX}/bootstrap/state")
    async def bootstrap_state() -> Any:
        return _redact(
            {
                "workspace": _snapshot().as_dict(),
                "navigation": ["command_room"],
                "authentication_mode": app.state.authentication_mode,
                #: WHICH implementation is answering, plus why. Separate from
                #: `authentication_mode`, which reports `subscription` whether Codex
                #: or the fake is driving -- so a fallback would be invisible without
                #: this, and the operator would read deterministic text as a real
                #: reply.
                "agent_provider": app.state.agent_provider,
                "agent_provider_detail": app.state.agent_provider_detail,
                "capabilities": _bootstrap_capabilities(),
            }
        )

    @app.get(f"{API_PREFIX}/workspace")
    async def workspace() -> Any:
        return _redact(_snapshot().as_dict())

    @app.get(f"{API_PREFIX}/tables/{{table_id}}")
    async def table(table_id: str) -> Any:
        journey = next(
            (item for item in _snapshot().tables if item.table_id == table_id), None
        )
        if journey is None:
            return _problem(
                404,
                "Unknown table",
                "No onboarded table matches that identifier.",
                "Open the Command Room to see the tables in this workspace.",
            )
        return _redact(journey.as_dict())

    @app.get(f"{API_PREFIX}/decisions")
    async def decisions() -> Any:
        """Read-only by construction: there is no mutation route to omit."""
        return {"items": []}

    @app.get(f"{API_PREFIX}/agent/health")
    async def agent_health() -> Any:
        return _snapshot().agent_health.as_dict()


def _register_frontend(app: FastAPI) -> None:
    """Serve the prebuilt bundle (FR-005).

    Registered AFTER the API routes so `/api/v1/*` always wins, and mounted rather than
    hand-rolled: Starlette's `StaticFiles` already resolves and contains paths, so a
    traversal-shaped asset request cannot escape the bundle. Hand-rolling that check
    would be a second, weaker copy of the containment logic.

    A missing bundle is not fatal here -- the launcher refuses before this point, and
    the API stays usable for a caller that only wants the projection.
    """
    from fastapi.staticfiles import StaticFiles

    from . import assets

    static_directory = assets.packaged_static_directory()
    if not static_directory.is_dir():
        return

    # `html=True` serves `index.html` for `/`, which is where a browser lands and
    # therefore where the token exchange runs.
    app.mount("/", StaticFiles(directory=static_directory, html=True), name="frontend")


def _probe_codex(configured_provider: str) -> tuple[str | None, str | None]:
    """The installed CLI's path and reported version, or `(None, None)`.

    Run ONCE at startup and only when Codex is actually configured: an operator on
    the fake must not pay a subprocess spawn at boot, and must not have a CLI that
    merely happens to be installed influence anything.

    Every failure returns `None` rather than raising. A missing, hung, or
    unintelligible CLI must degrade to the deterministic bridge -- a traceback here
    would take down the whole workspace, including the views that never needed Codex.
    """
    if configured_provider != "codex":
        return None, None
    executable = codex_process.find_codex_executable()
    if executable is None:
        return None, None
    try:
        completed = subprocess.run(  # noqa: S603 -- fixed argv, never a shell string
            [executable, "--version"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return executable, None
    reported = completed.stdout.strip().split()
    return executable, (reported[-1] if reported else None)


def create_app(
    workspace: Path | str,
    *,
    port: int,
    agent_provider: str = "fake",
    codex_version: str | None = _PROBE_CODEX,
) -> tuple[FastAPI, str]:
    """Build the app for one pinned workspace, returning it with its bootstrap token.

    The token is RETURNED rather than logged or stored in plaintext: the caller hands
    it to the browser once, and only its digest lives in the session store.

    ``port`` is REQUIRED and must be the port the server will actually listen on. An
    earlier revision hardcoded 8931 here while the launcher handed uvicorn
    ``OS_ASSIGNED_PORT`` (0), so the OS bound a random port while the Host guard
    demanded 8931 -- every request was refused, including the public health route,
    because Host is enforcement step 1. Taking the port as an argument makes the
    disagreement impossible to reintroduce: there is no default to fall back to, and
    FR-003's OS-assigned port stays the caller's to resolve.
    """
    launch = replace(
        config.LaunchConfiguration.for_workspace(workspace).with_bound_port(port),
        agent_provider=agent_provider,
    )
    #: `codex_version` is an injection seam for tests, which must exercise the
    #: untested-range and missing-CLI branches without depending on what happens to
    #: be installed on the machine running them. The sentinel keeps "probe the real
    #: CLI" distinguishable from an explicit `None` meaning "there is none".
    if codex_version is _PROBE_CODEX:
        executable, codex_version = _probe_codex(launch.agent_provider)
    else:
        executable = None if codex_version is None else "codex"
    token = session.generate_bootstrap_token()

    app = FastAPI(
        title="Seshat Studio", docs_url=None, redoc_url=None, openapi_url=None
    )
    app.state.launch = launch
    app.state.sessions = session.SessionStore(token)
    app.state.expected_host = f"{launch.bind_host}:{launch.port}"
    #: FR-013a: the default and the only path SC-010 certifies. An
    #: operator-configured alternate bridge sets this to
    #: `operator_configured_alternate`, and never by inference.
    #:
    #: Resolved through `select_bridge` rather than assigned literally, so the
    #: "never by degradation" guarantee lives in one tested function instead of in
    #: whatever this call site happens to do. `select_bridge` accepts the health
    #: state and deliberately ignores it -- see that module for why the parameter
    #: exists at all.
    app.state.bridge_selection = select_bridge(
        health_state="healthy",
        operator_configured_mode=launch.operator_configured_auth_mode,
        alternate_credential_present=launch.alternate_credential_present,
    )
    app.state.authentication_mode = app.state.bridge_selection.authentication_mode

    #: WHICH implementation answers turns, decided ONCE here. The probe is a
    #: subprocess; running it per turn would put a spawn on the critical path of
    #: every message, and could answer differently mid-session.
    provider = bridge_selection.select_provider(
        configured_provider=launch.agent_provider,
        executable=executable,
        version=codex_version,
        version_is_tested=codex_process.is_tested_version(codex_version),
    )
    app.state.agent_provider = provider.provider
    #: Reported to the browser because a SILENT fallback is the dangerous one: the
    #: operator sees a working Studio and believes Codex is answering while
    #: deterministic text comes back. `authentication_mode` cannot carry this -- it
    #: reads `subscription` either way.
    app.state.agent_provider_detail = provider.detail
    #: In-memory only (FR-035). The bridge is the deterministic fake until Phase 5
    #: introduces the Codex one; FR-014 keeps the swap to a single assignment.
    #:
    #: `workspace_root` is what enables FR-026 PATH redaction inside the event
    #: buffer: `redact_for_boundary` gates `redact_paths` on it, so omitting it
    #: silently disables half the redaction while credentials are still scrubbed and
    #: everything LOOKS clean. An earlier revision omitted it and every event carried
    #: absolute filesystem paths to the browser, including out-of-root paths that
    #: expose the operator's home directory layout.
    app.state.threads = events.ThreadStore(workspace_root=launch.workspace_root)
    app.state.bridge = (
        codex_bridge.CodexBridge(
            codex_process.CodexLaunchPlan.for_workspace(
                launch.workspace_root, executable=executable or "codex"
            )
        )
        if provider.provider == "codex"
        else bridge.FakeAgentBridge()
    )

    _register_routes(app)
    agent_routes.register_agent_routes(app)
    # After the API routes: the frontend mount claims `/`, so registering it first would
    # shadow every `/api/v1/*` path.
    _register_frontend(app)
    _install_security_middleware(app)
    return app, token
