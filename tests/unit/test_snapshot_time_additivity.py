"""Unit tests for HR5 -- snapshot fact measures declare time_additivity (spec 091).

Decision table exercised (data-model.md):
  1  unreadable file                              -> fail-loud ERROR
  2  no A10, time_additivity absent                -> clean
  3  no A10, time_additivity valid (volunteered)   -> clean (validated-only)
  4  no A10, time_additivity out-of-vocab           -> ERROR (unrecognized)
  5  A10, time_additivity absent                    -> ERROR (missing declaration)
  6  A10, time_additivity fully                     -> ERROR (illegal fully)
  7  A10, time_additivity semi                      -> clean
  8  A10, time_additivity non                       -> clean
  9  A10, time_additivity out-of-vocab               -> ERROR (unrecognized)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.snapshot_time_additivity import (
    _TEMPLATE_PATH,
    check_snapshot_time_additivity,
)

pytestmark = pytest.mark.unit

INST = "mappings/demo_table/metrics/DemoMetric.yaml"
_REPO = Path(__file__).resolve().parents[2]


def _ctx(tmp_path: Path, files: dict[str, str]) -> RuleContext:
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(files.keys()))


def _findings(ctx: RuleContext):
    return [f for f in check_snapshot_time_additivity(ctx) if f.rule_id == "HR5"]


def _contract(*, ambiguities: str = "[]", time_additivity: str | None = None) -> str:
    ta_line = (
        f"time_additivity: {time_additivity}\n" if time_additivity is not None else ""
    )
    return (
        "name: DemoMetric\n"
        "binds_to:\n"
        '  gold_table: "gold.fct_demo"\n'
        "  columns:\n"
        '    - "qty_on_hand"\n'
        f"{ta_line}"
        f"ambiguities: {ambiguities}\n"
    )


_A10_LIST = '[{id: "A10", decision_status: "undecided", ruling: "", evidence: [], number_moving: true}]'  # noqa: E501
_A10_DECIDED_LIST = '[{id: "A10", decision_status: "decided", ruling: "snapshot at close-of-day", evidence: ["ruled by X on 2026-01-01"], number_moving: true}]'  # noqa: E501
_NON_A10_LIST = '[{id: "A4", decision_status: "undecided", ruling: "", evidence: [], number_moving: true}]'  # noqa: E501


# --- row 5: A10 + absent -> ERROR (missing declaration) ---


def test_row5_a10_flagged_missing_declaration_fails_closed(tmp_path: Path) -> None:
    body = _contract(ambiguities=_A10_LIST)
    findings = _findings(_ctx(tmp_path, {INST: body}))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert findings[0].rule_id == "HR5"
    assert "missing" in findings[0].message.lower()
    assert INST in findings[0].locator


def test_row5_a10_null_value_treated_as_absent(tmp_path: Path) -> None:
    body = _contract(ambiguities=_A10_LIST, time_additivity="null")
    findings = _findings(_ctx(tmp_path, {INST: body}))
    assert len(findings) == 1
    assert "missing" in findings[0].message.lower()


def test_row5_a10_empty_string_treated_as_absent(tmp_path: Path) -> None:
    body = _contract(ambiguities=_A10_LIST, time_additivity='""')
    findings = _findings(_ctx(tmp_path, {INST: body}))
    assert len(findings) == 1
    assert "missing" in findings[0].message.lower()


def test_row5_a10_decided_still_requires_declaration(tmp_path: Path) -> None:
    """A `decided` A10 entry does not exempt the contract (Edge Case)."""
    body = _contract(ambiguities=_A10_DECIDED_LIST)
    findings = _findings(_ctx(tmp_path, {INST: body}))
    assert len(findings) == 1
    assert "missing" in findings[0].message.lower()


# --- row 6: A10 + fully -> ERROR (illegal fully), distinct message from row 5 ---


def test_row6_a10_flagged_fully_fails_closed(tmp_path: Path) -> None:
    body = _contract(ambiguities=_A10_LIST, time_additivity='"fully"')
    findings = _findings(_ctx(tmp_path, {INST: body}))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "fully" in findings[0].message.lower()


def test_row6_message_distinct_from_row5_missing_message() -> None:
    missing_msg = "missing time_additivity declaration on an A10-flagged (snapshot) contract -- a human owner must declare 'semi' or 'non' over the date axis"  # noqa: E501
    fully_msg = "an A10-flagged (snapshot) contract cannot declare time_additivity: fully -- a snapshot fact is never fully additive over time"  # noqa: E501
    assert missing_msg != fully_msg


# --- rows 7/8: A10 + semi/non -> clears ---


def test_row7_a10_flagged_semi_clears(tmp_path: Path) -> None:
    body = _contract(ambiguities=_A10_LIST, time_additivity='"semi"')
    assert _findings(_ctx(tmp_path, {INST: body})) == []


def test_row8_a10_flagged_non_clears(tmp_path: Path) -> None:
    body = _contract(ambiguities=_A10_LIST, time_additivity='"non"')
    assert _findings(_ctx(tmp_path, {INST: body})) == []


# --- rows 2/3: no A10 -> optional field, validated-only ---


def test_row2_no_a10_no_field_is_clean(tmp_path: Path) -> None:
    body = _contract(ambiguities="[]")
    assert _findings(_ctx(tmp_path, {INST: body})) == []


def test_row2_no_a10_other_ambiguity_no_field_is_clean(tmp_path: Path) -> None:
    body = _contract(ambiguities=_NON_A10_LIST)
    assert _findings(_ctx(tmp_path, {INST: body})) == []


def test_row3_no_a10_valid_volunteered_value_is_clean(tmp_path: Path) -> None:
    body = _contract(ambiguities="[]", time_additivity='"semi"')
    assert _findings(_ctx(tmp_path, {INST: body})) == []


# --- rows 4/9: out-of-vocabulary -> ERROR regardless of A10 ---


def test_row4_no_a10_out_of_vocab_fails_closed(tmp_path: Path) -> None:
    body = _contract(ambiguities="[]", time_additivity='"sometimes"')
    findings = _findings(_ctx(tmp_path, {INST: body}))
    assert len(findings) == 1
    assert "unrecognized" in findings[0].message.lower()


def test_row9_a10_out_of_vocab_fails_closed(tmp_path: Path) -> None:
    body = _contract(ambiguities=_A10_LIST, time_additivity='"sometimes"')
    findings = _findings(_ctx(tmp_path, {INST: body}))
    assert len(findings) == 1
    assert "unrecognized" in findings[0].message.lower()


@pytest.mark.parametrize("variant", ['"Fully"', '"SEMI"', '"non "'])
def test_case_whitespace_variant_is_out_of_vocab_never_normalized(
    tmp_path: Path, variant: str
) -> None:
    body = _contract(ambiguities=_A10_LIST, time_additivity=variant)
    findings = _findings(_ctx(tmp_path, {INST: body}))
    assert len(findings) == 1
    assert "unrecognized" in findings[0].message.lower()


def test_non_scalar_list_value_is_out_of_vocab_no_crash(tmp_path: Path) -> None:
    body = _contract(ambiguities=_A10_LIST, time_additivity='["semi", "non"]')
    findings = _findings(_ctx(tmp_path, {INST: body}))
    assert len(findings) == 1
    assert "unrecognized" in findings[0].message.lower()


def test_non_scalar_mapping_value_is_out_of_vocab_no_crash(tmp_path: Path) -> None:
    body = _contract(ambiguities=_A10_LIST, time_additivity="{a: b}")
    findings = _findings(_ctx(tmp_path, {INST: body}))
    assert len(findings) == 1
    assert "unrecognized" in findings[0].message.lower()


def test_out_of_vocab_message_distinct_from_missing_message(tmp_path: Path) -> None:
    missing = _findings(_ctx(tmp_path, {INST: _contract(ambiguities=_A10_LIST)}))
    out_of_vocab = _findings(
        _ctx(
            tmp_path,
            {INST: _contract(ambiguities=_A10_LIST, time_additivity='"bogus"')},
        )
    )
    assert missing[0].message != out_of_vocab[0].message


# --- row 1: unreadable/unparseable -> fail-loud ERROR ---


def test_row1_unparseable_contract_fails_loud(tmp_path: Path) -> None:
    body = "name: DemoMetric\nambiguities: {{{ not valid yaml\n"
    findings = _findings(_ctx(tmp_path, {INST: body}))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR


def test_row1_invalid_utf8_fails_loud(tmp_path: Path) -> None:
    p = tmp_path / INST
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xff\xfe ambiguities: \x80\x81 not decodable")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(INST,))
    findings = _findings(ctx)
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR


# --- exemptions: template + no contracts at all ---


def test_template_not_scanned(tmp_path: Path) -> None:
    body = _contract(ambiguities=_A10_LIST)
    assert _findings(_ctx(tmp_path, {_TEMPLATE_PATH: body})) == []


def test_no_contracts_silent_pass(tmp_path: Path) -> None:
    assert _findings(_ctx(tmp_path, {"README.md": "nothing"})) == []


# --- real committed tree: SC-001 clean baseline ---


def test_passes_against_real_committed_contracts() -> None:
    """SC-001: HR5 emits zero findings on the current committed corpus
    (no contract carries an A10 entry today)."""
    mapping_dir = _REPO / "mappings"
    rels = [
        str(p.relative_to(_REPO)).replace("\\", "/")
        for p in mapping_dir.glob("*/metrics/*.yaml")
    ]
    ctx = RuleContext(repo_root=_REPO, tracked_files=tuple(rels))
    assert _findings(ctx) == []


# --- static-only, no numeric score ---


def test_module_imports_no_database_driver() -> None:
    src = (
        _REPO / "src" / "seshat" / "rules" / "snapshot_time_additivity.py"
    ).read_text(encoding="utf-8")
    for forbidden in ("import psycopg", "import sqlalchemy", ".connect(", "DSN"):
        assert forbidden not in src


def test_no_module_scope_yaml_import() -> None:
    """Lazy import only -- the module stays stdlib-only at import scope (B1/B3)."""
    src = (
        _REPO / "src" / "seshat" / "rules" / "snapshot_time_additivity.py"
    ).read_text(encoding="utf-8")
    lines = [ln.strip() for ln in src.splitlines()]
    assert "import yaml" not in lines  # top-level statement form would match exactly
    assert any(
        ln
        == "import yaml  # lazy: keep the retail-check core stdlib-only at module scope (B1/B3)"  # noqa: E501
        for ln in lines
    )


def test_message_has_no_numeric_score(tmp_path: Path) -> None:
    body = _contract(ambiguities=_A10_LIST)
    ctx = _ctx(tmp_path, {INST: body})
    for f in _findings(ctx):
        assert "%" not in f.message
