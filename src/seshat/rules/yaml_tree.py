"""Shared read-only traversal for committed YAML documents.

DL10 and DL11 both walk a loaded YAML tree looking for keys, and each had grown its
own recursive dict/list pair. One walker, expressed as a flat generator over
(key, value) pairs, keeps that nesting in a single place and lets each rule express
its question as a filter rather than a traversal.

Read-only and stdlib-only at module scope: ``yaml`` is imported lazily inside
``load`` so the retail-check core import chain stays stdlib-only (B1/B3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator


def load(path: Path) -> Any:
    """Parse a committed YAML file, or ``None`` if it cannot be read or parsed.

    Fail-soft on purpose: a rule that cannot read a file reports nothing for it and
    lets the coverage census record the gap, rather than crashing a check run.
    """
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope

    try:
        with path.open(encoding="utf-8-sig") as handle:
            return yaml.safe_load(handle)
    except (OSError, yaml.YAMLError):
        return None


def _mapping_pairs(node: dict[Any, Any]) -> Iterator[tuple[str, Any]]:
    for key, value in node.items():
        yield str(key), value
        yield from pairs(value)


def _sequence_pairs(node: list[Any]) -> Iterator[tuple[str, Any]]:
    for item in node:
        yield from pairs(item)


def pairs(node: Any) -> Iterator[tuple[str, Any]]:
    """Every ``(key, value)`` in the tree, at any depth, mappings and lists alike."""
    if isinstance(node, dict):
        return _mapping_pairs(node)
    if isinstance(node, list):
        return _sequence_pairs(node)
    return iter(())


def values_for(node: Any, *keys: str) -> Iterator[Any]:
    """Every value stored under any of ``keys``, at any depth."""
    wanted = frozenset(keys)
    return (value for key, value in pairs(node) if key in wanted)


def strings_for(node: Any, *keys: str) -> Iterator[str]:
    """``values_for`` narrowed to non-empty strings, stripped."""
    for value in values_for(node, *keys):
        if isinstance(value, str) and value.strip():
            yield value.strip()


def first_value(node: Any, key: str) -> Any:
    """The first value stored under ``key`` at any depth, else ``None``.

    Used to find a declaration that may sit inside a named profile rather than at
    the document root.
    """
    return next(values_for(node, key), None)
