"""X-Ray audit findings X0-X4 over the model graph.

Advisory only: severities are ``info``/``warning``, NEVER ``error`` -- the
audit cannot fail a build. The conservative core: absence of evidence never
becomes a finding, and unresolved DAX references EXCLUDE a column from every
"unused" determination.

Enforcement stays with the check rules: D6 owns bi-directional relationships
(skipped entirely here), D3 owns duplicate normalized bodies (X3 adds graph
context and cites it), D7 owns the date-table marker (X4 cites it).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ..tmdl import (
    DATE_TABLE_MARKER,
    TmdlTable,
    normalize_measure_body,
    strip_dax_comments_and_strings,
)
from .bindings import ReportBindings
from .graph import ModelGraph

_NO_REPORT_SUFFIX = " (no report scanned -- visual usage unknown)"


@dataclass(frozen=True)
class XrayFinding:
    finding_id: str  # "X0".."X4"
    severity: str  # "info" | "warning" (advisory only; NEVER "error")
    message: str
    locator: str  # "<table>[<object>]" or repo-relative path
    fix_hint: str


def _relationship_endpoint_columns(graph: ModelGraph) -> set[tuple[str, str]]:
    refs: set[tuple[str, str]] = set()
    for rel in graph.relationships:
        endpoints = ((rel.from_table, rel.from_column), (rel.to_table, rel.to_column))
        refs |= {(t, c) for t, c in endpoints if t and c}
    return refs


def _sort_by_targets(graph: ModelGraph) -> set[tuple[str, str]]:
    return {
        (t.name, c.sort_by_column)
        for t in graph.tables
        for c in t.columns
        if c.sort_by_column
    }


def _measure_referenced_columns(graph: ModelGraph) -> set[tuple[str, str]]:
    refs: set[tuple[str, str]] = set()
    for cols in graph.column_refs.values():
        refs |= cols
    return refs


def _hierarchy_level_columns(
    graph: ModelGraph, bindings: ReportBindings
) -> set[tuple[str, str]]:
    """Resolve bound (entity, hierarchy, level) triples to their real columns.

    Falls back to treating the level NAME as a column name when the hierarchy
    is not declared in the parsed model: that can only ADD a reference, which
    keeps unused-detection conservative rather than inventing a finding.
    """
    declared: dict[tuple[str, str, str], str] = {}
    for table in graph.tables:
        for hierarchy in table.hierarchies:
            for level_name, column in hierarchy.levels:
                key = (
                    table.name.casefold(),
                    hierarchy.name.casefold(),
                    level_name.casefold(),
                )
                declared[key] = column
    refs: set[tuple[str, str]] = set()
    for entity, hierarchy_name, level in bindings.bound_hierarchy_levels:
        key = (entity.casefold(), hierarchy_name.casefold(), level.casefold())
        refs.add((entity, declared.get(key, level)))
    return refs


def _referenced_columns(
    graph: ModelGraph, bindings: ReportBindings
) -> frozenset[tuple[str, str]]:
    """Every column referenced by ANY scanned surface (computed once)."""
    refs = set(graph.text_referenced_columns) | set(bindings.bound_columns)
    refs |= _measure_referenced_columns(graph)
    refs |= _relationship_endpoint_columns(graph)
    refs |= _sort_by_targets(graph)
    refs |= _hierarchy_level_columns(graph, bindings)
    return frozenset(refs)


def _unresolved_tokens(graph: ModelGraph) -> frozenset[str]:
    tokens: set[str] = set()
    for bag in graph.unresolved.values():
        tokens |= bag
    return frozenset(tokens)


def _x0(graph: ModelGraph) -> Iterable[XrayFinding]:
    for path in graph.parse_notices:
        yield XrayFinding(
            finding_id="X0",
            severity="info",
            message="table file could not be parsed; it is excluded from the audit",
            locator=path,
            fix_hint=(
                "check the TMDL syntax; the file may use constructs the parser skips"
            ),
        )


def _x1_columns(
    graph: ModelGraph, bindings: ReportBindings, referenced: frozenset[tuple[str, str]]
) -> Iterable[XrayFinding]:
    unresolved = _unresolved_tokens(graph)
    severity = "warning" if bindings.report_scanned else "info"
    suffix = "" if bindings.report_scanned else _NO_REPORT_SUFFIX
    for table in graph.tables:
        for column in table.columns:
            ref = (table.name, column.name)
            if ref in referenced or column.name in unresolved:
                continue
            yield XrayFinding(
                finding_id="X1",
                severity=severity,
                message=f"column unreferenced in scanned surfaces{suffix}",
                locator=f"{table.name}[{column.name}]",
                fix_hint=(
                    "confirm with the model owner, then drop it from the model "
                    "or bind it to a visual"
                ),
            )


def _orphan_measure(name: str, inbound: set[str], bindings: ReportBindings) -> bool:
    if name in inbound:
        return False
    return not (bindings.report_scanned and name in bindings.bound_measures)


def _x1_measures(graph: ModelGraph, bindings: ReportBindings) -> Iterable[XrayFinding]:
    inbound: set[str] = set()
    for refs in graph.measure_refs.values():
        inbound |= refs
    severity = "warning" if bindings.report_scanned else "info"
    suffix = "" if bindings.report_scanned else _NO_REPORT_SUFFIX
    for table in graph.tables:
        for measure in table.measures:
            if not _orphan_measure(measure.name, inbound, bindings):
                continue
            yield XrayFinding(
                finding_id="X1",
                severity=severity,
                message=(
                    "orphan measure: no inbound measure reference and no "
                    f"visual binding{suffix}"
                ),
                locator=f"{table.name}[{measure.name}]",
                fix_hint=(
                    "bind it to a visual, reference it from another measure, "
                    "or retire it"
                ),
            )


def _active_relationships(graph: ModelGraph):
    """X2's working set: bi-di relationships belong to D6, not X-Ray."""
    return [
        rel
        for rel in graph.relationships
        if rel.cross_filtering_behavior != "bothDirections"
    ]


