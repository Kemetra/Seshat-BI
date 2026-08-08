"""Direct feeder readers shared by the capability oracle modules (spec 118/143).

The leaf of the oracle's three-tier layering: this module reads feeder sources
and depends on no other oracle module, ``_capability_public_ownership`` builds
the spec-143 ownership detectors on top of it, and ``_capability_oracle``
imports from both. Splitting the shared readers out is what keeps that stack
acyclic -- ``load_shipped_public_skills`` is needed by BOTH the ship-signal
checks in the parent and the ownership detectors in the sibling, so it can live
in neither of them.

ANTI-CIRCULARITY (load-bearing, repo lesson ``verifier-must-sit-on-the-risk``):
like every oracle module, this one reads the FEEDER sources DIRECTLY and
re-implements every reader. It MUST NOT import ``seshat.capability_feeders`` or
``seshat.capability_inventory`` -- an oracle that learns what a feeder says by
calling the code under test would pass vacuously on a builder bug that hides
drift on both sides. ``test_oracle_does_not_import_code_under_test`` asserts
this property across every module in the oracle stack, this one included.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml


def load_manifest(repo_root: Path) -> list[dict]:
    path = repo_root / "docs" / "capabilities" / "capabilities.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    return data.get("capabilities", []) if isinstance(data, dict) else []


def as_list(value: object) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def load_shipped_public_skills(repo_root: Path) -> set[str]:
    path = repo_root / "distribution" / "public-command-surface.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    skills = data.get("skills", []) if isinstance(data, dict) else []
    return {
        str(skill["name"])
        for skill in skills
        if isinstance(skill, dict)
        and skill.get("status") == "shipped"
        and isinstance(skill.get("name"), str)
        and skill["name"].strip()
    }


def _reference_values(entry: dict, key: str) -> list[str]:
    references = entry.get("references")
    if not isinstance(references, dict):
        return []
    value = references.get(key)
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _git_tracked_files(repo_root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    return {
        item.decode("utf-8", errors="surrogateescape")
        for item in result.stdout.split(b"\0")
        if item
    }
