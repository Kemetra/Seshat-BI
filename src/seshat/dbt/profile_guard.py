"""The runtime ``profiles.yml`` guard shared by ``dbt doctor`` and planning.

dbt reads the gitignored local ``profiles.yml`` (``--profiles-dir`` is the repo
root), while static validation checks only the committed
``profiles.example.yml`` template. Unless the local file is proven identical to
the template -- and still untracked and gitignored -- a plan or build could
connect with host, user or database literals nobody reviewed. ``dbt doctor``
always ran these checks; :func:`verify_runtime_profile` lets ``create_plan``
(and so plan, build, test and the Dagster dbt bridge) run them too.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from seshat.dbt.runner import DbtUnavailable
from seshat.gitstate import run_git


def pending(message: str) -> DbtUnavailable:
    """The ``[PENDING LIVE PROFILE]`` refusal every dbt prerequisite raises."""
    return DbtUnavailable(f"[PENDING LIVE PROFILE]: {message}")


def _profile_document(path: Path, label: str) -> dict[str, Any]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise pending(f"{label} is missing or invalid") from exc
    if not isinstance(document, dict):
        raise pending(f"{label} must be a YAML mapping")
    return document


def verify_local_profile(root: Path) -> None:
    """``profiles.yml`` exists and equals the governed template exactly."""
    local_profile = root / "profiles.yml"
    if not local_profile.is_file():
        raise pending("copy profiles.example.yml to the gitignored profiles.yml")
    local = _profile_document(local_profile, "profiles.yml")
    governed = _profile_document(root / "profiles.example.yml", "profiles.example.yml")
    if local != governed:
        raise pending("profiles.yml must match the exact governed template")


def _profile_git_result(root: Path, *args: str) -> int:
    # `root` is a user-supplied `--repo`: the shared hardened wrapper carries
    # the full untrusted-tree set plus safe.directory, stdin=DEVNULL and a
    # timeout.
    return run_git(root, *args, "--", "profiles.yml").returncode


def verify_profile_git_boundary(root: Path) -> None:
    """``profiles.yml`` is gitignored and untracked."""
    ignored = _profile_git_result(root, "check-ignore", "--quiet")
    tracked = _profile_git_result(root, "ls-files", "--error-unmatch")
    if (ignored, tracked) != (0, 1):
        raise pending("profiles.yml must remain untracked and gitignored")


def verify_runtime_profile(root: Path) -> None:
    """Both profile checks, in the order ``dbt doctor`` runs them."""
    verify_local_profile(root)
    verify_profile_git_boundary(root)
