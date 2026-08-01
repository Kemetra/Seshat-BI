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


class _Resolver:
    """Resolve one measure's DAX identifier references against the model.

    Holds the lookup maps once so each resolve step needs only the token;
    accumulates resolved measure/column references and unresolved tokens.
    """

    def __init__(
        self,
        own_table: str,
        measures: Mapping[str, str],
        columns: frozenset[tuple[str, str]],
    ) -> None:
        self._own_table = own_table
        self._measures = measures
        self._columns = columns
        self.measures: set[str] = set()
        self.columns: set[tuple[str, str]] = set()
        self.unresolved: set[str] = set()

    def resolve_qualified(self, table: str, column: str) -> None:
        if (table, column) in self._columns:
            self.columns.add((table, column))
        elif self._measures.get(column) == table:
            self.measures.add(column)
        else:
            self.unresolved.add(f"{table}[{column}]")

    def resolve_bare(self, name: str) -> None:
        if name in self._measures:
            self.measures.add(name)
        elif (self._own_table, name) in self._columns:
            self.columns.add((self._own_table, name))
        else:
            self.unresolved.add(name)


def _mask(text: str, match: re.Match[str]) -> str:
    span = match.end() - match.start()
    return text[: match.start()] + " " * span + text[match.end() :]


def _extract_refs(
    expression: str,
    own_table: str,
    measures: Mapping[str, str],
    columns: frozenset[tuple[str, str]],
) -> _Resolver:
    """Resolve every DAX identifier reference in one measure expression."""
    cleaned = _strip_for_refs(expression)
    out = _Resolver(own_table, measures, columns)
    masked = cleaned
    for match in reversed(list(_QUALIFIED.finditer(cleaned))):
        out.resolve_qualified(_qualified_table(match), match.group("c").strip())
        masked = _mask(masked, match)
    for bare in _BARE.finditer(masked):
        out.resolve_bare(bare.group("n").strip())
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


@dataclass(frozen=True)
class _Partition:
    """Model files split by role, plus every parsed relationship."""

    tables: tuple[TmdlTable, ...]
    notices: tuple[str, ...]
    raw_others: tuple[str, ...]
    relationships: tuple[TmdlRelationship, ...]


def _classify_table_file(
    path: str, text: str, tables: list[TmdlTable], notices: list[str]
) -> None:
    parsed = parse_tmdl(text)
    if parsed is None:
        notices.append(path)
    else:
        tables.append(parsed)


def _partition_files(model_files: Iterable[tuple[str, str]]) -> _Partition:
    tables: list[TmdlTable] = []
    notices: list[str] = []
    raw_others: list[str] = []
    relationships: list[TmdlRelationship] = []
    for path, text in model_files:
        relationships.extend(parse_relationships(text))
        if _is_table_file(path):
            _classify_table_file(path, text, tables, notices)
        elif "/cultures/" not in path:
            raw_others.append(text)
    return _Partition(
        tables=tuple(tables),
        notices=tuple(notices),
        raw_others=tuple(raw_others),
        relationships=tuple(relationships),
    )


def _resolved_refs(
    tables: tuple[TmdlTable, ...],
    measures: Mapping[str, str],
    columns: frozenset[tuple[str, str]],
) -> tuple[dict, dict, dict]:
    measure_refs: dict[str, frozenset[str]] = {}
    column_refs: dict[str, frozenset[tuple[str, str]]] = {}
    unresolved: dict[str, frozenset[str]] = {}
    for table in tables:
        for measure in table.measures:
            refs = _extract_refs(measure.expression, table.name, measures, columns)
            measure_refs[measure.name] = frozenset(refs.measures)
            column_refs[measure.name] = frozenset(refs.columns)
            unresolved[measure.name] = frozenset(refs.unresolved)
    return measure_refs, column_refs, unresolved


def build_graph(model_files: Iterable[tuple[str, str]]) -> ModelGraph:
    """Build the graph from ``(repo_relative_path, text)`` model-file pairs."""
    part = _partition_files(model_files)
    measures = {m.name: t.name for t in part.tables for m in t.measures}
    columns = frozenset((t.name, c.name) for t in part.tables for c in t.columns)
    measure_refs, column_refs, unresolved = _resolved_refs(
        part.tables, measures, columns
    )
    return ModelGraph(
        tables=part.tables,
        relationships=part.relationships,
        measure_refs=measure_refs,
        column_refs=column_refs,
        unresolved=unresolved,
        text_referenced_columns=_text_scan(part.raw_others, columns),
        parse_notices=part.notices,
    )
