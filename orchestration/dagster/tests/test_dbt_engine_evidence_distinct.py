"""FR-009 + FR-007/SC-005: the two evidence systems stay distinct, and a
dbt-engine run writes ZERO readiness truth.

* Evidence distinctness (T020/FR-009): the dagster record CITES the
  mappings/<table>/dbt-evidence/ path but never merges or copies the dbt
  evidence JSON's internal keys (parity / tests / seshat_exit_code).
* Readiness-no-write (T022/FR-007/SC-005, the spec-134 US3 oracle sitting ON the
  untrusted write path): after a full dbt-engine run, every byte under mappings/
  -- readiness-status.yaml, unresolved-questions.md, approvals, metrics/ -- is
  unchanged. No status:, Gate status:, approvals[], mapping, or metric is written.
"""

from __future__ import annotations

from pathlib import Path

from conftest import TABLE, mappings_digest, stub_green_db
from dagster import materialize
from tower_bi_orchestration.assets import build_table_assets
from tower_bi_orchestration.evidence_writer import (
    EvidenceWriter,
    RunMeta,
    finalize_run,
)

# dbt-evidence-internal keys that MUST NOT leak into the dagster record.
_DBT_EVIDENCE_INTERNAL_KEYS = frozenset(
    {"parity", "tests", "seshat_exit_code", "readiness_effect", "artifacts"}
)


def _set_all_dbt(root: Path) -> None:
    (root / "mappings" / TABLE / "build-engine.yaml").write_text(
        "silver: dbt\ngold: dbt\n", encoding="utf-8"
    )


def _stub_dbt_bridge(monkeypatch) -> None:
    from tower_bi_orchestration.assets import gates

    def fake_build_layer(context, table, layer, root):
        # a canned governed result citing (not merging) the dbt evidence JSON
        measured = {
            "engine": "dbt",
            "selector": f"seshat_table_{table}",
            "dbt_result": "built",
            "dbt_evidence_path": f"mappings/{table}/dbt-evidence/inv-{layer}.json",
        }
        return 0, measured, f"mappings/{table}/dbt-evidence/inv-{layer}.json"

    monkeypatch.setattr(gates.dbt_build, "build_layer", fake_build_layer)


def _full_dbt_run(root: Path):
    return materialize(build_table_assets(TABLE, root), raise_on_error=False)


def test_dagster_record_cites_but_does_not_merge_the_dbt_evidence(
    green_repo, monkeypatch
) -> None:
    from tower_bi_orchestration.assets import gates as _gates

    monkeypatch.setattr(_gates.dbt_build, "profile_present", lambda root: True)
    stub_green_db(monkeypatch)
    _set_all_dbt(green_repo)
    _stub_dbt_bridge(monkeypatch)

    _full_dbt_run(green_repo)
    records = {
        r["asset"]: r for r in EvidenceWriter(green_repo, "testrun-001").records()
    }
    silver = records["silver_tables"]
    measured = silver["measured"]

    # cite: a string path pointing into the distinct dbt-evidence artifact
    citation = measured["dbt_evidence_path"]
    assert isinstance(citation, str)
    assert citation.startswith(f"mappings/{TABLE}/dbt-evidence/")

    # not merge: none of the dbt evidence JSON's internal keys appear here
    leaked = _DBT_EVIDENCE_INTERNAL_KEYS & set(measured)
    assert leaked == set(), f"dbt-evidence internal keys leaked into dagster: {leaked}"


def test_full_dbt_engine_run_writes_zero_readiness_truth(
    green_repo, monkeypatch
) -> None:
    stub_green_db(monkeypatch)
    _set_all_dbt(green_repo)
    _stub_dbt_bridge(monkeypatch)

    before = mappings_digest(green_repo)
    _full_dbt_run(green_repo)
    finalize_run(
        green_repo, "testrun-001", [TABLE], RunMeta(started="2026-07-17T00:00:00Z")
    )

    # The oracle sits ON the untrusted write path: EVERY byte under mappings/
    # (readiness-status.yaml, unresolved-questions.md, approvals, metrics/) is
    # unchanged -- no status:, Gate status:, approvals[], mapping, or metric was
    # written by any code path this feature added.
    assert mappings_digest(green_repo) == before
