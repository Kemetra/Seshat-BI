"""Materialize the tracked seed into a throwaway workspace outside REPO_ROOT.

Two constraints shape this module:

* Windows has a 260-char path limit and the run nests root -> run-id -> venv ->
  site-packages -> bundle -> skill paths, which is exactly the shape that trips
  it. Hence the short prefix and the asserted budget.
* %TEMP% sits under the user profile, which on a developer machine holds a
  CLAUDE.md and .claude/. A workspace there inherits dev context through the
  parent chain, so the root is chosen by `find_clean_root`, not assumed.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from scripts.adopter_sim.blindness import declared_bundle_skills, find_clean_root
from scripts.adopter_sim.model import AdopterSimError

MAX_WORKSPACE_PATH = 120
RUN_ID_LENGTH = 8
ROOT_ENV_VAR = "ADOPTER_SIM_ROOT"
_DIR_NAME = "ssim"


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    venv_python: Path
    venv_bin: Path
    config_dir: Path
    data_dir: Path


def new_run_id(seed: str) -> str:
    """Deterministic short id.

    Deterministic on purpose: a random id makes a failed run impossible to
    reproduce.
    """
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return digest[:RUN_ID_LENGTH]


def root_candidates() -> tuple[Path, ...]:
    """Candidate workspace roots, most-preferred first.

    An explicit ADOPTER_SIM_ROOT wins. Otherwise a drive/filesystem root is
    preferred over %TEMP%, because %TEMP% under a user profile usually fails the
    clean-ancestor requirement.
    """
    candidates: list[Path] = []
    explicit = os.environ.get(ROOT_ENV_VAR)
    if explicit:
        candidates.append(Path(explicit))
    anchor = Path(tempfile.gettempdir()).resolve().anchor
    if anchor:
        candidates.append(Path(anchor) / _DIR_NAME)
    candidates.append(Path(tempfile.gettempdir()) / _DIR_NAME)
    return tuple(candidates)


def resolve_root() -> Path:
    """The first candidate root with a provably clean ancestor chain."""
    return find_clean_root(root_candidates())


def workspace_root(parent: Path, run_id: str) -> Path:
    """A workspace directory under `parent`.

    `parent` is expected to already be a `ssim`-style root (see resolve_root);
    when a bare temp dir is passed the `ssim` segment is added.
    """
    if parent.name == _DIR_NAME:
        return parent / run_id
    return parent / _DIR_NAME / run_id


def assert_path_budget(workspace: Path) -> None:
    if len(str(workspace)) > MAX_WORKSPACE_PATH:
        raise AdopterSimError(
            f"workspace path exceeds the {MAX_WORKSPACE_PATH}-char path budget "
            f"({len(str(workspace))} chars): {workspace}. Nested venv and bundle "
            "paths would breach the Windows 260-char limit."
        )
    return None


def _venv_paths(root: Path) -> tuple[Path, Path]:
    bin_name = "Scripts" if sys.platform == "win32" else "bin"
    python_name = "python.exe" if sys.platform == "win32" else "python"
    venv_bin = root / ".venv" / bin_name
    return venv_bin, venv_bin / python_name


def materialize(
    *,
    workspace: Path,
    wheel: Path,
    seed_dir: Path,
    dataset: str,
    bundle_root: Path,
) -> WorkspacePaths:
    """Create the workspace, install the wheel, copy only the shipped surface."""
    assert_path_budget(workspace)
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    (workspace / ".tmp").mkdir()

    venv_bin, venv_python = _venv_paths(workspace)
    _run([sys.executable, "-m", "venv", str(workspace / ".venv")])
    _run([str(venv_python), "-m", "pip", "install", "--quiet", str(wheel)])

    data_dir = workspace / "data"
    data_dir.mkdir()
    shutil.copy2(
        seed_dir / "datasets" / dataset / "orders.csv", data_dir / "orders.csv"
    )
    shutil.copy2(seed_dir / "CLIENT-RULES.md", workspace / "CLAUDE.md")

    config_dir = workspace / ".agent"
    config_dir.mkdir()
    copy_bundle(bundle_root, config_dir)

    _run(["git", "init", "--quiet"], cwd=workspace)
    return WorkspacePaths(
        root=workspace,
        venv_python=venv_python,
        venv_bin=venv_bin,
        config_dir=config_dir,
        data_dir=data_dir,
    )


def copy_bundle(bundle_root: Path, config_dir: Path) -> None:
    """Copy exactly the skills the bundle manifest declares, and nothing else."""
    manifest_path = bundle_root / "bundle-manifest.json"
    skills = sorted(declared_bundle_skills(manifest_path))
    target = config_dir / "skills"
    target.mkdir(exist_ok=True)
    for name in skills:
        source = bundle_root / "skills" / name
        if not source.is_dir():
            raise AdopterSimError(
                f"bundle manifest declares skill {name!r} but {source} is absent"
            )
        shutil.copytree(source, target / name, dirs_exist_ok=True)
    shutil.copy2(manifest_path, config_dir / "bundle-manifest.json")
    return None


def _run(command: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(
        command, cwd=str(cwd) if cwd else None, text=True, capture_output=True
    )
    if result.returncode:
        raise AdopterSimError(
            f"command failed ({' '.join(command)}):\n{result.stdout}{result.stderr}"
        )
    return None
