"""SC-scale coverage (spec 120, T100): 100 tables / 2,000 evidence references.

Plan targets: read-only projection within two seconds for a 100-table
workspace; passport and explorer generation within 10 seconds for 100 tables
and 2,000 evidence references. Timings use generous CI-safe bounds around
those product targets.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_TABLES = 100
_EVIDENCE_PER_TABLE = 20  # 100 x 20 = 2,000 evidence references


@pytest.fixture(scope="module")
def big_workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("scale")
    for index in range(_TABLES):
        table = f"table_{index:03d}"
        table_dir = root / "mappings" / table
        table_dir.mkdir(parents=True)
        references = []
        for evidence_index in range(_EVIDENCE_PER_TABLE):
            name = f"evidence-{evidence_index:02d}.md"
            (table_dir / name).write_text(
                f"evidence {index}/{evidence_index}\n", encoding="utf-8"
            )
            references.append(f"mappings/{table}/{name}")
        listed = ", ".join(references)
        (table_dir / "readiness-status.yaml").write_text(
            f"""\
table: {table}
current_stage: mapping_ready
stages:
  source_ready:
    status: pass
    evidence: [{listed}]
    blocking_reasons: []
  mapping_ready:
    status: blocked
    evidence: []
    blocking_reasons: [grain needs owner approval]
blocking_reasons: [grain needs owner approval]
approvals: []
next_action: Resolve grain with the data owner.
""",
            encoding="utf-8",
        )
    return root


def test_readiness_projection_stays_responsive_at_100_tables(
    big_workspace: Path,
) -> None:
    from seshat.readiness_projection import build_readiness_projection

    started = time.perf_counter()
    projection = build_readiness_projection(big_workspace)
    elapsed = time.perf_counter() - started
    assert len(projection["tables"]) == _TABLES
    assert elapsed < 4.0, f"projection took {elapsed:.2f}s for {_TABLES} tables"


def test_passport_export_handles_2000_evidence_references(
    big_workspace: Path,
) -> None:
    from seshat.passport import build_passport

    started = time.perf_counter()
    passport = build_passport(big_workspace)
    elapsed = time.perf_counter() - started
    evidence = [item for item in passport["artifacts"] if item["kind"] == "evidence"]
    assert len(evidence) == _TABLES * _EVIDENCE_PER_TABLE
    assert elapsed < 15.0, f"passport export took {elapsed:.2f}s"


def test_explorer_generation_handles_the_reference_scale(
    big_workspace: Path,
) -> None:
    from seshat.explorer.build import build_explorer_projection, render_explorer_html

    started = time.perf_counter()
    projection = build_explorer_projection(big_workspace)
    html = render_explorer_html(projection, repo=big_workspace)
    elapsed = time.perf_counter() - started
    assert len(projection["tables"]) == _TABLES
    assert html.count('class="table-card"') == _TABLES
    assert elapsed < 15.0, f"explorer generation took {elapsed:.2f}s"
