"""Regression pins for the two fourth-round PR #551 review findings.

Both were regressions from this PR's own fixes: a malformed-manifest CRASH and
an incomplete case-insensitivity path.
"""

from __future__ import annotations

import pytest

from seshat.cli.commands.xray import _by_path_target, _declared_model
from seshat.xray.audit import run_audit
from seshat.xray.bindings import read_bindings
from seshat.xray.graph import build_graph

pytestmark = pytest.mark.unit

_M = "m/X.SemanticModel/definition"


# --- a malformed .pbir degrades, never crashes -----------------------------


@pytest.mark.parametrize(
    ("label", "body"),
    [
        ("json-array", "[]"),
        ("json-string", '"nope"'),
        ("null-reference", '{"datasetReference": null}'),
        ("reference-not-object", '{"datasetReference": "x"}'),
        ("bypath-not-object", '{"datasetReference": {"byPath": 7}}'),
        ("path-not-string", '{"datasetReference": {"byPath": {"path": 7}}}'),
        ("unparseable", "{not json"),
        ("empty", ""),
    ],
)
def test_unusable_manifest_returns_none_without_raising(label, body):
    assert _by_path_target(body) is None, label


def test_declared_model_degrades_on_a_malformed_manifest():
    """No exception, and no ownership claim -- the caller falls back to stem."""
    files = [("R.Report/definition.pbir", "[]")]
    assert _declared_model("R.Report", files) is None


def test_valid_manifest_still_resolves():
    files = [
        (
            "R.Report/definition.pbir",
            '{"datasetReference": {"byPath": {"path": "../Alpha.SemanticModel"}}}',
        )
    ]
    assert _declared_model("R.Report", files) == "Alpha.SemanticModel"


# --- hierarchy references keep the DECLARED table spelling -----------------

HIER = (
    "table D\n\tcolumn CalendarYear\n\t\tdataType: int64\n"
    "\thierarchy Calendar\n\t\tlevel Year\n\t\t\tcolumn: CalendarYear\n"
)


def _visual(entity: str, hierarchy: str, level: str) -> str:
    return (
        '{"field":{"HierarchyLevel":{"Expression":{"Hierarchy":{"Expression":'
        f'{{"SourceRef":{{"Entity":"{entity}"}}}},"Hierarchy":"{hierarchy}"}}}},'
        f'"Level":"{level}"}}}}}}'
    )


@pytest.mark.parametrize(
    ("entity", "hierarchy", "level"),
    [
        ("D", "Calendar", "Year"),  # exact
        ("d", "calendar", "year"),  # all lowercase
        ("D", "CALENDAR", "YEAR"),  # mixed
    ],
)
def test_hierarchy_binding_resolves_regardless_of_casing(entity, hierarchy, level):
    bindings = read_bindings(
        [
            (
                "r/X.Report/definition/pages/p/visuals/v/visual.json",
                _visual(entity, hierarchy, level),
            )
        ]
    )
    graph = build_graph([(f"{_M}/tables/D.tmdl", HIER)])
    unused = {f.locator for f in run_audit(graph, bindings) if f.finding_id == "X1"}
    assert "D[CalendarYear]" not in unused, (
        "a bound hierarchy level must mark its backing column used, "
        "whatever casing PBIR uses"
    )


def test_unknown_hierarchy_still_falls_back_conservatively():
    """An undeclared hierarchy keeps the old behavior: add a reference rather
    than invent a finding."""
    bindings = read_bindings(
        [
            (
                "r/X.Report/definition/pages/p/visuals/v/visual.json",
                _visual("D", "NotDeclared", "CalendarYear"),
            )
        ]
    )
    graph = build_graph([(f"{_M}/tables/D.tmdl", HIER)])
    unused = {f.locator for f in run_audit(graph, bindings) if f.finding_id == "X1"}
    assert "D[CalendarYear]" not in unused
