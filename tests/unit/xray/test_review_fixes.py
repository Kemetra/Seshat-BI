"""Regression pins for the five PR #550 review findings.

Each test fails against the pre-fix behavior, so none of these defects can
return silently.
"""

from __future__ import annotations

import argparse
import subprocess

import pytest

from seshat.cli.commands.xray import xray_main
from seshat.tmdl import normalize_measure_body, parse_tmdl
from seshat.xray.audit import _measure_depths, run_audit
from seshat.xray.bindings import read_bindings
from seshat.xray.diff import diff_models
from seshat.xray.graph import build_graph
from tests.unit._gitfix import commit_all, make_git_repo

pytestmark = pytest.mark.unit

_M = "m/X.SemanticModel/definition"
NO_REPORT = read_bindings([])

# A multi-line measure whose FIRST body line is a `//` comment -- the shape
# that previously swallowed the entire remaining body.
COMMENTED = (
    "table T\n"
    "\tmeasure M =\n"
    "\t\t// explain the intent\n"
    "\t\tVAR x = SUM(T[a])\n"
    "\t\tRETURN x\n"
    "\tcolumn a\n"
)


# --- P1: line breaks preserved before comment stripping ---------------------


def test_multiline_comment_does_not_swallow_the_body():
    table = parse_tmdl(COMMENTED)
    assert table is not None
    body = table.measures[0].expression
    assert "\n" in body, "continuation lines must keep their boundaries"
    # normalize_measure_body lowercases, so compare against lowercase text.
    assert "return x" in normalize_measure_body(body)


def test_commented_measure_still_contributes_column_references():
    graph = build_graph([(f"{_M}/tables/T.tmdl", COMMENTED)])
    assert ("T", "a") in graph.column_refs["M"]


def test_commented_column_is_not_falsely_unused():
    graph = build_graph([(f"{_M}/tables/T.tmdl", COMMENTED)])
    unused = [f for f in run_audit(graph, NO_REPORT) if f.finding_id == "X1"]
    assert not [f for f in unused if f.locator == "T[a]"]


def test_change_after_a_comment_line_is_a_semantic_diff():
    head = COMMENTED.replace("SUM(T[a])", "SUM(T[a]) * 2")
    changes = diff_models(
        [(f"{_M}/tables/T.tmdl", COMMENTED)], [(f"{_M}/tables/T.tmdl", head)]
    )
    assert any(c.bucket == "semantic" and c.subject == "T[M]" for c in changes), (
        "logic edited after a comment line must not diff as silent"
    )


# --- P1: RLS role filters participate in the diff ---------------------------

ROLE_BASE = 'role Readers\n\tfilter Sales = Sales[region] = "EU"\n'
ROLE_HEAD = 'role Readers\n\tfilter Sales = Sales[region] <> "EU"\n'


def test_rls_filter_change_is_semantic():
    changes = diff_models(
        [(f"{_M}/roles/Readers.tmdl", ROLE_BASE)],
        [(f"{_M}/roles/Readers.tmdl", ROLE_HEAD)],
    )
    semantic = [c for c in changes if c.bucket == "semantic"]
    assert any(c.kind == "role" and c.subject == "Readers" for c in semantic)


def test_rls_reformatting_only_is_not_semantic():
    reformatted = 'role Readers\n\tfilter Sales =  Sales[region]   =  "EU"\n'
    changes = diff_models(
        [(f"{_M}/roles/Readers.tmdl", ROLE_BASE)],
        [(f"{_M}/roles/Readers.tmdl", reformatted)],
    )
    assert not [c for c in changes if c.kind == "role"]


def test_new_and_removed_roles_are_reported():
    added = diff_models([], [(f"{_M}/roles/R.tmdl", ROLE_BASE)])
    assert any(c.bucket == "additive" and c.kind == "role" for c in added)
    removed = diff_models([(f"{_M}/roles/R.tmdl", ROLE_BASE)], [])
    assert any(c.bucket == "removed" and c.kind == "role" for c in removed)


