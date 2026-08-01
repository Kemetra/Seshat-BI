"""Audit finding tests, X0-X4 (Task 4).

Inputs are built through ``build_graph`` / ``read_bindings`` -- never
hand-constructed ``ModelGraph`` instances -- so these tests also pin the
public construction path.
"""

from __future__ import annotations

import pytest

from seshat.xray.audit import run_audit
from seshat.xray.bindings import read_bindings
from seshat.xray.graph import build_graph

pytestmark = pytest.mark.unit

_M = "m/X.SemanticModel/definition"
NO_REPORT = read_bindings([])


def _visual(entity: str, prop: str, kind: str = "Column") -> str:
    return (
        '{"field": {"%s": {"Expression": {"SourceRef": {"Entity": "%s"}}, '
        '"Property": "%s"}}}' % (kind, entity, prop)
    )


def _bindings(*refs: tuple[str, str, str]) -> object:
    docs = ",".join(_visual(e, p, k) for e, p, k in refs)
    return read_bindings([("r/X.Report/definition/pages/p/visuals/v/visual.json", f"[{docs}]")])


def _ids(findings, fid):
    return [f for f in findings if f.finding_id == fid]


def test_x0_parse_notice():
    g = build_graph([(f"{_M}/tables/bad.tmdl", "@@@ nope")])
    found = _ids(run_audit(g, NO_REPORT), "X0")
    assert len(found) == 1 and "bad.tmdl" in found[0].locator


def test_x1_unused_column_fires_when_report_scanned():
    g = build_graph(
        [(f"{_M}/tables/T.tmdl", "table T\n\tcolumn used\n\tcolumn dead\n")]
    )
    b = _bindings(("T", "used", "Column"))
    hits = [f for f in _ids(run_audit(g, b), "X1") if "T[dead]" in f.locator]
    assert hits and hits[0].severity == "warning"


def test_x1_downgrades_to_info_without_report():
    g = build_graph([(f"{_M}/tables/T.tmdl", "table T\n\tcolumn dead\n")])
    hits = [f for f in _ids(run_audit(g, NO_REPORT), "X1") if "T[dead]" in f.locator]
    assert hits and hits[0].severity == "info"
    assert "no report scanned" in hits[0].message


def test_x1_relationship_key_never_unused():
    files = [
        (f"{_M}/tables/T.tmdl", "table T\n\tcolumn k\n"),
        (f"{_M}/tables/D.tmdl", "table D\n\tcolumn k\n"),
        (f"{_M}/relationships.tmdl", "relationship r\n\tfromColumn: T.k\n\ttoColumn: D.k\n"),
    ]
    g = build_graph(files)
    assert not [f for f in _ids(run_audit(g, NO_REPORT), "X1") if "[k]" in f.locator]


def test_x1_orphan_measure():
    g = build_graph(
        [(f"{_M}/tables/T.tmdl", "table T\n\tmeasure Orphan = 1\n\tcolumn c\n")]
    )
    b = _bindings(("T", "c", "Column"))
    hits = [f for f in _ids(run_audit(g, b), "X1") if "T[Orphan]" in f.locator]
    assert hits and hits[0].severity == "warning"


def test_x2_many_to_many():
    files = [
        (f"{_M}/relationships.tmdl",
         "relationship r\n\tfromCardinality: many\n\ttoCardinality: many\n"
         "\tfromColumn: A.k\n\ttoColumn: B.k\n"),
    ]
    hits = _ids(run_audit(build_graph(files), NO_REPORT), "X2")
    assert any("many-to-many" in f.message for f in hits)


def test_x2_inactive_without_userelationship():
    files = [
        (f"{_M}/tables/T.tmdl", "table T\n\tmeasure M = SUM(T[c])\n\tcolumn c\n"),
        (f"{_M}/relationships.tmdl",
         "relationship r\n\tisActive: false\n\tfromColumn: T.c\n\ttoColumn: D.k\n"),
    ]
    hits = _ids(run_audit(build_graph(files), NO_REPORT), "X2")
    assert any("USERELATIONSHIP" in f.message for f in hits)


def test_x2_inactive_with_userelationship_silent():
    files = [
        (f"{_M}/tables/T.tmdl",
         "table T\n\tmeasure M = CALCULATE(SUM(T[c]), USERELATIONSHIP(T[c], D[k]))\n\tcolumn c\n"),
        (f"{_M}/relationships.tmdl",
         "relationship r\n\tisActive: false\n\tfromColumn: T.c\n\ttoColumn: D.k\n"),
    ]
    hits = _ids(run_audit(build_graph(files), NO_REPORT), "X2")
    assert not any("USERELATIONSHIP" in f.message for f in hits)


