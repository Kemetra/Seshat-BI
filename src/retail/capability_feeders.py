"""Feeder readers for the capability inventory (spec 118).

Each function reads ONE existing committed source and returns the plain facts
it owns -- never the builder's own manifest. Driver-free: stdlib + the in-repo
YAML reader only (mirrors ``status_surface.py`` / ``run_next.py``). Every
reader is READ-ONLY and best-effort: a missing or malformed feeder file
returns an empty/None result rather than raising, so an empty drop-in repo
(no ``.seshat/``, no ``.claude/skills/``, no dispatch table) composes cleanly
instead of crashing (data-model.md edge case, FR-002).

Nothing here writes a file, opens a database connection, or imports a DB
driver at module scope.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import NamedTuple


class SkillFact(NamedTuple):
    """One repo skill's declared frontmatter facts."""

    name: str
    description: str


def _load_yaml_mapping(path: Path) -> dict | None:
    import yaml  # lazy: keep this module's import path stdlib-light

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def read_rule_titles(repo_root: Path) -> dict[str, str]:
    """Read ``{rule_id: title}`` from ``docs/rules/rules-manifest.json``."""
    path = repo_root / "docs" / "rules" / "rules-manifest.json"
    try:
        raw = path.read_text(encoding="utf-8-sig")
        data = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(data, list):
        return {}
    return {
        row["id"]: row["title"]
        for row in data
        if isinstance(row, dict)
        and isinstance(row.get("id"), str)
        and isinstance(row.get("title"), str)
    }


def _name_from_fence_line(fence: str) -> str | None:
    """Fallback extraction of a bare ``name: <value>`` line when the fence
    does not parse as strict YAML (e.g. an unquoted multi-sentence
    ``description`` containing a bare colon-space, which some committed
    SKILL.md files carry). ``name`` is always a simple single-line token in
    every shipped skill, so a targeted line scan is a safe, honest fallback
    -- it does NOT invent a description, it only recovers the identity."""
    for line in fence.splitlines():
        stripped = line.strip()
        if stripped.startswith("name:"):
            value = stripped[len("name:") :].strip().strip('"').strip("'")
            return value or None
    return None


def _parse_frontmatter(text: str) -> dict[str, str] | None:
    """Parse a minimal ``name``/``description`` pair out of a SKILL.md's
    YAML frontmatter fence. Returns ``None`` if the file has no frontmatter
    fence at all (a bare/undeclared file, per FR-002) or no usable name.

    A frontmatter fence that fails STRICT YAML parsing (some committed
    SKILL.md files carry an unquoted ``description`` with a bare
    colon-space, which is invalid as a YAML plain scalar) still declares a
    ``name`` -- recovered via ``_name_from_fence_line`` -- because the fence
    existing with a stated name IS the declaring metadata FR-002 requires;
    only a fence-less file is inadmissible."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fence = text[3:end]
    import yaml

    try:
        data = yaml.safe_load(fence)
    except yaml.YAMLError:
        data = None
    if isinstance(data, dict):
        name = data.get("name")
        description = data.get("description")
    else:
        name = _name_from_fence_line(fence)
        description = None
    if not isinstance(name, str) or not name.strip():
        return None
    return {
        "name": name.strip().strip('"'),
        "description": description if isinstance(description, str) else "",
    }


def read_skill_facts(repo_root: Path) -> dict[str, SkillFact]:
    """Read ``{skill_name: SkillFact}`` for every REPO skill: a
    ``.claude/skills/*/SKILL.md`` carrying a declaring frontmatter fence
    (``name`` + ``description``). A bare/frontmatter-less ``SKILL.md`` is NOT
    admissible evidence (FR-002) and is excluded, not merely unresolved."""
    skills_dir = repo_root / ".claude" / "skills"
    facts: dict[str, SkillFact] = {}
    if not skills_dir.is_dir():
        return facts
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        try:
            text = skill_md.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        parsed = _parse_frontmatter(text)
        if parsed is None:
            continue
        facts[parsed["name"]] = SkillFact(
            name=parsed["name"], description=parsed["description"]
        )
    return facts


def _id_set_from_yaml_list(
    repo_root: Path, rel_path: str, list_key: str, predicate=None
) -> set[str]:
    """Shared shape behind every 'read a YAML file, pull ``id`` out of a
    named list, keep rows matching an optional predicate' feeder -- kit-source
    verbs, parked-on edges, and (via ``predicate``) status-claims built rows
    all reduce to this one join."""
    data = _load_yaml_mapping(repo_root / rel_path)
    if data is None:
        return set()
    rows = data.get(list_key)
    if not isinstance(rows, list):
        return set()
    return {
        row["id"]
        for row in rows
        if isinstance(row, dict)
        and isinstance(row.get("id"), str)
        and (predicate is None or predicate(row))
    }


def read_kit_source_verbs(repo_root: Path) -> set[str]:
    """Read the verb ``id`` set from ``.seshat/kit-source.yaml``."""
    return _id_set_from_yaml_list(repo_root, ".seshat/kit-source.yaml", "verbs")


def _dispatch_assignment(tree: ast.Module) -> ast.Dict | None:
    """Find the ``_DISPATCH: dict = {...}`` module-level annotated assignment
    and return its dict literal node, or ``None`` if absent/not a literal."""
    for node in ast.walk(tree):
        target = getattr(node, "target", None)
        is_dispatch = (
            isinstance(node, ast.AnnAssign)
            and isinstance(target, ast.Name)
            and target.id == "_DISPATCH"
        )
        if is_dispatch and isinstance(node.value, ast.Dict):
            return node.value
    return None


def read_dispatch_keys(repo_root: Path) -> set[str]:
    """Read the ``_DISPATCH`` key set from ``src/retail/cli/__init__.py`` via
    stdlib ``ast`` -- NEVER by importing the module (keeps this reader
    driver-free and avoids loading any lazily-imported command handler)."""
    path = repo_root / "src" / "retail" / "cli" / "__init__.py"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return set()
    dispatch_dict = _dispatch_assignment(tree)
    if dispatch_dict is None:
        return set()
    return {
        key.value
        for key in dispatch_dict.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }


def read_roadmap_text(repo_root: Path) -> str:
    """Read the raw text of ``docs/roadmap/roadmap.md`` (empty string if
    absent) -- the caller checks feature-id + SHIPPED proximity itself."""
    path = repo_root / "docs" / "roadmap" / "roadmap.md"
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return ""


def read_status_claims_built(repo_root: Path) -> set[str]:
    """Read the set of status-claims ``id``s whose ``claimed-status`` is
    ``built`` from ``docs/quality/status-claims.yaml``."""
    return _id_set_from_yaml_list(
        repo_root,
        "docs/quality/status-claims.yaml",
        "claims",
        predicate=lambda row: row.get("claimed-status") == "built",
    )


def read_parked_on_ids(repo_root: Path) -> set[str]:
    """Read the edge ``id`` set from ``docs/quality/parked-on.yaml``."""
    return _id_set_from_yaml_list(repo_root, "docs/quality/parked-on.yaml", "edges")


def read_valid_readiness_stages(repo_root: Path) -> set[str]:
    """Read the valid ``stages.*`` key set from the single canonical source,
    ``templates/readiness-status.yaml`` (research D5)."""
    data = _load_yaml_mapping(repo_root / "templates" / "readiness-status.yaml")
    if data is None:
        return set()
    stages = data.get("stages")
    if not isinstance(stages, dict):
        return set()
    return {key for key in stages if isinstance(key, str)}
