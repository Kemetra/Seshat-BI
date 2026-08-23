"""Shared read-only traversal for committed YAML documents.

DL10 and DL11 both walk a loaded YAML tree looking for keys, and each had grown its
own recursive dict/list pair. One walker, expressed as a flat generator over
(key, value) pairs, keeps that nesting in a single place and lets each rule express
its question as a filter rather than a traversal.

Read-only and stdlib-only at module scope: ``yaml`` is imported lazily inside
``read`` so the retail-check core import chain stays stdlib-only (B1/B3).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


@dataclass(frozen=True)
class Document:
    """A parse attempt: the tree, plus whether reading it actually succeeded.

    ``failed`` is the whole point. An unparseable file and an empty one both carry
    ``data=None``, and a rule that cannot tell them apart treats an UNEXAMINED file
    as a clean one -- silence that the coverage census still counts as "evaluated".
    Callers that guard a corpus must report the failure instead of skipping the file.
    """

    data: Any
    failed: bool


def read(path: Path) -> Document:
    """Parse a committed YAML file, reporting whether the parse succeeded.

    A legitimately empty document is ``Document(None, failed=False)``; an unreadable
    or malformed one is ``Document(None, failed=True)``, so a rule can emit an error
    for the file it could not examine rather than passing it in silence.
    """
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope

    try:
        with path.open(encoding="utf-8-sig") as handle:
            return Document(yaml.safe_load(handle), failed=False)
    except (OSError, yaml.YAMLError):
        return Document(None, failed=True)


def load(path: Path) -> Any:
    """The parsed tree only, discarding parse status.

    Retained for callers that genuinely do not guard the file (an optional lookup
    where absence and emptiness mean the same thing). A rule whose silence would be
    read as a pass must use ``read`` and report ``failed``.
    """
    return read(path).data


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
