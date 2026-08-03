"""Workspace scaffolding shared by the report CLI test modules.

Underscore-prefixed so pytest does not collect it, following
``_adopter_sim_helpers.py``. It exists because the offline and live-path CLI tests
need the same table on disk -- an approved readiness status, a print overlay, and
at least one metric contract -- and two copies of that builder would drift into
disagreeing about what "an approved table" is.
"""

from __future__ import annotations

from pathlib import Path

import yaml

TABLE = "demo_table"

LAYOUT = {
    "version": 1,
    "cover_title_code": "cover.board_pack",
    "sections": [
        {
            "section_id": "headline",
            "order": 1,
            "heading_code": "section.headline",
            "visual_ids": ["v1"],
            "page_break_before": False,
        }
    ],
}

_OBSERVATIONS = {
    # The document states which table it was produced for. Without it the loader
    # refuses, because two tables can share visual and contract ids.
    "table": TABLE,
    "observations": [
        {
            "visual_id": "v1",
            "contract_id": "TotalSales",
            "metric": "TotalSales",
            "unit_kind": "currency",
            "label": "Region A",
            "value": "1552071",
        }
    ],
}


def workspace(
    tmp_path: Path,
    *,
    status: str = "pass",
    contracts: tuple[str, ...] = ("TotalSales",),
    evidence: tuple[str, ...] = ("design review APPROVED by data_owner on 2026-06-25",),
) -> tuple[str, Path]:
    """An approved table on disk, plus an observations file for it.

    ``status`` writes the recorded ``dashboard_ready`` status verbatim, so a test
    can set up a table the gate must refuse. ``evidence`` likewise: passing ``()``
    builds the status-with-nothing-behind-it case the gate now refuses.
    ``contracts`` names the metric files to create; passing ``()`` builds a table
    with no approved contracts at all.
    """
    mappings = tmp_path / "mappings" / TABLE
    (mappings / "design").mkdir(parents=True)
    (mappings / "metrics").mkdir(parents=True)
    for name in contracts:
        (mappings / "metrics" / f"{name}.yaml").write_text(
            yaml.safe_dump({"name": name, "readiness": {"status": "pass"}}),
            encoding="utf-8",
        )
    (mappings / "readiness-status.yaml").write_text(
        yaml.safe_dump(
            {
                "table": TABLE,
                "stages": {
                    "dashboard_ready": {"status": status, "evidence": list(evidence)}
                },
            }
        ),
        encoding="utf-8",
    )
    (mappings / "design" / "report-layout.yaml").write_text(
        yaml.safe_dump(LAYOUT, sort_keys=False), encoding="utf-8"
    )
    observations = tmp_path / "obs.yaml"
    observations.write_text(
        yaml.safe_dump(_OBSERVATIONS, sort_keys=False), encoding="utf-8"
    )
    return TABLE, observations
