"""Component declarations read from a plugin's own ``.claude-plugin/plugin.json``.

Claude Code honours the component fields of ``plugin.json`` (``commands``,
``agents``, ``skills``, ``hooks`` and ``mcpServers``) IN ADDITION to the default
directories. A closed-world firewall that only walks the default directories is
therefore fail-open: an inline hook or a custom command path would be active
while observation reports nothing. This module turns those fields into extra
enumeration roots, contained inside the plugin directory, and reports every key
it does not recognise so the comparison can fail closed on it.

Nothing here executes a plugin or reaches a network.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

PLUGIN_MANIFEST = Path(".claude-plugin") / "plugin.json"

# Descriptive keys that declare no capability.
METADATA_KEYS = frozenset(
    {
        "$schema",
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
        "category",
        "tags",
    }
)

# Capability classes this firewall enumerates. Any other key -- including real
# but unreviewed classes such as output styles or LSP servers -- is unknown.
COMPONENT_KEYS = frozenset({"commands", "agents", "skills", "hooks", "mcpServers"})

# The pseudo-key reported when plugin.json exists but cannot be read.
UNREADABLE = "<unreadable plugin.json>"


class InvalidDeclaration(ValueError):
    """A component declaration that cannot be enumerated safely."""


def read_manifest(root: Path) -> dict | None:
    """The parsed plugin.json: ``{}`` when absent, ``None`` when unreadable."""
    path = root / PLUGIN_MANIFEST
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def declarations(
    root: Path, extra: Mapping[str, object] | None = None
) -> tuple[dict[str, object], frozenset[str]]:
    """``(component declarations, unknown keys)`` for the plugin at ``root``.

    ``extra`` carries component fields declared OUTSIDE plugin.json -- a
    marketplace entry may declare them too -- and is merged in. A key declared
    in both places with different values is ambiguous and reported unknown.
    """
    manifest = read_manifest(root)
    if manifest is None:
        return {}, frozenset({UNREADABLE})
    unknown = {key for key in manifest if key not in METADATA_KEYS | COMPONENT_KEYS}
    declared = {key: manifest[key] for key in COMPONENT_KEYS if key in manifest}
    for key, value in (extra or {}).items():
        if key not in COMPONENT_KEYS:
            continue
        if key in declared and declared[key] != value:
            unknown.add(key)
            continue
        declared[key] = value
    return declared, frozenset(unknown)


def declared_paths(root: Path, value: object) -> tuple[Path, ...]:
    """Contained paths from a ``str`` or ``list[str]`` declaration.

    Raises :class:`InvalidDeclaration` for any other shape, a blank entry, or a
    path that resolves outside ``root`` (symlinks included).
    """
    entries = [value] if isinstance(value, str) else value
    if not isinstance(entries, list):
        raise InvalidDeclaration
    base = root.resolve()
    paths: list[Path] = []
    for entry in entries:
        if not isinstance(entry, str) or not entry.strip():
            raise InvalidDeclaration
        candidate = (root / entry).resolve()
        if not candidate.is_relative_to(base) or not candidate.exists():
            raise InvalidDeclaration
        paths.append(candidate)
    return tuple(paths)


def markdown_names(path: Path) -> frozenset[str]:
    """Command/agent names under ``path``: one ``.md`` file, or a directory of them.

    A directory is walked recursively (commands may be namespaced in
    subdirectories); any non-markdown file makes it unenumerable.
    """
    if path.is_file():
        if path.suffix.lower() != ".md":
            raise InvalidDeclaration
        return frozenset({path.stem})
    names: set[str] = set()
    try:
        children = sorted(path.rglob("*"))
    except OSError as exc:
        raise InvalidDeclaration from exc
    for child in children:
        if child.is_dir():
            continue
        if child.suffix.lower() != ".md":
            raise InvalidDeclaration
        names.add(child.relative_to(path).with_suffix("").as_posix())
    return frozenset(names)


def skill_names(path: Path) -> frozenset[str]:
    """Skill names under ``path``: a skill directory, or a directory of them."""
    if (path / "SKILL.md").is_file():
        return frozenset({path.name})
    if not path.is_dir():
        raise InvalidDeclaration
    names: set[str] = set()
    for child in path.iterdir():
        if not child.is_dir() or not (child / "SKILL.md").is_file():
            raise InvalidDeclaration
        names.add(child.name)
    return frozenset(names)


def inline_hook_events(value: dict) -> dict:
    """The event map of an inline ``hooks`` object, in either accepted shape.

    Both ``{"PreToolUse": [...]}`` and the ``hooks.json`` shape
    ``{"hooks": {"PreToolUse": [...]}}`` are accepted.
    """
    nested = value.get("hooks")
    if isinstance(nested, dict):
        return nested
    return value
