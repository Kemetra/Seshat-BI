"""Unit tests for SL1 -- Coverage Scorecard Linter (spec 056).

Contracts (from tasks.md / spec.md):
  C1  status outside the closed enum            -> one Finding
  C2  a `Blocked -- ...` row with no named blocker -> one Finding
  C3  a `Covered` row citing a non-resolving contracts/<file>.md -> one Finding
  C3b a `Planned` / `Out of scope` row with `--` contract -> no Finding
  C4  a number-then-`%` token anywhere          -> one Finding
  C4b a `%` with no adjacent digit (e.g. in a KPI name) -> no Finding
  C5  a fully well-formed generic scorecard     -> no Finding
  C6  the explicit template path / a tests/ fixture path -> never scanned
  C7  no committed instance                     -> silent pass (by absence)
  C8  an unreadable selected instance           -> fail-loud ERROR Finding
  C9  a stray 4-col table outside the anchored status table contributes no rows
"""

from __future__ import annotations

import pytest

from retail.core import RuleContext, Severity
from retail.rules.scorecard import _TEMPLATE_PATH, check_coverage_scorecard

pytestmark = pytest.mark.unit


def _ctx(tmp_path, files: dict[str, str]) -> RuleContext:
    """Write files under tmp_path and build a RuleContext over them."""
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(files.keys()))


def _scorecard(rows: str) -> str:
    return (
        "# Coverage scorecard\n\n"
        "> Table: `schema.tbl` -- generic grain\n\n"
        "| KPI | Contract | Coverage status | Blocker |\n"
        "|-----|----------|-----------------|------------------------------------------|\n"
        + rows
    )


INST = "mappings/tbl/tbl-coverage-scorecard.md"


def _findings(ctx):
    return [f for f in check_coverage_scorecard(ctx) if f.rule_id == "SL1"]


# --- C1: bad status enum ---------------------------------------------------
def test_c1_status_outside_enum_fires(tmp_path):
    body = _scorecard("| Net Sales | `contracts/net.md` | Sorta covered | -- |\n")
    findings = _findings(_ctx(tmp_path, {INST: body, "contracts/net.md": "x"}))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert INST in findings[0].locator


# --- C2: Blocked row with no named blocker ---------------------------------
def test_c2_blocked_without_blocker_fires(tmp_path):
    body = _scorecard("| Net Sales | -- | Blocked -- missing field | -- |\n")
    assert len(_findings(_ctx(tmp_path, {INST: body}))) == 1


# --- C3: Covered row citing a non-resolving contract path ------------------
def test_c3_covered_nonresolving_contract_fires(tmp_path):
    body = _scorecard("| Net Sales | `contracts/missing.md` | Covered | -- |\n")
    assert len(_findings(_ctx(tmp_path, {INST: body}))) == 1


# --- C3 (P1 regression): a Covered row's `contracts/<f>.md` citation resolves
# by SUFFIX to the real skills/retail-kpi-knowledge/contracts/<f>.md path -------
def test_c3_covered_contract_resolves_by_suffix(tmp_path):
    body = _scorecard("| Net Sales | `contracts/net-sales.md` | Covered | -- |\n")
    ctx = _ctx(
        tmp_path,
        {
            INST: body,
            "skills/retail-kpi-knowledge/contracts/net-sales.md": "x",
        },
    )
    assert _findings(ctx) == []


# --- C3b: Planned / Out of scope with `--` contract is fine ----------------
def test_c3b_planned_outofscope_dash_contract_ok(tmp_path):
    body = _scorecard(
        "| Future KPI | -- | Planned | -- |\n| Inv KPI | -- | Out of scope | -- |\n"
    )
    assert _findings(_ctx(tmp_path, {INST: body})) == []


# --- C4: number-then-% token ------------------------------------------------
def test_c4_percentage_token_fires(tmp_path):
    body = _scorecard("| Net Sales | `contracts/net.md` | Covered | 70% covered |\n")
    findings = _findings(_ctx(tmp_path, {INST: body, "contracts/net.md": "x"}))
    assert len(findings) >= 1


# --- C4b: % with no adjacent digit is fine ---------------------------------
def test_c4b_percent_sign_no_digit_ok(tmp_path):
    body = _scorecard("| % Growth KPI | `contracts/g.md` | Covered | -- |\n")
    assert _findings(_ctx(tmp_path, {INST: body, "contracts/g.md": "x"})) == []


