"""Acceptance coverage for `retail pack scaffold|validate` (spec 120, US5).

Covers the scaffold-to-validate loop (SC-006), the reference packs, and the
no-pack-core guarantee (FR-031): the core readiness surface behaves
identically whether or not any pack exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.integration

_REPO = Path(__file__).parents[2]
_REFERENCE_PACKS = [
    "packs/reference/kpi-basic/seshat-pack.yaml",
    "packs/reference/source-vocabulary-basic/seshat-pack.yaml",
    "packs/reference/accessibility-basic/seshat-pack.yaml",
]


def test_scaffolded_pack_validates_cleanly(tmp_path: Path) -> None:
    assert (
        main(
            [
                "pack",
                "scaffold",
                "--repo",
                str(tmp_path),
                "--id",
                "acme.retail-kpis",
                "--category",
                "kpi",
                "--owner",
                "Casey Analyst",
            ]
        )
        == 0
    )
    manifest = tmp_path / "packs/local/retail-kpis/seshat-pack.yaml"
    assert manifest.is_file()
    assert (
        main(["pack", "validate", "--repo", str(tmp_path), "--pack", str(manifest)])
        == 0
    )


def test_scaffold_refuses_existing_target(tmp_path: Path) -> None:
    args = [
        "pack",
        "scaffold",
        "--repo",
        str(tmp_path),
        "--id",
        "acme.retail-kpis",
        "--category",
        "kpi",
        "--owner",
        "Casey Analyst",
    ]
    assert main(args) == 0
    assert main(args) == 2


def test_three_reference_packs_pass_the_same_conformance_process() -> None:
    args = ["pack", "validate", "--repo", str(_REPO)]
    for manifest in _REFERENCE_PACKS:
        args += ["--pack", manifest]
    assert main(args) == 0


def test_validate_reports_findings_with_exit_1(tmp_path: Path) -> None:
    assert (
        main(
            [
                "pack",
                "scaffold",
                "--repo",
                str(tmp_path),
                "--id",
                "acme.retail-kpis",
                "--category",
                "kpi",
                "--owner",
                "Casey Analyst",
            ]
        )
        == 0
    )
    starter = tmp_path / "packs/local/retail-kpis/artifacts/kpi-template.yaml"
    starter.unlink()
    assert (
        main(
            [
                "pack",
                "validate",
                "--repo",
                str(tmp_path),
                "--pack",
                "packs/local/retail-kpis/seshat-pack.yaml",
            ]
        )
        == 1
    )


def test_unreadable_manifest_exits_2(tmp_path: Path) -> None:
    assert (
        main(
            [
                "pack",
                "validate",
                "--repo",
                str(tmp_path),
                "--pack",
                "packs/absent/seshat-pack.yaml",
            ]
        )
        == 2
    )


def test_core_readiness_surface_works_with_zero_packs(tmp_path: Path) -> None:
    # FR-031: a workspace with no packs/ directory is fully functional.
    table_dir = tmp_path / "mappings/orders"
    table_dir.mkdir(parents=True)
    (table_dir / "readiness-status.yaml").write_text(
        """\
table: orders
current_stage: source_ready
stages:
  source_ready:
    status: blocked
    evidence: []
    blocking_reasons: [profile pending]
blocking_reasons: [profile pending]
approvals: []
next_action: Profile the source.
""",
        encoding="utf-8",
    )
    assert main(["status", "--repo", str(tmp_path)]) == 0
    assert not (tmp_path / "packs").exists()
