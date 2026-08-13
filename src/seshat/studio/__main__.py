"""``seshat-studio`` -- the dedicated Studio launcher (spec 139, FR-002).

Deliberately OUTSIDE the ``seshat``/``retail`` dispatch chain. Routing this through
``seshat.cli`` would put a web import on the static core's import path and trip the
B1 never-execute boundary at ``src/seshat/cli/*.py``.

**Every web import in this module is function-local.** Importing this module must
never load FastAPI, Uvicorn, or Starlette, so a base ``seshat-bi`` install can run
``seshat-studio`` and receive a named diagnostic instead of a traceback (FR-006).

Exit codes mirror the CLI families: 0 success, 1 usage, 2 refusal (missing extra,
missing frontend assets).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import WEB_DEPENDENCIES, config, redaction

_EXIT_OK = 0
_EXIT_USAGE = 1
_EXIT_REFUSED = 2


def _build_parser() -> argparse.ArgumentParser:
    """Stdlib-only, like the repo's other optional-family parsers."""
    parser = argparse.ArgumentParser(
        prog="seshat-studio",
        description=(
            "Open the Seshat Studio analyst console for one workspace on loopback."
        ),
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Workspace to serve. Exactly one workspace per process (FR-001).",
    )
    parser.add_argument(
        "--agent",
        choices=("fake", "codex"),
        default="fake",
        help=(
            "Which agent answers turns. Defaults to the deterministic bridge. "
            "`codex` is EXPLICIT: an installed Codex CLI is never selected on its "
            "own, because presence is not consent to use a provider."
        ),
    )
    parser.add_argument(
        "--no-serve",
        action="store_true",
        help=(
            "Verify the full startup path -- workspace, extra, assets, app -- "
            "then exit without binding a port."
        ),
    )
    return parser


def _missing_extra_diagnostic(missing: str) -> str:
    """The FR-006 recovery text: name the extra, name both install lanes.

    Delegates to ``seshat.cli._extra_install_hint`` -- the ONE hint surface -- so
    Studio cannot drift from the form the rest of the CLI emits, and so it inherits
    the ``pipx inject`` lane that does not re-resolve the installed build (#513).
    """
    from seshat.cli import _extra_install_hint

    return (
        f"Seshat Studio needs the optional `studio` extra, which is not installed "
        f"(missing: {missing}).\n"
        f"The base seshat-bi install stays free of Studio web dependencies by "
        f"design; enable the extra with one of:\n"
        f"{_extra_install_hint('studio')}"
    )


def _exit_code_for_argparse(exit_signal: SystemExit) -> int:
    """Map argparse's own exit into this module's codes.

    argparse exits 0 for ``--help`` and 2 for a usage error. Passing both through
    ``code or _EXIT_USAGE`` turned ``--help`` into a nonzero exit and reported a
    usage error as 2, the code reserved here for refusal.
    """
    if exit_signal.code in (0, None):
        return _EXIT_OK
    return _EXIT_USAGE


def _blames_the_missing_extra(absent: ModuleNotFoundError) -> bool:
    """True when the ABSENT module is one the ``studio`` extra provides.

    A ``ModuleNotFoundError`` from deeper inside fastapi's own import tree means a
    broken transitive dependency; telling the reader to install an extra they already
    have sends them down the wrong path.

    ``name`` is normally set by the import machinery, but an explicitly raised
    ``ModuleNotFoundError`` may leave it ``None``, so fall back to the message text
    rather than mis-classifying on absent metadata.
    """
    named = (absent.name or "").split(".")[0]
    if named:
        return named in WEB_DEPENDENCIES
    return any(dependency in str(absent) for dependency in WEB_DEPENDENCIES)


def _report_web_stack_failure(absent: ModuleNotFoundError) -> None:
    """Explain an unimportable web stack as either an absent extra or a broken env."""
    named = (absent.name or "").split(".")[0]
    if _blames_the_missing_extra(absent):
        print(_missing_extra_diagnostic(named or "fastapi"), file=sys.stderr)
        return
    print(
        f"Seshat Studio could not start: the `studio` extra appears installed, but "
        f"importing its web stack failed on {named or str(absent)!r}. This is a "
        f"broken or incomplete dependency in the active environment, not a missing "
        f"extra.",
        file=sys.stderr,
    )


