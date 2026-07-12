"""CLI-level test for `retail pbir-validate-blueprint` (US8, spec 123, T045).

Mirrors the shape of `test_pbir_geometry_cli.py`: exercises the wired
`_DISPATCH` entry through `seshat.cli.main`, not the library function directly.
Read-only -- exit code communicates conformity (0 = pass, 1 = blocked); the CLI
never writes a file and never grants approval.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "pbir"
_PAGE_SHELL_SAMPLE = _FIXTURES / "page_shell.Report"
_LINECHART_SAMPLE = _FIXTURES / "visual_fmt.Report"
_PAGE_NAME = "a1b2c3d4e5f600112233"

_BLUEPRINT_YAML = """\
page_name: branch_perf
visuals:
  - visual_id: "v05"
    section: "main_insight"
    binds_contract: "TotalSales"
"""

_BINDING_MAP_MD = """\
| visual_id | visual_type | business_question | bound_contract (approved) | field |
|-----------|-------------|-------------------|---------------------------|-------|
| `v05` | `lineChart` | `q` | `TotalSales` | `fct_sales_rss.total_sales` |
"""


def _sample_visual_json(sample: Path) -> Path:
    return sample / "definition" / "pages" / "pg" / "visuals" / "v1" / "visual.json"


def _committed_visual_json(report_dir: Path, visual_id: str) -> Path:
    pages = report_dir / "definition" / "pages"
    return pages / _PAGE_NAME / "visuals" / visual_id / "visual.json"


def _setup(tmp_path: Path) -> tuple[Path, Path, Path]:
    report_dir = tmp_path / "RetailStoreSales.Report"
    shutil.copytree(_PAGE_SHELL_SAMPLE, report_dir)
    visual_src = _sample_visual_json(_LINECHART_SAMPLE)
    visual_dst = _committed_visual_json(report_dir, "v05")
    visual_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(visual_src, visual_dst)

    blueprint = tmp_path / "dashboard-page-blueprint.branch_perf.yaml"
    blueprint.write_text(_BLUEPRINT_YAML, encoding="utf-8")
    binding_map = tmp_path / "visual-contract-binding-map.md"
    binding_map.write_text(_BINDING_MAP_MD, encoding="utf-8")
    return report_dir, blueprint, binding_map


def test_cli_conforming_report_exit_zero(tmp_path: Path):
    report_dir, blueprint, binding_map = _setup(tmp_path)
    rc = main(
        [
            "pbir-validate-blueprint",
            "--report",
            str(report_dir),
            "--blueprint",
            str(blueprint),
            "--binding-map",
            str(binding_map),
        ]
    )
    assert rc == 0


def test_cli_unapproved_visual_exit_one(tmp_path: Path):
    report_dir, blueprint, binding_map = _setup(tmp_path)
    orphan_src = _sample_visual_json(_LINECHART_SAMPLE)
    orphan_dst = _committed_visual_json(report_dir, "v99")
    orphan_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(orphan_src, orphan_dst)

    rc = main(
        [
            "pbir-validate-blueprint",
            "--report",
            str(report_dir),
            "--blueprint",
            str(blueprint),
            "--binding-map",
            str(binding_map),
        ]
    )
    assert rc == 1


@pytest.mark.parametrize("missing_source", ["blueprint", "binding_map"])
def test_cli_blocks_on_unreadable_required_source(tmp_path: Path, missing_source: str):
    # M1 fail-open regression (FR-030/FR-034): a required expected-source that is
    # missing/unreadable previously rolled up to pass/exit 0 (empty inputs -> no
    # missing_elements detected). A check surface must fail CLOSED on either the
    # blueprint OR the binding map being unreadable.
    report_dir, blueprint, binding_map = _setup(tmp_path)
    if missing_source == "blueprint":
        blueprint = tmp_path / "no-such-blueprint.yaml"
    else:
        binding_map = tmp_path / "does-not-exist.md"

    rc = main(
        [
            "pbir-validate-blueprint",
            "--report",
            str(report_dir),
            "--blueprint",
            str(blueprint),
            "--binding-map",
            str(binding_map),
        ]
    )
    assert rc == 1


def test_blocked_result_names_the_unreadable_source(tmp_path: Path):
    # The blocked verdict must NAME the unreadable source (FR-034) and grant nothing.
    from seshat.pbir_validate_blueprint import validate_blueprint

    report_dir = tmp_path / "Empty.Report"
    report_dir.mkdir()
    blueprint = tmp_path / "dashboard-page-blueprint.branch_perf.yaml"
    blueprint.write_text(_BLUEPRINT_YAML, encoding="utf-8")
    missing_binding = tmp_path / "does-not-exist.md"

    result = validate_blueprint(
        report_dir=report_dir,
        blueprint_path=blueprint,
        binding_map_path=missing_binding,
    )
    assert result.status == "blocked"
    assert result.grants_approval is False
    assert any(
        d.dimension == "unreadable_source" and str(missing_binding) in d.locator
        for d in result.deviations
    )


def test_cli_writes_no_files(tmp_path: Path):
    report_dir, blueprint, binding_map = _setup(tmp_path)
    before = {p for p in report_dir.rglob("*") if p.is_file()}

    main(
        [
            "pbir-validate-blueprint",
            "--report",
            str(report_dir),
            "--blueprint",
            str(blueprint),
            "--binding-map",
            str(binding_map),
        ]
    )

    after = {p for p in report_dir.rglob("*") if p.is_file()}
    assert before == after