def test_x2_string_keys():
    files = [
        (f"{_M}/tables/A.tmdl", "table A\n\tcolumn k\n\t\tdataType: string\n"),
        (f"{_M}/tables/B.tmdl", "table B\n\tcolumn k\n\t\tdataType: string\n"),
        (f"{_M}/relationships.tmdl", "relationship r\n\tfromColumn: A.k\n\ttoColumn: B.k\n"),
    ]
    hits = _ids(run_audit(build_graph(files), NO_REPORT), "X2")
    assert any("string" in f.message for f in hits)


def test_x2_snowflake_three_hops():
    rel = (
        "relationship r1\n\tfromColumn: F.a\n\ttoColumn: D1.a\n"
        "relationship r2\n\tfromColumn: D1.b\n\ttoColumn: D2.b\n"
        "relationship r3\n\tfromColumn: D2.c\n\ttoColumn: D3.c\n"
    )
    hits = _ids(run_audit(build_graph([(f"{_M}/relationships.tmdl", rel)]), NO_REPORT), "X2")
    assert any("snowflake" in f.message for f in hits)


def test_x2_bidi_skipped_entirely():
    files = [
        (f"{_M}/relationships.tmdl",
         "relationship r\n\tcrossFilteringBehavior: bothDirections\n"
         "\tfromCardinality: many\n\ttoCardinality: many\n"
         "\tfromColumn: A.k\n\ttoColumn: B.k\n"),
    ]
    assert not _ids(run_audit(build_graph(files), NO_REPORT), "X2")


def test_x3_depth_and_cycle():
    chain = "table T\n" + "".join(
        f"\tmeasure M{i} = [M{i + 1}] + 1\n" for i in range(5)
    ) + "\tmeasure M5 = 1\n"
    hits = _ids(run_audit(build_graph([(f"{_M}/tables/T.tmdl", chain)]), NO_REPORT), "X3")
    assert any("depth" in f.message for f in hits)
    cyc = "table C\n\tmeasure A = [B]\n\tmeasure B = [A]\n"
    hits = _ids(run_audit(build_graph([(f"{_M}/tables/C.tmdl", cyc)]), NO_REPORT), "X3")
    assert any("circular" in f.message for f in hits)


def test_x3_duplicate_logic_cross_table_cites_d3():
    files = [
        (f"{_M}/tables/A.tmdl", "table A\n\tmeasure One = SUM(F[x])\n"),
        (f"{_M}/tables/B.tmdl", "table B\n\tmeasure Two = SUM(F[x])\n"),
    ]
    hits = _ids(run_audit(build_graph(files), NO_REPORT), "X3")
    assert any("D3" in f.message for f in hits)


def test_x4_unmarked_date_table_cites_d7():
    files = [
        (f"{_M}/tables/Dates.tmdl", "table Dates\n\tcolumn date_key\n"),
        (f"{_M}/tables/F.tmdl", "table F\n\tcolumn date_key\n"),
        (f"{_M}/relationships.tmdl",
         "relationship r\n\tfromColumn: F.date_key\n\ttoColumn: Dates.date_key\n"),
    ]
    hits = _ids(run_audit(build_graph(files), NO_REPORT), "X4")
    assert any("D7" in f.message for f in hits)


def test_x4_marked_date_table_silent():
    files = [
        (f"{_M}/tables/Dates.tmdl",
         "table Dates\n\tdataCategory: Time\n\tcolumn date_key\n\t\tisKey\n"),
        (f"{_M}/tables/F.tmdl", "table F\n\tcolumn date_key\n"),
        (f"{_M}/relationships.tmdl",
         "relationship r\n\tfromColumn: F.date_key\n\ttoColumn: Dates.date_key\n"),
    ]
    hits = _ids(run_audit(build_graph(files), NO_REPORT), "X4")
    assert not any("D7" in f.message for f in hits)


def test_x4_summarized_feeding_nothing():
    g = build_graph(
        [(f"{_M}/tables/T.tmdl", "table T\n\tcolumn q\n\t\tsummarizeBy: sum\n")]
    )
    hits = _ids(run_audit(g, NO_REPORT), "X4")
    assert any("T[q]" in f.locator and "summarize" in f.message.lower() for f in hits)


def test_no_finding_for_unresolved_refs():
    # [Ghost] resolves to nothing: conservative core says it must not create
    # unused-column findings for anything, nor crash.
    g = build_graph(
        [(f"{_M}/tables/T.tmdl", "table T\n\tmeasure M = [Ghost]\n")]
    )
    findings = run_audit(g, NO_REPORT)
    assert not any("Ghost" in f.locator for f in findings)
