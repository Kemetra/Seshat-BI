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

    # The serving surface arrives with T011 (typed endpoints plus the deferred half
    # of Phase 2: ASGI middleware, problem responses, security headers, cookie
    # expiry, unauthenticated refusal). Phase 2 delivers the package, launcher, and
    # security primitives, so a reachable launcher says so rather than pretending
    # to serve.
    print(
        "Studio launcher, workspace, and packaged assets are all present; the "
        "loopback service arrives with T011. Nothing is served yet.",
        file=sys.stderr,
    )
    return _EXIT_OK


if __name__ == "__main__":  # pragma: no cover - console-script parity
    raise SystemExit(main())
