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

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from . import config, projection, redaction, session

#: Every route lives under this prefix, matching the contract's server URL.
API_PREFIX = "/api/v1"

#: The only route reachable without a session.
_PUBLIC_PATHS = frozenset({f"{API_PREFIX}/health"})

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
    """Everything but the public health route and the exchange that mints a session."""
    return path not in _PUBLIC_PATHS and path != f"{API_PREFIX}/bootstrap"


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


def create_app(workspace: Path | str, *, port: int) -> tuple[FastAPI, str]:
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
    launch = config.LaunchConfiguration.for_workspace(workspace).with_bound_port(port)
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
    app.state.authentication_mode = "subscription"

    _register_routes(app)
    _install_security_middleware(app)
    return app, token
