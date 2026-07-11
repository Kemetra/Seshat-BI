"""Unit tests for HR4 (source freshness declaration presence/well-formedness gate)."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.source_freshness import check_hr4

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]


def _map(tmp_path: Path, table: str, yaml_text: str) -> str:
    """Write a source-map.yaml under tmp_path/mappings/<table>/; return its rel path."""
    rel = f"mappings/{table}/source-map.yaml"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(yaml_text, encoding="utf-8")
    return rel


def _ctx(tmp_path: Path, *rel: str) -> RuleContext:
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(rel))


_BASE_META = (
    "meta:\n"
    '  table_id: "{table}"\n'
    '  grain: "one row = one thing"\n'
    "  primary_key:\n"
    '    - "id"\n'
    '  reviewed_by: "data_owner"\n'
)


# --- US1: presence + well-formed passes free ---


def test_hr4_absent_freshness_block_passes(tmp_path: Path) -> None:
    """Presence-gated: absence of meta.freshness is NOT an error (Q-FR014-SCOPE)."""
    sql = _BASE_META.format(table="widgets")
    ctx = _ctx(tmp_path, _map(tmp_path, "widgets", sql))
    assert list(check_hr4(ctx)) == []


def test_hr4_well_formed_block_passes(tmp_path: Path) -> None:
    sql = _BASE_META.format(table="widgets") + (
        '  freshness:\n    expected_cadence: "weekly"\n    max_staleness: "3 days"\n'
    )
    ctx = _ctx(tmp_path, _map(tmp_path, "widgets", sql))
    assert list(check_hr4(ctx)) == []


def test_hr4_one_time_static_with_na_sentinel_passes(tmp_path: Path) -> None:
    sql = _BASE_META.format(table="lookup") + (
        '  freshness:\n    expected_cadence: "one_time"\n    max_staleness: "n/a"\n'
    )
    ctx = _ctx(tmp_path, _map(tmp_path, "lookup", sql))
    assert list(check_hr4(ctx)) == []


def test_hr4_static_synonym_and_case_insensitivity_pass(tmp_path: Path) -> None:
    sql = _BASE_META.format(table="lookup2") + (
        '  freshness:\n    expected_cadence: "  STATIC  "\n    max_staleness: "N/A"\n'
    )
    ctx = _ctx(tmp_path, _map(tmp_path, "lookup2", sql))
    assert list(check_hr4(ctx)) == []


def test_hr4_annually_and_yearly_synonyms_pass(tmp_path: Path) -> None:
    for table, word in (("t_annually", "annually"), ("t_yearly", "yearly")):
        sql = _BASE_META.format(table=table) + (
            "  freshness:\n"
            f'    expected_cadence: "{word}"\n'
            '    max_staleness: "1 year"\n'
        )
        ctx = _ctx(tmp_path, _map(tmp_path, table, sql))
        assert list(check_hr4(ctx)) == [], f"unexpected finding for {word}"


def test_hr4_no_map_at_all_passes(tmp_path: Path) -> None:
    """FR-005: a table with no source-map.yaml (Stage 1) is out of HR4's scope."""
    ctx = _ctx(tmp_path)  # no tracked files
    assert list(check_hr4(ctx)) == []


def test_hr4_template_path_excluded(tmp_path: Path) -> None:
    """Clarification C3: templates/source-map.yaml is schema doc, never evaluated."""
    dest = tmp_path / "templates" / "source-map.yaml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        'meta:\n  freshness:\n    expected_cadence: ""\n    max_staleness: ""\n',
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path, "templates/source-map.yaml")
    assert list(check_hr4(ctx)) == []


def test_hr4_test_fixture_path_excluded(tmp_path: Path) -> None:
    rel = "tests/fixtures/source_freshness/bad/mappings/x/source-map.yaml"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("meta:\n  freshness: not_a_mapping\n", encoding="utf-8")
    ctx = _ctx(tmp_path, rel)
    assert list(check_hr4(ctx)) == []


def test_hr4_passes_against_real_committed_maps() -> None:
    """SC-001/SC-003: HR4 emits zero Findings on the real committed source-maps."""
    map_dir = _REPO / "mappings"
    rels = [
        f"mappings/{p.parent.name}/source-map.yaml"
        for p in sorted(map_dir.glob("*/source-map.yaml"))
    ]
    ctx = RuleContext(repo_root=_REPO, tracked_files=tuple(rels))
    assert list(check_hr4(ctx)) == []


