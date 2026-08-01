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


@dataclass(frozen=True)
class ModelChange:
    bucket: str  # "semantic" | "cosmetic" | "additive" | "removed"
    kind: str  # "measure" | "column" | "relationship" | "table"
    subject: str  # "Sales[Revenue]" style locator
    sentence: str  # one business-terms line, ASCII only


def _parse_side(
    files: Iterable[tuple[str, str]],
) -> tuple[dict[str, TmdlTable], dict[tuple, TmdlRelationship]]:
    tables: dict[str, TmdlTable] = {}
    rels: dict[tuple, TmdlRelationship] = {}
    for path, text in files:
        if "/definition/tables/" in path and path.endswith(".tmdl"):
            parsed = parse_tmdl(text)
            if parsed is not None:
                tables[parsed.name] = parsed
        for rel in parse_relationships(text):
            key = (rel.from_table, rel.from_column, rel.to_table, rel.to_column)
            rels[key] = rel
    return tables, rels


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
                "additive", "measure", subject,
                f"new measure {name!r} referencing {_references(new.expression)}",
            )
        elif new is None:
            yield ModelChange("removed", "measure", subject, f"measure {name!r} removed")
        elif normalize_measure_body(old.expression) != normalize_measure_body(new.expression):
            yield ModelChange(
                "semantic", "measure", subject,
                f"measure {name!r} logic changed (normalized bodies differ)",
            )
        elif (old.format_string, old.description, old.display_folder) != (
            new.format_string, new.description, new.display_folder
        ):
            yield ModelChange(
                "cosmetic", "measure", subject,
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
                "semantic", "column", subject,
                f"column {name!r} type changed: {old.data_type} -> {new.data_type}",
            )
        elif (old.summarize_by, old.sort_by_column, old.is_hidden) != (
            new.summarize_by, new.sort_by_column, new.is_hidden
        ):
            yield ModelChange(
                "cosmetic", "column", subject,
                f"column {name!r} presentation changed (summarize/sort/hidden)",
            )


def _rel_semantics(rel: TmdlRelationship) -> tuple:
    return (rel.is_active, rel.from_cardinality, rel.to_cardinality,
            rel.cross_filtering_behavior)


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
                "semantic", "relationship", subject,
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
                "additive", "table", name,
                f"new table {name!r} ({len(head.columns)} columns, "
                f"{len(head.measures)} measures)",
            )


def diff_models(
    base_files: Iterable[tuple[str, str]],
    head_files: Iterable[tuple[str, str]],
) -> tuple[ModelChange, ...]:
    """Classify every model change between the two sides, in stable order."""
    base_tables, base_rels = _parse_side(base_files)
    head_tables, head_rels = _parse_side(head_files)
    changes: list[ModelChange] = []
    changes.extend(_diff_tables(base_tables, head_tables))
    for name in sorted(base_tables.keys() & head_tables.keys()):
        changes.extend(_diff_measures(base_tables[name], head_tables[name]))
        changes.extend(_diff_columns(base_tables[name], head_tables[name]))
    changes.extend(_diff_relationships(base_rels, head_rels))
    return tuple(changes)