def _x2_m2m(rels) -> Iterable[XrayFinding]:
    for rel in rels:
        if rel.from_cardinality == "many" and rel.to_cardinality == "many":
            yield XrayFinding(
                finding_id="X2",
                severity="warning",
                message=(
                    "many-to-many relationship: filters propagate both ways "
                    "over a shared key set"
                ),
                locator=rel.name,
                fix_hint=(
                    "introduce a bridge table or confirm the grain ruling "
                    "with the model owner"
                ),
            )


def _model_uses_userelationship(graph: ModelGraph) -> bool:
    dax = " ".join(
        strip_dax_comments_and_strings(m.expression).upper()
        for t in graph.tables
        for m in t.measures
    )
    return "USERELATIONSHIP" in dax


def _x2_inactive(graph: ModelGraph, rels) -> Iterable[XrayFinding]:
    if _model_uses_userelationship(graph):
        return
    for rel in rels:
        if not rel.is_active:
            yield XrayFinding(
                finding_id="X2",
                severity="info",
                message=(
                    "inactive relationship with no USERELATIONSHIP anywhere "
                    "in DAX: dead weight"
                ),
                locator=rel.name,
                fix_hint=(
                    "add the USERELATIONSHIP measure that needs it, or "
                    "remove the relationship"
                ),
            )


def _both_endpoints_string(rel, types: Mapping[tuple[str, str], str | None]) -> bool:
    from_type = types.get((rel.from_table or "", rel.from_column or ""))
    to_type = types.get((rel.to_table or "", rel.to_column or ""))
    return from_type == "string" and to_type == "string"


def _x2_string_keys(graph: ModelGraph, rels) -> Iterable[XrayFinding]:
    types = {(t.name, c.name): c.data_type for t in graph.tables for c in t.columns}
    for rel in rels:
        if _both_endpoints_string(rel, types):
            yield XrayFinding(
                finding_id="X2",
                severity="info",
                message=(
                    "relationship keys declared as string dataType "
                    "(statically provable from the column declaration; "
                    "cardinality itself is never guessed)"
                ),
                locator=rel.name,
                fix_hint=(
                    "join on integer surrogate keys where the warehouse provides them"
                ),
            )


