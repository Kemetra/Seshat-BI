"""Regression pins for the six PR #550 second-round review findings.

Each test fails against the pre-fix behavior.
"""

from __future__ import annotations

import argparse
import subprocess

import pytest

from seshat.cli.commands.xray import xray_main
from seshat.tmdl import parse_tmdl
from seshat.xray.audit import run_audit
from seshat.xray.bindings import read_bindings
from seshat.xray.diff import diff_models
from seshat.xray.graph import build_graph
from tests.unit._gitfix import commit_all, make_git_repo

pytestmark = pytest.mark.unit

_M = "m/X.SemanticModel/definition"
NO_REPORT = read_bindings([])


def _f(path: str, text: str) -> tuple[str, str]:
    return (path, text)


# --- R2-1 (P1): string literals are behavior, not formatting ---------------


def test_string_literal_case_change_is_semantic():
    base = _f(f"{_M}/tables/T.tmdl", 'table T\n\tmeasure L = "OK"\n')
    head = _f(f"{_M}/tables/T.tmdl", 'table T\n\tmeasure L = "ok"\n')
    changes = diff_models([base], [head])
    assert any(c.bucket == "semantic" and c.subject == "T[L]" for c in changes)


def test_string_literal_whitespace_change_is_semantic():
    base = _f(f"{_M}/tables/T.tmdl", 'table T\n\tmeasure L = "Grand Total"\n')
    head = _f(f"{_M}/tables/T.tmdl", 'table T\n\tmeasure L = "Grand  Total"\n')
    changes = diff_models([base], [head])
    assert any(c.bucket == "semantic" for c in changes)


def test_code_reformatting_outside_literals_is_still_not_semantic():
    base = _f(f"{_M}/tables/T.tmdl", 'table T\n\tmeasure L = IF(1=1,"OK","No")\n')
    head = _f(
        f"{_M}/tables/T.tmdl", 'table T\n\tmeasure L = IF( 1 = 1 , "OK" , "No" )\n'
    )
    assert not [c for c in diff_models([base], [head]) if c.bucket == "semantic"]


# --- R2-2: diff partitioned by semantic-model directory --------------------

_A = "a/Alpha.SemanticModel/definition/tables/Shared.tmdl"
_B = "b/Beta.SemanticModel/definition/tables/Shared.tmdl"


def test_same_table_name_in_two_models_does_not_mask_a_change():
    base = [
        _f(_A, "table Shared\n\tmeasure M = 1\n"),
        _f(_B, "table Shared\n\tmeasure M = 1\n"),
    ]
    head = [
        _f(_A, "table Shared\n\tmeasure M = 2\n"),  # changed
        _f(_B, "table Shared\n\tmeasure M = 1\n"),  # unchanged
    ]
    semantic = [c for c in diff_models(base, head) if c.bucket == "semantic"]
    assert len(semantic) == 1, f"expected exactly Alpha's change, got {semantic}"
    assert "Alpha.SemanticModel" in semantic[0].subject


def test_single_model_subjects_stay_unqualified():
    base = [_f(_A, "table Shared\n\tmeasure M = 1\n")]
    head = [_f(_A, "table Shared\n\tmeasure M = 2\n")]
    semantic = [c for c in diff_models(base, head) if c.bucket == "semantic"]
    assert semantic and semantic[0].subject == "Shared[M]"


# --- R2-3: report ownership from definition.pbir ---------------------------

PBIR = '{"datasetReference": {"byPath": {"path": "../Alpha.SemanticModel"}}}'
VISUAL = (
    '{"field": {"Column": {"Expression": {"SourceRef": {"Entity": "T"}},'
    ' "Property": "c"}}}'
)


