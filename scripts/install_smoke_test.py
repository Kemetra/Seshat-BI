#!/usr/bin/env python3
"""Install smoke test (spec 108, FR-003) -- release & distribution maturity.

Proves that a fresh, from-source build of this package installs cleanly into an
isolated environment and exposes BOTH console scripts (``retail`` and ``seshat``)
as working commands. This is NOT a publish step: it never talks to PyPI or any
other index, and it uses no credentials/secrets (FR-004).

What it does, in order:
    1. Build a wheel from the repo root with ``pip wheel . --no-deps`` into a
       throwaway temp directory. (No ``build`` module dependency required --
       pip alone is sufficient, and pip is always present in a Python
       environment capable of running this script.)
    2. Create a brand-new, empty virtual environment in another throwaway temp
       directory (``venv.create(..., with_pip=True)``) -- never reuses the
       calling interpreter's site-packages.
    3. Install the built wheel (plus its declared runtime dependencies --
       ``--no-deps`` above only skips fetching build-time deps twice; the
       wheel install below resolves and installs ``pyyaml`` normally) into
       that clean venv.
    4. Assert both the ``retail`` and ``seshat`` console-script executables
       exist in the venv's scripts directory.
    5. Run ``retail check --help`` (via the venv's own executable, not this
       process's) and assert it exits 0.
    6. Run ``seshat check --help`` and assert it exits 0 too, proving the two
       console scripts are genuinely equivalent, not just both present.

Exit code is 0 only if every step above succeeds. Any failure exits non-zero
with a clear message -- this script does not swallow errors or "skip if
unavailable"; a broken build/install IS the failure this script exists to
catch.

Usage (local):
    python scripts/install_smoke_test.py

Usage (CI): see the ``smoke`` job in ``.github/workflows/ci.yml``.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import venv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    """Run a subprocess, streaming output, and raise loudly on failure."""
    print(f"+ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        raise SystemExit(f"FAIL: command exited {result.returncode}: {' '.join(cmd)}")


def _venv_bin_dir(venv_dir: Path) -> Path:
    """Return the venv's script/executable directory, cross-platform."""
    scripts_dir = venv_dir / ("Scripts" if sys.platform == "win32" else "bin")
    if not scripts_dir.is_dir():
        raise SystemExit(f"FAIL: venv scripts dir not found: {scripts_dir}")
    return scripts_dir


def _executable_path(bin_dir: Path, name: str) -> Path:
    """Return the path to a named console script, adding .exe on Windows."""
    candidate = bin_dir / (f"{name}.exe" if sys.platform == "win32" else name)
    return candidate


_CONSOLE_SCRIPTS = ("retail", "seshat")


def _build_wheel(wheel_dir: Path) -> Path:
    """Build a wheel from the repo (no build-time dep re-fetch); return its path."""
    print("== Step 1: build wheel ==", flush=True)
    _run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            str(REPO_ROOT),
            "--no-deps",
            "-w",
            str(wheel_dir),
        ]
    )
    wheels = sorted(wheel_dir.glob("*.whl"))
    if not wheels:
        raise SystemExit(f"FAIL: no wheel produced in {wheel_dir}")
    print(f"Built wheel: {wheels[-1].name}", flush=True)
    return wheels[-1]


def _create_clean_venv(venv_dir: Path) -> tuple[Path, Path]:
    """Create a clean venv (never reuses this process's env). Return
    ``(bin_dir, venv_python)`` -- the interpreter may be ``python`` or, on some
    platforms, ``python3``."""
    print("== Step 2: create clean venv ==", flush=True)
    venv.create(venv_dir, with_pip=True)
    bin_dir = _venv_bin_dir(venv_dir)
    venv_python = _executable_path(bin_dir, "python")
    if not venv_python.exists():
        venv_python = _executable_path(bin_dir, "python3")  # some platforms
    if not venv_python.exists():
        raise SystemExit(f"FAIL: venv python not found under {bin_dir}")
    return bin_dir, venv_python


def _assert_scripts_exist(bin_dir: Path) -> None:
    """FAIL if either console script is missing from the installed venv."""
    print("== Step 4: assert console scripts exist ==", flush=True)
    missing = [
        str(_executable_path(bin_dir, name))
        for name in _CONSOLE_SCRIPTS
        if not _executable_path(bin_dir, name).exists()
    ]
    if missing:
        raise SystemExit(
            "FAIL: expected console script(s) not found: " + ", ".join(missing)
        )
    print("Both 'retail' and 'seshat' console scripts are present.", flush=True)


def _assert_check_help_runs(bin_dir: Path) -> None:
    """FAIL if `<script> check --help` exits non-zero via either console script."""
    print("== Step 5/6: run 'check --help' via both console scripts ==", flush=True)
    for name in _CONSOLE_SCRIPTS:
        exe = _executable_path(bin_dir, name)
        result = subprocess.run([str(exe), "check", "--help"])
        if result.returncode != 0:
            raise SystemExit(f"FAIL: `{name} check --help` exited {result.returncode}")
        print(f"`{name} check --help` exited 0.", flush=True)


def main() -> int:
    with (
        tempfile.TemporaryDirectory(prefix="seshat-smoke-wheel-") as wheel_tmp,
        tempfile.TemporaryDirectory(prefix="seshat-smoke-venv-") as venv_tmp,
    ):
        wheel_path = _build_wheel(Path(wheel_tmp))
        bin_dir, venv_python = _create_clean_venv(Path(venv_tmp) / "venv")
        print("== Step 3: install wheel into clean venv ==", flush=True)
        _run([str(venv_python), "-m", "pip", "install", str(wheel_path)])
        _assert_scripts_exist(bin_dir)
        _assert_check_help_runs(bin_dir)

    print("\nPASS: install smoke test succeeded.", flush=True)
    return 0


if __name__ == "__main__":
    # Explicit cleanup guard: TemporaryDirectory context managers above already
    # remove both temp trees on any exit path (success, SystemExit, or
    # uncaught exception), so no separate teardown is needed here.
    try:
        sys.exit(main())
    except KeyboardInterrupt:  # pragma: no cover - interactive use only
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