# --- US2: present-but-malformed fails closed; fixing clears ---


def test_hr4_missing_cadence_key_fails_closed(tmp_path: Path) -> None:
    sql = _BASE_META.format(table="widgets") + (
        '  freshness:\n    max_staleness: "2 days"\n'
    )
    ctx = _ctx(tmp_path, _map(tmp_path, "widgets", sql))
    findings = list(check_hr4(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert findings[0].rule_id == "HR4"
    assert "expected_cadence" in findings[0].message
    assert "widgets" in findings[0].message


def test_hr4_blank_cadence_fails_closed(tmp_path: Path) -> None:
    sql = _BASE_META.format(table="widgets") + (
        '  freshness:\n    expected_cadence: "   "\n    max_staleness: "2 days"\n'
    )
    ctx = _ctx(tmp_path, _map(tmp_path, "widgets", sql))
    findings = list(check_hr4(ctx))
    assert len(findings) == 1
    assert "expected_cadence" in findings[0].message


def test_hr4_missing_staleness_key_fails_closed(tmp_path: Path) -> None:
    sql = _BASE_META.format(table="widgets") + (
        '  freshness:\n    expected_cadence: "daily"\n'
    )
    ctx = _ctx(tmp_path, _map(tmp_path, "widgets", sql))
    findings = list(check_hr4(ctx))
    assert len(findings) == 1
    assert "max_staleness" in findings[0].message


def test_hr4_unparseable_cadence_fails_closed(tmp_path: Path) -> None:
    sql = _BASE_META.format(table="widgets") + (
        '  freshness:\n    expected_cadence: "whenever"\n    max_staleness: "2 days"\n'
    )
    ctx = _ctx(tmp_path, _map(tmp_path, "widgets", sql))
    findings = list(check_hr4(ctx))
    assert len(findings) == 1
    assert "expected_cadence" in findings[0].message
    assert "whenever" in findings[0].message


def test_hr4_unparseable_staleness_fails_closed(tmp_path: Path) -> None:
    sql = _BASE_META.format(table="widgets") + (
        '  freshness:\n    expected_cadence: "daily"\n    max_staleness: "a few days"\n'
    )
    ctx = _ctx(tmp_path, _map(tmp_path, "widgets", sql))
    findings = list(check_hr4(ctx))
    assert len(findings) == 1
    assert "max_staleness" in findings[0].message
    assert "a few days" in findings[0].message


def test_hr4_staleness_no_magnitude_fails_closed(tmp_path: Path) -> None:
    sql = _BASE_META.format(table="widgets") + (
        '  freshness:\n    expected_cadence: "daily"\n    max_staleness: "days"\n'
    )
    ctx = _ctx(tmp_path, _map(tmp_path, "widgets", sql))
    findings = list(check_hr4(ctx))
    assert len(findings) == 1


def test_hr4_staleness_unrecognized_unit_fails_closed(tmp_path: Path) -> None:
    sql = _BASE_META.format(table="widgets") + (
        "  freshness:\n"
        '    expected_cadence: "daily"\n'
        '    max_staleness: "2 fortnights"\n'
    )
    ctx = _ctx(tmp_path, _map(tmp_path, "widgets", sql))
    findings = list(check_hr4(ctx))
    assert len(findings) == 1


def test_hr4_both_fields_malformed_emits_two_findings(tmp_path: Path) -> None:
    sql = _BASE_META.format(table="widgets") + (
        '  freshness:\n    expected_cadence: "whenever"\n    max_staleness: "soon"\n'
    )
    ctx = _ctx(tmp_path, _map(tmp_path, "widgets", sql))
    findings = list(check_hr4(ctx))
    assert len(findings) == 2
    fields = {f.locator.rsplit(".", 1)[-1] for f in findings}
    assert fields == {"expected_cadence", "max_staleness"}


def test_hr4_block_not_a_mapping_fails_closed_with_whole_block_locator(
    tmp_path: Path,
) -> None:
    sql = _BASE_META.format(table="widgets") + '  freshness: "not-a-mapping"\n'
    ctx = _ctx(tmp_path, _map(tmp_path, "widgets", sql))
    findings = list(check_hr4(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert findings[0].locator.endswith(":meta.freshness")


def test_hr4_declaration_clears_a_previously_failing_table(tmp_path: Path) -> None:
    """Mutation-verify: fixing the malformed sub-key clears the Finding."""
    bad = _BASE_META.format(table="widgets") + (
        '  freshness:\n    expected_cadence: "whenever"\n    max_staleness: "2 days"\n'
    )
    rel = _map(tmp_path, "widgets", bad)
    ctx = _ctx(tmp_path, rel)
    assert len(list(check_hr4(ctx))) == 1

    good = _BASE_META.format(table="widgets") + (
        '  freshness:\n    expected_cadence: "monthly"\n    max_staleness: "2 days"\n'
    )
    (tmp_path / rel).write_text(good, encoding="utf-8")
    assert list(check_hr4(ctx)) == []


def test_hr4_removing_the_whole_block_also_clears(tmp_path: Path) -> None:
    """Mutation-verify the other direction: blanking/removing the block clears too
    (presence-gated; distinct from 'fixing the value')."""
    bad = _BASE_META.format(table="widgets") + (
        '  freshness:\n    expected_cadence: ""\n    max_staleness: "2 days"\n'
    )
    rel = _map(tmp_path, "widgets", bad)
    ctx = _ctx(tmp_path, rel)
    assert len(list(check_hr4(ctx))) == 1

    absent = _BASE_META.format(table="widgets")
    (tmp_path / rel).write_text(absent, encoding="utf-8")
    assert list(check_hr4(ctx)) == []


def test_hr4_multiple_tables_only_flags_the_offender(tmp_path: Path) -> None:
    good = _BASE_META.format(table="clean_table") + (
        '  freshness:\n    expected_cadence: "daily"\n    max_staleness: "1 day"\n'
    )
    bad = _BASE_META.format(table="dirty_table") + (
        '  freshness:\n    expected_cadence: "daily"\n'
    )
    ctx = _ctx(
        tmp_path,
        _map(tmp_path, "clean_table", good),
        _map(tmp_path, "dirty_table", bad),
    )
    findings = list(check_hr4(ctx))
    assert len(findings) == 1
    assert "dirty_table" in findings[0].message
    assert "clean_table" not in findings[0].message


# --- US3: static-only, no live-proof claim, no numeric score, no writes ---


def test_hr4_module_imports_no_database_or_network_driver() -> None:
    src = (_REPO / "src" / "seshat" / "rules" / "source_freshness.py").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "import psycopg",
        "import sqlalchemy",
        ".connect(",
        "DSN",
        "import socket",
        "import requests",
        "import urllib",
        "MAX(",
    ):
        assert forbidden not in src


def test_hr4_module_never_writes_mapping_or_readiness_artifacts() -> None:
    src = (_REPO / "src" / "seshat" / "rules" / "source_freshness.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("open(", '"w")', "write_text(", ".write("):
        assert forbidden not in src


def test_hr4_never_emits_pending_live_marker(tmp_path: Path) -> None:
    """C4: HR4 itself never emits the live-reporting marker; it only names it
    as a future contract in the docstring."""
    sql = _BASE_META.format(table="widgets") + (
        '  freshness:\n    expected_cadence: "whenever"\n    max_staleness: "2 days"\n'
    )
    ctx = _ctx(tmp_path, _map(tmp_path, "widgets", sql))
    for f in check_hr4(ctx):
        assert "PENDING LIVE FRESHNESS CHECK" not in f.message


def test_hr4_message_has_no_numeric_score(tmp_path: Path) -> None:
    sql = _BASE_META.format(table="widgets") + (
        '  freshness:\n    expected_cadence: "whenever"\n    max_staleness: "soon"\n'
    )
    ctx = _ctx(tmp_path, _map(tmp_path, "widgets", sql))
    for f in check_hr4(ctx):
        assert "%" not in f.message


def test_hr4_requires_no_live_dsn_or_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC-004: check_hr4 runs to completion using only files on disk."""
    monkeypatch.delenv("PGHOST", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    sql = _BASE_META.format(table="widgets") + (
        '  freshness:\n    expected_cadence: "daily"\n    max_staleness: "1 day"\n'
    )
    ctx = _ctx(tmp_path, _map(tmp_path, "widgets", sql))
    assert list(check_hr4(ctx)) == []
