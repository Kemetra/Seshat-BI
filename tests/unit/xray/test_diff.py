"""Semantic model diff tests (Task 5)."""

from __future__ import annotations

import pytest

from seshat.xray.diff import diff_models

pytestmark = pytest.mark.unit

_M = "m/X.SemanticModel/definition"


def _files(table_body: str, rels: str = "") -> list[tuple[str, str]]:
    files = [(f"{_M}/tables/T.tmdl", table_body)]
    if rels:
        files.append((f"{_M}/relationships.tmdl", rels))
    return files


def _by_bucket(changes, bucket):
    return [c for c in changes if c.bucket == bucket]


def test_measure_body_change_is_semantic():
    base = _files("table T\n\tmeasure M = SUM(T[a])\n\tcolumn a\n")
    head = _files("table T\n\tmeasure M = SUM(T[a]) + 1\n\tcolumn a\n")
    semantic = _by_bucket(diff_models(base, head), "semantic")
    assert any(c.subject == "T[M]" and "logic changed" in c.sentence for c in semantic)


def test_formatting_only_churn_is_cosmetic_or_silent():
    base = _files("table T\n\tmeasure M = SUM(T[a])\n\tcolumn a\n")
    head = _files(
        "table T\n\tmeasure M = sum ( T[a] )\n\t\tformatString: #,0\n\tcolumn a\n"
    )
    changes = diff_models(base, head)
    assert not _by_bucket(changes, "semantic")
    assert any(c.subject == "T[M]" for c in _by_bucket(changes, "cosmetic"))


def test_column_type_change_semantic_sortby_cosmetic():
    base = _files("table T\n\tcolumn a\n\t\tdataType: int64\n\tcolumn b\n")
    head = _files(
        "table T\n\tcolumn a\n\t\tdataType: string\n\tcolumn b\n\t\tsortByColumn: a\n"
    )
    changes = diff_models(base, head)
    assert any(c.subject == "T[a]" for c in _by_bucket(changes, "semantic"))
    assert any(c.subject == "T[b]" for c in _by_bucket(changes, "cosmetic"))


def test_relationship_guid_churn_same_endpoints_not_reported():
    base = _files(
        "table T\n\tcolumn a\n",
        "relationship guid-1\n\tfromColumn: T.a\n\ttoColumn: D.k\n",
    )
    head = _files(
        "table T\n\tcolumn a\n",
        "relationship guid-2\n\tfromColumn: T.a\n\ttoColumn: D.k\n",
    )
    assert not [c for c in diff_models(base, head) if c.kind == "relationship"]


def test_relationship_activity_flip_semantic():
    base = _files(
        "table T\n\tcolumn a\n", "relationship r\n\tfromColumn: T.a\n\ttoColumn: D.k\n"
    )
    head = _files(
        "table T\n\tcolumn a\n",
        "relationship r\n\tisActive: false\n\tfromColumn: T.a\n\ttoColumn: D.k\n",
    )
    semantic = _by_bucket(diff_models(base, head), "semantic")
    assert any(c.kind == "relationship" for c in semantic)


def test_new_measure_additive_lists_references():
    base = _files("table T\n\tcolumn a\n")
    head = _files("table T\n\tmeasure New = SUM(T[a])\n\tcolumn a\n")
    additive = _by_bucket(diff_models(base, head), "additive")
    assert any(c.subject == "T[New]" and "T[a]" in c.sentence for c in additive)


def test_removed_table_reported():
    base = _files("table T\n\tcolumn a\n") + [
        (f"{_M}/tables/Gone.tmdl", "table Gone\n\tcolumn x\n")
    ]
    head = _files("table T\n\tcolumn a\n")
    removed = _by_bucket(diff_models(base, head), "removed")
    assert any(c.kind == "table" and c.subject == "Gone" for c in removed)
