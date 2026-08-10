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
from pathlib import Path

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


def main(argv: Sequence[str] | None = None) -> int:
    """Launch Studio, or report why it cannot start.

    The web stack is imported HERE, not at module scope, so that the absence of the
    ``studio`` extra is a reported state rather than an import-time crash.
    """
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exit_signal:  # argparse's own usage exit
        return int(exit_signal.code or _EXIT_USAGE)

    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ModuleNotFoundError as absent:
        print(_missing_extra_diagnostic(absent.name or "fastapi"), file=sys.stderr)
        return _EXIT_REFUSED

    from . import assets

    static_directory = assets.packaged_static_directory()
    problem = assets.describe_missing_assets(static_directory)
    if problem is not None:
        print(problem, file=sys.stderr)
        return _EXIT_REFUSED

    # The serving surface arrives with T007 (launch configuration, session store,
    # security middleware). T005 delivers only the package and launcher seam, so a
    # reachable launcher reports that plainly rather than pretending to serve.
    # The workspace is resolved HERE and named in the message: FR-001 pins exactly
    # one workspace per process, so the launcher must carry the value it accepted
    # rather than discard it.
    workspace = Path(args.repo).resolve()
    print(
        f"Studio launcher and packaged assets are present for {workspace}; the "
        "loopback service arrives with T007. Nothing is served yet.",
        file=sys.stderr,
    )
    return _EXIT_OK


if __name__ == "__main__":  # pragma: no cover - console-script parity
    raise SystemExit(main())