def _relationship_edges(rels) -> dict[str, list[str]]:
    edges: dict[str, list[str]] = {}
    for rel in rels:
        if rel.from_table and rel.to_table:
            edges.setdefault(rel.from_table, []).append(rel.to_table)
    return edges


def _chain_depth(node: str, edges: Mapping[str, list[str]], seen: frozenset) -> int:
    if node in seen:
        return 0
    hops = (1 + _chain_depth(nxt, edges, seen | {node}) for nxt in edges.get(node, []))
    return max(hops, default=0)


def _x2_snowflake(rels) -> Iterable[XrayFinding]:
    edges = _relationship_edges(rels)
    targets = {t for nxts in edges.values() for t in nxts}
    for start in sorted(set(edges) - targets):
        hops = _chain_depth(start, edges, frozenset())
        if hops >= 3:
            yield XrayFinding(
                finding_id="X2",
                severity="info",
                message=(
                    f"snowflake chain: {hops} relationship hops walkable from '{start}'"
                ),
                locator=start,
                fix_hint=(
                    "flatten the dimension chain into the first-hop "
                    "dimension where the grain allows"
                ),
            )


def _measure_depths(
    refs: Mapping[str, frozenset[str]],
) -> tuple[dict[str, int], frozenset[str]]:
    """Longest reference-chain depth per measure + EVERY cycle member.

    The active path is tracked as a list, not just a set, so a back edge
    records the whole cycle segment. Recording only the re-entered node left
    every other member of an ``A -> B -> A`` cycle unreported (PR #550 review).
    """
    memo: dict[str, int] = {}
    path: list[str] = []
    on_path: set[str] = set()
    cyclic: set[str] = set()

    def walk(name: str) -> int:
        if name in on_path:
            # Back edge: everything from this node to the end of the active
            # path is part of the cycle.
            cyclic.update(path[path.index(name) :])
            return 0
        if name in memo:
            return memo[name]
        path.append(name)
        on_path.add(name)
        best = max((1 + walk(nxt) for nxt in refs.get(name, frozenset())), default=0)
        path.pop()
        on_path.discard(name)
        # A cycle member's depth is not a meaningful chain length, and
        # memoizing it would hide the cycle from another entry point.
        if name not in cyclic:
            memo[name] = best
        return best

    for name in sorted(refs):
        walk(name)
    return memo, frozenset(cyclic)


def _x3_cycles(
    owner: Mapping[str, str], cyclic: frozenset[str]
) -> Iterable[XrayFinding]:
    for name in sorted(cyclic):
        yield XrayFinding(
            finding_id="X3",
            severity="warning",
            message="circular measure reference",
            locator=f"{owner.get(name, '?')}[{name}]",
            fix_hint=(
                "break the cycle: one of these measures must compute from "
                "columns, not from the other"
            ),
        )


def _x3_depths(
    owner: Mapping[str, str], depths: Mapping[str, int], cyclic: frozenset[str]
) -> Iterable[XrayFinding]:
    for name, hops in sorted(depths.items()):
        if hops < 5 or name in cyclic:
            continue
        yield XrayFinding(
            finding_id="X3",
            severity="info",
            message=(
                f"measure reference depth {hops}: long chains are fragile "
                "under refactoring"
            ),
            locator=f"{owner.get(name, '?')}[{name}]",
            fix_hint="flatten intermediate measures the chain no longer needs",
        )


def _x3_depth_cycles(graph: ModelGraph) -> Iterable[XrayFinding]:
    owner = {m.name: t.name for t in graph.tables for m in t.measures}
    depths, cyclic = _measure_depths(graph.measure_refs)
    yield from _x3_cycles(owner, cyclic)
    yield from _x3_depths(owner, depths, cyclic)


