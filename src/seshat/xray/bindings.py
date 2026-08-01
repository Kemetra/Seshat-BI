"""Read PBIR visual field bindings for the X-Ray graph.

Schema-agnostic by design: PBIR nests ``Column`` / ``Measure`` /
``HierarchyLevel`` field nodes at many depths (projections, filters, sort
orders), so a recursive walk beats hardcoding paths. Read-only and fail-soft:
a malformed JSON file is skipped silently -- absence of evidence, not a
finding.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReportBindings:
    """What the committed report actually binds.

    ``report_scanned`` is True only when at least one supplied report JSON
    file PARSED: a report whose every file is malformed gives the audit no
    evidence, so it must degrade exactly like a missing report.
    """

    report_scanned: bool
    bound_columns: frozenset[tuple[str, str]]
    bound_measures: frozenset[str]
    # (entity, hierarchy, level) triples. A level's NAME is often not its
    # backing column's name, so these are recorded RAW and resolved against the
    # model's parsed hierarchy membership by the audit -- recording
    # ``(entity, level)`` as if it were a column left the real backing column
    # falsely reported unused (PR #550 review).
    bound_hierarchy_levels: frozenset[tuple[str, str, str]] = frozenset()


@dataclass
class _Sink:
    columns: set[tuple[str, str]] = field(default_factory=set)
    measures: set[str] = field(default_factory=set)
    hierarchy_levels: set[tuple[str, str, str]] = field(default_factory=set)


def _entity_property(node: dict) -> tuple[str, str] | None:
    """Dig ``Expression.SourceRef.Entity`` + ``Property`` out of a field node."""
    expression = node.get("Expression")
    if not isinstance(expression, dict):
        return None
    source_ref = expression.get("SourceRef")
    if not isinstance(source_ref, dict):
        return None
    entity = source_ref.get("Entity")
    prop = node.get("Property")
    if isinstance(entity, str) and isinstance(prop, str):
        return entity, prop
    return None


def _hierarchy_level(node: dict) -> tuple[str, str, str] | None:
    """Dig the (entity, hierarchy, level) triple out of a ``HierarchyLevel``."""
    outer = node.get("Expression", {})
    if not isinstance(outer, dict):
        return None
    inner = outer.get("Hierarchy")
    if not isinstance(inner, dict):
        return None
    expression = inner.get("Expression")
    if not isinstance(expression, dict):
        return None
    source_ref = expression.get("SourceRef")
    if not isinstance(source_ref, dict):
        return None
    entity = source_ref.get("Entity")
    hierarchy = inner.get("Hierarchy")
    level = node.get("Level")
    if all(isinstance(v, str) for v in (entity, hierarchy, level)):
        return entity, hierarchy, level  # type: ignore[return-value]
    return None


def _field_ref(node: dict, key: str) -> tuple[str, str] | None:
    """The (entity, property) pair for a ``Column``/``Measure`` node, or None."""
    child = node.get(key)
    return _entity_property(child) if isinstance(child, dict) else None


def _capture(node: dict, out: _Sink) -> None:
    column = _field_ref(node, "Column")
    if column is not None:
        out.columns.add(column)
    measure = _field_ref(node, "Measure")
    if measure is not None:
        out.measures.add(measure[1])
    raw_level = node.get("HierarchyLevel")
    if isinstance(raw_level, dict):
        level = _hierarchy_level(raw_level)
        if level is not None:
            out.hierarchy_levels.add(level)


def _children(node: object) -> Iterable[object]:
    if isinstance(node, dict):
        return node.values()
    if isinstance(node, list):
        return node
    return ()


def _walk(node: object, out: _Sink) -> None:
    if isinstance(node, dict):
        _capture(node, out)
    for child in _children(node):
        _walk(child, out)


def read_bindings(report_files: Iterable[tuple[str, str]]) -> ReportBindings:
    """Collect bindings from ``(repo_relative_path, raw_json_text)`` pairs."""
    sink = _Sink()
    parsed_any = False
    for _path, raw in report_files:
        try:
            doc = json.loads(raw)
        except ValueError:
            continue  # malformed report file: no evidence, never a finding
        parsed_any = True
        _walk(doc, sink)
    return ReportBindings(
        report_scanned=parsed_any,
        bound_columns=frozenset(sink.columns),
        bound_measures=frozenset(sink.measures),
        bound_hierarchy_levels=frozenset(sink.hierarchy_levels),
    )
