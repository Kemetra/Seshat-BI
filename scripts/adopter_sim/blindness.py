"""The eight blindness assertions. Each is a hard failure, never a warning.

Package-level isolation (2, 3, 5) proves Python cannot reach the dev tree.
Only assertion 7 proves the AGENT did not arrive carrying the developer's
global rules -- in which case it was never a client at all.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

from scripts.adopter_sim.env import assert_no_credentials
from scripts.adopter_sim.model import AdopterSimError

DEV_ANCESTOR_MARKERS = ("CLAUDE.md", "AGENTS.md", ".git")
LEAK_MARKERS = ("specs/", "src/seshat", "src\\seshat")
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


def _probe(venv_python: Path, code: str) -> str:
    result = subprocess.run(
        [str(venv_python), "-c", code], text=True, capture_output=True
    )
    if result.returncode:
        raise AdopterSimError(
            f"probe failed in {venv_python}: {result.stdout}{result.stderr}"
        )
    return result.stdout.strip()


def assert_outside_repo(workspace: Path, repo_root: Path) -> None:
    """Assertion 1."""
    workspace = workspace.resolve()
    repo_root = repo_root.resolve()
    if workspace == repo_root or repo_root in workspace.parents:
        raise AdopterSimError(
            f"workspace {workspace} is a descendant of REPO_ROOT {repo_root}; "
            "the run would not be blind"
        )
    return None


def assert_installed_seshat(venv_python: Path) -> None:
    """Assertion 2: seshat resolves from site-packages, never src/."""
    location = _probe(venv_python, "import seshat; print(seshat.__file__)")
    if "site-packages" not in location.replace("\\", "/"):
        raise AdopterSimError(f"seshat resolved outside site-packages: {location}")
    return None


def assert_no_dev_modules(venv_python: Path) -> None:
    """Assertion 3."""
    code = (
        "import importlib.util\n"
        f"names = {list(_FORBIDDEN_MODULES)!r}\n"
        "print(','.join(n for n in names "
        "if importlib.util.find_spec(n) is not None))"
    )
    present = [name for name in _probe(venv_python, code).split(",") if name]
    if present:
        raise AdopterSimError(
            f"developer modules resolve in the client venv: {present}"
        )
    return None


def _dirty_ancestor(start: Path, stop_at: Path | None) -> tuple[Path, str] | None:
    """First ancestor at or above `start` holding a dev marker, else None.

    Walks up to but EXCLUDING `stop_at`. A caller passing `stop_at` must have
    proved that boundary clean itself (see `find_clean_root`), otherwise the
    check is only as strong as the boundary.
    """
    boundary = stop_at.resolve() if stop_at is not None else None
    for ancestor in start.resolve().parents:
        if boundary is not None and (
            ancestor == boundary or ancestor in boundary.parents
        ):
            break
        for marker in DEV_ANCESTOR_MARKERS:
            if (ancestor / marker).exists():
                return ancestor, marker
    return None


def assert_no_dev_ancestor(workspace: Path, *, stop_at: Path | None = None) -> None:
    """Assertion 4: no dev CLAUDE.md / AGENTS.md / .git ABOVE the workspace.

    The workspace's own CLAUDE.md and .git are the client's, and expected.
    """
    dirty = _dirty_ancestor(workspace, stop_at)
    if dirty is not None:
        ancestor, marker = dirty
        raise AdopterSimError(
            f"ancestor {ancestor} holds {marker}; the agent would inherit dev "
            "context through the parent chain"
        )
    return None


def find_clean_root(candidates: Sequence[Path]) -> Path:
    """Return the first candidate workspace root with a clean ancestor chain.

    On Windows %TEMP% sits under the user profile, which routinely holds a
    developer CLAUDE.md and .claude/ -- a workspace there inherits dev context
    through the parent chain no matter what else the harness does. Rather than
    excusing that, the harness relocates. If no candidate is clean it fails with
    an actionable instruction instead of running a compromised journey.
    """
    rejected: list[str] = []
    for candidate in candidates:
        dirty = _dirty_ancestor(candidate, None)
        if dirty is None:
            return candidate
        ancestor, marker = dirty
        rejected.append(f"{candidate} (ancestor {ancestor} holds {marker})")
    raise AdopterSimError(
        "no candidate workspace root has a clean ancestor chain: "
        + "; ".join(rejected)
        + ". Set ADOPTER_SIM_ROOT to a directory whose ancestors hold no "
        "CLAUDE.md, AGENTS.md, or .git (a drive root such as C:\\ssim works)."
    )


def assert_no_editable_path(venv_python: Path, repo_root: Path) -> None:
    """Assertion 5: no PYTHONPATH, no editable .pth resolving into the repo."""
    code = (
        "import json, os, sys\n"
        "print(json.dumps({'pythonpath': os.environ.get('PYTHONPATH', ''), "
        "'paths': [p for p in sys.path if p]}))"
    )
    payload = json.loads(_probe(venv_python, code))
    if payload["pythonpath"]:
        raise AdopterSimError(
            f"PYTHONPATH is set in the client venv: {payload['pythonpath']}"
        )
    root = str(repo_root.resolve())
    offenders = [entry for entry in payload["paths"] if root in entry]
    if offenders:
        raise AdopterSimError(
            f"editable install or path entry resolves into REPO_ROOT: {offenders}"
        )
    return None


def assert_profile_isolated(config_dir: Path, bundle_manifest: Path) -> None:
    """Assertion 7: the on-disk profile equals the bundle, and nothing more.

    The inventory is read from disk. It is never obtained by asking the agent:
    the system under test cannot certify its own isolation.
    """
    for marker in ("CLAUDE.md", "AGENTS.md"):
        if (config_dir / marker).is_file():
            raise AdopterSimError(
                f"agent config profile holds a global {marker}; the client "
                "would inherit developer guidance"
            )
    if (config_dir / "rules").exists():
        raise AdopterSimError(
            "agent config profile holds a rules directory; the client would "
            "inherit developer rules"
        )
    try:
        declared = json.loads(bundle_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdopterSimError(
            f"cannot read bundle manifest {bundle_manifest}: {exc}"
        ) from exc
    expected = set(declared.get("skills") or [])
    skills_dir = config_dir / "skills"
    on_disk = (
        {entry.name for entry in skills_dir.iterdir() if entry.is_dir()}
        if skills_dir.is_dir()
        else set()
    )
    extra = sorted(on_disk - expected)
    missing = sorted(expected - on_disk)
    if extra:
        raise AdopterSimError(
            f"agent profile exposes skills outside the bundle manifest: {extra}"
        )
    if missing:
        raise AdopterSimError(f"agent profile is missing bundle skills: {missing}")
    return None


def assert_no_leak(raw_transcript: str, repo_root: Path) -> None:
    """Assertion 8, against the RAW transcript before sanitization.

    Sanitization exists to strip paths, so scanning sanitized text for path
    leaks would pass by construction.
    """
    root = str(repo_root.resolve())
    if root and root in raw_transcript:
        raise AdopterSimError(
            "raw transcript contains REPO_ROOT; the run was not blind"
        )
    for marker in LEAK_MARKERS:
        if marker in raw_transcript:
            raise AdopterSimError(
                f"raw transcript references {marker}; the run was not blind"
            )
    return None


def run_pre_journey_assertions(
    *,
    workspace: Path,
    repo_root: Path,
    venv_python: Path,
    config_dir: Path,
    bundle_manifest: Path,
    client_env: dict[str, str],
) -> None:
    """Assertions 1-7, in order. Any failure aborts the run."""
    assert_outside_repo(workspace, repo_root)
    assert_installed_seshat(venv_python)
    assert_no_dev_modules(venv_python)
    assert_no_dev_ancestor(workspace)  # strict: walks to the filesystem root
    assert_no_editable_path(venv_python, repo_root)
    assert_no_credentials(client_env, repo_root)
    assert_profile_isolated(config_dir, bundle_manifest)
    return None
