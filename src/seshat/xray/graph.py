"""Build the X-Ray model graph from parsed TMDL text.

Read-only: consumes ``(path, text)`` pairs the caller already loaded. Never
touches the filesystem or git itself.

NOTE: this module does NOT import the public
:func:`seshat.tmdl.strip_dax_comments_and_strings` -- the reference resolver
needs single-quoted table names intact (``'Dim Product'[list_price]``), so it
defines its own :func:`_strip_for_refs` (comments + double-quoted strings
only). The public stripper is consumed by ``audit.py`` and stays aliased in
``rules/dax.py`` for D4.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ..tmdl import (
    TmdlRelationship,
    TmdlTable,
    parse_relationships,
    parse_tmdl,
)

# 'Table Name'[Col] or Table[Col]; bare [Name] is scanned afterwards on the
# masked text so a qualified match never double-counts as a bare token.
_QUALIFIED = re.compile(
    r"(?:'(?P<qt>(?:[^']|'')*)'|(?P<bt>[A-Za-z_][\w ]*?))\[(?P<c>[^\]]+)\]"
)
_BARE = re.compile(r"\[(?P<n>[^\]]+)\]")


@dataclass(frozen=True)
class ModelGraph:
    """The resolved reference graph of one committed semantic model.

    Measure keys are measure names (model-globally unique in Tabular);
    column keys are ``(table_name, column_name)`` pairs.
    """

    tables: tuple[TmdlTable, ...]
    relationships: tuple[TmdlRelationship, ...]
    measure_refs: Mapping[str, frozenset[str]]
    column_refs: Mapping[str, frozenset[tuple[str, str]]]
    unresolved: Mapping[str, frozenset[str]]
    text_referenced_columns: frozenset[tuple[str, str]]
    parse_notices: tuple[str, ...]


def _is_table_file(path: str) -> bool:
    return "/definition/tables/" in path and path.endswith(".tmdl")


def _strip_for_refs(expr: str) -> str:
    """Strip comments and double-quoted strings, KEEPING quoted table names."""
    no_block = re.sub(r"/\*.*?\*/", " ", expr, flags=re.DOTALL)
    no_line = re.sub(r"//[^\n]*", " ", no_block)
    return re.sub(r'"(?:[^"]|"")*"', " ", no_line)


def _qualified_table(match: re.Match[str]) -> str:
    return (match.group("qt") or match.group("bt") or "").replace("''", "'").strip()


class _Refs:
    """Mutable accumulator for one measure's resolved references."""

    def __init__(self) -> None:
        self.measures: set[str] = set()
        self.columns: set[tuple[str, str]] = set()
        self.unresolved: set[str] = set()


def _resolve_qualified(
    table: str,
    column: str,
    measures: Mapping[str, str],
    columns: frozenset[tuple[str, str]],
    out: _Refs,
) -> None:
    if (table, column) in columns:
        out.columns.add((table, column))
    elif measures.get(column) == table:
        out.measures.add(column)
    else:
        out.unresolved.add(f"{table}[{column}]")


def _resolve_bare(
    name: str,
    own_table: str,
    measures: Mapping[str, str],
    columns: frozenset[tuple[str, str]],
    out: _Refs,
) -> None:
    if name in measures:
        out.measures.add(name)
    elif (own_table, name) in columns:
        out.columns.add((own_table, name))
    else:
        out.unresolved.add(name)


def _extract_refs(
    expression: str,
    own_table: str,
    measures: Mapping[str, str],
    columns: frozenset[tuple[str, str]],
) -> _Refs:
    """Resolve every DAX identifier reference in one measure expression."""
    cleaned = _strip_for_refs(expression)
    out = _Refs()
    masked = cleaned
    for match in reversed(list(_QUALIFIED.finditer(cleaned))):
        _resolve_qualified(
            _qualified_table(match), match.group("c").strip(), measures, columns, out
        )
        span = match.end() - match.start()
        masked = masked[: match.start()] + " " * span + masked[match.end() :]
    for bare in _BARE.finditer(masked):
        _resolve_bare(bare.group("n").strip(), own_table, measures, columns, out)
    return out


def _text_scan(
    raw_texts: Iterable[str], columns: frozenset[tuple[str, str]]
) -> frozenset[tuple[str, str]]:
    """Conservative raw-text column references in non-table model files.

    Roles, calculation groups, and model.tmdl are scanned with the same
    qualified-reference regex; every hit that resolves to a known column
    counts as a reference (so RLS-only columns are never called unused).
    """
    hits: set[tuple[str, str]] = set()
    for text in raw_texts:
        cleaned = _strip_for_refs(text)
        for match in _QUALIFIED.finditer(cleaned):
            ref = (_qualified_table(match), match.group("c").strip())
            if ref in columns:
                hits.add(ref)
    return frozenset(hits)


def build_graph(model_files: Iterable[tuple[str, str]]) -> ModelGraph:
    """Build the graph from ``(repo_relative_path, text)`` model-file pairs."""
    tables: list[TmdlTable] = []
    notices: list[str] = []
    raw_others: list[str] = []
    relationships: list[TmdlRelationship] = []
    for path, text in model_files:
        relationships.extend(parse_relationships(text))
        if _is_table_file(path):
            parsed = parse_tmdl(text)
            if parsed is None:
                notices.append(path)
            else:
                tables.append(parsed)
        elif "/cultures/" not in path:
            raw_others.append(text)
    measures = {m.name: t.name for t in tables for m in t.measures}
    columns = frozenset((t.name, c.name) for t in tables for c in t.columns)
    measure_refs: dict[str, frozenset[str]] = {}
    column_refs: dict[str, frozenset[tuple[str, str]]] = {}
    unresolved: dict[str, frozenset[str]] = {}
    for table in tables:
        for measure in table.measures:
            refs = _extract_refs(measure.expression, table.name, measures, columns)
            measure_refs[measure.name] = frozenset(refs.measures)
            column_refs[measure.name] = frozenset(refs.columns)
            unresolved[measure.name] = frozenset(refs.unresolved)
    return ModelGraph(
        tables=tuple(tables),
        relationships=tuple(relationships),
        measure_refs=measure_refs,
        column_refs=column_refs,
        unresolved=unresolved,
        text_referenced_columns=_text_scan(raw_others, columns),
        parse_notices=tuple(notices),
    )
