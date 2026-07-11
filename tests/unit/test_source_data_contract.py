"""Unit tests for HR12 (forward source data-contract presence)."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.source_data_contract import check_hr12

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]

_FILLED = """\
schema:
  - name: "order_id"
    type: "integer"
  - name: "order_date"
    type: "date"

arrival:
  cadence: "daily by 6am"

restatement:
  policy: "never resends; source system is append-only per upstream SLA"
"""


def _write(tmp_path: Path, rel: str, text: str) -> str:
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return rel


def _ctx(tmp_path: Path, *rel: str) -> RuleContext:
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(rel))


# --- US1: filled contract passes; absent contract is not-applicable ---------


def test_hr12_fully_filled_contract_passes_with_no_finding(tmp_path: Path) -> None:
    rel = _write(tmp_path, "mappings/some_table/source-data-contract.yaml", _FILLED)
    ctx = _ctx(tmp_path, rel)
    assert list(check_hr12(ctx)) == []


def test_hr12_no_contract_file_is_not_applicable(tmp_path: Path) -> None:
    # A table with no source-data-contract.yaml at all -- opt-in, never penalized.
    ctx = _ctx(tmp_path, "mappings/some_table/source-map.yaml")
    assert list(check_hr12(ctx)) == []


def test_hr12_template_path_is_excluded_from_evaluation(tmp_path: Path) -> None:
    template_rel = "templates/source-data-contract.yaml"
    sentinel_sql = (
        "schema:\n"
        '  - name: "REPLACE_ME_COLUMN_NAME"\n'
        '    type: "REPLACE_ME_COLUMN_TYPE"\n'
        "arrival:\n"
        '  cadence: "REPLACE_ME_ARRIVAL_CADENCE"\n'
        "restatement:\n"
        '  policy: "REPLACE_ME_RESTATEMENT_POLICY"\n'
    )
    _write(tmp_path, template_rel, sentinel_sql)
    ctx = _ctx(tmp_path, template_rel)
    assert list(check_hr12(ctx)) == []


def test_hr12_passes_against_real_committed_tree() -> None:
    """No real table has authored a source-data-contract.yaml yet -- zero Findings."""
    tracked: list[str] = []
    mappings_dir = _REPO / "mappings"
    if mappings_dir.exists():
        for p in mappings_dir.rglob("source-data-contract.yaml"):
            tracked.append(str(p.relative_to(_REPO).as_posix()))
    template = _REPO / "templates" / "source-data-contract.yaml"
    if template.exists():
        tracked.append("templates/source-data-contract.yaml")
    ctx = RuleContext(repo_root=_REPO, tracked_files=tuple(tracked))
    assert list(check_hr12(ctx)) == []


# --- US2: declared-but-incomplete contract fails closed ---------------------


def test_hr12_restatement_sentinel_fails_closed_naming_restatement(
    tmp_path: Path,
) -> None:
    sql = (
        "schema:\n"
        '  - name: "order_id"\n'
        '    type: "integer"\n'
        "arrival:\n"
        '  cadence: "daily by 6am"\n'
        "restatement:\n"
        '  policy: "REPLACE_ME_RESTATEMENT_POLICY"\n'
    )
    rel = _write(tmp_path, "mappings/t/source-data-contract.yaml", sql)
    ctx = _ctx(tmp_path, rel)
    findings = list(check_hr12(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert findings[0].rule_id == "HR12"
    assert "restatement" in findings[0].message
    assert "schema" not in findings[0].message.split("restatement")[0]


def test_hr12_blank_arrival_cadence_fails_closed_naming_arrival(
    tmp_path: Path,
) -> None:
    sql = (
        "schema:\n"
        '  - name: "order_id"\n'
        '    type: "integer"\n'
        "arrival:\n"
        '  cadence: ""\n'
        "restatement:\n"
        '  policy: "never resends"\n'
    )
    rel = _write(tmp_path, "mappings/t/source-data-contract.yaml", sql)
    ctx = _ctx(tmp_path, rel)
    findings = list(check_hr12(ctx))
    assert len(findings) == 1
    assert "arrival" in findings[0].message
    assert findings[0].severity is Severity.ERROR


def test_hr12_empty_schema_list_fails_closed_naming_schema(tmp_path: Path) -> None:
    sql = (
        "schema: []\n"
        "arrival:\n"
        '  cadence: "daily by 6am"\n'
        "restatement:\n"
        '  policy: "never resends"\n'
    )
    rel = _write(tmp_path, "mappings/t/source-data-contract.yaml", sql)
    ctx = _ctx(tmp_path, rel)
    findings = list(check_hr12(ctx))
    assert len(findings) == 1
    assert "schema" in findings[0].message
    assert findings[0].severity is Severity.ERROR


def test_hr12_schema_entry_missing_type_fails_closed_naming_schema(
    tmp_path: Path,
) -> None:
    sql = (
        "schema:\n"
        '  - name: "order_id"\n'
        "arrival:\n"
        '  cadence: "daily by 6am"\n'
        "restatement:\n"
        '  policy: "never resends"\n'
    )
    rel = _write(tmp_path, "mappings/t/source-data-contract.yaml", sql)
    ctx = _ctx(tmp_path, rel)
    findings = list(check_hr12(ctx))
    assert len(findings) == 1
    assert "schema" in findings[0].message


def test_hr12_malformed_yaml_fails_closed_naming_the_file(tmp_path: Path) -> None:
    sql = "schema:\n  - name: [unbalanced\n"
    rel = _write(tmp_path, "mappings/t/source-data-contract.yaml", sql)
    ctx = _ctx(tmp_path, rel)
    findings = list(check_hr12(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert findings[0].locator == rel
    # never names a section for a parse error -- nothing could be parsed
    assert "schema" not in findings[0].message
    assert "arrival" not in findings[0].message
    assert "restatement" not in findings[0].message


def test_hr12_multiple_incomplete_sections_each_named_individually(
    tmp_path: Path,
) -> None:
    sql = (
        'schema: []\narrival:\n  cadence: ""\nrestatement:\n  policy: "never resends"\n'
    )
    rel = _write(tmp_path, "mappings/t/source-data-contract.yaml", sql)
    ctx = _ctx(tmp_path, rel)
    findings = list(check_hr12(ctx))
    assert len(findings) == 2
    messages = " ".join(f.message for f in findings)
    assert "schema" in messages
    assert "arrival" in messages


# --- US3: static-only, no live-proof claim, no numeric score ---------------


def test_hr12_module_imports_no_database_driver() -> None:
    src = (_REPO / "src" / "seshat" / "rules" / "source_data_contract.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("import psycopg", "import sqlalchemy", ".connect(", "DSN"):
        assert forbidden not in src


def test_hr12_never_reads_source_map_or_readiness_status(tmp_path: Path) -> None:
    """HR12 must ignore source-map.yaml / readiness-status.yaml even if present.

    Behavioral proof (not a docstring grep, since the module's own docstring
    legitimately NAMES these files in prose to document the collision-avoidance
    boundary, per FR-004): plant both files alongside a filled contract and
    confirm the Findings are identical to the contract-only case.
    """
    contract_rel = _write(tmp_path, "mappings/t/source-data-contract.yaml", _FILLED)
    _write(tmp_path, "mappings/t/source-map.yaml", "meta:\n  freshness: weekly\n")
    _write(tmp_path, "readiness-status.yaml", "tables: {}\n")
    ctx = _ctx(
        tmp_path,
        contract_rel,
        "mappings/t/source-map.yaml",
        "readiness-status.yaml",
    )
    assert list(check_hr12(ctx)) == []


def test_hr12_static_only_unaffected_by_env_dsn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DSN", raising=False)
    sql = (
        "schema:\n"
        '  - name: "order_id"\n'
        '    type: "integer"\n'
        "arrival:\n"
        '  cadence: "daily by 6am"\n'
        "restatement:\n"
        '  policy: "never resends"\n'
    )
    rel = _write(tmp_path, "mappings/t/source-data-contract.yaml", sql)
    ctx = _ctx(tmp_path, rel)
    assert list(check_hr12(ctx)) == []


def test_hr12_message_has_no_numeric_score(tmp_path: Path) -> None:
    sql = "schema: []\n"
    rel = _write(tmp_path, "mappings/t/source-data-contract.yaml", sql)
    ctx = _ctx(tmp_path, rel)
    for f in check_hr12(ctx):
        assert "%" not in f.message
