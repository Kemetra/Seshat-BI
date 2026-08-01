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


@dataclass
class _Sink:
    columns: set[tuple[str, str]] = field(default_factory=set)
    measures: set[str] = field(default_factory=set)


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


def _hierarchy_level(node: dict) -> tuple[str, str] | None:
    """Dig the (entity, level) pair out of a ``HierarchyLevel`` field node."""
    hierarchy = node.get("Expression", {})
    if not isinstance(hierarchy, dict):
        return None
    inner = hierarchy.get("Hierarchy")
    if not isinstance(inner, dict):
        return None
    expression = inner.get("Expression")
    if not isinstance(expression, dict):
        return None
    source_ref = expression.get("SourceRef")
    if not isinstance(source_ref, dict):
        return None
    entity = source_ref.get("Entity")
    level = node.get("Level")
    if isinstance(entity, str) and isinstance(level, str):
        return entity, level
    return None


def _capture(node: dict, out: _Sink) -> None:
    column = node.get("Column")
    if isinstance(column, dict):
        ref = _entity_property(column)
        if ref is not None:
            out.columns.add(ref)
    measure = node.get("Measure")
    if isinstance(measure, dict):
        ref = _entity_property(measure)
        if ref is not None:
            out.measures.add(ref[1])
    level = node.get("HierarchyLevel")
    if isinstance(level, dict):
        hit = _hierarchy_level(level)
        if hit is not None:
            out.columns.add(hit)


def _walk(node: object, out: _Sink) -> None:
    if isinstance(node, dict):
        _capture(node, out)
        for value in node.values():
            _walk(value, out)
    elif isinstance(node, list):
        for item in node:
            _walk(item, out)


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
    )
