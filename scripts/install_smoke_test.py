#!/usr/bin/env python3
"""Clean install smoke test for the Seshat BI public-beta journey."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_CONSOLE_SCRIPTS = ("retail", "seshat")
_FORBIDDEN_MODULES = (
    "pytest",
    "ruff",
    "testcontainers",
    "psycopg2",
    "pyodbc",
    "mysql",
    "snowflake",
    "openpyxl",
)


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print(f"+ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode:
        raise SystemExit(f"FAIL: command exited {result.returncode}: {' '.join(cmd)}")


def _capture(cmd: list[str], *, cwd: Path) -> str:
    print(f"+ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    output = result.stdout + result.stderr
    if result.returncode:
        raise SystemExit(
            f"FAIL: command exited {result.returncode}: {' '.join(cmd)}\n{output}"
        )
    return output


def _executable(bin_dir: Path, name: str) -> Path:
    candidate = bin_dir / (f"{name}.exe" if sys.platform == "win32" else name)
    if not candidate.exists():
        raise SystemExit(f"FAIL: expected executable not found: {candidate}")
    return candidate


def _assert_truthful(output: str, *, label: str) -> None:
    if re.search(r"\b(?:score|confidence)\s*[:=]\s*\d", output, re.IGNORECASE):
        raise SystemExit(f"FAIL: {label} contains a numeric score or confidence")
    if re.search(r"\b(?:readiness_)?state\s*[:=]\s*['\"]?pass", output, re.IGNORECASE):
        raise SystemExit(f"FAIL: {label} fabricates a readiness pass")


def _build_artifacts(dist_dir: Path) -> Path:
    print("== Build wheel and source distribution ==", flush=True)
    _run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--sdist",
            "--outdir",
            str(dist_dir),
        ],
        cwd=REPO_ROOT,
    )
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("FAIL: expected exactly one wheel and one source distribution")
    print(f"Built {wheels[0].name} and {sdists[0].name}", flush=True)
    return wheels[0]


def _assert_clean_dependencies(app_python: Path) -> None:
    probe = "\n".join(
        (
            "import importlib.util",
            "import sys",
            f"names = {list(_FORBIDDEN_MODULES)!r}",
            (
                "present = [name for name in names "
                "if importlib.util.find_spec(name) is not None]"
            ),
            (
                "message = 'unexpected optional/developer modules: ' "
                "+ ', '.join(present) if present else 0"
            ),
            "sys.exit(message)",
        )
    )
    _run([str(app_python), "-c", probe])


def _assert_help(seshat: Path, workspace_parent: Path) -> None:
    help_output = _capture([str(seshat), "--help"], cwd=workspace_parent)
    for token in ("init-project", "status", "next", "check"):
        if token not in help_output:
            raise SystemExit(f"FAIL: seshat --help did not list {token}")


def _create_workspace(seshat: Path, workspace_parent: Path) -> Path:
    workspace = workspace_parent / "my-bi"
    _run([str(seshat), "init-project", str(workspace)], cwd=workspace_parent)
    _run(["git", "init"], cwd=workspace)
    return workspace


def _assert_status(seshat: Path, workspace: Path) -> None:
    status_output = _capture([str(seshat), "status", "--format", "json"], cwd=workspace)
    if json.loads(status_output) != {"tables": []}:
        raise SystemExit(
            f"FAIL: fresh status projection was not empty: {status_output}"
        )
    _assert_truthful(status_output, label="status output")


def _assert_next(seshat: Path, workspace: Path) -> None:
    next_output = _capture([str(seshat), "next", "--format", "agent"], cwd=workspace)
    for token in ("not_started", "next_allowed_action", "evidence", "blocking_reasons"):
        if token not in next_output:
            raise SystemExit(f"FAIL: next --format agent did not include {token}")
    _assert_truthful(next_output, label="next output")


def _assert_demo_proof(seshat: Path, workspace: Path) -> None:
    _run([str(seshat), "demo", "init"], cwd=workspace)
    _run([str(seshat), "demo", "run"], cwd=workspace)
    _run([str(seshat), "demo", "report", "--format", "html"], cwd=workspace)
    proof = workspace / ".seshat-output" / "demo" / "index.html"
    if not proof.is_file():
        raise SystemExit(f"FAIL: demo HTML proof was not generated: {proof}")
    text = proof.read_text(encoding="utf-8")
    for token in (
        "Readiness proof",
        "offline mode",
        "gold_ready",
        "No readiness score",
    ):
        if token not in text:
            raise SystemExit(f"FAIL: demo HTML proof did not include {token!r}")
    _assert_truthful(text, label="demo HTML proof")


def _assert_check_commands(seshat: Path, app_python: Path, workspace: Path) -> None:
    _run([str(seshat), "check"], cwd=workspace)
    _run([str(app_python), "-m", "retail.cli", "check"], cwd=workspace)


def _run_first_success(bin_dir: Path, app_python: Path, workspace_parent: Path) -> None:
    workspace_parent.mkdir()
    seshat = _executable(bin_dir, "seshat")
    _assert_help(seshat, workspace_parent)
    workspace = _create_workspace(seshat, workspace_parent)
    _assert_status(seshat, workspace)
    _assert_next(seshat, workspace)
    _assert_demo_proof(seshat, workspace)
    _assert_check_commands(seshat, app_python, workspace)


def _app_python(pipx_home: Path) -> Path:
    bin_name = "Scripts" if sys.platform == "win32" else "bin"
    python_name = "python.exe" if sys.platform == "win32" else "python"
    return pipx_home / "venvs" / "seshat-bi" / bin_name / python_name


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="seshat-smoke-") as temp:
        root = Path(temp)
        dist_dir = root / "dist"
        pipx_home = root / "pipx-home"
        pipx_bin = root / "pipx-bin"
        os.environ["PIPX_HOME"] = str(pipx_home)
        os.environ["PIPX_BIN_DIR"] = str(pipx_bin)

        wheel = _build_artifacts(dist_dir)
        print("== Install through isolated pipx environment ==", flush=True)
        _run([sys.executable, "-m", "pipx", "install", str(wheel)])
        for script in _CONSOLE_SCRIPTS:
            _executable(pipx_bin, script)

        app_python = _app_python(pipx_home)
        if not app_python.exists():
            raise SystemExit(f"FAIL: pipx app interpreter not found: {app_python}")
        _assert_clean_dependencies(app_python)
        _run_first_success(pipx_bin, app_python, root / "workspace-parent")

    print("PASS: clean public-beta install smoke test succeeded.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
