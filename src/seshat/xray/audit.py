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

from ..tmdl import TmdlTable, normalize_measure_body, strip_dax_comments_and_strings
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


def _finding(fid: str, sev: str, msg: str, loc: str, hint: str) -> XrayFinding:
    return XrayFinding(
        finding_id=fid, severity=sev, message=msg, locator=loc, fix_hint=hint
    )


def _referenced_columns(
    graph: ModelGraph, bindings: ReportBindings
) -> frozenset[tuple[str, str]]:
    """Every column referenced by ANY scanned surface (computed once)."""
    refs: set[tuple[str, str]] = set(graph.text_referenced_columns)
    refs |= set(bindings.bound_columns)
    for cols in graph.column_refs.values():
        refs |= cols
    for rel in graph.relationships:
        if rel.from_table and rel.from_column:
            refs.add((rel.from_table, rel.from_column))
        if rel.to_table and rel.to_column:
            refs.add((rel.to_table, rel.to_column))
    for table in graph.tables:
        for column in table.columns:
            if column.sort_by_column:
                refs.add((table.name, column.sort_by_column))
    return frozenset(refs)


def _unresolved_tokens(graph: ModelGraph) -> frozenset[str]:
    tokens: set[str] = set()
    for bag in graph.unresolved.values():
        tokens |= bag
    return frozenset(tokens)


