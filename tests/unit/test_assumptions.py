"""Unit tests for AL1 -- Assumption Ledger Rule (spec 059).

AL1 ERRORs when a metric contract records an UNRESOLVED assumption
(``readiness.status == "blocked"`` with a non-empty ``blocking_reasons[]``) AND ALSO
carries a SETTLED gold binding (a non-placeholder ``binds_to.gold_table`` + a non-empty,
non-placeholder ``binds_to.columns``). That is "a settled binding presented atop a
self-declared open question". It never fires on an honest blocked draft whose binding is
still a placeholder, nor on a ``pass`` contract.

Contracts:
  C1  blocked + non-empty blocking_reasons + filled binds_to  -> one ERROR
  C2  blocked + placeholder/empty binds_to                    -> no Finding (draft)
  C3  pass + bound                                            -> no Finding
  C5  no mappings/*/metrics/*.yaml                            -> no Finding
  C6  tracked-but-unparseable contract                        -> fail-loud ERROR
"""

from __future__ import annotations

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.assumptions import _TEMPLATE_PATH, check_unresolved_assumptions

pytestmark = pytest.mark.unit

INST = "mappings/demo_table/metrics/DemoMetric.yaml"


def _ctx(tmp_path, files: dict[str, str]) -> RuleContext:
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(files.keys()))


def _contract(status: str, blocking: str, gold_table: str, columns: str) -> str:
    return (
        "name: DemoMetric\n"
        "binds_to:\n"
        f"  gold_table: {gold_table}\n"
        "  columns:\n"
        f"{columns}"
        "readiness:\n"
        f'  status: "{status}"\n'
        f"  blocking_reasons: {blocking}\n"
    )


def _findings(ctx):
    return [f for f in check_unresolved_assumptions(ctx) if f.rule_id == "AL1"]


# C1: blocked + reasons + filled binding -> ERROR
def test_c1_blocked_with_settled_binding_fires(tmp_path):
    body = _contract(
        "blocked",
        '["A4 gross/net denominator not ruled"]',
        '"gold.fct_demo"',
        '    - "net_amount"\n',
    )
    findings = _findings(_ctx(tmp_path, {INST: body}))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert INST in findings[0].locator


# C2: blocked but binding still a placeholder -> honest draft, no Finding
def test_c2_blocked_placeholder_binding_ok(tmp_path):
    body = _contract(
        "blocked",
        '["still deciding"]',
        '"gold.<fact_or_dim>"',
        '    - "<gold_column_a>"\n',
    )
    assert _findings(_ctx(tmp_path, {INST: body})) == []


def test_c2_blocked_empty_columns_ok(tmp_path):
    body = (
        "name: DemoMetric\n"
        "binds_to:\n"
        '  gold_table: "gold.fct_demo"\n'
        "  columns: []\n"
        "readiness:\n"
        '  status: "blocked"\n'
        '  blocking_reasons: ["open"]\n'
    )
    assert _findings(_ctx(tmp_path, {INST: body})) == []


# C3: pass + bound -> no Finding
def test_c3_pass_bound_ok(tmp_path):
    body = _contract(
        "pass",
        "[]",
        '"gold.fct_demo"',
        '    - "net_amount"\n',
    )
    assert _findings(_ctx(tmp_path, {INST: body})) == []


# C5: no metric contracts at all -> silent pass
def test_c5_no_contracts_silent_pass(tmp_path):
    assert _findings(_ctx(tmp_path, {"README.md": "nothing"})) == []


# C6: unparseable contract -> fail-loud ERROR
def test_c6_unparseable_fails_loud(tmp_path):
    body = "name: DemoMetric\nbinds_to: {{{ not valid yaml\n"
    findings = _findings(_ctx(tmp_path, {INST: body}))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR


# C6b: invalid-UTF-8 contract -> fail-loud ERROR, not a crash (UnicodeDecodeError)
def test_c6b_invalid_utf8_fails_loud(tmp_path):
    p = tmp_path / INST
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xff\xfe binds_to: \x80\x81 not decodable")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(INST,))
    findings = _findings(ctx)
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR


# C6c: tracked-but-deleted-on-disk contract (#430: deleted-but-unstaged) still
# fails loud. AL1 is a PRESENCE-requiring rule -- a deleted required metric
# contract IS a governance finding, so the fix for the runner's #430 crash
# must NOT make this pass vacuously by dropping the path from tracked_files.
def test_c6c_deleted_but_tracked_contract_still_fires_loud(tmp_path):
    # RuleContext.tracked_files lists the path but nothing exists on disk --
    # exactly what `git ls-files` reports for a deleted-but-unstaged file.
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(INST,))
    findings = _findings(ctx)
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert INST in findings[0].locator


# Template is never scanned
def test_template_not_scanned(tmp_path):
    body = _contract(
        "blocked",
        '["open"]',
        '"gold.fct_demo"',
        '    - "net_amount"\n',
    )
    assert _findings(_ctx(tmp_path, {_TEMPLATE_PATH: body})) == []
