"""THE documented Studio frontend build command (T012, FR-005).

One command, so there is no ambiguity about how the browser bundle reaches the wheel:

    python scripts/build_studio_frontend.py

It runs `npm ci` (or `npm install` when a lockfile is absent), `npm run build`, then
copies `studio-ui/dist/` into `src/seshat/studio/static/`, which sits inside the
already-declared wheel package so hatchling ships it with no force-include. End users
therefore never need Node (FR-005); only whoever BUILDS the wheel does.

The copy replaces the destination wholesale rather than merging: a stale asset left
behind from an earlier build would be served alongside the new one, and content-hashed
filenames mean the old file stays reachable indefinitely.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_UI = _REPO_ROOT / "studio-ui"
_DIST = _UI / "dist"
_TARGET = _REPO_ROOT / "src/seshat/studio/static"


def _run(command: list[str]) -> int:
    """Run one build step in the frontend workspace, streaming its output.

    `shell=False` with an argument LIST, never a joined string: the arguments are
    literals here, and keeping the list form means no shell ever interpolates them.
    """
    print(f"$ {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=_UI, shell=False, check=False)
    return completed.returncode


def _npm() -> str:
    """`npm.cmd` on Windows -- `npm` alone is not an executable there."""
    return "npm.cmd" if sys.platform == "win32" else "npm"


def _install() -> int:
    # `ci` is reproducible but REQUIRES a lockfile; falling back to `install` keeps a
    # fresh clone working instead of failing on a missing package-lock.json.
    if (_UI / "package-lock.json").is_file():
        return _run([_npm(), "ci", "--no-audit", "--no-fund"])
    return _run([_npm(), "install", "--no-audit", "--no-fund"])


def _copy_into_package() -> None:
    if not (_DIST / "index.html").is_file():
        where = _DIST.relative_to(_REPO_ROOT).as_posix()
        raise SystemExit(f"the build produced no {where}/index.html")
    if _TARGET.exists():
        shutil.rmtree(_TARGET)
    shutil.copytree(_DIST, _TARGET)
    shipped = sum(1 for path in _TARGET.rglob("*") if path.is_file())
    print(
        f"copied {shipped} file(s) into {_TARGET.relative_to(_REPO_ROOT).as_posix()}",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_studio_frontend",
        description="Build the Studio browser bundle and stage it for the wheel.",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Reuse the existing node_modules instead of reinstalling.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip the frontend unit tests. The release build must NOT skip them.",
    )
    args = parser.parse_args(argv)

    if not _UI.is_dir():
        raise SystemExit(f"{_UI.relative_to(_REPO_ROOT).as_posix()} does not exist")

    if not args.skip_install and (code := _install()) != 0:
        return code
    if not args.skip_tests and (code := _run([_npm(), "test", "--", "--run"])) != 0:
        return code
    if (code := _run([_npm(), "run", "build"])) != 0:
        return code

    _copy_into_package()
    return 0


if __name__ == "__main__":
    sys.exit(main())
