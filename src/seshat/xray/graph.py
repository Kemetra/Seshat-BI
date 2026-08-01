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
from itertools import chain

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


@dataclass(frozen=True)
class _Lookup:
    """Case-INSENSITIVE name resolution that yields the DECLARED spelling.

    DAX identifiers are case-insensitive, so ``SUM(sales[AMOUNT])`` must resolve
    against a declared ``Sales[amount]``. Comparing exact tuples dropped the
    edge and could emit a false X1 unused-column finding (PR #550 review).
    Keys are casefolded; values keep the declared spelling so locators and
    findings still read as the model author wrote them.
    """

    # casefolded measure name -> (declared measure name, casefolded owning table)
    measures: Mapping[str, tuple[str, str]]
    # (casefolded table, casefolded column) -> (declared table, declared column)
    columns: Mapping[tuple[str, str], tuple[str, str]]

    @classmethod
    def build(cls, tables: Iterable[TmdlTable]) -> _Lookup:
        materialized = list(tables)
        return cls(
            measures={
                m.name.casefold(): (m.name, t.name.casefold())
                for t in materialized
                for m in t.measures
            },
            columns={
                (t.name.casefold(), c.name.casefold()): (t.name, c.name)
                for t in materialized
                for c in t.columns
            },
        )


class _Resolver:
    """Resolve one measure's DAX identifier references against the model.

    Holds the lookup once so each resolve step needs only the token;
    accumulates resolved measure/column references and unresolved tokens.
    """

    def __init__(self, own_table: str, lookup: _Lookup) -> None:
        self._own_table = own_table.casefold()
        self._lookup = lookup
        self.measures: set[str] = set()
        self.columns: set[tuple[str, str]] = set()
        self.unresolved: set[str] = set()

    def resolve_qualified(self, table: str, column: str) -> None:
        declared = self._lookup.columns.get((table.casefold(), column.casefold()))
        if declared is not None:
            self.columns.add(declared)
            return
        measure = self._lookup.measures.get(column.casefold())
        if measure is not None and measure[1] == table.casefold():
            self.measures.add(measure[0])
            return
        self.unresolved.add(f"{table}[{column}]")

    def resolve_bare(self, name: str) -> None:
        measure = self._lookup.measures.get(name.casefold())
        if measure is not None:
            self.measures.add(measure[0])
            return
        declared = self._lookup.columns.get((self._own_table, name.casefold()))
        if declared is not None:
            self.columns.add(declared)
            return
        self.unresolved.add(name)


def _mask(text: str, match: re.Match[str]) -> str:
    span = match.end() - match.start()
    return text[: match.start()] + " " * span + text[match.end() :]


def _extract_refs(expression: str, own_table: str, lookup: _Lookup) -> _Resolver:
    """Resolve every DAX identifier reference in one measure expression."""
    cleaned = _strip_for_refs(expression)
    out = _Resolver(own_table, lookup)
    masked = cleaned
    for match in reversed(list(_QUALIFIED.finditer(cleaned))):
        out.resolve_qualified(_qualified_table(match), match.group("c").strip())
        masked = _mask(masked, match)
    for bare in _BARE.finditer(masked):
        out.resolve_bare(bare.group("n").strip())
    return out


def _text_scan(raw_texts: Iterable[str], lookup: _Lookup) -> frozenset[tuple[str, str]]:
    """Conservative raw-text column references in non-table model files.

    Roles, calculation groups, and model.tmdl are scanned with the same
    qualified-reference regex; every hit that resolves to a known column
    counts as a reference (so RLS-only columns are never called unused).
    Resolution is case-insensitive, like DAX itself.
    """
    hits: set[tuple[str, str]] = set()
    for text in raw_texts:
        cleaned = _strip_for_refs(text)
        for match in _QUALIFIED.finditer(cleaned):
            key = (
                _qualified_table(match).casefold(),
                match.group("c").strip().casefold(),
            )
            declared = lookup.columns.get(key)
            if declared is not None:
                hits.add(declared)
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


def _measure_items(tables: tuple[TmdlTable, ...]) -> Iterable[tuple[str, str, str]]:
    return (
        (measure.name, table.name, measure.expression)
        for table in tables
        for measure in table.measures
    )


def _calc_column_items(tables: tuple[TmdlTable, ...]) -> Iterable[tuple[str, str, str]]:
    """CALCULATED columns only -- a plain data column carries no DAX."""
    return (
        (f"{table.name}[{column.name}]", table.name, column.expression or "")
        for table in tables
        for column in table.columns
        if column.expression
    )


def _dax_bearing_items(
    tables: tuple[TmdlTable, ...],
) -> Iterable[tuple[str, str, str]]:
    """``(ref_key, owning table, DAX)`` for everything carrying DAX.

    A CALCULATED column's expression references model fields exactly as a
    measure does, so skipping it would call those fields unused.
    """
    return chain(_measure_items(tables), _calc_column_items(tables))


def _resolved_refs(
    tables: tuple[TmdlTable, ...], lookup: _Lookup
) -> tuple[dict, dict, dict]:
    """Resolved measure/column references per DAX-bearing item."""
    measure_refs: dict[str, frozenset[str]] = {}
    column_refs: dict[str, frozenset[tuple[str, str]]] = {}
    unresolved: dict[str, frozenset[str]] = {}
    for key, owner, expression in _dax_bearing_items(tables):
        refs = _extract_refs(expression, owner, lookup)
        measure_refs[key] = frozenset(refs.measures)
        column_refs[key] = frozenset(refs.columns)
        unresolved[key] = frozenset(refs.unresolved)
    return measure_refs, column_refs, unresolved


def build_graph(model_files: Iterable[tuple[str, str]]) -> ModelGraph:
    """Build the graph from ``(repo_relative_path, text)`` model-file pairs."""
    part = _partition_files(model_files)
    lookup = _Lookup.build(part.tables)
    measure_refs, column_refs, unresolved = _resolved_refs(part.tables, lookup)
    return ModelGraph(
        tables=part.tables,
        relationships=part.relationships,
        measure_refs=measure_refs,
        column_refs=column_refs,
        unresolved=unresolved,
        text_referenced_columns=_text_scan(part.raw_others, lookup),
        parse_notices=part.notices,
    )