def _bind_loopback(host: str):  # type: ignore[no-untyped-def]
    """Bind an OS-assigned loopback port and return the listening socket.

    ``socket`` is imported HERE rather than at module scope. B1's never-execute rule
    bans a module-scope socket import in the static core, and while this module is
    outside `_GOVERNED_PREFIXES`, keeping the import local preserves the property that
    importing the launcher opens nothing.
    """
    import socket

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, 0))
    listener.listen(128)
    return listener


def _serve(application, *, host: str, port: int, sock=None) -> None:  # type: ignore[no-untyped-def]
    """Run the ASGI server. Extracted so a test can observe the served port."""
    import uvicorn

    config_kwargs = {"host": host, "port": port, "log_level": "warning"}
    server = uvicorn.Server(uvicorn.Config(application, **config_kwargs))
    if sock is not None:
        server.run(sockets=[sock])
    else:  # pragma: no cover - the launcher always binds first
        server.run()


def _web_stack_is_importable() -> ModuleNotFoundError | None:
    """Import the web stack lazily; return the failure instead of raising.

    Function-local by contract: importing this module must never load FastAPI or
    Uvicorn, so a base install can run ``seshat-studio`` and get a diagnostic.
    """
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ModuleNotFoundError as absent:
        return absent
    return None


def main(argv: Sequence[str] | None = None) -> int:
    """Launch Studio, or report why it cannot start.

    The order of the checks is contractual: the workspace is resolved and RECOGNIZED
    BEFORE the web stack is imported ("resolves the requested repository before
    importing or starting the web server"), so an unrecognized workspace is refused
    on its own terms rather than surfacing as whatever the next step happens to hit.
    """
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exit_signal:
        return _exit_code_for_argparse(exit_signal)

    try:
        launch = config.LaunchConfiguration.for_workspace(args.repo)
    except ValueError as refusal:
        print(str(refusal), file=sys.stderr)
        return _EXIT_REFUSED

    absent = _web_stack_is_importable()
    if absent is not None:
        _report_web_stack_failure(absent)
        return _EXIT_REFUSED

    from . import assets

    problem = assets.describe_missing_assets(assets.packaged_static_directory())
    if problem is not None:
        print(
            redaction.redact_paths(problem, workspace_root=launch.workspace_root),
            file=sys.stderr,
        )
        return _EXIT_REFUSED

    # Serving is legal HERE and only here: B1's never-execute boundary governs
    # `src/seshat/rules/` and `src/seshat/cli/`, and this module is outside both
    # (asserted by test_the_launcher_is_outside_the_seshat_cli_dispatch_chain). FR-003
    # requires Studio to bind loopback, which the static core must never do.
    from . import app as app_module

    # BIND FIRST, then build. The app's Host guard compares against a concrete port, so
    # the port has to be known before the app exists. Binding here and handing uvicorn
    # the already-bound socket means the OS assigns the port exactly once -- no fixed
    # port (FR-003), and no window in which another process could take it.
    listener = _bind_loopback(launch.bind_host)
    bound = launch.with_bound_port(listener.getsockname()[1])

    application, token = app_module.create_app(
        bound.workspace_root, port=bound.port, agent_provider=args.agent
    )
    # The DOCUMENT ROOT carries the token, not the exchange route. An earlier revision
    # printed `/api/v1/bootstrap?token=...`, which is POST-only -- a browser navigating
    # there got 405 and Studio was simply unopenable. The page served at `/` reads the
    # token from its own URL, POSTs it, and strips it from history.
    print(
        f"Studio is ready. Open http://{application.state.expected_host}/?token={token}"
        " once, then discard the link.",
        file=sys.stderr,
    )
    if args.no_serve:
        # A launch that verifies the whole startup path without occupying a port --
        # what `--check` style callers and the acceptance harness need.
        listener.close()
        return _EXIT_OK

    _serve(application, host=bound.bind_host, port=bound.port, sock=listener)
    return _EXIT_OK
    return _EXIT_OK


if __name__ == "__main__":  # pragma: no cover - console-script parity
    raise SystemExit(main())
