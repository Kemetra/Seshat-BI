from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts.export_agent_bundles import (
    BuildOptions,
    ExportError,
    build_bundle,
    load_allowlist,
    validate_allowlist,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_CANONICAL_ROOTS = {
    "skills/bi-sql-knowledge/SKILL.md",
    "skills/bi-dax-knowledge/SKILL.md",
    "skills/bi-python-knowledge/SKILL.md",
    "skills/bi-bigdata-knowledge/SKILL.md",
    "skills/retail-kpi-knowledge/SKILL.md",
    "skills/bi-analyst-knowledge/SKILL.md",
}
EXPECTED_EXPANDED_SOURCES = {
    "contracts/knowledge/knowledge-layer-handoff.yaml",
    "skills/bi-analyst-knowledge/action-and-review-cadence.md",
    "skills/bi-analyst-knowledge/checklists/narrative-judgment-review-checklist.md",
    "skills/bi-analyst-knowledge/diagnostic-question-tree.md",
    "skills/bi-analyst-knowledge/narrative-change-review.md",
    "skills/bi-bigdata-knowledge/checklists/operational-evidence-checklist.md",
    "skills/bi-bigdata-knowledge/knowledge/backfills-and-partition-evolution.md",
    "skills/bi-bigdata-knowledge/knowledge/observability-and-partial-failures.md",
    "skills/bi-dax-knowledge/checklists/dax-diagnostic-checklist.md",
    "skills/bi-dax-knowledge/knowledge/dax-calculation-groups-and-precedence.md",
    "skills/bi-dax-knowledge/knowledge/dax-relationships-and-virtual-filters.md",
    "skills/bi-dax-knowledge/knowledge/dax-semi-additive-and-blank-semantics.md",
    "skills/bi-python-knowledge/checklists/dataframe-review-checklist.md",
    "skills/bi-python-knowledge/checklists/merge-fanout-checklist.md",
    "skills/bi-python-knowledge/checklists/python-pipeline-review-checklist.md",
    "skills/bi-python-knowledge/checklists/validation-reconciliation-checklist.md",
    "skills/bi-python-knowledge/knowledge/dataframe-mental-model.md",
    "skills/bi-python-knowledge/knowledge/dates-times-and-calendars.md",
    "skills/bi-python-knowledge/knowledge/joins-merge-and-fanout.md",
    "skills/bi-python-knowledge/knowledge/nulls-missing-values-and-blanks.md",
    "skills/bi-python-knowledge/knowledge/pandas-dtypes-and-schema.md",
    "skills/bi-python-knowledge/knowledge/performance-and-memory.md",
    "skills/bi-python-knowledge/knowledge/profiling-and-source-inspection.md",
    "skills/bi-python-knowledge/knowledge/python-anti-patterns.md",
    "skills/bi-python-knowledge/knowledge/python-core-concepts-for-bi.md",
    "skills/bi-python-knowledge/knowledge/python-retail-examples.md",
    "skills/bi-python-knowledge/knowledge/validation-and-reconciliation.md",
    "skills/bi-python-knowledge/patterns/analyzer-rules.json",
    "skills/bi-python-knowledge/patterns/python-patterns.json",
    "skills/bi-python-knowledge/patterns/validation-patterns.json",
    "skills/bi-sql-knowledge/checklists/postgresql-plan-review-checklist.md",
    "skills/bi-sql-knowledge/knowledge/postgresql-execution-plans.md",
    "skills/bi-sql-knowledge/patterns/postgresql-plan-patterns.json",
    "skills/retail-kpi-knowledge/checklists/kpi-policy-decision-checklist.md",
    "skills/retail-kpi-knowledge/knowledge/kpi-sufficiency-and-policy-decisions.md",
    "skills/retail-kpi-knowledge/references/implementation-handoff-template.md",
}


def test_repository_allowlist_has_literal_reviewed_entries() -> None:
    document = load_allowlist(ROOT)
    assert set(document["canonical_roots"]) == EXPECTED_CANONICAL_ROOTS
    entries = validate_allowlist(ROOT, document, allow_untracked_inputs=True)
    assert EXPECTED_EXPANDED_SOURCES <= {
        str(entry["source"]) for entry in entries
    }
    assert len(entries) > 100
    assert all("*" not in str(entry["source"]) for entry in entries)


def test_canonical_roots_cannot_be_redefined_by_the_allowlist() -> None:
    document = copy.deepcopy(load_allowlist(ROOT))
    document["canonical_roots"][0] = "skills/other/SKILL.md"
    with pytest.raises(ExportError, match="six Seshat skills"):
        validate_allowlist(ROOT, document, allow_untracked_inputs=True)


@pytest.mark.parametrize("source", ["skills/**", "../secret.md", "C:/secret.md"])
def test_unsafe_source_paths_fail_closed(source: str) -> None:
    document = copy.deepcopy(load_allowlist(ROOT))
    document["entries"][0]["source"] = source
    with pytest.raises(ExportError, match="literal POSIX|escapes|drive"):
        validate_allowlist(ROOT, document, allow_untracked_inputs=True)


def test_untracked_and_symlink_inputs_fail_closed(tmp_path: Path) -> None:
    document = copy.deepcopy(load_allowlist(ROOT))
    with pytest.raises(ExportError, match="not tracked"):
        validate_allowlist(ROOT, document, tracked_paths=set())
    source = tmp_path / "source.md"
    source.write_text("safe\n", encoding="utf-8")
    link = tmp_path / "link.md"
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    minimal = copy.deepcopy(document)
    minimal["entries"][0]["source"] = "link.md"
    with pytest.raises(ExportError, match="symlink"):
        validate_allowlist(
            tmp_path,
            minimal,
            tracked_paths={"link.md"},
            allow_untracked_inputs=True,
        )


def test_secret_marker_is_rejected_before_export(tmp_path: Path) -> None:
    source = (
        ROOT
        / "distribution"
        / "bundle-templates"
        / "shared"
        / "portable-operating-contract.md"
    )
    original = source.read_bytes()
    try:
        source.write_bytes(original + b"\nghp_abcdefghijklmnopqrstuvwxyz123456\n")
        with pytest.raises(ExportError, match="GitHub token"):
            build_bundle(
                ROOT,
                "claude",
                tmp_path / "bundle",
                BuildOptions(allow_untracked_inputs=True),
            )
    finally:
        source.write_bytes(original)


def test_missing_transitive_markdown_reference_fails_closed(tmp_path: Path) -> None:
    source = (
        ROOT
        / "distribution"
        / "bundle-templates"
        / "shared"
        / "portable-operating-contract.md"
    )
    original = source.read_bytes()
    try:
        source.write_bytes(original + b"\n[missing](missing-public-file.md)\n")
        with pytest.raises(ExportError, match="transitive reference"):
            build_bundle(
                ROOT,
                "codex",
                tmp_path / "bundle",
                BuildOptions(allow_untracked_inputs=True),
            )
    finally:
        source.write_bytes(original)
