"""Semantic model diff: classify TMDL changes into reviewer-readable buckets.

Pure function over ``(path, text)`` pairs from both sides -- the CLI pulls the
base side from ``git show``; nothing here touches git or the filesystem.

Buckets: ``semantic`` (meaning changed), ``cosmetic`` (presentation only),
``additive`` (new object), ``removed`` (object gone). Table matching is by
table NAME; a renamed table is reported as removed + additive (rename
detection is deliberately out of scope). Relationships are matched by their
ENDPOINT tuple, never by name: TMDL relationship names are GUIDs that churn.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from ..tmdl import (
    TmdlRelationship,
    TmdlTable,
    normalize_measure_body,
    parse_relationships,
    parse_tmdl,
)

_REF = re.compile(r"(?:'(?:[^']|'')*'|[A-Za-z_][\w ]*?)\[[^\]]+\]")
_ROLE_HEADER = re.compile(r"^role\s+('?)(?P<name>[^'\n]+?)\1\s*$")


def _role_name(raw: str) -> str | None:
    """The role name if ``raw`` is a top-level ``role <name>`` header, else None."""
    if raw[:1].isspace():
        return None
    match = _ROLE_HEADER.match(raw.strip())
    return match.group("name").strip() if match else None


def _block_body(lines: list[str], start: int) -> str:
    """The indented body following the top-level header at ``start``."""
    body: list[str] = []
    for follower in lines[start + 1 :]:
        if follower.strip() and not follower[:1].isspace():
            break  # next top-level block
        body.append(follower.strip())
    return "\n".join(body)


def _parse_roles(text: str) -> dict[str, str]:
    """Top-level ``role <name>`` blocks -> normalized body text.

    RLS lives in ``definition/roles/*.tmdl``, which is neither a table file nor
    a relationship block, so without this the diff stayed silent on a changed
    security filter -- the one change class the design calls out as semantic
    (PR #550 review). Bodies are normalized with the same comment-stripping
    whitespace canonicalizer used for measures, so reformatting a filter is
    not reported as a behavior change.
    """
    lines = text.splitlines()
    return {
        name: normalize_measure_body(_block_body(lines, i))
        for i, raw in enumerate(lines)
        if (name := _role_name(raw)) is not None
    }


@dataclass(frozen=True)
class ModelChange:
    bucket: str  # "semantic" | "cosmetic" | "additive" | "removed"
    kind: str  # "measure" | "column" | "relationship" | "table" | "role"
    subject: str  # "Sales[Revenue]" style locator
    sentence: str  # one business-terms line, ASCII only


@dataclass(frozen=True)
class _Side:
    """One side of the diff: tables by name, relationships by endpoint, roles."""

    tables: dict[str, TmdlTable]
    relationships: dict[tuple, TmdlRelationship]
    roles: dict[str, str]


def _parse_side(files: Iterable[tuple[str, str]]) -> _Side:
    tables: dict[str, TmdlTable] = {}
    rels: dict[tuple, TmdlRelationship] = {}
    roles: dict[str, str] = {}
    for path, text in files:
        if "/definition/tables/" in path and path.endswith(".tmdl"):
            parsed = parse_tmdl(text)
            if parsed is not None:
                tables[parsed.name] = parsed
        for rel in parse_relationships(text):
            key = (rel.from_table, rel.from_column, rel.to_table, rel.to_column)
            rels[key] = rel
        roles.update(_parse_roles(text))
    return _Side(tables=tables, relationships=rels, roles=roles)


def _diff_roles(base: dict[str, str], head: dict[str, str]) -> Iterable[ModelChange]:
    """Every RLS role change is semantic (or an outright add/remove)."""
    for name in sorted(base.keys() | head.keys()):
        old, new = base.get(name), head.get(name)
        if old is None:
            yield ModelChange(
                "additive", "role", name, f"new security role {name!r} added"
            )
        elif new is None:
            yield ModelChange(
                "removed", "role", name, f"security role {name!r} removed"
            )
        elif old != new:
            yield ModelChange(
                "semantic",
                "role",
                name,
                f"security role {name!r} filter changed -- row visibility "
                "differs for its members",
            )


def _references(expression: str) -> str:
    refs = sorted(set(_REF.findall(expression)))
    return ", ".join(refs) if refs else "no model fields"


def _diff_measures(base: TmdlTable, head: TmdlTable) -> Iterable[ModelChange]:
    base_measures = {m.name: m for m in base.measures}
    head_measures = {m.name: m for m in head.measures}
    for name in sorted(base_measures.keys() | head_measures.keys()):
        subject = f"{head.name}[{name}]"
        old, new = base_measures.get(name), head_measures.get(name)
        if old is None:
            yield ModelChange(
                "additive",
                "measure",
                subject,
                f"new measure {name!r} referencing {_references(new.expression)}",
            )
        elif new is None:
            yield ModelChange(
                "removed", "measure", subject, f"measure {name!r} removed"
            )
        elif normalize_measure_body(old.expression) != normalize_measure_body(
            new.expression
        ):
            yield ModelChange(
                "semantic",
                "measure",
                subject,
                f"measure {name!r} logic changed (normalized bodies differ)",
            )
        elif (old.format_string, old.description, old.display_folder) != (
            new.format_string,
            new.description,
            new.display_folder,
        ):
            yield ModelChange(
                "cosmetic",
                "measure",
                subject,
                f"measure {name!r} presentation changed (format/description/folder)",
            )


def _diff_columns(base: TmdlTable, head: TmdlTable) -> Iterable[ModelChange]:
    base_columns = {c.name: c for c in base.columns}
    head_columns = {c.name: c for c in head.columns}
    for name in sorted(base_columns.keys() | head_columns.keys()):
        subject = f"{head.name}[{name}]"
        old, new = base_columns.get(name), head_columns.get(name)
        if old is None:
            yield ModelChange("additive", "column", subject, f"new column {name!r}")
        elif new is None:
            yield ModelChange("removed", "column", subject, f"column {name!r} removed")
        elif old.data_type != new.data_type:
            yield ModelChange(
                "semantic",
                "column",
                subject,
                f"column {name!r} type changed: {old.data_type} -> {new.data_type}",
            )
        elif (old.summarize_by, old.sort_by_column, old.is_hidden) != (
            new.summarize_by,
            new.sort_by_column,
            new.is_hidden,
        ):
            yield ModelChange(
                "cosmetic",
                "column",
                subject,
                f"column {name!r} presentation changed (summarize/sort/hidden)",
            )


def _rel_semantics(rel: TmdlRelationship) -> tuple:
    return (
        rel.is_active,
        rel.from_cardinality,
        rel.to_cardinality,
        rel.cross_filtering_behavior,
    )


def _rel_subject(key: tuple) -> str:
    return f"{key[0]}[{key[1]}] -> {key[2]}[{key[3]}]"


def _diff_relationships(base_rels: dict, head_rels: dict) -> Iterable[ModelChange]:
    for key in sorted(base_rels.keys() | head_rels.keys(), key=str):
        subject = _rel_subject(key)
        old, new = base_rels.get(key), head_rels.get(key)
        if old is None:
            yield ModelChange(
                "additive", "relationship", subject, f"new relationship {subject}"
            )
        elif new is None:
            yield ModelChange(
                "removed", "relationship", subject, f"relationship {subject} removed"
            )
        elif _rel_semantics(old) != _rel_semantics(new):
            yield ModelChange(
                "semantic",
                "relationship",
                subject,
                f"relationship {subject} behavior changed "
                "(activity/cardinality/filter direction)",
            )


def _diff_tables(
    base_tables: dict[str, TmdlTable], head_tables: dict[str, TmdlTable]
) -> Iterable[ModelChange]:
    for name in sorted(base_tables.keys() | head_tables.keys()):
        if name not in head_tables:
            yield ModelChange("removed", "table", name, f"table {name!r} removed")
        elif name not in base_tables:
            head = head_tables[name]
            yield ModelChange(
                "additive",
                "table",
                name,
                f"new table {name!r} ({len(head.columns)} columns, "
                f"{len(head.measures)} measures)",
            )


def diff_models(
    base_files: Iterable[tuple[str, str]],
    head_files: Iterable[tuple[str, str]],
) -> tuple[ModelChange, ...]:
    """Classify every model change between the two sides, in stable order."""
    base, head = _parse_side(base_files), _parse_side(head_files)
    changes: list[ModelChange] = []
    changes.extend(_diff_tables(base.tables, head.tables))
    for name in sorted(base.tables.keys() & head.tables.keys()):
        changes.extend(_diff_measures(base.tables[name], head.tables[name]))
        changes.extend(_diff_columns(base.tables[name], head.tables[name]))
    changes.extend(_diff_relationships(base.relationships, head.relationships))
    changes.extend(_diff_roles(base.roles, head.roles))
    return tuple(changes)