def _x0(graph: ModelGraph) -> Iterable[XrayFinding]:
    for path in graph.parse_notices:
        yield _finding(
            "X0",
            "info",
            "table file could not be parsed; it is excluded from the audit",
            path,
            "check the TMDL syntax; the file may use constructs the parser skips",
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
            yield _finding(
                "X1",
                severity,
                f"column unreferenced in scanned surfaces{suffix}",
                f"{table.name}[{column.name}]",
                "confirm with the model owner, then drop it from the model "
                "or bind it to a visual",
            )


def _x1_measures(
    graph: ModelGraph, bindings: ReportBindings
) -> Iterable[XrayFinding]:
    inbound: set[str] = set()
    for refs in graph.measure_refs.values():
        inbound |= refs
    severity = "warning" if bindings.report_scanned else "info"
    suffix = "" if bindings.report_scanned else _NO_REPORT_SUFFIX
    for table in graph.tables:
        for measure in table.measures:
            if measure.name in inbound:
                continue
            if bindings.report_scanned and measure.name in bindings.bound_measures:
                continue
            yield _finding(
                "X1",
                severity,
                f"orphan measure: no inbound measure reference and no visual "
                f"binding{suffix}",
                f"{table.name}[{measure.name}]",
                "bind it to a visual, reference it from another measure, or "
                "retire it",
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
            yield _finding(
                "X2",
                "warning",
                "many-to-many relationship: filters propagate both ways over "
                "a shared key set",
                rel.name,
                "introduce a bridge table or confirm the grain ruling with "
                "the model owner",
            )


def _x2_inactive(graph: ModelGraph, rels) -> Iterable[XrayFinding]:
    dax = " ".join(
        strip_dax_comments_and_strings(m.expression).upper()
        for t in graph.tables
        for m in t.measures
    )
    if "USERELATIONSHIP" in dax:
        return
    for rel in rels:
        if not rel.is_active:
            yield _finding(
                "X2",
                "info",
                "inactive relationship with no USERELATIONSHIP anywhere in "
                "DAX: dead weight",
                rel.name,
                "add the USERELATIONSHIP measure that needs it, or remove "
                "the relationship",
            )


def _x2_string_keys(graph: ModelGraph, rels) -> Iterable[XrayFinding]:
    types = {
        (t.name, c.name): c.data_type for t in graph.tables for c in t.columns
    }
    for rel in rels:
        from_type = types.get((rel.from_table or "", rel.from_column or ""))
        to_type = types.get((rel.to_table or "", rel.to_column or ""))
        if from_type == "string" and to_type == "string":
            yield _finding(
                "X2",
                "info",
                "relationship keys declared as string dataType (statically "
                "provable from the column declaration; cardinality itself is "
                "never guessed)",
                rel.name,
                "join on integer surrogate keys where the warehouse provides "
                "them",
            )


def _x2_snowflake(rels) -> Iterable[XrayFinding]:
    edges: dict[str, list[str]] = {}
    for rel in rels:
        if rel.from_table and rel.to_table:
            edges.setdefault(rel.from_table, []).append(rel.to_table)

    def depth(node: str, seen: frozenset[str]) -> int:
        if node in seen:
            return 0
        return max(
            (1 + depth(nxt, seen | {node}) for nxt in edges.get(node, [])),
            default=0,
        )

    targets = {t for nxts in edges.values() for t in nxts}
    for start in sorted(set(edges) - targets):
        hops = depth(start, frozenset())
        if hops >= 3:
            yield _finding(
                "X2",
                "info",
                f"snowflake chain: {hops} relationship hops walkable from "
                f"'{start}'",
                start,
                "flatten the dimension chain into the first-hop dimension "
                "where the grain allows",
            )


def _measure_depths(
    refs: Mapping[str, frozenset[str]],
) -> tuple[dict[str, int], frozenset[str]]:
    """Longest reference-chain depth per measure + the cycle-member set."""
    memo: dict[str, int] = {}
    on_stack: set[str] = set()
    cyclic: set[str] = set()

    def walk(name: str) -> int:
        if name in memo:
            return memo[name]
        if name in on_stack:
            cyclic.add(name)
            return 0
        on_stack.add(name)
        best = 0
        for nxt in refs.get(name, frozenset()):
            best = max(best, 1 + walk(nxt))
        on_stack.discard(name)
        memo[name] = best
        return best

    for name in refs:
        walk(name)
    return memo, frozenset(cyclic)


def _x3_depth_cycles(graph: ModelGraph) -> Iterable[XrayFinding]:
    owner = {m.name: t.name for t in graph.tables for m in t.measures}
    depths, cyclic = _measure_depths(graph.measure_refs)
    for name in sorted(cyclic):
        yield _finding(
            "X3",
            "warning",
            "circular measure reference",
            f"{owner.get(name, '?')}[{name}]",
            "break the cycle: one of these measures must compute from "
            "columns, not from the other",
        )
    for name, hops in sorted(depths.items()):
        if hops >= 5 and name not in cyclic:
            yield _finding(
                "X3",
                "info",
                f"measure reference depth {hops}: long chains are fragile "
                "under refactoring",
                f"{owner.get(name, '?')}[{name}]",
                "flatten intermediate measures the chain no longer needs",
            )


def _x3_duplicates(graph: ModelGraph) -> Iterable[XrayFinding]:
    by_body: dict[str, list[tuple[str, str]]] = {}
    for table in graph.tables:
        for measure in table.measures:
            body = normalize_measure_body(measure.expression)
            by_body.setdefault(body, []).append((table.name, measure.name))
    for body in sorted(by_body):
        owners = by_body[body]
        if len({t for t, _ in owners}) < 2:
            continue
        listed = ", ".join(f"{t}[{m}]" for t, m in sorted(owners))
        yield _finding(
            "X3",
            "info",
            f"duplicate measure logic across tables: {listed} (see rule D3)",
            listed.split(", ")[0],
            "keep one canonical measure and reference it from the others",
        )


def _date_marked(table: TmdlTable) -> bool:
    return table.data_category == "Time" and any(c.is_key for c in table.columns)


def _x4_date(graph: ModelGraph) -> Iterable[XrayFinding]:
    tables = {t.name: t for t in graph.tables}
    seen: set[str] = set()
    for rel in graph.relationships:
        name, column = rel.to_table, rel.to_column
        if not name or not column or "date" not in column.lower():
            continue
        table = tables.get(name)
        if table is None or name in seen or _date_marked(table):
            continue
        seen.add(name)
        yield _finding(
            "X4",
            "info",
            f"'{name}' joins on a date-named key but is not marked as a "
            "date table (see rule D7)",
            name,
            "set dataCategory: Time and an isKey date column, then re-run",
        )


def _x4_summarized(
    graph: ModelGraph, bindings: ReportBindings, referenced_by_measures: frozenset
) -> Iterable[XrayFinding]:
    for table in graph.tables:
        for column in table.columns:
            if column.summarize_by in (None, "none"):
                continue
            ref = (table.name, column.name)
            if ref in referenced_by_measures or ref in bindings.bound_columns:
                continue
            yield _finding(
                "X4",
                "info",
                "column carries a default summarizeBy but feeds no measure "
                "or visual",
                f"{table.name}[{column.name}]",
                "set summarizeBy: none, or build the measure that should "
                "own this aggregation",
            )


def run_audit(
    graph: ModelGraph, bindings: ReportBindings
) -> tuple[XrayFinding, ...]:
    """All advisory findings, in family order X0..X4."""
    referenced = _referenced_columns(graph, bindings)
    measure_cols: set[tuple[str, str]] = set()
    for cols in graph.column_refs.values():
        measure_cols |= cols
    rels = _active_relationships(graph)
    findings: list[XrayFinding] = []
    findings.extend(_x0(graph))
    findings.extend(_x1_columns(graph, bindings, referenced))
    findings.extend(_x1_measures(graph, bindings))
    findings.extend(_x2_m2m(rels))
    findings.extend(_x2_inactive(graph, rels))
    findings.extend(_x2_string_keys(graph, rels))
    findings.extend(_x2_snowflake(rels))
    findings.extend(_x3_depth_cycles(graph))
    findings.extend(_x3_duplicates(graph))
    findings.extend(_x4_date(graph))
    findings.extend(_x4_summarized(graph, bindings, frozenset(measure_cols)))
    return tuple(findings)
