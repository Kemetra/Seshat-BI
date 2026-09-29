"""Unit tests for the PBIR per-visual formatting writer (adapter increment B).

The fixture visual.json is a REAL Microsoft PBIP-sample lineChart (data-bound,
with objects + visualContainerObjects) from data-goblin/power-bi-visual-templates
-- so the writer is proven against real wire format, not a self-invented shape.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from seshat.pbir_visual_format import PbirFormatError, apply_visual_format

pytestmark = pytest.mark.unit

FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures/pbir/visual_fmt.Report/definition/pages/pg/visuals/v1/visual.json"
)


def _copy(tmp: Path) -> Path:
    dst = tmp / "x.Report" / "v" / "visual.json"
    dst.parent.mkdir(parents=True)
    shutil.copy(FIXTURE, dst)
    return dst


def _query_of(path: Path) -> str:
    v = json.loads(path.read_text())["visual"]
    return json.dumps({"q": v.get("query"), "t": v.get("visualType")}, sort_keys=True)


def test_sets_container_title(tmp_path: Path) -> None:
    # The real fixture already has a title.text; overwriting it needs force.
    vj = _copy(tmp_path)
    apply_visual_format(
        vj,
        {"visualContainerObjects": {"title": {"show": True, "text": "Sales"}}},
        force=True,
    )
    doc = json.loads(vj.read_text())
    props = doc["visual"]["visualContainerObjects"]["title"][0]["properties"]
    assert props["text"] == {"expr": {"Literal": {"Value": "'Sales'"}}}
    assert props["show"] == {"expr": {"Literal": {"Value": "true"}}}


def test_sets_a_new_group_property(tmp_path: Path) -> None:
    # `labels` does not pre-exist in the fixture -> a clean add, no force needed.
    vj = _copy(tmp_path)
    apply_visual_format(vj, {"objects": {"labels": {"show": True}}})
    doc = json.loads(vj.read_text())
    props = doc["visual"]["objects"]["labels"][0]["properties"]
    assert props["show"] == {"expr": {"Literal": {"Value": "true"}}}


def test_integer_property_uses_dax_long_suffix(tmp_path: Path) -> None:
    # PBIR integer literals carry the DAX long suffix (the real fixture uses 0L/70L).
    vj = _copy(tmp_path)
    apply_visual_format(
        vj, {"visualContainerObjects": {"dropShadow": {"shadowBlur": 12}}}, force=True
    )
    doc = json.loads(vj.read_text())
    props = doc["visual"]["visualContainerObjects"]["dropShadow"][0]["properties"]
    assert props["shadowBlur"] == {"expr": {"Literal": {"Value": "12L"}}}


def test_string_with_embedded_quote_is_doubled(tmp_path: Path) -> None:
    # An embedded single quote must be doubled ('') or the PBIR literal is malformed.
    vj = _copy(tmp_path)
    apply_visual_format(
        vj,
        {"visualContainerObjects": {"title": {"text": "Today's Sales"}}},
        force=True,
    )
    doc = json.loads(vj.read_text())
    props = doc["visual"]["visualContainerObjects"]["title"][0]["properties"]
    assert props["text"] == {"expr": {"Literal": {"Value": "'Today''s Sales'"}}}


def test_non_scalar_value_raises(tmp_path: Path) -> None:
    vj = _copy(tmp_path)
    with pytest.raises(PbirFormatError, match="bool/int/float/str"):
        apply_visual_format(vj, {"objects": {"labels": {"show": [1, 2]}}})


def test_data_binding_is_byte_identical(tmp_path: Path) -> None:
    # THE FR-003 guarantee: formatting must NOT change query/visualType.
    vj = _copy(tmp_path)
    before = _query_of(vj)
    apply_visual_format(
        vj,
        {
            "visualContainerObjects": {"title": {"text": "New"}},
            "objects": {"labels": {"show": True}},
        },
        force=True,
    )
    assert _query_of(vj) == before


def test_out_of_allowlist_container_refused(tmp_path: Path) -> None:
    vj = _copy(tmp_path)
    with pytest.raises(PbirFormatError, match="allow-list"):
        apply_visual_format(vj, {"query": {"anything": {}}})


def test_out_of_allowlist_group_refused(tmp_path: Path) -> None:
    vj = _copy(tmp_path)
    with pytest.raises(PbirFormatError, match="allow-list"):
        apply_visual_format(vj, {"objects": {"secretMeasure": {"x": 1}}})


def test_deterministic_reapply(tmp_path: Path) -> None:
    vj = _copy(tmp_path)
    fmt = {"objects": {"labels": {"show": True}}}  # a new group -> no force needed
    apply_visual_format(vj, fmt)
    first = vj.read_text()
    apply_visual_format(vj, fmt)  # identical value re-set is allowed (idempotent)
    assert vj.read_text() == first


def test_different_value_needs_force(tmp_path: Path) -> None:
    vj = _copy(tmp_path)
    apply_visual_format(vj, {"objects": {"labels": {"show": True}}})
    with pytest.raises(PbirFormatError, match="force"):
        apply_visual_format(vj, {"objects": {"labels": {"show": False}}})
    apply_visual_format(vj, {"objects": {"labels": {"show": False}}}, force=True)


def test_missing_visual_file_raises(tmp_path: Path) -> None:
    with pytest.raises(PbirFormatError, match="not found"):
        apply_visual_format(tmp_path / "nope.Report" / "visual.json", {})


def test_not_in_report_tree_refused(tmp_path: Path) -> None:
    stray = tmp_path / "loose" / "visual.json"
    stray.parent.mkdir(parents=True)
    shutil.copy(FIXTURE, stray)
    with pytest.raises(PbirFormatError, match="Report"):
        apply_visual_format(stray, {"objects": {"legend": {"show": True}}})


def test_invalid_json_raises(tmp_path: Path) -> None:
    vj = tmp_path / "x.Report" / "visual.json"
    vj.parent.mkdir(parents=True)
    vj.write_text("{not json")
    with pytest.raises(PbirFormatError, match="valid JSON"):
        apply_visual_format(vj, {"objects": {"legend": {"show": True}}})


# --- F141: a measure-bound property is a data binding, even under force ------

_MEASURE_TITLE = {
    "expr": {
        "Measure": {
            "Expression": {"SourceRef": {"Entity": "Sales"}},
            "Property": "Dynamic Title",
        }
    }
}


def _with_measure_title(tmp: Path) -> Path:
    vj = _copy(tmp)
    doc = json.loads(vj.read_text(encoding="utf-8"))
    vco = doc["visual"].setdefault("visualContainerObjects", {})
    vco["title"] = [{"properties": {"text": _MEASURE_TITLE}}]
    vj.write_text(json.dumps(doc), encoding="utf-8")
    return vj


def test_force_never_overwrites_a_measure_bound_property(tmp_path: Path) -> None:
    vj = _with_measure_title(tmp_path)
    before = vj.read_text(encoding="utf-8")
    fmt = {"visualContainerObjects": {"title": {"text": "Sales"}}}
    with pytest.raises(PbirFormatError, match="data binding"):
        apply_visual_format(vj, fmt, force=True)
    assert vj.read_text(encoding="utf-8") == before


def test_non_ascii_title_is_written_verbatim(tmp_path: Path) -> None:
    vj = _copy(tmp_path)
    arabic = "\u0645\u0628\u064a\u0639\u0627\u062a"
    fmt = {"objects": {"labels": {"text": arabic}}}
    apply_visual_format(vj, fmt)
    raw = vj.read_text(encoding="utf-8")
    assert arabic in raw
    assert "\\u0645" not in raw  # not ASCII-escaped


def test_force_never_overwrites_a_nested_field_value_colour(tmp_path: Path) -> None:
    """Field-value colours nest the binding: fill.solid.color.expr.Measure."""
    vj = _copy(tmp_path)
    doc = json.loads(vj.read_text(encoding="utf-8"))
    fill = {"solid": {"color": _MEASURE_TITLE}}
    doc["visual"].setdefault("objects", {})["dataPoint"] = [
        {"properties": {"fill": fill}}
    ]
    vj.write_text(json.dumps(doc), encoding="utf-8")
    before = vj.read_text(encoding="utf-8")
    with pytest.raises(PbirFormatError, match="data binding"):
        apply_visual_format(vj, {"objects": {"dataPoint": {"fill": "x"}}}, force=True)
    assert vj.read_text(encoding="utf-8") == before
