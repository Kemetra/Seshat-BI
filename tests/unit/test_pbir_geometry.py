"""Unit tests for the PBIR geometry writer (increment D)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from seshat.pbir_geometry import PbirGeometryError, set_geometry

pytestmark = pytest.mark.unit

FIXTURE = Path(__file__).parent.parent / "fixtures" / "pbir" / "geometry.Report"


def _report(tmp_path: Path) -> Path:
    dst = tmp_path / "geometry.Report"
    shutil.copytree(FIXTURE, dst)
    return dst


def _visual(report: Path, v: str) -> Path:
    return report / "definition" / "pages" / "pg" / "visuals" / v / "visual.json"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8-sig"))


def test_valid_move_writes_position_and_preserves_binding(tmp_path: Path):
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    before = _load(vp)["visual"]
    out = set_geometry(vp, {"x": 200, "y": 150, "width": 400, "height": 250})
    assert out == vp
    after = _load(vp)
    assert after["position"]["x"] == 200
    assert after["position"]["width"] == 400
    # untouched position keys preserved
    assert after["position"]["z"] == 1000
    assert after["position"]["tabOrder"] == 1000
    # binding byte-identical (FR-003)
    assert after["visual"] == before


def test_offcanvas_rejected_using_REAL_canvas_not_hardcoded_default(tmp_path: Path):
    # Canvas is 1600x900. This rectangle (x=1300,w=250 -> right edge 1550) is
    # on-canvas at the REAL 1600-wide canvas but would be off-canvas at a
    # hardcoded 1280x720 default (1550 > 1280). A writer that hardcodes canvas
    # dims instead of reading page.json would wrongly reject this valid write.
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    out = set_geometry(vp, {"x": 1300, "y": 100, "width": 250, "height": 200})
    assert out == vp  # valid at real 1600 wide; a hardcoded-1280 writer would reject


def test_truly_offcanvas_rejected(tmp_path: Path):
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="off-canvas"):
        set_geometry(
            vp, {"x": 1500, "y": 100, "width": 300, "height": 200}
        )  # 1800>1600


def test_negative_coord_rejected(tmp_path: Path):
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="off-canvas"):
        set_geometry(vp, {"x": -10, "y": 100, "width": 100, "height": 100})


def test_overlap_is_allowed(tmp_path: Path):
    # Move vA to fully overlap vB's rectangle -> must NOT raise (overlap allowed).
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    out = set_geometry(vp, {"x": 300, "y": 250, "width": 300, "height": 300})
    assert out == vp


def test_visualtype_key_is_not_in_allowlist(tmp_path: Path):
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="allow-list"):
        set_geometry(vp, {"visualType": "line"})


def test_nonnumeric_value_rejected(tmp_path: Path):
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="must be a number"):
        set_geometry(vp, {"x": "left"})


def test_missing_page_json_is_clean_error_no_hardcode(tmp_path: Path):
    report = _report(tmp_path)
    (report / "definition" / "pages" / "pg" / "page.json").unlink()
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="page.json not found"):
        set_geometry(vp, {"x": 200, "y": 150, "width": 300, "height": 300})


def test_repeated_move_is_allowed_no_force_gate(tmp_path: Path):
    # Moving a visual repeatedly is the operation, not an error -- there is no
    # force gate (position keys always pre-exist; a differs->refuse gate would
    # block every real move). Each call just re-lays-out.
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    assert set_geometry(vp, {"x": 200}) == vp  # 100 -> 200, no force needed
    assert set_geometry(vp, {"x": 250}) == vp  # 200 -> 250, still fine
    assert _load(vp)["position"]["x"] == 250


def test_bool_value_rejected(tmp_path):
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="must be a number"):
        set_geometry(vp, {"x": True})


def test_nonnumeric_page_json_dims_is_clean_error(tmp_path):
    report = _report(tmp_path)
    page = report / "definition" / "pages" / "pg" / "page.json"
    d = json.loads(page.read_text(encoding="utf-8-sig"))
    d["width"] = "wide"  # non-numeric
    page.write_text(json.dumps(d), encoding="utf-8")
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="numeric"):
        set_geometry(vp, {"x": 200, "y": 150, "width": 300, "height": 300})


def test_partial_move_overrunning_unchanged_width_is_rejected(tmp_path):
    report = _report(tmp_path)
    vp = _visual(report, "vA")  # x=100, width=300 on 1600-wide canvas
    with pytest.raises(PbirGeometryError, match="off-canvas"):
        set_geometry(vp, {"x": 1400})  # 1400 + unchanged 300 = 1700 > 1600


def test_negative_width_rejected(tmp_path):
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="must be positive"):
        set_geometry(vp, {"width": -50})


def test_negative_dimension_cannot_escape_offcanvas_guard(tmp_path):
    # Origin x=5000 is far off a 1600-wide canvas, but width=-4000 makes
    # rx + rw = 1000, which is NOT > canvas_w -- the overrun half of the
    # off-canvas check alone would wrongly accept this. The width/height
    # positivity guard must catch it first.
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="must be positive"):
        set_geometry(vp, {"x": 5000, "width": -4000})


def test_zero_size_rejected(tmp_path):
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="must be positive"):
        set_geometry(vp, {"width": 0, "height": 0})