def test_pbir_pairs_a_report_whose_stem_differs(tmp_path, capsys):
    repo = make_git_repo(tmp_path)
    tables = repo / "Alpha.SemanticModel" / "definition" / "tables"
    tables.mkdir(parents=True)
    (tables / "T.tmdl").write_text("table T\n\tcolumn c\n", encoding="utf-8")
    report = repo / "Renamed.Report"
    (report / "definition" / "pages" / "p" / "visuals" / "v").mkdir(parents=True)
    (report / "definition.pbir").write_text(PBIR, encoding="utf-8")
    (
        report / "definition" / "pages" / "p" / "visuals" / "v" / "visual.json"
    ).write_text(VISUAL, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    commit_all(repo, "mismatched stem paired via pbir")
    assert xray_main(argparse.Namespace(repo=str(repo), output_format="json")) == 0
    out = capsys.readouterr().out
    assert '"report_scanned":true' in out, "pbir byPath must associate the report"
    assert "T[c]" not in out, "a bound column must not be reported unused"


# --- R2-4: DAX identifiers are case-insensitive ---------------------------


def test_case_differing_reference_resolves():
    text = (
        "table Sales\n\tmeasure M = SUM(sales[AMOUNT])\n"
        "\tcolumn amount\n\t\tdataType: double\n"
    )
    graph = build_graph([_f(f"{_M}/tables/Sales.tmdl", text)])
    assert ("Sales", "amount") in graph.column_refs["M"], "declared spelling expected"
    assert not graph.unresolved["M"]


def test_case_differing_reference_prevents_false_unused():
    text = (
        "table Sales\n\tmeasure M = SUM(sales[AMOUNT])\n"
        "\tcolumn amount\n\t\tdataType: double\n"
    )
    graph = build_graph([_f(f"{_M}/tables/Sales.tmdl", text)])
    x1 = [f for f in run_audit(graph, NO_REPORT) if f.finding_id == "X1"]
    assert not [f for f in x1 if f.locator == "Sales[amount]"]


def test_bare_measure_reference_is_case_insensitive():
    text = "table T\n\tmeasure Revenue = 1\n\tmeasure M = [revenue] + 1\n"
    graph = build_graph([_f(f"{_M}/tables/T.tmdl", text)])
    assert "Revenue" in graph.measure_refs["M"]


# --- R2-5: calculated-column expressions ---------------------------------

CALC = "table T\n\tcolumn Margin = [Price] - [Cost]\n\t\tdataType: double\n"


def test_calculated_column_name_excludes_its_expression():
    table = parse_tmdl(CALC)
    assert table is not None
    assert [c.name for c in table.columns] == ["Margin"]


def test_calculated_column_expression_is_captured():
    table = parse_tmdl(CALC)
    assert table is not None
    assert "[Price]" in (table.columns[0].expression or "")


def test_calculated_column_logic_change_is_semantic():
    head = CALC.replace("[Price] - [Cost]", "[Price] - [Cost] - [Tax]")
    changes = diff_models(
        [_f(f"{_M}/tables/T.tmdl", CALC)], [_f(f"{_M}/tables/T.tmdl", head)]
    )
    semantic = [c for c in changes if c.bucket == "semantic"]
    assert any(c.subject == "T[Margin]" for c in semantic)
    assert not [c for c in changes if c.bucket in ("additive", "removed")], (
        "a logic edit must not read as a rename"
    )


def test_quoted_calculated_column_is_parsed():
    text = "table T\n\tcolumn 'Gross Margin' = [Price] - [Cost]\n"
    table = parse_tmdl(text)
    assert table is not None
    assert table.columns[0].name == "Gross Margin"
    assert "[Price]" in (table.columns[0].expression or "")


# --- R2-6: hierarchy levels resolve to their backing column --------------

HIER = (
    "table D\n"
    "\tcolumn CalendarYear\n\t\tdataType: int64\n"
    "\thierarchy Calendar\n"
    "\t\tlevel Year\n"
    "\t\t\tcolumn: CalendarYear\n"
)
HIER_VISUAL = (
    '{"field": {"HierarchyLevel": {"Expression": {"Hierarchy": {"Expression":'
    ' {"SourceRef": {"Entity": "D"}}, "Hierarchy": "Calendar"}},'
    ' "Level": "Year"}}}'
)


def test_hierarchy_membership_is_parsed():
    table = parse_tmdl(HIER)
    assert table is not None
    assert table.hierarchies
    assert table.hierarchies[0].name == "Calendar"
    assert table.hierarchies[0].levels == (("Year", "CalendarYear"),)


def test_hierarchy_level_binding_marks_the_backing_column_used():
    bindings = read_bindings(
        [_f("r/X.Report/definition/pages/p/visuals/v/visual.json", HIER_VISUAL)]
    )
    graph = build_graph([_f(f"{_M}/tables/D.tmdl", HIER)])
    x1 = [f for f in run_audit(graph, bindings) if f.finding_id == "X1"]
    assert not [f for f in x1 if f.locator == "D[CalendarYear]"], (
        "a hierarchy-level binding must count as using its source column"
    )
