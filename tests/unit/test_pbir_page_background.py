"""Unit tests for the PBIR page-background writer (adapter increment C).

The wire format (the ResourcePackageItem image URL, PackageType 1) is taken from a
real Power BI Desktop-authored sample. The fixture here is a GENERIC page + a
generic placeholder asset (no tenant/brand asset, no client page -- Principle VII).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from seshat.pbir_page_background import PbirPageBgError, set_page_background

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "pbir"
FX_REPORT = FIXTURES / "page_bg.Report"
ASSET = FIXTURES / "placeholder-asset.png"


def _report_copy(tmp: Path) -> Path:
    dst = tmp / "R.Report"
    shutil.copytree(FX_REPORT, dst)
    return dst


def _page(report: Path) -> dict:
    return json.loads((report / "definition/pages/pg/page.json").read_text())


def _report(report: Path) -> dict:
    return json.loads((report / "definition/report.json").read_text())


def test_sets_background_full_end_to_end(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    written = set_page_background(ASSET, report, "pg", scaling="Fill")
    # asset copied into RegisteredResources
    asset_dest = report / "StaticResources/RegisteredResources/placeholder-asset.png"
    assert asset_dest in written
    assert asset_dest.exists()
    # registered in report.json
    reg = next(
        p
        for p in _report(report)["resourcePackages"]
        if p["name"] == "RegisteredResources"
    )
    assert reg["items"][0] == {
        "name": "placeholder-asset.png",
        "path": "placeholder-asset.png",
        "type": "Image",
    }


def test_image_url_is_resourcepackageitem(tmp_path: Path) -> None:
    # THE format that could not be guessed: url is a ResourcePackageItem, not a Literal.
    report = _report_copy(tmp_path)
    set_page_background(ASSET, report, "pg", scaling="Fit")
    bg = _page(report)["objects"]["background"][0]["properties"]["image"]["image"]
    assert bg["url"] == {
        "expr": {
            "ResourcePackageItem": {
                "PackageName": "RegisteredResources",
                "PackageType": 1,
                "ItemName": "placeholder-asset.png",
            }
        }
    }
    assert bg["scaling"] == {"expr": {"Literal": {"Value": "'Fit'"}}}
    # display name KEEPS the extension (matches the real Desktop sample's 'name.ico')
    assert bg["name"] == {"expr": {"Literal": {"Value": "'placeholder-asset.png'"}}}


def test_transparency_is_raw_0D_literal(tmp_path: Path) -> None:
    # Verbatim from the real sample: transparency is the RAW decimal literal "0D"
    # (opaque), NOT a quoted string '0D'. Absent transparency can render invisible.
    report = _report_copy(tmp_path)
    set_page_background(ASSET, report, "pg")
    props = _page(report)["objects"]["background"][0]["properties"]
    assert props["transparency"] == {"expr": {"Literal": {"Value": "0D"}}}


def test_other_page_objects_are_preserved(tmp_path: Path) -> None:
    # The fixture page has an outspacePane object; it must survive untouched.
    report = _report_copy(tmp_path)
    before = _page(report)["objects"]["outspacePane"]
    set_page_background(ASSET, report, "pg")
    after = _page(report)
    assert after["objects"]["outspacePane"] == before
    assert "background" in after["objects"]  # and the background was added


def test_schema_preserved(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    set_page_background(ASSET, report, "pg")
    assert _page(report)["$schema"].endswith("page/2.1.0/schema.json")
    assert _report(report)["$schema"].endswith("report/3.3.0/schema.json")


def test_invalid_scaling_refused(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    with pytest.raises(PbirPageBgError, match="scaling"):
        set_page_background(ASSET, report, "pg", scaling="Stretch")


def test_missing_asset_raises(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    with pytest.raises(PbirPageBgError, match="asset not found"):
        set_page_background(tmp_path / "nope.png", report, "pg")


def test_missing_page_raises(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    with pytest.raises(PbirPageBgError, match="page.json not found"):
        set_page_background(ASSET, report, "no_such_page")


def test_refuses_replace_without_force(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    set_page_background(ASSET, report, "pg")
    with pytest.raises(PbirPageBgError, match="already has a background"):
        set_page_background(ASSET, report, "pg")
    set_page_background(ASSET, report, "pg", force=True)  # ok with force


def test_deterministic_reapply_with_force(tmp_path: Path) -> None:
    report = _report_copy(tmp_path)
    set_page_background(ASSET, report, "pg", force=True)
    first = (report / "definition/pages/pg/page.json").read_text()
    set_page_background(ASSET, report, "pg", force=True)
    assert (report / "definition/pages/pg/page.json").read_text() == first
