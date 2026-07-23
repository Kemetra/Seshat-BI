"""Library tests for the offline PBIR binding-resolution validator (#454).

Every test builds its report + model trees under ``tmp_path`` -- deterministic,
no live Power BI, no network, no repo state. The validator is READ-ONLY and
grants no approval; the shape tests pin that structurally (same posture as
``test_pbir_validate_blueprint``'s FR-031 tests).

TMDL fixture text uses REAL TAB indentation (the parser is tab-driven).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.pbir_validate_bindings import (
    BindingFinding,
    BindingValidationResult,
    validate_bindings,
)

pytestmark = pytest.mark.unit

# --------------------------------------------------------------------------- #
# Fixture builders
# --------------------------------------------------------------------------- #

_MODEL_TMDL = (
    "table Sales\n"
    "\tcolumn Amount\n"
    "\t\tdataType: decimal\n"
    "\t\tsummarizeBy: sum\n"
    "\n"
    "\tmeasure 'Total Amount' = SUM(Sales[Amount])\n"
    "\t\tdisplayFolder: Core\n"
    "\n"
    "table dim_staff\n"
    "\tcolumn staff_name_masked\n"
    "\t\tdataType: string\n"
    "\n"
    "table dim_date\n"
    "\tcolumn year\n"
    "\t\tdataType: int64\n"
)


def _write_model(tmp_path: Path, text: str = _MODEL_TMDL) -> Path:
    model_dir = tmp_path / "Demo.SemanticModel"
    tables = model_dir / "definition"
    tables.mkdir(parents=True)
    (tables / "model.tmdl").write_text(text, encoding="utf-8")
    return model_dir


def _write_split_model(tmp_path: Path) -> Path:
    """The Desktop default layout: one table per definition/tables/*.tmdl."""
    model_dir = tmp_path / "Split.SemanticModel"
    tables = model_dir / "definition" / "tables"
    tables.mkdir(parents=True)
    (tables / "Sales.tmdl").write_text(
        "table Sales\n"
        "\tcolumn Amount\n"
        "\t\tdataType: decimal\n"
        "\n"
        "\tmeasure 'Total Amount' = SUM(Sales[Amount])\n",
        encoding="utf-8",
    )
    (tables / "dim_date.tmdl").write_text(
        "table dim_date\n\tcolumn year\n\t\tdataType: int64\n",
        encoding="utf-8",
    )
    return model_dir


def _field(kind: str, entity: str, prop: str) -> dict:
    return {
        kind: {
            "Expression": {"SourceRef": {"Entity": entity}},
            "Property": prop,
        }
    }


def _visual_doc(*fields: dict) -> dict:
    return {
        "name": "v1",
        "visual": {
            "visualType": "lineChart",
            "query": {
                "queryState": {
                    "Y": {
                        "projections": [
                            {"field": f, "queryRef": f"q{i}"}
                            for i, f in enumerate(fields)
                        ]
                    }
                }
            },
        },
    }


def _write_visual(
    report_dir: Path, doc: dict, page: str = "pg", visual_id: str = "v1"
) -> Path:
    visual = (
        report_dir / "definition" / "pages" / page / "visuals" / visual_id
    ) / "visual.json"
    visual.parent.mkdir(parents=True, exist_ok=True)
    visual.write_text(json.dumps(doc), encoding="utf-8")
    return visual


def _write_report(tmp_path: Path, *fields: dict) -> Path:
    report_dir = tmp_path / "Demo.Report"
    _write_visual(report_dir, _visual_doc(*fields))
    return report_dir


# --------------------------------------------------------------------------- #
# Clean resolution
# --------------------------------------------------------------------------- #


def test_resolving_column_and_measure_pass(tmp_path: Path):
    model = _write_model(tmp_path)
    report = _write_report(
        tmp_path,
        _field("Column", "dim_date", "year"),
        _field("Measure", "Sales", "Total Amount"),
    )
    result = validate_bindings(report_dir=report, model_dir=model)
    assert result.status == "pass"
    assert result.unresolved == ()
    assert result.kind_mismatches == ()


def test_resolution_is_case_insensitive(tmp_path: Path):
    # Power BI object names are case-insensitive; a case difference must not
    # fabricate an error card Desktop never shows.
    model = _write_model(tmp_path)
    report = _write_report(tmp_path, _field("Column", "DIM_DATE", "Year"))
    result = validate_bindings(report_dir=report, model_dir=model)
    assert result.status == "pass"


def test_split_tables_layout_resolves(tmp_path: Path):
    model = _write_split_model(tmp_path)
    report = _write_report(tmp_path, _field("Measure", "Sales", "Total Amount"))
    result = validate_bindings(report_dir=report, model_dir=model)
    assert result.status == "pass"


def test_multi_table_model_tmdl_attributes_fields_to_their_own_table(tmp_path: Path):
    # A single model.tmdl carrying several table blocks (Desktop sometimes
    # writes this) must NOT attribute every column to the first table.
    model = _write_model(tmp_path)
    report = _write_report(tmp_path, _field("Column", "Sales", "year"))
    result = validate_bindings(report_dir=report, model_dir=model)
    assert result.status == "blocked"
    assert any(f.dimension == "unresolved_field" for f in result.unresolved)


# --------------------------------------------------------------------------- #
# Unresolved bindings (the #454 error-card class) -> blocked
# --------------------------------------------------------------------------- #


def test_unknown_entity_blocks(tmp_path: Path):
    model = _write_model(tmp_path)
    report = _write_report(tmp_path, _field("Column", "dim_branch", "branch"))
    result = validate_bindings(report_dir=report, model_dir=model)
    assert result.status == "blocked"
    assert any(f.dimension == "unknown_entity" for f in result.unresolved)


def test_missing_column_blocks_and_names_the_near_match(tmp_path: Path):
    # The exact ex-2 defect: a visual bound to the pre-mask column name while
    # the governed model carries the masked rename.
    model = _write_model(tmp_path)
    report = _write_report(tmp_path, _field("Column", "dim_staff", "staff_name"))
    result = validate_bindings(report_dir=report, model_dir=model)
    assert result.status == "blocked"
    finding = next(f for f in result.unresolved if f.dimension == "unresolved_field")
    assert "staff_name_masked" in finding.message  # did-you-mean hint
    assert "renam" in finding.message or "mask" in finding.message


def test_missing_measure_blocks(tmp_path: Path):
    model = _write_model(tmp_path)
    report = _write_report(tmp_path, _field("Measure", "Sales", "Total Margin"))
    result = validate_bindings(report_dir=report, model_dir=model)
    assert result.status == "blocked"
    assert any(f.dimension == "unresolved_field" for f in result.unresolved)


def test_duplicate_references_dedupe_to_one_finding(tmp_path: Path):
    model = _write_model(tmp_path)
    report = _write_report(
        tmp_path,
        _field("Column", "dim_branch", "branch"),
        _field("Column", "dim_branch", "branch"),
    )
    result = validate_bindings(report_dir=report, model_dir=model)
    assert len([f for f in result.unresolved if f.dimension == "unknown_entity"]) == 1


# --------------------------------------------------------------------------- #
# Projection-kind mismatch (the #456 detection side) -> warning, not blocked
# --------------------------------------------------------------------------- #


def test_column_projected_as_measure_warns(tmp_path: Path):
    model = _write_model(tmp_path)
    report = _write_report(tmp_path, _field("Measure", "dim_date", "year"))
    result = validate_bindings(report_dir=report, model_dir=model)
    assert result.status == "warning"
    assert result.unresolved == ()
    assert any(f.dimension == "projection_kind" for f in result.kind_mismatches)


def test_measure_projected_as_column_warns(tmp_path: Path):
    model = _write_model(tmp_path)
    report = _write_report(tmp_path, _field("Column", "Sales", "Total Amount"))
    result = validate_bindings(report_dir=report, model_dir=model)
    assert result.status == "warning"
    assert any(f.dimension == "projection_kind" for f in result.kind_mismatches)


# --------------------------------------------------------------------------- #
# References outside queryState: filters resolve through From-aliases
# --------------------------------------------------------------------------- #


def test_filter_reference_through_from_alias_resolves(tmp_path: Path):
    model = _write_model(tmp_path)
    doc = _visual_doc(_field("Measure", "Sales", "Total Amount"))
    doc["filterConfig"] = {
        "filters": [
            {
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Source": "d"}},
                        "Property": "nope",
                    }
                },
                "filter": {"From": [{"Name": "d", "Entity": "dim_date", "Type": 0}]},
            }
        ]
    }
    report_dir = tmp_path / "Demo.Report"
    _write_visual(report_dir, doc)
    result = validate_bindings(report_dir=report_dir, model_dir=model)
    # alias d -> dim_date; property "nope" is not a dim_date field -> blocked
    assert result.status == "blocked"
    finding = next(f for f in result.unresolved if f.dimension == "unresolved_field")
    assert "dim_date" in finding.message


def test_unresolvable_alias_is_skipped_not_invented(tmp_path: Path):
    model = _write_model(tmp_path)
    doc = _visual_doc(_field("Measure", "Sales", "Total Amount"))
    doc["orphanRef"] = {
        "Column": {
            "Expression": {"SourceRef": {"Source": "zz"}},
            "Property": "whatever",
        }
    }
    report_dir = tmp_path / "Demo.Report"
    _write_visual(report_dir, doc)
    result = validate_bindings(report_dir=report_dir, model_dir=model)
    assert result.status == "pass"


def test_hierarchy_level_wrapper_is_out_of_scope(tmp_path: Path):
    model = _write_model(tmp_path)
    doc = _visual_doc(_field("Measure", "Sales", "Total Amount"))
    doc["visual"]["query"]["queryState"]["Category"] = {
        "projections": [
            {
                "field": {
                    "HierarchyLevel": {
                        "Expression": {
                            "Hierarchy": {
                                "Expression": {"SourceRef": {"Entity": "dim_date"}},
                                "Hierarchy": "Date Hierarchy",
                            }
                        },
                        "Level": "Year",
                    }
                }
            }
        ]
    }
    report_dir = tmp_path / "Demo.Report"
    _write_visual(report_dir, doc)
    result = validate_bindings(report_dir=report_dir, model_dir=model)
    assert result.status == "pass"


def test_page_level_json_is_walked_too(tmp_path: Path):
    model = _write_model(tmp_path)
    report = _write_report(tmp_path, _field("Measure", "Sales", "Total Amount"))
    page_json = report / "definition" / "pages" / "pg" / "page.json"
    page_json.write_text(
        json.dumps(
            {
                "name": "pg",
                "filterConfig": {
                    "filters": [{"field": _field("Column", "dim_branch", "b")}]
                },
            }
        ),
        encoding="utf-8",
    )
    result = validate_bindings(report_dir=report, model_dir=model)
    assert result.status == "blocked"
    assert any(f.dimension == "unknown_entity" for f in result.unresolved)


def test_bom_tolerant_reads(tmp_path: Path):
    model_dir = tmp_path / "Bom.SemanticModel"
    (model_dir / "definition").mkdir(parents=True)
    (model_dir / "definition" / "model.tmdl").write_bytes(
        b"\xef\xbb\xbf" + _MODEL_TMDL.encode("utf-8")
    )
    report_dir = tmp_path / "Bom.Report"
    visual = (
        report_dir / "definition" / "pages" / "pg" / "visuals" / "v1" / "visual.json"
    )
    visual.parent.mkdir(parents=True)
    visual.write_bytes(
        b"\xef\xbb\xbf"
        + json.dumps(_visual_doc(_field("Column", "dim_date", "year"))).encode("utf-8")
    )
    result = validate_bindings(report_dir=report_dir, model_dir=model_dir)
    assert result.status == "pass"


# --------------------------------------------------------------------------- #
# Fail-closed posture (the #453 lesson): never a silent pass over nothing
# --------------------------------------------------------------------------- #


def test_zero_visuals_blocks(tmp_path: Path):
    model = _write_model(tmp_path)
    report_dir = tmp_path / "Empty.Report"
    (report_dir / "definition" / "pages").mkdir(parents=True)
    result = validate_bindings(report_dir=report_dir, model_dir=model)
    assert result.status == "blocked"
    assert any(f.dimension == "unreadable_source" for f in result.unresolved)


def test_missing_report_dir_blocks(tmp_path: Path):
    model = _write_model(tmp_path)
    result = validate_bindings(report_dir=tmp_path / "no-such.Report", model_dir=model)
    assert result.status == "blocked"


def test_zero_model_tables_blocks(tmp_path: Path):
    model_dir = tmp_path / "Hollow.SemanticModel"
    (model_dir / "definition").mkdir(parents=True)
    (model_dir / "definition" / "relationships.tmdl").write_text(
        "relationship r1\n\tfromColumn: Sales.Amount\n", encoding="utf-8"
    )
    report = _write_report(tmp_path, _field("Column", "dim_date", "year"))
    result = validate_bindings(report_dir=report, model_dir=model_dir)
    assert result.status == "blocked"
    assert any(f.dimension == "unreadable_source" for f in result.unresolved)


def test_missing_model_dir_blocks(tmp_path: Path):
    report = _write_report(tmp_path, _field("Column", "dim_date", "year"))
    result = validate_bindings(
        report_dir=report, model_dir=tmp_path / "no-such.SemanticModel"
    )
    assert result.status == "blocked"


def test_corrupt_visual_json_blocks_not_skips(tmp_path: Path):
    # A corrupt visual.json is itself an error-card source -- silently skipping
    # it would be the #453 fail-open pattern all over again.
    model = _write_model(tmp_path)
    report = _write_report(tmp_path, _field("Column", "dim_date", "year"))
    bad = report / "definition" / "pages" / "pg" / "visuals" / "v2" / "visual.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{not json", encoding="utf-8")
    result = validate_bindings(report_dir=report, model_dir=model)
    assert result.status == "blocked"
    assert any(f.dimension == "unparseable_json" for f in result.unresolved)


def test_visuals_with_zero_references_pass_with_visible_count(tmp_path: Path):
    model = _write_model(tmp_path)
    report_dir = tmp_path / "Scaffold.Report"
    _write_visual(report_dir, {"name": "v1", "visual": {"visualType": "card"}})
    result = validate_bindings(report_dir=report_dir, model_dir=model)
    assert result.status == "pass"
    assert any("0 field reference" in line for line in result.evidence)


# --------------------------------------------------------------------------- #
# Shape: read-only evidence, never an approval grant
# --------------------------------------------------------------------------- #


def test_result_never_grants_approval(tmp_path: Path):
    model = _write_model(tmp_path)
    report = _write_report(tmp_path, _field("Column", "dim_date", "year"))
    result = validate_bindings(report_dir=report, model_dir=model)
    assert result.grants_approval is False
    assert not hasattr(result, "approve")
    assert not hasattr(result, "grant_approval")


def test_finding_shape_is_evidence_only():
    finding = BindingFinding(dimension="d", locator="l", message="m")
    assert finding == ("d", "l", "m")
    assert not hasattr(BindingValidationResult, "approve")