def _measures_by_body(graph: ModelGraph) -> dict[str, list[tuple[str, str]]]:
    by_body: dict[str, list[tuple[str, str]]] = {}
    for table in graph.tables:
        for measure in table.measures:
            body = normalize_measure_body(measure.expression)
            by_body.setdefault(body, []).append((table.name, measure.name))
    return by_body


def _x3_duplicates(graph: ModelGraph) -> Iterable[XrayFinding]:
    by_body = _measures_by_body(graph)
    for body in sorted(by_body):
        owners = by_body[body]
        if len({t for t, _ in owners}) < 2:
            continue
        listed = ", ".join(f"{t}[{m}]" for t, m in sorted(owners))
        yield XrayFinding(
            finding_id="X3",
            severity="info",
            message=f"duplicate measure logic across tables: {listed} (see rule D3)",
            locator=listed.split(", ")[0],
            fix_hint="keep one canonical measure and reference it from the others",
        )


def _date_marked(table: TmdlTable) -> bool:
    """True if the table carries EITHER accepted date-table marker.

    Must stay in lockstep with ``rules/dax.py::_table_is_marked_date_table``:
    X4 cites D7, so accepting fewer markers than D7 does would report a
    finding against a model that D7 passes.
    """
    if any(ann.strip() == DATE_TABLE_MARKER for ann in table.annotations):
        return True
    return table.data_category == "Time" and any(c.is_key for c in table.columns)


def _unmarked_date_target(rel, tables: Mapping[str, TmdlTable]) -> str | None:
    """The to-side table name when it joins on a date-named key unmarked."""
    if not rel.to_table or not rel.to_column:
        return None
    if "date" not in rel.to_column.lower():
        return None
    table = tables.get(rel.to_table)
    if table is None or _date_marked(table):
        return None
    return rel.to_table


def _x4_date(graph: ModelGraph) -> Iterable[XrayFinding]:
    tables = {t.name: t for t in graph.tables}
    seen: set[str] = set()
    for rel in graph.relationships:
        name = _unmarked_date_target(rel, tables)
        if name is None or name in seen:
            continue
        seen.add(name)
        yield XrayFinding(
            finding_id="X4",
            severity="info",
            message=(
                f"'{name}' joins on a date-named key but is not marked as "
                "a date table (see rule D7)"
            ),
            locator=name,
            fix_hint="set dataCategory: Time and an isKey date column, then re-run",
        )


def _summarized_unfed(column, ref, measure_cols, bindings: ReportBindings) -> bool:
    if column.summarize_by in (None, "none"):
        return False
    return ref not in measure_cols and ref not in bindings.bound_columns


def _x4_summarized(
    graph: ModelGraph,
    bindings: ReportBindings,
    measure_cols: frozenset[tuple[str, str]],
) -> Iterable[XrayFinding]:
    for table in graph.tables:
        for column in table.columns:
            ref = (table.name, column.name)
            if not _summarized_unfed(column, ref, measure_cols, bindings):
                continue
            yield XrayFinding(
                finding_id="X4",
                severity="info",
                message=(
                    "column carries a default summarizeBy but feeds no "
                    "measure or visual"
                ),
                locator=f"{table.name}[{column.name}]",
                fix_hint=(
                    "set summarizeBy: none, or build the measure that "
                    "should own this aggregation"
                ),
            )


def run_audit(graph: ModelGraph, bindings: ReportBindings) -> tuple[XrayFinding, ...]:
    """All advisory findings, in family order X0..X4."""
    referenced = _referenced_columns(graph, bindings)
    measure_cols = frozenset(_measure_referenced_columns(graph))
    rels = _active_relationships(graph)
    families: tuple[Iterable[XrayFinding], ...] = (
        _x0(graph),
        _x1_columns(graph, bindings, referenced),
        _x1_measures(graph, bindings),
        _x2_m2m(rels),
        _x2_inactive(graph, rels),
        _x2_string_keys(graph, rels),
        _x2_snowflake(rels),
        _x3_depth_cycles(graph),
        _x3_duplicates(graph),
        _x4_date(graph),
        _x4_summarized(graph, bindings, measure_cols),
    )
    return tuple(f for family in families for f in family)