# --- C5: well-formed scorecard is clean ------------------------------------
def test_c5_wellformed_clean(tmp_path):
    body = _scorecard(
        "| Net Sales | `contracts/net.md` | Covered | -- |\n"
        "| Returns Rate | -- | Blocked -- needs business definition | A2 policy |\n"
        "| Future KPI | -- | Planned | -- |\n"
    )
    assert _findings(_ctx(tmp_path, {INST: body, "contracts/net.md": "x"})) == []


# --- C6: template + tests/ fixtures are never scanned ----------------------
def test_c6_template_path_not_scanned(tmp_path):
    bad = _scorecard("| X | `contracts/missing.md` | Covered | -- |\n")
    ctx = _ctx(tmp_path, {_TEMPLATE_PATH: bad})
    assert _findings(ctx) == []


def test_c6_tests_fixture_not_scanned(tmp_path):
    bad = _scorecard("| X | `contracts/missing.md` | Covered | -- |\n")
    ctx = _ctx(tmp_path, {"tests/fixtures/tbl-coverage-scorecard.md": bad})
    assert _findings(ctx) == []


# --- C7: no committed instance -> silent pass ------------------------------
def test_c7_no_instance_silent_pass(tmp_path):
    ctx = _ctx(tmp_path, {"README.md": "nothing here"})
    assert _findings(ctx) == []


# --- C8: unreadable selected instance -> fail-loud -------------------------
def test_c8_unreadable_instance_fails_loud(tmp_path):
    # A tracked path with no file on disk -> read raises -> ERROR Finding.
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(INST,))
    findings = _findings(ctx)
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR


# --- C9: stray 4-col table outside the status table contributes no rows ----
def test_c9_stray_table_not_parsed(tmp_path):
    body = _scorecard("| Net Sales | `contracts/net.md` | Covered | -- |\n") + (
        "\n## Notes\n\n| a | b | Sorta covered | d |\n|---|---|---|---|\n"
    )
    # The stray 'Sorta covered' is in a Notes table, not the anchored status table.
    assert _findings(_ctx(tmp_path, {INST: body, "contracts/net.md": "x"})) == []


# --- C9b: a stray 4-col table under a ### subheading is not parsed ----------
def test_c9b_subheading_table_not_parsed(tmp_path):
    body = _scorecard("| Net Sales | `contracts/net.md` | Covered | -- |\n") + (
        "\n### Notes\n\n| a | b | Sorta covered | d |\n|---|---|---|---|\n"
    )
    assert _findings(_ctx(tmp_path, {INST: body, "contracts/net.md": "x"})) == []


# --- C9c: a stray table after intervening prose is not parsed --------------
def test_c9c_table_after_prose_not_parsed(tmp_path):
    body = _scorecard("| Net Sales | `contracts/net.md` | Covered | -- |\n") + (
        "\nSome prose here.\n\n| a | b | Sorta covered | d |\n|---|---|---|---|\n"
    )
    assert _findings(_ctx(tmp_path, {INST: body, "contracts/net.md": "x"})) == []


# --- malformed row: a 3-cell pipe row inside the table is flagged, not skipped ---
def test_malformed_row_flagged(tmp_path):
    body = _scorecard(
        "| Net Sales | `contracts/net.md` | Covered | -- |\n"
        "| Broken KPI | contracts/x.md | Covered |\n"  # only 3 cells -- missing Blocker
    )
    findings = _findings(_ctx(tmp_path, {INST: body, "contracts/net.md": "x"}))
    assert len(findings) == 1
    assert "malformed" in findings[0].message.lower()
    assert findings[0].severity is Severity.ERROR


# --- glob: a *coverage-scorecard.md OUTSIDE mappings/ is not scanned --------
def test_non_mappings_scorecard_not_scanned(tmp_path):
    bad = _scorecard("| X | `contracts/missing.md` | Covered | -- |\n")
    ctx = _ctx(tmp_path, {"docs/reference/x-coverage-scorecard.md": bad})
    assert _findings(ctx) == []


# --- C8b: an invalid-UTF-8 instance -> fail-loud ERROR, not a crash --------
def test_c8b_invalid_utf8_fails_loud(tmp_path):
    p = tmp_path / INST
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xff\xfe invalid utf8 \x80\x81")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(INST,))
    findings = _findings(ctx)
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