# --- P2: annotation form of the date-table marker --------------------------


def test_annotation_date_marker_silences_x4():
    files = [
        (
            f"{_M}/tables/Dates.tmdl",
            "table Dates\n\tannotation PBI_DateTable = true\n\tcolumn date_key\n",
        ),
        (f"{_M}/tables/F.tmdl", "table F\n\tcolumn date_key\n"),
        (
            f"{_M}/relationships.tmdl",
            "relationship r\n\tfromColumn: F.date_key\n\ttoColumn: Dates.date_key\n",
        ),
    ]
    hits = run_audit(build_graph(files), NO_REPORT)
    assert not [f for f in hits if f.finding_id == "X4" and "D7" in f.message], (
        "X4 cites D7, so it must accept every marker D7 accepts"
    )


# --- P2: every cycle member recorded ---------------------------------------


def test_two_node_cycle_reports_both_members():
    _, cyclic = _measure_depths({"A": frozenset({"B"}), "B": frozenset({"A"})})
    assert set(cyclic) == {"A", "B"}


def test_three_node_cycle_reports_all_members():
    refs = {
        "A": frozenset({"B"}),
        "B": frozenset({"C"}),
        "C": frozenset({"A"}),
    }
    assert set(_measure_depths(refs)[1]) == {"A", "B", "C"}


def test_cycle_findings_name_each_measure():
    cyc = "table C\n\tmeasure A = [B]\n\tmeasure B = [A]\n"
    hits = [
        f
        for f in run_audit(build_graph([(f"{_M}/tables/C.tmdl", cyc)]), NO_REPORT)
        if "circular" in f.message
    ]
    assert {f.locator for f in hits} == {"C[A]", "C[B]"}


# --- P2: per-model partitioning -------------------------------------------


def test_two_models_do_not_cross_resolve(tmp_path, capsys):
    """Same table+column name in two models must not mask an unused column."""
    repo = make_git_repo(tmp_path)
    for stem in ("Alpha", "Beta"):
        tables = repo / f"{stem}.SemanticModel" / "definition" / "tables"
        tables.mkdir(parents=True)
        body = "table Shared\n\tcolumn c\n"
        if stem == "Alpha":  # only Alpha references its own column
            body = "table Shared\n\tmeasure M = SUM(Shared[c])\n\tcolumn c\n"
        (tables / "Shared.tmdl").write_text(body, encoding="utf-8")
    commit_all(repo, "two models")
    assert xray_main(argparse.Namespace(repo=str(repo), output_format="json")) == 0
    out = capsys.readouterr().out
    # Beta's unreferenced column must still be reported, model-qualified.
    assert "Beta.SemanticModel: Shared[c]" in out
    assert "Alpha.SemanticModel: Shared[c]" not in out


def test_report_bindings_are_paired_by_stem(tmp_path, capsys):
    """Another model's report is not evidence that THIS column is used."""
    repo = make_git_repo(tmp_path)
    tables = repo / "Alpha.SemanticModel" / "definition" / "tables"
    tables.mkdir(parents=True)
    (tables / "T.tmdl").write_text("table T\n\tcolumn c\n", encoding="utf-8")
    # A report belonging to a DIFFERENT stem binds T[c].
    visuals = repo / "Beta.Report" / "definition" / "pages" / "p" / "visuals" / "v"
    visuals.mkdir(parents=True)
    (visuals / "visual.json").write_text(
        '{"field": {"Column": {"Expression": {"SourceRef": {"Entity": "T"}},'
        ' "Property": "c"}}}',
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    commit_all(repo, "mismatched stems")
    assert xray_main(argparse.Namespace(repo=str(repo), output_format="json")) == 0
    out = capsys.readouterr().out
    assert "T[c]" in out, "the foreign report must not suppress the finding"
    assert '"report_scanned":false' in out
