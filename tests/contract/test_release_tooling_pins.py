"""The tooling that builds and checks published artifacts is pinned.

The wheel PyPI receives is produced by the build backend and frontend that are
installed at dispatch time. Floating either lets a new (or compromised) release
change what ships -- and lets the pre-tag inspection build and the tag build use
different tools. The backend is pinned exactly in ``[build-system]``; ``build``
and ``twine`` (and their closure) are installed only from a hash-locked file.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / ".github/release-tooling/requirements.txt"
SOURCE = ROOT / ".github/release-tooling/requirements.in"
RELEASE_WORKFLOWS = (
    ROOT / ".github/workflows/release.yml",
    ROOT / ".github/workflows/prepare-coordinated-release.yml",
)
_EXACT = re.compile(r"^[A-Za-z0-9_.-]+==[0-9][^\s;]*$")


def _locked_requirements() -> dict[str, str]:
    """``{name: version}`` for every requirement line in the hash-locked file,
    asserting each carries at least one sha256 hash."""
    text = LOCK.read_text(encoding="utf-8")
    entries = re.split(r"\n(?=[A-Za-z0-9])", text.split("\n", 1)[1])
    locked: dict[str, str] = {}
    for entry in entries:
        head = entry.split("\\", 1)[0].split(";", 1)[0].strip()
        if not head or head.startswith("#"):
            continue
        assert _EXACT.match(head), f"not an exact pin: {head!r}"
        assert "--hash=sha256:" in entry, f"no hash for {head!r}"
        name, version = head.split("==", 1)
        locked[name.lower()] = version
    return locked


def test_build_backend_is_pinned_exactly() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requires = pyproject["build-system"]["requires"]
    assert requires, "build-system.requires is empty"
    for requirement in requires:
        assert _EXACT.match(requirement), f"floating build requirement: {requirement}"


def test_release_tooling_lock_is_exact_and_hashed_and_matches_its_source() -> None:
    locked = _locked_requirements()
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        assert _EXACT.match(line), f"requirements.in must pin exactly: {line!r}"
        name, version = line.split("==", 1)
        assert locked.get(name.lower()) == version, name


@pytest.mark.parametrize("workflow", RELEASE_WORKFLOWS, ids=lambda p: p.name)
def test_release_workflows_install_build_tooling_only_from_the_lock(
    workflow: Path,
) -> None:
    text = workflow.read_text(encoding="utf-8")
    installs = [
        line.replace("\\\n", " ")
        for line in re.findall(r"pip install ((?:[^\n]*\\\n)*[^\n]*)", text)
    ]
    assert any(
        "--require-hashes" in line
        and "-r .github/release-tooling/requirements.txt" in line
        for line in installs
    ), workflow.name
    for line in installs:
        if "--require-hashes" in line:
            continue
        tokens = set(line.split())
        assert not tokens & {"build", "twine", "hatchling"}, (workflow.name, line)


def _first_index(steps: list[dict], matches) -> int | None:
    return next((i for i, step in enumerate(steps) if matches(step)), None)


def _wheel_building_jobs(workflow: Path) -> list[tuple[str, list[dict], int]]:
    """``(job, steps, build_index)`` for EVERY job step running ``python -m build``.

    All of them, not the first: a second wheel-building job must be held to the same
    frontend-first order, or it could ship the missing-assets wheel unguarded.
    """
    import yaml

    document = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    found = [
        (name, job.get("steps", []), index)
        for name, job in document["jobs"].items()
        for index, step in enumerate(job.get("steps", []))
        if "python -m build" in str(step.get("run", ""))
    ]
    assert found, f"{workflow.name} never runs `python -m build`"
    return found


@pytest.mark.parametrize("workflow", RELEASE_WORKFLOWS, ids=lambda p: p.name)
def test_every_wheel_build_builds_the_studio_frontend_first(workflow: Path) -> None:
    """The inspector requires `seshat/studio/static/` in the wheel (f71776e9).

    That directory is gitignored build output, so ANY workflow that builds a wheel and
    then runs `inspect_release_artifacts.py` must build the frontend before it, with
    Node available. release.yml did; prepare-coordinated-release.yml did not, so the
    v3.0.0 dispatch (run 36621668968) blocked on "wheel is missing required package
    data" -- a latent break since the inspector began deriving its required files.
    """
    for job, steps, build in _wheel_building_jobs(workflow):
        frontend = _first_index(
            steps, lambda s: "scripts/build_studio_frontend.py" in str(s.get("run", ""))
        )
        node = _first_index(
            steps, lambda s: str(s.get("uses", "")).startswith("actions/setup-node@")
        )
        where = f"{workflow.name} job {job!r}"
        assert frontend is not None and frontend < build, (
            f"{where} builds a wheel without building the Studio frontend first"
        )
        # Node must precede the step that NEEDS it, not merely the wheel build.
        assert node is not None and node < frontend, (
            f"{where} builds the Studio frontend without setting up Node first"
        )
