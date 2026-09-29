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

from tests.unit._gitfix import commit_tree

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


# Every governed code the report tests use, so a test that only cares about
# figures does not have to author wording. Real reports load this from
# `mappings/<table>/design/report-vocabulary.yaml`; a missing code refuses there
# exactly as it does here.
_TERMS = {
    "cover.board_pack": "Board pack",
    "cover.x": "Cover",
    "section.a": "Section A",
    "section.b": "Section B",
    "section.by_region": "By region",
    "section.detail": "Detail",
    "section.first": "First",
    "section.headline": "Headline",
    "section.mix": "Mix",
    "section.overview": "Overview",
    "section.second": "Second",
    "caveat.demo": "A stated caveat.",
}


def approved_contract(name: str, **extra: object) -> dict:
    """A contract the shared inventory approves (with the approval ``workspace``
    records): owner, checkable definition, gold binding, evidence."""
    return {
        "name": name,
        "owner": "metric_owner",
        "binds_to": {"gold_table": f"gold.fct_{name.lower()}", "columns": ["x"]},
        "definition": {"kind": "base", "aggregation": "sum", "filter": []},
        "readiness": {
            "status": "pass",
            "evidence": ["approved by the named metric owner"],
            "blocking_reasons": [],
        },
        **extra,
    }


def approvals(contracts: tuple[str, ...]) -> list[dict]:
    """The named-human approvals a renderable table records."""
    return [
        {
            "stage": "semantic_model_ready",
            "owner": "Grace Hopper (metric_owner)",
            "at": "2026-06-25",
            "contracts": list(contracts),
        },
        {
            "stage": "dashboard_ready",
            "owner": "Dana Report (report_owner)",
            "at": "2026-06-25",
        },
    ]


def vocabulary(language: str = "en", **extra: str):
    """A Vocabulary covering the codes these tests use."""
    from seshat.report.vocabulary import Vocabulary

    return Vocabulary(language=language, terms={**_TERMS, **extra})


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
    with no approved contracts at all. The workspace is committed (the gate and
    contract inventory read HEAD); a test that edits a file afterwards must
    ``commit_tree`` again for the edit to count.
    """
    mappings = tmp_path / "mappings" / TABLE
    (mappings / "design").mkdir(parents=True)
    (mappings / "metrics").mkdir(parents=True)
    for name in contracts:
        (mappings / "metrics" / f"{name}.yaml").write_text(
            yaml.safe_dump(approved_contract(name)), encoding="utf-8"
        )
    (mappings / "readiness-status.yaml").write_text(
        yaml.safe_dump(
            {
                "table": TABLE,
                "stages": {
                    "dashboard_ready": {"status": status, "evidence": list(evidence)}
                },
                "approvals": approvals(contracts),
            }
        ),
        encoding="utf-8",
    )
    (mappings / "design" / "report-layout.yaml").write_text(
        yaml.safe_dump(LAYOUT, sort_keys=False), encoding="utf-8"
    )
    # Headings are governed codes, so a table without a vocabulary cannot render.
    (mappings / "design" / "report-vocabulary.yaml").write_text(
        yaml.safe_dump(
            {
                "schema": "seshat.report-vocabulary/v1",
                "table": TABLE,
                "languages": {"en": dict(_TERMS)},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    observations = tmp_path / "obs.yaml"
    observations.write_text(
        yaml.safe_dump(_OBSERVATIONS, sort_keys=False), encoding="utf-8"
    )
    # The readiness record and contracts approve a render only once COMMITTED.
    commit_tree(tmp_path)
    return TABLE, observations
